import logging
import sys

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