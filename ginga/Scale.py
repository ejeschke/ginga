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

    def get_scale_pct(self, pct):
        raise ScaleError("Subclass needs to override this method")


class LinearScale(ScaleBase):
    """
    y = x
        where x in (0..1)
    """
    
    def __init__(self, hashsize):
        super(LinearScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()
        
    def get_scale_pct(self, pct):
        val = min(max(float(pct), 0.0), 1.0)
        return val

    def __str__(self):
        return 'linear'


class LogScale(ScaleBase):
    """
    y = log(a*x + 1) / log(a)
        where x in (0..1)
    """
    
    def __init__(self, hashsize, exp=1000.0):
        self.exp = exp
        super(LogScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.log(self.exp * base + 1.0) / numpy.log(self.exp)
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_scale_pct(self, pct):
        val_inv = (math.exp(pct * math.log(self.exp)) - 1) / self.exp
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'log'


class PowerScale(ScaleBase):
    """
    y = ((a ** x) - 1) / a
        where x in (0..1)
    """
    
    def __init__(self, hashsize, exp=1000.0):
        self.exp = exp
        super(PowerScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (self.exp ** base) / self.exp
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_scale_pct(self, pct):
        val_inv = math.log(self.exp * pct + 1, self.exp)
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'power'


class SqrtScale(ScaleBase):
    """
    y = sqrt(x)
        where x in (0..1)
    """
    
    def __init__(self, hashsize):
        super(SqrtScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.sqrt(base)
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_scale_pct(self, pct):
        val_inv = pct ** 2.0
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'sqrt'


class SquaredScale(ScaleBase):
    """
    y = x ** 2
        where x in (0..1)
    """
    
    def __init__(self, hashsize):
        super(SquaredScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (base ** 2.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_scale_pct(self, pct):
        val_inv = math.sqrt(pct)
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'squared'


class AsinhScale(ScaleBase):
    """
    y = asinh(nonlinearity * x) / factor
        where x in (0..1)
    """
    
    def __init__(self, hashsize, factor=10.0, nonlinearity=3.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(AsinhScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.arcsinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def get_scale_pct(self, pct):
        # calculate inverse of scale fn
        val_inv = math.sinh(self.nonlinearity * pct) / self.factor
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'asinh'


class SinhScale(ScaleBase):
    """
    y = sinh(factor * x) / nonlinearity
        where x in (0..1)
    """
    
    def __init__(self, hashsize, factor=3.0, nonlinearity=10.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(SinhScale, self).__init__(hashsize)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.sinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def get_scale_pct(self, pct):
        # calculate inverse of scale fn
        val_inv = math.asinh(self.nonlinearity * pct) / self.factor
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'sinh'


class HistogramEqualizationScale(ScaleBase):
    """
    The histogram equalization scale function distributes colors based
    on the frequency of each data value.
    """
    
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
        
    def get_scale_pct(self, pct):
        # TODO: this is wrong but we need a way to invert the hash
        return pct

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
