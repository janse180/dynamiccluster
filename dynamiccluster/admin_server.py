
from bottle import route, run
import threading
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)
data = None

class AdminServer(threading.Thread):
    
    @route('/hello')
    def hello():
        log.debug("html hello")
        return "Hello World!"
    
    @route('/workernode')
    def get_workernodes():
        global data
        log.debug(data.__dict__)
        return repr(data.worker_nodes)
    
    @route('/job')
    def get_jobs():
        global data
        log.debug(data.__dict__)
        return repr(data.queued_jobs)
    
    def __init__(self, port=8000, info=None):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.__port=port
        global data
        data=info
        log.debug(data.__dict__)
        
    def run(self):
        run(host='0.0.0.0', port=self.__port, debug=True)
