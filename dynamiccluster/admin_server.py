
from bottle import route, run
import threading
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)
server = None

class AdminServer(threading.Thread):
    
    @route('/hello')
    def hello():
        log.debug("html hello")
        return "Hello World!"
    
    @route('/workernode')
    def get_workernodes():
        global server
        #log.debug(data.__dict__)
        return repr(server.info.worker_nodes)
    
    @route('/job')
    def get_jobs():
        global server
        #log.debug(data.__dict__)
        return repr(server.info.queued_jobs)
    
    @route('/server/config')
    def get_server_config():
        global server
        return server.config
    
    @route('/server/status')
    def get_server_status():
        global server
        return server.get_status()
    
    @route('/server/sleep', method="POST")
    def get_server_sleep():
        global server
        return server.set_sleep()
    
    @route('/server/sleep', method="DELETE")
    def unset_server_sleep():
        global server
        return server.unset_sleep()
    
    def __init__(self, srv=None):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        global server
        server=srv
        self.__port=server.config['dynamic-cluster']['admin-server']['port']
        
    def run(self):
        run(host='0.0.0.0', port=self.__port, debug=True)
