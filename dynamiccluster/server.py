import json
import time
import os, signal, sys
import admin_server
import yaml
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
from dynamiccluster.exceptions import NoClusterDefinedException, ServerInitializationError, NoCloudResourceException, WorkerNodeNotFoundException
from dynamiccluster.resource_allocator import ResourceAllocator
import logging

log = getLogger(__name__)

class Server(Daemon):
    def __init__(self, pidfile="", configfile="", working_path="/", stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        Daemon.__init__(self, pidfile, stdin, stdout, stderr)
        self.__pidfile=pidfile
        self.configfile=configfile
        self.__working_path=working_path
        self.__running=True
        stream = open(configfile, 'r')
        self.config = yaml.load(stream)
        self.info=ClusterInfo()
        self.__cluster=None
        self.__auto=True
        self.__task_queue=Queue()
        self.__result_queue=Queue()
        self.__workers=[]
        self.__plugin_objects=[]
        self.resources=[]
        self.__resource_allocator=None
        
    def __sigTERMhandler(self, signum, frame):
        log.debug("Caught signal %d. Exiting" % signum)
        self.quit()
        
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
                    workernodes=[w for w in self.info.worker_nodes if w.hostname==instance.public_dns_name]
                    if len(workernodes)>0:
                        log.debug("instance %s is a worker node in cluster"%instance.public_dns_name)
                        workernodes[0].instance=instance
                        workernodes[0].type=self.config['cloud'][instance.cloud_resource]['type']
                        if workernodes[0].state==WorkerNode.Idle or workernodes[0].state==WorkerNode.Busy:
                            workernodes[0].instance.state=Instance.Configured
                    else:
                        log.debug("instance %s is not a worker node in cluster, delete it"%instance.public_dns_name)
                        wn=WorkerNode(instance.public_dns_name)
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
                    workernodes=[w for w in self.info.worker_nodes if w.hostname==instance.public_dns_name]
                    if len(workernodes)>0:
                        log.debug("instance %s is a worker node in cluster and it is in a funny state, need further checking."%instance.public_dns_name)
                        #if workernodes[0].state==Busy:
                        #    log.debug("instance %s is a worker node in cluster and it is running jobs, but it is dead in the cloud, let admin fix it."%instance.public_dns_name)
                        #else:
                        #    log.debug("instance %s is a worker node in cluster but it is not running any jobs and dead in the cloud, remove it"%instance.public_dns_name)
                        #    workernodes[0].instance=instance
                        #    workernodes[0].state=WorkerNode.Deleting
                        #    self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                    else:
                        log.debug("instance %s is not a worker node in cluster and it is dead in the cloud, remove it"%instance.public_dns_name)
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

        
    def query_and_process(self):
        log.debug("query thread started")
        interval=int(self.config['dynamic-cluster']['cluster_poller_interval'])
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
            if interval==0:
                #log.debug("__gather_cluster_info")
                self.__gather_cluster_info()
                interval=int(self.config['dynamic-cluster']['cluster_poller_interval'])
                self.check_existing_worker_nodes()
        
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
        elif result.type==Result.UpdateCloudState:
            instance=result.data['instance']
            workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.instance_name==instance.instance_name]
            if len(workernodes)==0:
                log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
                return
            instance.tasked=False
            instance.last_task_result=result.status
            workernodes[0].instance=instance
            if result.status==Result.Success:
                workernodes[0].instance.last_update_time=time.time()
                if workernodes[0].state==WorkerNode.Starting:
                    if workernodes[0].instance.state==Instance.Active:
                        workernodes[0].hostname=workernodes[0].instance.public_dns_name
                        workernodes[0].num_proc=workernodes[0].instance.vcpu_number
                        workernodes[0].state=WorkerNode.Configuring
                        workernodes[0].state_start_time=time.time()
                        # run post-provision script here!
                        if "post_vm_provision_command" in self.config['dynamic-cluster']:
                            run_post_command(workernodes[0], self.config['dynamic-cluster']["post_vm_provision_command"])
                        if self.config['cluster']['type']=="sge":
                            log.debug("workernode %s is provisioned, add it to cluster"%workernodes[0].hostname)
                            if self.__cluster.add_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation']):
                                #workernodes[0].state=WorkerNode.Idle
                                #workernodes[0].state_start_time=time.time()
                                # run post add_node_command here!
                                if "post_add_node_command" in self.config['dynamic-cluster']:
                                    run_post_command(workernodes[0], self.config['dynamic-cluster']["post_add_node_command"])
                            else:
                                log.debug("cannot add node %s to cluster, delete it"%workernodes[0].hostname)
                                self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                                workernodes[0].state=WorkerNode.Deleting
                                workernodes[0].state_start_time=time.time()
                    elif workernodes[0].instance.state==Instance.Starting and time.time()-workernodes[0].instance.creation_time>self.config['dynamic-cluster']['max_launch_time']:
                        log.debug("it takes too long for worker node %s to launch, kill it"%workernodes[0].hostname)
                        workernodes[0].instance.tasked=True
                        self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==workernodes[0].instance.cloud_resource][0], "instance": workernodes[0].instance}))  
                    elif workernodes[0].instance.state==Instance.Inexistent:
                        log.debug("instance %s is gone, remove it from the list" % instance)
                        self.info.worker_nodes.remove(workernodes[0])
                        if "post_vm_provision_command" in self.config['dynamic-cluster']:
                            run_post_command(workernodes[0], self.config['dynamic-cluster']["post_vm_provision_command"])
                elif workernodes[0].state==WorkerNode.Error:
                    if workernodes[0].instance.state==Instance.Active:
                        log.debug("instance %s is OK, check config status"%workernodes[0].hostname)
                        workernodes[0].instance.tasked=True
                        self.__task_queue.put(Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": workernodes[0].instance}))
                    elif workernodes[0].instance.state==Instance.Error:
                        log.debug("instance %s is not OK..."%workernodes[0].hostname)
                        self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                        if workernodes[0].jobs is None:
                            log.debug("instance %s has no jobs running, remove it"%workernodes[0].hostname)
                            workernodes[0].state=WorkerNode.Deleting
                            self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==workernodes[0].instance.cloud_resource][0], "instance": workernodes[0].instance}))                    
                            workernodes[0].state_start_time=time.time()
                        else:
                            log.debug("instance %s has jobs running, need admin's attention"%workernodes[0].hostname)
                            #send an alert to admin here
                    elif workernodes[0].instance.state==Instance.Error or workernodes[0].instance.state==Instance.Inexistent:    
                        log.debug("instance %s is gone, remove it"%workernodes[0].hostname)
                        self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                        self.info.worker_nodes.remove(workernodes[0])
                        if "post_vm_destroy_command" in self.config['dynamic-cluster']:
                            run_post_command(workernodes[0], self.config['dynamic-cluster']["post_vm_destroy_command"])
                elif workernodes[0].state==WorkerNode.Deleting and workernodes[0].instance.state==Instance.Inexistent:
                    log.debug("instance %s is gone, remove it"%workernodes[0].hostname)
                    self.info.worker_nodes.remove(workernodes[0])
                    if "post_vm_destroy_command" in self.config['dynamic-cluster']:
                        run_post_command(workernodes[0], self.config['dynamic-cluster']["post_vm_destroy_command"])
                log.debug("updated workernode %s"%workernodes[0])
            else:
                log.debug("failed to update cloud state for instance %s, try again later."%instance.uuid)
        elif result.type==Result.UpdateConfigStatus:
            instance=result.data['instance']
            workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.instance_name==instance.instance_name]
            if len(workernodes)==0:
                log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
                return
            workernodes[0].instance=instance
            workernodes[0].instance.tasked=False
            workernodes[0].instance.last_task_result=result.status
            if result.status==Result.Success:
                workernodes[0].instance.last_update_time=time.time()
                if workernodes[0].state==WorkerNode.Configuring:
                    if workernodes[0].instance.state==Instance.Configured:
                        if self.config['cluster']['type']=="torque":
                            log.debug("workernode %s is ready, add it to cluster"%workernodes[0].hostname)
                            if self.__cluster.add_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation']):
                                # run post add_node_command here!
                                if "post_add_node_command" in self.config['dynamic-cluster']:
                                    run_post_command(workernodes[0], self.config['dynamic-cluster']["post_add_node_command"])
                            else:
                                log.debug("cannot add node %s to cluster, delete it"%workernodes[0].hostname)
                                self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
                        else:
                            workernodes[0].state=WorkerNode.Idle
                            workernodes[0].state_start_time=time.time()
                    elif time.time()-workernodes[0].instance.creation_time>self.config['dynamic-cluster']['max_launch_time']:
                        log.debug("it takes too long for worker node %s to launch, kill it")
                        workernodes[0].instance.tasked=True
                        self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==workernodes[0].instance.cloud_resource][0], "instance": workernodes[0].instance}))                    
                elif workernodes[0].state==WorkerNode.Error:
                    log.debug("worker node is fine, it will be changed back to normal state")
            else:
                log.debug("failed to update config status for instance %s, try again later."%instance.uuid)
        elif result.type==Result.Destroy:
            instance=result.data['instance']
            workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.instance_name==instance.instance_name]
            if len(workernodes)==0:
                log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
                return
            workernodes[0].instance.tasked=False
            workernodes[0].instance.last_task_result=result.status
            if result.status==Result.Success:
                workernodes[0].instance.last_update_time=time.time()
                workernodes[0].state=WorkerNode.Deleting
                    
    def check_existing_worker_nodes(self):
        for wn in self.info.worker_nodes:
            if wn.type.lower()=="physical" or wn.instance.tasked==True:
                continue
            if wn.state==WorkerNode.Starting:
                if wn.instance.state!=Instance.Active and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                    log.debug("worker node %s is starting, and the cloud is starting it, update its state now." % wn.hostname)
                    wn.instance.tasked=True
                    self.__task_queue.put(Task(Task.UpdateCloudState, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))
                elif wn.instance.state==Instance.Active:
                    wn.hostname=wn.instance.public_dns_name
                    wn.state=WorkerNode.Configuring
                    wn.state_start_time=time.time()
                    log.debug("worker node %s is starting, and it is active in cloud, check its configuration state." % wn.hostname)
                    wn.instance.tasked=True
                    self.__task_queue.put(Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": wn.instance}))
            elif wn.state==WorkerNode.Configuring and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                log.debug("worker node %s is configuring, and it is active in cloud, check its configuration state again." % wn.hostname)
                wn.instance.tasked=True
                self.__task_queue.put(Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": wn.instance}))
            elif wn.state==WorkerNode.Deleting and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                log.debug("worker node %s is deleting, update its state now." % wn.hostname)
                wn.instance.tasked=True
                self.__task_queue.put(Task(Task.UpdateCloudState, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))
            elif wn.state==WorkerNode.Holding:
                log.debug("trying to hold worker node %s, wait for its jobs to finish" % wn.hostname)
            elif wn.state==WorkerNode.Held:
                log.debug("held worker node %s, delete it" % wn.hostname)
                self.__cluster.remove_node(wn, self.config['cloud'][wn.instance.cloud_resource]['reservation'])
                if "post_remove_node_command" in self.config['dynamic-cluster']:
                    run_post_command(workernodes[0], self.config['dynamic-cluster']["post_remove_node_command"])
                wn.instance.tasked=True
                wn.state=WorkerNode.Deleting
                wn.state_start_time=time.time()
                self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))                    
            elif wn.state==WorkerNode.Idle and (wn.time_in_current_state>self.config['dynamic-cluster']['max_idle_time'] or (wn.state_start_time>0 and time.time()-wn.state_start_time>self.config['dynamic-cluster']['max_idle_time'])):
                res=[r for r in self.resources if r.name==wn.instance.cloud_resource]
                if len(res)==0:
                    log.error("cannot find resource %s"%wn.instance.cloud_resource)
                    return
                current_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res[0].name and w.state not in [WorkerNode.Deleting, WorkerNode.Holding, WorkerNode.Held, WorkerNode.Starting, WorkerNode.Configuring]])
                log.notice("update current_num of res %s: %s" % (res[0].name,current_num))
                if current_num>res[0].min_num:
                    log.debug("worker node %s has been idle for too long and the resource has more nodes than minimal requirement, delete it" % wn.hostname)
                    self.__cluster.remove_node(wn, self.config['cloud'][wn.instance.cloud_resource]['reservation'])
                    wn.instance.tasked=True
                    wn.state=WorkerNode.Deleting
                    wn.state_start_time=time.time()
                    self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))                    
            elif wn.state==WorkerNode.Error and (wn.time_in_current_state>self.config['dynamic-cluster']['max_down_time'] or (wn.state_start_time>0 and time.time()-wn.state_start_time>self.config['dynamic-cluster']['max_down_time'])):
                log.debug("worker node %s has been down for too long, delete it" % wn.hostname)
                self.__cluster.remove_node(wn, self.config['cloud'][wn.instance.cloud_resource]['reservation'])
                wn.instance.tasked=True
                wn.state=WorkerNode.Deleting
                wn.state_start_time=time.time()
                self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))                    
        for res in self.resources:
            res.current_num=len([w for w in self.info.worker_nodes if w.instance and w.instance.cloud_resource==res.name])
            if self.__auto and res.current_num<res.min_num and (not self.has_starting_worker_nodes(res.name)):
                log.debug("resource %s has less worker nodes than min value, launch more" % res.name)
                task=Task(Task.Provision, {"resource": res, "number": res.min_num-res.current_num})
                self.__task_queue.put(task)
        if self.__auto:
            free_resources=[]
            for res in self.resources:
                if not self.has_starting_worker_nodes(res.name):
                    free_resources.append(res)
            try:
                tasks=self.__resource_allocator.allocate(self.info.queued_jobs, free_resources, self.info.worker_nodes)
                for task in tasks:
                    log.debug("tasks from resource allocator: %s"%task)
                    self.__task_queue.put(task)
            except:
                log.exception("Error allocating new resources to pending jobs")
                    
    def has_starting_worker_nodes(self, res_name):
        """
        check if there is any worker node in starting/configuring state
        """
        list=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.cloud_resource==res_name and (w.state==WorkerNode.Starting or w.state==WorkerNode.Configuring)]
        return len(list)>0
        
    def init(self, run_in_background, verbose):
        if run_in_background and 'logging' in self.config:
            if 'log_level' in self.config['logging']:
                log.setLevel(get_log_level(self.config['logging']['log_level']))
            log_formatter = logging.Formatter(self.config['logging']['log_format'])
            file_handler = None
            if 'log_max_size' in self.config['logging']:
                file_handler = logging.handlers.RotatingFileHandler(
                                                self.config['logging']['log_location'],
                                                maxBytes=self.config['logging']['log_max_size'],
                                                backupCount=3)
            else:
                try:
                    file_handler = logging.handlers.WatchedFileHandler(
                                                self.config['logging']['log_location'],)
                except AttributeError:
                    # Python 2.5 doesn't support WatchedFileHandler
                    file_handler = logging.handlers.RotatingFileHandler(
                                                self.config['logging']['log_location'],)
    
            file_handler.setFormatter(log_formatter)
            log.addHandler(file_handler)
        if verbose>0:
            log.setLevel(get_log_level(verbose))
        log.debug(json.dumps(self.config, indent=2))
        if self.config['cluster']['type'].lower()=="torque":
            self.__cluster=cluster_manager.TorqueManager(self.config['cluster']['config'])
        elif self.config['cluster']['type'].lower()=="sge":
            self.__cluster=cluster_manager.SGEManager(self.config['cluster']['config'])
        else:
            raise NoClusterDefinedException()
        
        self.__gather_cluster_info()
        self.__init_resources()
        self.__resource_allocator=ResourceAllocator()
    
    def run(self):
        log.info("Starting Dynamic Cluster v" + version.version)
        
        # Install signal handlers
        signal.signal(signal.SIGTERM, self.__sigTERMhandler)
        signal.signal(signal.SIGINT, self.__sigTERMhandler)
        # Ensure unhandled exceptions are logged
        sys.excepthook = excepthook

        log.debug("self.__working_path %s"%self.__working_path)
        adminServer=AdminServer(self, self.__working_path)
        adminServer.daemon = True
        adminServer.start()
        
        worker_num=1
        if "worker_number" in self.config['dynamic-cluster']:
            worker_num=int(self.config['dynamic-cluster']['worker_number'])
        else:
            cpu_num=cpu_count()
            if cpu_num>1:
                worker_num=cpu_num-1
        for i in xrange(worker_num):
            p=Worker(i, self.__task_queue, self.__result_queue)
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
                arguments=plugin['arguments']
                arguments['_info']=self.info
                self.__plugin_objects.append(init_object(class_name, **arguments))
        for plugin_obj in self.__plugin_objects:
            plugin_obj.daemon=True
            plugin_obj.start()
        
        self.query_and_process()
            
        log.info("Dynamic Cluster has stopped")
             
    def quit(self):
        for i in xrange(len(self.__workers)):
            log.debug("send Quit to shut down child process")
            self.__task_queue.put(Task(Task.Quit))
        for plugin_obj in self.__plugin_objects:
            plugin_obj.stop()
        self.__running=False
        log.debug("Waiting for Dynamic Cluster to exit ...")
        for plugin_obj in self.__plugin_objects:
            plugin_obj.join()
        for w in self.__workers:
            w.join()
            
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

    def launch_new_instance(self, resource, number):
        resources=[r for r in self.resources if r.name==resource]
        if len(resources)<1:
            raise NoCloudResourceException()
        task=Task(Task.Provision, {"resource": resources[0], "number": number})
        self.__task_queue.put(task)
        
    def delete_worker_node(self, hostname, forced=False):
        workernodes=[w for w in self.info.worker_nodes if w.hostname==hostname]
        if len(workernodes)==0:
            raise WorkerNodeNotFoundException()
        if workernodes[0].state==WorkerNode.Busy and not forced:
            raise WorkerNodeIsBusyException()
        elif workernodes[0].state==WorkerNode.Error:
            self.__cluster.remove_node(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation'])
            workernodes[0].instance.tasked=True
            workernodes[0].state=WorkerNode.Deleting
            self.__task_queue.put(Task(Task.Destroy, {"resource": [r for r in self.resources if r.name==workernodes[0].instance.cloud_resource][0], "instance": workernodes[0].instance}))                    
        elif (workernodes[0].state==WorkerNode.Busy and forced) or workernodes[0].state!=WorkerNode.Busy:
            self.__cluster.hold_node(workernodes[0])
            workernodes[0].state=WorkerNode.Holding

