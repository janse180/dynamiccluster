from dynamiccluster.utilities import getLogger

log = getLogger(__name__)

class ConfigChecker(object):
    def check(self, **kwargs):
        assert 0, 'Must define check'
        
class PortChecker(ConfigChecker):
    def __init__(self, port):
        self.port=port
    def check(self, address):
        import socket
        if hasattr(socket, 'setdefaulttimeout'):
            # Set the default timeout on sockets to 10 seconds
            socket.setdefaulttimeout(10)
        # Create a TCP socket
        log.debug( "Attempting to connect to %s on port %s" % (address, self.port) )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        try:
            s.connect((address, self.port))
            log.debug(  "Connected to %s on port %s" % (address, self.port))
            s.shutdown(2)
            return True
        except socket.error, e:
            log.debug( "Connection to %s on port %s failed: %s" % (address, self.port, e))
            return False
