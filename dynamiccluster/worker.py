import multiprocessing
import signal
from dynamiccluster.utilities import getLogger
from Queue import Empty
from dynamiccluster.os_manager import OpenStackManager
from dynamiccluster.aws_manager import AWSManager
from dynamiccluster.config_checker import PortChecker

log = getLogger(__name__)

class Task(object):
    Quit, Provision, Destroy, UpdateCloudState, UpdateConfigStatus = range(5)
    def __init__(self, type, data={}):
        self.type=type
        self.data=data
        
    def __str__(self):
        return "Task: type: %s, data: %s"%(["Quit", "Provision", "Destroy", "UpdateCloudState", "UpdateConfigStatus"][self.type], self.data)
    
class Result(object):
    WorkerCrash, Provision, Destroy, UpdateCloudState, UpdateConfigStatus = range(5)
    Success, Failed = range(2)
    def __init__(self, type, status, data={}):
        self.type=type
        self.status=status
        self.data=data
    def __str__(self):
        return "Result: type: %s, status: %s, data: %s"%(["WorkerCrash", "Provision", "Destroy", "UpdateCloudState", "UpdateConfigStatus"][self.type], ["Success", "Failed"][self.status], self.data)
      
class Worker(multiprocessing.Process):
    def __init__(self, id, task_queue, result_queue):
        super(Worker, self).__init__()
        self.__id=id
        self.__task_queue=task_queue
        self.__result_queue=result_queue
        self.__running=True
        
    def run(self):
        #stop child process propagating signals to parent
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        log.debug("worker %s started"%self.__id)
        while self.__running:
            try:
                log.notice("worker %s waiting for task, %s"%(self.__id,self.__running))
                try:
                    task=self.__task_queue.get(timeout=1)
                    log.debug("got task %s"%task)
                    if task.type==Task.Provision:
                        cloud_manager=self.__get_cloud_manager(task.data['resource'])
                        instances=cloud_manager.boot(number=task.data['number'])
                        self.__result_queue.put(Result(Result.Provision, Result.Success, {'instances':instances}))
                    elif task.type==Task.UpdateCloudState:
                        cloud_manager=self.__get_cloud_manager(task.data['resource'])
                        instance=cloud_manager.update(instance=task.data['instance'])
                        self.__result_queue.put(Result(Result.UpdateCloudState, Result.Success, {'instance':instance}))
                    elif task.type==Task.UpdateConfigStatus:
                        checker=self.__get_config_checker(task.data['checker'])
                        self.__result_queue.put(Result(Result.UpdateConfigStatus, Result.Success, {'instance':task.data['instance'], "ready": checker.check(task.data['instance'].ip)}))
                    elif task.type==Task.Destroy:
                        cloud_manager=self.__get_cloud_manager(task.data['resource'])
                        cloud_manager.destroy(instance=task.data['instance'])
                        self.__result_queue.put(Result(Result.Destroy, Result.Success, {'instance':task.data['instance']}))
                    elif task.type==Task.Quit:
                        log.debug("got quit task, existing...")
                        break
                except Empty:
                    pass
                except Exception as e:
                    log.exception("task (%s) cannot be executed." % task)
                    self.__result_queue.put(Result(task.type, Result.Failed, task.data))
            except KeyboardInterrupt:
                    break
            except Exception as e:
                log.exception("worker %s caught unknown exception, report to parent"%self.__id)
                self.__result_queue.put(Result(Result.WorkerCrash, {'id':self.__id}))
                break
        log.debug("worker %s has quit"%self.__id)
    
    def __get_cloud_manager(self, resource):
        if resource.type.lower()=="openstack":
            return OpenStackManager(resource.name, resource.config)
        elif resource.type.lower()=="aws":
            return AWSManager(resource.name, resource.config)
        else:
            raise CloudNotSupportedException("Cloud type %s is not supported" % resource.type)
        
    def __get_config_checker(self, config):
        if config.keys()[0].lower()=="port":
            return PortChecker(port=config['port']['number'])
        else:
            raise ConfigCheckerNotSupportedException("Config checker %s is not supported" % config.keys()[0])
        
class CloudNotSupportedException(BaseException):
    pass

class ConfigCheckerNotSupportedException(BaseException):
    pass
