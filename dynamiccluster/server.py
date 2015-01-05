import json
import time
import admin_server
import yaml
from dynamiccluster.admin_server import AdminServer
import dynamiccluster.cluster_manager as cluster_manager
from dynamiccluster.utilities import getLogger
from dynamiccluster.data import ClusterInfo

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
        self.__info=ClusterInfo()
        self.__cluster=None
        
    def init(self):
        if self.__config['cluster']['type'].lower()=="torque":
            self.__cluster=cluster_manager.TorqueManager(self.__config['cluster']['config'])
        elif self.__config['cluster']['type'].lower()=="sge":
            self.__cluster=cluster_manager.SGEManager(self.__config['cluster']['config'])
        else:
            raise NoClusterDefinedException()
        
        self.__gather_cluster_info()
        adminServer=AdminServer(self.__config['dynamic-cluster']['admin-server']['port'], self.__info)
        adminServer.daemon = True
        adminServer.start()
    
    def start(self):
        while self.__running:
            time.sleep(int(self.__config['dynamic-cluster']['cluster_poller_interval']))
            self.__gather_cluster_info()           
             
    def quit(self):
        self.__running=False
        
    def __gather_cluster_info(self):
        self.__cluster.update_worker_nodes(self.__info.worker_nodes)
        self.__info.queued_jobs, self.__info.total_queued_job_number=self.__cluster.query_jobs()

class NoClusterDefinedException(BaseException):
    pass

