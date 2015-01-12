import logging
import sys
import random
import string
import socket
import datetime

def getLogger(name):
    """Get logging.Logger instance with logger name convention
    """
    if "." in name:
        name = "dynamiccluster.%s" % name.rpartition(".")[-1]
    return logging.getLogger(name)

def excepthook(exctype, value, traceback):
    """Except hook used to log unhandled exceptions to log
    """
    getLogger("dynamiccluster").critical(
        "Unhandled exception in Dynamic Cluster:", exc_info=True)
    return sys.__excepthook__(exctype, value, traceback)

def get_unique_string():
    return ''.join(random.choice(string.ascii_letters + string.digits) for letter in xrange(8))

def load_template_with_jinja(location, vars):
    # Load the jinja library's namespace into the current module.
    import jinja2
    
    # In this case, we will load templates off the filesystem.
    # This means we must construct a FileSystemLoader object.
    # 
    # The search path can be used to make finding templates by
    #   relative paths much easier.  In this case, we are using
    #   absolute paths and thus set it to the filesystem root.
    templateLoader = jinja2.FileSystemLoader( searchpath="/" )
    
    # An environment provides the data necessary to read and
    #   parse our templates.  We pass in the loader object here.
    templateEnv = jinja2.Environment( loader=templateLoader )
    
    # Read the template file using the environment object.
    # This also constructs our Template object.
    template = templateEnv.get_template( location )
    
    # Finally, process the template to produce our final text.
    return template.render( vars )

def hostname_lookup(ip):
    if hasattr(socket, 'setdefaulttimeout'):
        # Set the default timeout on sockets to 10 seconds
        socket.setdefaulttimeout(10)
    return socket.gethostbyaddr(ip)[0]

def unix_time(dt):
    epoch = datetime.datetime.utcfromtimestamp(0)
    delta = dt - epoch
    return delta.days*86400+delta.seconds+delta.microseconds/1e6