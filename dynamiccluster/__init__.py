import logging.handlers

# Custom debug level
logging.HEAVYDEBUG = 5

"""
Below derived from:
    https://mail.python.org/pipermail/tutor/2007-August/056243.html
"""

logging.NOTICE = logging.INFO + 5
logging.addLevelName(logging.NOTICE, 'NOTICE')

# define a new logger function for notice
# this is exactly like existing info, critical, debug...etc
def _Logger_notice(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity 'NOTICE'.
    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.
    logger.notice("Houston, we have a %s", "major disaster", exc_info=1)
    """
    if self.isEnabledFor(logging.NOTICE):
        self._log(logging.NOTICE, msg, args, **kwargs)

logging.Logger.notice = _Logger_notice

# define a new root level notice function
# this is exactly like existing info, critical, debug...etc
def _root_notice(msg, *args, **kwargs):
    """
    Log a message with severity 'NOTICE' on the root logger.
    """
    if len(logging.root.handlers) == 0:
        logging.basicConfig()
    logging.root.notice(msg, *args, **kwargs)

# make the notice root level function known
logging.notice = _root_notice

# add NOTICE to the priority map of all the levels
logging.handlers.SysLogHandler.priority_map['NOTICE'] = 'notice'
