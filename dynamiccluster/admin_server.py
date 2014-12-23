
from bottle import route, run
import threading

class Server(threading.Thread):
    @route('/hello')
    def hello():
        print "html hello"
        return "Hello World!"
    
    def __init__(self, port=8000):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        this.__port=port
        
    def run(self):
        run(host='localhost', port=__port, debug=True)
