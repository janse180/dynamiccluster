
import time

class Server(object):
    def __init__(self, background=False, pidfile=""):
        self.__background=background
        self.__pidfile=pidfile
        self.__running=True
        
    def start(self):
        while self.__running:
            time.sleep(1)
            print "hello"
            
    def quit(self):
        self.__running=False