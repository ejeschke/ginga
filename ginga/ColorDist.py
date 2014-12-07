#
# ColorDist.py -- Color Distribution algorithms
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
These algorithms are modeled after the ones described for ds9 here:

    http://ds9.si.edu/doc/ref/how.html
    
"""
import math
import numpy

class ColorDistError(Exception):
    pass

class ColorDistBase(object):

    def __init__(self, hashsize, colorlen=None):
        super(ColorDistBase, self).__init__()

        self.hashsize = hashsize
        if colorlen is None:
            colorlen = 256
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
               ColorDistError("Bad hash size!")
        self.hashsize = size
        self.calc_hash()

    def check_hash(self):
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
               ColorDistError("Computed hash table size (%d) != specified size (%d)" % (hashlen, self.hashsize))

    def calc_hash(self):
        raise ColorDistError("Subclass needs to override this method")

    def get_dist_pct(self, pct):
        raise ColorDistError("Subclass needs to override this method")


class LinearDist(ColorDistBase):
    """
    y = x
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None):
        super(LinearDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()
        
    def get_dist_pct(self, pct):
        val = min(max(float(pct), 0.0), 1.0)
        return val

    def __str__(self):
        return 'linear'


class LogDist(ColorDistBase):
    """
    y = log(a*x + 1) / log(a)
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None, exp=1000.0):
        self.exp = exp
        super(LogDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.log(self.exp * base + 1.0) / numpy.log(self.exp)
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_dist_pct(self, pct):
        val_inv = (math.exp(pct * math.log(self.exp)) - 1) / self.exp
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'log'


class PowerDist(ColorDistBase):
    """
    y = ((a ** x) - 1) / a
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None, exp=1000.0):
        self.exp = exp
        super(PowerDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (self.exp ** base - 1.0) / self.exp
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_dist_pct(self, pct):
        val_inv = math.log(self.exp * pct + 1, self.exp)
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'power'


class SqrtDist(ColorDistBase):
    """
    y = sqrt(x)
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None):
        super(SqrtDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.sqrt(base)
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_dist_pct(self, pct):
        val_inv = pct ** 2.0
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'sqrt'


class SquaredDist(ColorDistBase):
    """
    y = x ** 2
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None):
        super(SquaredDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = (base ** 2.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)
        
        self.check_hash()

    def get_dist_pct(self, pct):
        val_inv = math.sqrt(pct)
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'squared'


class AsinhDist(ColorDistBase):
    """
    y = asinh(nonlinearity * x) / factor
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None, factor=10.0,
                 nonlinearity=3.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(AsinhDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.arcsinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def get_dist_pct(self, pct):
        # calculate inverse of dist fn
        val_inv = math.sinh(self.nonlinearity * pct) / self.factor
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'asinh'


class SinhDist(ColorDistBase):
    """
    y = sinh(factor * x) / nonlinearity
        where x in (0..1)
    """
    
    def __init__(self, hashsize, colorlen=None, factor=3.0,
                 nonlinearity=10.0):
        self.factor = factor
        self.nonlinearity = nonlinearity
        super(SinhDist, self).__init__(hashsize, colorlen=colorlen)

    def calc_hash(self):
        base = numpy.arange(0.0, float(self.hashsize), 1.0) / self.hashsize
        base = numpy.sinh(self.factor * base) / self.nonlinearity
        base = base.clip(0.0, 1.0)
        # normalize to color range
        l = base * (self.colorlen - 1)
        self.hash = l.astype(numpy.uint)

        self.check_hash()

    def get_dist_pct(self, pct):
        # calculate inverse of dist fn
        val_inv = math.asinh(self.nonlinearity * pct) / self.factor
        val = min(max(float(val_inv), 0.0), 1.0)
        return val

    def __str__(self):
        return 'sinh'


class HistogramEqualizationDist(ColorDistBase):
    """
    The histogram equalization distribution function distributes colors
    based on the frequency of each data value.
    """
    
    def __init__(self, hashsize, colorlen=None):
        super(HistogramEqualizationDist, self).__init__(hashsize,
                                                         colorlen=colorlen)

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
        
    def get_dist_pct(self, pct):
        # TODO: this is wrong but we need a way to invert the hash
        return pct

    def __str__(self):
        return 'histeq'



distributions = {
    'linear': LinearDist,
    'log': LogDist,
    'power': PowerDist,
    'sqrt': SqrtDist,
    'squared': SquaredDist,
    'asinh': AsinhDist,
    'sinh': SinhDist,
    'histeq': HistogramEqualizationDist,
    }
    
def add_dist(name, distClass):
    global distributions
    distributions[name.lower()] = distClass
    
def get_dist_names():
    #return distributions.keys()
    return ['linear', 'log', 'power', 'sqrt', 'squared', 'asinh', 'sinh',
            'histeq']
    
def get_dist(name):
    if not name in distributions:
        raise ColorDistError("Invalid distribution algorithm '%s'" % (name))
    return distributions[name]
    
#END
