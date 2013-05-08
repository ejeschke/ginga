#
# FitsImage.py -- abstract classes for the display of FITS files
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
import sys, traceback
import time

from ginga.misc import Callback, Settings
from ginga import RGBMap, AstroImage, AutoCuts
from ginga import cmap, imap, version


class FitsImageError(Exception):
    pass
class FitsImageCoordsError(FitsImageError):
    pass

class FitsImageBase(Callback.Callbacks):
    """An abstract base class for displaying FITS images represented by
    numpy data arrays, such as loaded by the pyfits module.

    This class attempts to do as much of the image handling using numpy
    array manipulations (even color and intensity mapping) so that only
    a minimal mapping to a pixel buffer is necessary in concrete subclasses
    that connect to an actual rendering surface.
    """

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindings=None):
        Callback.Callbacks.__init__(self)

        if logger != None:
            self.logger = logger
        else:
            self.logger = logging.Logger('FitsImageBase')

        # RGB mapper
        if rgbmap:
            self.rgbmap = rgbmap
        else:
            rgbmap = RGBMap.RGBMapper()
            self.rgbmap = rgbmap

        # Object that calculates auto cut levels
        self.autocuts = AutoCuts.AutoCuts(self.logger)
        
        # Dummy 1-pixel image
        self.image = AstroImage.AstroImage(numpy.zeros((1, 1)),
                                           logger=self.logger)
        # for debugging
        self.name = str(self)

        # Create settings and set defaults
        if settings == None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.t_ = settings
        
        # for color mapping
        self.t_.addDefaults(color_map='ramp', intensity_map='ramp',
                            color_algorithm='linear',
                            color_hashsize=65535)
        for name in ('color_map', 'intensity_map', 'color_algorithm',
                     'color_hashsize'):
            self.t_.getSetting(name).add_callback('set', self.cmap_changed_cb)

        # Initialize RGBMap
        cmap_name = self.t_.get('color_map', 'ramp')
        try:
            cm = cmap.get_cmap(cmap_name)
        except KeyError:
            cm = cmap.get_cmap('ramp')
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

        # for cut levels
        self.t_.addDefaults(locut=0.0, hicut=0.0)
        for name in ('locut', 'hicut'):
            self.t_.getSetting(name).add_callback('set', self.cut_levels_cb)

        # for auto cut levels
        self.autocuts_options = ('on', 'override', 'off')
        self.t_.addDefaults(autocuts='override', autocut_method='histogram',
                            autocut_hist_pct=AutoCuts.default_autocuts_hist_pct,
                            autocut_bins=AutoCuts.default_autocuts_bins)
        for name in ('autocuts', 'autocut_method', 'autocut_hist_pct',
                     'autocut_bins'):
            self.t_.getSetting(name).add_callback('set', self.auto_levels_cb)

        # for zooming
        self.t_.addDefaults(zoomlevel=1.0, zoom_algorithm='step',
                            scale_x_base=1.0, scale_y_base=1.0,
                            zoom_rate=math.sqrt(2.0))
        for name in ('zoom_rate', 'zoom_algorithm', 'scale_x_base', 'scale_y_base'):
            self.t_.getSetting(name).add_callback('set', self.zoomalg_change_cb)

        # max/min scaling
        self.t_.addDefaults(scale_max=10000.0, scale_min=0.00001)
        
        # autozoom options
        self.autozoom_options = ('on', 'override', 'off')
        self.t_.addDefaults(autozoom='on')

        # for panning
        self.t_makebg = False
        self.t_.addDefaults(reverse_pan=False, autocenter=True)
        
        # for transforms
        self.t_.addDefaults(flip_x=False, flip_y=False, swap_xy=False)
        for name in ('flip_x', 'flip_y', 'swap_xy'):
            self.t_.getSetting(name).add_callback('set', self.transform_cb)

        # desired rotation angle
        self.t_.addDefaults(rot_deg=0.0)
        self.t_.getSetting('rot_deg').add_callback('set', self.rotation_change_cb)

        # misc
        self.t_.addDefaults(use_embedded_profile=True, auto_orient=False)

        # PRIVATE IMPLEMENTATION STATE
        
        # image window width and height (see set_window_dimensions())
        self._imgwin_wd = 1
        self._imgwin_ht = 1
        self._imgwin_set = False
        # center (and reference) pixel in the screen image (in pixel coords)
        self._ctr_x = 1
        self._ctr_y = 1
        # data indexes at the reference pixel (in data coords)
        self._org_x = 0
        self._org_y = 0

        # pan position
        self._pan_x = 0.0
        self._pan_y = 0.0

        # Origin in the data array of what is currently displayed (LL, UR)
        self._org_x1 = 0
        self._org_y1 = 0
        self._org_x2 = 0
        self._org_y2 = 0
        # offsets in the screen image for drawing (in screen coords)
        self._dst_x = 0
        self._dst_y = 0
        self._invertY = True
        # offsets in the screen image (in data coords)
        self._off_x = 0
        self._off_y = 0

        # desired scale factors
        self._scale_x = 1.0
        self._scale_y = 1.0
        # actual scale factors produced from desired ones
        self._org_scale_x = 0
        self._org_scale_y = 0

        self._cutout = None
        self._rotimg = None
        self._prergb = None
        self._rgbarr = None

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
        
        # For callbacks
        # TODO: we should be able to deprecate a lot of these with the new
        # settings callbacks
        for name in ('cut-set', 'zoom-set', 'pan-set', 'transform',
                     'rotate', 'image-set', 'configure',
                     'autocuts', 'autozoom'):
            self.enable_callback(name)

    def set_window_size(self, width, height, redraw=True):
        """This is called by the subclass when the actual dimensions of the
        window are known."""
        self._imgwin_wd = width
        self._imgwin_ht = height
        self._ctr_x = width // 2
        self._ctr_y = height // 2
        self._imgwin_set = True
        self.logger.info("image resized to %dx%d" % (width, height))

        self.make_callback('configure', width, height)
        if redraw:
            self.redraw(whence=0)

    def get_window_size(self):
        if not self._imgwin_set:
            raise FitsImageError("Dimensions of actual window are not yet determined")
        return (self._imgwin_wd, self._imgwin_ht)

    def get_dims(self, data):
        height, width = data.shape[:2]
        return (width, height)

    def get_data_size(self):
        return self.image.get_size()

    def get_settings(self):
        return self.t_
    
    # TODO: deprecate these two?
    def set_cmap(self, cm, redraw=True):
        self.rgbmap.set_cmap(cm, callback=redraw)

    def set_imap(self, im, redraw=True):
        self.rgbmap.set_imap(im, callback=redraw)

    def shift_cmap(self, pct, redraw=True):
        self.rgbmap.shift(pct, callback=redraw)

    def scaleNshift_cmap(self, scale_pct, shift_pct, redraw=True):
        self.rgbmap.scaleNshift(scale_pct, shift_pct, callback=redraw)

    def rgbmap_cb(self, rgbmap):
        self.logger.info("RGB map has changed.")
        self.redraw(whence=1)
        
    def cmap_changed_cb(self, setting, value):
        self.logger.info("Color settings have changed.")

        cmap_name = self.t_.get('color_map', "ramp")
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
        return self.rgbmap

    def set_rgbmap(self, rgbmap, redraw=False):
        self.rgbmap = rgbmap
        rgbmap.add_callback('changed', self.rgbmap_cb)
        if redraw:
            self.redraw(whence=2)
        
    def get_image(self):
        return self.image
    
    def set_image(self, image, redraw=True):
        self.image = image
        profile = self.image.get('profile', None)
        if (profile != None) and (self.t_['use_embedded_profile']):
            self.apply_profile(profile, redraw=False)

        if self.t_['auto_orient']:
            self.auto_orient(redraw=False)

        if self.t_['autozoom'] != 'off':
            self.zoom_fit(redraw=False, no_reset=True)

        if self.t_['autocenter']:
            self.center_image(redraw=False)

        if self.t_['autocuts'] != 'off':
            self.auto_levels(redraw=False)

        if redraw:
            self.redraw()

        # update our display if the image changes underneath us
        image.add_callback('modified', self._image_updated)
        
        self.make_callback('image-set', image)

    def _image_updated(self, image):
        self.redraw(whence=0)
        
    def set_data(self, data, metadata=None, redraw=True):
        dims = data.shape
        ## assert (len(dims) == 2), \
        ##        FitsImageError("Only 2D images are supported!")
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      logger=self.logger)
        self.set_image(image, redraw=redraw)

    def clear(self, redraw=True):
        self.set_data(numpy.zeros((1, 1)), redraw=redraw)
        
    def save_profile(self, **params):
        if self.image == None:
            return
        profile = self.image.get('profile', None)
        if (profile == None):
            # If image has no profile then create one
            profile = Settings.SettingGroup()
            self.image.set(profile=profile) 

        self.logger.debug("saving to image profile: params=%s" % (
                str(params)))
        profile.set(**params)
            
    def apply_profile(self, profile, redraw=False):
        # If there is image metadata associated that has cut levels
        # then use those values if t_use_saved_cuts == True
        ## if (self.t_['use_saved_cuts'] and (self.image != None) and
        ##     (self.image.get('cutlo', None) != None)):
        ##     loval, hival = self.image.get_list('cutlo', 'cuthi')
        ##     self.logger.debug("setting cut levels from saved cuts lo=%f hi=%f" % (
        ##         loval, hival))
        ##     self.cut_levels(loval, hival, no_reset=True, redraw=redraw)
        pass

    def copy_to_dst(self, target):
        #target.set_data(self._data_org.copy())
        target.set_image(self.image)

    def redraw(self, whence=0):
        #print "REDRAWING %s whence=%d" % (str(self), whence)
        try:
            self.redraw_data(whence=whence)
            
            # finally update the window drawable from the offscreen surface
            self.update_image()

        except Exception, e:
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
        rgbobj = self.get_rgb_object(whence=whence)
        self.render_image(rgbobj, self._dst_x, self._dst_y)
        # TODO: see if we can deprecate this fake callback
        if whence <= 0:
            self.make_callback('pan-set')

    def render_image(self, rgbobj, dst_x, dst_y):
        self.logger.warn("Subclass needs to override this method!")
        
    def update_image(self):
        self.logger.warn("Subclass should override this abstract method!")
    
    def get_datarect(self):
        x1, y1, x2, y2 = self._org_x1, self._org_y1, self._org_x2, self._org_y2
        return (x1, y1, x2, y2)

    def get_rgb_object(self, whence=0):
        """Create an RGB numpy array (NxMx3) representing the data that
        should be rendered at this zoom level and pan settings.
        """
        time_start = time.time()
        if (whence <= 0) or (self._cutout == None):
            # Get the smallest slice of data that will fit our display needs.
            self._cutout = self.get_scaled_cutout(self.image,
                  self._scale_x, self._scale_y,
                  self._pan_x, self._pan_y,
                  self._imgwin_wd, self._imgwin_ht)

        time_split1 = time.time()
        if (whence <= 0.5) or (self._rotimg == None):
            # Apply any viewing transformations or rotations
            self._rotimg = self.apply_transforms(self._cutout,
                              self.t_['rot_deg'], 
                              self._imgwin_wd, self._imgwin_ht)
            
        time_split2 = time.time()
        if (whence <= 1) or (self._prergb == None):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = self.rgbmap.get_hash_size() - 1
            newdata = self.apply_visuals(self._rotimg, 0, vmax)

            # Convert data to an index array
            self._prergb = newdata.astype('uint')
            #self._prergb = newdata

        time_split3 = time.time()
        if (whence <= 2) or (self._rgbarr == None):
            #idx = self._prergb.astype('uint32')
            idx = self._prergb
            self.logger.debug("shape of index is %s" % (str(idx.shape)))

            # Apply color and intensity mapping.  We produce a group of
            # ARGB slices.
            rgb = self.rgbmap.get_rgbarray(idx)
            self._rgbarr = rgb

        time_end = time.time()
        self.logger.info("times: total=%.4f 0=%.4f 1=%.4f 2=%.4f" % (
            (time_end - time_start),
            (time_split2 - time_start),
            (time_split3 - time_split2),
            (time_end - time_split3),
            ))
        return self._rgbarr

    def get_scaled_cutout(self, image, scale_x, scale_y,
                          pan_x, pan_y, win_wd, win_ht):

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
        # (below) calculations can proceed, later these values may
        # refined slightly by the dimensions of the actual cutout
        self._org_x, self._org_y = pan_x, pan_y
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
        
        # constrain to image dimensions and integer indexes
        width, height = image.get_size()

        x1, y1, x2, y2 = int(a1), int(b1), int(round(a2)), int(round(b2))
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(x2, width-1)
        y2 = min(y2, height-1)

        # distance from start of cutout data to pan position
        xo, yo = pan_x - x1, pan_y - y1

        self.logger.info("approx area covered is %dx%d to %dx%d" % (
            x1, y1, x2, y2))

        self._org_x1 = x1
        self._org_y1 = y1
        self._org_x2 = x2
        self._org_y2 = y2

        # Cut out data and scale it appropriately
        res = image.get_scaled_cutout(x1, y1, x2, y2, scale_x, scale_y)
        data = res.data
        # actual cutout may have changed scaling slightly
        self._org_scale_x, self._org_scale_y = res.scale_x, res.scale_y
        #self._scale_x, self._scale_y = res.scale_x, res.scale_y
            
        # calculate dimensions of scaled cutout
        wd, ht = self.get_dims(data)
        ocx = int(xo * res.scale_x)
        ocy = int(yo * res.scale_y)
        self.logger.info("ocx,ocy=%d,%d cutout=%dx%d win=%dx%d" % (
            ocx, ocy, wd, ht, win_wd, win_ht))
        ## assert (0 <= ocx) and (ocx < wd) and (0 <= ocy) and (ocy < ht), \
        ##     FitsImageError("calculated center not in cutout!")
        if not ((0 <= ocx) and (ocx < wd) and (0 <= ocy) and (ocy < ht)):
            self.logger.warn("calculated center (%d,%d) not in cutout (%dx%d)" % (
                ocx, ocy, wd, ht))
        # offset from pan position (at center) in this array
        self._org_xoff, self._org_yoff = ocx, ocy

        # If there is no rotation, then we are done
        if not self.t_makebg and (self.t_['rot_deg'] == 0.0):
            return data

        # Make a square from the scaled cutout, with room to rotate
        slop = 20
        side = int(math.sqrt(win_wd**2 + win_ht**2) + slop)
        new_wd = new_ht = side
        dims = (new_ht, new_wd) + data.shape[2:]
        # TODO: fill with a different background color?
        newdata = numpy.zeros(dims)
        # Find center of new data array 
        ncx, ncy = new_wd // 2, new_ht // 2

        # Overlay the scaled cutout image on the window image
        # with the pan position centered on the center of the window
        ldx, rdx = min(ocx, ncx), min(wd - ocx, ncx)
        bdy, tdy = min(ocy, ncy), min(ht - ocy, ncy)

        newdata[ncy-bdy:ncy+tdy, ncx-ldx:ncx+rdx] = \
                                 data[ocy-bdy:ocy+tdy, ocx-ldx:ocx+rdx]
        self._org_xoff, self._org_yoff = ncx, ncy
        return newdata


    def apply_transforms(self, data, rot_deg, win_wd, win_ht):
        start_time = time.time()

        wd, ht = self.get_dims(data)
        xoff, yoff = self._org_xoff, self._org_yoff

        # Do transforms as necessary
        if self.t_['flip_y']:
            data = numpy.flipud(data)
            yoff = ht - yoff

        if self.t_['flip_x']:
            data = numpy.fliplr(data)
            xoff = wd - xoff

        if self.t_['swap_xy']:
            data = data.swapaxes(0, 1)
            xoff, yoff = yoff, xoff
            
        split_time = time.time()
        self.logger.info("reshape time %.3f sec" % (
            split_time - start_time))

        wd, ht = self.get_dims(data)

        # Rotate the image as necessary
        rotctr_x, rotctr_y = wd // 2, ht // 2
        if rot_deg != 0:
            # TODO: this is the slowest part of the rendering
            # need to find a way to speed it up!
            yi, xi = numpy.mgrid[0:ht, 0:wd]
            xi = xi - rotctr_x
            yi = yi - rotctr_y
            cos_t = numpy.cos(numpy.radians(-rot_deg))
            sin_t = numpy.sin(numpy.radians(-rot_deg))
            ap = (xi * cos_t) - (yi * sin_t) + rotctr_x
            bp = (xi * sin_t) + (yi * cos_t) + rotctr_y
            ## ap = numpy.rint(ap).astype('int').clip(0, wd-1)
            ## bp = numpy.rint(bp).astype('int').clip(0, ht-1)
            ap = ap.astype('int').clip(0, wd-1)
            bp = bp.astype('int').clip(0, ht-1)
            newdata = data[bp, ap]
            new_wd, new_ht = self.get_dims(newdata)
            self.logger.debug("rotated shape is %dx%d" % (new_wd, new_ht))

            assert (wd == new_wd) and (ht == new_ht), \
                   FitsImageError("rotated cutout is %dx%d original=%dx%d" % (
                new_wd, new_ht, wd, ht))
            wd, ht, data = new_wd, new_ht, newdata

        split2_time = time.time()
        self.logger.info("rotate time %.3f sec, total reshape %.3f sec" % (
            split2_time - split_time, split2_time - start_time))

        ## assert (wd >= win_wd) and (ht >= win_ht), \
        ##        FitsImageError("scaled cutout is %dx%d  window=%dx%d" % (
        ##     wd, ht, win_wd, win_ht))

        ctr_x, ctr_y = self._ctr_x, self._ctr_y
        dst_x, dst_y = ctr_x - xoff, ctr_y - (ht - yoff)
        self._dst_x, self._dst_y = dst_x, dst_y
        self.logger.info("ctr=%d,%d off=%d,%d dst=%d,%d cutout=%dx%d window=%d,%d" % (
            ctr_x, ctr_y, xoff, yoff, dst_x, dst_y, wd, ht, win_wd, win_ht))
        return data

    def get_data_xy(self, win_x, win_y, center=True):
        """Returns the closest x, y coordinates in the data array to the
        x, y coordinates reported on the window (win_x, win_y).

        If center==True, then the coordinates are mapped such that the
        integer pixel begins in the center of the square when the image
        is zoomed in past 1X.  This is the specification of the FITS image
        standard, that the pixel is centered on the integer row/column.
        """
        self.logger.debug("before adjustment, win_x=%d win_y=%d" % (win_x, win_y))

        # First, translate window coordinates onto pixel image
        off_x, off_y = self.canvas2offset(win_x, win_y)

        # Reverse scaling
        off_x = off_x * (1.0 / self._org_scale_x)
        off_y = off_y * (1.0 / self._org_scale_y)

        # Add data index at (_ctr_x, _ctr_y) to offset
        data_x = self._org_x + off_x
        data_y = self._org_y + off_y
        if center:
            data_x -= 0.5
            data_y -= 0.5

        self.logger.debug("data_x=%d data_y=%d" % (data_x, data_y))
        return (data_x, data_y)

    def get_canvas_xy(self, data_x, data_y, center=True):
        """Returns the closest x, y coordinates in the graphics space to the
        x, y coordinates in the data.  data_x and data_y can be integer or
        floating point values.

        If center==True, then the coordinates are mapped such that the
        integer pixel begins in the center of the square when the image
        is zoomed in past 1X.  This is the specification of the FITS image
        standard, that the pixel is centered on the integer row/column.
        """
        if center:
            data_x += 0.5
            data_y += 0.5
        # subtract data indexes at center reference pixel
        off_x = data_x - self._org_x
        off_y = data_y - self._org_y

        # scale according to current settings
        off_x *= self._org_scale_x
        off_y *= self._org_scale_y

        win_x, win_y = self.offset2canvas(off_x, off_y)
        self.logger.debug("win_x=%d win_y=%d" % (win_x, win_y))

        return (win_x, win_y)
        
    def offset2canvas(self, off_x, off_y, asint=True):

        if self.t_['flip_x']:
            off_x = - off_x
        if self.t_['flip_y']:
            off_y = - off_y
        if self.t_['swap_xy']:
            off_x, off_y = off_y, off_x

        if self.t_['rot_deg'] != 0:
            off_x, off_y = self._rotate_pt(off_x, off_y, self.t_['rot_deg'])

        # add center pixel to convert from X/Y coordinate space to
        # canvas graphics space
        win_x = off_x + self._ctr_x
        win_y = self._ctr_y - off_y

        # round to pixel units
        if asint:
            win_x = int(round(win_x))
            win_y = int(round(win_y))
        
        return (win_x, win_y)

    def canvas2offset(self, win_x, win_y):
        # make relative to center pixel to convert from canvas
        # graphics space to standard X/Y coordinate space
        off_x = win_x - self._ctr_x
        off_y = self._ctr_y - win_y

        if self.t_['rot_deg'] != 0:
            off_x, off_y = self._rotate_pt(off_x, off_y, -self.t_['rot_deg'])

        if self.t_['swap_xy']:
            off_x, off_y = off_y, off_x
        if self.t_['flip_y']:
            off_y = - off_y
        if self.t_['flip_x']:
            off_x = - off_x

        return (off_x, off_y)

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
        return self.image.get_data_xy(data_x, data_y)

    def get_pixels_on_line(self, x1, y1, x2, y2, getvalues=True):
        """Uses Bresenham's line algorithm to enumerate the pixels along
        a line.
        (see http://en.wikipedia.org/wiki/Bresenham%27s_line_algorithm)
        """
        dx = abs(x2 - x1)
        dy = abs(y2 - y1) 
        if x1 < x2:
            sx = 1
        else:
            sx = -1
        if y1 < y2:
            sy = 1
        else:
            sy = -1
        err = dx - dy

        res = []
        x, y = x1, y1
        while True:
            if getvalues:
                val = self.get_data(x, y)
                res.append(val)
            else:
                res.append((x, y))
            if (x == x2) and (y == y2):
                break
            e2 = 2 * err
            if e2 > -dy:
                err = err - dy
                x += sx
            if e2 <  dx: 
                err = err + dx
                y += sy

        return res

    def get_pixel_distance(self, x1, y1, x2, y2):
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        dist = math.sqrt(dx*dx + dy*dy)
        dist = round(dist)
        return dist
    
    def apply_visuals(self, data, vmin, vmax):
        # apply other transforms
        if self._invertY:
            # Flip Y for natural natural Y-axis inversion between FITS coords
            # and screen coords
            data = numpy.flipud(data)

        # Apply cut levels
        newdata = self.autocuts.cut_levels(data, self.t_['locut'],
                                           self.t_['hicut'],
                                           vmin=vmin, vmax=vmax)
        return newdata

        
    def scale_to(self, scale_x, scale_y, no_reset=False, redraw=True):
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
                    zoom_algorithm=zoomalg)

        self._scale_to(scale_x, scale_y, no_reset=no_reset, redraw=redraw)

    def _scale_to(self, scale_x, scale_y, no_reset=False, redraw=True):
        # Check scale limits
        maxscale = max(scale_x, scale_y)
        if (maxscale > self.t_['scale_max']):
            self.logger.error("Scale (%.2f) exceeds max scale limit (%.2f)" % (
                maxscale, self.t_['scale_max']))
            # TODO: popup? exception?
            return
        
        minscale = min(scale_x, scale_y)
        if (minscale < self.t_['scale_min']):
            self.logger.error("Scale (%.2f) exceeds min scale limit (%.2f)" % (
                minscale, self.t_['scale_min']))
            # TODO: popup? exception?
            return
        
        # Sanity check on the scale vs. window size
        try:
            win_wd, win_ht = self.get_window_size()
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

        self._scale_x = scale_x
        self._scale_y = scale_y

        # If user specified override for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_['autozoom'] == 'override'):
            value = 'off'
            self.t_['autozoom'] = value
            self.make_callback('autozoom', value)

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
            zoomlevel = maxscale
            if zoomlevel < 1.0:
                zoomlevel = - (1.0 / zoomlevel)
            #print "calc zoomlevel=%f" % (zoomlevel)
            
        self.t_.set(zoomlevel=zoomlevel)

        self.make_callback('zoom-set', zoomlevel, scale_x, scale_y)
        if redraw:
            self.redraw()

    def get_scale(self):
        #scalefactor = max(self._org_scale_x, self._org_scale_y)
        scalefactor = max(self._scale_x, self._scale_y)
        return scalefactor

    def get_scale_xy(self):
        #return (self._org_scale_x, self._org_scale_y)
        return (self._scale_x, self._scale_y)

    def get_scale_base_xy(self):
        return (self.t_['scale_x_base'], self.t_['scale_y_base'])
        
    def set_scale_base_xy(self, scale_x_base, scale_y_base,
                          redraw=True):
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

    def zoom_to(self, zoomlevel, no_reset=False, redraw=True):
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

        #print "scale_x=%f scale_y=%f zoom=%f" % (
        #    scale_x, scale_y, zoomlevel)
        self._scale_to(scale_x, scale_y,
                       no_reset=no_reset, redraw=redraw)

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
                
    def zoom_fit(self, no_reset=False, redraw=True):
        try:
            wwidth, wheight = self.get_window_size()
            self.logger.debug("Window size is %dx%d" % (wwidth, wheight))
            if self.t_['swap_xy']:
                wwidth, wheight = wheight, wwidth
        except:
            return

        # Calculate optimum zoom level to still fit the window size
        width, height = self.get_data_size()
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
        
        self._scale_to(scale_x, scale_y,
                      no_reset=no_reset, redraw=redraw)

    def get_zoom(self):
        return self.t_['zoomlevel']
        
    def get_zoomrate(self):
        return self.t_['zoom_rate']
        
    def set_zoomrate(self, zoomrate, redraw=True):
        self.t_.set(zoom_rate=zoomrate)
        
    def get_zoom_algorithm(self):
        return self.t_['zoom_algorithm']
        
    def set_zoom_algorithm(self, name, redraw=True):
        name = name.lower()
        assert name in ('step', 'rate'), \
              FitsImageError("Alg '%s' must be one of: step, rate" % name)
        self.t_.set(zoom_algorithm=name)
        
    def zoomalg_change_cb(self, setting, value):
        self.zoom_to(self.t_['zoomlevel'])
        
    def set_name(self, name):
        self.name = name
        
    def get_scale_limits(self):
        return (self.t_['scale_min'], self.t_['scale_max'])

    def set_scale_limits(self, scale_min, scale_max):
        self.t_.set(scale_min=scale_min, scale_max=scale_max)
        
    def enable_autozoom(self, option):
        option = option.lower()
        assert(option in self.autozoom_options), \
                      FitsImageError("Bad autozoom option '%s': must be one of %s" % (
            str(self.autozoom_options)))
        self.t_.set(autozoom=option)
        
        self.make_callback('autozoom', option)
        
    def get_autozoom_options(self):
        return self.autozoom_options
    
    def set_pan(self, pan_x, pan_y, redraw=True):
        self._pan_x = pan_x
        self._pan_y = pan_y
        self.logger.info("pan set to %.2f,%.2f" % (
            pan_x, pan_y))
        self.make_callback('pan-set')
        if redraw:
            self.redraw(whence=0)

    def get_pan(self):
        return (self._pan_x, self._pan_y)
    
    def panset_xy(self, data_x, data_y, redraw=True):
        # To center on the pixel
        pan_x, pan_y = data_x + 0.5, data_y + 0.5
        
        self.set_pan(pan_x, pan_y, redraw=redraw)

    def panset_pct(self, pct_x, pct_y, redraw=True):
        width, height = self.get_data_size()
        data_x, data_y = width * pct_x, height * pct_y
        self.panset_xy(data_x, data_y, redraw=redraw)

    def set_pan_reverse(self, tf):
        self.t_.set(reverse_pan=tf)
        
    def center_image(self, redraw=True):
        width, height = self.get_data_size()
        data_x, data_y = float(width) / 2.0, float(height) / 2.0
        self.panset_xy(data_x, data_y)
        if redraw:
            self.redraw(whence=0)
        
    def get_pan_reverse(self):
        return self.t_['reverse_pan']
        
    def get_transforms(self):
        return (self.t_['flip_x'], self.t_['flip_y'], self.t_['swap_xy'])

    def set_autocut_params(self, method, pct=None, numbins=None):
        self.logger.debug("Setting autocut params method=%s pct=%s" % (
            method, str(pct)))
        self.t_.set(autocut_method=method)
        if pct:
            self.t_.set(autocut_hist_pct=pct)
        if numbins:
            self.t_.set(autocut_bins=numbins)

    def get_autocut_methods(self):
        return self.autocuts.get_algorithms()
    
    def get_cut_levels(self):
        return (self.t_['locut'], self.t_['hicut'])
    
    def cut_levels(self, loval, hival, no_reset=False, redraw=True):
        self.t_.set(locut=loval, hicut=hival)

        # If user specified override for auto levels, then turn off
        # auto levels now that they have set the levels manually
        if (not no_reset) and (self.t_['autocuts'] == 'override'):
            value = 'off'
            self.t_.set(autocuts=value)
            self.make_callback('autocuts', value)

        # Save cut levels with this image embedded profile
        self.save_profile(cutlo=loval, cuthi=hival)
            
    def auto_levels(self, method=None, pct=None,
                    numbins=None, redraw=True):
        if method == None:
            method = self.t_['autocut_method']
        if pct == None:
            pct = self.t_['autocut_hist_pct']
        if numbins == None:
            numbins = self.t_['autocut_bins']
        image = self.get_image()
        loval, hival = self.autocuts.calc_cut_levels(image, method=method,
                                                     pct=pct, numbins=numbins)
        # this will invoke cut_levels_cb()
        self.t_.set(locut=loval, hicut=hival)

    def auto_levels_cb(self, setting, value):
        if self.t_['autocuts'] != 'off':
            self.auto_levels()

    def cut_levels_cb(self, setting, value):
        loval = self.t_['locut']
        hival = self.t_['hicut']

        self.redraw(whence=1)
        self.make_callback('cut-set', loval, hival)

    def enable_autocuts(self, option):
        option = option.lower()
        assert(option in self.autocuts_options), \
                      FitsImageError("Bad autocuts option '%s': must be one of %s" % (
            str(self.autocuts_options)))
        self.t_.set(autocuts=option)
        
        self.make_callback('autocuts', option)

    def get_autocuts_options(self):
        return self.autocuts_options

    def transform(self, flip_x, flip_y, swap_xy, redraw=True):
        self.logger.debug("flip_x=%s flip_y=%s swap_xy=%s" % (
            flip_x, flip_y, swap_xy))
        self.t_.set(flip_x=flip_x, flip_y=flip_y, swap_xy=swap_xy)

    def transform_cb(self, setting, value):
        self.make_callback('transform')
        self.redraw(whence=0)

    def copy_attributes(self, dst_fi, attrlist, redraw=False):
        """Copy interesting attributes of our configuration to another
        instance of a FitsImage."""

        if 'transforms' in attrlist:
            dst_fi.transform(self.t_['flip_x'], self.t_['flip_y'],
                             self.t_['swap_xy'],
                             redraw=False)

        if 'rotation' in attrlist:
            dst_fi.rotate(self.t_['rot_deg'], redraw=False)

        if 'cutlevels' in attrlist:
            dst_fi.cut_levels(self.t_['locut'], self.t_['hicut'],
                              redraw=False)

        if 'rgbmap' in attrlist:
            #dst_fi.set_rgbmap(self.rgbmap, redraw=False)
            dst_fi.rgbmap = self.rgbmap

        if 'zoom' in attrlist:
            dst_fi.zoom_to(self.t_['zoomlevel'], redraw=False)

        if 'pan' in attrlist:
            dst_fi.set_pan(self._pan_x, self._pan_y, redraw=False)

        if redraw:
            dst_fi.redraw(whence=0)

    def set_makebg(self, tf):
        self.t_makebg = tf

    def get_rotation(self):
        return self.t_['rot_deg']

    def rotate(self, deg, redraw=True):
        self.t_.set(rot_deg=deg)

    def rotation_change_cb(self, setting, value):
        self.make_callback('rotate', value)
        self.redraw(whence=0)
        
    def get_center(self):
        return (self._ctr_x, self._ctr_y)
        
    def get_rotation_info(self):
        return (self._ctr_x, self._ctr_y, self.t_['rot_deg'])
        
    def _rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        a = x - xoff
        b = y - yoff
        cos_t = math.cos(math.radians(theta))
        sin_t = math.sin(math.radians(theta))
        ap = (a * cos_t) - (b * sin_t)
        bp = (a * sin_t) + (b * cos_t)
        return (ap + xoff, bp + yoff)

    def enable_auto_orient(self, tf):
        self.t_.set(auto_orient=tf)
        
    def auto_orient(self, redraw=True):
        """Set the orientation for the image to a reasonable default.
        """
        invertY = not isinstance(self.image, AstroImage.AstroImage)

        # Check for various things to set based on metadata
        header = self.image.get_header()
        if header:
            # Auto-orientation
            orient = header.get('Orientation', None)
            if orient:
                try:
                    orient = int(orient)
                    self.logger.info("setting orientation from metadata [%d]" % (
                        orient))
                    flip_x, flip_y, swap_xy = self.orientMap[orient]

                    self.transform(flip_x, flip_y, swap_xy, redraw=redraw)
                    invertY = False

                except Exception, e:
                    # problems figuring out orientation--let it be
                    pass

        if invertY:
            flip_x, flip_y, swap_xy = self.get_transforms()
            #flip_y = not flip_y
            flip_y = True
            self.transform(flip_x, flip_y, swap_xy, redraw=redraw)

#END
