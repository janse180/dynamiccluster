import multiprocessing
import signal
from dynamiccluster.utilities import getLogger
from Queue import Empty
from dynamiccluster.cloud_manager import OpenStackManager, AWSManager 

log = getLogger(__name__)

class Task(object):
    Quit, Provision, Destroy, Update = range(4)
    def __init__(self, type, data={}):
        self.type=type
        self.data=data
        
    def __str__(self):
        return "type: %s, data: %s"%(["Quit", "Provision", "Destroy", "Update"][self.type], self.data)
    
class Result(object):
    WorkerCrash, Provision = range(2)
    def __init__(self, type, data={}):
        self.type=type
        self.data=data
      
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
                        self.run_provision_task(task)
                    if task.type==Task.Quit:
                        log.debug("got quit task, existing...")
                        break
                except Empty:
                    pass
                except Exception as e:
                    log.exception("task (%s) cannot be executed. type: %s, data: %s" % task)
            except KeyboardInterrupt:
                    break
            except Exception as e:
                log.exception("worker %s caught unknown exception, report to parent"%self.__id)
                self.__result_queue.put(Result(Result.WorkerCrash, {'id':self.__id}))
                break
        log.debug("worker %s has quit"%self.__id)
    
    def run_provision_task(self, task):
        cloud_manager=None
        if task.data['resource'].type.lower()=="openstack":
            cloud_manager=OpenStackManager(task.data['resource'].name, task.data['resource'].config)
        elif task.data['resource'].type.lower()=="aws":
            cloud_manager=AWSManager(task.data['resource'].name, task.data['resource'].config)
        else:
            raise CloudNotSupportedException("Cloud type %s is not supported" % task.data['resource'].type)
        instances=cloud_manager.boot(number=task.data['number'])
        self.__result_queue.put(Result(Result.Provision, {'instances':instances}))
        
class CloudNotSupportedException(BaseException):
    pass