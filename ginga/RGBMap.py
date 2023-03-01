#
# RGBMap.py -- color mapping
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import uuid
import numpy as np

from ginga.misc import Callback, Settings, Bunch
from ginga import ColorDist, trcalc
from ginga import cmap as mod_cmap
from ginga import imap as mod_imap
from ginga.util import pipeline
from ginga.util.stages.base import Stage, StageError


class RGBMapError(StageError):
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

        # For color and intensity maps
        self.cmap = None
        self.imap = None

        # targeted bit depth per-pixel band of the output RGB array
        # (can be less than the data size of the output array)
        if bpp is None:
            bpp = 8
        self.set_bpp(bpp)

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
                             color_hashsize=self.maxc + 1,
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

    def set_bpp(self, bpp):
        """
        Set the bit depth (per band) for the output.
        A typical "32-bit RGBA" image would be 8; a 48-bit image would
        be 16, etc.
        """
        self.bpp = bpp
        self.maxc = int(2 ** self.bpp - 1)

        self.create_pipeline()

        self.refresh_cache()

    def create_pipeline(self):
        # create RGB mapping pipeline
        self.p_input = RGBInput(bpp=self.bpp)
        self.p_dist = Distribute(bpp=self.bpp)
        self.p_shift = ShiftMap(bpp=self.bpp)
        self.p_imap = IntensityMap(bpp=self.bpp)
        self.p_cmap = ColorMap(bpp=self.bpp)

        stages = [self.p_input,
                  self.p_dist,
                  self.p_shift,
                  self.p_imap,
                  self.p_cmap,
                  ]
        self.pipeline = pipeline.Pipeline(self.logger, stages)
        self.pipeline.name = 'rgb-mapper'

        # TODO: get from upper pipeline
        state = Bunch.Bunch(order='RGBA')
        self.pipeline.set(state=state)

        self.refresh_cache()

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
        self.p_cmap.set_cmap(self.cmap)
        carr = self.p_cmap.get_carr()
        self.t_.set(color_array=carr)

    def invert_cmap(self, callback=True):
        self.p_cmap.invert_cmap()
        carr = self.p_cmap.get_carr()
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr)

    def rotate_cmap(self, num, callback=True):
        self.p_cmap.rotate_cmap(num)
        carr = self.p_cmap.get_carr()
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr)

    def restore_cmap(self, callback=True):
        with self.suppress_changed:
            self.reset_sarr(callback=False)
            self.calc_cmap()
            # TEMP: ignore passed callback parameter

    def reset_cmap(self):
        self.p_cmap.reset_cmap()
        self.recalc()

    def get_rgb(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxc range associated
        mapped by the value of `index`.
        """
        index = int(index)
        assert (index >= 0) and (index <= self.maxc), \
            RGBMapError("Index must be in range 0-%d !" % (self.maxc))
        return tuple(self.cache_arr[index])

    def get_rgbval(self, index):
        """
        Return a tuple of (R, G, B) values in the 0-maxc range associated
        mapped by the value of `index`.
        """
        index = int(index)
        assert (index >= 0) and (index <= self.maxc), \
            RGBMapError("Index must be in range 0-%d !" % (self.maxc))
        return self.cache_arr[index]

    def get_colors(self):
        return self.cache_arr

    def get_colors(self):
        idx = np.arange(0, self.maxc + 1, dtype=np.uint)
        return self.arr[self.sarr[idx]]

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
            self.recalc(callback=callback)
            # callback=False in the following because we don't want to
            # recursively invoke set_imap()
            self.t_.set(intensity_map=imap.name, callback=False)

    def get_imap(self):
        """
        Return the intensity map used by this RGBMapper.
        """
        return self.imap

    def calc_imap(self):
        self.p_imap.set_imap(self.imap)
        self.refresh_cache()

    def reset_sarr(self, callback=True):
        self.p_shift.reset_sarr()
        sarr = self.p_shift.get_sarr()
        self.t_.set(shift_array=sarr)

    def get_sarr(self):
        sarr = self.p_shift.get_sarr()
        return sarr

    def set_sarr(self, sarr, callback=True):
        if sarr is not None:
            sarr = np.asarray(sarr)
        # TEMP: ignore passed callback parameter
        self.t_.set(shift_array=sarr)

    def shift_array_set_cb(self, setting, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            self.p_shift.set_sarr(sarr)
            self.refresh_cache()
        self.make_callback('changed')

    def get_carr(self):
        return self.p_cmap.get_carr()

    def set_carr(self, carr, callback=True):
        if carr is not None:
            carr = np.asarray(carr)
        # TEMP: ignore passed callback parameter
        self.t_.set(color_array=carr, callback=True)

    def color_array_set_cb(self, setting, carr):
        self.p_cmap.set_carr(carr)
        self.refresh_cache()
        self.recalc(callback=True)

    def refresh_cache(self):
        i_arr = np.arange(0, self.maxc + 1, dtype=np.uint)
        self.p_dist.result.setvals(res_np=i_arr)
        self.pipeline.run_from(self.p_shift)
        cache_arr = self.pipeline.get_data(self.pipeline[-1])
        #self.cache_arr = self.get_carr()
        if cache_arr is not None:
            self.cache_arr = cache_arr[:, :3]

    def recalc(self, callback=True):
        self.refresh_cache()
        if callback:
            self.make_callback('changed')

    def get_hash_size(self):
        return self.p_dist.get_hash_size()

    def set_hash_size(self, size, callback=True):
        # TEMP: ignore passed callback parameter
        self.t_.set(color_hashsize=size)

    def color_hashsize_set_cb(self, setting, size):
        self.p_dist.set_hash_size(size)
        self.make_callback('changed')

    def get_hash_algorithms(self):
        return ColorDist.get_dist_names()

    def get_hash_algorithm(self):
        return str(self.p_dist.dist)

    def get_dist(self):
        """
        Return the color distribution used by this RGBMapper.
        """
        return self.p_dist.get_dist()

    def set_dist(self, dist, callback=True):
        self.p_dist.set_dist(dist)
        if callback:
            self.make_callback('changed')

    def set_hash_algorithm(self, name, callback=True, **kwargs):
        # TODO: deal with algorithm parameters in kwargs
        self.t_.set(color_algorithm=name)

    def set_color_algorithm(self, name):
        self.t_.set(color_algorithm=name)

    def color_algorithm_set_cb(self, setting, name):
        self.p_dist.set_color_algorithm(name)
        self.make_callback('changed')

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [order.index(c) for c in cs]

    def get_rgb_array(self, idx, order='RGB', image_order=''):
        """
        Parameters
        ----------
        idx : index array

        order : str
            The order of the color planes in the output array (e.g. "ARGB")

        image_order : str or None
            The order of channels if indexes already contain RGB info.
        """
        t1 = time.time()

        self.p_input.set_input(idx)
        self.pipeline.run_from(self.p_input)

        out_arr = self.pipeline.get_data(self.pipeline[-1])

        # reorder as caller needs it
        #out_arr = trcalc.reorder_image(order, out_arr, state.order)

        t2 = time.time()
        self.logger.debug("rgbmap: total=%.4f" % (t2 - t1))
        return out_arr

    def get_hasharray(self, idx):
        return self.p_dist.dist.hash_array(idx)

    def shift(self, pct, rotate=False, callback=True):
        self.p_shift.shift(pct, rotate=rotate)
        self.t_.set(shift_array=self.p_shift.get_sarr())

    def scale_and_shift(self, scale_pct, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        self.p_shift.scale_and_shift(scale_pct, shift_pct)
        self.t_.set(shift_array=self.p_shift.get_sarr())

    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        self.p_shift.stretch(scale_factor)
        self.t_.set(shift_array=self.p_shift.get_sarr())

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

    def create_pipeline(self):
        # create RGB mapping pipeline
        self.p_input = RGBInput(bpp=self.bpp)
        self.p_dist = Distribute(bpp=self.bpp)
        self.p_shift = ShiftMap(bpp=self.bpp)
        self.p_imap = IntensityMap(bpp=self.bpp)
        self.p_cmap = ColorMap(bpp=self.bpp)

        stages = [self.p_input,
                  self.p_dist,
                  self.p_shift,
                  ]
        self.pipeline = pipeline.Pipeline(self.logger, stages)
        self.pipeline.name = 'rgb-mapper'

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


class RGBMapStage(Stage):

    def __init__(self, bpp=8):
        super().__init__()

        self.set_bpp(bpp)

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


class RGBInput(RGBMapStage):
    """First.

    """
    _stagename = 'rgbmap-input'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.in_arr = None

    def set_input(self, in_arr):
        if not np.issubdtype(in_arr.dtype, np.uint):
            in_arr = in_arr.astype(np.uint)

        #self.verify_2d(in_arr)

        self.in_arr = in_arr

    def run(self, prev_stage):
        if prev_stage is not None:
            raise StageError("'{}' in wrong location".format(self._stagename))

        if self._bypass:
            self.pipeline.send(res_np=None)
            return

        self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                         self.in_arr))
        self.pipeline.send(res_np=self.in_arr)


class Distribute(RGBMapStage):
    """Distribute data according to a curve.

    """
    _stagename = 'rgbmap-distribute'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.hashsize = 65536
        self.set_color_algorithm('linear')

    def set_dist(self, dist):
        self.dist = dist

    def get_dist(self):
        return self.dist

    def get_hash_size(self):
        return self.hashsize

    def set_hash_size(self, size):
        self.hashsize = size
        self.dist.set_hash_size(size)

    def set_color_algorithm(self, name):
        color_dist_class = ColorDist.get_dist(name)
        self.dist = color_dist_class(self.hashsize)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if arr_in is None:
            self.pipeline.send(res_np=None)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        out_arr = self.dist.hash_array(arr_in)

        self.logger.debug("{}: sending result ({})".format(self._stagename,
                                                           out_arr))
        self.pipeline.send(res_np=out_arr)


class ShiftMap(RGBMapStage):
    """Redistribute data according to a shift array.

    """
    _stagename = 'rgbmap-shift-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.reset_sarr()

    def get_sarr(self):
        return self.sarr

    def reset_sarr(self):
        maxlen = self.maxc + 1
        self.scale_pct = 1.0
        self.sarr = np.arange(maxlen)

    def set_sarr(self, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            maxlen = self.maxc + 1
            _len = len(sarr)
            if _len != maxlen:
                raise RGBMapError("shift map length %d != %d" % (_len, maxlen))
            self.sarr = sarr
        else:
            self.reset_sarr()

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

        self.sarr = work

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

        self.sarr = work

    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        self.scale_pct *= scale_factor
        self.scale_and_shift(self.scale_pct, 0.0, callback=callback)

    def run(self, prev_stage):
        in_arr = self.pipeline.get_data(prev_stage)
        if in_arr is None:
            self.pipeline.send(res_np=None)
            return
        #self.verify_2d(in_arr)

        if not np.issubdtype(in_arr.dtype, np.uint):
            in_arr = in_arr.astype(np.uint)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # out_arr = self.sarr[in_arr].clip(0, self.maxc).astype(np.uint, copy=False)
        out_arr = self.sarr[in_arr]
        # TODO: I think we can avoid this operation, if shift array contents
        # can be limited to 0..maxc
        #out_arr.clip(0, self.maxc, out=out_arr)

        self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                         out_arr))
        self.pipeline.send(res_np=out_arr)


class IntensityMap(RGBMapStage):
    """Map indexes through a curve.

    """
    _stagename = 'rgbmap-intensity-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.imap = None
        self.iarr = None
        self.set_intensity_map('ramp')

    def get_iarr(self):
        return self.iarr

    def set_intensity_map(self, imap_name):
        im = mod_imap.get_imap(imap_name)
        self.set_imap(im)

    def set_imap(self, imap):
        self.imap = imap
        self.calc_imap()

    def calc_imap(self):
        arr = np.array(self.imap.ilst) * float(self.maxc)
        self.iarr = np.round(arr).astype(np.uint, copy=False)

    def run(self, prev_stage):
        in_arr = self.pipeline.get_data(prev_stage)
        if in_arr is None:
            self.pipeline.send(res_np=None)
            return
        #self.verify_2d(in_arr)

        if not np.issubdtype(in_arr.dtype, np.uint):
            in_arr = in_arr.astype(np.uint)

        out_arr = self.iarr[in_arr]

        self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                         out_arr))
        self.pipeline.send(res_np=out_arr)


class ColorMap(RGBMapStage):
    """Map indexes through a three-color lookup table.

    """
    _stagename = 'rgbmap-color-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.cmap = None
        self.carr = None
        self.set_color_map('gray')

    def set_color_map(self, cmap_name):
        cm = mod_cmap.get_cmap(cmap_name)
        self.set_cmap(cm)

    def get_carr(self):
        return self.carr

    def set_carr(self, carr):
        if carr is not None:
            carr = np.asarray(carr).clip(0, self.maxc).astype(self.dtype)
            maxlen = self.maxc + 1
            self.carr = carr
            _len = carr.shape[1]
            if _len != maxlen:
                raise RGBMapError("color map length %d != %d" % (_len, maxlen))
        else:
            self.calc_cmap()

    def set_cmap(self, cmap):
        self.cmap = cmap
        self.calc_cmap()

    def invert_cmap(self):
        self.carr = np.fliplr(self.carr)

    def rotate_cmap(self, num):
        self.carr = np.roll(self.carr, num, axis=1)

    def reset_cmap(self):
        self.calc_cmap()

    def calc_cmap(self):
        clst = self.cmap.clst
        self.maxc = len(clst) - 1
        arr = np.array(clst).transpose() * float(self.maxc)
        # does this really need to be the same type as rgbmap output type?
        self.carr = np.round(arr).astype(self.dtype, copy=False)

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [order.index(c) for c in cs]

    def run(self, prev_stage):
        in_arr = self.pipeline.get_data(prev_stage)
        if in_arr is None:
            self.pipeline.send(res_np=None)
            return
        #self.verify_2d(in_arr)

        if not np.issubdtype(in_arr.dtype, np.uint):
            in_arr = in_arr.astype(np.uint)

        # prepare output array
        shape = in_arr.shape
        # get RGB order requested for output
        state = self.pipeline.get('state')
        order = state.order
        depth = len(order)
        image_order = trcalc.guess_order(shape)

        if (image_order is not None) and (len(image_order) > 1):
            # indexes contain RGB axis, so omit this
            res_shape = shape[:-1] + (depth, )
        else:
            res_shape = shape + (depth, )

        out = np.empty(res_shape, dtype=self.dtype, order='C')

        rgbobj = RGBPlanes(out, order)

        # set alpha channel
        if rgbobj.hasAlpha:
            aa = rgbobj.get_slice('A')
            aa.fill(self.maxc)

        ri, gi, bi = self.get_order_indexes(rgbobj.get_order(), 'RGB')
        out_arr = rgbobj.rgbarr

        arr = self.carr.T

        # See NOTE [A]
        if (image_order is None) or (len(image_order) == 1):
            out_arr[..., [ri, gi, bi]] = arr[in_arr]

        elif len(image_order) == 2:
            mj, aj = self.get_order_indexes(image_order, 'MA')
            out_arr[..., [ri, gi, bi]] = arr[in_arr[..., mj]]

        else:
            # <== indexes already contain RGB info.
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            out_arr[..., ri] = arr[:, 0][in_arr[..., rj]]
            out_arr[..., gi] = arr[:, 1][in_arr[..., gj]]
            out_arr[..., bi] = arr[:, 2][in_arr[..., bj]]

        # alpha = self.pipeline.get('alpha')
        # if alpha is not None:
        #     out_arr[..., -1] = alpha

        self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                         out_arr))
        self.pipeline.send(res_np=out_arr)
