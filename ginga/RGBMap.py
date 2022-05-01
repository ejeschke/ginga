#
# RGBMap.py -- color mapping
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import uuid
import numpy as np

from ginga.misc import Callback, Settings
from ginga import ColorDist, trcalc
from ginga import cmap as mod_cmap
from ginga import imap as mod_imap


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

    def get_array(self, order, dtype=None):
        """Get Numpy array that represents the RGB layers.

        Parameters
        ----------
        order : str
            The desired order of RGB color layers.

        Returns
        -------
        arr : ndarray
            Numpy array that represents the RGB layers.

        dtype : numpy array dtype (optional)
            Type of the numpy array desired.

        """
        if dtype is None:
            dtype = self.rgbarr.dtype
        order = order.upper()
        if order == self.order:
            return self.rgbarr.astype(dtype, copy=False)

        res = trcalc.reorder_image(order, self.rgbarr, self.order)
        res = res.astype(dtype, copy=False, casting='unsafe')

        return res

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

    def __init__(self, logger, dist=None, settings=None, bpp=None):
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.mapper_id = str(uuid.uuid4())

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.t_ = settings
        self.settings_keys = ['color_map', 'intensity_map',
                              'color_array', 'shift_array',
                              'color_algorithm', 'color_hashsize',
                              ]

        # add our defaults
        self.t_.add_defaults(color_map='gray', intensity_map='ramp',
                             color_algorithm='linear',
                             color_hashsize=65536,
                             color_array=None, shift_array=None)
        self.t_.get_setting('color_map').add_callback('set',
                                                      self.color_map_set_cb)
        self.t_.get_setting('intensity_map').add_callback('set',
                                                          self.intensity_map_set_cb)
        self.t_.get_setting('color_array').add_callback('set',
                                                        self.color_array_set_cb)
        self.t_.get_setting('shift_array').add_callback('set',
                                                        self.shift_array_set_cb)
        self.t_.get_setting('color_hashsize').add_callback('set',
                                                           self.color_hashsize_set_cb)
        self.t_.get_setting('color_algorithm').add_callback('set',
                                                            self.color_algorithm_set_cb)

        # For color and intensity maps
        self.cmap = None
        self.imap = None
        self.arr = None
        self.iarr = None
        self.carr = None
        self.sarr = None
        self.scale_pct = 1.0

        # targeted bit depth per-pixel band of the output RGB array
        # (can be less than the data size of the output array)
        if bpp is None:
            bpp = 8
        self.bpp = bpp
        # maximum value that we can generate in this range
        self.maxc = int(2 ** self.bpp - 1)
        # data size per pixel band in the output RGB array
        self._set_dtype()

        # For scaling algorithms
        hashsize = self.t_.get('color_hashsize', 65536)
        if dist is None:
            color_alg_name = self.t_.get('color_algorithm', 'linear')
            color_dist_class = ColorDist.get_dist(color_alg_name)
            dist = color_dist_class(hashsize)
        self.dist = dist

        # For callbacks
        for name in ('changed', ):
            self.enable_callback(name)

        self.suppress_changed = self.suppress_callback('changed', 'last')

        carr = self.t_.get('color_array', None)
        sarr = self.t_.get('shift_array', None)

        cm_name = self.t_.get('color_map', 'gray')
        self.set_color_map(cm_name)

        im_name = self.t_.get('intensity_map', 'ramp')
        self.set_intensity_map(im_name)

        # Initialize color array
        if carr is not None:
            self.set_carr(carr)
        else:
            self.calc_cmap()

        # Initialize shift array
        if sarr is not None:
            self.set_sarr(sarr)
        else:
            self.reset_sarr(callback=False)

    def _set_dtype(self):
        if self.bpp <= 8:
            self.dtype = np.dtype(np.uint8)
        elif self.bpp <= 16:
            self.dtype = np.dtype(np.uint16)
        else:
            self.dtype = np.dtype(np.uint32)

    def set_bpp(self, bpp):
        """
        Set the bit depth (per band) for the output.
        A typical "32-bit RGBA" image would be 8; a 48-bit image would
        be 16, etc.
        """
        self.bpp = bpp
        self.maxc = int(2 ** self.bpp - 1)
        self._set_dtype()
        self.calc_cmap()
        self.recalc(callback=False)

    def get_settings(self):
        return self.t_

    def set_color_map(self, cmap_name):
        self.t_.set(color_map=cmap_name)

    def color_map_set_cb(self, setting, cmap_name):
        cm = mod_cmap.get_cmap(cmap_name)
        self.set_cmap(cm, callback=True)

    def set_cmap(self, cmap, callback=True):
        """
        Set the color map used by this RGBMapper.

        `cmap` specifies a ColorMap object.  If `callback` is True, then
        any callbacks associated with this change will be invoked.
        """
        self.cmap = cmap
        with self.suppress_changed:
            self.calc_cmap()
            # TEMP: ignore passed callback parameter
            # callback=False in the following because we don't want to
            # recursively invoke set_cmap()
            self.t_.set(color_map=cmap.name, callback=False)

    def get_cmap(self):
        """
        Return the color map used by this RGBMapper.
        """
        return self.cmap

    def calc_cmap(self):
        clst = self.cmap.clst
        self.maxc = len(clst) - 1
        arr = np.array(clst).transpose() * float(self.maxc)
        # does this really need to be the same type as rgbmap output type?
        carr = np.round(arr).astype(self.dtype, copy=False)
        self.t_.set(color_array=carr)

    def invert_cmap(self, callback=True):
        carr = np.fliplr(self.carr)
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr)

    def rotate_cmap(self, num, callback=True):
        carr = np.roll(self.carr, num, axis=1)
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr)

    def restore_cmap(self, callback=True):
        with self.suppress_changed:
            self.reset_sarr(callback=False)
            # TEMP: ignore passed callback parameter
            self.calc_cmap()

    def reset_cmap(self):
        self.recalc()

    def get_rgb(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxc range associated
        mapped by the value of `index`.
        """
        index = int(index)
        return tuple(self.arr[index])

    def get_rgbval(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxc range associated
        mapped by the value of `index`.
        """
        index = int(index)
        assert (index >= 0) and (index <= self.maxc), \
            RGBMapError("Index must be in range 0-%d !" % (self.maxc))
        index = int(self.sarr[index].clip(0, self.maxc))
        return self.arr[index]

    def set_intensity_map(self, imap_name):
        self.t_.set(intensity_map=imap_name)

    def intensity_map_set_cb(self, setting, imap_name):
        im = mod_imap.get_imap(imap_name)
        self.set_imap(im, callback=True)

    def set_imap(self, imap, callback=True):
        """
        Set the intensity map used by this RGBMapper.

        `imap` specifies an IntensityMap object.  If `callback` is True, then
        any callbacks associated with this change will be invoked.
        """
        self.imap = imap
        self.calc_imap()
        with self.suppress_changed:
            # TEMP: ignore passed callback parameter
            self.recalc()
            # callback=False in the following because we don't want to
            # recursively invoke set_imap()
            self.t_.set(intensity_map=imap.name, callback=False)

    def get_imap(self):
        """
        Return the intensity map used by this RGBMapper.
        """
        return self.imap

    def calc_imap(self):
        arr = np.array(self.imap.ilst) * float(self.maxc)
        self.iarr = np.round(arr).astype(np.uint, copy=False)

    def reset_sarr(self, callback=True):
        maxlen = self.maxc + 1
        self.scale_pct = 1.0
        sarr = np.arange(maxlen)
        # TEMP: ignore passed callback parameter
        self.t_.set(shift_array=sarr)

    def get_sarr(self):
        return self.sarr

    def set_sarr(self, sarr, callback=True):
        if sarr is not None:
            sarr = np.asarray(sarr)
        # TEMP: ignore passed callback parameter
        self.t_.set(shift_array=sarr)

    def shift_array_set_cb(self, setting, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            maxlen = self.maxc + 1
            _len = len(sarr)
            if _len != maxlen:
                raise RGBMapError("shift map length %d != %d" % (_len, maxlen))
            self.sarr = sarr
            # NOTE: can't reset scale_pct here because it results in a
            # loop with e.g. scale_and_shift()
            #self.scale_pct = 1.0
            self.make_callback('changed')
        else:
            self.reset_sarr(callback=True)

    def get_carr(self):
        return self.carr

    def set_carr(self, carr, callback=True):
        if carr is not None:
            carr = np.asarray(carr)
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr, callback=True)

    def color_array_set_cb(self, setting, carr):
        if carr is not None:
            carr = np.asarray(carr).clip(0, self.maxc).astype(self.dtype)
            maxlen = self.maxc + 1
            self.carr = carr
            _len = carr.shape[1]
            if _len != maxlen:
                raise RGBMapError("color map length %d != %d" % (_len, maxlen))
        else:
            self.calc_cmap()
        self.recalc(callback=True)

    def recalc(self, callback=True):
        self.arr = np.copy(self.carr.T)
        # Apply intensity map to rearrange colors
        if self.iarr is not None:
            self.arr = self.arr[self.iarr]

        # NOTE: don't reset shift array
        #self.reset_sarr(callback=False)
        if callback:
            self.make_callback('changed')

    def get_hash_size(self):
        return self.dist.get_hash_size()

    def set_hash_size(self, size, callback=True):
        # TEMP: ignore passed callback parameter
        self.t_.set(color_hashsize=size)

    def color_hashsize_set_cb(self, setting, size):
        self.dist.set_hash_size(size)
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

    def set_hash_algorithm(self, name, callback=True, **kwargs):
        # TODO: deal with algorithm parameters in kwargs
        self.t_.set(color_algorithm=name)

    def set_color_algorithm(self, name):
        size = self.t_.get('color_hashsize', self.dist.get_hash_size())
        dist = ColorDist.get_dist(name)(size)
        self.set_dist(dist, callback=True)

    def color_algorithm_set_cb(self, setting, name):
        self.set_color_algorithm(name)

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [order.index(c) for c in cs]

    def _get_rgbarray(self, idx, rgbobj, image_order=''):
        # NOTE: data is assumed to be in the range 0-maxc at this point
        # but clip as a precaution
        # NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        # idx = idx.clip(0, self.maxc).astype(np.uint, copy=False)
        #idx.clip(0, self.maxc, out=idx)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # idx = self.sarr[idx].clip(0, self.maxc).astype(np.uint, copy=False)
        idx = self.sarr[idx]
        # TODO: I think we can avoid this operation, if shift array contents
        # can be limited to 0..maxc
        #idx.clip(0, self.maxc, out=idx)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        out = rgbobj.rgbarr

        # See NOTE [A]
        if (image_order is None) or (len(image_order) == 1):
            out[..., [ri, gi, bi]] = self.arr[idx]

        elif len(image_order) == 2:
            mj, aj = self.get_order_indexes(image_order, 'MA')
            out[..., [ri, gi, bi]] = self.arr[idx[..., mj]]

        else:
            # <== indexes already contain RGB info.
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            out[..., ri] = self.arr[:, 0][idx[..., rj]]
            out[..., gi] = self.arr[:, 1][idx[..., gj]]
            out[..., bi] = self.arr[:, 2][idx[..., bj]]

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
        t1 = time.time()
        # prepare output array
        shape = idx.shape
        depth = len(order)

        if (image_order is not None) and (len(image_order) > 1):
            # indexes contain RGB axis, so omit this
            res_shape = shape[:-1] + (depth, )
        else:
            res_shape = shape + (depth, )

        if out is None:
            out = np.empty(res_shape, dtype=self.dtype, order='C')
        else:
            # TODO: assertion check on shape of out
            if res_shape != out.shape:
                raise RGBMapError("Output array shape %s doesn't match result "
                                  "shape %s" % (str(out.shape), str(res_shape)))

        res = RGBPlanes(out, order)

        # set alpha channel
        if res.hasAlpha:
            aa = res.get_slice('A')
            aa.fill(self.maxc)

        t2 = time.time()
        idx = self.get_hasharray(idx)

        t3 = time.time()
        self._get_rgbarray(idx, res, image_order=image_order)

        t4 = time.time()
        self.logger.debug("rgbmap: t2=%.4f t3=%.4f t4=%.4f total=%.4f" % (
            t2 - t1, t3 - t2, t4 - t3, t4 - t1))
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

        xi = (xi * iscale_x).astype(np.uint, copy=False)
        xi = xi.clip(0, old_wd - 1).astype(np.uint, copy=False)
        newdata = sarr[xi]
        return newdata

    def shift(self, pct, rotate=False, callback=True):
        work = self._shift(self.sarr, pct, rotate=rotate)
        maxlen = self.maxc + 1
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)
        self.t_.set(shift_array=work)

    def scale_and_shift(self, scale_pct, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        maxlen = self.maxc + 1
        self.sarr = np.arange(maxlen)

        # limit shrinkage to 5% of original size
        scale = max(scale_pct, 0.050)
        self.scale_pct = scale

        work = self._stretch(self.sarr, scale)
        n = len(work)
        if n < maxlen:
            # pad on the lowest and highest values of the shift map
            m = (maxlen - n) // 2 + 1
            barr = np.array([0] * m)
            tarr = np.array([self.maxc] * m)
            work = np.concatenate([barr, work, tarr])
            work = work[:maxlen]

        # we are mimicing ds9's stretch and shift algorithm here.
        # ds9 seems to cut the center out of the stretched array
        # BEFORE shifting
        n = len(work) // 2
        halflen = maxlen // 2
        work = work[n - halflen:n + halflen].astype(np.uint, copy=False)
        assert len(work) == maxlen, \
            RGBMapError("scaled shift map is != %d" % maxlen)

        # shift map according to the shift_pct
        work = self._shift(work, shift_pct)
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)

        self.t_.set(shift_array=work)

    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        self.scale_pct *= scale_factor
        self.scale_and_shift(self.scale_pct, 0.0, callback=callback)

    def copy_attributes(self, dst_rgbmap, keylist=None):
        if keylist is None:
            keylist = self.settings_keys
        self.t_.copy_settings(dst_rgbmap.get_settings(), keylist=keylist)

    def share_attributes(self, dst_rgbmap, keylist=None):
        if keylist is None:
            keylist = self.settings_keys
        self.t_.share_settings(dst_rgbmap.get_settings(), keylist=keylist)


class NonColorMapper(RGBMapper):
    """
    A kind of color mapper for data that is already in RGB form.

    This mapper allows changing of color distribution and contrast
    adjustment, but does no coloring.
    """
    def __init__(self, logger, dist=None, bpp=None):
        super(NonColorMapper, self).__init__(logger, dist=dist, bpp=bpp)

        maxlen = self.maxc + 1
        self.dist.set_hash_size(maxlen)
        self.reset_sarr(callback=False)

    def _get_rgbarray(self, idx, rgbobj, image_order='RGB'):
        # NOTE: data is assumed to be in the range 0-maxc at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        #idx.clip(0, self.maxc, out=idx)

        # run it through the shift array and clip the result
        # See NOTE [A]
        idx = self.sarr[idx]
        #idx.clip(0, self.maxc, out=idx)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
        out = rgbobj.rgbarr

        out[..., [ri, gi, bi]] = idx[..., [rj, gj, bj]]


class PassThruRGBMapper(RGBMapper):
    """
    A kind of color mapper for data that is already in RGB form.

    This mapper bypasses color distribution, contrast adjustment and
    coloring.  It is thus the most efficient one to use for maximum
    speed rendering of "finished" RGB data.
    """
    def __init__(self, logger, dist=None, bpp=None):
        super(PassThruRGBMapper, self).__init__(logger, bpp=bpp)

        # ignore passed in distribution
        maxlen = self.maxc + 1
        self.dist = ColorDist.LinearDist(maxlen)

    def get_hasharray(self, idx):
        # data is already constrained to 0..maxc and we want to
        # bypass color redistribution
        return idx

    def _get_rgbarray(self, idx, rgbobj, image_order='RGB'):
        # NOTE: data is assumed to be in the range 0-maxc at this point
        # but clip as a precaution
        # See NOTE [A]: idx is always an array calculated in the caller and
        #    discarded afterwards
        ## idx.clip(0, self.maxc, out=idx)

        # bypass the shift array and skip color mapping,
        # index is the final data
        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
        out = rgbobj.rgbarr

        out[..., [ri, gi, bi]] = idx[..., [rj, gj, bj]]


#END
