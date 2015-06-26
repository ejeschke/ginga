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

    def __init__(self, length=0):
        self.length = length
        self.cursor = -1
        self.datums = {}
        self.history = []
        self.sortedkeys = []
        self.cond = threading.Condition()
        self.newdata = threading.Event()

    def __getitem__(self, key):
        with self.cond:
            return self.datums[key]

    def __setitem__(self, key, value):
        self.push(key, value)

    def __contains__(self, key):
        with self.cond:
            return key in self.datums

    def has_key(self, key):
        with self.cond:
            return key in self.datums

    def __delitem__(self, key):
        self.remove(key)

    def __len__(self):
        with self.cond:
            return len(self.history)

    def push(self, key, value):
        with self.cond:
            if key in self.history:
                self.history.remove(key)

            self.history.append(key)

            self.datums[key] = value
            self._eject_old()

            self.newdata.set()
            self.cond.notify()


    def pop_one(self):
        return self.remove(self.history[0])

    def pop(self, *args):
        if len(args) == 0:
            return self.remove(self.history[0])

        assert len(args) == 1, \
               ValueError("Too many parameters to pop()")
        return self.remove(args[0])

    def remove(self, key):
        with self.cond:
            val = self.datums[key]
            self.history.remove(key)
            del self.datums[key]

            self.sortedkeys = list(self.datums.keys())
            self.sortedkeys.sort()
            return val

    def _eject_old(self):
        if (self.length is None) or (self.length <= 0):
            # no limit
            return
        while len(self.history) > self.length:
            oldest = self.history.pop(0)
            del self.datums[oldest]

        self.sortedkeys = list(self.datums.keys())
        self.sortedkeys.sort()


    def index(self, key):
        with self.cond:
            return self.history.index(key)

    def index2key(self, index):
        with self.cond:
            return self.history[index]

    def index2value(self, index):
        with self.cond:
            return self.datums[self.history[index]]

    def youngest(self):
        return self.datums[self.history[-1]]

    def oldest(self):
        return self.datums[self.history[0]]

    def pop_oldest(self):
        return self.pop(self.history[0])

    def pop_youngest(self):
        return self.pop(self.history[-1])

    def keys(self, sort='alpha'):
        with self.cond:
            if sort == 'alpha':
                return self.sortedkeys
            elif sort == 'time':
                return self.history
            else:
                return self.datums.keys()

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
