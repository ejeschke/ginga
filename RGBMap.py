#
# RGBMap.py -- color mapping
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Tue Aug 28 10:43:42 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

import Callback

class RGBMapError(Exception):
    pass

class RGBMapper(Callback.Callbacks):

    def __init__(self):
        Callback.Callbacks.__init__(self)

        # For color and intensity maps
        self.cmap = None
        self.imap = None
        self.arr = None

        # For color scale algorithms
        self.hashalgs = { 'linear': self.calc_linear_hash,
                          'logarithmic': self.calc_logarithmic_hash,
                          'exponential': self.calc_exponential_hash,
                          }
        self.hashalg = 'linear'
        self.maxhashsize = 1024*1024
        self.hashsize = 65536
        self.expo = 10.0
        self.calc_hash()

        # For callbacks
        for name in ('changed', ):
            self.enable_callback(name)

    def set_cmap(self, cmap, callback=True):
        self.cmap = cmap
        self.calc_cmap()
        if callback:
            self.make_callback('changed')

    def get_cmap(self):
        return self.cmap
    
    def calc_cmap(self):
        clst = self.cmap.clst
        arr = numpy.array(clst).transpose() * 255.0
        self.arr = arr.astype('uint8')
        self.calc_imap()

    def get_rgb(self, index):
        return tuple(self.arr[index])

    def get_rgbval(self, index):
        return (self.arr[0][index],
                self.arr[1][index],
                self.arr[2][index])

    def set_imap(self, imap, callback=True):
        self.imap = imap
        # Reset colormap (TODO: we shouldn't have to do this?)
        self.calc_cmap()
        #self.calc_imap()
        if callback:
            self.make_callback('changed')

    def get_imap(self):
        return self.imap
    
    def calc_imap(self):
        if self.imap != None:
            # Apply intensity map to rearrange colors
            idx = self.imap.arr
            self.arr[0] = self.arr[0][idx]
            self.arr[1] = self.arr[1][idx]
            self.arr[2] = self.arr[2][idx]
        
    def get_hash_size(self):
        return self.hashsize

    def set_hash_size(self, size, callback=True):
        assert (size > 255) and (size <= self.maxhashsize), \
               RGBMapError("Bad hash size!")
        self.hashsize = size
        self.calc_hash()
        if callback:
            self.make_callback('changed')
    
    def get_hash_algorithms(self):
        return self.hashalgs.keys()
    
    def get_hash_algorithm(self):
        return self.hashalg
    
    def set_hash_algorithm(self, name, callback=True):
        if not name in self.hashalgs.keys():
            raise ColorMapError("Invalid hash algorithm '%s'" % (name))
        self.hashalg = name
        self.calc_hash()
        if callback:
            self.make_callback('changed')
    
    def _get_rgbarray(self, idx):
        # NOTE: data is assumed to be in the range 0-255 at this point
        # but clip as a precaution
        idx = idx.clip(0, 255)
        ar = self.arr[0][idx]
        ag = self.arr[1][idx]
        ab = self.arr[2][idx]
        arr = numpy.dstack((ar, ag, ab))
        return arr
        
    def _get_rgbarray_rgb(self, idx_r, idx_g, idx_b):
        # NOTE: data is assumed to be in the range 0-255 at this point
        # but clip as a precaution
        idx_r = idx_r.clip(0, 255)
        ar = self.arr[0][idx_r]
        idx_g = idx_g.clip(0, 255)
        ag = self.arr[1][idx_g]
        idx_b = idx_b.clip(0, 255)
        ab = self.arr[2][idx_b]
        arr = numpy.dstack((ar, ag, ab))
        return arr

    def get_rgbarray(self, idx):
        shape = idx.shape
        if len(shape) == 2:
            # 2D monochrome image
            idx = self.get_hasharray(idx)
            arr = self._get_rgbarray(idx)
        elif len(shape) == 3:
            # Assume 2D color image
            assert shape[2] in (3, 4), \
                   RGBMapError("Number of color channels != 3")
            idx_r = self.get_hasharray(idx[:, :, 0])
            idx_g = self.get_hasharray(idx[:, :, 1])
            idx_b = self.get_hasharray(idx[:, :, 2])
            # alpha channel is usually 3
            arr = self._get_rgbarray_rgb(idx_r, idx_g, idx_b)
            
        return arr
        
    def get_hasharray(self, idx):
        # NOTE: data is assumed to be in the range 0-hashsize at this point
        # but clip as a precaution
        idx = idx.clip(0, self.hashsize)
        arr = self.hash[idx]
        return arr
        
    def rshift(self, pct, callback=True):
        self.calc_cmap()
        pct = 1.0 - pct
        num = int(255.0 * pct)
        pfx = self.arr.transpose()
        #print "len1=%d" % (len(pfx))
        pfx = pfx[:num]
        #print "n=%d len2=%d" % (num, len(pfx))
        zarr = numpy.ones(len(pfx))
        zarr[0] = 257 - num
        pfx = pfx.repeat(list(zarr), axis=0)
        #print "len3=%d" % len(pfx)
        self.arr = pfx.transpose()
        if callback:
            self.make_callback('changed')
            
    def lshift(self, pct, callback=True):
        self.calc_cmap()
        num = int(255.0 * pct)
        pfx = self.arr.transpose()
        #print "len1=%d" % (len(pfx))
        pfx = pfx[num:]
        #print "n=%d len2=%d" % (num, len(pfx))
        zarr = numpy.ones(len(pfx))
        zarr[-1] = num+1
        #print "len(zarr)=%d" % (len(zarr))
        pfx = pfx.repeat(list(zarr), axis=0)
        #print "len3=%d" % len(pfx)
        self.arr = pfx.transpose()
        if callback:
            self.make_callback('changed')
    
    # Color scale distribution algorithms are all based on similar
    # algorithms in skycat
    
    def calc_linear_hash(self):
        l = []
        step = int(round(self.hashsize / 256.0))
        for i in xrange(int(self.hashsize / step) + 1):
            l.extend([i]*step)
        l = l[:self.hashsize]
        self.hash = numpy.array(l)
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
               ColorMapError("Computed hash table size (%d) != specified size (%d)" % (hashlen, self.hashsize))
            

    def calc_logarithmic_hash(self):
        if self.expo >= 0:
            scale = float(self.hashsize) / (math.exp(self.expo) - 1.0)
        else:
            scale = float(self.hashsize) / (1.0 - math.exp(self.expo))

        l = []
        prevstep = 0
        for i in xrange(256+1):
            if self.expo > 0:
                step = int(((math.exp((float(i) / 256.0) * self.expo) - 1.0) * scale) + 0.5)
            else:
                step = int((1.0 - math.exp((float(i) / 256.0) * self.expo) * scale) + 0.5)
            #print "step is %d delta=%d" % (step, step-prevstep)
            l.extend([i] * (step - prevstep))
            prevstep = step
        #print "length of l=%d" % (len(l))
        l = l[:self.hashsize]
        self.hash = numpy.array(l)
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
               ColorMapError("Computed hash table size (%d) != specified size (%d)" % (hashlen, self.hashsize))

    def calc_exponential_hash(self):
        l = []
        prevstep = 0
        for i in xrange(256+1):
            step = int((math.pow((float(i) / 256.0), self.expo) * self.hashsize) + 0.5)
            #print "step is %d delta=%d" % (step, step-prevstep)
            l.extend([i] * (step - prevstep))
            prevstep = step
        #print "length of l=%d" % (len(l))
        l = l[:self.hashsize]
        self.hash = numpy.array(l)
        hashlen = len(self.hash)
        assert hashlen == self.hashsize, \
               ColorMapError("Computed hash table size (%d) != specified size (%d)" % (hashlen, self.hashsize))

    def calc_hash(self):
        method = self.hashalgs[self.hashalg]
        method()

    def copy_attributes(self, dst_rgbmap):
        dst_rgbmap.set_cmap(self.cmap)
        dst_rgbmap.set_imap(self.imap)
        dst_rgbmap.set_hash_algorithm(self.hashalg)

    def reset_cmap(self):
        self.set_cmap(self.cmap)
        
#END
