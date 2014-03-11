#
# log.py -- logging routines for Ginga
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
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
        
    def debug(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def info(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()
            
    def warn(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()

    def error(self, msg):
        if self.f_out:
            self.f_out.write("%s\n" % msg)
            self.f_out.flush()


def get_logger(name='ginga', level=None, null=False,
               options=None, log_file=None, log_stderr=False):

    if null:
        # User wants a Null Logger
        return NullLogger()
    
    # Create a logger
    logger = logging.Logger('ginga')

    if level == None:
        if (options != None) and (options.loglevel != None):
            level = options.loglevel
        else:
            level = logging.WARN

    fmt = logging.Formatter(LOG_FORMAT)
    if (not log_file) and (options != None) and (options.logfile != None):
        log_file = options.logfile

    if log_file:
        fileHdlr  = logging.handlers.RotatingFileHandler(options.logfile,
                                                         maxBytes=log_maxsize,
                                                         backupCount=log_backups)
        fileHdlr.setLevel(level)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if (not log_stderr) and (options != None) and (options.logstderr):
        log_stderr = options.logstderr

    if log_stderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(level)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    return logger

#END
