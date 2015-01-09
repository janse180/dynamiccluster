import json
import time
import os, signal, sys
import admin_server
import yaml
from threading import Thread
from Queue import Empty
from multiprocessing import Process, Queue, cpu_count
from dynamiccluster.admin_server import AdminServer
import dynamiccluster.cluster_manager as cluster_manager
from dynamiccluster.utilities import getLogger, excepthook
from dynamiccluster.data import ClusterInfo
from dynamiccluster.data import CloudResource
from dynamiccluster.data import Instance
from dynamiccluster.worker import Worker
from dynamiccluster.worker import Task
from dynamiccluster.worker import Result
from dynamiccluster.data import WorkerNode
import dynamiccluster.__version__ as version
from dynamiccluster.cloud_manager import OpenStackManager, AWSManager
from dynamiccluster.hooks import run_post_vm_provision_command

log = getLogger(__name__)

class Server(object):
    def __init__(self, background=False, pidfile="", configfile=""):
        self.__background=background
        self.__pidfile=pidfile
        self.configfile=configfile
        self.__running=True
        stream = open(configfile, 'r')
        self.config = yaml.load(stream)
        log.debug(json.dumps(self.config, indent=2))
        self.info=ClusterInfo()
        self.__cluster=None
        self.__auto=True
        self.__task_queue=Queue()
        self.__result_queue=Queue()
        self.__workers=[]
        self.resources=[]
        
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
            if res.type.lower()=="openstack":
                cloud_manager=OpenStackManager(res.name, res.config, max_attempt_time=1)
                flavor_id=cloud_manager.get_flavor_id(res.config['flavor'])
                res.config['flavor_id']=flavor_id
        
    def query_and_process(self):
        log.debug("query thread started")
        interval=int(self.config['dynamic-cluster']['cluster_poller_interval'])
        while self.__running:
            try:
                result=self.__result_queue.get(timeout=1)
                log.debug("got a result: %s"%result)
                self.process_result(result)
            except Empty:
                pass
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
            workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.uuid==instance.uuid]
            if len(workernodes)==0:
                log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
                return
            instance.tasked=False
            instance.last_task_result=result.status
            workernodes[0].instance=instance
            if result.status==Result.Success:
                workernodes[0].instance.last_update_time=time.time()
                if workernodes[0].instance.state==Instance.Active:
                    workernodes[0].hostname=workernodes[0].instance.public_dns_name
                    workernodes[0].state=WorkerNode.Configuring
                    # run post-provision script here!
                    if "post_vm_provision_command" in self.config['dynamic-cluster']:
                        run_post_vm_provision_command(workernodes[0], self.config['dynamic-cluster']["post_vm_provision_command"])
                log.debug("updated workernode %s"%workernodes[0])
            else:
                log.debug("failed to update instance %s, try again later."%instance.uuid)
        elif result.type==Result.UpdateConfigStatus:
            instance=result.data['instance']
            workernodes=[w for w in self.info.worker_nodes if w.instance is not None and w.instance.uuid==instance.uuid]
            if len(workernodes)==0:
                log.error("instance %s is not in the current list. something is wrong" % instance.uuid)
                return
            workernodes[0].instance.tasked=False
            workernodes[0].instance.last_task_result=result.status
            if result.status==Result.Success:
                workernodes[0].instance.last_update_time=time.time()
                if result.data['ready']==True:
                    log.debug("workernode %s is ready, add it to cluster"%workernodes[0].hostname)
                    if self.__cluster.add_node_to_cluster(workernodes[0], self.config['cloud'][workernodes[0].instance.cloud_resource]['reservation']):
                        workernodes[0].state=WorkerNode.Idle
                        # run post add_node_command here!
                        if "post_add_node_command" in self.config['dynamic-cluster']:
                            run_post_add_node_command(workernodes[0], self.config['dynamic-cluster']["post_add_node_command"])
                    else:
                        # cannot add this node to cluster, delete it
                        pass
                    
    def check_existing_worker_nodes(self):
        for wn in self.info.worker_nodes:
            if wn.type.lower()=="physical" or wn.instance.tasked==True:
                continue
            if wn.state==WorkerNode.Starting:
                if wn.instance.state!=Instance.Active and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                    log.debug("worker node %s is starting, and the cloud is starting it, update its state now." % wn.hostname)
                    wn.instance.tasked=True
                    self.__task_queue.put(Task(Task.UpdateCloudState, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))
                if wn.instance.state==Instance.Active:
                    wn.hostname=wn.instance.public_dns_name
                    wn.state=WorkerNode.Configuring
                    log.debug("worker node %s is starting, and it is active in cloud, check its configuration state." % wn.hostname)
                    wn.instance.tasked=True
                    self.__task_queue.put(Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": wn.instance}))
            if wn.state==WorkerNode.Configuring and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                log.debug("worker node %s is configuring, and it is active in cloud, check its configuration state again." % wn.hostname)
                wn.instance.tasked=True
                self.__task_queue.put(Task(Task.UpdateConfigStatus, {"checker": self.config['dynamic-cluster']['config-checker'], "instance": wn.instance}))
            if wn.state==WorkerNode.Deleting and time.time()-wn.instance.last_update_time>self.config['dynamic-cluster']['cloud_poller_interval']:
                log.debug("worker node %s is deleting, update its state now." % wn.hostname)
                wn.instance.tasked=True
                self.__task_queue.put(Task(Task.UpdateCloudState, {"resource": [r for r in self.resources if r.name==wn.instance.cloud_resource][0], "instance": wn.instance}))
                
        
    def start(self):
        log.info("Starting Dynamic Cluster v" + version.version)
        
        # Install signal handlers
        signal.signal(signal.SIGTERM, self.__sigTERMhandler)
        signal.signal(signal.SIGINT, self.__sigTERMhandler)
        # Ensure unhandled exceptions are logged
        sys.excepthook = excepthook
        
        if self.config['cluster']['type'].lower()=="torque":
            self.__cluster=cluster_manager.TorqueManager(self.config['cluster']['config'])
        elif self.config['cluster']['type'].lower()=="sge":
            self.__cluster=cluster_manager.SGEManager(self.config['cluster']['config'])
        else:
            raise NoClusterDefinedException()
        
        self.__gather_cluster_info()
        self.__init_resources()
        
        adminServer=AdminServer(self)
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

        
        # First set the mask to only allow access to owner
        os.umask(0077)
        if self.__background: # pragma: no cover
            log.info("Starting in daemon mode")
            ret = self.__createDaemon()
            if ret:
                log.info("Daemon started")
            else:
                log.error("Could not create daemon")
                raise ServerInitializationError("Could not create daemon")
        
            # Creates a PID file.
            if len(self.__pidfile)>0:
                try:
                    log.debug("Creating PID file %s" % self.__pidfile)
                    pidFile = open(self.__pidfile, 'w')
                    pidFile.write("%s\n" % os.getpid())
                    pidFile.close()
                except IOError, e:
                    log.error("Unable to create PID file: %s" % e)
            self.query_and_process()
        else:
            main_thread=Thread(target=self.query_and_process, name="QueryThread")
            main_thread.daemon = True
            main_thread.start()
        
        for w in self.__workers:
            w.join()
            
        if self.__background:
            log.debug("joining main thread")
            main_thread.join()
             # Removes the PID file.
            try:
                log.debug("Remove PID file %s" % self.__pidfile)
                os.remove(self.__pidfile)
            except OSError, e:
                log.error("Unable to remove PID file: %s" % e)

        log.info("Dynamic Cluster has stopped")
             
    def quit(self):
        for i in xrange(len(self.__workers)):
            log.debug("send Quit to shut down child process")
            self.__task_queue.put(Task(Task.Quit))
        self.__running=False
        log.debug("Waiting for Dynamic Cluster to exit ...")
            
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

    def __createDaemon(self): # pragma: no cover
        """ Detach a process from the controlling terminal and run it in the
            background as a daemon.
        
            http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/278731
        """
    
        # When the first child terminates, all processes in the second child
        # are sent a SIGHUP, so it's ignored.

        # We need to set this in the parent process, so it gets inherited by the
        # child process, and this makes sure that it is effect even if the parent
        # terminates quickly.
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        
        try:
            # Fork a child process so the parent can exit.  This will return control
            # to the command line or shell.  This is required so that the new process
            # is guaranteed not to be a process group leader.  We have this guarantee
            # because the process GID of the parent is inherited by the child, but
            # the child gets a new PID, making it impossible for its PID to equal its
            # PGID.
            pid = os.fork()
        except OSError, e:
            return((e.errno, e.strerror))     # ERROR (return a tuple)
        
        if pid == 0:       # The first child.
    
            # Next we call os.setsid() to become the session leader of this new
            # session.  The process also becomes the process group leader of the
            # new process group.  Since a controlling terminal is associated with a
            # session, and this new session has not yet acquired a controlling
            # terminal our process now has no controlling terminal.  This shouldn't
            # fail, since we're guaranteed that the child is not a process group
            # leader.
            os.setsid()
        
            try:
                # Fork a second child to prevent zombies.  Since the first child is
                # a session leader without a controlling terminal, it's possible for
                # it to acquire one by opening a terminal in the future.  This second
                # fork guarantees that the child is no longer a session leader, thus
                # preventing the daemon from ever acquiring a controlling terminal.
                pid = os.fork()        # Fork a second child.
            except OSError, e:
                return((e.errno, e.strerror))  # ERROR (return a tuple)
        
            if (pid == 0):      # The second child.
                # Ensure that the daemon doesn't keep any directory in use.  Failure
                # to do this could make a filesystem unmountable.
                os.chdir("/")
            else:
                os._exit(0)      # Exit parent (the first child) of the second child.
        else:
            os._exit(0)         # Exit parent of the first child.
        
        # Close all open files.  Try the system configuration variable, SC_OPEN_MAX,
        # for the maximum number of open files to close.  If it doesn't exist, use
        # the default value (configurable).
        try:
            maxfd = os.sysconf("SC_OPEN_MAX")
        except (AttributeError, ValueError):
            maxfd = 256       # default maximum
    
        # urandom should not be closed in Python 3.4.0. Fixed in 3.4.1
        # http://bugs.python.org/issue21207
        if sys.version_info[0:3] == (3, 4, 0): # pragma: no cover
            urandom_fd = os.open("/dev/urandom", os.O_RDONLY)
            for fd in range(0, maxfd):
                try:
                    if not os.path.sameopenfile(urandom_fd, fd):
                        os.close(fd)
                except OSError:   # ERROR (ignore)
                    pass
            os.close(urandom_fd)
        else:
            os.closerange(0, maxfd)
    
        # Redirect the standard file descriptors to /dev/null.
        os.open("/dev/null", os.O_RDONLY)    # standard input (0)
        os.open("/dev/null", os.O_RDWR)        # standard output (1)
        os.open("/dev/null", os.O_RDWR)        # standard error (2)
        return True


class NoClusterDefinedException(BaseException):
    pass

class ServerInitializationError(BaseException):
    pass

class NoCloudResourceException(BaseException):
    pass