import json
import time
import os, signal, sys
import admin_server
import yaml
from threading import Thread
from multiprocessing import Process, Queue, cpu_count
from dynamiccluster.admin_server import AdminServer
import dynamiccluster.cluster_manager as cluster_manager
from dynamiccluster.utilities import getLogger, excepthook
from dynamiccluster.data import ClusterInfo
from dynamiccluster.worker import Worker
from dynamiccluster.worker import Task
import dynamiccluster.__version__ as version

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
        self.__sleep=False
        self.__task_queue=Queue()
        self.__result_queue=Queue()
        self.__workers=[]
        
    def __sigTERMhandler(self, signum, frame):
        log.debug("Caught signal %d. Exiting" % signum)
        self.quit()
        
    def query_and_process(self):
        log.debug("query thread started")
        interval=int(self.config['dynamic-cluster']['cluster_poller_interval'])
        while self.__running:
            time.sleep(1)
            #log.debug(interval)
            interval-=1
            if interval==0:
                #log.debug("__gather_cluster_info")
                self.__gather_cluster_info()
                interval=int(self.config['dynamic-cluster']['cluster_poller_interval'])
                if not self.__sleep:
                    tasks=self.check_existing_worker_nodes()
                    if len(tasks)>0:
                        for t in tasks:
                            self.__task_queue.put(t)
        
    def check_existing_worker_nodes(self):
        tasks=[]
        for wn in self.info.worker_nodes:
            if wn.type=="Physical":
                continue
        return tasks
        
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
        
    def set_sleep(self):
        self.__sleep=True

    def unset_sleep(self):
        self.__sleep=False
        
    def get_status(self):
        status={}
        status['sleep']=self.__sleep
        status['cluster']=self.__cluster.state
        return status


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