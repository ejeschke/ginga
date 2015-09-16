#
# RGBMap.py -- color mapping
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math
import numpy

from ginga.misc import Callback
from ginga import ColorDist


class RGBMapError(Exception):
    pass

class RGBPlanes(object):

    def __init__(self, rgbarr, order):
        self.rgbarr = rgbarr
        order = order.upper()
        self.order = order
        self.hasAlpha = 'A' in order

    def get_slice(self, ch):
        return self.rgbarr[..., self.order.index(ch.upper())]

    def has_slice(self, ch):
        return ch.upper() in self.order

    def get_order(self):
        return self.order

    def get_order_indexes(self, cs):
        cs = cs.upper()
        return [ self.order.index(c) for c in cs ]

    def get_array(self, order):
        order = order.upper()
        if order == self.order:
            return self.rgbarr
        l = [ self.get_slice(c) for c in order ]
        return numpy.dstack(l)

    def get_size(self):
        """Returns (height, width) tuple of slice size."""
        return self.get_slice('R').shape

class RGBMapper(Callback.Callbacks):

    ############################################################
    # CODE NOTES
    #
    # [A] Some numpy routines have been optomized by using the out=
    # parameter, which avoids having to allocate a new array for the
    # result
    #

    def __init__(self, logger, dist=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger

        # For color and intensity maps
        self.cmap = None
        self.imap = None
        self.arr = None
        self.iarr = None
        self.carr = None
        self.sarr = None
        self.scale_pct = 1.0

        # For scaling algorithms
        hashsize = 65536
        if dist is None:
            dist = ColorDist.LinearDist(hashsize)
        self.dist = dist

        # For callbacks
        for name in ('changed', ):
            self.enable_callback(name)

    def set_cmap(self, cmap, callback=True):
        """
        Set the color map used by this RGBMapper.

        `cmap` specifies a ColorMap object.  If `callback` is True, then
        any callbacks associated with this change will be invoked.
        """
        self.cmap = cmap
        self.calc_cmap()
        self.recalc(callback=callback)

    def get_cmap(self):
        """
        Return the color map used by this RGBMapper.
        """
        return self.cmap

    def calc_cmap(self):
        clst = self.cmap.clst
        arr = numpy.array(clst).transpose() * 255.0
        #self.carr = arr.astype('uint8')
        self.carr = numpy.round(arr).astype('uint8')

    def get_rgb(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-255 range associated
        mapped by the value of `index`.
        """
        return tuple(self.arr[index])

    def get_rgbval(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-255 range associated
        mapped by the value of `index`.
        """
        assert (index >= 0) and (index < 256), \
               RGBMapError("Index must be in range 0-255 !")
        index = self.sarr[index].clip(0, 255)
        return (self.arr[0][index],
                self.arr[1][index],
                self.arr[2][index])

    def set_imap(self, imap, callback=True):
        """
        Set the intensity map used by this RGBMapper.

        `imap` specifies an IntensityMap object.  If `callback` is True, then
        any callbacks associated with this change will be invoked.
        """
        self.imap = imap
        self.calc_imap()
        self.recalc(callback=callback)

    def get_imap(self):
        """
        Return the intensity map used by this RGBMapper.
        """
        return self.imap

    def calc_imap(self):
        arr = numpy.array(self.imap.ilst) * 255.0
        self.iarr = numpy.round(arr).astype('uint')

    def reset_sarr(self, callback=True):
        self.sarr = numpy.arange(256)
        self.scale_pct = 1.0
        if callback:
            self.make_callback('changed')

    def set_sarr(self, sarr, callback=True):
        assert len(sarr) == 256, \
               RGBMapError("shift map length %d != 256" % (len(sarr)))
        self.sarr = sarr.astype('uint')
        self.scale_pct = 1.0

        if callback:
            self.make_callback('changed')

    def get_sarr(self):
        return self.sarr

    def recalc(self, callback=True):
        self.arr = numpy.copy(self.carr)
        # Apply intensity map to rearrange colors
        if self.iarr is not None:
            idx = self.iarr
            self.arr[0] = self.arr[0][idx]
            self.arr[1] = self.arr[1][idx]
            self.arr[2] = self.arr[2][idx]

        self.reset_sarr(callback=callback)

    def get_hash_size(self):
        return self.dist.get_hash_size()

    def set_hash_size(self, size, callback=True):
        self.dist.set_hash_size(size)
        if callback:
            self.make_callback('changed')

    def get_hash_algorithms(self):
        return ColorDist.get_dist_names()

    def get_hash_algorithm(self):
        return str(self.dist)

    def get_dist(self):
        """
        Return the color distribution used by this RGBMapper.
        """
        return self.dist

    def set_dist(self, dist, callback=True):
        self.dist = dist
        if callback:
            self.make_callback('changed')

    def set_hash_algorithm(self, name, callback=True, **kwdargs):
        hashsize = self.dist.get_hash_size()
        dist = ColorDist.get_dist(name)(hashsize, **kwdargs)
        self.set_dist(dist, callback=callback)

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [ order.index(c) for c in cs ]

    def _get_rgbarray(self, idx, rgbobj, image_order):
        # NOTE: data is assumed to be in the range 0-255 at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        # idx = idx.clip(0, 255)
        idx.clip(0, 255, out=idx)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # idx = self.sarr[idx].clip(0, 255)
        idx = self.sarr[idx]
        idx.clip(0, 255, out=idx)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        out = rgbobj.rgbarr

        if len(idx.shape) == 2:
            out[..., ri] = self.arr[0][idx]
            out[..., gi] = self.arr[1][idx]
            out[..., bi] = self.arr[2][idx]
        else:
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            out[..., ri] = self.arr[0][idx[..., rj]]
            out[..., gi] = self.arr[1][idx[..., gj]]
            out[..., bi] = self.arr[2][idx[..., bj]]

    def get_rgbarray(self, idx, out=None, order='RGB', image_order='RGB'):
        # prepare output array
        shape = idx.shape
        depth = len(order)
        res_shape = (shape[0], shape[1], depth)
        if out is None:
            out = numpy.empty(res_shape, dtype=numpy.uint8, order='C')
        else:
            # TODO: assertion check on shape of out
            assert res_shape == out.shape, \
                   RGBMapError("Output array shape %s doesn't match result shape %s" % (
                str(out.shape), str(res_shape)))

        res = RGBPlanes(out, order)

        # set alpha channel
        if res.hasAlpha:
            aa = res.get_slice('A')
            aa.fill(255)

        idx = self.get_hasharray(idx)

        self._get_rgbarray(idx, res, image_order)

        return res

    def get_hasharray(self, idx):
        return self.dist.hash_array(idx)

    def _shift(self, sarr, pct, rotate=False):
        n = len(sarr)
        num = int(n * pct)
        arr = numpy.roll(sarr, num)
        if not rotate:
            if num > 0:
                arr[0:num] = sarr[0]
            elif num < 0:
                arr[n+num:n] = sarr[-1]
        return arr

    def _stretch(self, sarr, scale):
        old_wd = len(sarr)
        new_wd = int(round(scale * old_wd))

        # Is there a more efficient way to do this?
        xi = numpy.mgrid[0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)

        xi *= iscale_x
        xi = xi.astype('int').clip(0, old_wd-1)
        newdata = sarr[xi]
        return newdata

    def shift(self, pct, rotate=False, callback=True):
        work = self._shift(self.sarr, pct, rotate=rotate)
        assert len(work) == 256, \
               RGBMapError("shifted shift map is != 256")
        self.sarr = work
        if callback:
            self.make_callback('changed')

    def scale_and_shift(self, scale_pct, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        self.sarr = numpy.arange(256)

        #print "amount=%.2f location=%.2f" % (scale_pct, shift_pct)
        # limit shrinkage to 5% of original size
        scale = max(scale_pct, 0.050)
        self.scale_pct = scale

        work = self._stretch(self.sarr, scale)
        n = len(work)
        if n < 256:
            # pad on the lowest and highest values of the shift map
            m = (256 - n) // 2 + 1
            barr = numpy.array([0]*m)
            tarr = numpy.array([255]*m)
            work = numpy.concatenate([barr, work, tarr])
            work = work[:256]

        # we are mimicing ds9's stretch and shift algorithm here.
        # ds9 seems to cut the center out of the stretched array
        # BEFORE shifting
        n = len(work) // 2
        work = work[n-128:n+128].astype('uint')
        assert len(work) == 256, \
               RGBMapError("scaled shift map is != 256")

        # shift map according to the shift_pct
        work = self._shift(work, shift_pct)
        assert len(work) == 256, \
               RGBMapError("shifted shift map is != 256")

        self.sarr = work
        if callback:
            self.make_callback('changed')


    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        self.scale_pct *= scale_factor
        self.scale_and_shift(self.scale_pct, 0.0, callback=callback)

    def copy_attributes(self, dst_rgbmap):
        dst_rgbmap.set_cmap(self.cmap)
        dst_rgbmap.set_imap(self.imap)
        dst_rgbmap.set_hash_algorithm(str(self.dist))

    def reset_cmap(self):
        self.recalc()


class PassThruRGBMapper(RGBMapper):

    def __init__(self, logger, dist=None):
        super(PassThruRGBMapper, self).__init__(logger)

        # ignore passed in distribution
        self.dist = ColorDist.LinearDist(256)

    def get_rgbarray(self, idx, out=None, order='RGB', image_order='RGB'):
        # prepare output array
        shape = idx.shape
        depth = len(order)
        res_shape = (shape[0], shape[1], depth)
        if out is None:
            out = numpy.empty(res_shape, dtype=numpy.uint8, order='C')
        else:
            # TODO: assertion check on shape of out
            assert res_shape == out.shape, \
                   RGBMapError("Output array shape %s doesn't match result shape %s" % (
                str(out.shape), str(res_shape)))

        res = RGBPlanes(out, order)

        # set alpha channel
        if res.hasAlpha:
            aa = res.get_slice('A')
            aa.fill(255)

        # skip color mapping, index is the final data
        ri, gi, bi = self.get_order_indexes(res.get_order(), 'RGB')
        rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
        out[..., ri] = idx[..., rj]
        out[..., gi] = idx[..., gj]
        out[..., bi] = idx[..., bj]

        return res


#END
