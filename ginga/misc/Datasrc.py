#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading

class TimeoutError(Exception):
    pass

class Datasrc(object):

    def __init__(self, length=20):
        self.length = length
        self.cursor = -1
        self.datums = {}
        self.history = []
        self.sortedkeys = []
        self.cond = threading.Condition()
        self.newdata = threading.Event()


    def __getitem__(self, key):
        with self.cond:
            if isinstance(key, int):
                return self.datums[self.sortedkeys[key]]
            else:
                return self.datums[key]

        
    def __setitem__(self, key, value):
        with self.cond:
            if key in self.history:
                self.history.remove(key)

            self.history.append(key)

            self.datums[key] = value
            self._eject_old()
            
            self.newdata.set()
            self.cond.notify()
        

    def __len__(self):
        with self.cond:
            return len(self.sortedkeys)


    def _eject_old(self):
        while len(self.history) > self.length:
            oldest = self.history.pop(0)
            del self.datums[oldest]

        self.sortedkeys = list(self.datums.keys())
        self.sortedkeys.sort()


    def index(self, key):
        with self.cond:
            return self.sortedkeys.index(key)

    def index2key(self, index):
        with self.cond:
            return self.sortedkeys[index]

    def youngest(self):
        return self.datums[self.history[-1]]
    
    def oldest(self):
        return self.datums[self.history[0]]
    
    def keys(self, sort='alpha'):
        with self.cond:
            if sort == 'alpha':
                return self.sortedkeys
            elif sort == 'time':
                return self.history
            else:
                return self.datums.keys()

    def has_key(self, key):
        with self.cond:
            return self.datums.has_key(key)
        
    def wait(self, timeout=None):
        with self.cond:
            self.cond.wait(timeout=timeout)

            if not self.newdata.isSet():
                raise TimeoutError("Timed out waiting for datum")

            self.newdata.clear()
            return self.history[-1]


    def get_bufsize(self):
        with self.cond:
            return self.length
       
        
    def set_bufsize(self, length):
        with self.cond:
            self.length = length
            self._eject_old()

        
#END
