#
# NullLogger.py -- placeholder for a logging module logger
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

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


#END
