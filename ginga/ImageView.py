#
# ImageView.py -- base class for the display of image files
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""This module handles image viewers."""
import numpy
import math
import logging
import threading
import sys
import traceback
import time

from ginga.misc import Callback, Settings
from ginga import BaseImage, AstroImage
from ginga import RGBMap, AutoCuts, ColorDist
from ginga import cmap, imap, trcalc, version
from ginga.canvas import coordmap, transform
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util import io_rgb
from ginga.util.six.moves import map

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
    (e.g., Qt or GTK).

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

    def __init__(self, logger=None, rgbmap=None, settings=None):
        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('ImageViewBase')

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.t_ = settings

        # RGB mapper
        if rgbmap:
            self.rgbmap = rgbmap
        else:
            rgbmap = RGBMap.RGBMapper(self.logger)
            self.rgbmap = rgbmap

        # for debugging
        self.name = str(self)

        # for color mapping
        self.t_.addDefaults(color_map='gray', intensity_map='ramp',
                            color_algorithm='linear',
                            color_hashsize=65535)
        for name in ('color_map', 'intensity_map', 'color_algorithm',
                     'color_hashsize'):
            self.t_.getSetting(name).add_callback('set', self.cmap_changed_cb)

        # Initialize RGBMap
        cmap_name = self.t_.get('color_map', 'gray')
        try:
            cm = cmap.get_cmap(cmap_name)
        except KeyError:
            cm = cmap.get_cmap('gray')
        rgbmap.set_cmap(cm)
        imap_name = self.t_.get('intensity_map', 'ramp')
        try:
            im = imap.get_imap(imap_name)
        except KeyError:
            im = imap.get_imap('ramp')
        rgbmap.set_imap(im)
        hash_size = self.t_.get('color_hashsize', 65535)
        rgbmap.set_hash_size(hash_size)
        hash_alg = self.t_.get('color_algorithm', 'linear')
        rgbmap.set_hash_algorithm(hash_alg)

        rgbmap.add_callback('changed', self.rgbmap_cb)

        # for scale
        self.t_.addDefaults(scale=(1.0, 1.0))
        for name in ['scale']:
            self.t_.getSetting(name).add_callback('set', self.scale_cb)

        # for pan
        self.t_.addDefaults(pan=(1.0, 1.0), pan_coord='data')
        for name in ['pan', ]:   #'pan_coord'
            self.t_.getSetting(name).add_callback('set', self.pan_cb)

        # for cut levels
        self.t_.addDefaults(cuts=(0.0, 0.0))
        for name in ['cuts']:
            self.t_.getSetting(name).add_callback('set', self.cut_levels_cb)

        # for auto cut levels
        self.autocuts_options = ('on', 'override', 'once', 'off')
        self.t_.addDefaults(autocuts='override', autocut_method='zscale',
                            autocut_params=[])
        for name in ('autocut_method', 'autocut_params'):
            self.t_.getSetting(name).add_callback('set', self.auto_levels_cb)

        # for zooming
        self.t_.addDefaults(zoomlevel=1.0, zoom_algorithm='step',
                            scale_x_base=1.0, scale_y_base=1.0,
                            interpolation='basic',
                            zoom_rate=math.sqrt(2.0))
        for name in ('zoom_rate', 'zoom_algorithm',
                     'scale_x_base', 'scale_y_base'):
            self.t_.getSetting(name).add_callback('set', self.zoomalg_change_cb)
        self.t_.getSetting('interpolation').add_callback(
            'set', self.interpolation_change_cb)

        # max/min scaling
        self.t_.addDefaults(scale_max=10000.0, scale_min=0.00001)

        # autozoom options
        self.autozoom_options = ('on', 'override', 'once', 'off')
        self.t_.addDefaults(autozoom='on')

        # for panning
        self.autocenter_options = ('on', 'override', 'once', 'off')
        self.t_.addDefaults(autocenter='on')

        # for transforms
        self.t_.addDefaults(flip_x=False, flip_y=False, swap_xy=False)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.getSetting(name).add_callback('set', self.transform_cb)

        # desired rotation angle
        self.t_.addDefaults(rot_deg=0.0)
        self.t_.getSetting('rot_deg').add_callback(
            'set', self.rotation_change_cb)

        # misc
        self.t_.addDefaults(auto_orient=False,
                            defer_redraw=True, defer_lagtime=0.025,
                            show_pan_position=False,
                            show_mode_indicator=True,
                            show_focus_indicator=False,
                            onscreen_font='Sans Serif',
                            onscreen_font_size=24)

        # embedded image "profiles"
        self.t_.addDefaults(profile_use_scale=False, profile_use_pan=False,
                            profile_use_cuts=False, profile_use_transform=False,
                            profile_use_rotation=False)

        # ICC profile support
        d = dict(icc_output_profile=None, icc_output_intent='perceptual',
                 icc_proof_profile=None,  icc_proof_intent='perceptual',
                 icc_black_point_compensation=False)
        self.t_.addDefaults(**d)
        for key in d:
            # Note: transform_cb will redraw enough to pick up
            #       ICC profile change
            self.t_.getSetting(key).add_callback('set', self.transform_cb)

        # Object that calculates auto cut levels
        name = self.t_.get('autocut_method', 'zscale')
        klass = AutoCuts.get_autocuts(name)
        self.autocuts = klass(self.logger)

        # PRIVATE IMPLEMENTATION STATE

        # image window width and height (see set_window_dimensions())
        self._imgwin_wd = 0
        self._imgwin_ht = 0
        self._imgwin_set = False
        # desired size
        # on gtk, this seems to set a boundary on the lower size, so we
        # default to very small, set it larger with set_desired_size()
        #self._desired_size = (300, 300)
        self._desired_size = (1, 1)
        # center (and reference) pixel in the screen image (in pixel coords)
        self._ctr_x = 1
        self._ctr_y = 1
        # data indexes at the reference pixel (in data coords)
        self._org_x = 0
        self._org_y = 0
        # offset from pan position (at center) in this array
        self._org_xoff = 0
        self._org_yoff = 0
        # limits for data
        self._limits = None

        # offset of pixel 0 from data coordinates
        # (pixels are centered on the coordinate)
        self.data_off = 0.5

        # Origin in the data array of what is currently displayed (LL, UR)
        self._org_x1 = 0
        self._org_y1 = 0
        self._org_x2 = 0
        self._org_y2 = 0
        # offsets in the screen image for drawing (in screen coords)
        self._dst_x = 0
        self._dst_y = 0
        self._invertY = True
        self._originUpper = True
        self._self_scaling = False
        # offsets in the screen image (in data coords)
        self._off_x = 0
        self._off_y = 0

        # actual scale factors produced from desired ones
        self._org_scale_x = 1.0
        self._org_scale_y = 1.0

        self._rgbarr = None
        self._rgbarr2 = None
        self._rgbobj = None

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

        self.img_bg = (0.2, 0.2, 0.2)
        self.img_fg = (1.0, 1.0, 1.0)

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0

        self.orientMap = {
            # tag: (flip_x, flip_y, swap_xy)
            1: (False, True,  False),
            2: (True,  True,  False),
            3: (True,  False, False),
            4: (False, False, False),
            5: (True,  False, True),
            6: (True,  True,  True),
            7: (False, True,  True),
            8: (False, False, True),
            }

        # our canvas
        self.canvas = DrawingCanvas()
        self.canvas.initialize(None, self, self.logger)
        self.canvas.add_callback('modified', self.canvas_changed_cb)
        self.canvas.set_surface(self)
        self.canvas.ui_setActive(True)

        # private canvas for drawing
        self.private_canvas = self.canvas

        # handle to image object on the image canvas
        self._imgobj = None
        self._canvas_img_tag = '__image'

        # set up basic transforms
        self.tform = {
            'canvas_to_window': transform.CanvasWindowTransform(self),
            'cartesian_to_window': (transform.RotationTransform(self) +
                                    transform.CartesianWindowTransform(self)),
            'data_to_cartesian': (transform.DataCartesianTransform(self) +
                                  transform.ScaleTransform(self)),
            'data_to_scrollbar': (transform.DataCartesianTransform(self) +
                                  transform.RotationTransform(self)),
            'data_to_window': (transform.DataCartesianTransform(self) +
                               transform.ScaleTransform(self) +
                               transform.RotationTransform(self) +
                               transform.CartesianWindowTransform(self)),
            'wcs_to_data': transform.WCSDataTransform(self),
            'wcs_to_window': (transform.WCSDataTransform(self) +
                              transform.DataCartesianTransform(self) +
                              transform.ScaleTransform(self) +
                              transform.RotationTransform(self) +
                              transform.CartesianWindowTransform(self)),
            }

        self.coordmap = {
            'canvas': coordmap.CanvasMapper(self),
            'cartesian': coordmap.CartesianMapper(self),
            'data': coordmap.DataMapper(self),
            None: coordmap.DataMapper(self),
            'offset': coordmap.OffsetMapper(self, None),
            'wcs': coordmap.WCSMapper(self, coordmap.DataMapper(self)),
            }

        # cursors
        self.cursor = {}

        # For callbacks
        for name in ('transform', 'image-set', 'image-unset', 'configure',
                     'redraw', 'limits-set'):
            self.enable_callback(name)


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
        self._imgwin_wd = int(width)
        self._imgwin_ht = int(height)
        self._ctr_x = width // 2
        self._ctr_y = height // 2
        self.logger.info("widget resized to %dx%d" % (width, height))

        self.make_callback('configure', width, height)
        self.redraw(whence=0)

    def configure(self, width, height):
        """See :meth:`set_window_size`."""
        self._imgwin_set = True
        self.set_window_size(width, height)

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
        ## if not self._imgwin_set:
        ##     raise ImageViewError("Dimensions of actual window are not yet determined")
        return (self._imgwin_wd, self._imgwin_ht)

    def get_dims(self, data):
        """Get the first two dimensions of Numpy array data.
        Data may have more dimensions, but they are not reported.

        Returns
        -------
        dims : tuple
            Data dimensions in the form of ``(width, height)``.

        """
        height, width = data.shape[:2]
        return (width, height)

    def get_data_size(self):
        """Get the dimensions of the image currently being displayed.

        Returns
        -------
        size : tuple
            Image dimensions in the form of ``(width, height)``.

        """
        image = self.get_image()
        if image is None:
            raise ImageViewNoDataError("No data found")
        return image.get_size()

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
        canvas.ui_setActive(True)

        self._imgobj = None

        # private canvas set?
        if not (private_canvas is None):
            self.private_canvas = private_canvas

            if private_canvas != canvas:
                private_canvas.set_surface(self)
                private_canvas.ui_setActive(True)
                private_canvas.add_callback('modified', self.canvas_changed_cb)

        # sanity check that we have a private canvas, and if not,
        # set it to the "advertised" canvas
        if self.private_canvas is None:
            self.private_canvas = canvas

        # make sure private canvas has our non-private one added
        if (self.private_canvas != self.canvas) and (
            not self.private_canvas.has_object(canvas)):
            self.private_canvas.add(canvas)

        self.initialize_private_canvas(self.private_canvas)

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
        cm = cmap.get_cmap(cmap_name)
        self.set_cmap(cm)

    def set_intensity_map(self, imap_name):
        """Set the intensity map.

        Available intensity map names can be discovered using
        :func:`ginga.imap.get_names`.

        Parameters
        ----------
        imap_name :  str
            The name of an intensity map.

        """
        im = imap.get_imap(imap_name)
        self.set_imap(im)

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
        distClass = ColorDist.get_dist(calg_name)
        hashsize = self.rgbmap.get_hash_size()
        dist = distClass(hashsize, **kwdargs)
        self.set_calg(dist)

    def get_color_algorithms(self):
        """Get available color distribution algorithm names.
        See :func:`ginga.ColorDist.get_dist_names`.

        """
        return ColorDist.get_dist_names()

    def set_cmap(self, cm):
        """Set color map.
        See :meth:`ginga.RGBMap.RGBMapper.set_cmap`.

        """
        self.rgbmap.set_cmap(cm)

    def invert_cmap(self):
        """Invert the color map.
        See :meth:`ginga.RGBMap.RGBMapper.invert_cmap`.

        """
        self.rgbmap.invert_cmap()

    def set_imap(self, im):
        """Set intensity map.
        See :meth:`ginga.RGBMap.RGBMapper.set_imap`.

        """
        self.rgbmap.set_imap(im)

    def set_calg(self, dist):
        """Set color distribution algorithm.
        See :meth:`ginga.RGBMap.RGBMapper.set_dist`.

        """
        self.rgbmap.set_dist(dist)

    def shift_cmap(self, pct):
        """Shift color map.
        See :meth:`ginga.RGBMap.RGBMapper.shift`.

        """
        self.rgbmap.shift(pct)

    def scale_and_shift_cmap(self, scale_pct, shift_pct):
        """Stretch and/or shrink the color map.
        See :meth:`ginga.RGBMap.RGBMapper.scale_and_shift`.

        """
        self.rgbmap.scale_and_shift(scale_pct, shift_pct)

    def restore_contrast(self):
        """Restores the color map from any stretch and/or shrinkage.
        See :meth:`ginga.RGBMap.RGBMapper.reset_sarr`.

        """
        self.rgbmap.reset_sarr()

    def restore_cmap(self):
        """Restores the color map from any rotation, stretch and/or shrinkage.
        See :meth:`ginga.RGBMap.RGBMapper.restore_cmap`.

        """
        self.rgbmap.restore_cmap()

    def rgbmap_cb(self, rgbmap):
        """Handle callback for when RGB map has changed."""
        self.logger.debug("RGB map has changed.")
        self.redraw(whence=2)

    def cmap_changed_cb(self, setting, value):
        """Handle callback that is invoked when the color settings
        have changed in some way.

        """
        self.logger.debug("Color settings have changed.")

        # Update our RGBMapper with any changes
        cmap_name = self.t_.get('color_map', "gray")
        cm = cmap.get_cmap(cmap_name)
        self.rgbmap.set_cmap(cm, callback=False)

        imap_name = self.t_.get('intensity_map', "ramp")
        im = imap.get_imap(imap_name)
        self.rgbmap.set_imap(im, callback=False)

        hash_size = self.t_.get('color_hashsize', 65535)
        self.rgbmap.set_hash_size(hash_size, callback=False)

        hash_alg = self.t_.get('color_algorithm', "linear")
        self.rgbmap.set_hash_algorithm(hash_alg, callback=True)

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
        rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw(whence=2)

    def get_image(self):
        """Get the image currently being displayed.

        Returns
        -------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            Image object.

        """
        if self._imgobj is not None:
            # quick optomization
            return self._imgobj.get_image()

        canvas_img = self.get_canvas_image()
        return canvas_img.get_image()

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
            NormImage = self.canvas.getDrawClass('normimage')
            interp = self.t_.get('interpolation', 'basic')

            # previous choice might not be available if preferences
            # were saved when opencv was being used (and not used now)
            # --if so, default to "basic"
            if not interp in trcalc.interpolation_methods:
                interp='basic'

            self._imgobj = NormImage(0, 0, None, alpha=1.0,
                                      interpolation=interp)
            self._imgobj.add_callback('image-set', self._image_set_cb)

        return self._imgobj

    def set_image(self, image, add_to_canvas=True):
        """Set an image to be displayed.

        If there is no error, the ``'image-unset'`` and ``'image-set'``
        callbacks will be invoked.

        Parameters
        ----------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            Image object.

        add_to_canvas : bool
            Add image to canvas.

        """
        canvas_img = self.get_canvas_image()

        old_image = canvas_img.get_image()
        self.make_callback('image-unset', old_image)

        with self.suppress_redraw:

            # this line should force the callback of _image_set_cb()
            canvas_img.set_image(image)

            if add_to_canvas:
                try:
                    self.canvas.get_object_by_tag(self._canvas_img_tag)

                except KeyError:
                    tag = self.canvas.add(canvas_img,
                                          tag=self._canvas_img_tag)
                    #self.logger.debug("adding image to canvas %s" % self.canvas)

                # move image to bottom of layers
                self.canvas.lowerObject(canvas_img)

            #self.canvas.update_canvas(whence=0)

    def _image_set_cb(self, canvas_img, image):
        try:
            self.apply_profile_or_settings(image)

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

        # update our display if the image changes underneath us
        image.add_callback('modified', self._image_modified_cb)

        # out with the old, in with the new...
        self.make_callback('image-set', image)

    def apply_profile_or_settings(self, image):
        """Apply an embedded profile in an image to the viewer.

        Parameters
        ----------
        image : `~ginga.AstroImage.AstroImage` or `~ginga.RGBImage.RGBImage`
            Image object.

        This function is used to initialize the viewer when a new image
        is loaded.  Either the profile settings embedded in the image or
        the default settings are applied as specified in the preferences.
        """
        profile = image.get('profile', None)

        with self.suppress_redraw:
            # initialize transform
            if ((profile is not None) and
                    (self.t_['profile_use_transform']) and
                    profile.has_key('flip_x')):
                flip_x, flip_y = profile['flip_x'], profile['flip_y']
                swap_xy = profile['swap_xy']
                self.transform(flip_x, flip_y, swap_xy)
            else:
                self.logger.debug(
                    "auto orient (%s)" % (self.t_['auto_orient']))
                if self.t_['auto_orient']:
                    self.auto_orient()

            # initialize scale
            if ((profile is not None) and (self.t_['profile_use_scale']) and
                    profile.has_key('scale_x')):
                scale_x, scale_y = profile['scale_x'], profile['scale_y']
                self.logger.debug("restoring scale to (%f,%f)" % (
                    scale_x, scale_y))
                self.scale_to(scale_x, scale_y, no_reset=True)
            else:
                self.logger.debug("auto zoom (%s)" % (self.t_['autozoom']))
                if self.t_['autozoom'] != 'off':
                    self.zoom_fit(no_reset=True)

            # initialize pan position
            if ((profile is not None) and (self.t_['profile_use_pan']) and
                   profile.has_key('pan_x')):
                pan_x, pan_y = profile['pan_x'], profile['pan_y']
                self.logger.debug("restoring pan position to (%f,%f)" % (
                    pan_x, pan_y))
                self.set_pan(pan_x, pan_y, no_reset=True)
            else:
                # NOTE: False a possible value from historical use
                self.logger.debug(
                    "auto center (%s)" % (self.t_['autocenter']))
                if not self.t_['autocenter'] in ('off', False):
                    self.center_image(no_reset=True)

            # initialize rotation
            if ((profile is not None) and
                    (self.t_['profile_use_rotation']) and
                    profile.has_key('rot_deg')):
                rot_deg = profile['rot_deg']
                self.rotate(rot_deg)

            # initialize cuts
            if ((profile is not None) and (self.t_['profile_use_cuts']) and
                   profile.has_key('cutlo')):
                loval, hival = profile['cutlo'], profile['cuthi']
                self.cut_levels(loval, hival, no_reset=True)
            else:
                self.logger.debug("auto cuts (%s)" % (self.t_['autocuts']))
                if self.t_['autocuts'] != 'off':
                    self.auto_levels()

            self.canvas.update_canvas(whence=0)


    def _image_modified_cb(self, image):

        canvas_img = self.get_canvas_image()
        image2 = canvas_img.get_image()
        if image is not image2:
            # not the image we are now displaying, perhaps a former image
            return

        with self.suppress_redraw:

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
        dims = data.shape
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      logger=self.logger)
        self.set_image(image)

    def clear(self):
        """Clear the displayed image."""
        self._imgobj = None
        try:
            # See if there is an image on the canvas
            self.canvas.delete_object_by_tag(self._canvas_img_tag)
        except KeyError:
            pass

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
        if (profile is None):
            # If image has no profile then create one
            profile = Settings.SettingGroup()
            image.set(profile=profile)

        self.logger.debug("saving to image profile: params=%s" % (
                str(params)))
        profile.set(**params)

    ## def apply_profile(self, image, profile, redraw=False):

    ##     self.logger.info("applying existing profile found in image")

    ##     if profile.has_key('scale_x'):
    ##         scale_x, scale_y = profile['scale_x'], profile['scale_y']
    ##         self.scale_to(scale_x, scale_y, no_reset=True, redraw=False)

    ##     if profile.has_key('pan_x'):
    ##         pan_x, pan_y = profile['pan_x'], profile['pan_y']
    ##         self.set_pan(pan_x, pan_y, no_reset=True, redraw=False)

    ##     if profile.has_key('cutlo'):
    ##         loval, hival = profile['cutlo'], profile['cuthi']
    ##         self.cut_levels(loval, hival, no_reset=True, redraw=False)

    ##     if redraw:
    ##         self.redraw(whence=0)

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
        whence
            See :meth:`get_rgb_object`.

        """
        if not self.defer_redraw:
            if self._hold_redraw_cnt == 0:
                self.redraw_now(whence=whence)
            return

        with self._defer_lock:
            whence = min(self._defer_whence, whence)
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

    def redraw_now(self, whence=0):
        """Redraw the displayed image.

        Parameters
        ----------
        whence
            See :meth:`get_rgb_object`.

        """
        try:
            time_start = time.time()
            self.redraw_data(whence=whence)

            # finally update the window drawable from the offscreen surface
            self.update_image()
            time_done = time.time()
            time_delta = time_start - self.time_last_redraw
            time_elapsed = time_done - time_start
            self.time_last_redraw = time_done
            self.logger.debug("widget '%s' redraw (whence=%d) delta=%.4f "
                              "elapsed=%.4f sec" % (
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
            See :meth:`get_rgb_object`.

        """
        if not self._imgwin_set:
            # window has not been realized yet
            return

        if not self._self_scaling:
            rgbobj = self.get_rgb_object(whence=whence)
            self.render_image(rgbobj, self._dst_x, self._dst_y)

        self.private_canvas.draw(self)

        # TODO: see if we can deprecate this fake callback
        if whence <= 0:
            self.make_callback('redraw')

    def getwin_array(self, order='RGB', alpha=1.0):
        """Get Numpy data array for display window.

        Parameters
        ----------
        order : str
            The desired order of RGB color layers.

        alpha : float
            Opacity.

        Returns
        -------
        outarr : ndarray
            Numpy data array for display window.

        """
        order = order.upper()
        depth = len(order)

        # Prepare data array for rendering
        data = self._rgbobj.get_array(order)

        # NOTE [A]
        height, width, depth = data.shape

        imgwin_wd, imgwin_ht = self.get_window_size()

        # create RGBA array for output
        outarr = numpy.zeros((imgwin_ht, imgwin_wd, depth), dtype='uint8')

        # fill image array with the background color
        r, g, b = self.img_bg
        bgval = dict(A=int(255*alpha), R=int(255*r), G=int(255*g), B=int(255*b))

        for i in range(len(order)):
            outarr[:, :, i] = bgval[order[i]]

        # overlay our data
        trcalc.overlay_image(outarr, self._dst_x, self._dst_y,
                             data, flipy=False, fill=False, copy=False)

        return outarr

    def getwin_buffer(self, order='RGB'):
        """Same as :meth:`getwin_array`, but with the output array converted
        to C-order Python bytes.

        """
        outarr = self.getwin_array(order=order)

        return outarr.tobytes(order='C')

    def get_datarect(self):
        """Get the approximate bounding box of the displayed image.

        Returns
        -------
        rect : tuple
            Bounding box in data coordinates in the form of
            ``(x1, y1, x2, y2)``.

        """
        x1, y1, x2, y2 = self._org_x1, self._org_y1, self._org_x2, self._org_y2
        return (x1, y1, x2, y2)

    def get_limits(self, coord='data'):
        """Get the bounding box of the viewer extents.

        Returns
        -------
        rect : tuple
            Bounding box in data coordinates in the form of
            ``(x1, y1, x2, y2)``.

        """
        if self._limits is not None:
            # User set limits
            limits = self._limits

        else:
            # No user defined limits.  If there is an image loaded
            # use its dimensions as the limits
            image = self.get_image()
            if image is not None:
                wd, ht = image.get_size()
                limits = ((0.0, 0.0), (float(wd), float(ht)))

            else:
                # No limits found, go to default
                limits = ((0.0, 0.0), (0.0, 0.0))

        # convert to data coordinates
        crdmap = self.get_coordmap(coord)
        limits = list(map(lambda pt: crdmap.data_to(pt[0], pt[1]),
                          limits))

        return limits

    def set_limits(self, limits, coord='data'):
        """Set the bounding box of the viewer extents.

        Parameters
        ----------
        limits : tuple or None
            A tuple setting the extents of the viewer in the form of
            ``((x1, y1), (x2, y2))``.
        """
        if limits is not None:
            assert len(limits) == 2, ValueError("limits takes a 2 tuple")

            # convert to data coordinates
            crdmap = self.get_coordmap(coord)
            limits = list(map(lambda pt: crdmap.to_data(pt[0], pt[1]),
                              limits))

        self._limits = limits
        self.make_callback('limits-set', limits)

    def get_rgb_object(self, whence=0):
        """Create and return RGB slices representing the data
        that should be rendered at the current zoom level and pan settings.

        Parameters
        ----------
        whence : {0, 1, 2, 3}
            Optimization flag that reduces the time to create
            the RGB object by only recalculating what is necessary:

                0. New image, pan/scale has changed, or rotation/transform
                   has changed; Recalculate everything
                1. Cut levels or similar has changed
                2. Color mapping has changed
                3. Graphical overlays have changed

        Returns
        -------
        rgbobj : `~ginga.RGBMap.RGBPlanes`
            RGB object.

        """
        time_start = time.time()
        win_wd, win_ht = self.get_window_size()
        order = self.get_rgb_order()

        if (whence <= 0.0) or (self._rgbarr is None):
            # calculate dimensions of window RGB backing image
            pan_x, pan_y = self.get_pan()
            scale_x, scale_y = self.get_scale_xy()
            wd, ht = self._calc_bg_dimensions(scale_x, scale_y,
                                              pan_x, pan_y,
                                              win_wd, win_ht)

            # create backing image
            depth = len(order)
            rgba = numpy.zeros((ht, wd, depth), dtype=numpy.uint8)
            self._rgbarr = rgba

        if (whence <= 2.0) or (self._rgbarr2 is None):
            # Apply any RGB image overlays
            self._rgbarr2 = numpy.copy(self._rgbarr)
            self.overlay_images(self.canvas, self._rgbarr2, whence=whence)

        if (whence <= 2.5) or (self._rgbobj is None):
            rotimg = self._rgbarr2

            # Apply any viewing transformations or rotations
            # if not applied earlier
            rotimg = self.apply_transforms(rotimg,
                                           self.t_['rot_deg'])
            rotimg = numpy.ascontiguousarray(rotimg)

            self._rgbobj = RGBMap.RGBPlanes(rotimg, order)

            # convert to output ICC profile, if one is specified
            output_profile = self.t_.get('icc_output_profile', None)
            if not (output_profile is None):
                self.convert_via_profile(self._rgbobj, 'working',
                                         output_profile)

        time_end = time.time()
        self.logger.debug("times: total=%.4f" % (
            (time_end - time_start)))
        return self._rgbobj

    def _calc_bg_dimensions(self, scale_x, scale_y,
                            pan_x, pan_y, win_wd, win_ht):

        coord = self.t_.get('pan_coord', 'data')
        if coord == 'wcs':
            # <-- pan_x, pan_y are in WCS
            image = self.get_image()
            if image is None:
                # TODO:
                pan_x, pan_y = 0.0, 0.0
            else:
                pan_x, pan_y = image.radectopix(pan_x, pan_y)

        # Sanity check on the scale
        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            #self.logger.warning("new scale would exceed max/min; scale unchanged")
            raise ImageViewError("new scale would exceed pixel max; scale unchanged")

        # It is necessary to store these so that the get_data_xy()
        # (below) calculations can proceed
        self._org_x, self._org_y = pan_x - self.data_off, pan_y - self.data_off
        self._org_scale_x, self._org_scale_y = scale_x, scale_y

        # calc minimum size of pixel image we will generate
        # necessary to fit the window in the desired size

        # get the data points in the four corners
        xul, yul = self.get_data_xy(0, 0)
        xur, yur = self.get_data_xy(win_wd, 0)
        xlr, ylr = self.get_data_xy(win_wd, win_ht)
        xll, yll = self.get_data_xy(0, win_ht)

        # determine bounding box
        a1 = min(xul, xur, xlr, xll)
        b1 = min(yul, yur, ylr, yll)
        a2 = max(xul, xur, xlr, xll)
        b2 = max(yul, yur, ylr, yll)

        # constrain to integer indexes
        x1, y1, x2, y2 = int(a1), int(b1), int(round(a2)), int(round(b2))
        x1 = max(0, x1)
        y1 = max(0, y1)

        self.logger.debug("approx area covered is %dx%d to %dx%d" % (
            x1, y1, x2, y2))

        self._org_x1 = x1
        self._org_y1 = y1
        self._org_x2 = x2
        self._org_y2 = y2

        # Make a square from the scaled cutout, with room to rotate
        slop = 20
        side = int(math.sqrt(win_wd**2 + win_ht**2) + slop)
        wd = ht = side

        # Find center of new array
        ncx, ncy = wd // 2, ht // 2
        self._org_xoff, self._org_yoff = ncx, ncy

        return (wd, ht)


    def _reset_bbox(self):
        """This function should only be called internally.  It resets
        the viewers bounding box based on changes to pan or scale.
        """
        scale_x, scale_y = self.get_scale_xy()
        pan_x, pan_y = self.get_pan()
        win_wd, win_ht = self.get_window_size()

        self._calc_bg_dimensions(scale_x, scale_y,
                                 pan_x, pan_y, win_wd, win_ht)


    def apply_transforms(self, data, rot_deg):
        """Apply transformations to the given data.
        These include flip/swap X/Y, invert Y, and rotation.

        Parameters
        ----------
        data : ndarray
            Data to be transformed.

        rot_deg : float
            Rotate the data by the given degrees.

        Returns
        -------
        data : ndarray
            Transformed data.

        """
        start_time = time.time()

        wd, ht = self.get_dims(data)
        xoff, yoff = self._org_xoff, self._org_yoff

        # Do transforms as necessary
        flip_x, flip_y = self.t_['flip_x'], self.t_['flip_y']
        swap_xy = self.t_['swap_xy']

        data = trcalc.transform(data, flip_x=flip_x, flip_y=flip_y,
                                swap_xy=swap_xy)
        if flip_y:
            yoff = ht - yoff
        if flip_x:
            xoff = wd - xoff
        if swap_xy:
            xoff, yoff = yoff, xoff

        split_time = time.time()
        self.logger.debug("reshape time %.3f sec" % (
            split_time - start_time))

        # Rotate the image as necessary
        if rot_deg != 0:
            # This is the slowest part of the rendering--install the OpenCv or pyopencl
            # packages to speed it up
            data = numpy.ascontiguousarray(data)
            data = trcalc.rotate_clip(data, -rot_deg, out=data,
                                      logger=self.logger)

        split2_time = time.time()

        # apply other transforms
        if self._invertY:
            # Flip Y for natural natural Y-axis inversion between FITS coords
            # and screen coords
            data = numpy.flipud(data)

        self.logger.debug("rotate time %.3f sec, total reshape %.3f sec" % (
            split2_time - split_time, split2_time - start_time))

        # dimensions may have changed in transformations
        wd, ht = self.get_dims(data)

        ctr_x, ctr_y = self._ctr_x, self._ctr_y
        dst_x, dst_y = ctr_x - xoff, ctr_y - (ht - yoff)
        self._dst_x, self._dst_y = dst_x, dst_y
        self.logger.debug("ctr=%d,%d off=%d,%d dst=%d,%d cutout=%dx%d" % (
            ctr_x, ctr_y, xoff, yoff, dst_x, dst_y, wd, ht))

        win_wd, win_ht = self.get_window_size()
        self.logger.debug("win=%d,%d coverage=%d,%d" % (
            win_wd, win_ht, dst_x + wd, dst_y + ht))

        return data

    def overlay_images(self, canvas, data, whence=0.0):
        """Overlay data on all the canvas objects.

        Parameters
        ----------
        canvas : `~ginga.canvas.types.layer.DrawingCanvas`
            Canvas to overlay.

        data : ndarray
            Data to overlay.

        whence
             See :meth:`get_rgb_object`.

        """
        #if not canvas.is_compound():
        if not hasattr(canvas, 'objects'):
            return

        for obj in canvas.get_objects():
            if hasattr(obj, 'draw_image'):
                obj.draw_image(self, data, whence=whence)
            elif obj.is_compound() and (obj != canvas):
                self.overlay_images(obj, data, whence=whence)

    def convert_via_profile(self, rgbobj, inprof_name, outprof_name):
        """Convert the given RGB object from one ICC profile to another.

        Parameters
        ----------
        rgbobj : `~ginga.RGBMap.RGBPlanes`
            RGB object that is modified in-place.

        inprof_name, outprof_name : str
            ICC profile names (see :func:`ginga.util.io_rgb.get_profiles`).

        """
        # get rest of necessary conversion parameters
        to_intent = self.t_.get('icc_output_intent', 'perceptual')
        proofprof_name = self.t_.get('icc_proof_profile', None)
        proof_intent = self.t_.get('icc_proof_intent', 'perceptual')
        use_black_pt = self.t_.get('icc_black_point_compensation', False)

        self.logger.info("Attempting conversion from '%s' to '%s' profile" % (
            inprof_name, outprof_name))

        inp = rgbobj.get_array('RGB')
        arr = io_rgb.convert_profile_fromto(inp, inprof_name, outprof_name,
                                            to_intent=to_intent,
                                            proof_name=proofprof_name,
                                            proof_intent=proof_intent,
                                            use_black_pt=use_black_pt)
        out = rgbobj.rgbarr

        ri, gi, bi = rgbobj.get_order_indexes('RGB')
        out[..., ri] = arr[..., 0]
        out[..., gi] = arr[..., 1]
        out[..., bi] = arr[..., 2]

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
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        return self.tform['data_to_window'].from_(win_x, win_y)

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
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        return self.tform['data_to_cartesian'].from_(off_x, off_y)

    def get_canvas_xy(self, data_x, data_y, center=None):
        """Reverse of :meth:`get_data_xy`.

        """
        if center is not None:
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        return self.tform['data_to_window'].to_(data_x, data_y)

    def data_to_offset(self, data_x, data_y, center=None):
        """Reverse of :meth:`offset_to_data`.

        """
        if center is not None:
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        return self.tform['data_to_cartesian'].to_(data_x, data_y)

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
        return self.tform['cartesian_to_window'].to_(off_x, off_y)

    def window_to_offset(self, win_x, win_y):
        """Reverse of :meth:`offset_to_window`."""
        return self.tform['cartesian_to_window'].from_(win_x, win_y)

    def canvascoords(self, data_x, data_y, center=None):
        """Same as :meth:`get_canvas_xy`.

        """
        if center is not None:
            self.logger.warn("`center` keyword is ignored and will be deprecated")

        # data->canvas space coordinate conversion
        return self.tform['data_to_window'].to_(data_x, data_y)

    def get_data_pct(self, xpct, ypct):
        """Calculate new data size for the given axis ratios.
        See :meth:`get_data_size`.

        Parameters
        ----------
        xpct, ypct : float
            Ratio for X and Y, respectively, where 1 is 100%.

        Returns
        -------
        x, y : int
            Scaled dimensions.

        """
        width, height = self.get_data_size()
        x = int(float(xpct) * (width-1))
        y = int(float(ypct) * (height-1))
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
        points = []
        wd, ht = self.get_window_size()
        for x, y in ((0, 0), (wd-1, 0), (wd-1, ht-1), (0, ht-1)):
            c, d = self.get_data_xy(x, y)
            points.append((c, d))
        return points

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
            Data slice.

        Raises
        ------
        ginga.ImageView.ImageViewNoDataError
            Image not found.

        """
        image = self.get_image()
        if image is not None:
            return image.get_data_xy(data_x, data_y)

        raise ImageViewNoDataError("No image found")

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
        dist = math.sqrt(dx*dx + dy*dy)
        dist = round(dist)
        return dist

    def _sanity_check_scale(self, scale_x, scale_y):
        """Do a sanity check on the proposed scale vs. window size.
        Raises an exception if there will be a problem.
        """
        win_wd, win_ht = self.get_window_size()
        if (win_wd <= 0) or (win_ht <= 0):
            raise ImageViewError("window size undefined")

        # final sanity check on resulting output image size
        if (win_wd * scale_x < 1) or (win_ht * scale_y < 1):
            raise ValueError("resulting scale (%f, %f) "
                             "would result in image size of <1 in width or height" % (
                scale_x, scale_y))

        sx = float(win_wd) / scale_x
        sy = float(win_ht) / scale_y
        if (sx < 1.0) or (sy < 1.0):
            raise ValueError("resulting scale (%f, %f) "
                             "would result in pixel size approaching window size" % (
                scale_x, scale_y))

    def scale_to(self, scale_x, scale_y, no_reset=False):
        """Scale the image in a channel.
        This only changes the relevant settings; The image is not modified.
        Also see :meth:`zoom_to`.

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
        if (maxscale > self.t_['scale_max']):
            self.logger.error("Scale (%.2f) exceeds max scale limit (%.2f)" % (
                maxscale, self.t_['scale_max']))
            # TODO: exception?
            return

        minscale = min(scale_x, scale_y)
        if (minscale < self.t_['scale_min']):
            self.logger.error("Scale (%.2f) exceeds min scale limit (%.2f)" % (
                minscale, self.t_['scale_min']))
            # TODO: exception?
            return

        # Sanity check on the scale vs. window size
        try:
            self._sanity_check_scale(scale_x, scale_y)

        except Exception as e:
            self.logger.warning("Error in scaling: %s" % (str(e)))
            return

        self.t_.set(scale=(scale_x, scale_y))
        self._reset_bbox()

        # If user specified "override" or "once" for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_['autozoom'] in ('override', 'once')):
            self.t_.set(autozoom='off')

        if self.t_['profile_use_scale']:
            # Save scale with this image embedded profile
            self.save_profile(scale_x=scale_x, scale_y=scale_y)

    def scale_cb(self, setting, value):
        """Handle callback related to image scaling."""
        scale_x, scale_y = value

        if self.t_['zoom_algorithm'] == 'rate':
            zoom_x = math.log(scale_x / self.t_['scale_x_base'],
                              self.t_['zoom_rate'])
            zoom_y = math.log(scale_y / self.t_['scale_y_base'],
                              self.t_['zoom_rate'])
            # TODO: avg, max?
            zoomlevel = min(zoom_x, zoom_y)
        else:
            maxscale = max(scale_x, scale_y)
            zoomlevel = maxscale
            if zoomlevel < 1.0:
                zoomlevel = - (1.0 / zoomlevel)

        self.t_.set(zoomlevel=zoomlevel)

        self.redraw(whence=0)

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
        #return (self._org_scale_x, self._org_scale_y)
        return self.t_['scale']

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
        scalefactor = self.get_scale()
        if scalefactor >= 1.0:
            #text = '%dx' % (int(scalefactor))
            text = '%.2fx' % (scalefactor)
        else:
            #text = '1/%dx' % (int(1.0/scalefactor))
            text = '1/%.2fx' % (1.0/scalefactor)
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
        if self.t_['zoom_algorithm'] == 'rate':
            scale_x = self.t_['scale_x_base'] * (
                self.t_['zoom_rate'] ** zoomlevel)
            scale_y = self.t_['scale_y_base'] * (
                self.t_['zoom_rate'] ** zoomlevel)
        else:
            if zoomlevel >= 1.0:
                scalefactor = zoomlevel
            elif zoomlevel < -1.0:
                scalefactor = 1.0 / float(abs(zoomlevel))
            else:
                scalefactor = 1.0
            scale_x = scale_y = scalefactor

        ## print("scale_x=%f scale_y=%f zoom=%f" % (
        ##     scale_x, scale_y, zoomlevel))
        self._scale_to(scale_x, scale_y, no_reset=no_reset)

    def zoom_in(self):
        """Zoom in a level.
        Also see :meth:`zoom_to`.

        """
        if self.t_['zoom_algorithm'] == 'rate':
            self.zoom_to(self.t_['zoomlevel'] + 1)
        else:
            zl = int(self.t_['zoomlevel'])
            if (zl >= 1) or (zl <= -3):
                self.zoom_to(zl + 1)
            else:
                self.zoom_to(1)

    def zoom_out(self):
        """Zoom out a level.
        Also see :meth:`zoom_to`.

        """
        if self.t_['zoom_algorithm'] == 'rate':
            self.zoom_to(self.t_['zoomlevel'] - 1)
        else:
            zl = int(self.t_['zoomlevel'])
            if zl == 1:
                self.zoom_to(-2)
            elif (zl >= 2) or (zl <= -2):
                self.zoom_to(zl - 1)
            else:
                self.zoom_to(1)

    def zoom_fit(self, no_reset=False):
        """Zoom to fit display window.
        Also see :meth:`zoom_to`.

        Parameters
        ----------
        no_reset : bool
            Do not reset ``autozoom`` setting.

        """
        # calculate actual width of the image, considering rotation
        try:
            width, height = self.get_data_size()

        except ImageViewNoDataError:
            return

        try:
            wwidth, wheight = self.get_window_size()
            self.logger.debug("Window size is %dx%d" % (wwidth, wheight))
            if self.t_['swap_xy']:
                wwidth, wheight = wheight, wwidth
        except:
            return

        # zoom_fit also centers image
        with self.suppress_redraw:

            self.center_image(no_reset=no_reset)

            ctr_x, ctr_y, rot_deg = self.get_rotation_info()
            min_x, min_y, max_x, max_y = 0, 0, 0, 0
            for x, y in ((0, 0), (width-1, 0), (width-1, height-1), (0, height-1)):
                x0, y0 = trcalc.rotate_pt(x, y, rot_deg, xoff=ctr_x, yoff=ctr_y)
                min_x, min_y = min(min_x, x0), min(min_y, y0)
                max_x, max_y = max(max_x, x0), max(max_y, y0)

            width, height = max_x - min_x, max_y - min_y
            if min(width, height) <= 0:
                return

            # Calculate optimum zoom level to still fit the window size
            if self.t_['zoom_algorithm'] == 'rate':
                scale_x = (float(wwidth) /
                           (float(width) * self.t_['scale_x_base']))
                scale_y = (float(wheight) /
                           (float(height) * self.t_['scale_y_base']))

                scalefactor = min(scale_x, scale_y)
                # account for t_[scale_x/y_base]
                scale_x = scalefactor * self.t_['scale_x_base']
                scale_y = scalefactor * self.t_['scale_y_base']
            else:
                scale_x = float(wwidth) / float(width)
                scale_y = float(wheight) / float(height)

                scalefactor = min(scale_x, scale_y)
                scale_x = scale_y = scalefactor

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
        return self.t_['zoomlevel']

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
        name : {'rate', 'step'}
            Zoom algorithm.

        """
        return self.t_['zoom_algorithm']

    def set_zoom_algorithm(self, name):
        """Set zoom algorithm.

        Parameters
        ----------
        name : {'rate', 'step'}
            Zoom algorithm.

        """
        name = name.lower()
        assert name in ('step', 'rate'), \
              ImageViewError("Alg '%s' must be one of: step, rate" % name)
        self.t_.set(zoom_algorithm=name)

    def zoomalg_change_cb(self, setting, value):
        """Handle callback related to changes in zoom."""
        self.zoom_to(self.t_['zoomlevel'])

    def interpolation_change_cb(self, setting, value):
        """Handle callback related to changes in interpolation."""
        canvas_img = self.get_canvas_image()
        canvas_img.interpolation = value
        canvas_img.reset_optimize()
        self.redraw(whence=0)

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
        assert(option in self.autozoom_options), \
            ImageViewError("Bad autozoom option '%s': must be one of %s" % (
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
        """Set pan behavior.

        Parameters
        ----------
        pan_x, pan_y : float
            Pan positions.

        coord : {'data', 'wcs'}
            Indicates whether the given pan positions are in data or WCS space.

        no_reset : bool
            Do not reset ``autocenter`` setting.

        """
        with self.suppress_redraw:
            self.t_.set(pan=(pan_x, pan_y), pan_coord=coord)
            self._reset_bbox()

        # If user specified "override" or "once" for auto center, then turn off
        # auto center now that they have set the pan manually
        if (not no_reset) and (self.t_['autocenter'] in ('override', 'once')):
            self.t_.set(autocenter='off')

        if self.t_['profile_use_pan']:
            # Save pan position with this image embedded profile
            self.save_profile(pan_x=pan_x, pan_y=pan_y)

    def pan_cb(self, setting, value):
        """Handle callback related to changes in pan."""
        pan_x, pan_y = value

        self.logger.debug("pan set to %.2f,%.2f" % (pan_x, pan_y))
        self.redraw(whence=0)

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
        pan_x, pan_y = self.t_['pan']
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
        try:
            width, height = self.get_data_size()

        except ImageViewNoDataError:
            return

        data_x, data_y = width * pct_x, height * pct_y
        self.panset_xy(data_x, data_y)

    def center_image(self, no_reset=True):
        """Pan to the center of the image.

        Parameters
        ----------
        no_reset : bool
            See :meth:`set_pan`.

        """
        try:
            width, height = self.get_data_size()

        except ImageViewNoDataError:
            return

        data_x, data_y = float(width) / 2.0, float(height) / 2.0
        self.panset_xy(data_x, data_y, no_reset=no_reset)
        # See Footnote [1]
        ## if redraw:
        ##     self.redraw(whence=0)

        if self.t_['autocenter'] == 'once':
            self.t_.set(autocenter='off')

    def set_autocenter(self, option):
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

        if self.t_['profile_use_cuts']:
            # Save cut levels with this image embedded profile
            self.save_profile(cutlo=loval, cuthi=hival)

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

        image = self.get_image()
        if image is None:
            return

        loval, hival = autocuts.calc_cut_levels(image)

        # this will invoke cut_levels_cb()
        self.t_.set(cuts=(loval, hival))

        # If user specified "once" for auto levels, then turn off
        # auto levels now that we have cut levels established
        if self.t_['autocuts'] == 'once':
            self.t_.set(autocuts='off')

    def auto_levels_cb(self, setting, value):
        """Handle callback related to changes in auto-cut levels."""
        # Did we change the method?
        method = self.t_['autocut_method']
        params = self.t_.get('autocut_params', [])
        params = dict(params)

        if method != str(self.autocuts):
            ac_class = AutoCuts.get_autocuts(method)
            self.autocuts = ac_class(self.logger, **params)
        else:
            # TODO: find a cleaner way to update these
            self.autocuts.__dict__.update(params)

        # Redo the auto levels
        #if self.t_['autocuts'] != 'off':
        # NOTE: users seems to expect that when the auto cuts parameters
        # are changed that the cuts should be immediately recalculated
        self.auto_levels()

    def cut_levels_cb(self, setting, value):
        """Handle callback related to changes in cut levels."""
        self.redraw(whence=1)

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
        params = list(params.items())
        self.t_.set(autocut_method=method, autocut_params=params)

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

        if self.t_['profile_use_transform']:
            # Save transform with this image embedded profile
            self.save_profile(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)

    def transform_cb(self, setting, value):
        """Handle callback related to changes in transformations."""
        self.make_callback('transform')
        # whence=0 because need to calculate new extents for proper
        # cutout for rotation (TODO: always make extents consider
        #  room for rotation)
        whence = 0
        self.redraw(whence=whence)

    def copy_attributes(self, dst_fi, attrlist):
        """Copy interesting attributes of our configuration to another
        image view.

        Parameters
        ----------
        dst_fi : subclass of `ImageViewBase`
            Another instance of image view.

        attrlist : list
            A list of attribute names to copy. They can be ``'transforms'``,
            ``'rotation'``, ``'cutlevels'``, ``'rgbmap'``, ``'zoom'``, or
            ``'pan'``.

        """
        with dst_fi.suppress_redraw:
            if 'transforms' in attrlist:
                dst_fi.transform(self.t_['flip_x'], self.t_['flip_y'],
                                 self.t_['swap_xy'])

            if 'rotation' in attrlist:
                dst_fi.rotate(self.t_['rot_deg'])

            if 'cutlevels' in attrlist:
                loval, hival = self.t_['cuts']
                dst_fi.cut_levels(loval, hival)

            if 'rgbmap' in attrlist:
                #dst_fi.set_rgbmap(self.rgbmap)
                dst_fi.rgbmap = self.rgbmap

            if 'zoom' in attrlist:
                dst_fi.zoom_to(self.t_['zoomlevel'])

            if 'pan' in attrlist:
                pan_x, pan_y = self.get_pan()[:2]
                pan_coord = self.t_['pan_coord']
                dst_fi.set_pan(pan_x, pan_y, coord=pan_coord)

            dst_fi.redraw(whence=0)

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

        if self.t_['profile_use_rotation']:
            # Save rotation with this image embedded profile
            self.save_profile(rot_deg=deg)

    def rotation_change_cb(self, setting, value):
        """Handle callback related to changes in rotation angle."""
        # whence=0 because need to calculate new extents for proper
        # cutout for rotation (TODO: always make extents consider
        #  room for rotation)
        whence = 0
        self.redraw(whence=whence)

    def get_center(self):
        """Get image center.

        Returns
        -------
        ctr : tuple
            X and Y positions, in that order.

        """
        return (self._ctr_x, self._ctr_y)

    def get_rgb_order(self):
        """Get RGB order.

        Returns
        -------
        rgb : str
            Returns the order of RGBA planes required by the subclass
            to render the canvas properly.
            Should be overridden by any subclass.

        """
        return 'RGB'

    def get_rotation_info(self):
        """Get rotation information.

        Returns
        -------
        info : tuple
            X and Y positions, and rotation angle in degrees, in that order.

        """
        return (self._ctr_x, self._ctr_y, self.t_['rot_deg'])

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
        invertY = not isinstance(image, AstroImage.AstroImage)

        # Check for various things to set based on metadata
        header = image.get_header()
        if header:
            # Auto-orientation
            orient = header.get('Orientation', None)
            if not orient:
                orient = header.get('Image Orientation', None)
                self.logger.debug("orientation [%s]" % (
                        orient))
            if orient:
                try:
                    orient = int(str(orient))
                    self.logger.info(
                        "setting orientation from metadata [%d]" % (orient))
                    flip_x, flip_y, swap_xy = self.orientMap[orient]

                    self.transform(flip_x, flip_y, swap_xy)
                    invertY = False

                except Exception as e:
                    # problems figuring out orientation--let it be
                    self.logger.error("orientation error: %s" % str(e))
                    pass

        if invertY:
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

    def set_bg(self, r, g, b):
        """Set the background color.

        Parameters
        ----------
        r, g, b : float
            RGB values, which should be between 0 and 1, inclusive.

        """
        self.img_bg = (r, g, b)
        self.redraw(whence=3)

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
        self.img_fg = (r, g, b)
        self.redraw(whence=3)

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
        return self._originUpper

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
        """Determine whether the viewer widget should take focus the
        cursor enters the window.

        Parameters
        ----------
        tf : bool
            If True the widget will grab focus when the cursor moves into
            the window.

        This should be implemented by subclasses.
        """
        self.logger.warning("Subclass should override this abstract method!")

    def update_image(self):
        """Update image.
        This must be implemented by subclasses.

        """
        self.logger.warning("Subclass should override this abstract method!")

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render image.
        This must be implemented by subclasses.

        Parameters
        ----------
        rgbobj : `~ginga.RGBMap.RGBPlanes`
            RGB object.

        dst_x, dst_y : float
            Offsets in screen coordinates.

        """
        self.logger.warning("Subclass should override this abstract method!")

    def reschedule_redraw(self, time_sec):
        """Reschedule redraw event.
        This must be implemented by subclasses.

        Parameters
        ----------
        time_sec : float
            Time, in seconds, to wait.

        """
        self.logger.warning("Subclass should override this abstract method!")

    def set_cursor(self, cursor):
        """Set the cursor in the viewer widget.
        This should be implemented by subclasses.

        Parameters
        ----------
        cursor : object
            a cursor object in the back end's toolkit

        """
        self.logger.warning("Subclass should override this abstract method!")

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

    def get_image_as_array(self):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a numpy array with channels as needed and ordered
        by the back end widget.

        This should be implemented by subclasses.
        """
        raise ImageViewError("Subclass should override this abstract method!")

    def get_image_as_buffer(self, output=None):
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

        arr8 = self.get_image_as_array()
        obuf.write(arr8.tobytes(order='C'))

        ## if output is not None:
        ##     return None
        return obuf

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        """Get the current image shown in the viewer, with any overlaid
        graphics, in a file IO-like object encoded as a bitmap graphics
        file.
        This should be implemented by subclasses.

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
        raise ImageViewError("Subclass should override this abstract method!")

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
        with open(filepath, 'w') as out_f:
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

    def show_pan_mark(self, tf, color='red'):
        """Show a mark in the pan position (center of window).

        Parameters
        ----------
        tf : bool
            If True, show the mark; else remove it if present.

        color : str
            Color of the mark; default is 'red'.
        """
        tag = '_$pan_mark'
        radius = 10

        canvas = self.get_private_canvas()
        try:
            mark = canvas.get_object_by_tag(tag)
            if not tf:
                canvas.delete_object_by_tag(tag)
            else:
                mark.color = color

        except KeyError:
            if tf:
                Point = canvas.get_draw_class('point')
                canvas.add(Point(0, 0, radius, style='plus', color=color,
                                 coord='cartesian'),
                           tag=tag, redraw=False)

        canvas.update_canvas(whence=3)

    def show_mode_indicator(self, tf, corner='ur'):
        """Show a keyboard mode indicator in one of the corners.

        Parameters
        ----------
        tf : bool
            If True, show the mark; else remove it if present.

        corner : str
            One of 'll', 'lr', 'ul' or 'ur' selecting a corner.
            The default is 'ur'.

        """
        tag = '_$mode_indicator'

        canvas = self.get_private_canvas()
        try:
            indic = canvas.get_object_by_tag(tag)
            if not tf:
                canvas.delete_object_by_tag(tag)
            else:
                indic.corner = corner

        except KeyError:
            if tf:
                # force a redraw if the mode changes
                bm = self.get_bindmap()
                bm.add_callback('mode-set',
                                lambda *args: self.redraw(whence=3))

                Indicator = canvas.get_draw_class('modeindicator')
                canvas.add(Indicator(corner=corner),
                           tag=tag, redraw=False)

        canvas.update_canvas(whence=3)

    def show_color_bar(self, tf, side='bottom'):
        """Show a color bar in the window.

        Parameters
        ----------
        tf : bool
            If True, show the color bar; else remove it if present.

        side : str
            One of 'top' or 'bottom'. The default is 'bottom'.

        """

        tag = '_$color_bar'
        canvas = self.get_private_canvas()
        try:
            cbar = canvas.get_object_by_tag(tag)
            if not tf:
                canvas.delete_object_by_tag(tag)
            else:
                cbar.side = side

        except KeyError:
            if tf:
                Cbar = canvas.get_draw_class('colorbar')
                canvas.add(Cbar(side=side), tag=tag, redraw=False)

        canvas.update_canvas(whence=3)

    def set_onscreen_message(self, text, redraw=True):
        """Called by a subclass to update the onscreen message.

        Parameters
        ----------
        text : str
            The text to show in the display.

        """
        font = self.t_.get('onscreen_font', 'sans serif')
        font_size = self.t_.get('onscreen_font_size', 24)

        # TODO: need some way to accurately estimate text extents
        # without actually putting text on the canvas
        ht, wd = font_size, font_size
        if text is not None:
            wd = len(text) * font_size * 0.5

        width, height = self.get_window_size()
        x = (width // 2) - (wd // 2)
        y = ((height // 3) * 2) - (ht // 2)

        tag = '_$onscreen_msg'

        canvas = self.get_private_canvas()
        try:
            message = canvas.get_object_by_tag(tag)
            if text is None:
                canvas.delete_object_by_tag(tag)
            else:
                message.x = x
                message.y = y
                message.text = text

        except KeyError:
            if text is not None:
                Text = canvas.get_draw_class('text')
                canvas.add(Text(x, y, text=text,
                                font=font, fontsize=font_size,
                                color=self.img_fg, coord='canvas'),
                           tag=tag, redraw=False)

        if redraw:
            canvas.update_canvas(whence=3)


    def show_focus_indicator(self, tf, color='white'):
        """Show a focus indicator in the window.

        Parameters
        ----------
        tf : bool
            If True, show the color bar; else remove it if present.

        color : str
            Color for the focus indicator.

        """

        tag = '_$focus_indicator'
        canvas = self.get_private_canvas()
        try:
            fcsi = canvas.get_object_by_tag(tag)
            if not tf:
                canvas.delete_object_by_tag(tag)
            else:
                fcsi.color = color

        except KeyError:
            if tf:
                Fcsi = canvas.get_draw_class('focusindicator')
                fcsi = Fcsi(color=color)
                canvas.add(fcsi, tag=tag, redraw=False)
                self.add_callback('focus', fcsi.focus_cb)

        canvas.update_canvas(whence=3)


class SuppressRedraw(object):
    def __init__(self, viewer):
        self.viewer = viewer

    def __enter__(self):
        self.viewer._hold_redraw_cnt += 1
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.viewer._hold_redraw_cnt -= 1

        if (self.viewer._hold_redraw_cnt <= 0):
            # TODO: whence should be largest possible
            #whence = 0
            whence = self.viewer._defer_whence
            self.viewer.redraw(whence=whence)
        return False


#END
