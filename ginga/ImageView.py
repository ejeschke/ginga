#
# ImageView.py -- base class for the display of image files
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import math
import logging
import threading
import sys, traceback
import time

from ginga.misc import Callback, Settings
from ginga import RGBMap, AstroImage, AutoCuts, ColorDist
from ginga import cmap, imap, trcalc, version
from ginga.canvas import coordmap
from ginga.canvas.types.layer import DrawingCanvas
from ginga.util import io_rgb


class ImageViewError(Exception):
    pass
class ImageViewCoordsError(ImageViewError):
    pass
class ImageViewNoDataError(ImageViewError):
    pass

class ImageViewBase(Callback.Callbacks):
    """An abstract base class for displaying images represented by
    numpy data arrays.

    This class attempts to do as much of the image handling using numpy
    array manipulations (even color and intensity mapping) so that only
    a minimal mapping to a pixel buffer is necessary in concrete subclasses
    that connect to an actual rendering surface.
    """

    def __init__(self, logger=None, rgbmap=None, settings=None):
        """
        Constructor for an image display object.

        Parameters
        ----------
        logger: logging-module compatible logger object, or None
            a logger for tracing and debugging; if None, one will be created

        rgbmap: a ginga.RGBMap.RGBMapper object, or None
            an RGB mapper object; if None, one will be created

        settings: a ginga.Settings.SettingGroup object, or None
            viewer preferences; if None, one will be created
        """
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
                            autocut_params={})
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
        self.t_.getSetting('interpolation').add_callback('set', self.interpolation_change_cb)

        # max/min scaling
        self.t_.addDefaults(scale_max=10000.0, scale_min=0.00001)

        # autozoom options
        self.autozoom_options = ('on', 'override', 'once', 'off')
        self.t_.addDefaults(autozoom='on')

        # image overlays
        # TO BE DEPRECATED
        self.t_.addDefaults(image_overlays=True)
        self.t_.getSetting('image_overlays').add_callback('set', self.overlays_change_cb)

        # for panning
        self.autocenter_options = ('on', 'override', 'once', 'off')
        self.t_.addDefaults(autocenter='on')

        # for transforms
        self.t_.addDefaults(flip_x=False, flip_y=False, swap_xy=False)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.getSetting(name).add_callback('set', self.transform_cb)

        # desired rotation angle
        self.t_.addDefaults(rot_deg=0.0)
        self.t_.getSetting('rot_deg').add_callback('set', self.rotation_change_cb)

        # misc
        self.t_.addDefaults(auto_orient=False,
                            defer_redraw=True, defer_lagtime=0.025)

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
            # Note: transform_cb will redraw enough to pick up ICC profile change
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
        self._desired_size = (300, 300)
        # center (and reference) pixel in the screen image (in pixel coords)
        self._ctr_x = 1
        self._ctr_y = 1
        # data indexes at the reference pixel (in data coords)
        self._org_x = 0
        self._org_y = 0
        # offset from pan position (at center) in this array
        self._org_xoff = 0
        self._org_yoff = 0

        # pan position
        self._pan_x = 0.0
        self._pan_y = 0.0
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
        # offsets in the screen image (in data coords)
        self._off_x = 0
        self._off_y = 0

        # desired scale factors
        self._scale_x = 1.0
        self._scale_y = 1.0
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
        self._defer_lock = threading.RLock()
        self._defer_flag = False
        self._hold_redraw_cnt = 0
        self.suppress_redraw = SuppressRedraw(self)

        self.img_bg = (0.2, 0.2, 0.2)
        self.img_fg = (1.0, 1.0, 1.0)

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

        self.coordmap = {
            'canvas': coordmap.CanvasMapper(self),
            'data': coordmap.DataMapper(self),
            #'offset': coordmap.OffsetMapper(self),
            'wcs': coordmap.WCSMapper(self),
            }

        # For callbacks
        for name in ('transform', 'image-set', 'configure', 'redraw', ):
            self.enable_callback(name)


    def set_window_size(self, width, height):
        """Report the size of the window to display the image.

        Parameters
        ----------
        width: int
            the width of the window in pixels
        height: int
            the height of the window in pixels
        redraw: boolean, optional, default==True
            if True, will redraw the the image in the new dimensions

        Notes
        -----
        This is called by the subclass with width and height as soon as
        the actual dimensions of the allocated window are known.

        Callbacks
        ---------
        Will call any callbacks registered for the 'configure' event.
        Callbacks should have a method signature of
            (viewer, width, height, ...)
        """
        self._imgwin_wd = width
        self._imgwin_ht = height
        self._ctr_x = width // 2
        self._ctr_y = height // 2
        self.logger.info("widget resized to %dx%d" % (width, height))

        self.make_callback('configure', width, height)
        self.redraw(whence=0)

    def configure(self, width, height):
        self._imgwin_set = True
        self.set_window_size(width, height)

    def set_desired_size(self, width, height):
        self._desired_size = (width, height)
        if not self._imgwin_set:
            self.set_window_size(width, height)

    def get_desired_size(self):
        return self._desired_size

    def get_window_size(self):
        """
        Returns the window size in the underlying implementation as a tuple
        of (width, height).
        """
        ## if not self._imgwin_set:
        ##     raise ImageViewError("Dimensions of actual window are not yet determined")
        return (self._imgwin_wd, self._imgwin_ht)

    def get_dims(self, data):
        """
        Returns the dimensions of numpy array data as a tuple of
        (width, height).  data may have more dimensions, but they are not
        reported.
        """
        height, width = data.shape[:2]
        return (width, height)

    def get_data_size(self):
        """
        Returns the dimensions of the image currently being displayed as a
        tuple of (width, height).
        """
        image = self.get_image()
        if image is None:
            raise ImageViewNoDataError("No data found")
        return image.get_size()

    def get_settings(self):
        """
        Returns the Settings object used by this instance.
        """
        return self.t_

    def get_logger(self):
        """
        Returns the logger object used by this instance.
        """
        return self.logger

    def get_canvas(self):
        return self.canvas

    def set_canvas(self, canvas, private_canvas=None):
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

    def set_color_map(self, cmap_name):
        """Sets the color map.

        Parameters
        ----------
        cmap_name:  string
            the name of a color map
        """
        cm = cmap.get_cmap(cmap_name)
        self.set_cmap(cm)

    def set_intensity_map(self, imap_name):
        """Sets the intensity map.

        Parameters
        ----------
        imap_name:  string
            the name of an intensity map
        """
        im = imap.get_imap(imap_name)
        self.set_imap(im)

    def set_color_algorithm(self, calg_name, **kwdargs):
        """Sets the color distribution algorithm.

        Parameters
        ----------
        calg_name:  string
            the name of a color distribution algorithm
        """
        distClass = ColorDist.get_dist(calg_name)
        hashsize = self.rgbmap.get_hash_size()
        dist = distClass(hashsize, **kwdargs)
        self.set_calg(dist)

    def get_color_algorithms(self):
        return ColorDist.get_dist_names()

    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)

    def set_imap(self, im):
        self.rgbmap.set_imap(im)

    def set_calg(self, dist):
        self.rgbmap.set_dist(dist)

    def shift_cmap(self, pct):
        self.rgbmap.shift(pct)

    def scale_and_shift_cmap(self, scale_pct, shift_pct):
        self.rgbmap.scale_and_shift(scale_pct, shift_pct)

    def rgbmap_cb(self, rgbmap):
        self.logger.debug("RGB map has changed.")
        self.redraw(whence=2)

    def cmap_changed_cb(self, setting, value):
        # This method is a callback that is invoked when the color settings
        # have changed in some way.
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
        """
        Returns the RGBMapper object used by this instance.
        """
        return self.rgbmap

    def set_rgbmap(self, rgbmap):
        """
        Set the RGBMapper object used by this instance.  The RGBMapper
        controls how the values in the image are mapped to color.

        See RGBMap module.
        """
        self.rgbmap = rgbmap
        rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw(whence=2)

    def get_image(self):
        """
        Returns the image currently being displayed.  The object returned
        will be a subclass of BaseImage.
        """
        if not (self._imgobj is None):
            # quick optomization
            return self._imgobj.image

        canvas_img = self.get_canvas_image()
        return canvas_img.image

    def get_canvas_image(self):
        if not (self._imgobj is None):
            return self._imgobj

        try:
            # See if there is an image on the canvas
            self._imgobj = self.canvas.getObjectByTag(self._canvas_img_tag)

        except KeyError:
            # add a normalized image item to this canvas if we don't
            # have one already--then just keep reusing it
            NormImage = self.canvas.getDrawClass('normimage')
            interp = self.t_.get('interpolation', 'basic')
            self._imgobj = NormImage(0, 0, None, alpha=1.0,
                                      interpolation=interp)
        return self._imgobj

    def set_image(self, image, add_to_canvas=True,
                  raise_initialize_errors=True):
        """
        Sets an image to be displayed.

        image should be a subclass of BaseImage.
        If there is no error, this method will invoke the 'image-set'
        callback.

        If raise_initialize_errors is passed as False, then errors
        relating to orienting/zooming/centering/autolevels will not
        raise an exception, although an error message and traceback
        will appear in the log.
        """
        with self.suppress_redraw:

            canvas_img = self.get_canvas_image()
            canvas_img.set_image(image)

            if add_to_canvas:
                try:
                    self.canvas.getObjectByTag(self._canvas_img_tag)
                except KeyError:
                    tag = self.canvas.add(canvas_img,
                                                tag=self._canvas_img_tag)
                    #print("adding image to canvas %s" % self.canvas)

                # move image to bottom of layers
                self.canvas.lowerObject(canvas_img)

            profile = image.get('profile', None)
            try:
                # initialize transform
                if (profile is not None) and (self.t_['profile_use_transform']) and \
                       profile.has_key('flip_x'):
                    flip_x, flip_y = profile['flip_x'], profile['flip_y']
                    swap_xy = profile['swap_xy']
                    self.transform(flip_x, flip_y, swap_xy)
                else:
                    self.logger.debug("auto orient (%s)" % (self.t_['auto_orient']))
                    if self.t_['auto_orient']:
                        self.auto_orient()

                # initialize scale
                if (profile is not None) and (self.t_['profile_use_scale']) and \
                       profile.has_key('scale_x'):
                    scale_x, scale_y = profile['scale_x'], profile['scale_y']
                    self.scale_to(scale_x, scale_y, no_reset=True)
                else:
                    self.logger.debug("auto zoom (%s)" % (self.t_['autozoom']))
                    if self.t_['autozoom'] != 'off':
                        self.zoom_fit(no_reset=True)

                # initialize pan position
                if (profile is not None) and (self.t_['profile_use_pan']) and \
                       profile.has_key('pan_x'):
                    pan_x, pan_y = profile['pan_x'], profile['pan_y']
                    self.set_pan(pan_x, pan_y, no_reset=True)
                else:
                    # NOTE: False a possible value from historical use
                    self.logger.debug("auto center (%s)" % (self.t_['autocenter']))
                    if not self.t_['autocenter'] in ('off', False):
                        self.center_image(no_reset=True)

                # initialize rotation
                if (profile is not None) and (self.t_['profile_use_rotation']) and \
                       profile.has_key('rot_deg'):
                    rot_deg = profile['rot_deg']
                    self.rotate(rot_deg)

                # initialize cuts
                if (profile is not None) and (self.t_['profile_use_cuts']) and \
                       profile.has_key('cutlo'):
                    loval, hival = profile['cutlo'], profile['cuthi']
                    self.cut_levels(loval, hival, no_reset=True)
                else:
                    self.logger.debug("auto cuts (%s)" % (self.t_['autocuts']))
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
                if raise_initialize_errors:
                    raise e

            self.canvas.update_canvas(whence=0)

        # update our display if the image changes underneath us
        image.add_callback('modified', self._image_updated)

        self.make_callback('image-set', image)

    def _image_updated(self, image):

        with self.suppress_redraw:

            canvas_img = self.get_canvas_image()
            #canvas_img.set_image(image)
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
        """
        Sets an image to be displayed by providing raw data.

        This is a convenience method for first constructing an image
        with AstroImage and then calling set_image().

        data should be at least a 2D numpy array.
        metadata can be a dictionary (map-like) of image metadata.
        """
        dims = data.shape
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      logger=self.logger)
        self.set_image(image)

    def clear(self):
        """
        Clear the displayed image.
        """
        self.canvas.deleteAllObjects()
        self._imgobj = None
        self.canvas.update_canvas(whence=0)

    def save_profile(self, **params):
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
        """
        Extract our image and call set_image() on the target with it.
        """
        image = self.get_image()
        target.set_image(image)

    def redraw(self, whence=0):
        if not self.defer_redraw:
            if self._hold_redraw_cnt == 0:
                self.redraw_now(whence=whence)
            return

        with self._defer_lock:
            whence = min(self._defer_whence, whence)
            # If there is no redraw scheduled:
            if not self._defer_flag:
                elapsed = time.time() - self.time_last_redraw
                # If more time than defer_lagtime has passed since the
                # last redraw then just do the redraw immediately
                if elapsed > self.defer_lagtime:
                    if self._hold_redraw_cnt > 0:
                        #self._defer_flag = True
                        self._defer_whence = whence
                        return

                    self._defer_whence = 3
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

    def canvas_changed_cb(self, canvas, whence):
        self.logger.debug("root canvas changed, whence=%d" % (whence))
        self.redraw(whence=whence)

    def delayed_redraw(self):
        # This is the optomized redraw method
        with self._defer_lock:
            # pick up the lowest necessary level of redrawing
            whence = self._defer_whence
            self._defer_whence = 3
            flag = self._defer_flag
            self._defer_flag = False

        if flag:
            # If a redraw was scheduled, do it now
            self.redraw_now(whence=whence)

    def set_redraw_lag(self, lag_sec):
        self.defer_redraw = (lag_sec > 0.0)
        if self.defer_redraw:
            self.defer_lagtime = lag_sec

    def redraw_now(self, whence=0):
        """
        Redraw the displayed image.

        For the meaning of whence, see get_rgb_object().
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
            self.logger.debug("widget '%s' redraw (whence=%d) delta=%.4f elapsed=%.4f sec" % (
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
        """
        Do not call this method unless you are implementing a subclass.
        """
        if not self._imgwin_set:
            # window has not been realized yet
            return

        rgbobj = self.get_rgb_object(whence=whence)
        self.render_image(rgbobj, self._dst_x, self._dst_y)

        self.private_canvas.draw(self)

        # TODO: see if we can deprecate this fake callback
        if whence <= 0:
            self.make_callback('redraw')

    def getwin_array(self, order='RGB', alpha=1.0):
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
        outarr = self.getwin_array(order=order)

        return outarr.tostring(order='C')

    def get_datarect(self):
        """
        Returns the approximate bounding box of the displayed image in
        data coordinates (x1, y1, x2, y2).
        """
        x1, y1, x2, y2 = self._org_x1, self._org_y1, self._org_x2, self._org_y2
        return (x1, y1, x2, y2)

    def get_rgb_object(self, whence=0):
        """
        Create and return an RGB slices object representing the data
        that should be rendered at this zoom level and pan settings.

        `whence` is an optimization flag that reduces the time to create
        the object by only recalculating what is necessary:

        0   = new image, pan/scale has changed, or rotation/transform
                 has changed--recalculate everything
        1   = cut levels or similar has changed
        2   = color mapping has changed
        3   = graphical overlays have changed
        """
        time_start = time.time()
        win_wd, win_ht = self.get_window_size()
        order = self.get_rgb_order()

        if (whence <= 0.0) or (self._rgbarr is None):
            # calculate dimensions of window RGB backing image
            wd, ht = self._calc_bg_dimensions(self._scale_x, self._scale_y,
                                              self._pan_x, self._pan_y,
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
            new_scale_x = scale_x * sx
            new_scale_y = scale_y * sy
            self.logger.warn("scale adjusted downward X (%.4f -> %.4f), Y (%.4f -> %.4f)" % (
                scale_x, new_scale_x, scale_y, new_scale_y))
            scale_x, scale_y = new_scale_x, new_scale_y

        # It is necessary to store these so that the get_data_xy()
        # (below) calculations can proceed
        self._org_x, self._org_y = pan_x - self.data_off, pan_y - self.data_off
        self._org_scale_x, self._org_scale_y = scale_x, scale_y

        # calc minimum size of pixel image we will generate
        # necessary to fit the window in the desired size

        # get the data points in the four corners
        xul, yul = self.get_data_xy(0, 0, center=True)
        xur, yur = self.get_data_xy(win_wd, 0, center=True)
        xlr, ylr = self.get_data_xy(win_wd, win_ht, center=True)
        xll, yll = self.get_data_xy(0, win_ht, center=True)

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


    def apply_transforms(self, data, rot_deg):
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

        # dimensions may have changed in a swap axes
        wd, ht = self.get_dims(data)

        # Rotate the image as necessary
        if rot_deg != 0:
            # TODO: this is the slowest part of the rendering
            # need to find a way to speed it up!
            data = trcalc.rotate_clip(data, -rot_deg, out=data)

        split2_time = time.time()

        # apply other transforms
        if self._invertY:
            # Flip Y for natural natural Y-axis inversion between FITS coords
            # and screen coords
            data = numpy.flipud(data)

        self.logger.debug("rotate time %.3f sec, total reshape %.3f sec" % (
            split2_time - split_time, split2_time - start_time))

        ctr_x, ctr_y = self._ctr_x, self._ctr_y
        dst_x, dst_y = ctr_x - xoff, ctr_y - (ht - yoff)
        self._dst_x, self._dst_y = dst_x, dst_y
        self.logger.debug("ctr=%d,%d off=%d,%d dst=%d,%d cutout=%dx%d" % (
            ctr_x, ctr_y, xoff, yoff, dst_x, dst_y, wd, ht))
        return data


    def overlay_images(self, canvas, data, whence=0.0):
        #if not canvas.is_compound():
        if not hasattr(canvas, 'objects'):
            return

        for obj in canvas.getObjects():
            if hasattr(obj, 'draw_image'):
                obj.draw_image(self, data, whence=whence)
            elif obj.is_compound() and (obj != canvas):
                self.overlay_images(obj, data, whence=whence)

    def convert_via_profile(self, rgbobj, inprof_name, outprof_name):

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

    def get_data_xy(self, win_x, win_y, center=True):
        """Returns the closest x, y coordinates in the data array to the
        x, y coordinates reported on the window (win_x, win_y).

        If center==True, then the coordinates are mapped such that the
        pixel is centered on the square when the image is zoomed in past
        1X.  This is the specification of the FITS image standard,
        that the pixel is centered on the integer row/column.

        This function can take numpy arrays for win_x and win_y.
        """
        # First, translate window coordinates onto pixel image
        off_x, off_y = self.canvas2offset(win_x, win_y)

        # Reverse scaling
        off_x = off_x * (1.0 / self._org_scale_x)
        off_y = off_y * (1.0 / self._org_scale_y)

        # Add data index at (_ctr_x, _ctr_y) to offset
        data_x = self._org_x + off_x
        data_y = self._org_y + off_y
        if center:
            data_x += self.data_off
            data_y += self.data_off

        return (data_x, data_y)

    def get_canvas_xy(self, data_x, data_y, center=True):
        """Returns the closest x, y coordinates in the graphics space to the
        x, y coordinates in the data.  data_x and data_y can be integer or
        floating point values.

        If center==True, then the coordinates are mapped such that the
        integer pixel begins in the center of the square when the image
        is zoomed in past 1X.  This is the specification of the FITS image
        standard, that the pixel is centered on the integer row/column.

        This function can take numpy arrays for data_x and data_y.
        """
        if center:
            data_x -= self.data_off
            data_y -= self.data_off
        # subtract data indexes at center reference pixel
        off_x = data_x - self._org_x
        off_y = data_y - self._org_y

        # scale according to current settings
        off_x *= self._org_scale_x
        off_y *= self._org_scale_y

        win_x, win_y = self.offset2canvas(off_x, off_y)
        return (win_x, win_y)

    def offset2canvas(self, off_x, off_y, asint=True):
        """
        This method can take numpy arrays for off_x and off_y.
        """
        if self.t_['flip_x']:
            off_x = - off_x
        if self.t_['flip_y']:
            off_y = - off_y
        if self.t_['swap_xy']:
            off_x, off_y = off_y, off_x

        if self.t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y,
                                            self.t_['rot_deg'])

        # add center pixel to convert from X/Y coordinate space to
        # canvas graphics space
        win_x = off_x + self._ctr_x
        if self._originUpper:
            win_y = self._ctr_y - off_y
        else:
            win_y = off_y + self._ctr_y

        # round to pixel units
        if asint:
            win_x = numpy.rint(win_x).astype(numpy.int)
            win_y = numpy.rint(win_y).astype(numpy.int)

        return (win_x, win_y)

    def canvas2offset(self, win_x, win_y):
        """
        This method can take numpy arrays for win_x and win_y.
        """
        # make relative to center pixel to convert from canvas
        # graphics space to standard X/Y coordinate space
        off_x = win_x - self._ctr_x
        if self._originUpper:
            off_y = self._ctr_y - win_y
        else:
            off_y = win_y - self._ctr_y

        if self.t_['rot_deg'] != 0:
            off_x, off_y = trcalc.rotate_pt(off_x, off_y,
                                            -self.t_['rot_deg'])

        if self.t_['swap_xy']:
            off_x, off_y = off_y, off_x
        if self.t_['flip_y']:
            off_y = - off_y
        if self.t_['flip_x']:
            off_x = - off_x

        return (off_x, off_y)

    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def get_data_pct(self, xpct, ypct):
        width, height = self.get_data_size()
        x = int(float(xpct) * (width-1))
        y = int(float(ypct) * (height-1))
        return (x, y)

    def get_pan_rect(self):
        """Return the coordinates in the actual data corresponding to the
        area shown in the display for the current zoom level and pan.
        Returns ((x0, y0), (x1, y1), (x2, y2), (x3, y3)) lower-left to
        lower-right.
        """
        points = []
        wd, ht = self.get_window_size()
        for x, y in ((0, 0), (wd-1, 0), (wd-1, ht-1), (0, ht-1)):
            c, d = self.get_data_xy(x, y)
            points.append((c, d))
        return points


    def get_data(self, data_x, data_y):
        """Get the data value at position (data_x, data_y).  Indexes are
        0-based, as in numpy.
        """
        image = self.get_image()
        if image is not None:
            return image.get_data_xy(data_x, data_y)
        raise ImageViewNoDataError("No image found")

    def get_pixel_distance(self, x1, y1, x2, y2):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dist = math.sqrt(dx*dx + dy*dy)
        dist = round(dist)
        return dist

    def scale_to(self, scale_x, scale_y, no_reset=False):
        """Scale the image in a channel.

        Parameters
        ----------
        chname: string
            the name of the channel containing the image
        scale_x: float
            the scaling factor for the image in the X axis
        scale_y: float
            the scaling factor for the image in the Y axis

        Returns
        -------
        0

        See Also
        --------
        zoom_to
        """
        ratio = float(scale_x) / float(scale_y)
        if ratio < 1.0:
            # Y is stretched
            scale_x_base, scale_y_base = 1.0, 1.0 / ratio
        else:
            # X may be stretched
            scale_x_base, scale_y_base = ratio, 1.0
        if scale_x_base != scale_y_base:
            zoomalg = 'rate'
        else:
            zoomalg = 'step'

        self.t_.set(scale_x_base=scale_x_base, scale_y_base=scale_y_base,
                    #zoom_algorithm=zoomalg)
                    )

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
            win_wd, win_ht = self.get_window_size()
            if (win_ht <= 0) or (win_ht <= 0):
                # TODO: exception?
                return
            sx = float(win_wd) / scale_x
            sy = float(win_ht) / scale_y
            if (sx < 1.0) or (sy < 1.0):
                new_scale_x = scale_x * sx
                new_scale_y = scale_y * sy
                self.logger.warn("scale adjusted downward X (%.4f -> %.4f), Y (%.4f -> %.4f)" % (
                    scale_x, new_scale_x, scale_y, new_scale_y))
                scale_x, scale_y = new_scale_x, new_scale_y
        except:
            pass

        self.t_.set(scale=(scale_x, scale_y))

        # If user specified "override" or "once" for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_['autozoom'] in ('override', 'once')):
            self.t_.set(autozoom='off')

        if self.t_['profile_use_scale']:
            # Save scale with this image embedded profile
            self.save_profile(scale_x=scale_x, scale_y=scale_y)

    def scale_cb(self, setting, value):
        scale_x, scale_y = self.t_['scale']
        self._scale_x = scale_x
        self._scale_y = scale_y

        if self.t_['zoom_algorithm'] == 'rate':
            zoom_x = math.log(scale_x / self.t_['scale_x_base'],
                              self.t_['zoom_rate'])
            zoom_y = math.log(scale_y / self.t_['scale_y_base'],
                              self.t_['zoom_rate'])
            # TODO: avg, max?
            zoomlevel = min(zoom_x, zoom_y)
            #print "calc zoom_x=%f zoom_y=%f zoomlevel=%f" % (
            #    zoom_x, zoom_y, zoomlevel)
        else:
            maxscale = max(scale_x, scale_y)
            zoomlevel = maxscale
            if zoomlevel < 1.0:
                zoomlevel = - (1.0 / zoomlevel)
            #print "calc zoomlevel=%f" % (zoomlevel)

        self.t_.set(zoomlevel=zoomlevel)

        self.redraw(whence=0)

    def get_scale(self):
        return self.get_scale_max()

    def get_scale_max(self):
        #scalefactor = max(self._org_scale_x, self._org_scale_y)
        scalefactor = max(self._scale_x, self._scale_y)
        return scalefactor

    def get_scale_xy(self):
        #return (self._org_scale_x, self._org_scale_y)
        return (self._scale_x, self._scale_y)

    def get_scale_base_xy(self):
        return (self.t_['scale_x_base'], self.t_['scale_y_base'])

    def set_scale_base_xy(self, scale_x_base, scale_y_base):
        self.t_.set(scale_x_base=scale_x_base, scale_y_base=scale_y_base)

    def get_scale_text(self):
        scalefactor = self.get_scale()
        if scalefactor >= 1.0:
            #text = '%dx' % (int(scalefactor))
            text = '%.2fx' % (scalefactor)
        else:
            #text = '1/%dx' % (int(1.0/scalefactor))
            text = '1/%.2fx' % (1.0/scalefactor)
        return text

    def zoom_to(self, zoomlevel, no_reset=False):
        """Set zoom level on channel.

        Parameters
        ----------
        zoomlevel: int
            the zoom level to zoom the image: negative is out, positive is in

        Returns
        -------
        0

        Notes
        -----
        The zoom level is an integer that calculates a zoom level based on
        the zoom settings defined for the channel in preferences.

        See Also
        --------
        scale
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
        if self.t_['zoom_algorithm'] == 'rate':
            self.zoom_to(self.t_['zoomlevel'] + 1)
        else:
            zl = int(self.t_['zoomlevel'])
            if (zl >= 1) or (zl <= -3):
                self.zoom_to(zl + 1)
            else:
                self.zoom_to(1)

    def zoom_out(self):
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
                scale_x = float(wwidth) / (float(width) * self.t_['scale_x_base'])
                scale_y = float(wheight) / (float(height) * self.t_['scale_y_base'])

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
        return self.t_['zoomlevel']

    def get_zoomrate(self):
        return self.t_['zoom_rate']

    def set_zoomrate(self, zoomrate):
        self.t_.set(zoom_rate=zoomrate)

    def get_zoom_algorithm(self):
        return self.t_['zoom_algorithm']

    def set_zoom_algorithm(self, name):
        name = name.lower()
        assert name in ('step', 'rate'), \
              ImageViewError("Alg '%s' must be one of: step, rate" % name)
        self.t_.set(zoom_algorithm=name)

    def zoomalg_change_cb(self, setting, value):
        self.zoom_to(self.t_['zoomlevel'])

    def interpolation_change_cb(self, setting, value):
        canvas_img = self.get_canvas_image()
        canvas_img.interpolation = value
        canvas_img.reset_optimize()
        self.redraw(whence=0)

    def set_name(self, name):
        self.name = name

    def get_scale_limits(self):
        return (self.t_['scale_min'], self.t_['scale_max'])

    def set_scale_limits(self, scale_min, scale_max):
        # TODO: force scale to within limits if already outside?
        self.t_.set(scale_min=scale_min, scale_max=scale_max)

    def enable_autozoom(self, option):
        option = option.lower()
        assert(option in self.autozoom_options), \
                      ImageViewError("Bad autozoom option '%s': must be one of %s" % (
            str(self.autozoom_options)))
        self.t_.set(autozoom=option)

    def get_autozoom_options(self):
        return self.autozoom_options

    def set_pan(self, pan_x, pan_y, coord='data', no_reset=False):
        with self.suppress_redraw:
            self.t_.set(pan=(pan_x, pan_y), pan_coord=coord)

        # If user specified "override" or "once" for auto center, then turn off
        # auto center now that they have set the pan manually
        if (not no_reset) and (self.t_['autocenter'] in ('override', 'once')):
            self.t_.set(autocenter='off')

        if self.t_['profile_use_pan']:
            # Save pan position with this image embedded profile
            self.save_profile(pan_x=pan_x, pan_y=pan_y)


    def pan_cb(self, setting, value):
        pan_x, pan_y = self.t_['pan']
        self._pan_x = pan_x
        self._pan_y = pan_y
        self.logger.debug("pan set to %.2f,%.2f" % (pan_x, pan_y))
        self.redraw(whence=0)

    def get_pan(self, coord='data'):
        pan_x, pan_y = self._pan_x, self._pan_y
        if coord == 'wcs':
            if self.t_['pan_coord'] == 'data':
                image = self.get_image()
                return image.pixtoradec(pan_x, pan_y)
            # <-- data already in coordinates form
            return (pan_x, pan_y)

        # <-- requesting data coords
        if self.t_['pan_coord'] == 'data':
            return (pan_x, pan_y)
        image = self.get_image()
        return image.radectopix(pan_x, pan_y)

    def panset_xy(self, data_x, data_y, no_reset=False):
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
        try:
            width, height = self.get_data_size()
        except ImageViewNoDataError:
            return

        data_x, data_y = width * pct_x, height * pct_y
        self.panset_xy(data_x, data_y)

    def center_image(self, no_reset=True):
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
        option = option.lower()
        assert(option in self.autocenter_options), \
                      ImageViewError("Bad autocenter option '%s': must be one of %s" % (
            str(self.autocenter_options)))
        self.t_.set(autocenter=option)

    def get_autocenter_options(self):
        return self.autocenter_options

    def get_transforms(self):
        return (self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy'])

    def get_cut_levels(self):
        return self.t_['cuts']

    def cut_levels(self, loval, hival, no_reset=False):
        """Apply cut levels on the image view.

        Parameters
        ----------
        loval : float
            the low value of the cut levels
        hival : float
            the high value of the cut levels
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
        """
        Apply an auto cut levels on the image view.

        Parameters
        ----------
        autocuts : a ginga.AutoCuts.* compatible object
            An object that implements the auto cuts algorithms
        redraw : boolean, optional
            If True, will redraw the image with the cut levels applied

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
        # Did we change the method?
        method = self.t_['autocut_method']
        params = self.t_.get('autocut_params', [])
        # TEMP: params is stored as a list of tuples
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
        self.redraw(whence=1)

    def enable_autocuts(self, option):
        option = option.lower()
        assert(option in self.autocuts_options), \
                      ImageViewError("Bad autocuts option '%s': must be one of %s" % (
            str(self.autocuts_options)))
        self.t_.set(autocuts=option)

    def get_autocuts_options(self):
        return self.autocuts_options

    def set_autocut_params(self, method, **params):
        self.logger.debug("Setting autocut params method=%s params=%s" % (
            method, str(params)))
        params = list(params.items())
        self.t_.set(autocut_method=method, autocut_params=params)

    def get_autocut_methods(self):
        return self.autocuts.get_algorithms()

    def set_autocuts(self, autocuts):
        """
        Set the autocuts class instance that determines the algorithm used
        for calculating cut levels.
        """
        self.autocuts = autocuts

    def transform(self, flip_x, flip_y, swap_xy):
        """Transforms view of image.

        Parameters
        ----------
        flipx:  boolean
            if True, flip the image in the X axis
        flipy:  boolean
            if True, flip the image in the Y axis
        swapxy:  boolean
            if True, swap the X and Y axes

        Returns
        -------
        0

        Notes
        -----
        Transforming the image is generally faster than rotating,
        if rotating in 90 degree increments.

        See Also
        --------
        rotate
        """
        self.logger.debug("flip_x=%s flip_y=%s swap_xy=%s" % (
            flip_x, flip_y, swap_xy))

        with self.suppress_redraw:
            self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)

        if self.t_['profile_use_transform']:
            # Save transform with this image embedded profile
            self.save_profile(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)

    def transform_cb(self, setting, value):
        self.make_callback('transform')
        # whence=0 because need to calculate new extents for proper
        # cutout for rotation (TODO: always make extents consider
        #  room for rotation)
        whence = 0
        self.redraw(whence=whence)

    def copy_attributes(self, dst_fi, attrlist):
        """Copy interesting attributes of our configuration to another
        instance of a ImageView."""

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
                dst_fi.set_pan(self._pan_x, self._pan_y)

            dst_fi.redraw(whence=0)

    def get_rotation(self):
        return self.t_['rot_deg']

    def rotate(self, deg):
        """Rotates the view of image in channel.

        Parameters
        ----------
        deg:  float
            degrees to rotate the image

        Returns
        -------
        0

        Notes
        -----
        Transforming the image is generally faster than rotating,
        if rotating in 90 degree increments.

        See Also
        --------
        transform
        """
        self.t_.set(rot_deg=deg)

        if self.t_['profile_use_rotation']:
            # Save rotation with this image embedded profile
            self.save_profile(rot_deg=deg)

    def rotation_change_cb(self, setting, value):
        # whence=0 because need to calculate new extents for proper
        # cutout for rotation (TODO: always make extents consider
        #  room for rotation)
        whence = 0
        self.redraw(whence=whence)

    def get_center(self):
        return (self._ctr_x, self._ctr_y)

    def get_rgb_order(self):
        return 'RGB'

    def get_rotation_info(self):
        return (self._ctr_x, self._ctr_y, self.t_['rot_deg'])

    def enable_auto_orient(self, tf):
        self.t_.set(auto_orient=tf)

    def auto_orient(self):
        """Set the orientation for the image to a reasonable default.
        """
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
                    self.logger.info("setting orientation from metadata [%d]" % (
                        orient))
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
        return self.coordmap[key]

    def set_coordmap(self, key, mapper):
        self.coordmap[key] = mapper

    # TO BE DEPRECATED
    def enable_overlays(self, tf):
        self.t_.set(image_overlays=tf)

    # TO BE DEPRECATED
    def overlays_change_cb(self, setting, value):
        self.redraw(whence=2)

    def set_bg(self, r, g, b):
        """Set the background color.  Values r, g, b should be between
        0 and 1 inclusive.
        """
        self.img_bg = (r, g, b)
        self.redraw(whence=3)

    def get_bg(self):
        return self.img_bg

    def set_fg(self, r, g, b):
        """Set the foreground color.  Values r, g, b should be between
        0 and 1 inclusive.
        """
        self.img_fg = (r, g, b)
        self.redraw(whence=3)

    def get_fg(self):
        return self.img_fg

    def is_compound(self):
        # this is overridden by subclasses which can overplot objects
        return False

    def update_image(self):
        self.logger.warn("Subclass should override this abstract method!")

    def render_image(self, rgbobj, dst_x, dst_y):
        self.logger.warn("Subclass should override this abstract method!")

    def reschedule_redraw(self, time_sec):
        self.logger.warn("Subclass should override this abstract method!")


## class SuppressRedraw(object):
##     def __init__(self, viewer):
##         self.viewer = viewer

##     def __enter__(self):
##         self.viewer._hold_redraw_cnt += 1
##         return self

##     def __exit__(self, exc_type, exc_val, exc_tb):
##         self.viewer._hold_redraw_cnt -= 1

##         if (self.viewer._hold_redraw_cnt <= 0):
##             # TODO: whence should be largest possible
##             # maybe self.viewer._defer_whence ??
##             whence = 0
##             self.viewer.redraw(whence=whence)
##         return False

class SuppressRedraw(object):
    def __init__(self, viewer):
        self.viewer = viewer

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

# FOOTNOTES
# [1] This redraw is redundant due to the automatic redraw happening via
#     a preferences callback.  It is commented out, but left here in case
#     we can/need to implement it again.


#END
