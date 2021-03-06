"""
Worker thread that runs tasks
"""
import threading
import time
import sys
import errno
import copy
from dynamiccluster.utilities import getLogger, init_object, excepthook
from Queue import Empty
from dynamiccluster.os_manager import OpenStackManager
from dynamiccluster.aws_manager import AWSManager
from dynamiccluster.config_checker import PortChecker
from dynamiccluster.exceptions import CloudNotSupportedException, ConfigCheckerNotSupportedException

log = getLogger(__name__)

class Task(object):
    Quit, Provision, Destroy, UpdateCloudState, UpdateConfigStatus, Unknown = range(6)
    def __init__(self, type, data={}):
        self.type=type
        self.data=data
        
    def __str__(self):
        instance=""
        if 'instance' in self.data:
            instance="%s %s %s" % (self.data['instance'].uuid, self.data['instance'].instance_name, self.data['instance'].ip)
        return "Task: type: %s, instance: %s"%(["Quit", "Provision", "Destroy", "UpdateCloudState", "UpdateConfigStatus"][self.type], instance)
    
class Result(object):
    WorkerCrash, Provision, Destroy, UpdateCloudState, UpdateConfigStatus = range(5)
    Success, Failed = range(2)
    def __init__(self, type, status, data={}):
        self.type=type
        self.status=status
        self.data=data
    def __str__(self):
        return "Result: type: %s, status: %s, data: %s"%(["WorkerCrash", "Provision", "Destroy", "UpdateCloudState", "UpdateConfigStatus"][self.type], ["Success", "Failed"][self.status], self.data)
      
class Worker(threading.Thread):
    """
    worker thread, get a task, do the job, and return result
    """
    def __init__(self, id, task_queue, result_queue):
        threading.Thread.__init__(self, name="Worker %s"%id)
        self.id=id
        self.__task_queue=task_queue
        self.__result_queue=result_queue
        self.__running=True
        
    def quit(self):
        self.__running=False

    def run(self):
        log.info("worker %s started"%self.id)
        while self.__running:
            try:
                log.notice("worker %s waiting for task, is running? %s, queue %s size %s"%(self.id,self.__running,self.__task_queue,self.__task_queue.qsize()))
                task=None
                try:
                    task=self.__task_queue.get_nowait()
                    log.debug("got task %s"%task)
                    self.do_task(task)
                    self.__task_queue.task_done()
                except Empty:
                    log.notice("got nothing from task queue")
                    if self.__task_queue.qsize()>0:
                        log.error("task queue size %d but got nothing from task queue"%self.__task_queue.qsize())
                    time.sleep(1)
                except IOError, e:            
                    if e.errno == errno.EINTR:
                        break
                    log.exception("IO ERROR")
                    self.__task_queue.task_done()
                    time.sleep(1)
                except Exception as e:
                    log.exception("task (%s) cannot be executed." % task)
                    self.__result_queue.put(Result(task.type, Result.Failed, task.data))
                    self.__task_queue.task_done()
                    time.sleep(1)
            except KeyboardInterrupt:
                    break
            except Exception as e:
                log.exception("worker %s caught unknown exception, report to parent"%self.id)
                self.__result_queue.put(Result(task.type if task else Task.Unknown, Result.WorkerCrash, {'id':self.id}))
                break
        log.info("worker %s has quit"%self.id)

    def do_task(self, task):
        if task.type==Task.Provision:
            cloud_manager=self.__get_cloud_manager(task.data['resource'])
            instances=cloud_manager.boot(number=task.data['number'])
            self.__result_queue.put(Result(Result.Provision, Result.Success, {'instances':instances}))
        elif task.type==Task.UpdateCloudState:
            cloud_manager=self.__get_cloud_manager(task.data['resource'])
            instance=cloud_manager.update(instance=copy.deepcopy(task.data['instance']))
            instance.last_update_time=time.time()
            self.__result_queue.put(Result(Result.UpdateCloudState, Result.Success, {'instance':instance}))
        elif task.type==Task.UpdateConfigStatus:
            checker=self.__get_config_checker(task.data['checker'])
            instance=checker.check(instance=copy.deepcopy(task.data['instance']))
            instance.last_update_time=time.time()
            self.__result_queue.put(Result(Result.UpdateConfigStatus, Result.Success, {'instance':instance}))
        elif task.type==Task.Destroy:
            cloud_manager=self.__get_cloud_manager(task.data['resource'])
            if cloud_manager.destroy(instance=task.data['instance']):
                instance=cloud_manager.update(instance=task.data['instance'])
                task.data['instance'].last_update_time=time.time()
                self.__result_queue.put(Result(Result.Destroy, Result.Success, {'instance':instance}))
            else:
                self.__result_queue.put(Result(task.type, Result.Failed, task.data))
        elif task.type==Task.Quit:
            log.debug("got quit task, exiting...")
            self.__running=False
    
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
        elif config.keys()[0].lower()=="plugin":
            plugin_name=config['plugin']['name']
            return init_object(plugin_name)
        else:
            raise ConfigCheckerNotSupportedException("Config checker %s is not supported" % config.keys()[0])
        
