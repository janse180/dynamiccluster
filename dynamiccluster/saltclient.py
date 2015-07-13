from dynamiccluster.utilities import getLogger
from dynamiccluster.config_checker import ConfigChecker
from dynamiccluster.data import WorkerNode
from dynamiccluster.data import Instance
import threading
import time

log = getLogger(__name__)
info = None

class SaltListener(threading.Thread):
    def __init__(self, _info=None):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        global info
        info=_info
        self.__running=True
        
    def run(self):
        import salt.utils.event
        event = salt.utils.event.MasterEvent('/var/run/salt/master')
        
        log.debug("salt listener has started.")
        while self.__running:
            evdata = event.get_event(wait=1, full=True)
            if evdata is not None:
                tag, data = evdata['tag'], evdata['data']
                log.debug("tag %s data %s" % (tag, data))
                if tag=="salt/auth":
                    self.process_auth_event(data)
            time.sleep(1)
        log.debug("salt listener has quit.")

    def process_auth_event(self, data):
        global info
        if 'act' in data and data['act']=="pend":
            minion_id=data['id']
            workernodes=[w for w in info.worker_nodes if w.instance.instance_name==minion_id and (w.state==WorkerNode.Starting or w.state==WorkerNode.Configuring)]
            import salt
            opts = salt.config.master_config('/etc/salt/master')
            import salt.wheel as wheel
            wheel = wheel.Wheel(opts)
            argument={'match':minion_id}
            if len(workernodes)==0:
                log.debug("node %s is a valid node, accept it" % minion_id)
                wheel.call_func('key.accept',**argument)
            else:
                log.debug("node %s is not a valid node, reject it" % minion_id)
                wheel.call_func('key.reject',**argument)
    def stop(self):
        self.__running=False
                
class SaltChecker(ConfigChecker):

    def check(self, instance):
        import salt.client
        local = salt.client.LocalClient()
        running_jobs=local.cmd(instance.instance_name,'saltutil.is_running',['state.highstate'])
        if running_jobs is None or instance.instance_name not in running_jobs:
            log.error("Unable to check the config status of %s"%instance.instance_name)
            raise ConfigCheckerError()
        if len(running_jobs[instance.instance_name])>0:
            log.notice("highstate is still running, wait a bit longer")
            instance.state=Instance.Active
            return instance
        results=local.cmd(instance.instance_name, 'state.highstate', {"test":True})
        if results is None or instance.instance_name not in results:
            log.error("Unable to check the config status of %s"%instance.instance_name)
            raise ConfigCheckerError()
        instance.state=Instance.Active
        configured=True
        for check in results[instance.instance_name].keys():
            if results[instance.instance_name][check]['result'] is not True:
                configured=False
                break
        if configured is True:
            instance.state=Instance.Configured
        return instance