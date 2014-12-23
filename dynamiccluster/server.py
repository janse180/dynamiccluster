import json
import time
import admin_server
import yaml
from dynamiccluster.admin_server import AdminServer
import dynamiccluster.cluster_manager as cluster_manager
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

class Server(object):
    def __init__(self, background=False, pidfile="", configfile=""):
        self.__background=background
        self.__pidfile=pidfile
        self.__configfile=configfile
        self.__running=True
        stream = open(configfile, 'r')
        self.__config = yaml.load(stream)
        log.debug(json.dumps(self.__config, indent=2))
        self.__info={"worker_nodes":[], "queued_jobs":[], "total_queued_job_number": 0}
        
    def init(self):
        cluster=None
        if self.__config['cluster']['type'].lower()=="torque":
            cluster=cluster_manager.TorqueManager(self.__config['cluster']['config'])
        elif self.__config['cluster']['type'].lower()=="sge":
            cluster=cluster_manager.SGEManager(self.__config['cluster']['config'])
        else:
            raise NoClusterDefinedException()
        
        cluster.update_worker_nodes(self.__info["worker_nodes"])
        self.__info["queued_jobs"], self.__info["total_queued_job_number"]=cluster.query_jobs()
        
        adminServer=AdminServer(self.__config['dynamic-cluster']['admin-server']['port'], self.__info)
        adminServer.daemon = True
        adminServer.start()
    
    def start(self):
        while self.__running:
            log.debug("hello")
            time.sleep(10)
            
    def quit(self):
        self.__running=False

class NoClusterDefinedException(BaseException):
    pass

class WorkerNode(object):
    Inexistent, Starting, Idle, Busy, Error, Deleting = range(6)
    def __init__(self, hostname):
        self.__hostname=hostname
        self.__jobs=None
        self.__state=Inexistent
        self.__num_proc=0
        self.__extra_attributes=None
        
class Job(object):
    Queued, Running, Other = range(3)
    def __init__(self, jobid):
        self.__jobid=jobid
        self.__priority=-1
        self.__name=None
        self.__owner=None
        self.__state=None
        self.__queue=None
        self.__requested_proc=None
        self.__requested_mem=None
        self.__requested_walltime=0
        self.__creation_time=0
        self.__extra_attributes=None
