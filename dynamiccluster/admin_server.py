
from bottle import route, run
import threading
from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

class AdminServer(threading.Thread):
    @route('/hello')
    def hello():
        log.debug("html hello")
        return "Hello World!"
    
    def __init__(self, port=8000):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        self.__port=port
        
    def run(self):
        run(host='0.0.0.0', port=self.__port, debug=True)
