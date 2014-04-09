#
# Scale.py -- Data scaling
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Scaling algorithms are modeled after the ones described for ds9 here:

    http://ds9.si.edu/doc/ref/how.html
    
"""
import math
import numpy

class ScaleError(Exception):
    pass

class ScaleBase(object):

    def __init__(self, hashsize, colorlen=256):
        super(ScaleBase, self).__init__()

        self.hashsize = hashsize
        self.colorlen = colorlen
        self.maxhashsize = 1024*1024
        # this actually holds the hash array
        self.hash = None
        self.calc_hash()

    def hash_array(self, idx):
        # NOTE: data could be assumed to be in the range 0..hashsize-1
        # at this point but clip as a precaution
        idx = idx.clip(0, self.hashsize-1)
        arr = self.hash[idx]
        return arr
        
    def get_hash_size(self):
        return self.hashsize
    
    def set_hash_size(self, size):
        assert (size >= self.colorlen) and (size <= self.maxhashsize), \
               ScaleError("Bad hash size!")
        self.hashsize = size
        self.calc_hash()

    def check_hash(self):
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
               ScaleError("Computed hash table size (%d) != specified size (%d)" % (hashlen, self.hashsize))

    def calc_hash(self):
        raise ScaleError("Subclass needs to override this method")


class LinearScale(ScaleBase):
    
    def __init__(self, hashsize):
        super(LinearScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()
        
    def __str__(self):
        return 'linear'


class LogScale(ScaleBase):
    
    def __init__(self, hashsize, exp=1000.0):
        self.exp = exp
        super(LogScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        l = numpy.log(self.exp * base + 1.0) / numpy.log(self.exp)
        # normalize to color range
        l = l.clip(0.0, 1.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def __str__(self):
        return 'log'


class PowerScale(ScaleBase):
    
    def __init__(self, hashsize, exp=1000.0):
        self.exp = exp
        super(PowerScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        l = (self.exp ** base) / self.exp
        # normalize to color range
        l = l.clip(0.0, 1.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def __str__(self):
        return 'power'


class SqrtScale(ScaleBase):
    
    def __init__(self, hashsize):
        super(SqrtScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        l = numpy.sqrt(base)
        # normalize to color range
        l = l.clip(0.0, 1.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def __str__(self):
        return 'sqrt'


class SquaredScale(ScaleBase):
    
    def __init__(self, hashsize):
        super(SquaredScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        # normalize to color range
        l = (base ** 2.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def __str__(self):
        return 'squared'


class AsinhScale(ScaleBase):
    
    def __init__(self, hashsize, factor=10.0, nonlinearity=3.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(AsinhScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        l = numpy.arcsinh(self.factor * base) / self.nonlinearity
        # normalize to color range
        l = l.clip(0.0, 1.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def __str__(self):
        return 'asinh'


class SinhScale(ScaleBase):
    
    def __init__(self, hashsize, factor=3.0, nonlinearity=10.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(SinhScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        l = numpy.sinh(self.factor * base) / self.nonlinearity
        l = l.clip(0.0, 1.0) * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def __str__(self):
        return 'sinh'


class HistogramEqualizationScale(ScaleBase):
    
    def __init__(self, hashsize):
        super(HistogramEqualizationScale, self).__init__(hashsize)

    def calc_hash(self):
        pass

    # TODO: this method has a lot more overhead compared to the other
    # scaling methods because the hash array must be computed each time
    # the data is delivered to hash_array()--in the other scaling
    # methods it is precomputed in calc_hash().  Investigate whether
    # there is a way to make this more efficient.
    #
    def hash_array(self, idx):
        # NOTE: data could be assumed to be in the range 0..hashsize-1
        # at this point but clip as a precaution
        idx = idx.clip(0, self.hashsize-1)
        
        #get image histogram
        hist, bins = numpy.histogram(idx.flatten(),
                                     self.hashsize, density=False)
        cdf = hist.cumsum()

        # normalize to color range
        l = (cdf - cdf.min()) * (self.colorlen - 1) / (
            cdf.max() - cdf.min())
        self.hash = l.astype(numpy.uint)
        self.check_hash()

        arr = self.hash[idx]
        return arr
        
    def __str__(self):
        return 'histeq'



scaler = {
    'linear': LinearScale,
    'log': LogScale,
    'power': PowerScale,
    'sqrt': SqrtScale,
    'squared': SquaredScale,
    'asinh': AsinhScale,
    'sinh': SinhScale,
    'histeq': HistogramEqualizationScale,
    }
    
def add_scaler(name, scaleClass):
    global scaler
    scaler[name.lower()] = scaleClass
    
def get_scaler_names():
    #return scaler.keys()
    return ['linear', 'log', 'power', 'sqrt', 'squared', 'asinh', 'sinh',
            'histeq']
    
def get_scaler(name):
    if not name in scaler:
        raise ScaleError("Invalid scale algorithm '%s'" % (name))
    return scaler[name]
    
#END
