#
# ImageView.py -- base class for the display of image files
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""This module handles image viewers."""

from io import BytesIO

import math
import logging
import threading
import sys
import traceback
import time
import uuid

import numpy as np

from ginga.misc import Callback, Settings
from ginga import BaseImage, AstroImage
from ginga import RGBMap, AutoCuts, ColorDist, zoom
from ginga import colors, trcalc
from ginga.canvas import coordmap, transform
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util import addons, vip

__all__ = ['ImageViewBase']


class ImageViewError(Exception):
    pass


class ImageViewCoordsError(ImageViewError):
    pass


class ImageViewNoDataError(ImageViewError):
    pass


class ImageViewBase(Callback.Callbacks):
    """An abstract base class for displaying images represented by
    Numpy data arrays.

    This class attempts to do as much of the image handling as possible
    using Numpy array manipulations (even color and intensity mapping)
    so that only a minimal mapping to a pixel buffer is necessary in
    concrete subclasses that connect to an actual rendering surface
    (e.g., Qt, GTK, Tk, HTML5).

    Parameters
    ----------
    logger : :py:class:`~logging.Logger` or `None`
        Logger for tracing and debugging. If not given, one will be created.

    rgbmap : `~ginga.RGBMap.RGBMapper` or `None`
        RGB mapper object. If not given, one will be created.

    settings : `~ginga.misc.Settings.SettingGroup` or `None`
        Viewer preferences. If not given, one will be created.

    """

    vname = 'Ginga Image'
    vtypes = [BaseImage.BaseImage]

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer."""
        if not isinstance(dataobj, BaseImage.BaseImage):
            return False
        shp = list(dataobj.shape)
        if len(shp) < 2:
            return False
        return True

    def __init__(self, logger=None, rgbmap=None, settings=None):
        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('ImageViewBase')

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        # to be eventually deprecated
        self.t_ = settings

        # RGB mapper
        if rgbmap:
            # which way should the settings be migrated--
            # rgbmap to viewer or vice-versa?
            t_ = rgbmap.get_settings()
            t_.share_settings(self.t_, keylist=rgbmap.settings_keys)
        else:
            rgbmap = RGBMap.RGBMapper(self.logger, settings=self.t_)
        self.rgbmap = rgbmap

        # Renderer
        self.renderer = None

        # for debugging
        self.viewer_id = str(uuid.uuid4())
        self.name = self.viewer_id

        # Initialize RGBMap
        rgbmap.add_callback('changed', self.rgbmap_cb)

        # for scale
        self.t_.add_defaults(scale=(1.0, 1.0), sanity_check_scale=True)
        for name in ['scale']:
            self.t_.get_setting(name).add_callback('set', self.scale_cb)

        # for pan
        self.t_.add_defaults(pan=(1.0, 1.0), pan_coord='data')
        for name in ['pan', ]:  # 'pan_coord'
            self.t_.get_setting(name).add_callback('set', self.pan_cb)

        # for cut levels
        self.t_.add_defaults(cuts=(0.0, 0.0))
        for name in ['cuts']:
            self.t_.get_setting(name).add_callback('set', self.cut_levels_cb)

        # for auto cut levels
        self.autocuts_options = ('on', 'override', 'once', 'off')
        self.t_.add_defaults(autocuts='override', autocut_method='zscale',
                             autocut_params=[])
        for name in ('autocut_method', 'autocut_params'):
            self.t_.get_setting(name).add_callback('set', self.autocut_params_cb)

        # for zooming
        self.t_.add_defaults(zoomlevel=1.0, zoom_algorithm='step',
                             scale_x_base=1.0, scale_y_base=1.0,
                             interpolation='basic',
                             zoom_rate=math.sqrt(2.0))
        for name in ('zoom_rate', 'zoom_algorithm',
                     'scale_x_base', 'scale_y_base'):
            self.t_.get_setting(name).add_callback('set', self.zoomsetting_change_cb)
        self.zoom = zoom.get_zoom_alg(self.t_['zoom_algorithm'])(self)

        self.t_.get_setting('interpolation').add_callback(
            'set', self.interpolation_change_cb)

        # max/min scaling
        self.t_.add_defaults(scale_max=None, scale_min=None)

        # autozoom options
        self.autozoom_options = ('on', 'override', 'once', 'off')
        self.t_.add_defaults(autozoom='on')

        # for panning
        self.autocenter_options = ('on', 'override', 'once', 'off')
        self.t_.add_defaults(autocenter='on')

        # for transforms
        self.t_.add_defaults(flip_x=False, flip_y=False, swap_xy=False)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.get_setting(name).add_callback('set', self.transform_cb)

        # desired rotation angle
        self.t_.add_defaults(rot_deg=0.0)
        self.t_.get_setting('rot_deg').add_callback(
            'set', self.rotation_change_cb)

        # misc
        self.t_.add_defaults(auto_orient=True,
                             defer_redraw=True, defer_lagtime=0.025,
                             show_pan_position=False,
                             show_mode_indicator=True,
                             show_focus_indicator=None,
                             onscreen_font='Sans Serif',
                             onscreen_font_size=None,
                             color_fg="#D0F0E0", color_bg="#404040",
                             limits=None, enter_focus=None)
        self.t_.get_setting('limits').add_callback('set', self._set_limits_cb)

        # embedded image "profiles"
        self.t_.add_defaults(profile_use_scale=False, profile_use_pan=False,
                             profile_use_cuts=False,
                             profile_use_transform=False,
                             profile_use_rotation=False,
                             profile_use_color_map=False)

        # ICC profile support
        d = dict(icc_output_profile=None, icc_output_intent='perceptual',
                 icc_proof_profile=None, icc_proof_intent='perceptual',
                 icc_black_point_compensation=False)
        self.t_.add_defaults(**d)
        for key in d:
            self.t_.get_setting(key).add_callback('set', self.icc_profile_cb)

        # viewer profile support
        self.use_image_profile = False
        self.profile_keylist = ['flip_x', 'flip_y', 'swap_xy', 'scale',
                                'pan', 'pan_coord', 'rot_deg', 'cuts',
                                'color_algorithm', 'color_hashsize',
                                'color_map', 'intensity_map',
                                'color_array', 'shift_array']
        for name in self.t_.keys():
            self.t_.get_setting(name).add_callback('set',
                                                   self._update_profile_cb)

        # Object that calculates auto cut levels
        name = self.t_.get('autocut_method', 'zscale')
        klass = AutoCuts.get_autocuts(name)
        self.autocuts = klass(self.logger)

        self.vip = vip.ViewerImageProxy(self)

        # PRIVATE IMPLEMENTATION STATE

        # flag indicating whether our size has been set
        self._imgwin_set = False
        self._imgwin_wd = 0
        self._imgwin_ht = 0
        # desired size
        # on gtk, this seems to set a boundary on the lower size, so we
        # default to very small, set it larger with set_desired_size()
        #self._desired_size = (300, 300)
        self._desired_size = (1, 1)

        # viewer window backend has its canvas origin (0, 0) in upper left
        self.origin_upper = True
        # offset of pixel 0 from data coordinates
        # (pixels are centered on the coordinate)
        self.data_off = 0.5

        self._invert_y = True

        # optimization of redrawing
        self.defer_redraw = self.t_.get('defer_redraw', True)
        self.defer_lagtime = self.t_.get('defer_lagtime', 0.025)
        self.time_last_redraw = time.time()
        self._defer_whence = 0
        self._defer_whence_reset = 5
        self._defer_lock = threading.RLock()
        self._defer_flag = False
        self._hold_redraw_cnt = 0
        self.suppress_redraw = SuppressRedraw(self)

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0

        self.orient_map = {
            # tag: (flip_x, flip_y, swap_xy)
            1: (False, True, False),
            2: (True, True, False),
            3: (True, False, False),
            4: (False, False, False),
            5: (True, False, True),
            6: (True, True, True),
            7: (False, True, True),
            8: (False, False, True),
        }

        # our canvas
        self.canvas = DrawingCanvas()
        self.canvas.initialize(None, self, self.logger)
        self.canvas.add_callback('modified', self.canvas_changed_cb)
        self.canvas.set_surface(self)
        self.canvas.ui_set_active(True, viewer=self)

        # private canvas for drawing
        self.private_canvas = self.canvas

        # handle to image object on the image canvas
        self._imgobj = None
        self._canvas_img_tag = '__image'

        # set up basic transforms
        self.trcat = transform.get_catalog()
        self.tform = {}
        self.recalc_transforms(self.trcat)

        self.coordmap = {
            'native': coordmap.NativeMapper(self),
            'window': coordmap.WindowMapper(self),
            'percentage': coordmap.PercentageMapper(self),
            'cartesian': coordmap.CartesianMapper(self),
            'data': coordmap.DataMapper(self),
            None: coordmap.DataMapper(self),
            'offset': coordmap.OffsetMapper(self, None),
            'wcs': coordmap.WCSMapper(self),
        }

        # cursors
        self.cursor = {}

        # setup default fg color
        color = self.t_.get('color_fg', "#D0F0E0")
        r, g, b = colors.lookup_color(color)
        self.img_fg = (r, g, b)

        # setup default bg color
        color = self.t_.get('color_bg', "#404040")
        r, g, b = colors.lookup_color(color)
        self.img_bg = (r, g, b)

        # For callbacks
        for name in ('transform', 'image-set', 'image-unset', 'configure',
                     'redraw', 'limits-set', 'cursor-changed'):
            self.enable_callback(name)

        # for timed refresh
        self.rf_fps = 1
        self.rf_rate = 1.0 / self.rf_fps
        self.rf_timer = self.make_timer()
        self.rf_flags = {}
        self.rf_draw_count = 0
        self.rf_delta_total = 0.0
        self.rf_timer_count = 0
        self.rf_start_time = 0.0
        self.rf_late_warn_time = 0.0
        self.rf_late_warn_interval = 10.0
        self.rf_late_total = 0.0
        self.rf_late_count = 0
        self.rf_early_total = 0.0
        self.rf_early_count = 0
        self.rf_skip_total = 0.0
        if self.rf_timer is not None:
            self.rf_timer.add_callback('expired', self.refresh_timer_cb,
                                       self.rf_flags)

    def set_window_size(self, width, height):
        """Report the size of the window to display the image.

        **Callbacks**

        Will call any callbacks registered for the ``'configure'`` event.
        Callbacks should have a method signature of::

            (viewer, width, height, ...)

        .. note::

            This is called by the subclass with ``width`` and ``height``
            as soon as the actual dimensions of the allocated window are known.

        Parameters
        ----------
        width : int
            The width of the window in pixels.

        height : int
            The height of the window in pixels.

        """
        width, height = int(width), int(height)
        self._imgwin_wd = width
        self._imgwin_ht = height
        self.logger.debug("widget resized to %dx%d" % (width, height))

        self.renderer.resize((width, height))

        self.make_callback('configure', width, height)

    def configure(self, width, height):
        """See :meth:`set_window_size`."""
        self._imgwin_set = True
        self.set_window_size(width, height)

    def configure_surface(self, width, height):
        """See :meth:`configure`."""
        # legacy API--to be deprecated
        self.configure(width, height)

    def set_desired_size(self, width, height):
        """See :meth:`set_window_size`."""
        self._desired_size = (width, height)
        if not self._imgwin_set:
            self.set_window_size(width, height)

    def get_desired_size(self):
        """Get desired size.

        Returns
        -------
        size : tuple
            Desired size in the form of ``(width, height)``.

        """
        return self._desired_size

    def get_window_size(self):
        """Get the window size in the underlying implementation.

        Returns
        -------
        size : tuple
            Window size in the form of ``(width, height)``.

        """
        return (self._imgwin_wd, self._imgwin_ht)

    def get_dims(self, data):
        """Get the first two dimensions of Numpy array data.
        Data may have more dimensions, but they are not reported.

        Parameter
        ---------
        data : ndarray
            A numpy array with at least two dimensions

        Returns
        -------
        dims : tuple
            Data dimensions in the form of ``(width, height)``.

        """
        height, width = data.shape[:2]
        return (width, height)

    def get_settings(self):
        """Get the settings used by this instance.

        Returns
        -------
        settings : `~ginga.misc.Settings.SettingGroup`
            Settings.

        """
        return self.t_

    def get_logger(self):
        """Get the logger used by this instance.

        Returns
        -------
        logger : :py:class:`~logging.Logger`
            Logger.

        """
        return self.logger

    def get_vip(self):
        """Get the ViewerImageProxy object used by this instance.

        Returns
        -------
        vip : `~ginga.util.vip.ViewerImageProxy`
            A ViewerImageProxy object.

        """
        return self.vip

    def set_renderer(self, renderer):
        """Set and initialize the renderer used by this instance.
        """
        self.renderer = renderer
        width, height = self.get_window_size()
        if width > 0 and height > 0:
            renderer.resize((width, height))

    def get_canvas(self):
        """Get the canvas object used by this instance.

        Returns
        -------
        canvas : `~ginga.canvas.types.layer.DrawingCanvas`
            Canvas.

        """
        return self.canvas

    def set_canvas(self, canvas, private_canvas=None):
        """Set the canvas object.

        Parameters
        ----------
        canvas : `~ginga.canvas.types.layer.DrawingCanvas`
            Canvas object.

        private_canvas : `~ginga.canvas.types.layer.DrawingCanvas` or `None`
            Private canvas object. If not given, this is the same as ``canvas``.

        """
        self.canvas = canvas
        canvas.initialize(None, self, self.logger)
        canvas.add_callback('modified', self.canvas_changed_cb)
        canvas.set_surface(self)
        canvas.ui_set_active(True, viewer=self)

        self._imgobj = None

        # private canvas set?
        if private_canvas is not None:
            self.private_canvas = private_canvas
            self.initialize_private_canvas(self.private_canvas)

            if private_canvas != canvas:
                private_canvas.set_surface(self)
                private_canvas.ui_set_active(True, viewer=self)
                private_canvas.add_callback('modified', self.canvas_changed_cb)

        # sanity check that we have a private canvas, and if not,
        # set it to the "advertised" canvas
        if self.private_canvas is None:
            self.private_canvas = canvas
            self.initialize_private_canvas(self.private_canvas)

        # make sure private canvas has our non-private one added
        if (self.private_canvas != self.canvas) and (
                not self.private_canvas.has_object(canvas)):
            self.private_canvas.add(canvas)

    def get_private_canvas(self):
        """Get the private canvas object used by this instance.

        Returns
        -------
        canvas : `~ginga.canvas.types.layer.DrawingCanvas`
            Canvas.

        """
        return self.private_canvas

    def initialize_private_canvas(self, private_canvas):
        """Initialize the private canvas used by this instance.
        """
        if self.t_.get('show_pan_position', False):
            self.show_pan_mark(True)

        if self.t_.get('show_focus_indicator', False):
            self.show_focus_indicator(True)

    def set_color_map(self, cmap_name):
        """Set the color map.

        Available color map names can be discovered using
        :func:`~ginga.cmap.get_names`.

        Parameters
        ----------
        cmap_name : str
            The name of a color map.

        """
        self.t_.set(color_map=cmap_name)

    def set_intensity_map(self, imap_name):
        """Set the intensity map.

        Available intensity map names can be discovered using
        :func:`ginga.imap.get_names`.

        Parameters
        ----------
        imap_name :  str
            The name of an intensity map.

        """
        self.t_.set(intensity_map=imap_name)

    def set_color_algorithm(self, calg_name, **kwdargs):
        """Set the color distribution algorithm.

        Available color distribution algorithm names can be discovered using
        :func:`ginga.ColorDist.get_dist_names`.

        Parameters
        ----------
        calg_name : str
            The name of a color distribution algorithm.

        kwdargs : dict
            Keyword arguments for color distribution object
            (see `~ginga.ColorDist`).

        """
        # TEMP: ignore kwdargs
        self.t_.set(color_algorithm=calg_name)

    def get_color_algorithms(self):
        """Get available color distribution algorithm names.
        See :func:`ginga.ColorDist.get_dist_names`.

        """
        return ColorDist.get_dist_names()

    def set_cmap(self, cm):
        """Set color map.
        See :meth:`ginga.RGBMap.RGBMapper.set_cmap`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.set_cmap(cm)

    def invert_cmap(self):
        """Invert the color map.
        See :meth:`ginga.RGBMap.RGBMapper.invert_cmap`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.invert_cmap()

    def set_imap(self, im):
        """Set intensity map.
        See :meth:`ginga.RGBMap.RGBMapper.set_imap`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.set_imap(im)

    def set_calg(self, dist):
        """Set color distribution algorithm.
        See :meth:`ginga.RGBMap.RGBMapper.set_dist`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.set_dist(dist)

    def shift_cmap(self, pct):
        """Shift color map.
        See :meth:`ginga.RGBMap.RGBMapper.shift`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.shift(pct)

    def scale_and_shift_cmap(self, scale_pct, shift_pct):
        """Stretch and/or shrink the color map.
        See :meth:`ginga.RGBMap.RGBMapper.scale_and_shift`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.scale_and_shift(scale_pct, shift_pct)

    def restore_contrast(self):
        """Restores the color map from any stretch and/or shrinkage.
        See :meth:`ginga.RGBMap.RGBMapper.reset_sarr`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.reset_sarr()

    def restore_cmap(self):
        """Restores the color map from any rotation, stretch and/or shrinkage.
        See :meth:`ginga.RGBMap.RGBMapper.restore_cmap`.

        """
        rgbmap = self.get_rgbmap()
        rgbmap.restore_cmap()

    def rgbmap_cb(self, rgbmap):
        """Handle callback for when RGB map has changed."""
        self.logger.debug("RGB map has changed.")
        self.renderer.rgbmap_change(rgbmap)

    def get_rgbmap(self):
        """Get the RGB map object used by this instance.

        Returns
        -------
        rgbmap : `~ginga.RGBMap.RGBMapper`
            RGB map.

        """
        return self.rgbmap

    def set_rgbmap(self, rgbmap):
        """Set RGB map object used by this instance.
        It controls how the values in the image are mapped to color.

        Parameters
        ----------
        rgbmap : `~ginga.RGBMap.RGBMapper`
            RGB map.

        """
        self.rgbmap = rgbmap
        t_ = rgbmap.get_settings()
        t_.share_settings(self.t_, keylist=rgbmap.settings_keys)
        rgbmap.add_callback('changed', self.rgbmap_cb)

        self.renderer.rgbmap_change(rgbmap)

    def get_image(self):
        """Get the image currently being displayed.

        Returns
        -------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            Image object.

        """
        if self._imgobj is not None:
            # quick optimization
            return self._imgobj.get_image()

        canvas_img = self.get_canvas_image()
        return canvas_img.get_image()

    # for compatibility with other viewers
    get_dataobj = get_image

    def get_canvas_image(self):
        """Get canvas image object.

        Returns
        -------
        imgobj : `~ginga.canvas.types.image.NormImage`
            Normalized image sitting on the canvas.

        """
        if self._imgobj is not None:
            return self._imgobj

        try:
            # See if there is an image on the canvas
            self._imgobj = self.canvas.get_object_by_tag(self._canvas_img_tag)
            self._imgobj.add_callback('image-set', self._image_set_cb)

        except KeyError:
            # add a normalized image item to this canvas if we don't
            # have one already--then just keep reusing it
            NormImage = self.canvas.get_draw_class('normimage')

            self._imgobj = NormImage(0, 0, None, alpha=1.0,
                                     interpolation=None)
            self._imgobj.is_data = True
            self._imgobj.add_callback('image-set', self._image_set_cb)

        return self._imgobj

    def set_image(self, image, add_to_canvas=True):
        """Set an image to be displayed.

        If there is no error, the ``'image-unset'`` and ``'image-set'``
        callbacks will be invoked.

        Parameters
        ----------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            2D Image object.

        add_to_canvas : bool
            Add image to canvas.

        """
        if not self.viewable(image):
            raise ValueError("Wrong type of object to load: %s" % (
                str(type(image))))

        canvas_img = self.get_canvas_image()

        old_image = canvas_img.get_image()
        self.make_callback('image-unset', old_image)

        with self.suppress_redraw:

            # update viewer limits
            wd, ht = image.get_size()
            limits = ((-self.data_off, -self.data_off),
                      (float(wd - self.data_off),
                       float(ht - self.data_off)))
            self.t_.set(limits=limits)

            if add_to_canvas:
                try:
                    self.canvas.get_object_by_tag(self._canvas_img_tag)

                except KeyError:
                    self.canvas.add(canvas_img, tag=self._canvas_img_tag,
                                    redraw=False)

                # move image to bottom of layers
                self.canvas.lower_object(canvas_img)

            # this line should force the callback of _image_set_cb()
            canvas_img.set_image(image)

            self.canvas.update_canvas(whence=0)

    # for compatibility with other viewers
    set_dataobj = set_image

    def _image_set_cb(self, canvas_img, image):

        try:
            self.apply_profile_or_settings(image)

        except Exception as e:
            self.logger.error("Failed to initialize image: {}".format(e),
                              exc_info=True)

        # update our display if the image changes underneath us
        image.add_callback('modified', self._image_modified_cb)

        # out with the old, in with the new...
        self.make_callback('image-set', image)

    def reload_image(self):
        self.set_image(self.get_image())

    def apply_profile_or_settings(self, image):
        """Apply a profile to the viewer.

        Parameters
        ----------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            Image object.

        This function is used to initialize the viewer when a new image
        is loaded.  Either the embedded profile settings or the default
        settings are applied as specified in the channel preferences.
        """
        profile = image.get('profile', None)
        keylist = []
        with self.suppress_redraw:
            if profile is not None:
                if self.t_['profile_use_transform'] and 'flip_x' in profile:
                    keylist.extend(['flip_x', 'flip_y', 'swap_xy'])

                if self.t_['profile_use_scale'] and 'scale' in profile:
                    keylist.extend(['scale'])

                if self.t_['profile_use_pan'] and 'pan' in profile:
                    keylist.extend(['pan'])

                if self.t_['profile_use_rotation'] and 'rot_deg' in profile:
                    keylist.extend(['rot_deg'])

                if self.t_['profile_use_cuts'] and 'cuts' in profile:
                    keylist.extend(['cuts'])

                if self.t_['profile_use_color_map'] and 'color_map' in profile:
                    keylist.extend(['color_algorithm', 'color_hashsize',
                                    'color_map', 'intensity_map',
                                    'color_array', 'shift_array'])

                self.apply_profile(profile, keylist=keylist)

            # proceed with initialization that is not in the profile
            # initialize transforms
            if self.t_['auto_orient'] and 'flip_x' not in keylist:
                self.logger.debug(
                    "auto orient (%s)" % (self.t_['auto_orient']))
                self.auto_orient()

            # initialize scale
            if self.t_['autozoom'] != 'off' and 'scale' not in keylist:
                self.logger.debug("auto zoom (%s)" % (self.t_['autozoom']))
                self.zoom_fit(no_reset=True)

            # initialize pan position
            # NOTE: False a possible value from historical use
            if (self.t_['autocenter'] not in ('off', False) and
                'pan' not in keylist):
                self.logger.debug(
                    "auto center (%s)" % (self.t_['autocenter']))
                self.center_image(no_reset=True)

            # initialize cuts
            if self.t_['autocuts'] != 'off' and 'cuts' not in keylist:
                self.logger.debug("auto cuts (%s)" % (self.t_['autocuts']))
                self.auto_levels()

            # save the profile in the image
            if self.use_image_profile:
                self.checkpoint_profile()

    def apply_profile(self, profile, keylist=None):
        """Apply a profile to the viewer.

        Parameters
        ----------
        profile : `~ginga.misc.Settings.SettingGroup`

        This function is used to initialize the viewer to a known state.
        The keylist, if given, will limit the items to be transferred
        from the profile to viewer settings, otherwise all items are
        copied.
        """
        with self.suppress_redraw:
            profile.copy_settings(self.t_, keylist=keylist,
                                  callback=True)

    def capture_profile(self, profile):
        self.t_.copy_settings(profile)
        self.logger.debug("profile attributes set")

    def checkpoint_profile(self):
        profile = self.save_profile()
        self.capture_profile(profile)
        return profile

    def save_profile(self, **params):
        """Save the given parameters into profile settings.

        Parameters
        ----------
        params : dict
            Keywords and values to be saved.

        """
        image = self.get_image()
        if (image is None):
            return

        profile = image.get('profile', None)
        if profile is None:
            # If image has no profile then create one
            profile = Settings.SettingGroup()
            image.set(profile=profile)

        self.logger.debug("saving to image profile: params=%s" % (
            str(params)))
        profile.set(**params)
        return profile

    def _update_profile_cb(self, setting, value):
        key = setting.name
        if self.use_image_profile:
            # ? and key in self.profile_keylist
            kwargs = {key: value}
            self.save_profile(**kwargs)

    def _image_modified_cb(self, image):

        canvas_img = self.get_canvas_image()
        image2 = canvas_img.get_image()
        if image is not image2:
            # not the image we are now displaying, perhaps a former image
            return

        with self.suppress_redraw:

            # update viewer limits
            wd, ht = image.get_size()
            limits = ((-self.data_off, -self.data_off),
                      (float(wd - self.data_off),
                       float(ht - self.data_off)))
            self.t_.set(limits=limits)

            canvas_img.reset_optimize()

            # Per issue #111, zoom and pan and cuts probably should
            # not change if the image is _modified_, or it should be
            # optional--these settings are only for _new_ images
            # UPDATE: don't zoom/pan (assuming image size, etc. hasn't
            # changed), but *do* apply cuts
            try:
                self.logger.debug("image data updated")
                ## if self.t_['auto_orient']:
                ##     self.auto_orient()

                ## if self.t_['autozoom'] != 'off':
                ##     self.zoom_fit(no_reset=True)

                ## if not self.t_['autocenter'] in ('off', False):
                ##     self.center_image()

                if self.t_['autocuts'] != 'off':
                    self.auto_levels()

            except Exception as e:
                self.logger.error("Failed to initialize image: %s" % (str(e)))
                try:
                    # log traceback, if possible
                    (type, value, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.error("Traceback:\n%s" % (tb_str))
                except Exception:
                    tb_str = "Traceback information unavailable."
                    self.logger.error(tb_str)

            self.canvas.update_canvas(whence=0)

    def set_data(self, data, metadata=None):
        """Set an image to be displayed by providing raw data.

        This is a convenience method for first constructing an image
        with `~ginga.AstroImage.AstroImage` and then calling :meth:`set_image`.

        Parameters
        ----------
        data : ndarray
            This should be at least a 2D Numpy array.

        metadata : dict or `None`
            Image metadata mapping keywords to their respective values.

        """
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      logger=self.logger)
        self.set_image(image)

    def clear(self):
        """Clear the displayed image."""
        self._imgobj = None
        try:
            # See if there is an image on the canvas
            self.canvas.delete_object_by_tag(self._canvas_img_tag)
            self.redraw()
        except KeyError:
            pass

    def copy_to_dst(self, target):
        """Extract our image and call :meth:`set_image` on the target with it.

        Parameters
        ----------
        target
            Subclass of `ImageViewBase`.

        """
        image = self.get_image()
        target.set_image(image)

    def redraw(self, whence=0):
        """Redraw the canvas.

        Parameters
        ----------
        whence : int or float
            Optimization flag that reduces the time to refresh the
            viewer by only recalculating what is necessary:

                0: New image, pan/scale has changed
                1: Cut levels or similar has changed
                2: Color mapping has changed
                2.3: ICC profile has changed
                2.5: Transforms have changed
                2.6: Rotation has changed
                3: Graphical overlays have changed

        """
        with self._defer_lock:
            whence = min(self._defer_whence, whence)

            if not self.defer_redraw:
                if self._hold_redraw_cnt == 0:
                    self._defer_whence = self._defer_whence_reset
                    self.redraw_now(whence=whence)
                else:
                    self._defer_whence = whence
                return

            elapsed = time.time() - self.time_last_redraw

            # If there is no redraw scheduled, or we are overdue for one:
            if (not self._defer_flag) or (elapsed > self.defer_lagtime):
                # If more time than defer_lagtime has passed since the
                # last redraw then just do the redraw immediately
                if elapsed > self.defer_lagtime:
                    if self._hold_redraw_cnt > 0:
                        #self._defer_flag = True
                        self._defer_whence = whence
                        return

                    self._defer_whence = self._defer_whence_reset
                    self.logger.debug("lagtime expired--forced redraw")
                    self.redraw_now(whence=whence)
                    return

                # Indicate that a redraw is necessary and record whence
                self._defer_flag = True
                self._defer_whence = whence

                # schedule a redraw by the end of the defer_lagtime
                secs = self.defer_lagtime - elapsed
                self.logger.debug("defer redraw (whence=%.2f) in %.f sec" % (
                    whence, secs))
                self.reschedule_redraw(secs)

            else:
                # A redraw is already scheduled.  Just record whence.
                self._defer_whence = whence
                self.logger.debug("update whence=%.2f" % (whence))

    def is_redraw_pending(self):
        """Indicates whether a deferred redraw has been scheduled.

        Returns
        -------
        pending : bool
            True if a deferred redraw is pending, False otherwise.

        """
        return self._defer_whence < self._defer_whence_reset

    def canvas_changed_cb(self, canvas, whence):
        """Handle callback for when canvas has changed."""
        self.logger.debug("root canvas changed, whence=%d" % (whence))

        # special check for whether image changed out from under us in
        # a shared canvas scenario
        try:
            # See if there is an image on the canvas
            canvas_img = self.canvas.get_object_by_tag(self._canvas_img_tag)
            if self._imgobj is not canvas_img:
                self._imgobj = canvas_img
                self._imgobj.add_callback('image-set', self._image_set_cb)

                self._image_set_cb(canvas_img, canvas_img.get_image())

        except KeyError:
            self._imgobj = None

        self.redraw(whence=whence)

    def delayed_redraw(self):
        """Handle delayed redrawing of the canvas."""

        # This is the optimized redraw method
        with self._defer_lock:
            # pick up the lowest necessary level of redrawing
            whence = self._defer_whence
            self._defer_whence = self._defer_whence_reset
            flag = self._defer_flag
            self._defer_flag = False

        if flag:
            # If a redraw was scheduled, do it now
            self.redraw_now(whence=whence)

    def set_redraw_lag(self, lag_sec):
        """Set lag time for redrawing the canvas.

        Parameters
        ----------
        lag_sec : float
            Number of seconds to wait.

        """
        self.defer_redraw = (lag_sec > 0.0)
        if self.defer_redraw:
            self.defer_lagtime = lag_sec

    def set_refresh_rate(self, fps):
        """Set the refresh rate for redrawing the canvas at a timed interval.

        Parameters
        ----------
        fps : float
            Desired rate in frames per second.

        """
        self.rf_fps = fps
        self.rf_rate = 1.0 / self.rf_fps
        #self.set_redraw_lag(self.rf_rate)
        self.logger.info("set a refresh rate of %.2f fps" % (self.rf_fps))

    def start_refresh(self):
        """Start redrawing the canvas at the previously set timed interval.
        """
        self.logger.debug("starting timed refresh interval")
        self.rf_flags['done'] = False
        self.rf_draw_count = 0
        self.rf_timer_count = 0
        self.rf_late_count = 0
        self.rf_late_total = 0.0
        self.rf_early_count = 0
        self.rf_early_total = 0.0
        self.rf_delta_total = 0.0
        self.rf_skip_total = 0.0
        self.rf_start_time = time.time()
        self.rf_deadline = self.rf_start_time
        self.refresh_timer_cb(self.rf_timer, self.rf_flags)

    def stop_refresh(self):
        """Stop redrawing the canvas at the previously set timed interval.
        """
        self.logger.debug("stopping timed refresh")
        self.rf_flags['done'] = True
        self.rf_timer.clear()

    def get_refresh_stats(self):
        """Return the measured statistics for timed refresh intervals.

        Returns
        -------
        stats : float
            The measured rate of actual back end updates in frames per second.

        """
        if self.rf_draw_count == 0:
            fps = 0.0
        else:
            interval = time.time() - self.rf_start_time
            fps = self.rf_draw_count / interval

        jitter = self.rf_delta_total / max(1, self.rf_timer_count)

        late_avg = self.rf_late_total / max(1, self.rf_late_count)
        late_pct = self.rf_late_count / max(1.0, float(self.rf_timer_count)) * 100

        early_avg = self.rf_early_total / max(1, self.rf_early_count)
        early_pct = self.rf_early_count / max(1.0, float(self.rf_timer_count)) * 100

        balance = self.rf_late_total - self.rf_early_total

        stats = dict(fps=fps, jitter=jitter,
                     early_avg=early_avg, early_pct=early_pct,
                     late_avg=late_avg, late_pct=late_pct,
                     balance=balance)
        return stats

    def refresh_timer_cb(self, timer, flags):
        """Refresh timer callback.
        This callback will normally only be called internally.

        Parameters
        ----------
        timer : a Ginga GUI timer
            A GUI-based Ginga timer

        flags : dict-like
            A set of flags controlling the timer
        """
        # this is the timer call back, from the GUI thread
        start_time = time.time()

        if flags.get('done', False):
            return

        # calculate next deadline
        deadline = self.rf_deadline
        self.rf_deadline += self.rf_rate

        self.rf_timer_count += 1
        delta = abs(start_time - deadline)
        self.rf_delta_total += delta
        adjust = 0.0

        if start_time > deadline:
            # we are late
            self.rf_late_total += delta
            self.rf_late_count += 1
            late_avg = self.rf_late_total / self.rf_late_count
            adjust = - (late_avg / 2.0)
            self.rf_skip_total += delta
            if self.rf_skip_total < self.rf_rate:
                self.rf_draw_count += 1
                # TODO: can we optimize whence?
                self.redraw_now(whence=0)
            else:
                # <-- we are behind by amount of time equal to one frame.
                # skip a redraw and attempt to catch up some time
                self.rf_skip_total = 0
        else:
            if start_time < deadline:
                # we are early
                self.rf_early_total += delta
                self.rf_early_count += 1
                self.rf_skip_total = max(0.0, self.rf_skip_total - delta)
                early_avg = self.rf_early_total / self.rf_early_count
                adjust = early_avg / 4.0

            self.rf_draw_count += 1
            # TODO: can we optimize whence?
            self.redraw_now(whence=0)

        delay = max(0.0, self.rf_deadline - time.time() + adjust)
        timer.start(delay)

    def redraw_now(self, whence=0):
        """Redraw the displayed image.

        Parameters
        ----------
        whence
            See :meth:`redraw`.

        """
        try:
            time_start = time.time()
            self.renderer.initialize()

            self.redraw_data(whence=whence)

            self.renderer.finalize()

            # finally update the window drawable from the offscreen surface
            self.update_widget()

            time_done = time.time()
            time_delta = time_start - self.time_last_redraw
            time_elapsed = time_done - time_start
            self.time_last_redraw = time_done
            self.logger.debug(
                "widget '%s' redraw (whence=%d) delta=%.4f elapsed=%.4f sec" % (
                    self.name, whence, time_delta, time_elapsed))

        except Exception as e:
            self.logger.error("Error redrawing image: %s" % (str(e)))
            try:
                # log traceback, if possible
                (type, value, tb) = sys.exc_info()
                tb_str = "".join(traceback.format_tb(tb))
                self.logger.error("Traceback:\n%s" % (tb_str))
            except Exception:
                tb_str = "Traceback information unavailable."
                self.logger.error(tb_str)

    def redraw_data(self, whence=0):
        """Render image from RGB map and redraw private canvas.

        .. note::

            Do not call this method unless you are implementing a subclass.

        Parameters
        ----------
        whence
            See :meth:`redraw`.

        """
        if not self._imgwin_set:
            # window has not been realized yet
            return

        self._whence = whence
        self.renderer.render_whence(whence)

        self.private_canvas.draw(self)

        self.make_callback('redraw', whence)

        if whence < 3:
            self.check_cursor_location()

    def check_cursor_location(self):
        """Check whether the data location of the last known position
        of the cursor has changed.  If so, issue a callback.
        """
        # Check whether cursor data position has changed relative
        # to previous value
        data_x, data_y = self.get_data_xy(self.last_win_x,
                                          self.last_win_y)
        if (data_x != self.last_data_x or
            data_y != self.last_data_y):
            self.last_data_x, self.last_data_y = data_x, data_y
            self.logger.debug("cursor location changed %.4f,%.4f => %.4f,%.4f" % (
                self.last_data_x, self.last_data_y, data_x, data_y))

            # we make this call compatible with the motion callback
            # for now, but there is no concept of a button here
            button = 0

            self.make_ui_callback('cursor-changed', button, data_x, data_y)

        return data_x, data_y

    def getwin_array(self, order='RGB', alpha=1.0, dtype=None):
        return self.renderer.getwin_array(order=order, alpha=alpha,
                                          dtype=dtype)

    def getwin_buffer(self, order='RGB', alpha=1.0, dtype=None):
        """Same as :meth:`getwin_array`, but with the output array converted
        to C-order Python bytes.

        """
        outarr = self.renderer.getwin_array(order=order, alpha=alpha,
                                            dtype=dtype)

        if not hasattr(outarr, 'tobytes'):
            # older versions of numpy
            return outarr.tostring(order='C')
        return outarr.tobytes(order='C')

    def get_limits(self, coord='data'):
        """Get the bounding box of the viewer extents.

        Returns
        -------
        limits : tuple
            Bounding box in coordinates of type `coord` in the form of
               ``(ll_pt, ur_pt)``.

        """
        limits = self.t_['limits']

        if limits is None:
            # No user defined limits.
            # Calculate limits based on plotted points, if any
            canvas = self.get_canvas()
            pts = canvas.get_points()
            if len(pts) > 0:
                limits = trcalc.get_bounds(pts)
            else:
                # No limits found, go to default
                limits = ((0.0, 0.0), (0.0, 0.0))

        # convert to desired coordinates
        crdmap = self.get_coordmap(coord)
        limits = crdmap.data_to(limits)

        return limits

    def set_limits(self, limits, coord='data'):
        """Set the bounding box of the viewer extents.

        Parameters
        ----------
        limits : tuple or None
            A tuple setting the extents of the viewer in the form of
            ``(ll_pt, ur_pt)``.
        """
        if limits is not None:
            if len(limits) != 2:
                raise ValueError("limits takes a 2 tuple, or None")

            # convert to data coordinates
            crdmap = self.get_coordmap(coord)
            limits = crdmap.to_data(limits)

        self.t_.set(limits=limits)

    def reset_limits(self):
        """Reset the bounding box of the viewer extents.

        Parameters
        ----------
        None
        """
        self.t_.set(limits=None)

    def _set_limits_cb(self, setting, limits):
        self.renderer.limits_change(limits)

        # TODO: deprecate this chained callback and have users just use
        # 'set' callback for "limits" setting ?
        self.make_callback('limits-set', limits)

    def icc_profile_cb(self, setting, value):
        """Handle callback related to changes in output ICC profiles."""
        self.renderer.icc_profile_change()

    def get_data_pt(self, win_pt):
        """Similar to :meth:`get_data_xy`, except that it takes a single
        array of points.

        """
        return self.tform['mouse_to_data'].to_(win_pt)

    def get_data_xy(self, win_x, win_y, center=None):
        """Get the closest coordinates in the data array to those
        reported on the window.

        Parameters
        ----------
        win_x, win_y : float or ndarray
            Window coordinates.

        center : bool
            If `True`, then the coordinates are mapped such that the
            pixel is centered on the square when the image is zoomed in past
            1X. This is the specification of the FITS image standard,
            that the pixel is centered on the integer row/column.

        Returns
        -------
        coord : tuple
            Data coordinates in the form of ``(x, y)``.

        """
        if center is not None:
            self.logger.warning("`center` keyword is ignored and will be deprecated")

        arr_pts = np.asarray((win_x, win_y)).T
        return self.tform['mouse_to_data'].to_(arr_pts).T[:2]

    def offset_to_data(self, off_x, off_y, center=None):
        """Get the closest coordinates in the data array to those
        in cartesian fixed (non-scaled) canvas coordinates.

        Parameters
        ----------
        off_x, off_y : float or ndarray
            Cartesian canvas coordinates.

        Returns
        -------
        coord : tuple
            Data coordinates in the form of ``(x, y)``.

        """
        if center is not None:
            self.logger.warning("`center` keyword is ignored and will be deprecated")

        arr_pts = np.asarray((off_x, off_y)).T
        return self.tform['data_to_cartesian'].from_(arr_pts).T[:2]

    def get_canvas_pt(self, data_pt):
        """Similar to :meth:`get_canvas_xy`, except that it takes a single
        array of points.

        """
        return self.tform['data_to_native'].to_(data_pt)

    def get_canvas_xy(self, data_x, data_y, center=None):
        """Reverse of :meth:`get_data_xy`.

        """
        if center is not None:
            self.logger.warning("`center` keyword is ignored and will be deprecated")

        arr_pts = np.asarray((data_x, data_y)).T
        return self.tform['data_to_native'].to_(arr_pts).T[:2]

    def data_to_offset(self, data_x, data_y, center=None):
        """Reverse of :meth:`offset_to_data`.

        """
        if center is not None:
            self.logger.warning("`center` keyword is ignored and will be deprecated")

        arr_pts = np.asarray((data_x, data_y)).T
        return self.tform['data_to_cartesian'].to_(arr_pts).T[:2]

    def offset_to_window(self, off_x, off_y):
        """Convert data offset to window coordinates.

        Parameters
        ----------
        off_x, off_y : float or ndarray
            Data offsets.

        Returns
        -------
        coord : tuple
            Offset in window coordinates in the form of ``(x, y)``.

        """
        arr_pts = np.asarray((off_x, off_y)).T
        return self.tform['cartesian_to_native'].to_(arr_pts).T[:2]

    def window_to_offset(self, win_x, win_y):
        """Reverse of :meth:`offset_to_window`."""
        arr_pts = np.asarray((win_x, win_y)).T
        return self.tform['cartesian_to_native'].from_(arr_pts).T[:2]

    def canvascoords(self, data_x, data_y, center=None):
        """Same as :meth:`get_canvas_xy`.

        """
        if center is not None:
            self.logger.warning("`center` keyword is ignored and will be deprecated")

        # data->canvas space coordinate conversion
        arr_pts = np.asarray((data_x, data_y)).T
        return self.tform['data_to_native'].to_(arr_pts).T[:2]

    def get_data_size(self):
        """Get the dimensions of the image currently being displayed.

        Returns
        -------
        size : tuple
            Image dimensions in the form of ``(width, height)``.

        """
        xy_mn, xy_mx = self.get_limits()
        ht = abs(xy_mx[1] - xy_mn[1])
        wd = abs(xy_mx[0] - xy_mn[0])
        return (wd, ht)

    def get_data_pct(self, xpct, ypct):
        """Calculate new data size for the given axis ratios.
        See :meth:`get_limits`.

        Parameters
        ----------
        xpct, ypct : float
            Ratio for X and Y, respectively, where 1 is 100%.

        Returns
        -------
        x, y : int
            Scaled dimensions.

        """
        wd, ht = self.get_data_size()
        x, y = int(float(xpct) * wd), int(float(ypct) * ht)
        return (x, y)

    def get_pan_rect(self):
        """Get the coordinates in the actual data corresponding to the
        area shown in the display for the current zoom level and pan.

        Returns
        -------
        points : list
            Coordinates in the form of
            ``[(x0, y0), (x1, y1), (x2, y2), (x3, y3)]``
            from lower-left to lower-right.

        """
        wd, ht = self.get_window_size()
        win_pts = np.asarray([(0, 0), (wd, 0), (wd, ht), (0, ht)])
        arr_pts = self.tform['data_to_window'].from_(win_pts)
        return arr_pts

    def get_draw_rect(self):
        """Get the coordinates in the actual data corresponding to the
        area needed for drawing images for the current zoom level and pan.
        Unlike get_pan_rect(), this includes areas outside of the
        current viewport, but that might be viewed with a transformation
        or rotation subsequently applied.

        Returns
        -------
        points : list
            Coordinates in the form of
            ``[(x0, y0), (x1, y1), (x2, y2), (x3, y3)]``
            corresponding to the four corners.

        """
        wd, ht = self.get_window_size()
        radius = int(np.ceil(math.sqrt(wd**2 + ht**2) * 0.5))
        ctr_x, ctr_y = self.get_center()[:2]
        win_pts = np.asarray([(ctr_x - radius, ctr_y - radius),
                              (ctr_x + radius, ctr_y - radius),
                              (ctr_x + radius, ctr_y + radius),
                              (ctr_x - radius, ctr_y + radius)])
        arr_pts = self.tform['data_to_window'].from_(win_pts)
        return arr_pts

    def get_datarect(self):
        """Get the approximate LL and UR corners of the displayed image.

        Returns
        -------
        rect : tuple
            Bounding box in data coordinates in the form of
            ``(x1, y1, x2, y2)``.

        """
        # get the data points in the four corners
        a, b = trcalc.get_bounds(self.get_pan_rect())

        # determine bounding box
        x1, y1 = a[:2]
        x2, y2 = b[:2]
        return (x1, y1, x2, y2)

    def get_data(self, data_x, data_y):
        """Get the data value at the given position.
        Indices are zero-based, as in Numpy.

        Parameters
        ----------
        data_x, data_y : int
            Data indices for X and Y, respectively.

        Returns
        -------
        value
            Data value.
        """
        return self.vip.get_data_xy(data_x, data_y)

    def get_pixel_distance(self, x1, y1, x2, y2):
        """Calculate distance between the given pixel positions.

        Parameters
        ----------
        x1, y1, x2, y2 : number
            Pixel coordinates.

        Returns
        -------
        dist : float
            Rounded distance.

        """
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dist = np.sqrt(dx * dx + dy * dy)
        dist = np.round(dist)
        return dist

    def _sanity_check_scale(self, scale_x, scale_y):
        """Do a sanity check on the proposed scale vs. window size.
        Raises an exception if there will be a problem.
        """
        win_wd, win_ht = self.get_window_size()
        if (win_wd <= 0) or (win_ht <= 0):
            raise ImageViewError("window size undefined")

        # final sanity check on resulting output image size
        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            if self.settings.get('sanity_check_scale', True):
                raise ValueError(
                    "resulting scale (%f, %f) would result in pixel size "
                    "approaching window size" % (scale_x, scale_y))

    def _reset_bbox(self):
        """This function should only be called internally.  It resets
        the viewers bounding box based on changes to pan or scale.
        """
        scale_x, scale_y = self.get_scale_xy()
        pan_x, pan_y = self.get_pan(coord='data')[:2]
        win_wd, win_ht = self.get_window_size()
        # NOTE: need to set at least a minimum 1-pixel dimension on
        # the window or we get a scale calculation exception. See github
        # issue 431
        win_wd, win_ht = max(1, win_wd), max(1, win_ht)

        self.renderer._confirm_pan_and_scale(scale_x, scale_y,
                                             pan_x, pan_y, win_wd, win_ht)

    def set_scale(self, scale, no_reset=False):
        """Scale the image in a channel.
        Also see :meth:`zoom_to`.

        Parameters
        ----------
        scale : tuple of float
            Scaling factors for the image in the X and Y axes.

        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        return self.scale_to(*scale[:2], no_reset=no_reset)

    def scale_to(self, scale_x, scale_y, no_reset=False):
        """Scale the image in a channel.
        This only changes the viewer settings; the image is not modified
        in any way.  Also see :meth:`zoom_to`.

        Parameters
        ----------
        scale_x, scale_y : float
            Scaling factors for the image in the X and Y axes, respectively.

        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        try:
            self._sanity_check_scale(scale_x, scale_y)

        except Exception as e:
            self.logger.warning("Error in scaling: %s" % (str(e)))
            return

        ratio = float(scale_x) / float(scale_y)
        if ratio < 1.0:
            # Y is stretched
            scale_x_base, scale_y_base = 1.0, 1.0 / ratio
        else:
            # X may be stretched
            scale_x_base, scale_y_base = ratio, 1.0

        self.t_.set(scale_x_base=scale_x_base, scale_y_base=scale_y_base)

        self._scale_to(scale_x, scale_y, no_reset=no_reset)

    def _scale_to(self, scale_x, scale_y, no_reset=False):
        # Check scale limits
        maxscale = max(scale_x, scale_y)
        max_lim = self.t_.get('scale_max', None)
        if (max_lim is not None) and (maxscale > max_lim):
            self.logger.warning("Scale (%.2f) exceeds max scale limit (%.2f)" % (
                maxscale, self.t_['scale_max']))
            # TODO: exception?
            return

        minscale = min(scale_x, scale_y)
        min_lim = self.t_.get('scale_min', None)
        if (min_lim is not None) and (minscale < min_lim):
            self.logger.warning("Scale (%.2f) exceeds min scale limit (%.2f)" % (
                minscale, self.t_['scale_min']))
            # TODO: exception?
            return

        # Sanity check on the scale vs. window size
        try:
            self._sanity_check_scale(scale_x, scale_y)

        except Exception as e:
            self.logger.warning("Error in scaling: %s" % (str(e)))
            return

        with self.suppress_redraw:
            self.t_.set(scale=(scale_x, scale_y))

        # If user specified "override" or "once" for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_['autozoom'] in ('override', 'once')):
            self.t_.set(autozoom='off')

    def scale_cb(self, setting, value):
        """Handle callback related to image scaling."""
        self._reset_bbox()
        zoomlevel = self.zoom.calc_level(value)
        self.t_.set(zoomlevel=zoomlevel)

        self.renderer.scale(value)

    def get_scale(self):
        """Same as :meth:`get_scale_max`."""
        return self.get_scale_max()

    def get_scale_max(self):
        """Get maximum scale factor.

        Returns
        -------
        scalefactor : float
            Scale factor for X or Y, whichever is larger.

        """
        scale = self.get_scale_xy()
        scalefactor = max(*scale)
        return scalefactor

    def get_scale_min(self):
        """Get minimum scale factor.

        Returns
        -------
        scalefactor : float
            Scale factor for X or Y, whichever is smaller.

        """
        scale = self.get_scale_xy()
        scalefactor = min(*scale)
        return scalefactor

    def get_scale_xy(self):
        """Get scale factors.

        Returns
        -------
        scalefactors : tuple
            Scale factors for X and Y, in that order.

        """
        return self.t_['scale'][:2]

    def get_scale_base_xy(self):
        """Get stretch factors.

        Returns
        -------
        stretchfactors : tuple
            Stretch factors for X and Y, in that order.

        """
        return (self.t_['scale_x_base'], self.t_['scale_y_base'])

    def set_scale_base_xy(self, scale_x_base, scale_y_base):
        """Set stretch factors.

        Parameters
        ----------
        scale_x_base, scale_y_base : float
            Stretch factors for X and Y, respectively.

        """
        self.t_.set(scale_x_base=scale_x_base, scale_y_base=scale_y_base)

    def get_scale_text(self):
        """Report current scaling in human-readable format.

        Returns
        -------
        text : str
            ``'<num> x'`` if enlarged, or ``'1/<num> x'`` if shrunken.

        """
        scalefactor = self.get_scale_max()
        if scalefactor >= 1.0:
            text = '%.2fx' % (scalefactor)
        else:
            text = '1/%.2fx' % (1.0 / scalefactor)
        return text

    def zoom_to(self, zoomlevel, no_reset=False):
        """Set zoom level in a channel.
        This only changes the relevant settings; The image is not modified.
        Also see :meth:`scale_to`.

        .. note::

            In addition to the given zoom level, other zoom settings are
            defined for the channel in preferences.

        Parameters
        ----------
        zoomlevel : int
            The zoom level to zoom the image.
            Negative value to zoom out; positive to zoom in.

        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        scale_x, scale_y = self.zoom.calc_scale(zoomlevel)
        self._scale_to(scale_x, scale_y, no_reset=no_reset)

    def zoom_in(self, incr=1.0):
        """Zoom in a level.
        Also see :meth:`zoom_to`.

        Parameters
        ----------
        incr : float (optional, defaults to 1)
            The value to increase the zoom level

        """
        level = self.zoom.calc_level(self.t_['scale'])
        self.zoom_to(level + incr)

    def zoom_out(self, decr=1.0):
        """Zoom out a level.
        Also see :meth:`zoom_to`.

        Parameters
        ----------
        decr : float (optional, defaults to 1)
            The value to decrease the zoom level

        """
        level = self.zoom.calc_level(self.t_['scale'])
        self.zoom_to(level - decr)

    def zoom_fit(self, axis='lock', no_reset=False):
        """Zoom to fit display window.
        Pan the image and scale the view to fit the size of the set
        limits (usually set to the image size).  Parameter `axis` can
        be used to set which axes are allowed to be scaled; if set to
        'lock' then all axes are scaled in such a way as to keep the
        scale factor uniform between axes.  Also see :meth:`zoom_to`.

        Parameters
        ----------
        axis : str
            One of: 'x', 'y', 'xy', or 'lock' (default).

        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        # calculate actual width of the limits/image, considering rotation
        xy_mn, xy_mx = self.get_limits()

        try:
            wwidth, wheight = self.get_window_size()
            self.logger.debug("Window size is %dx%d" % (wwidth, wheight))
            if self.t_['swap_xy']:
                wwidth, wheight = wheight, wwidth
        except Exception:
            return

        # zoom_fit also centers image
        with self.suppress_redraw:

            opan_x, opan_y = self.get_pan()[:2]
            pan_x = (xy_mn[0] + xy_mx[0]) * 0.5
            pan_y = (xy_mn[1] + xy_mx[1]) * 0.5

            if axis == 'x':
                pan_y = opan_y
            elif axis == 'y':
                pan_x = opan_x

            self.panset_xy(pan_x, pan_y, no_reset=no_reset)

            ctr_x, ctr_y, rot_deg = self.get_rotation_info()

            # Find min/max extents of limits as shown by viewer
            xs = np.array((xy_mn[0], xy_mx[0], xy_mx[0], xy_mn[0]))
            ys = np.array((xy_mn[1], xy_mn[1], xy_mx[1], xy_mx[1]))
            x0, y0 = trcalc.rotate_pt(xs, ys, rot_deg, xoff=ctr_x, yoff=ctr_y)

            min_x, min_y = np.min(x0), np.min(y0)
            max_x, max_y = np.max(x0), np.max(y0)

            width, height = max_x - min_x, max_y - min_y
            if min(width, height) <= 0:
                return

            # Calculate optimum zoom level to still fit the window size
            scale_x = (float(wwidth) /
                       (float(width) * self.t_['scale_x_base']))
            scale_y = (float(wheight) /
                       (float(height) * self.t_['scale_y_base']))

            oscale_x, oscale_y = self.get_scale_xy()

            # account for t_[scale_x/y_base]
            if axis == 'x':
                scale_x *= self.t_['scale_x_base']
                scale_y = oscale_y
            elif axis == 'y':
                scale_x = oscale_x
                scale_y *= self.t_['scale_y_base']
            elif axis == 'xy':
                scale_x *= self.t_['scale_x_base']
                scale_y *= self.t_['scale_y_base']
            else:
                scalefactor = min(scale_x, scale_y)
                scale_x = scalefactor * self.t_['scale_x_base']
                scale_y = scalefactor * self.t_['scale_y_base']

            self._scale_to(scale_x, scale_y, no_reset=no_reset)

        if self.t_['autozoom'] == 'once':
            self.t_.set(autozoom='off')

    def get_zoom(self):
        """Get zoom level.

        Returns
        -------
        zoomlevel : float
            Zoom level.

        """
        return self.zoom.calc_level(self.t_['scale'])

    def get_zoomrate(self):
        """Get zoom rate.

        Returns
        -------
        zoomrate : float
            Zoom rate.

        """
        return self.t_['zoom_rate']

    def set_zoomrate(self, zoomrate):
        """Set zoom rate.

        Parameters
        ----------
        zoomrate : float
            Zoom rate.

        """
        self.t_.set(zoom_rate=zoomrate)

    def get_zoom_algorithm(self):
        """Get zoom algorithm.

        Returns
        -------
        name : str
            Name of the zoom algorithm in use.

        """
        return str(self.zoom)

    def set_zoom_algorithm(self, name):
        """Set zoom algorithm.

        Parameters
        ----------
        name : str
            Name of a zoom algorithm to use.

        """
        name = name.lower()
        alg_names = list(zoom.get_zoom_alg_names())
        if name not in alg_names:
            raise ImageViewError("Alg '%s' must be one of: %s" % (
                name, ', '.join(alg_names)))
        self.t_.set(zoom_algorithm=name)

    def zoomsetting_change_cb(self, setting, value):
        """Handle callback related to changes in zoom."""
        alg_name = self.t_['zoom_algorithm']
        self.zoom = zoom.get_zoom_alg(alg_name)(self)

        self.zoom_to(self.get_zoom(), no_reset=True)

    def interpolation_change_cb(self, setting, value):
        """Handle callback related to changes in interpolation."""
        self.renderer.interpolation_change(value)

    def set_name(self, name):
        """Set viewer name."""
        self.name = name

    def get_scale_limits(self):
        """Get scale limits.

        Returns
        -------
        scale_limits : tuple
            Minimum and maximum scale limits, respectively.

        """
        return (self.t_['scale_min'], self.t_['scale_max'])

    def set_scale_limits(self, scale_min, scale_max):
        """Set scale limits.

        Parameters
        ----------
        scale_min, scale_max : float
            Minimum and maximum scale limits, respectively.

        """
        # TODO: force scale to within limits if already outside?
        self.t_.set(scale_min=scale_min, scale_max=scale_max)

    def enable_autozoom(self, option):
        """Set ``autozoom`` behavior.

        Parameters
        ----------
        option : {'on', 'override', 'once', 'off'}
            Option for zoom behavior. A list of acceptable options can
            also be obtained by :meth:`get_autozoom_options`.

        Raises
        ------
        ginga.ImageView.ImageViewError
            Invalid option.

        """
        option = option.lower()
        if option not in self.autozoom_options:
            raise ImageViewError("Bad autozoom option '%s': must be one of %s" % (
                str(self.autozoom_options)))
        self.t_.set(autozoom=option)

    def get_autozoom_options(self):
        """Get all valid ``autozoom`` options.

        Returns
        -------
        autozoom_options : tuple
            A list of valid options.

        """
        return self.autozoom_options

    def set_pan(self, pan_x, pan_y, coord='data', no_reset=False):
        """Set pan position.

        Parameters
        ----------
        pan_x, pan_y : float
            Pan positions in X and Y.

        coord : {'data', 'wcs'}
            Indicates whether the given pan positions are in data or WCS space.

        no_reset : bool
            Do not reset ``autocenter`` setting.

        """
        pan_pos = (pan_x, pan_y)

        with self.suppress_redraw:
            self.t_.set(pan=pan_pos, pan_coord=coord)

        # If user specified "override" or "once" for auto center, then turn off
        # auto center now that they have set the pan manually
        if (not no_reset) and (self.t_['autocenter'] in ('override', 'once')):
            self.t_.set(autocenter='off')

    def pan_cb(self, setting, value):
        """Handle callback related to changes in pan."""
        self._reset_bbox()
        pan_x, pan_y = value[:2]

        self.logger.debug("pan set to %.2f,%.2f" % (pan_x, pan_y))
        self.renderer.pan(value)

    def get_pan(self, coord='data'):
        """Get pan positions.

        Parameters
        ----------
        coord : {'data', 'wcs'}
            Indicates whether the pan positions are returned in
            data or WCS space.

        Returns
        -------
        positions : tuple
            X and Y positions, in that order.

        """
        pan_x, pan_y = self.t_['pan'][:2]
        if coord == 'wcs':
            if self.t_['pan_coord'] == 'data':
                image = self.get_image()
                if image is not None:
                    try:
                        return image.pixtoradec(pan_x, pan_y)
                    except Exception as e:
                        pass
            # <-- data already in coordinates form
            return (pan_x, pan_y)

        # <-- requesting data coords
        if self.t_['pan_coord'] == 'data':
            return (pan_x, pan_y)
        image = self.get_image()
        if image is not None:
            try:
                return image.radectopix(pan_x, pan_y)
            except Exception as e:
                pass
        return (pan_x, pan_y)

    def panset_xy(self, data_x, data_y, no_reset=False):
        """Similar to :meth:`set_pan`, except that input pan positions
        are always in data space.

        """
        pan_coord = self.t_['pan_coord']
        # To center on the pixel
        if pan_coord == 'wcs':
            image = self.get_image()
            if image is None:
                return
            pan_x, pan_y = image.pixtoradec(data_x, data_y)
        else:
            pan_x, pan_y = data_x, data_y

        self.set_pan(pan_x, pan_y, coord=pan_coord, no_reset=no_reset)

    def panset_pct(self, pct_x, pct_y):
        """Similar to :meth:`set_pan`, except that pan positions
        are determined by multiplying data dimensions with the given
        scale factors, where 1 is 100%.

        """
        xy_mn, xy_mx = self.get_limits()

        data_x = (xy_mn[0] + xy_mx[0]) * pct_x
        data_y = (xy_mn[1] + xy_mx[1]) * pct_y

        self.panset_xy(data_x, data_y)

    def position_at_canvas_xy(self, data_pt, canvas_pt, no_reset=False):
        """Position a data point at a certain canvas position.
        Calculates and sets the pan position necessary to position a
        data point precisely at a point on the canvas.

        Parameters
        ----------
        data_pt : tuple
            data point to position, must include x and y (x, y).

        canvas_pt : tuple
            canvas coordinate (cx, cy) where data point should end up.

        no_reset : bool
            See :meth:`set_pan`.

        """
        # get current data point at desired canvas position
        cx, cy = canvas_pt[:2]
        data_cx, data_cy = self.get_data_xy(cx, cy)

        # calc deltas from pan position to desired pos in data coords
        pan_x, pan_y = self.get_pan()
        dx, dy = pan_x - data_cx, pan_y - data_cy

        # calc pan position to set by offsetting data_pt by the
        # deltas
        data_x, data_y = data_pt[:2]
        self.panset_xy(data_x + dx, data_y + dy, no_reset=no_reset)

    def center_image(self, no_reset=True):
        """Pan to the center of the image.

        Parameters
        ----------
        no_reset : bool
            See :meth:`set_pan`.

        """
        xy_mn, xy_mx = self.get_limits()

        data_x = (xy_mn[0] + xy_mx[0]) * 0.5
        data_y = (xy_mn[1] + xy_mx[1]) * 0.5

        self.panset_xy(data_x, data_y, no_reset=no_reset)

        if self.t_['autocenter'] == 'once':
            self.t_.set(autocenter='off')

    def enable_autocenter(self, option):
        """Set ``autocenter`` behavior.

        Parameters
        ----------
        option : {'on', 'override', 'once', 'off'}
            Option for auto-center behavior. A list of acceptable options can
            also be obtained by :meth:`get_autocenter_options`.

        Raises
        ------
        ginga.ImageView.ImageViewError
            Invalid option.

        """
        option = option.lower()
        assert(option in self.autocenter_options), \
            ImageViewError("Bad autocenter option '%s': must be one of %s" % (
                str(self.autocenter_options)))
        self.t_.set(autocenter=option)

    set_autocenter = enable_autocenter

    def get_autocenter_options(self):
        """Get all valid ``autocenter`` options.

        Returns
        -------
        autocenter_options : tuple
            A list of valid options.

        """
        return self.autocenter_options

    def get_transforms(self):
        """Get transformations behavior.

        Returns
        -------
        transforms : tuple
            Selected options for ``flip_x``, ``flip_y``, and ``swap_xy``.

        """
        return (self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy'])

    def get_cut_levels(self):
        """Get cut levels.

        Returns
        -------
        cuts : tuple
            Low and high values, in that order.

        """
        return self.t_['cuts']

    def cut_levels(self, loval, hival, no_reset=False):
        """Apply cut levels on the image view.

        Parameters
        ----------
        loval, hival : float
            Low and high values of the cut levels, respectively.

        no_reset : bool
            Do not reset ``autocuts`` setting.

        """
        self.t_.set(cuts=(loval, hival))

        # If user specified "override" or "once" for auto levels,
        # then turn off auto levels now that they have set the levels
        # manually
        if (not no_reset) and (self.t_['autocuts'] in ('once', 'override')):
            self.t_.set(autocuts='off')

    def auto_levels(self, autocuts=None):
        """Apply auto-cut levels on the image view.

        Parameters
        ----------
        autocuts : subclass of `~ginga.AutoCuts.AutoCutsBase` or `None`
            An object that implements the desired auto-cut algorithm.
            If not given, use algorithm from preferences.

        """
        if autocuts is None:
            autocuts = self.autocuts

        image = self.get_vip()
        if image is None:
            #image = self.vip
            return

        loval, hival = autocuts.calc_cut_levels(image)

        # this will invoke cut_levels_cb()
        self.t_.set(cuts=(loval, hival))

        # If user specified "once" for auto levels, then turn off
        # auto levels now that we have cut levels established
        if self.t_['autocuts'] == 'once':
            self.t_.set(autocuts='off')

    def autocut_params_cb(self, setting, value):
        """Handle callback related to changes in auto-cut levels."""
        # Did we change the method?
        if setting.name == 'autocut_method':
            method = self.t_['autocut_method']
            if method != str(self.autocuts):
                ac_class = AutoCuts.get_autocuts(method)
                self.autocuts = ac_class(self.logger)

        elif setting.name == 'autocut_params':
            params = self.t_.get('autocut_params', [])
            params = dict(params)
            self.autocuts.update_params(**params)

        # Redo the auto levels
        #if self.t_['autocuts'] != 'off':
        # NOTE: users seem to expect that when the auto cuts parameters
        # are changed that the cuts should be immediately recalculated
        self.auto_levels()

    def cut_levels_cb(self, setting, value):
        """Handle callback related to changes in cut levels."""
        self.renderer.levels_change(value)

    def enable_autocuts(self, option):
        """Set ``autocuts`` behavior.

        Parameters
        ----------
        option : {'on', 'override', 'once', 'off'}
            Option for auto-cut behavior. A list of acceptable options can
            also be obtained by :meth:`get_autocuts_options`.

        Raises
        ------
        ginga.ImageView.ImageViewError
            Invalid option.

        """
        option = option.lower()
        assert(option in self.autocuts_options), \
            ImageViewError("Bad autocuts option '%s': must be one of %s" % (
                str(self.autocuts_options)))
        self.t_.set(autocuts=option)

    def get_autocuts_options(self):
        """Get all valid ``autocuts`` options.

        Returns
        -------
        autocuts_options : tuple
            A list of valid options.

        """
        return self.autocuts_options

    def set_autocut_params(self, method, **params):
        """Set auto-cut parameters.

        Parameters
        ----------
        method : str
            Auto-cut algorithm.  A list of acceptable options can
            be obtained by :meth:`get_autocut_methods`.

        params : dict
            Algorithm-specific keywords and values.

        """
        self.logger.debug("Setting autocut params method=%s params=%s" % (
            method, str(params)))
        # NOTE: we need to do them sequentially in this order because
        # if params is set before method, they might be some parameters
        # that are incompatible with the current method. We want to be sure
        # the method is set first
        self.t_.set(autocut_method=method, autocut_params=[])
        params = list(params.items())
        self.t_.set(autocut_params=params)

    def get_autocut_methods(self):
        """Same as :meth:`ginga.AutoCuts.AutoCutsBase.get_algorithms`."""
        return self.autocuts.get_algorithms()

    def set_autocuts(self, autocuts):
        """Set the auto-cut algorithm.

        Parameters
        ----------
        autocuts : subclass of `~ginga.AutoCuts.AutoCutsBase`
            An object that implements the desired auto-cut algorithm.

        """
        self.autocuts = autocuts

    def transform(self, flip_x, flip_y, swap_xy):
        """Transform view of the image.

        .. note::

            Transforming the image is generally faster than rotating,
            if rotating in 90 degree increments. Also see :meth:`rotate`.

        Parameters
        ----------
        flipx, flipy : bool
            If `True`, flip the image in the X and Y axes, respectively

        swapxy : bool
            If `True`, swap the X and Y axes.

        """
        self.logger.debug("flip_x=%s flip_y=%s swap_xy=%s" % (
            flip_x, flip_y, swap_xy))

        with self.suppress_redraw:
            self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)

    def transform_cb(self, setting, value):
        """Handle callback related to changes in transformations."""
        self.make_callback('transform')

        state = (self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy'])
        self.renderer.transform_2d(state)

    def copy_attributes(self, dst_fi, attrlist, share=False, whence=0):
        """Copy interesting attributes of our configuration to another
        image view.

        Parameters
        ----------
        dst_fi : subclass of `ImageViewBase`
            Another instance of image view.

        attrlist : list
            A list of attribute names to copy. They can be ``'transforms'``,
            ``'rotation'``, ``'cutlevels'``, ``'rgbmap'``, ``'zoom'``,
            ``'pan'``, ``'autocuts'``, ``'limits'``, ``'icc'`` or
            ``'interpolation'``.

        share : bool
            If True, the designated settings will be shared, otherwise the
            values are simply copied.
        """
        # TODO: change API to just go with settings names?
        keylist = []
        _whence = 3.0

        if whence <= 0.0:
            if 'limits' in attrlist:
                keylist.extend(['limits'])
                _whence = min(_whence, 0.0)

            if 'zoom' in attrlist:
                keylist.extend(['scale'])
                _whence = min(_whence, 0.0)

            if 'interpolation' in attrlist:
                keylist.extend(['interpolation'])
                _whence = min(_whence, 0.0)

            if 'pan' in attrlist:
                keylist.extend(['pan'])
                _whence = min(_whence, 0.0)

        if whence <= 1.0:
            if 'autocuts' in attrlist:
                keylist.extend(['autocut_method', 'autocut_params'])
                _whence = min(_whence, 1.0)

            if 'cutlevels' in attrlist:
                keylist.extend(['cuts'])
                _whence = min(_whence, 1.0)

        if whence <= 2.0:
            if 'rgbmap' in attrlist:
                keylist.extend(['color_algorithm', 'color_hashsize',
                                'color_map', 'intensity_map',
                                'color_array', 'shift_array'])
                _whence = min(_whence, 2.0)

        if whence <= 2.3:
            if 'icc' in attrlist:
                keylist.extend(['icc_output_profile', 'icc_output_intent',
                                'icc_proof_profile', 'icc_proof_intent',
                                'icc_black_point_compensation'])
                _whence = min(_whence, 2.3)

        if whence <= 2.5:
            if 'transforms' in attrlist:
                keylist.extend(['flip_x', 'flip_y', 'swap_xy'])
                _whence = min(_whence, 2.5)

        if whence <= 2.6:
            if 'rotation' in attrlist:
                keylist.extend(['rot_deg'])
                _whence = min(_whence, 2.6)

        whence = max(_whence, whence)

        with dst_fi.suppress_redraw:
            if share:
                self.t_.share_settings(dst_fi.get_settings(),
                                       keylist=keylist)
            else:
                self.t_.copy_settings(dst_fi.get_settings(),
                                      keylist=keylist)

    def get_rotation(self):
        """Get image rotation angle.

        Returns
        -------
        rot_deg : float
            Rotation angle in degrees.

        """
        return self.t_['rot_deg']

    def rotate(self, deg):
        """Rotate the view of an image in a channel.

        .. note::

            Transforming the image is generally faster than rotating,
            if rotating in 90 degree increments. Also see :meth:`transform`.

        Parameters
        ----------
        deg : float
            Rotation angle in degrees.

        """
        self.t_.set(rot_deg=deg)

    def rotation_change_cb(self, setting, value):
        """Handle callback related to changes in rotation angle."""
        self.renderer.rotate_2d(value)

    def get_center(self):
        """Get image center.

        Returns
        -------
        ctr : tuple
            X and Y positions, in that order.

        """
        center = self.renderer.get_window_center()[:2]
        return center

    def get_rgb_order(self):
        """Get RGB order.

        Returns
        -------
        rgb : str
            Returns the order of RGBA planes required by the subclass
            to render the canvas properly.

        """
        return self.rgb_order

    def get_rotation_info(self):
        """Get rotation information.

        Returns
        -------
        info : tuple
            X and Y positions, and rotation angle in degrees, in that order.

        """
        win_x, win_y = self.get_center()
        return (win_x, win_y, self.t_['rot_deg'])

    def enable_auto_orient(self, tf):
        """Set ``auto_orient`` behavior.

        Parameters
        ----------
        tf : bool
            Turns automatic image orientation on or off.

        """
        self.t_.set(auto_orient=tf)

    def auto_orient(self):
        """Set the orientation for the image to a reasonable default."""
        image = self.get_image()
        if image is None:
            return
        invert_y = not isinstance(image, AstroImage.AstroImage)

        # Check for various things to set based on metadata
        header = image.get_header()
        if header:
            # Auto-orientation
            orient = header.get('Orientation', None)
            if orient is None:
                orient = header.get('Image Orientation', None)
            if orient is not None:
                self.logger.debug("orientation [%s]" % orient)
                try:
                    orient = int(str(orient))
                    self.logger.info(
                        "setting orientation from metadata [%d]" % (orient))
                    flip_x, flip_y, swap_xy = self.orient_map[orient]

                    self.transform(flip_x, flip_y, swap_xy)
                    invert_y = False

                except Exception as e:
                    # problems figuring out orientation--let it be
                    self.logger.error("orientation error: %s" % str(e))

        if invert_y:
            flip_x, flip_y, swap_xy = self.get_transforms()
            #flip_y = not flip_y
            flip_y = True
            self.transform(flip_x, flip_y, swap_xy)

    def get_coordmap(self, key):
        """Get coordinate mapper.

        Parameters
        ----------
        key : str
            Name of the desired coordinate mapper.

        Returns
        -------
        mapper
            Coordinate mapper object (see `ginga.canvas.coordmap`).

        """
        return self.coordmap[key]

    def set_coordmap(self, key, mapper):
        """Set coordinate mapper.

        Parameters
        ----------
        key : str
            Name of the coordinate mapper.

        mapper
            Coordinate mapper object (see `ginga.canvas.coordmap`).

        """
        self.coordmap[key] = mapper

    def recalc_transforms(self, trcat=None):
        """Takes a catalog of transforms (`trcat`) and builds the chain
        of default transforms necessary to do rendering with most backends.

        """
        if trcat is None:
            trcat = self.trcat

        self.tform = {
            'window_to_native': trcat.WindowNativeTransform(self),
            'cartesian_to_window': trcat.CartesianWindowTransform(self),
            'cartesian_to_native': (trcat.RotationFlipTransform(self) +
                                    trcat.CartesianNativeTransform(self)),
            'data_to_cartesian': (trcat.DataCartesianTransform(self) +
                                  trcat.ScaleTransform(self)),
            'data_to_scrollbar': (trcat.DataCartesianTransform(self) +
                                  trcat.RotationFlipTransform(self)),
            'mouse_to_data': (
                trcat.InvertedTransform(trcat.DataCartesianTransform(self) +
                                        trcat.ScaleTransform(self) +
                                        trcat.RotationFlipTransform(self) +
                                        trcat.CartesianNativeTransform(self))),
            'data_to_window': (trcat.DataCartesianTransform(self) +
                               trcat.ScaleTransform(self) +
                               trcat.RotationFlipTransform(self) +
                               trcat.CartesianWindowTransform(self)),
            'data_to_percentage': (trcat.DataCartesianTransform(self) +
                                   trcat.ScaleTransform(self) +
                                   trcat.RotationFlipTransform(self) +
                                   trcat.CartesianWindowTransform(self) +
                                   trcat.WindowPercentageTransform(self)),
            'data_to_native': (trcat.DataCartesianTransform(self) +
                               trcat.ScaleTransform(self) +
                               trcat.RotationFlipTransform(self) +
                               trcat.CartesianNativeTransform(self)),
            'wcs_to_data': trcat.WCSDataTransform(self),
            'wcs_to_native': (trcat.WCSDataTransform(self) +
                              trcat.DataCartesianTransform(self) +
                              trcat.ScaleTransform(self) +
                              trcat.RotationFlipTransform(self) +
                              trcat.CartesianNativeTransform(self)),
        }

    def set_bg(self, r, g, b):
        """Set the background color.

        Parameters
        ----------
        r, g, b : float
            RGB values, which should be between 0 and 1, inclusive.

        """
        self.set_background((r, g, b))

    def set_background(self, bg):
        """Set the background color.

        Parameters
        ----------
        bg : str or tuple of float
            color name or tuple of floats, between 0 and 1, inclusive.

        """
        self.img_bg = colors.resolve_color(bg)
        self.renderer.bg_change(self.img_bg)

    def get_bg(self):
        """Get the background color.

        Returns
        -------
        img_bg : tuple
            RGB values.

        """
        return self.img_bg

    def set_fg(self, r, g, b):
        """Set the foreground color.

        Parameters
        ----------
        r, g, b : float
            RGB values, which should be between 0 and 1, inclusive.

        """
        self.set_foreground((r, g, b))

    def set_foreground(self, fg):
        """Set the foreground color.

        Parameters
        ----------
        fg : str or tuple of float
            color name or tuple of floats, between 0 and 1, inclusive.

        """
        self.img_fg = colors.resolve_color(fg)
        self.renderer.fg_change(self.img_fg)

    def get_fg(self):
        """Get the foreground color.

        Returns
        -------
        img_fg : tuple
            RGB values.

        """
        return self.img_fg

    def is_compound(self):
        """Indicate if canvas object is a compound object.
        This can be re-implemented by subclasses that can overplot objects.

        Returns
        -------
        status : bool
            Currently, this *always* returns `False`.

        """
        return False

    def window_has_origin_upper(self):
        """Indicate if window of backend toolkit is implemented with an
        origin up or down.

        Returns
        -------
        res : bool
            Returns `True` if the origin is up, `False` otherwise.

        """
        return self.origin_upper

    def get_last_win_xy(self):
        """Get the last position of the cursor in window coordinates.
        This can be overridden by subclasses, if necessary.

        """
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        """Get the last position of the cursor in data coordinates.
        This can be overridden by subclasses, if necessary.

        """
        return (self.last_data_x, self.last_data_y)

    def onscreen_message(self, text, delay=None, redraw=True):
        """Place a message onscreen in the viewer window.
        This must be implemented by subclasses.

        Parameters
        ----------
        text : str
            the text to draw in the window

        delay : float or None
            if None, the message will remain until another message is
            set.  If a float, specifies the time in seconds before the
            message will be erased.  (default: None)

        redraw : bool
            True if the widget should be redrawn right away (so that
            the message appears).  (default: True)

        """
        self.logger.warning("Subclass should override this abstract method!")

    def onscreen_message_off(self):
        """Erase any message onscreen in the viewer window.

        """
        return self.onscreen_message(None)

    def set_enter_focus(self, tf):
        """Determine whether the viewer widget should take focus when the
        cursor enters the window.

        Parameters
        ----------
        tf : bool
            If True the widget will grab focus when the cursor moves into
            the window.
        """
        self.t_.set(enter_focus=tf)

    def update_widget(self):
        """Update the area corresponding to the backend widget.
        This must be implemented by subclasses.

        """
        self.logger.warning("Subclass should override this abstract method!")

    # TO BE DEPRECATED--please use update_widget
    def update_image(self):
        return self.update_widget()

    def reschedule_redraw(self, time_sec):
        """Reschedule redraw event.

        This should be implemented by subclasses.

        Parameters
        ----------
        time_sec : float
            Time, in seconds, to wait.

        """
        # subclass implements this method to call delayed_redraw() after
        # time_sec.  If subclass does not override, redraw is immediate.
        self.delayed_redraw()

    def set_cursor(self, cursor):
        """Set the cursor in the viewer widget.
        This should be implemented by subclasses.

        Parameters
        ----------
        cursor : object
            a cursor object in the back end's toolkit

        """
        self.logger.warning("Subclass should override this abstract method!")

    def make_timer(self):
        """Return a timer object implemented using the back end.
        This should be implemented by subclasses.

        Returns
        -------
        timer : a Timer object

        """
        #self.logger.warning("Subclass should override this abstract method!")
        return None

    def make_cursor(self, iconpath, x, y):
        """Make a cursor in the viewer's native widget toolkit.
        This should be implemented by subclasses.

        Parameters
        ----------
        iconpath : str
            the path to a PNG image file defining the cursor

        x : int
            the X position of the center of the cursor hot spot

        y : int
            the Y position of the center of the cursor hot spot

        """
        self.logger.warning("Subclass should override this abstract method!")
        return None

    def center_cursor(self):
        """Center the cursor in the viewer's widget, in both X and Y.

        This should be implemented by subclasses.

        """
        self.logger.warning("Subclass should override this abstract method!")

    def position_cursor(self, data_x, data_y):
        """Position the current cursor to a location defined it data coords.
        This should be implemented by subclasses.

        Parameters
        ----------
        data_x : float
            the X position to position the cursor in data coords

        data_y : float
            the X position to position the cursor in data coords

        """
        self.logger.warning("Subclass should override this abstract method!")

    def get_cursor(self, cname):
        """Get the cursor stored under the name.
        This can be overridden by subclasses, if necessary.

        Parameters
        ----------
        cname : str
            name of the cursor to return.

        """
        return self.cursor[cname]

    def define_cursor(self, cname, cursor):
        """Define a viewer cursor under a name.  Does not change the
        current cursor.

        Parameters
        ----------
        cname : str
            name of the cursor to define.

        cursor : object
            a cursor object in the back end's toolkit

        `cursor` is usually constructed from `make_cursor`.
        """
        self.cursor[cname] = cursor

    def switch_cursor(self, cname):
        """Switch the viewer's cursor to the one defined under a name.

        Parameters
        ----------
        cname : str
            name of the cursor to switch to.

        """
        self.set_cursor(self.cursor[cname])

    def prepare_image(self, cvs_img, cache, whence):
        """This can be overridden by subclasses.
        """
        self.renderer.prepare_image(cvs_img, cache, whence)

    def get_image_as_array(self, order=None):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a numpy array with channels as needed and ordered.

        This can be overridden by subclasses.
        """
        if order is None:
            order = self.rgb_order
        return self.renderer.get_surface_as_array(order=order)

    def get_image_as_buffer(self, output=None, order=None):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a IO buffer with channels as needed and ordered
        by the back end widget.

        This can be overridden by subclasses.

        Parameters
        ----------
        output : a file IO-like object or None
            open python IO descriptor or None to have one created

        Returns
        -------
        buffer : file IO-like object
            This will be the one passed in, unless `output` is None
            in which case a BytesIO obejct is returned

        """
        obuf = output
        if obuf is None:
            obuf = BytesIO()

        arr8 = self.get_image_as_array(order=order)
        if not hasattr(arr8, 'tobytes'):
            # older versions of numpy
            obuf.write(arr8.tostring(order='C'))
        else:
            obuf.write(arr8.tobytes(order='C'))

        ## if output is not None:
        ##     return None
        return obuf

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a file IO-like object encoded as a bitmap graphics
        file.

        This can be overridden by subclasses.

        Parameters
        ----------
        output : a file IO-like object or None
            open python IO descriptor or None to have one created

        format : str
            A string defining the format to save the image.  Typically
            at least 'jpeg' and 'png' are supported. (default: 'png')

        quality: int
            The quality metric for saving lossy compressed formats.

        Returns
        -------
        buffer : file IO-like object
            This will be the one passed in, unless `output` is None
            in which case a BytesIO obejct is returned

        """
        return self.renderer.get_surface_as_rgb_format_buffer(
            output=output, format=format, quality=quality)

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in the form of a buffer in the form of bytes.

        Parameters
        ----------
        format : str
            See :meth:`get_rgb_image_as_buffer`.

        quality: int
            See :meth:`get_rgb_image_as_buffer`.

        Returns
        -------
        buffer : bytes
            The window contents as a buffer in the form of bytes.

        """
        obuf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return bytes(obuf.getvalue())

    def get_rgb_image_as_widget(self, output=None, format='png',
                                quality=90):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in the form of a image widget in the toolkit of the
        back end.

        Parameters
        ----------
        See :meth:`get_rgb_image_as_buffer`.

        Returns
        -------
        widget : object
            An image widget object in the viewer's back end toolkit

        """
        raise ImageViewError("Subclass should override this abstract method!")

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        """Save the current image shown in the viewer, with any overlaid
        graphics, in a file with the specified format and quality.
        This can be overridden by subclasses.

        Parameters
        ----------
        filepath : str
            path of the file to write

        format : str
            See :meth:`get_rgb_image_as_buffer`.

        quality: int
            See :meth:`get_rgb_image_as_buffer`.

        """
        with open(filepath, 'wb') as out_f:
            self.get_rgb_image_as_buffer(output=out_f, format=format,
                                         quality=quality)
        self.logger.debug("wrote %s file '%s'" % (format, filepath))

    def get_plain_image_as_widget(self):
        """Get the current image shown in the viewer, without any overlaid
        graphics, in the format of an image widget in the back end toolkit.
        Typically used for generating thumbnails.
        This should be implemented by subclasses.

        Returns
        -------
        widget : object
            An image widget object in the viewer's back end toolkit

        """
        raise ImageViewError("Subclass should override this abstract method!")

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Save the current image shown in the viewer, without any overlaid
        graphics, in a file with the specified format and quality.
        Typically used for generating thumbnails.
        This should be implemented by subclasses.

        Parameters
        ----------
        filepath : str
            path of the file to write

        format : str
            See :meth:`get_rgb_image_as_buffer`.

        quality: int
            See :meth:`get_rgb_image_as_buffer`.

        """
        raise ImageViewError("Subclass should override this abstract method!")

    def take_focus(self):
        """Have the widget associated with this viewer take the keyboard
        focus.
        This should be implemented by subclasses, if they have a widget that
        can take focus.
        """
        pass

    def set_onscreen_message(self, text, redraw=True):
        """Called by a subclass to update the onscreen message.

        Parameters
        ----------
        text : str
            The text to show in the display.

        """
        width, height = self.get_window_size()

        font = self.t_.get('onscreen_font', 'sans serif')
        font_size = self.t_.get('onscreen_font_size', None)
        if font_size is None:
            font_size = self._calc_font_size(width)

        # TODO: need some way to accurately estimate text extents
        # without actually putting text on the canvas
        ht, wd = font_size, font_size
        if text is not None:
            wd = len(text) * font_size * 1.1

        x = (width // 2) - (wd // 2)
        y = ((height // 3) * 2) - (ht // 2)

        tag = '_$onscreen_msg'

        canvas = self.get_private_canvas()
        try:
            message = canvas.get_object_by_tag(tag)
            if text is None:
                message.text = ''
            else:
                message.x = x
                message.y = y
                message.text = text
                message.fontsize = font_size

        except KeyError:
            if text is None:
                text = ''
            Text = canvas.get_draw_class('text')
            canvas.add(Text(x, y, text=text,
                            font=font, fontsize=font_size,
                            color=self.img_fg, coord='window'),
                       tag=tag, redraw=False)

        if redraw:
            canvas.update_canvas(whence=3)

    def _calc_font_size(self, win_wd):
        """Heuristic to calculate an appropriate font size based on the
        width of the viewer window.

        Parameters
        ----------
        win_wd : int
            The width of the viewer window.

        Returns
        -------
        font_size : int
            Approximately appropriate font size in points

        """
        font_size = 4
        if win_wd >= 1600:
            font_size = 24
        elif win_wd >= 1000:
            font_size = 18
        elif win_wd >= 800:
            font_size = 16
        elif win_wd >= 600:
            font_size = 14
        elif win_wd >= 500:
            font_size = 12
        elif win_wd >= 400:
            font_size = 11
        elif win_wd >= 300:
            font_size = 10
        elif win_wd >= 250:
            font_size = 8
        elif win_wd >= 200:
            font_size = 6

        return font_size

    def show_pan_mark(self, tf, color='red'):
        # TO BE DEPRECATED--please use addons.show_pan_mark
        addons.show_pan_mark(self, tf, color=color)

    def show_mode_indicator(self, tf, corner='ur'):
        # TO BE DEPRECATED--please use addons.show_mode_indicator
        addons.show_mode_indicator(self, tf, corner=corner)

    def show_color_bar(self, tf, side='bottom'):
        # TO BE DEPRECATED--please use addons.show_color_bar
        addons.show_color_bar(self, tf, side=side)

    def show_focus_indicator(self, tf, color='white'):
        # TO BE DEPRECATED--please use addons.show_focus_indicator
        addons.show_focus_indicator(self, tf, color=color)


class SuppressRedraw(object):
    def __init__(self, viewer):
        self.viewer = viewer

    def __enter__(self):
        self.viewer._hold_redraw_cnt += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.viewer._hold_redraw_cnt -= 1

        if (self.viewer._hold_redraw_cnt <= 0):
            # whence should be largest possible
            whence = self.viewer._defer_whence
            self.viewer.redraw(whence=whence)
        return False


# END
