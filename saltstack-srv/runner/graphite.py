# -*- coding: utf-8 -*-

from __future__ import absolute_import

import salt.pillar

# Import salt libs
import salt.utils.error
        
def send(minion_id, data, host, port):
    """
    a method to send metric to graphite
    """
    import socket
    timeout_in_seconds = 2
    _socket = socket.socket()
    _socket.settimeout(timeout_in_seconds)
    addr=(host, port)
    messages = _generate_messages(minion_id, data)
    try:
        _socket.connect(addr)
    except socket.timeout:
        salt.utils.error.raise_error(name="graphite.send", message="Took over %d second(s) to connect to %s" % (timeout_in_seconds, addr))
    except socket.gaierror:
        salt.utils.error.raise_error(name="graphite.send", message="No address associated with hostname %s" % addr)
    except Exception as error:
        salt.utils.error.raise_error(name="graphite.send", message="unknown exception while connecting to %s - %s" % (addr, error))

    try:
        _socket.sendall('\n'.join(messages)+'\n')

    # Capture missing socket.
    except socket.gaierror as error:
        salt.utils.error.raise_error(name="graphite.send", message="Failed to send data to %s, with error: %s" % (addr, error))

    # Capture socket closure before send.
    except socket.error as error:
        salt.utils.error.raise_error(name="graphite.send", message="Socket closed before able to send data to %s, with error: %s" % (addr, error))

    except Exception as error:
        salt.utils.error.raise_error(name="graphite.send", message="Unknown error while trying to send data down socket to %s, with error: %s" % (addr, error))

    try:
        _socket.close()

    # If its currently a socket, set it to None
    except AttributeError:
        pass
    except Exception:
        pass

def _generate_messages(minion_id, data):
    messages=[]
    if data['tag']=='loadavg':
        messages.append("%s.load.1min %s %d" % (minion_id, data['1m'], data['timestamp'] ))
        messages.append("%s.load.5min %s %d" % (minion_id, data['5m'], data['timestamp'] ))
        messages.append("%s.load.15min %s %d" % (minion_id, data['15m'], data['timestamp'] ))
    return messages

def cleanup(minion_id, whisper_path):
    """
    a method to clean up metric data in whisper
    """
    import shutil
    import os
    try:
        shutil.rmtree(whisper_path+os.linesep+minion_id)
    except Exception as error:
        salt.utils.error.raise_error(name="graphite.cleanup", message="unable to cleanup data for worker node %s: %s" % (minion_id, error))