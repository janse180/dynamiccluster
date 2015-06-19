from dynamiccluster.utilities import getLogger
from dynamiccluster.data import WorkerNode
from dynamiccluster.data import Instance
import threading
import time

log = getLogger(__name__)
info = None

class GraphiteReporter(threading.Thread):
    def __init__(self, _info=None, hostname="localhost", port=8080, interval=60, prefix="headnode.dynamiccluster"):
        threading.Thread.__init__(self, name=self.__class__.__name__)
        global info
        info=_info
        self.__running=True
        self.__address=(hostname, port)
        self.__interval=interval
        self.__prefix=prefix
        
    def run(self):
        global info
        import socket
        timeout_in_seconds = 2
        _socket = socket.socket()
        _socket.settimeout(timeout_in_seconds)
        try:
            _socket.connect(self.addr)
        except socket.timeout:
            raise GraphiteReporterError(
                "Took over %d second(s) to connect to %s" %
                (timeout_in_seconds, self.addr))
        except socket.gaierror:
            raise GraphiteReporterError(
                "No address associated with hostname %s:%s" % self.addr)
        except Exception as error:
            raise GraphiteReporterError(
                "unknown exception while connecting to %s - %s" %
                (self.addr, error)
            )
        log.debug("graphite reporter has started.")
        count=0
        while self.__running:
            if count%self.__interval==0:
                timestamp = int(time.time())
                value = len(info.worker_nodes)
                message = "%s.%s %d %d\n" % (self.__prefix, total_number,
                                          value, timestamp)
                try:
                    _socket.sendall(message)
    
                # Capture missing socket.
                except socket.gaierror as error:
                    raise GraphiteReporterError(
                        "Failed to send data to %s, with error: %s" %
                        (self.addr, error))
        
                # Capture socket closure before send.
                except socket.error as error:
                    raise GraphiteReporterError(
                        "Socket closed before able to send data to %s, "
                        "with error: %s" %
                        (self.addr, error)
                    )
        
                except Exception as error:
                    raise GraphiteReporterError(
                        "Unknown error while trying to send data down socket to %s, "
                        "error: %s" %
                        (self.addr, error)
                    )
                count=0
            else:
                count+=1
            time.sleep(1)

        try:
            _socket.shutdown(1)

        # If its currently a socket, set it to None
        except AttributeError:
            _socket = None
        except Exception:
            _socket = None

        # Set the self.socket to None, no matter what.
        finally:
            _socket = None
        log.debug("graphite reporter has quit.")

    def stop(self):
        self.__running=False
