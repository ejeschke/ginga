#
# Bunch.py -- simple classes for grouping variables
# 
# See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308
# Description:
#
# TODO: make these true subclasses of dict
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading

class caselessDict(object):
    """
    Case-insensitive dictionary.  Adapted from
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66315
    """
    def __init__(self, inDict=None):
        """Constructor: takes conventional dictionary as input (or nothing)
        """
        self.dict = {}
        if inDict is not None:
            self.update(inDict)

    def lower(self, key):
        try:
            return key.lower()
        except AttributeError:
            return key

    def update(self, inDict):
        for key in inDict.keys():
            k = self.lower(key) 
            self.dict[k] = (key, inDict[key])

    def store(self, inDict):
        return self.update(inDict)

    def setvals(self, **kwdargs):
        return self.update(kwdargs)

    def fetchList(self, keySeq):
        res = []
        for key in keySeq:
            res.append(self.dict[key])

        return res

    def fetchDict(self, keyDict):
        res = {}
        for key in keyDict.keys():
            res[key] = self.dict[key]
        return res

    def fetch(self, keyDict):
        """Like update(), but for retrieving values.
        """
        for key in keyDict.keys():
            keyDict[key] = self.dict[key]

    def clear(self):
        self.dict.clear()

    def setdefault(self, key, val):
        if key in self:
            return self.__getitem__(key)
        else:
            self.__setitem__(key, val)
            return val

    def __iter__(self):
        self.iterPosition = 0
        self.keyList = self.dict.keys()
        return(self)

    def next(self):
        if self.iterPosition >= len(self.keyList):
            raise StopIteration
        x = self.dict[self.keyList[self.iterPosition]][0]
        self.iterPosition += 1
        return x

    def iteritems(self):
        return iter(self.items())

    def iterkeys(self):
        return iter(self.keys())

    def itervalues(self):
        return iter(self.values())

    def __getitem__(self, key):
        k = self.lower(key)
        return self.dict[k][1]

    def __setitem__(self, key, value):
        k = self.lower(key)
        self.dict[k] = (key, value)

    def __delitem__(self, key):
        k = self.lower(key)
        del self.dict[k]

    def has_key(self, key):
        k = self.lower(key)
        return k in self.dict

    def canonicalKey(self, key):
        k = self.lower(key)
        return self.dict[k][0]

    def get(self, key, alt=None):
        if key in self:
            return self.__getitem__(key)
        return alt

    def __len__(self):
        return len(self.dict)

    def keys(self):
        return [v[0] for v in self.dict.values()]

    def values(self):
        return [v[1] for v in self.dict.values()]

    def items(self):
        return self.dict.values()

    def __contains__(self, item):
        return item.lower() in self.dict
        
    def __repr__(self):
        items = ", ".join([("%r: %r" % (k,v)) for k,v in self.items()])
        return "{%s}" % items

    def __str__(self):
        return repr(self)

    def copy(self):
        d={}
        for k,v in self.dict.items():
            d[k]=v[1] 
        return d


    
class Bunch(object):
    """Often we want to just collect a bunch of stuff together, naming each
    item of the bunch; a dictionary's OK for that, but a small do-nothing
    class is even handier, and prettier to use.
    
    e.g.
    point = Bunch(datum=y, squared=y*y, coord=x)
    
    and of course you can read/write the named attributes you just created,
    add others, delete some of them, e.g.
        if point.squared > threshold:
            point.isok = 1
    This Bunch class provides both dictionary and attribute-style access,
    so you can use either method for member access or even mix-and-match.
    """

    def __init__(self, inDict=None, caseless=False, **kwdargs):
        """Constructor for a Bunch.  If _caseless_ is True, bunch will
        ignore case in looking up members; e.g.

        foo = Bunch(caseless=True, Bar=4)
        foo['BAR'] => 4
        foo['bar'] => 4
        foo['BaR'] => 4
        foo.BAR => 4
        foo.bar => 4
        foo.BaR => 4
        """

        if caseless:
            self.tbl = caselessDict(inDict=inDict)
        else:
            self.tbl = {}
            if inDict is not None:
                self.tbl.update(inDict)

        self.tbl.update(kwdargs)

        self.iterPosition = 0
        self.keyList = self.tbl.keys()

        # after initialisation, setting attributes is the same as setting
        # an item.
        self.__initialised = True
        

    def __getitem__(self, key):
        """Maps dictionary keys to values.
        Called for dictionary style access of this object.
        """
        return self.tbl[key]

    def __setitem__(self, key, value):
        """Maps dictionary keys to values for assignment.  Called for dictionary style
        access with assignment.
        """
        self.tbl[key] = value

    def __delitem__(self, key):
        del self.tbl[key]

    def __getattr__(self, attr):
        """Maps values to attributes.
        Only called if there *isn't* an attribute with this name.  Called for attribute
        style access of this object.
        """
        return self.tbl[attr]


    def __setattr__(self, attr, value):
        """Maps attributes to values for assignment.  Called for attribute style access
        of this object for assignment.
        """

        # this test allows attributes to be set in the __init__ method
        # (self.__dict__[_Bunch__initialised] same as self.__initialized)
        if '_Bunch__initialised' not in self.__dict__:
            self.__dict__[attr] = value

        else:
            # Any normal attributes are handled normally
            if attr in self.__dict__:
                self.__dict__[attr] = value
            # Others are entries in the table
            else:
                self.tbl[attr] = value


    def __str__(self):
        return self.tbl.__str__()


    def __repr__(self):
        return self.tbl.__repr__()


    def __getstate__(self):
        return self.tbl.__repr__()


    def __setstate__(self, pickled_state):
        self.tbl = eval(pickled_state)

    def __iter__(self):
        return iter(self.tbl.keys())

    def __contains__(self, key):
        return key in self.tbl

    ## def next(self):
    ##     if self.iterPosition >= len(self.keyList):
    ##         raise StopIteration
    ##     x = self.tbl[self.keyList[self.iterPosition]][0]
    ##     self.iterPosition += 1
    ##     return x

    ## def iteritems(self):
    ##     return iter(self.items())

    ## def iterkeys(self):
    ##     return iter(self.keys())

    ## def itervalues(self):
    ##     return iter(self.values())

    def update(self, dict2):
        return self.tbl.update(dict2)

    def store(self, dict2):
        return self.tbl.update(dict2)

    def setvals(self, **kwdargs):
        return self.tbl.update(kwdargs)

    def fetch(self, keyDict):
        """Like update(), but for retrieving values.
        """
        for key in keyDict.keys():
            keyDict[key] = self.tbl[key]

    def fetchDict(self, keyDict):
        res = {}
        for key in keyDict.keys():
            res[key] = self.tbl[key]
        return res

    def fetchList(self, keySeq):
        res = []
        for key in keySeq:
            res.append(self.tbl[key])

        return res

    def keys(self):
        return self.tbl.keys()

    def has_key(self, key):
        return key in self.tbl

    def get(self, key, alt=None):
        if key in self:
            return self.__getitem__(key)
        return alt

    def setdefault(self, key, val):
        if key in self:
            return self.__getitem__(key)
        else:
            self.__setitem__(key, val)
            return val

    def items(self):
        return self.tbl.items()

    def values(self):
        return self.tbl.values()

    def copy(self):
        return self.tbl.copy()


class threadSafeBunch(object):
    """Like a Bunch, but with thread safety built-in.  Multiple threads can
    try to read and write the bunch concurrently and it all just works.
    """

    def __init__(self, inDict=None, caseless=False, **kwdargs):

        self.lock = threading.RLock()
        if caseless:
            self.tbl = caselessDict(inDict=inDict)
        else:
            self.tbl = {}
            if inDict is not None:
                self.tbl.update(inDict)

        self.tbl.update(kwdargs)

        # After initialisation, setting attributes is the same as setting
        # an item.
        self.__initialised = True
        

    def enter(self):
        """Acquires the lock used for this Bunch.  USE WITH EXTREME CAUTION!
        """
        return self.lock.acquire()


    def leave(self):
        """Releases the lock on this Bunch.  USE WITH EXTREME CAUTION!
        """
        return self.lock.release()


    def getlock(self):
        """Returns the lock used for this Bunch.  USE WITH EXTREME CAUTION!
        """
        return self.lock


    def getitem(self, key):
        """Maps dictionary keys to values.
        Called for dictionary style access of this object.
        """
        with self.lock:
            return self.tbl[key]


    def __getitem__(self, key):
        return self.getitem(key)


    def fetch(self, keyDict):
        """Like update(), but for retrieving values.
        """
        with self.lock:
            for key in keyDict.keys():
                keyDict[key] = self.tbl[key]


    def fetchDict(self, keyDict):
        with self.lock:
            res = {}
            for key in keyDict.keys():
                res[key] = self.tbl[key]

            return res
        

    def fetchList(self, keySeq):
        with self.lock:
            res = []
            for key in keySeq:
                res.append(self.tbl[key])

            return res


    def setitem(self, key, value):
        """Maps dictionary keys to values for assignment.  Called for
        dictionary style access with assignment.
        """
        with self.lock:
            self.tbl[key] = value


    def __setitem__(self, key, value):
        return self.setitem(key, value)
    

    def setvals(self, **kwdargs):
        return self.update(kwdargs)

    
    def delitem(self, key):
        """Deletes key/value pairs from object.
        """
        with self.lock:
            del self.tbl[key]

    def __contains__(self, key):
        with self.lock:
            return key in self.tbl
    
    def __delitem__(self, key):
        return self.delitem(key)
    

    def __getattr__(self, key):
        """Maps values to attributes.
        Only called if there *isn't* an attribute with this name.
        Called for attribute style access of this object.
        """
        return self.getitem(key)


    def __setattr__(self, key, value):
        """Maps attributes to values for assignment.
        Called for attribute style access of this object for assignment.
        """

        # this test allows attributes to be set in the __init__ method
        # (self.__dict__[_threadSafeBunch__initialised] same as
        #   self.__initialized)
        if '_threadSafeBunch__initialised' not in self.__dict__:
            self.__dict__[key] = value

        else:
            with self.lock:
                # Any normal attributes are handled normally
                if key in self.__dict__:
                    self.__dict__[key] = value
                # Others are entries in the table
                else:
                    self.tbl[key] = value
            

    def __delattr__(self, key):
        """Deletes key/value pairs from object.
        """
        with self.lock:
            del self.tbl[key]


    def __str__(self):
        with self.lock:
            return self.tbl.__str__()


    def __len__(self):
        with self.lock:
            return len(self.tbl)


    def __repr__(self):
        with self.lock:
            return self.tbl.__repr__()

    def clear(self):
        """Clears all key/value pairs.
        """
        with self.lock:
            self.tbl.clear()

    ##############################################################
    # the following methods are inherited by subclasses
    ##############################################################

    def has_key(self, key):
        """Checks for membership of dictionary key.
        """
        with self.lock:
            return key in self.tbl


    def keys(self):
        """Returns list of keys.
        """
        with self.lock:
            return self.tbl.keys()


    def values(self):
        """Returns list of values.
        """
        with self.lock:
            return self.tbl.values()

    def update(self, updict):
        """Updates key/value pairs in dictionary from _updict_.
        """
        
        with self.lock:
            for (key, value) in updict.items():
                self.setitem(key, value)


    def items(self):
        """Returns list of items.
        """
        with self.lock:
            return self.tbl.items()


    def get(self, key, alt=None):
        """If dictionary contains _key_ return the associated value,
        otherwise return _alt_. 
        """
        with self.lock:
            if key in self:
                return self.getitem(key)
            
            else:
                return alt


    def setdefault(self, key, value):
        """Atomic store conditional.  Stores _value_ into dictionary
        at _key_, but only if _key_ does not already exist in the dictionary.
        Returns the old value found or the new value.
        """
        with self.lock:
            if key in self:
                return self.getitem(key)

            else:
                self.setitem(key, value)
                return value

    def getsetitem(self, key, klass, args=None, kwdargs=None):
        """This is similar to setdefault(), except that the new value is
        created by instantiating _klass_.  This prevents you from having
        to create an object and initialize it and then throw it away if
        there is already a dictionary item of that type.
        """

        with self.lock:
            if key in self:
                return self.getitem(key)

            # Instantiate value.
            if not args:
                args = []
            if not kwdargs:
                kwdargs = {}
            value = klass(*args, **kwdargs)

            self.setitem(key, value)
            return value


# Undoubtedly there are more dictionary interface methods ...

class threadSafeList(object):
    """Like a list, but thread-safe.
    """

    def __init__(self, *args):

        self.lock = threading.RLock()
        self.list = list(args)


    def append(self, item):
        with self.lock:
            self.list.append(item)
        
    def extend(self, list2):
        with self.lock:
            self.list.extend(list2)
        
    def prepend(self, item):
        with self.lock:
            self.list = [item].extend(self.list)
            return self.list
        
    def cons(self, item):
        return self.prepend(item)

    
#END Bunch.py

