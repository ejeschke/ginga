#
# log.py -- logging routines for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import logging
import logging.handlers

LOG_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

# max size of log file before rotating
log_maxsize = 20 * 1024*1024
log_backups = 4

class NullLogger(object):
    """
    The NullLogger can be used in the place of a "real" logging module logger
    if the code just uses the standard levels/methods for logging.

    It is useful when you need to suppress logging or bypass the overhead of
    the logging module logger.
    """
    def __init__(self, f_out=None):
        self.f_out = f_out
        self.handlers = []

    def debug(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def info(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def warning(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def warn(self, msg):
        return self.warning(msg)

    def error(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def addHandler(self, hndlr):
        pass


def get_logger(name='ginga', level=None, null=False,
               options=None, log_file=None, log_stderr=False):

    if null or ((options is not None) and hasattr(options, 'nulllogger') and
                options.nulllogger):
        # User wants a Null Logger
        return NullLogger()

    # Create a logger
    logger = logging.Logger('ginga')

    if level is None:
        if (options is not None) and (options.loglevel is not None):
            level = options.loglevel
        else:
            level = logging.WARN

    fmt = logging.Formatter(LOG_FORMAT)
    if (not log_file) and (options is not None) and (options.logfile is not None):
        log_file = options.logfile

    if log_file is not None:
        if ((options is not None) and (getattr(options, 'rmlog', False)) and
            os.path.exists(log_file)):
            os.remove(log_file)
        # TODO: get maxsize and backup from options, if present
        fileHdlr  = logging.handlers.RotatingFileHandler(log_file,
                                                         maxBytes=log_maxsize,
                                                         backupCount=log_backups)
        fileHdlr.setLevel(level)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if (not log_stderr) and (options is not None) and (options.logstderr):
        log_stderr = options.logstderr

    if log_stderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(level)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    return logger


def addlogopts(parser):
    if hasattr(parser, 'add_option'):
        # older OptParse
        add_argument = parser.add_option
    else:
        # newer ArgParse
        add_argument = parser.add_argument

    add_argument("--log", dest="logfile", metavar="FILE",
                 help="Write logging output to FILE")
    add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                 default=20, type=int,
                 help="Set logging level to LEVEL")
    add_argument("--lognull", dest="nulllogger", default=False,
                 action="store_true",
                 help="Use a null logger")
    add_argument("--logsize", dest="logsize", metavar="NUMBYTES",
                 type=int, default=log_maxsize,
                 help="Set maximum logging level to NUMBYTES")
    add_argument("--logbackups", dest="logbackups", metavar="NUM",
                 type=int, default=log_backups,
                 help="Set maximum number of backups to NUM")
    add_argument("--rmlog", dest="rmlog", default=False,
                 action="store_true",
                 help="Remove log if present (don't append)")
    add_argument("--stderr", dest="logstderr", default=False,
                 action="store_true",
                 help="Copy logging also to stderr")


#END
