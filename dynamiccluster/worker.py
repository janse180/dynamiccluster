import multiprocessing
import signal
from dynamiccluster.utilities import getLogger
from Queue import Empty

log = getLogger(__name__)

class Task(object):
    Quit, Provision, Destroy, Update = range(4)
    def __init__(self, type):
        self.type=type
    
class Result(object):
    WorkerCrash, Success = range(2)
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
                    if task.type==Task.Quit:
                        log.debug("got quit task, existing...")
                        break
                except Empty:
                    pass
            except KeyboardInterrupt:
                    break
            except Exception as e:
                log.exception("worker %s caught unknown exception, report to parent"%self.__id)
                self.__result_queue.put(Result(Result.WorkerCrash, {'id':self.__id}))
                break
        log.debug("worker %s has quit"%self.__id)