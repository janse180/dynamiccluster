from dynamiccluster.utilities import getLogger
from dynamiccluster.data import Instance

log = getLogger(__name__)

class ConfigChecker(object):
    def check(self, **kwargs):
        assert 0, 'Must define check'
        
class PortChecker(ConfigChecker):
    """
    Check if a port is opened.
    """
    def __init__(self, port):
        self.port=port
    def check(self, instance):
        import socket
        if hasattr(socket, 'setdefaulttimeout'):
            # Set the default timeout on sockets to 10 seconds
            socket.setdefaulttimeout(10)
        # Create a TCP socket
        log.debug( "Attempting to connect to %s on port %s" % (instance.ip, self.port) )
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        try:
            s.connect((instance.ip, self.port))
            log.debug(  "Connected to %s on port %s" % (instance.ip, self.port))
            s.shutdown(socket.SHUT_RDWR)
            s.close()
            instance.state=Instance.Ready
        except socket.error, e:
            log.debug( "Connection to %s on port %s failed: %s" % (instance.ip, self.port, e))
            instance.state=Instance.Active
        return instance
