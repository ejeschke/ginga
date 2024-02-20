#
# RGBMap.py -- color mapping
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import uuid
import numpy as np

from ginga.misc import Callback, Settings, Bunch
from ginga import ColorDist, trcalc
from ginga import cmap as mod_cmap
from ginga import imap as mod_imap
from ginga.util import pipeline
from ginga.util.stages.color import (RGBInput, Distribute, ShiftMap,
                                     IntensityMap, ColorMap, RGBMapError)


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

    def contrast_set_cb(self, setting, pct):
        self.p_shift.set_contrast(pct)
        self.recalc()

    def brightness_set_cb(self, setting, pct):
        self.p_shift.set_brightness(pct)
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

    def get_hasharray(self, idx):
        return self.p_dist.dist.hash_array(idx)

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
