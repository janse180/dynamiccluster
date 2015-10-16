import json
import time
import os, signal, sys
import admin_server
import yaml
import threading
from threading import Thread
from Queue import Empty
from dynamiccluster.daemon import Daemon
from multiprocessing import Process, Queue, cpu_count
from dynamiccluster.admin_server import AdminServer
import dynamiccluster.cluster_manager as cluster_manager
from dynamiccluster.utilities import getLogger, excepthook, get_aws_vcpu_num_by_instance_type, init_object, get_log_level
from dynamiccluster.data import ClusterInfo
from dynamiccluster.data import CloudResource
from dynamiccluster.data import Instance
from dynamiccluster.worker import Worker
from dynamiccluster.worker import Task
from dynamiccluster.worker import Result
from dynamiccluster.data import WorkerNode
import dynamiccluster.__version__ as version
from dynamiccluster.os_manager import OpenStackManager
from dynamiccluster.aws_manager import AWSManager
from dynamiccluster.hooks import run_post_command
from dynamiccluster.exceptions import *
from dynamiccluster.resource_allocator import ResourceAllocator
import logging

log = getLogger(__name__)

class DynamicServer(Daemon):
    def __init__(self, config, pidfile="", working_path="/", stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.__pidfile=pidfile
        self.info=ClusterInfo()
        self.__working_path=working_path
        self.__running=True
        self.task_queue=Queue()
        self.result_queue=Queue()
        self.__workers=[]
        self.__plugin_objects=[]
        self.config=config
        self.engine=None
        
    def __sigTERMhandler(self, signum, frame):
        log.debug("Caught signal %d. Exiting" % signum)
        self.quit()
        
    def init(self):
        self.engine = DynamicEngine(self.config,self.info,self.task_queue,self.result_queue)
        
    def run(self):
        log.info("Starting Dynamic Cluster v" + version.version)
        
        # Install signal handlers
        signal.signal(signal.SIGTERM, self.__sigTERMhandler)
        signal.signal(signal.SIGINT, self.__sigTERMhandler)
        # Ensure unhandled exceptions are logged
        sys.excepthook = excepthook

        log.debug("self.__working_path %s"%self.__working_path)
        adminServer=AdminServer(self.engine, self.__working_path)
        adminServer.daemon = True
        adminServer.start()
        
        worker_process_num=1
        if "worker_process_number" in self.config['dynamic-cluster']:
            worker_process_num=int(self.config['dynamic-cluster']['worker_process_number'])
        else:
            cpu_num=cpu_count()
            if cpu_num>1:
                worker_process_num=cpu_num-1
        for i in xrange(worker_process_num):
            p=Worker(i, self.task_queue, self.result_queue)
            p.daemon=True
            self.__workers.append(p)
        for w in self.__workers:
            w.start()
            log.debug("started worker pid=%d"%w.pid)
        if 'plugins' in self.config:
            plugins=self.config['plugins']
            log.debug("plugins %s" % plugins)
            for plugin_name,plugin in plugins.iteritems():
                class_name=plugin['class_name']
                arguments=plugin['arguments'].copy()
                arguments['_info']=self.info
                arguments['_resource']=self.config['cloud']
                self.__plugin_objects.append(init_object(class_name, **arguments))
        for plugin_obj in self.__plugin_objects:
            #plugin_obj.daemon=True
            plugin_obj.start()
        
        self.engine.start()
            
        for w in self.__workers:
            w.join()
        for plugin_obj in self.__plugin_objects:
            plugin_obj.join()
        self.engine.join()
        self.task_queue.close()
        self.result_queue.close()
        log.info("Dynamic Cluster has stopped")
             
    def quit(self):
#         for i in xrange(len(self.__workers)):
#             log.debug("send Quit to shut down child process")
#             self.__task_queue.put(Task(Task.Quit))
        for w in self.__workers:
            if w.pid>-1:
                try:
                    os.kill(w.pid, signal.SIGTERM)
                except OSError as err:
                    err = str(err)
                    if err.find("No such process") > 0:
                        log.info("Pusher process has gone.")
        for plugin_obj in self.__plugin_objects:
            plugin_obj.stop()
        self.engine.quit()
        log.debug("Waiting for Dynamic Cluster to exit ...")
            
class DynamicEngine(threading.Thread):
    def __init__(self, config, info, task_queue, result_queue):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.config=config
        self.info=info
        self.__running=True
        self.__cluster=None
        self.__auto=self.config['dynamic-cluster'].get('auto_mode', True)
        self.resources=[]
        self.__task_queue=task_queue
        self.__result_queue=result_queue
        self.__resource_allocator=None
        self.__cloud_poller_interval=self.config['dynamic-cluster'].get('cloud_poller_interval', 60)
        self.__auto_provision_interval=self.config['dynamic-cluster'].get('auto_provision_interval', 60)
        self.__max_idle_time=self.config['dynamic-cluster'].get('max_idle_time', 600)
        self.__max_down_time=self.config['dynamic-cluster'].get('max_down_time', 600)
        self.__max_launch_time=self.config['dynamic-cluster'].get('max_launch_time', 1200)

        if self.config['cluster']['type'].lower()=="torque":
            self.__cluster=cluster_manager.TorqueManager(self.config['cluster']['config'])
        elif self.config['cluster']['type'].lower()=="sge":
            self.__cluster=cluster_manager.SGEManager(self.config['cluster']['config'])
        else:
            raise NoClusterDefinedException()
        self.__gather_cluster_info()
        self.__init_resources()
        self.__resource_allocator=ResourceAllocator()

    def quit(self):
        self.__running=False
        
    def __init_resources(self):
        if "cloud" not in self.config:
            raise NoCloudResourceException()
        for res, val in self.config['cloud'].items():
            log.debug(res+" "+str(val))
            self.resources.append(CloudResource(res, **val))
        #get flavor id for openstack resources
        for res in self.resources:
            cloud_manager=None
            if res.type.lower()=="openstack":
                cloud_manager=OpenStackManager(res.name, res.config, max_attempt_time=1)
                res.config['flavor_id'], res.cores_per_node=cloud_manager.get_flavor_details(res.config['flavor'])
            elif res.type.lower()=="aws":
                cloud_manager=AWSManager(res.name, res.config)
                res.cores_per_node=get_aws_vcpu_num_by_instance_type(res.config['instance_type'])
            instance_list=cloud_manager.list()
            for instance in instance_list:
                if instance.state==Instance.Active:
                    workernodes=[w for w in self.info.worker_nodes if w.hostname==instance.dns_name]
                    if len(workernodes)>0:
                        log.debug("instance %s is a worker node in cluster"%instance.dns_name)
                        workernodes[0].instance=instance
                        workernodes[0].type=self.config['cloud'][instance.cloud_resource]['type']
                        self.__cluster.check_reservation(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                        if workernodes[0].state==WorkerNode.Idle or workernodes[0].state==WorkerNode.Busy:
                            workernodes[0].instance.state=Instance.Ready
                    else:
                        log.debug("instance %s is not a worker node in cluster, delete it"%instance.dns_name)
                        wn=WorkerNode(instance.dns_name)
                        wn.state=WorkerNode.Deleting
                        wn.state_start_time=time.time()
                        wn.instance=instance
                        wn.instance.last_update_time=time.time()
                        wn.num_proc=wn.instance.vcpu_number
                        wn.type=self.config['cloud'][instance.cloud_resource]['type']
                        self.info.worker_nodes.append(wn)
                        wn.instance.tasked=True
                        self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))                    
                elif instance.state==Instance.Starting:
                    wn=WorkerNode(instance.instance_name)
                    wn.state=WorkerNode.Starting
                    wn.state_start_time=time.time()
                    wn.instance=instance
                    wn.instance.last_update_time=time.time()
                    wn.num_proc=wn.instance.vcpu_number
                    wn.type=self.config['cloud'][instance.cloud_resource]['type']
                    self.info.worker_nodes.append(wn)
                elif instance.state!=Instance.Inexistent:
                    workernodes=[w for w in self.info.worker_nodes if w.hostname==instance.dns_name]
                    if len(workernodes)>0:
                        log.warn("instance %s is a worker node in cluster and it is in a funny state, need further checking."%instance.dns_name)
                        #if workernodes[0].state==Busy:
                        #    log.debug("instance %s is a worker node in cluster and it is running jobs, but it is dead in the cloud, let admin fix it."%instance.dns_name)
                        #else:
                        #    log.debug("instance %s is a worker node in cluster but it is not running any jobs and dead in the cloud, remove it"%instance.dns_name)
                        #    workernodes[0].instance=instance
                        #    workernodes[0].state=WorkerNode.Deleting
                        #    self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                    else:
                        log.debug("instance %s is not a worker node in cluster and it is dead in the cloud, remove it"%instance.dns_name)
                        wn=WorkerNode(instance.instance_name)
                        wn.state=WorkerNode.Deleting
                        wn.state_start_time=time.time()
                        wn.instance=instance
                        wn.instance.last_update_time=time.time()
                        wn.num_proc=wn.instance.vcpu_number
                        wn.type=self.config['cloud'][instance.cloud_resource]['type']
                        self.info.worker_nodes.append(wn)
                        wn.instance.tasked=True
                        self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))                    
            res.current_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name])

    def reset_interval(self):
        return int(self.config['dynamic-cluster']['cluster_poller_interval'])
    
    def run(self):
        log.debug("query thread started")
        interval=self.reset_interval()
        provision_interval=self.__auto_provision_interval
        while self.__running:
            try:
                result=self.__result_queue.get(block=False)
                log.debug("got a result: %s"%result)
                self.process_result(result)
            except Empty:
                pass
            time.sleep(1)
            #log.debug(interval)
            interval-=1
            provision_interval=-1
            if interval==0:
                #log.debug("__gather_cluster_info")
                self.__gather_cluster_info()
                interval=self.reset_interval()
                auto_provision_time=False
                if provision_interval<=0:
                    provision_interval=self.__auto_provision_interval
                    auto_provision_time=True
                self.check_existing_worker_nodes(auto_provision_time)
        log.debug("query thread ended")
        
    def get_worker_node_by_hostname(self, hostname):
        workernodes=[w for w in self.info.worker_nodes if w.hostname==hostname]
        if len(workernodes)==0:
            raise WorkerNodeNotFoundException()
        if len(workernodes)>1:
            raise DuplicatedWorkerNodeException()
        return workernodes[0]

    def get_worker_node_by_instance(self, instance):
        workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.instance_name==instance.instance_name]
        if len(workernodes)==0:
            log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
            return None
        return workernodes[0]
    
    def get_resource_by_name(self, resource_name):
        resources=[r for r in self.resources if r.name==resource_name]
        if len(resources)==0:
            raise CloudResourceNotFoundException()
        if len(resources)>1:
            raise DuplicatedCloudResourceException()
        return resources[0]
    
    def idle_for_too_long(self, worker_node):
        return worker_node.time_in_current_state>self.__max_idle_time or (worker_node.state_start_time>0 and time.time()-worker_node.state_start_time>self.__max_idle_time)

    def down_for_too_long(self, worker_node):
        return worker_node.time_in_current_state>self.__max_down_time or (worker_node.state_start_time>0 and time.time()-worker_node.state_start_time>self.__max_down_time)

    def is_provisioning(self):
        return len([w for w in self.info.worker_nodes if w.state==WorkerNode.Starting])>0
    
    def run_post_vm_destroy_command(self, worker_node):
        if "post_vm_destroy_command" in self.config['dynamic-cluster']:
            run_post_command(worker_node, self.config['dynamic-cluster']["post_vm_destroy_command"])
        
    def trigger(self, worker_node):
        """
        trigger actions according to the current worker node state
        """
        getattr(self, "on_"+WorkerNode.tostring(worker_node.state).lower())(worker_node)
        
    def transit(self, worker_node, state, task):
        """
        transit a state to another by a new task
        """
        worker_node.state=state
        worker_node.state_start_time=time.time()
        if task:
            worker_node.instance.tasked=True
            self.__task_queue.put(task)
        
    def new_task(self, worker_node, task):
        """
        create a new task
        """
        worker_node.instance.tasked=True
        self.__task_queue.put(task)

    def on_inexistent(self, worker_node):
        pass

    def on_starting(self, worker_node):
        if worker_node.instance.state==Instance.Active:
            worker_node.hostname=worker_node.instance.dns_name
            worker_node.num_proc=worker_node.instance.vcpu_number
        elif worker_node.instance.state==Instance.Inexistent:
            log.debug("instance %s is gone, remove it from the list" % worker_node.instance)
            self.info.worker_nodes.remove(worker_node)
            self.run_post_vm_destroy_command(worker_node)
            return
        elif worker_node.instance.state==Instance.Error:
            log.debug("instance %s is in error state, kill it" % worker_node.hostname)
            self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))  
            return
        if time.time()-worker_node.instance.last_update_time>self.__cloud_poller_interval:
            if worker_node.instance.state==Instance.Pending or worker_node.instance.state==Instance.Starting:
                log.debug("worker node %s is starting, and the cloud state is pending/starting, update its cloud state now." % worker_node.hostname)
                self.new_task(worker_node, Task(Task.UpdateCloudState, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
            elif worker_node.instance.state==Instance.Active:
                log.debug("worker node %s is starting, and it is active in cloud, check its configuration state." % worker_node.hostname)
                self.new_task(worker_node, Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": worker_node.instance}))
        elif time.time()-worker_node.instance.creation_time>self.__max_launch_time:
            log.debug("it takes too long for worker node %s to launch, kill it" % worker_node.hostname)
            self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))  
    
    def on_idle(self, worker_node):
        if worker_node.instance.state==Instance.Active:
            log.debug("worker node %s is idle, but it is active in cloud, check its configuration state." % worker_node.hostname)
            self.new_task(worker_node, Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": worker_node.instance}))
        if self.__auto and self.idle_for_too_long(worker_node):
            res=self.get_resource_by_name(worker_node.instance.cloud_resource)
            current_usable_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name and w.state in [WorkerNode.Idle, WorkerNode.Busy]])
            log.notice("update current_usable_num of res %s: %s" % (res.name,current_usable_num))
            if current_usable_num>res.min_num:
                log.debug("worker node %s has been idle for too long and the resource has more nodes than minimal requirement, hold it and delete it" % worker_node.hostname)
                self.transit(worker_node, WorkerNode.Holding, None)
                self.__cluster.hold_node(worker_node)
#                 if self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation']):
#                     self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": res, "instance": worker_node.instance}))
    
    def on_busy(self, worker_node):
        if worker_node.instance.state==Instance.Active:
            log.debug("worker node %s is busy, but it is active in cloud, check its configuration state." % worker_node.hostname)
            self.new_task(worker_node, Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": worker_node.instance}))
    
    def on_error(self, worker_node):
        if worker_node.instance.state==Instance.Inexistent:    
            log.debug("instance %s is gone, remove it"%worker_node.hostname)
            self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation'])
            self.info.worker_nodes.remove(worker_node)
            self.run_post_vm_destroy_command(worker_node)
#         elif worker_node.instance.state==Instance.Active or worker_node.instance.state==Instance.Ready:
#             ### Not sure about this, maybe it should rescue the worker node???
#             log.debug("instance %s is OK, check config status"%worker_node.hostname)
#             self.new_task(worker_node, Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": worker_node.instance}))
        elif self.__auto and self.down_for_too_long(worker_node):
            log.debug("worker node %s has been down for too long, delete it" % worker_node.hostname)
            if self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation']):
                if worker_node.jobs is None:
                    log.debug("instance %s has no jobs running, remove it"%worker_node.hostname)
                    self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
                else:
                    ## delete jobs??
                    log.error("instance %s is in error state but it has jobs running, need admin's attention"%worker_node.hostname)
            else:
                log.debug("unable to remove instance %s in the normal way, force delete"%worker_node.hostname)
                self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
            
    def on_deleting(self, worker_node):
        if worker_node.instance.state==Instance.Inexistent:
            log.debug("instance %s is gone, remove it"%worker_node.hostname)
            self.info.worker_nodes.remove(worker_node)
            self.run_post_vm_destroy_command(worker_node)
        elif worker_node.instance.state!=Instance.Deleting:
            log.debug("worker node %s is not deleting, delete it again." % worker_node.hostname)
            self.new_task(worker_node, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
        elif time.time()-worker_node.instance.last_update_time>self.__cloud_poller_interval:
            log.debug("worker node %s is deleting, update its state now." % worker_node.hostname)
            self.new_task(worker_node, Task(Task.UpdateCloudState, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
    
    def on_holding(self, worker_node):
        log.debug("trying to hold worker node %s" % worker_node.hostname)
    
    def on_held(self, worker_node):
        if not self.__auto:
            return
        if worker_node.jobs is not None and len(worker_node.jobs)>0:
            log.debug("worker node %s has running jobs, can't delete it now, need to wait for all jobs to finish" % worker_node.hostname)
            return
        res=self.get_resource_by_name(worker_node.instance.cloud_resource)
        current_usable_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name and w.state in [WorkerNode.Idle, WorkerNode.Busy]])
        log.debug("update current_usable_num of res %s: %s" % (res.name,current_usable_num))
        if current_usable_num+1>res.min_num:
            log.debug("held worker node %s and it has no running jobs, delete it" % worker_node.hostname)
            if self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation']):
                if "post_remove_node_command" in self.config['dynamic-cluster']:
                    run_post_command(worker_node, self.config['dynamic-cluster']["post_remove_node_command"])
                self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
    
    def process_result(self, result):
        if result.type==Result.Provision:
            if result.status==Result.Success:
                instances=result.data["instances"]
                for i in instances:
                    wn=WorkerNode(i.instance_name)
                    wn.state=WorkerNode.Starting
                    wn.state_start_time=time.time()
                    wn.instance=i
                    wn.instance.last_update_time=time.time()
                    wn.num_proc=wn.instance.vcpu_number
                    wn.type=self.config['cloud'][i.cloud_resource]['type']
                    self.info.worker_nodes.append(wn)
            else:
                log.debug("failed to start instances, try again later.")
        else:
            instance=result.data['instance']
            worker_node=self.get_worker_node_by_instance(instance)
            if worker_node is None:
                return
            instance.tasked=False
            instance.last_task_result=result.status
            previous_cloud_state=worker_node.instance.state
            worker_node.instance=instance
                 
            if result.type==Result.Destroy and result.status==Result.Success:
                worker_node.state=WorkerNode.Deleting
            elif result.type in [Result.UpdateCloudState, Result.UpdateConfigStatus] and result.status==Result.Success:
                self.trigger(worker_node)
                if worker_node.state==WorkerNode.Starting and previous_cloud_state!=Instance.Active and worker_node.instance.state==Instance.Active:
                    # run post-provision script here!
                    if "post_vm_provision_command" in self.config['dynamic-cluster']:
                        run_post_command(worker_node, self.config['dynamic-cluster']["post_vm_provision_command"])
                    self.__cluster.on_instance_active(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation'])
                elif worker_node.state==WorkerNode.Starting and worker_node.instance.state==Instance.Ready:
                    self.__cluster.on_instance_ready(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation'])
                
    def check_existing_worker_nodes(self, provision_time):
        for wn in self.info.worker_nodes:
            if wn.type.lower()=="physical" or wn.instance.tasked==True:
                continue
            self.trigger(wn)
        has_new_provision_task=False
        for res in self.resources:
            res.current_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name])
            if self.__auto and res.current_num<res.min_num and (not self.has_starting_worker_nodes(res.name)):
                log.debug("resource %s has less worker nodes than min value, launch more" % res.name)
                task=Task(Task.Provision, {"resource": res, "number": res.min_num-res.current_num})
                self.__task_queue.put(task)
                has_new_provision_task=True
        if self.__auto and not self.is_provisioning() and not has_new_provision_task and provision_time:
#             free_resources=[]
#             for res in self.resources:
#                 if not self.has_starting_worker_nodes(res.name):
#                     free_resources.append(res)
            try:
                tasks=self.__resource_allocator.allocate(self.info.queued_jobs, self.resources, self.info.worker_nodes)
                for task in tasks:
                    log.debug("tasks from resource allocator: %s"%task)
                    self.__task_queue.put(task)
            except:
                log.exception("Error allocating new resources to pending jobs")
                    
    def has_starting_worker_nodes(self, res_name):
        """
        check if there is any worker node in starting/configuring state
        """
        list=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.cloud_resource==res_name and w.state==WorkerNode.Starting]
        return len(list)>0

    def __gather_cluster_info(self):
        self.__cluster.update_worker_nodes(self.info.worker_nodes)
        self.info.queued_jobs, self.info.total_queued_job_number=self.__cluster.query_jobs()
        
    def set_auto(self):
        self.__auto=True

    def unset_auto(self):
        self.__auto=False
        
    def get_status(self):
        status={}
        status['auto_mode']=self.__auto
        status['cluster']=self.__cluster.state
        return status
    
    def get_queues(self):
        log.debug("queues: %s %s"%(self.__task_queue, self.__result_queue))
        return {'tasks': self.__task_queue.qsize(), 'results': self.__result_queue.qsize()}

    def launch_new_instance(self, resource_name, number):
        resource=self.get_resource_by_name(resource_name)
        current_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==resource.name])
        if number>resource.max_num-current_num:
            raise InsufficientResourceException()
        task=Task(Task.Provision, {"resource": resource, "number": number})
        self.__task_queue.put(task)
        
    def delete_worker_node(self, hostname):
        worker_node=self.get_worker_node_by_hostname(hostname)
        if worker_node.state==WorkerNode.Inexistent:
            return
        elif worker_node.state==WorkerNode.Busy or (worker_node.jobs is not None and len(worker_node.jobs)>0):
            raise WorkerNodeIsBusyException()
        elif worker_node.state==WorkerNode.Error or worker_node.state==WorkerNode.Starting:
            self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation'])
            if "post_remove_node_command" in self.config['dynamic-cluster']:
                run_post_command(worker_node, self.config['dynamic-cluster']["post_remove_node_command"])
            self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
        elif worker_node.state==WorkerNode.Held:
            if self.__cluster.remove_node(worker_node, self.config['cloud'][worker_node.instance.cloud_resource]['reservation']):
                if "post_remove_node_command" in self.config['dynamic-cluster']:
                    run_post_command(worker_node, self.config['dynamic-cluster']["post_remove_node_command"])
                self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": self.get_resource_by_name(worker_node.instance.cloud_resource), "instance": worker_node.instance}))
        else:
            log.debug("can't delete worker node in current state: %s"%worker_node)
            raise InvalidStateException()
        
    def hold_worker_node(self, hostname):
        worker_node=self.get_worker_node_by_hostname(hostname)
        if worker_node.state not in [WorkerNode.Idle, WorkerNode.Busy]:
            raise InvalidStateException()
        self.transit(worker_node, WorkerNode.Holding, None)
        self.__cluster.hold_node(worker_node)
        
    def unhold_worker_node(self, hostname):
        worker_node=self.get_worker_node_by_hostname(hostname)
        if worker_node.state!=WorkerNode.Held:
            raise InvalidStateException()
        self.__cluster.unhold_node(worker_node)
        
    def vacate_worker_node(self, hostname):
        worker_node=self.get_worker_node_by_hostname(hostname)
        self.__cluster.vacate_node(worker_node)
        self.__gather_cluster_info()
        
    def freeze_resource(self, resource_name):
        log.debug("freeze resource %s"%resource_name)
        resource=self.get_resource_by_name(resource_name)
        resource.min_num=resource.current_num
        resource.max_num=resource.current_num
        log.debug("frozen %s"%resource)
        
    def restore_resource(self, resource_name):
        resource=self.get_resource_by_name(resource_name)
        res_config=self.config['cloud'][resource_name]
        resource.min_num=res_config['quantity']['min']
        resource.max_num=res_config['quantity']['max']
        
    def drain_resource(self, resource_name):
        resource=self.get_resource_by_name(resource_name)
        resource.min_num=0
        resource.max_num=0
        workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.cloud_resource==resource_name]
        for worker_node in workernodes:
            if worker_node.state in [WorkerNode.Idle, WorkerNode.Busy]:
                self.transit(worker_node, WorkerNode.Holding, None)
                self.__cluster.hold_node(worker_node)
            elif worker_node.state==WorkerNode.Inexistent or (worker_node.jobs is not None and len(worker_node.jobs)>0):
                continue
            else:
                self.transit(worker_node, WorkerNode.Deleting, Task(Task.Destroy, {"resource": resource, "instance": worker_node.instance}))
                  