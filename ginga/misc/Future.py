# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading
from . import Callback

class TimeoutError(Exception):
    pass

class Future(Callback.Callbacks):
    def __init__(self, data=None):
        Callback.Callbacks.__init__(self)

        self.evt = threading.Event()
        self.res = None
        # User can attach some arbitrary data if desired
        self.data = data

        self.enable_callback('resolved')

    def get_data(self):
        return self.data
    
    def freeze(self, method, *args, **kwdargs):
        self.method = method
        self.args = args
        self.kwdargs = kwdargs

    def thaw(self, suppress_exception=True):
        self.evt.clear()
        if not suppress_exception:
            res = self.method(*self.args, **self.kwdargs)

        else:
            try:
                res = self.method(*self.args, **self.kwdargs)

            except Exception as e:
                res = e

        self.resolve(res)
        return res
        
    def has_value(self):
        return self.evt.isSet()
    
    def resolve(self, value):
        self.res = value
        self.evt.set()
        # TODO: need to change callbacks on some custom plugins first
        #self.make_callback('resolved', value)
        self.make_callback('resolved')

    def get_value(self, block=True, timeout=None, suppress_exception=False):
        if block:
            self.evt.wait(timeout=timeout)
        if not self.has_value():
            raise TimeoutError("Timed out waiting for value!")

        if isinstance(self.res, Exception) and (not suppress_exception):
            raise self.res

        return self.res

    def wait(self, timeout=None):
        self.evt.wait(timeout=timeout)
        if not self.has_value():
            raise TimeoutError("Timed out waiting for value!")

        return self.res


#END
