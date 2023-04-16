#
# RGBMap.py -- color mapping
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import uuid
import numpy as np
import warnings

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
        self.cache_arr = None

        # For color and intensity maps
        self.cmap = None
        self.imap = None
        self.dist = dist

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
                              'color_algorithm', 'color_hashsize',
                              'color_map_invert', 'color_map_rot_pct',
                              'contrast', 'brightness',
                              ]

        # add our defaults
        self.t_.add_defaults(color_map='gray', intensity_map='ramp',
                             color_map_invert=False, color_map_rot_pct=0.0,
                             color_algorithm='linear',
                             color_hashsize=self.maxc + 1,
                             contrast=0.5, brightness=0.5)
        self.t_.get_setting('color_map').add_callback('set',
                                                      self.color_map_set_cb)
        self.t_.get_setting('intensity_map').add_callback('set',
                                                          self.intensity_map_set_cb)
        self.t_.get_setting('color_map_invert').add_callback('set',
                                                             self.color_map_invert_set_cb)
        self.t_.get_setting('color_map_rot_pct').add_callback('set',
                                                              self.color_map_rot_pct_set_cb)
        self.t_.get_setting('contrast').add_callback('set',
                                                     self.contrast_set_cb)
        self.t_.get_setting('brightness').add_callback('set',
                                                       self.brightness_set_cb)
        self.t_.get_setting('color_hashsize').add_callback('set',
                                                           self.color_hashsize_set_cb)
        self.t_.get_setting('color_algorithm').add_callback('set',
                                                            self.color_algorithm_set_cb)

        # For callbacks
        for name in ('changed', ):
            self.enable_callback(name)

        self.suppress_changed = self.suppress_callback('changed', 'last')

        cm_name = self.t_.get('color_map', 'gray')
        self.set_color_map(cm_name)

        self.p_cmap.invert_cmap(False)
        self.p_cmap.rotate_color_map(0.0)

        im_name = self.t_.get('intensity_map', 'ramp')
        self.set_intensity_map(im_name)

    def set_bpp(self, bpp):
        """
        Set the bit depth (per band) for the output.
        A typical "32-bit RGBA" image would be 8; a 48-bit image would
        be 16, etc.
        """
        self.bpp = bpp
        self.maxc = int(2 ** self.bpp - 1)

        self.create_pipeline()

        self._refresh_cache()

    def create_pipeline(self):
        # create RGB mapping pipeline
        self.p_input = RGBInput(bpp=self.bpp)
        self.p_dist = Distribute(bpp=self.bpp)
        if self.dist is not None:
            self.p_dist.set_dist(self.dist)
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

        # will be set from outer pipelines
        state = Bunch.Bunch(order='RGBA')
        self.pipeline.set(state=state)

        self._refresh_cache()

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
        self.recalc()

    def invert_cmap(self, callback=True):
        tf = not self.t_.get('color_map_invert', False)
        self.t_.set(color_map_invert=tf, callback=callback)

    def color_map_invert_set_cb(self, setting, tf):
        self.p_cmap.invert_cmap(tf)
        self.recalc()

    def rotate_cmap(self, num, callback=True):
        pct = num / (self.maxc + 1)
        self.t_.set(color_map_rot_pct=pct, callback=callback)

    def color_map_rot_pct_set_cb(self, setting, pct):
        self.p_cmap.rotate_color_map(pct)
        self.recalc()

    def restore_cmap(self, callback=True):
        """Undoes color map rotation and inversion, also resets contrast
        and brightness.
        """
        with self.suppress_changed:
            self.t_.set(color_map_invert=False, color_map_rot_pct=0.0,
                        contrast=0.5, brightness=0.5)

    def reset_cmap(self):
        """Similar to restore_cmap, but also restores the default color
        and intensity maps.
        """
        with self.suppress_changed:
            self.t_.set(color_map='gray', intensity_map='ramp')
            self.restore_cmap()

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
        self.recalc()

    def reset_sarr(self, callback=True):
        self.t_.set(contrast=0.5, brightness=0.5, callback=callback)

    def _get_sarr(self):
        warnings.warn("get_sarr() has been deprecated", DeprecationWarning)
        return self.p_shift._get_sarr()

    def _set_sarr(self, sarr, callback=True):
        warnings.warn("set_sarr() has been deprecated", DeprecationWarning)
        self.p_shift._set_sarr(sarr)
        self.recalc()

    def contrast_set_cb(self, setting, pct):
        self.p_shift.set_contrast(pct)
        self.recalc()

    def brightness_set_cb(self, setting, pct):
        self.p_shift.set_brightness(pct)
        self.recalc()

    def get_carr(self):
        warnings.warn("get_carr() has been deprecated", DeprecationWarning)
        return self.p_cmap.get_carr()

    def set_carr(self, carr, callback=True):
        warnings.warn("set_carr() has been deprecated", DeprecationWarning)
        self.p_cmap.set_carr(carr)
        self.recalc()

    def _refresh_cache(self):
        i_arr = np.arange(0, self.maxc + 1, dtype=np.uint)
        self.p_dist.result.setvals(res_np=i_arr)
        self.pipeline.run_from(self.p_shift)
        cache_arr = self.pipeline.get_data(self.pipeline[-1])
        if cache_arr is not None:
            if len(cache_arr.shape) < 2:
                # if colormap stage is bypassed then output will need to
                # be broadcast to RGB
                cache_arr = np.dstack((cache_arr, cache_arr, cache_arr)).reshape(cache_arr.shape + (3,))
            self.cache_arr = cache_arr[:, :3]

    def recalc(self, callback=True):
        self._refresh_cache()
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

    def get_rgb_array(self, idx, order=None):

        if self.cache_arr is not None:
            # if the cache array is set, then this will deliver a faster
            # short cut to the colorized output--just apply the color
            # distribution and then map through the cache array
            idx = self.p_dist.get_hasharray(idx)
            arr_out = self.p_cmap.do_map_index(idx, self.cache_arr)

        else:
            # else run through the pipeline as usual
            self.p_input.set_input(idx)
            self.pipeline.run_from(self.p_input)

            arr_out = self.pipeline.get_data(self.pipeline[-1])

        # reorder as caller needs it
        state = self.pipeline.get('state')
        if order is not None and order != state.order:
            arr_out = trcalc.reorder_image(order, arr_out, state.order)

        return arr_out

    def get_rgbarray(self, idx, order='RGB', image_order=None):
        """
        Parameters
        ----------
        idx : index array

        order : str
            The order of the color planes in the output array (e.g. "RGBA")

        image_order : str or None
            The order of channels if indexes already contain RGB info.
        """
        warnings.warn("get_rgbarray(idx) has been deprecated--"
                      "use get_rgb_array(idx) instead",
                      DeprecationWarning)

        if image_order not in (None, ''):
            # reorder image channels for pipeline
            state = self.pipeline.get('state')
            if state.order != image_order:
                idx = trcalc.reorder_image(state.order, idx, image_order)

        arr_out = self.get_rgb_array(idx, order=order)
        return RGBPlanes(arr_out, order)

    def get_hasharray(self, idx):
        return self.p_dist.dist.hash_array(idx)

    def shift(self, pct, rotate=False, callback=True):
        warnings.warn("shift() has been deprecated", DeprecationWarning)
        #self.p_shift.shift(pct, rotate=rotate)
        brightness = self.p_shift._shift_to_brightness(pct, reset=False)
        self.t_.set(brightness=brightness)

    def scale_and_shift(self, scale_pct, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        warnings.warn("scale_and_shift() has been deprecated", DeprecationWarning)
        #self.p_shift.scale_and_shift(scale_pct, shift_pct)
        brightness = self.p_shift._shift_to_brightness(shift_pct, reset=True)
        contrast = self.p_shift._scale_to_contrast(scale_pct, reset=True)
        self.t_.set(brightness=brightness, contrast=contrast)

    def stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        warnings.warn("stretch() has been deprecated", DeprecationWarning)
        #self.p_shift.stretch(scale_factor)
        contrast = self.p_shift._scale_to_contrast(scale_factor, reset=False)
        self.t_.set(contrast=contrast)

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
        super().__init__(logger, dist=dist, bpp=bpp)

        self.p_imap.bypass(True)
        self.p_cmap.bypass(True)


class PassThruRGBMapper(RGBMapper):
    """
    A kind of color mapper for data that is already in RGB form.

    This mapper bypasses color distribution, contrast adjustment and
    coloring.  It is thus the most efficient one to use for maximum
    speed rendering of "finished" RGB data.
    """
    def __init__(self, logger, dist=None, bpp=None):
        super().__init__(logger, dist=dist, bpp=bpp)

        self.p_dist.bypass(True)
        self.p_shift.bypass(True)
        self.p_imap.bypass(True)
        self.p_cmap.bypass(True)


class RGBMapStage(Stage):
    """A class that all stages participating in color mapping subclass.

    Establishes the bit depth of the RGB mapping.
    """
    def __init__(self, bpp=8):
        super().__init__()

        self.trace = False
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
    """First stage of a sub-pipeline that accepts the input to be colored
    this should usually be the output of the "Cuts" stage of rendering.
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

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             self.in_arr))
        self.pipeline.send(res_np=self.in_arr)


class Distribute(RGBMapStage):
    """Distribute data according to a curve.

    This stage handles the distribution of input values according to a
    predefined mapping such as linear, log, power, sqrt, asinh, etc.
    """
    _stagename = 'rgbmap-distribute'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.dist = None
        self._hashsize = self.maxc + 1
        self.set_color_algorithm('linear')

    def set_dist(self, dist):
        self.dist = dist

    def get_dist(self):
        return self.dist

    def get_hash_size(self):
        return self._hashsize

    def set_hash_size(self, size):
        self._hashsize = size
        self.dist.set_hash_size(size)

    def set_color_algorithm(self, name):
        color_dist_class = ColorDist.get_dist(name)
        self.dist = color_dist_class(self._hashsize)

    def get_hasharray(self, arr_in):
        if self._bypass or arr_in is None:
            return arr_in

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        return self.dist.hash_array(arr_in)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        arr_out = self.get_hasharray(arr_in)

        if self.trace:
            self.logger.debug("{}: sending result ({})".format(self._stagename,
                                                               arr_out))
        self.pipeline.send(res_np=arr_out)


class ShiftMap1(RGBMapStage):
    """Redistribute data according to a shift array.

    This stage handles colormap shifts and stretches, which are used to
    set brightness and contrast in the image.
    """
    _stagename = 'rgbmap-shift-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self._scale_factor = 1.0
        self._shift_pct = 0.0
        self._sarr = None

        self._reset_sarr()

    def _scale_to_contrast(self, scale_factor, reset=False):
        if not reset:
            # if not reset, multipy by the current scale factor
            scale_factor *= self._scale_factor
        pct = np.clip((np.clip(scale_factor, 0.01, 20.0) * 1000) / 2000,
                      0.0, 1.0)
        pct = 1.0 - pct
        return pct

    def _contrast_to_scale(self, contrast_pct):
        # I tried to mimic ds9's exponential scale feel along the Y-axis
        i = np.clip(contrast_pct, 0.0001, 1.0)
        scale_factor = (1.0 / (i**3)) * 0.0001 + (1.0 / i) - 1.0
        scale_factor = np.clip(scale_factor, 0.0, self.maxc)
        return scale_factor

    def set_contrast(self, pct):
        scale_factor = self._contrast_to_scale(pct)
        self._stretch(scale_factor)

    @property
    def contrast(self):
        return self._scale_to_contrast(self._scale_factor)

    def _brightness_to_shift(self, brightness_pct):
        pct = 1.0 - brightness_pct
        # convert to (-1.0, 1.0) for shift pct
        shift_pct = (pct - 0.5) * 2.0
        return shift_pct

    def _shift_to_brightness(self, shift_pct, reset=False):
        if not reset:
            # if not reset, add the current shift pct
            shift_pct += self._shift_pct
        pct = (np.clip(shift_pct, -1.0, 1.0) + 1) * 0.5
        return 1.0 - pct

    def set_brightness(self, pct):
        shift_pct = self._brightness_to_shift(pct)
        self._shift(shift_pct)

    @property
    def brightness(self):
        return self._shift_to_brightness(self._shift_pct)

    def _reset_sarr(self):
        maxlen = self.maxc + 1
        self._scale_factor = 1.0
        self._shift_pct = 0.0
        self._sarr = np.arange(maxlen)

    def _get_sarr(self):
        return self._sarr

    def _set_sarr(self, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            maxlen = self.maxc + 1
            _len = len(sarr)
            if _len != maxlen:
                raise RGBMapError("shift map length %d != %d" % (_len, maxlen))
            self._sarr = sarr
        else:
            self._reset_sarr()

    def _shift_arr(self, sarr, pct, rotate=False):
        n = len(sarr)
        num = int(n * pct)
        arr = np.roll(sarr, num)
        if not rotate:
            if num > 0:
                arr[0:num] = sarr[0]
            elif num < 0:
                arr[n + num:n] = sarr[-1]
        return arr

    def _stretch_arr(self, sarr, scale):
        old_wd = len(sarr)
        new_wd = int(round(scale * old_wd))

        # Is there a more efficient way to do this?
        xi = np.mgrid[0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)

        xi = (xi * iscale_x).astype(np.uint, copy=False)
        xi = xi.clip(0, old_wd - 1).astype(np.uint, copy=False)
        newdata = sarr[xi]
        return newdata

    def _scale_and_shift(self, scale_factor, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        # reset the shift array to normal
        maxlen = self.maxc + 1
        self._sarr = np.arange(maxlen)

        # limit shrinkage to 1% of original size
        scale = max(scale_factor, 0.01)
        self._scale_factor = scale

        work = self._stretch_arr(self._sarr, scale)
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
        self._shift_pct = shift_pct
        work = self._shift_arr(work, shift_pct)
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)

        self._sarr = work

    def _stretch(self, scale_factor, reset=True, callback=True):
        """Stretch the color map via altering the shift map.
        """
        if not reset:
            scale_factor = self._scale_factor * scale_factor
        self._scale_and_shift(scale_factor, self._shift_pct, callback=callback)

    def _shift(self, pct, rotate=False, reset=True, callback=True):
        if not reset:
            pct = self._shift_pct + pct
        self._scale_and_shift(self._scale_factor, pct, callback=callback)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # arr_out = self._sarr[arr_in].clip(0, self.maxc).astype(np.uint, copy=False)
        arr_out = self._sarr[arr_in]
        # TODO: I think we can avoid this operation, if shift array contents
        # can be limited to 0..maxc
        #arr_out.clip(0, self.maxc, out=arr_out)

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)


class ShiftMap(RGBMapStage):
    """Redistribute data according to a shift array.

    This stage handles colormap shifts and stretches, which are used to
    set brightness and contrast in the image.
    """
    _stagename = 'rgbmap-shift-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self._contrast = 0.5
        self._brightness = 0.5
        self._sarr = None

        self._reset_sarr()

    @property
    def contrast(self):
        return self._contrast

    def set_contrast(self, pct):
        self._contrast = pct
        scale_factor = self._contrast_to_scale(pct)
        self._stretch(scale_factor)

    @property
    def brightness(self):
        return self._brightness

    def set_brightness(self, pct):
        self._brightness = pct
        shift_pct = self._brightness_to_shift(pct)
        self._shift(shift_pct)

    def _scale_to_contrast(self, scale_factor, reset=False):
        if not reset:
            # if not reset, multipy by the current scale factor
            scale_factor *= self._scale_factor
        pct = np.clip((np.clip(scale_factor, 0.01, 20.0) * 1000) / 2000,
                      0.0, 1.0)
        pct = 1.0 - pct
        return pct

    def _contrast_to_scale(self, contrast_pct):
        # I tried to mimic ds9's exponential scale feel along the Y-axis
        i = np.clip(contrast_pct, 0.0001, 1.0)
        scale_factor = (1.0 / (i**3)) * 0.0001 + (1.0 / i) - 1.0
        scale_factor = np.clip(scale_factor, 0.0, self.maxc)
        return scale_factor

    def _brightness_to_shift(self, brightness_pct):
        pct = 1.0 - brightness_pct
        # convert to (-1.0, 1.0) for shift pct
        shift_pct = (pct - 0.5) * 2.0
        return shift_pct

    def _shift_to_brightness(self, shift_pct, reset=False):
        if not reset:
            # if not reset, add the current shift pct
            shift_pct += self._shift_pct
        pct = (np.clip(shift_pct, -1.0, 1.0) + 1) * 0.5
        return 1.0 - pct

    def _reset_sarr(self):
        maxlen = self.maxc + 1
        self._contrast = 0.5
        self._brightness = 0.5
        self._sarr = np.arange(maxlen)

    def _get_sarr(self):
        return self._sarr

    def _set_sarr(self, sarr):
        if sarr is not None:
            sarr = np.asarray(sarr).clip(0, self.maxc).astype(np.uint)
            maxlen = self.maxc + 1
            _len = len(sarr)
            if _len != maxlen:
                raise RGBMapError("shift map length %d != %d" % (_len, maxlen))
            self._sarr = sarr
        else:
            self._reset_sarr()

    def _shift_arr(self, sarr, pct, rotate=False):
        n = len(sarr)
        num = int(n * pct)
        arr = np.roll(sarr, num)
        if not rotate:
            if num > 0:
                arr[0:num] = sarr[0]
            elif num < 0:
                arr[n + num:n] = sarr[-1]
        return arr

    def _stretch_arr(self, sarr, scale):
        old_wd = len(sarr)
        new_wd = int(round(scale * old_wd))

        # Is there a more efficient way to do this?
        xi = np.mgrid[0:new_wd]
        iscale_x = float(old_wd) / float(new_wd)

        xi = (xi * iscale_x).astype(np.uint, copy=False)
        xi = xi.clip(0, old_wd - 1).astype(np.uint, copy=False)
        newdata = sarr[xi]
        return newdata

    def _scale_and_shift(self, scale_factor, shift_pct, callback=True):
        """Stretch and/or shrink the color map via altering the shift map.
        """
        # reset the shift array to normal
        maxlen = self.maxc + 1
        self._sarr = np.arange(maxlen)

        # limit shrinkage to 1% of original size
        scale = max(scale_factor, 0.01)

        work = self._stretch_arr(self._sarr, scale)
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
        work = self._shift_arr(work, shift_pct)
        assert len(work) == maxlen, \
            RGBMapError("shifted shift map is != %d" % maxlen)

        self._sarr = work

    def _stretch(self, scale_factor, callback=True):
        """Stretch the color map via altering the shift map.
        """
        shift_pct = self._brightness_to_shift(self._brightness)
        self._scale_and_shift(scale_factor, shift_pct, callback=callback)

    def _shift(self, shift_pct, rotate=False, callback=True):
        scale_factor = self._contrast_to_scale(self._contrast)
        self._scale_and_shift(scale_factor, shift_pct, callback=callback)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        # run it through the shift array and clip the result
        # See NOTE [A]
        # arr_out = self._sarr[arr_in].clip(0, self.maxc).astype(np.uint, copy=False)
        arr_out = self._sarr[arr_in]
        # TODO: I think we can avoid this operation, if shift array contents
        # can be limited to 0..maxc
        #arr_out.clip(0, self.maxc, out=arr_out)

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)


class IntensityMap(RGBMapStage):
    """Map indexes through a curve.

    """
    _stagename = 'rgbmap-intensity-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.imap = None
        self._iarr = None
        self.set_intensity_map('ramp')

    def set_intensity_map(self, imap_name):
        im = mod_imap.get_imap(imap_name)
        self.set_imap(im)

    def set_imap(self, imap):
        self.imap = imap
        self.calc_imap()

    def calc_imap(self):
        arr = np.array(self.imap.ilst) * float(self.maxc)
        self._iarr = np.round(arr).astype(np.uint, copy=False)

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        arr_out = self._iarr[arr_in]

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)


class ColorMap(RGBMapStage):
    """Map indexes through a three-color lookup table.

    """
    _stagename = 'rgbmap-color-map'

    def __init__(self, bpp=8):
        super().__init__(bpp=bpp)

        self.cmap = None
        self._carr = None
        self._inverted = False
        self._rot_pct = 0.0

        self.set_color_map('gray')

    @property
    def inverted(self):
        return self._inverted

    @property
    def rot_pct(self):
        return self._rot_pct

    def set_color_map(self, cmap_name):
        cm = mod_cmap.get_cmap(cmap_name)
        self.set_cmap(cm)

    def set_cmap(self, cmap):
        self.cmap = cmap
        self.calc_cmap()

    def invert_cmap(self, tf):
        self._inverted = tf
        self.calc_cmap()

    def rotate_color_map(self, pct):
        self._rot_pct = np.clip(pct, -1.0, 1.0)
        self.calc_cmap()

    def _gen_cmap(self):
        clst = self.cmap.clst
        self.maxc = len(clst) - 1
        arr = np.array(clst).transpose() * float(self.maxc)
        # does this really need to be the same type as rgbmap output type?
        carr = np.round(arr).astype(self.dtype, copy=False)
        return carr

    def reset_cmap(self):
        self._inverted = False
        self._rot_pct = 0.0
        self.calc_cmap()

    def calc_cmap(self):
        self._carr = self._gen_cmap()
        if self._inverted:
            self._carr = np.fliplr(self._carr)
        num = int((self.maxc + 1) * self._rot_pct)
        if num != 0:
            self._carr = np.roll(self._carr, num, axis=1)

    def get_order_indexes(self, order, cs):
        order = order.upper()
        if order == '':
            # assume standard RGB order if we don't find an order
            # explicitly set
            return [0, 1, 2]
        cs = cs.upper()
        return [order.index(c) for c in cs]

    def do_map_index(self, arr_in, map_arr):
        if not np.issubdtype(arr_in.dtype, np.uint):
            arr_in = arr_in.astype(np.uint)

        # prepare output array
        shape = arr_in.shape
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
        arr_out = rgbobj.rgbarr

        # See NOTE [A]
        if (image_order is None) or (len(image_order) == 1):
            arr_out[..., [ri, gi, bi]] = map_arr[arr_in]

        elif len(image_order) == 2:
            mj, aj = self.get_order_indexes(image_order, 'MA')
            arr_out[..., [ri, gi, bi]] = map_arr[arr_in[..., mj]]

        else:
            # <== indexes already contain RGB info.
            rj, gj, bj = self.get_order_indexes(image_order, 'RGB')
            arr_out[..., ri] = map_arr[:, 0][arr_in[..., rj]]
            arr_out[..., gi] = map_arr[:, 1][arr_in[..., gj]]
            arr_out[..., bi] = map_arr[:, 2][arr_in[..., bj]]

        # alpha = self.pipeline.get('alpha')
        # if alpha is not None:
        #     arr_out[..., -1] = alpha

        return arr_out

    def run(self, prev_stage):
        arr_in = self.pipeline.get_data(prev_stage)
        if self._bypass or arr_in is None:
            self.pipeline.send(res_np=arr_in)
            return
        #self.verify_2d(arr_in)

        arr_out = self.do_map_index(arr_in, self._carr.T)

        if self.trace:
            self.logger.debug("{}: sending data ({})".format(self._stagename,
                                                             arr_out))
        self.pipeline.send(res_np=arr_out)
