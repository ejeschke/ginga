#
# RGBMap.py -- color mapping
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

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
        return [self.order.index(c) for c in cs]

    def get_array(self, order):
        """Get Numpy array that represents the RGB layers.

        Parameters
        ----------
        order : str
            The desired order of RGB color layers.

        Returns
        -------
        arr : ndarray
            Numpy array that represents the RGB layers.

        """
        order = order.upper()
        if order == self.order:
            return self.rgbarr
        l = [self.get_slice(c) for c in order]
        return np.concatenate([arr[..., np.newaxis]
                               for arr in l], axis=-1)

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
        self.maxv = 255
        self.nptype = np.uint8

        # For scaling algorithms
        hashsize = 65536
        if dist is None:
            dist = ColorDist.LinearDist(hashsize)
        self.dist = dist

        self.reset_sarr(callback=False)

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
        arr = np.array(clst).transpose() * float(self.maxv)
        self.carr = np.round(arr).astype(self.nptype)

    def invert_cmap(self, callback=True):
        self.carr = np.fliplr(self.carr)
        self.recalc(callback=callback)

    def rotate_cmap(self, num, callback=True):
        self.carr = np.roll(self.carr, num, axis=1)
        self.recalc(callback=callback)

    def restore_cmap(self, callback=True):
        self.reset_sarr(callback=False)
        self.calc_cmap()
        self.recalc(callback=callback)

    def get_rgb(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxv range associated
        mapped by the value of `index`.
        """
        return tuple(self.arr[index])

    def get_rgbval(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxv range associated
        mapped by the value of `index`.
        """
        assert (index >= 0) and (index <= self.maxv), \
            RGBMapError("Index must be in range 0-%d !" % (self.maxv))
        index = self.sarr[index].clip(0, self.maxv)
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
        arr = np.array(self.imap.ilst) * float(self.maxv)
        self.iarr = np.round(arr).astype(np.uint)

    def reset_sarr(self, callback=True):
        maxlen = self.maxv + 1
        self.sarr = np.arange(maxlen)
        self.scale_pct = 1.0
        if callback:
            self.make_callback('changed')

    def set_sarr(self, sarr, callback=True):
        maxlen = self.maxv + 1
        assert len(sarr) == maxlen, \
            RGBMapError("shift map length %d != %d" % (len(sarr), maxlen))
        self.sarr = sarr.astype(np.uint)
        self.scale_pct = 1.0

        if callback:
            self.make_callback('changed')

    def get_sarr(self):
        return self.sarr

    def recalc(self, callback=True):
        self.arr = np.copy(self.carr)
        # Apply intensity map to rearrange colors
        if self.iarr is not None:
            idx = self.iarr
            self.arr[0] = self.arr[0][idx]
            self.arr[1] = self.arr[1][idx]
            self.arr[2] = self.arr[2][idx]

        # NOTE: don't reset shift array
        #self.reset_sarr(callback=False)
        if callback:
            self.make_callback('changed')

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
        return [order.index(c) for c in cs]

    def _get_rgbarray(self, idx, rgbobj, image_order=''):
        # NOTE: data is assumed to be in the range 0-maxv at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        # idx = idx.clip(0, self.maxv)
        idx.clip(0, self.maxv, out=idx)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # idx = self.sarr[idx].clip(0, self.maxv)
        idx = self.sarr[idx]
        idx.clip(0, self.maxv, out=idx)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        out = rgbobj.rgbarr

        # change [A]
        if (image_order is None) or (len(image_order) < 3):
            out[..., ri] = self.arr[0][idx]
            out[..., gi] = self.arr[1][idx]
            out[..., bi] = self.arr[2][idx]
        else:
            # <== indexes already contain RGB info.
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            out[..., ri] = self.arr[0][idx[..., rj]]
            out[..., gi] = self.arr[1][idx[..., gj]]
            out[..., bi] = self.arr[2][idx[..., bj]]

    def get_rgbarray(self, idx, out=None, order='RGB', image_order=''):
        """
        Parameters
        ----------
        idx : index array

        out : output array or None
            The output array.  If `None` one of the correct size and depth
            will be created.

        order : str
            The order of the color planes in the output array (e.g. "ARGB")

        image_order : str or None
            The order of channels if indexes already contain RGB info.
        """
        # prepare output array
        shape = idx.shape
        depth = len(order)

        if (image_order is not None) and (len(image_order) > 1):
            # indexes contain RGB axis, so omit this
            res_shape = shape[:-1] + (depth, )
        else:
            res_shape = shape + (depth, )

        if out is None:
            out = np.empty(res_shape, dtype=self.nptype, order='C')
        else:
            # TODO: assertion check on shape of out
            assert res_shape == out.shape, \
                RGBMapError("Output array shape %s doesn't match result "
                            "shape %s" % (str(out.shape), str(res_shape)))

        res = RGBPlanes(out, order)

        # set alpha channel
        if res.hasAlpha:
            aa = res.get_slice('A')
            aa.fill(self.maxv)

        idx = self.get_hasharray(idx)

        self._get_rgbarray(idx, res, image_order=image_order)

        return res

    def get_hasharray(self, idx):
        return self.dist.hash_array(idx)

    def _shift(self, sarr, pct, rotate=False):
        n = len(sarr)
        num = int(n * pct)
        arr = np.roll(sarr, num)
        if not rotate:
            if num > 0:
                arr[0:num] = sarr[0]
            elif num < 0:
                arr[n + num:n] = sarr[-1]
        return arr

    def _stretch(self, sarr, scale):
        old_wd = len(sarr)
        new_wd = int(round(scale * old_wd))

        # Is there a more efficient way to do this?
        xi = np.mgrid[0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)

        xi = (xi * iscale_x).astype('int')
        xi = xi.clip(0, old_wd - 1)
        newdata = sarr[xi]
        return newdata

    def shift(self, pct, rotate=False, callback=True):
        work = self._shift(self.sarr, pct, rotate=rotate)
        maxlen = self.maxv + 1
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)
        self.sarr = work
        if callback:
            self.make_callback('changed')

    def scale_and_shift(self, scale_pct, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        maxlen = self.maxv + 1
        self.sarr = np.arange(maxlen)

        #print "amount=%.2f location=%.2f" % (scale_pct, shift_pct)
        # limit shrinkage to 5% of original size
        scale = max(scale_pct, 0.050)
        self.scale_pct = scale

        work = self._stretch(self.sarr, scale)
        n = len(work)
        if n < maxlen:
            # pad on the lowest and highest values of the shift map
            m = (maxlen - n) // 2 + 1
            barr = np.array([0] * m)
            tarr = np.array([self.maxv] * m)
            work = np.concatenate([barr, work, tarr])
            work = work[:maxlen]

        # we are mimicing ds9's stretch and shift algorithm here.
        # ds9 seems to cut the center out of the stretched array
        # BEFORE shifting
        n = len(work) // 2
        halflen = maxlen // 2
        work = work[n - halflen:n + halflen].astype(np.uint)
        assert len(work) == maxlen, \
            RGBMapError("scaled shift map is != %d" % maxlen)

        # shift map according to the shift_pct
        work = self._shift(work, shift_pct)
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)

        self.sarr = work
        if callback:
            self.make_callback('changed')

    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        self.scale_pct *= scale_factor
        self.scale_and_shift(self.scale_pct, 0.0, callback=callback)

    def copy_attributes(self, dst_rgbmap):
        dst_rgbmap.set_cmap(self.cmap, callback=False)
        dst_rgbmap.set_imap(self.imap, callback=False)
        dst_rgbmap.set_hash_algorithm(str(self.dist), callback=False)
        # TODO: set hash size
        dst_rgbmap.carr = np.copy(self.carr)
        dst_rgbmap.sarr = np.copy(self.sarr)
        dst_rgbmap.recalc()

    def reset_cmap(self):
        self.recalc()


class NonColorMapper(RGBMapper):
    """
    A kind of color mapper for data that is already in RGB form.

    This mapper allows changing of color distribution and contrast
    adjustment, but does no coloring.
    """
    def __init__(self, logger, dist=None):
        super(NonColorMapper, self).__init__(logger)

        maxlen = self.maxv + 1
        self.dist.set_hash_size(maxlen)
        self.reset_sarr(callback=False)

    def _get_rgbarray(self, idx, rgbobj, image_order='RGB'):
        # NOTE: data is assumed to be in the range 0-maxv at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        idx.clip(0, self.maxv, out=idx)

        # run it through the shift array and clip the result
        # See NOTE [A]
        idx = self.sarr[idx]
        idx.clip(0, self.maxv, out=idx)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
        out = rgbobj.rgbarr

        out[..., ri] = idx[..., rj]
        out[..., gi] = idx[..., gj]
        out[..., bi] = idx[..., bj]


class PassThruRGBMapper(RGBMapper):
    """
    A kind of color mapper for data that is already in RGB form.

    This mapper bypasses color distribution, contrast adjustment and
    coloring.  It is thus the most efficient one to use for maximum
    speed rendering of "finished" RGB data.
    """
    def __init__(self, logger, dist=None):
        super(PassThruRGBMapper, self).__init__(logger)

        # ignore passed in distribution
        maxlen = self.maxv + 1
        self.dist = ColorDist.LinearDist(maxlen)

    def get_hasharray(self, idx):
        # data is already constrained to 0..maxv and we want to
        # bypass color redistribution
        return idx

    def _get_rgbarray(self, idx, rgbobj, image_order='RGB'):
        # NOTE: data is assumed to be in the range 0-maxv at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        idx.clip(0, self.maxv, out=idx)

        # bypass the shift array and skip color mapping,
        # index is the final data
        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
        out = rgbobj.rgbarr

        out[..., ri] = idx[..., rj]
        out[..., gi] = idx[..., gj]
        out[..., bi] = idx[..., bj]

#END
