import logging
import sys

def getLogger(name):
    """Get logging.Logger instance with logger name convention
    """
    if "." in name:
        name = "dynamiccluster.%s" % name.rpartition(".")[-1]
    return logging.getLogger(name)

