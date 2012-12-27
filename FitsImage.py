#
# FitsImage.py -- abstract classes for the display of FITS files
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Thu Dec 27 11:53:05 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
import math
import logging
import time

import Callback
import Settings
import RGBMap
import AstroImage
import AutoCuts
import cmap, imap


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

    def __init__(self, logger=None, rgbmap=None):
        Callback.Callbacks.__init__(self)

        if logger != None:
            self.logger = logger
        else:
            self.logger = logging.Logger('FitsImageBase')

        if rgbmap:
            self.rgbmap = rgbmap
            cm = rgbmap.get_cmap()
        else:
            self.rgbmap = RGBMap.RGBMapper()
            # Set default color map and intensity map
            cm = cmap.get_cmap('real')
            self.rgbmap.set_cmap(cm)
            im = imap.get_imap('ramp')
            self.rgbmap.set_imap(im)
        self.rgbmap.add_callback('changed', self.rgbmap_cb)

        # Object that calculates auto cut levels
        self.autocuts = AutoCuts.AutoCuts(self.logger)
        
        # actual image width and height (see set_data())
        self.image = AstroImage.AstroImage(numpy.zeros((1, 1)),
                                           logger=self.logger)
        # for debugging
        self.name = str(self)
        
        # for cut levels
        self.autolevels_options = ('on', 'override', 'off')
        self.t_autolevels = 'override'
        self.t_locut = 0.0
        self.t_hicut = 0.0
        self.t_autocut_method = 'histogram'
        #self.t_autocut_method = 'stddev'
        self.t_autocut_hist_pct = AutoCuts.default_autolevels_hist_pct
        self.t_autocut_bins = AutoCuts.default_autolevels_bins
        self.t_autocut_usecrop = True
        self.t_autocut_crop_radius = 512
        self.t_use_embedded_profile = True
        self.t_reversepan = False

        # for zoom levels
        self.autoscale_options = ('on', 'override', 'off')
        self.t_autoscale = 'on'
        self.t_zoomlevel = 1.0
        # max/min for zooming
        self.t_zoom_max = 20.0
        self.t_zoom_min = -20.0
        # max/min for autozooming
        self.t_zoom_maxauto = 3.0
        self.t_zoom_minauto = -20.0

        # for panning
        self.canpan = True
        self.t_makebg = False
        self.auto_recenter = False
        
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
        # pan position indexes (in data coords)
        self._pan_x = 1.0
        self._pan_y = 1.0
        
        # for transforms
        self._swapXY = False
        self._flipX = False
        self._flipY = False
        self._invertY = True

        # Origin in the data array of what is currently displayed (LL, UR)
        self._org_x1 = 0
        self._org_y1 = 0
        self._org_x2 = 0
        self._org_y2 = 0
        # offsets in the screen image for drawing (in screen coords)
        self._dst_x = 0
        self._dst_y = 0
        # offsets in the screen image (in data coords)
        self._off_x = 0
        self._off_y = 0

        # desired scale factors
        self._scale_x = 1.0
        self._scale_y = 1.0
        # actual scale factors produced from desired ones
        self._org_scale_x = 0
        self._org_scale_y = 0
        # desired rotation angle
        self._rot_deg = 0.0

        self._cutout = None
        self._rotimg = None
        self._prergb = None
        self._rgbarr = None

        # For callbacks
        for name in ('cut-set', 'zoom-set', 'pan-set', 'transform',
                     'rotate', 'image-set', 'data-set', 'configure',
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

    # TODO: deprecate these two?
    def set_cmap(self, cm, redraw=True):
        self.rgbmap.set_cmap(cm, callback=redraw)

    def set_imap(self, im, redraw=True):
        self.rgbmap.set_imap(im, callback=redraw)

    def shift_cmap(self, pct):
        if pct > 0.0:
            self.rgbmap.rshift(pct)
        else:
            self.rgbmap.lshift(math.fabs(pct))

    def rgbmap_cb(self, rgbmap):
        self.logger.info("RGB map has changed.")
        self.redraw(whence=1)
        
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
        #self.first_cuts(redraw=False)
        self.image = image
        profile = self.image.get('profile', None)
        if (profile != None) and (self.t_use_embedded_profile):
            self.apply_profile(profile, redraw=False)

        self._invertY = isinstance(image, AstroImage.AstroImage)
            
        # Set pan position to middle of the image initially
        width, height = image.get_size()
        self._pan_x = float(width) / 2.0
        self._pan_y = float(height) / 2.0
        
        if self.t_autoscale != 'off':
            self.zoom_fit(redraw=False, no_reset=True)
        if self.t_autolevels != 'off':
            self.auto_levels(redraw=False)

        if redraw:
            self.redraw()

        data = image.get_data()
        self.make_callback('data-set', data)
        self.make_callback('image-set', image)

    def set_data(self, data, metadata=None, redraw=True):
        dims = data.shape
        ## assert (len(dims) == 2), \
        ##        FitsImageError("Only 2D images are supported!")
        image = AstroImage.AstroImage(data, metadata=metadata,
                                      logger=self.logger)
        self.set_image(image, redraw=redraw)

    def clear(self, redraw=True):
        self.set_data(numpy.zeros((1, 1)), redraw=redraw)
        
    def save_profile(self, category, **params):
        if self.image == None:
            return
        profile = self.image.get('profile', None)
        if (profile == None):
            # If image has no profile then create one
            profile = Settings.Settings()
            self.image.set(profile=profile) 

        self.logger.debug("saving to image profile: cat='%s' params=%s" % (
                category, str(params)))
        section = profile.createCategory(category)
        section.update(params)
            
    def apply_profile(self, profile, redraw=False):
        # If there is image metadata associated that has cut levels
        # then use those values if t_use_saved_cuts == True
        ## if (self.t_use_saved_cuts and (self.image != None) and
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
        self.redraw_data(whence=whence)
        
        # finally update the window drawable from the offscreen surface
        self.update_image()

    def redraw_data(self, whence=0):
        rgbobj = self.get_rgb_object(whence=whence)
        self.render_image(rgbobj, self._dst_x, self._dst_y)
        if whence <= 0:
            self.make_callback('pan-set')

    def render_image(self, rgbobj, dst_x, dst_y):
        self.logger.warn("Subclass needs to override this method!")
        
    def update_image(self):
        self.logger.warn("Subclass should override this abstract method!")
    
    def get_datarect(self):
        x1, y1, x2, y2 = self._org_x1, self._org_y1, self._org_x2, self._org_y2
        return (x1, y1, x2, y2)

    def get_canpan(self):
        return self.canpan
    
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
                              self._rot_deg, self.t_makebg,
                              self._imgwin_wd, self._imgwin_ht)
            
        time_split2 = time.time()
        if (whence <= 1) or (self._prergb == None):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = self.rgbmap.get_hash_size() - 1
            newdata = self.apply_visuals(self._rotimg, 0, vmax)

            # Convert data to an index array
            #self._prergb = newdata.astype('uint')
            self._prergb = newdata

        time_split3 = time.time()
        if (whence <= 2) or (self._rgbarr == None):
            idx = self._prergb.astype('uint32')
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
        if not self.t_makebg and (self._rot_deg == 0.0):
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


    def apply_transforms(self, data, rot_deg, make_bg, win_wd, win_ht):
        start_time = time.time()

        wd, ht = self.get_dims(data)
        xoff, yoff = self._org_xoff, self._org_yoff

        # Do transforms as necessary
        if self._flipY:
            data = numpy.flipud(data)
            yoff = ht - yoff

        if self._flipX:
            data = numpy.fliplr(data)
            xoff = wd - xoff

        if self._swapXY:
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

        if self._flipX:
            off_x = - off_x
        if self._flipY:
            off_y = - off_y
        if self._swapXY:
            off_x, off_y = off_y, off_x

        if self._rot_deg != 0:
            off_x, off_y = self._rotate_pt(off_x, off_y, self._rot_deg)

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

        if self._rot_deg != 0:
            off_x, off_y = self._rotate_pt(off_x, off_y, -self._rot_deg)

        if self._swapXY:
            off_x, off_y = off_y, off_x
        if self._flipY:
            off_y = - off_y
        if self._flipX:
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
        newdata = self._cut_levels(data, self.t_locut, self.t_hicut,
                                   vmin=vmin, vmax=vmax)
        return newdata

        
    def scale_to(self, scale_x, scale_y, no_reset=False, redraw=True):
        self._scale_x = scale_x
        self._scale_y = scale_y

        scalefactor = max(scale_x, scale_y)
        
        # If user specified override for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_autoscale == 'override'):
            value = 'off'
            self.t_autoscale = value
            self.make_callback('autozoom', value)

        zoomlevel = scalefactor
        if zoomlevel < 1.0:
            zoomlevel = - (1.0 / zoomlevel)
        self.t_zoomlevel = zoomlevel

        self.make_callback('zoom-set', zoomlevel, scalefactor)
        if redraw:
            self.redraw()

    def zoom_to(self, zoomlevel, no_reset=False, redraw=True):
        if zoomlevel > self.t_zoom_max:
            self.logger.debug("max zoom reached")
            return
        if zoomlevel < self.t_zoom_min:
            self.logger.debug("min zoom reached")
            return

        if zoomlevel >= 1.0:
            scalefactor = zoomlevel
        elif zoomlevel < -1.0:
            scalefactor = 1.0 / float(abs(zoomlevel))
        else:
            # wierd condition?--reset to 1:1
            scalefactor = 1.0

        self.scale_to(scalefactor, scalefactor,
                      no_reset=no_reset, redraw=redraw)

    def zoom_in(self):
        zl = int(self.t_zoomlevel)
        if (zl >= 1) or (zl <= -3):
            self.zoom_to(zl + 1)
        else:
            self.zoom_to(1)
        
    def zoom_out(self):
        zl = int(self.t_zoomlevel)
        if zl == 1:
            self.zoom_to(-2)
        elif (zl >= 2) or (zl <= -2):
            self.zoom_to(zl - 1)
        else:
            self.zoom_to(1)

    def zoom_fit(self, no_reset=False, redraw=True):
        try:
            wwidth, wheight = self.get_window_size()
        except:
            return
        self.logger.debug("Window size is %dx%d" % (wwidth, wheight))

        # Calculate optimum zoom level to still fit the window size
        width, height = self.get_data_size()
        zoomx = float(wwidth) / float(width)
        zoomy = float(wheight) / float(height)
        zoom = min(zoomx, zoomy)
        if zoom < 1.0:
            zoomlevel = - max(2, int(math.ceil(1.0/zoom)))
        else:
            zoomlevel = max(1, int(math.floor(zoom)))

        # Constrain autoscaling to limits set
        self.logger.debug("calculated zoomlevel is %d (min=%d, max=%d)" % (
            zoomlevel, self.t_zoom_minauto, self.t_zoom_maxauto))
        zoomlevel = min(zoomlevel, self.t_zoom_maxauto)
        zoomlevel = max(zoomlevel, self.t_zoom_minauto)
        self.logger.debug("zoomx=%.2f zoomy=%.2f zoom=%.2f zoomlevel=%d" % (
            zoomx, zoomy, zoom, zoomlevel))

        self.zoom_to(zoomlevel, no_reset=no_reset, redraw=redraw)

    def is_max_zoom(self):
        return self.t_zoomlevel >= self.t_zoom_max
        
    def is_min_zoom(self):
        return self.t_zoomlevel <= self.t_zoom_min

    def get_zoom(self):
        return self.t_zoomlevel
        
    def get_scale(self):
        scalefactor = min(self._scale_x, self._scale_y)
        return scalefactor

    def get_scale_xy(self):
        return (self._scale_x, self._scale_y)

    def get_scale_text(self):
        scalefactor = self.get_scale()
        if scalefactor >= 1.0:
            text = '%dx' % (int(scalefactor))
        else:
            text = '1/%dx' % (int(1.0/scalefactor))
        return text

    def set_name(self, name):
        self.name = name
        
    def get_zoom_limits(self):
        return (self.t_zoom_min, self.t_zoom_max)

    def set_zoom_limits(self, zmin, zmax):
        self.t_zoom_min = zmin
        self.t_zoom_max = zmax
        
    def set_autoscale_limits(self, zmin, zmax):
        self.t_zoom_minauto = zmin
        self.t_zoom_maxauto = zmax

    def get_autoscale_limits(self):
        return (self.t_zoom_minauto, self.t_zoom_maxauto)

    def enable_autoscale(self, option):
        option = option.lower()
        assert(option in self.autoscale_options), \
                      FitsImageError("Bad autoscale option '%s': must be one of %s" % (
            str(self.autoscale_options)))
        self.t_autoscale = option
        
        self.make_callback('autozoom', option)
        
    def get_autoscale_options(self):
        return self.autoscale_options
    
    def set_pan(self, data_x, data_y, redraw=True):
        self._pan_x = data_x
        self._pan_y = data_y
        self.logger.info("pan set to %.2f,%.2f" % (
            data_x, data_y))
        if redraw:
            self.redraw(whence=0)

    def get_pan(self):
        return (self._pan_x, self._pan_y)
    
    def panset_xy(self, data_x, data_y, redraw=True):
        self.set_pan(data_x, data_y, redraw=redraw)

    def panset_pct(self, pct_x, pct_y, redraw=True):
        width, height = self.get_data_size()
        data_x, data_y = width * pct_x, height * pct_y
        self.set_pan(data_x, data_y, redraw=redraw)

    def set_pan_reverse(self, tf):
        self.t_reversepan = tf
        
    def center_image(self, redraw=True):
        width, height = self.get_data_size()
        data_x, data_y = float(width) / 2.0, float(height) / 2.0
        self.set_pan(data_x, data_y)
        if redraw:
            self.redraw(whence=0)
        
    def get_pan_reverse(self):
        return self.t_reversepan
        
    def get_transforms(self):
        return (self._flipX, self._flipY, self._swapXY)

    def set_autolevel_params(self, method, pct=None, numbins=None,
                             usecrop=None, cropradius=None):
        self.logger.debug("Setting autolevel params method=%s pct=%.4f" % (
            method, pct))
        self.t_autocut_method = method
        if pct:
            self.t_autocut_hist_pct = pct
        if numbins:
            self.t_autocut_bins = numbins
        if usecrop != None:
            self.t_autocut_usecrop = usecrop
        if cropradius:
            self.t_autocut_crop_radius = cropradius

    def get_autocut_methods(self):
        return self.autocuts.get_algorithms()
    
    def get_cut_levels(self):
        return (self.t_locut, self.t_hicut)
    
    def _cut_levels(self, data, loval, hival, vmin=0.0, vmax=255.0):
        self.logger.debug("loval=%.2f hival=%.2f" % (loval, hival))
        delta = hival - loval
        if delta == 0:
            f = (data - loval).clip(0.0, 1.0)
            # threshold
            f[numpy.nonzero(f)] = 1.0
        else:
            data = data.clip(loval, hival)
            f = ((data - loval) / delta)
        data = f.clip(0.0, 1.0) * vmax
        return data

    def cut_levels(self, loval, hival, no_reset=False, redraw=True):
        self.t_locut = loval
        self.t_hicut = hival

        # If user specified override for auto levels, then turn off
        # auto levels now that they have set the levels manually
        if (not no_reset) and (self.t_autolevels == 'override'):
            value = 'off'
            self.t_autolevels = value
            self.make_callback('autocuts', value)

        # Save cut levels with this image embedded profile
        self.save_profile('cut_levels', cutlo=loval, cuthi=hival)
            
        self.make_callback('cut-set', self.t_locut, self.t_hicut)
        if redraw:
            self.redraw(whence=1)

    def auto_levels(self, method=None, pct=None,
                    numbins=None, redraw=True):
        loval, hival = self.autocuts.calc_cut_levels(self, method=method,
                                                     pct=pct, numbins=numbins)
        self.t_locut = loval
        self.t_hicut = hival

        # Save cut levels with this image embedded profile
        # UPDATE: only manual cut_levels saves to profile
        #self.save_profile('cut_levels', cutlo=loval, cuthi=hival)
            
        self.make_callback('cut-set', self.t_locut, self.t_hicut)
        if redraw:
            self.redraw(whence=1)

    def enable_autolevels(self, option):
        option = option.lower()
        assert(option in self.autolevels_options), \
                      FitsImageError("Bad autolevels option '%s': must be one of %s" % (
            str(self.autolevels_options)))
        self.t_autolevels = option
        
        self.make_callback('autocuts', option)

    def get_autolevels_options(self):
        return self.autolevels_options

    def transform(self, flipx, flipy, swapxy, redraw=True):
        self._flipX = flipx
        self._flipY = flipy
        self._swapXY = swapxy
        self.logger.debug("flipx=%s flipy=%s swapXY=%s" % (
            self._flipX, self._flipY, self._swapXY))

        self.make_callback('transform')
        if redraw:
            self.redraw(whence=0)

    def copy_attributes(self, dst_fi, attrlist, redraw=False):
        """Copy interesting attributes of our configuration to another
        instance of a FitsImage."""

        dst_fi.set_invertY(self._invertY)
        
        if 'transforms' in attrlist:
            dst_fi.transform(self._flipX, self._flipY, self._swapXY,
                             redraw=False)

        if 'rotation' in attrlist:
            # NOTE: rotation is handled in a subclass
            dst_fi.rotate(self._rot_deg, redraw=False)

        if 'cutlevels' in attrlist:
            dst_fi.cut_levels(self.t_locut, self.t_hicut,
                              redraw=False)

        if 'rgbmap' in attrlist:
            #dst_fi.set_rgbmap(self.rgbmap, redraw=False)
            dst_fi.rgbmap = self.rgbmap

        if 'zoom' in attrlist:
            dst_fi.zoom_to(self.t_zoomlevel, redraw=False)

        if 'pan' in attrlist:
            dst_fi.set_pan(self._pan_x, self._pan_y, redraw=False)

        if redraw:
            dst_fi.redraw(whence=0)

    def set_makebg(self, tf):
        self.t_makebg = tf

    def set_invertY(self, tf):
        self._invertY = tf

    def get_rotation(self):
        return self._rot_deg

    def rotate(self, deg, redraw=True):
        self._rot_deg = deg
        self.make_callback('rotate', deg)
        if redraw:
            self.redraw(whence=0)

    def get_center(self):
        return (self._ctr_x, self._ctr_y)
        
    def get_rotation_info(self):
        return (self._ctr_x, self._ctr_y, self._rot_deg)
        
    def _rotate_pt(self, x, y, theta, xoff=0, yoff=0):
        a = x - xoff
        b = y - yoff
        cos_t = math.cos(math.radians(theta))
        sin_t = math.sin(math.radians(theta))
        ap = (a * cos_t) - (b * sin_t)
        bp = (a * sin_t) + (b * cos_t)
        return (ap + xoff, bp + yoff)

#END
