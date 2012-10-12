#
# FitsImage.py -- abstract classes for the display of FITS files
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Tue Oct  9 22:59:13 HST 2012
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
        self.image = AstroImage.AstroImage(numpy.zeros((1, 1)))
        self.data = self.image.get_data()
        self.width  = 1
        self.height = 1
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
        self.t_panx = 0.5
        self.t_pany = 0.5
        self.canpan = False
        self.auto_recenter = False

        # PRIVATE IMPLEMENTATION STATE
        
        # image window width and height (see set_window_dimensions())
        self._imgwin_wd = 1
        self._imgwin_ht = 1
        self._imgwin_set = False
        
        # for transforms
        self._swapXY = False
        self._flipX = False
        self._flipY = False

        self._pxwd = 0
        self._pxht = 0
        self._src_x = 0
        self._src_y = 0
        # Origin in the data array of what is currently displayed (LL, UR)
        self._org_x1 = 0
        self._org_y1 = 0
        self._org_x2 = 0
        self._org_y2 = 0
        self._org_fac = 1
        self._org_wd = 0
        self._org_ht = 0
        # offsets in the screen image (in screen coords)
        self._dst_x = 0
        self._dst_y = 0
        # offsets in the screen image (in data coords)
        self._off_x = 0
        self._off_y = 0

        self._scalefactor = 1.0
        self._cutout = None
        self._prergb = None
        self._rgbarr = None

        # For callbacks
        for name in ('cut-set', 'zoom-set', 'pan-set', 'transform',
                     'image-set', 'data-set', 'configure',
                     'autocuts', 'autozoom'):
            self.enable_callback(name)

        
    def set_window_size(self, width, height, redraw=True):
        """This is called by the subclass when the actual dimensions of the
        window are known."""
        self._imgwin_wd = width
        self._imgwin_ht = height
        self._imgwin_set = True
        self.logger.debug("image resized to %dx%d" % (width, height))

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
        return self.image.get_data_size()

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

        # NOTE [A]
        self.apply_data_transforms1()

        if self.t_autoscale != 'off':
            self.zoom_fit(redraw=False, no_reset=True)
        if self.t_autolevels != 'off':
            self.auto_levels(redraw=False)

        if redraw:
            self.redraw()

        data = image.get_data()
        self.make_callback('data-set', data)
        self.make_callback('image-set', image)

    def set_data(self, data, image=None, redraw=True):
        dims = data.shape
        ## assert (len(dims) == 2), \
        ##        FitsImageError("Only 2D images are supported!")
        if image == None:
            image = AstroImage.AstroImage(data)
        self.set_image(image)
        

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

    def update_image(self):
        raise FitsImageError("Override this abstract method!")
    
    def redraw_data(self, whence=0):
        rgbobj = self.get_rgb_object(whence=whence)
        self.render_image(rgbobj, self._dst_x, self._dst_y)
        if whence <= 0:
            self.make_callback('pan-set')

    def _calc_fit(self):
        width, height = self.width, self.height
            
        # calculate width and height in pixels at desired zoom level
        pxwd = int(width * self._scalefactor)
        pxht = int(height * self._scalefactor)

        # calculate difference from actual window dimensions
        diff_wd = self._imgwin_wd - pxwd
        diff_ht = self._imgwin_ht - pxht

        self.canpan = (diff_wd < 0) or (diff_ht < 0)
        # If desired, recenter panning offsets when we display whole image
        if (not self.canpan) and self.auto_recenter:
            self.t_panx = 0.5
            self.t_pany = 0.5

        # calculate coordinates into zoom image
        if diff_wd > 0:
            # image window is wider than the zoom image
            src_x = 0
            dst_x = diff_wd // 2
            dst_wd = pxwd
        elif diff_wd < 0:
            # image window is narrower than the zoom image
            dst_x = 0
            dst_wd = self._imgwin_wd
            panx = ( int(round(self.t_panx * pxwd)) -
                     int(round(0.5 * self._imgwin_wd)) )
            panx = max(0, panx)
            panx = min(panx, pxwd - self._imgwin_wd)
            #pxwd = min(abs(diff_wd), panx)
            #src_x = abs(diff_wd) // 2
            src_x = panx
        else:
            # image window is same width as the zoom image
            dst_x = src_x = 0
            dst_wd = pxwd

        if diff_ht > 0:
            # image window is taller than the zoom image
            src_y = 0
            dst_y = diff_ht // 2
            dst_ht = pxht
        elif diff_ht < 0:
            # image window is shorter than the zoom image
            dst_y = 0
            dst_ht = self._imgwin_ht
            pany = ( int(round(self.t_pany * pxht)) -
                     int(round(0.5 * self._imgwin_ht)) )
            pany = max(0, pany)
            pany = min(pany, pxht - self._imgwin_ht)
            #src_y = abs(diff_ht) // 2
            src_y = pany
        else:
            # image window is same height as the zoom image
            dst_y = src_y = 0
            dst_ht = pxht

        # pxwd, pxht: calculated width and height of a full (unrealized)
        # image zoomed (scaled) to the desired setting.  This could be
        # smaller or larger than the actual window.
        self._pxwd = pxwd
        self._pxht = pxht
        # src_x, src_y: calculated indexes into the full scaled image.
        # Depends upon zoom level and panning position.
        self._src_x = src_x
        self._src_y = src_y
        # dst_x, dst_y: actual offsets into the graphics window
        # (in the graphics coordinate space) where to begin writing
        # the image.  Will be 0 unless we are zoomed out far enough to
        # see the borders of the image.
        self._dst_x = dst_x
        self._dst_y = dst_y
        # dst_wd, dst_ht: the size of the image to create to put in the
        # window.  Will be the dimensions of the window or smaller.
        self.dst_wd = dst_wd
        self.dst_ht = dst_ht
        self.logger.debug("src_x=%d src_y=%d dst_x=%d dst_y=%d dst_wd=%d dst_ht=%d" % (
            src_x, src_y, dst_x, dst_y, dst_wd, dst_ht))

        # Record the boundaries (origin) of the view into the real data
        x1 = int(round((float(src_x) / float(pxwd)) * width))
        y1 = int(round((float(src_y) / float(pxht)) * height))
        x2 = int(round((float(src_x+self._imgwin_wd) / float(pxwd)) * width))
        x2 = min(x2, width-1)
        y2 = int(round((float(src_y+self._imgwin_ht) / float(pxht)) * height))
        y2 = min(y2, height-1)
        self.logger.debug("approx area covered is %dx%d to %dx%d" % (
            x1, y1, x2, y2))
        self._org_x1 = x1
        self._org_y1 = y1
        self._org_x2 = x2
        self._org_y2 = y2
        
    def get_zoomrect(self):
        x1, y1, x2, y2 = self._org_x1, self._org_y1, self._org_x2, self._org_y2
        return (x1, y1, x2, y2)

    def get_scaling_info(self):
        return (self._pxwd, self._pxht, self._src_x, self._src_y)
    
    def get_canpan(self):
        return self.canpan
    
    def get_rgb_object(self, whence=0):
        """Create an RGB numpy array (NxMx3) representing the data that
        should be rendered at this zoom level and pan settings.
        """
        if (whence <= 0) or (self._cutout == None):
            self._calc_fit()
            # Get the smallest slice of data that will fit our display needs.
            self._cutout = self.get_cutout()

        if (whence <= 1) or (self._prergb == None):
            # apply current transforms (cut levels, etc)
            vmax = self.rgbmap.get_hash_size() - 1
            newdata = self.apply_data_transforms2(self._cutout, 0, vmax)

            # Record offsets for calculating mapping between screen and data
            # These are the screen locations for self._org_x1 and self._org_y1
            # Note [A]
            fnwd, fnht = self.get_dims(newdata)
            self._off_x = self._dst_x
            self._off_y = self._imgwin_ht - (self._dst_y + fnht)
            self.logger.debug("off_x=%d off_y=%d" % (self._off_x, self._off_y))

            self._prergb = newdata

        if (whence <= 2) or (self._rgbarr == None):
            # Convert data to an index array
            # TODO: Not sure which is the fastest index type, might be 64-bit
            # on 64-bit systems?
            idx = self._prergb.astype('uint32')
            self.logger.debug("shape of index is %s" % (str(idx.shape)))

            # Apply color and intensity mapping.  We produce a dict of
            # ARGB slices.
            rgb = self.rgbmap.get_rgbarray(idx)
            self._rgbarr = rgb

        return self._rgbarr

    def get_cutout(self):
        # get the approx coords of the actual data covered by the
        # desired rendered size in the window
        x1, y1, x2, y2 = self.get_zoomrect()
        dx = x2 - x1 + 1
        dy = y2 - y1 + 1
        self.logger.debug("dx,dy=%d,%d" % (dx, dy))
        width = self.dst_wd
        height = self.dst_ht

        if (dx >= width) or (dy >= height):
            # data size is bigger, skip pixels
            xskip = max(1, dx // width)
            yskip = max(1, dy // height)
            skip = max(xskip, yskip)
            self.logger.debug("xskip=%d yskip=%d skip=%d" % (xskip, yskip, skip))

            # NOTE [A]
            newdata = self.data[y1:y2+1:skip, x1:x2+1:skip]
            self.logger.debug("intermediate shape %s" % str(newdata.shape))
            org_fac = - skip
        else:
            # data size is smaller, repeat pixels
            xrept = max(1, int(math.ceil(float(width) / float(dx))))
            yrept = max(1, int(math.ceil(float(height) / float(dy))))
            rept = max(xrept, yrept)
            self.logger.debug("xrept=%d yrept=%d rept=%d" % (xrept, yrept, rept))

            # Is there a more efficient way to do this?
            # NOTE [A]
            newdata = self.data[y1:y2+1, x1:x2+1]
            self.logger.debug("intermediate shape 1 %s" % str(newdata.shape))
            newdata = newdata.repeat(rept, axis=0)
            newdata = newdata.repeat(rept, axis=1)
            self.logger.debug("intermediate shape 2 %s" % str(newdata.shape))
            org_fac = rept

        # NOTE [A]
        wd, ht = self.get_dims(newdata)
        self.logger.debug("cutout is %dx%d  render=%dx%d" % (wd, ht, width, height))
        assert (wd >= width) and (ht >= height), \
               FitsImageError("cutout is %dx%d  render=%dx%d" % (
            wd, ht, width, height))

        # Record the transformation (skips or fills)
        self._org_fac = org_fac
        self._org_wd = wd
        self._org_ht = ht
        
        return newdata
        

    def get_data_xy(self, win_x, win_y, fractional=True, center=True):
        """Returns the closest x, y coordinates in the data array to the
        x, y coordinates reported on the window (win_x, win_y).

        If center==True, then the coordinates are mapped such that the
        integer pixel begins in the center of the square when the image
        is zoomed in past 1X.  This is the specification of the FITS image
        standard, that the pixel is centered on the integer row/column.
        """
        self.logger.debug("before adjustment, win_x=%d win_y=%d" % (win_x, win_y))

        ## if ((win_x < self._dst_x) or (win_x >= self._dst_x + self._pxwd) or
        ##     (win_y < self._dst_y) or (win_y >= self._dst_y + self._pxht)):
        ##     raise FitsImageCoordsError("Screen coords (%d, %d) out of range of image" % (
        ##         win_x, win_y))


        # First, translate window coordinates onto pixel image
        win_x = win_x - self._off_x
        # (invert Y-axis for FITS)
        win_y = (self._imgwin_ht - 1) - win_y
        win_y = win_y - self._off_y
        self.logger.debug("after adjustment, win_x=%d win_y=%d" % (win_x, win_y))

        if self._org_fac < 0:
            #<= View is zoomed out less than 1X (1/2, 1/3, ...)
            off_x = win_x * abs(self._org_fac)
            off_y = win_y * abs(self._org_fac)
        else:
            if not fractional:
                off_x = win_x // self._org_fac
                off_y = win_y // self._org_fac
            else:
                off_x = float(win_x) / self._org_fac
                off_y = float(win_y) / self._org_fac
                if center:
                    off_x -= 0.5
                    off_y -= 0.5
                    
        # Second, convert screen coords to data coords
        x = self._org_x1 + off_x
        y = self._org_y1 + off_y
        self.logger.debug("data_x=%d data_y=%d" % (x, y))

        ## if (x < 0) or (x >= self.width) or (y < 0) or (y >= self.height):
        ##     raise FitsImageCoordsError("Image coords (%d, %d) out of range of image (%d, %d)" % (
        ##         x, y, self.width-1, self.height-1))

        # Account for user specified transforms
        if self._flipX:
            x = self.width - 1 - x
        if self._flipY:
            y = self.height - 1 - y
        if self._swapXY:
            x, y = y, x

        return (x, y)

    def get_data_pct(self, xpct, ypct):
        # Account for user specified transforms
        ## if self._swapXY:
        ##     xpct, ypct = ypct, xpct

        width, height = self.get_data_size()
        x = int(float(xpct) * (width-1))
        y = int(float(ypct) * (height-1))
        
        ## if self._flipY:
        ##     y = height - 1 - y
        ## if self._flipX:
        ##     x = width - 1 - x

        return (x, y)
        
    def get_data_rect(self):
        """Return the coordinates in the actual data corresponding to the
        area shown in the display for the current zoom level and pan.
        Returns (x1, y1, x2, y2) lower-left to upper-right
        """
        a1 = self._dst_x
        b1 = self._dst_y
        a2 = a1 + self._pxwd - 1
        if a2 >= self._imgwin_wd:
            a2 = self._imgwin_wd - 1
        b2 = b1 + self._pxht - 1
        if b2 >= self._imgwin_ht:
            b2 = self._imgwin_ht - 1
        x1, y1 = self.get_data_xy(a1, b2)
        x2, y2 = self.get_data_xy(a2, b1)

        return (x1, y1, x2, y2)


    def get_data(self, data_x, data_y):
        """Get the data value at position (data_x, data_y).  Indexes are
        0-based, as in numpy.
        """
        return self.image.get_data_xy(data_x, data_y)

    def get_canvas_xy(self, data_x, data_y, center=True):
        """Returns the closest x, y coordinates in the graphics space to the
        x, y coordinates in the data.  data_x and data_y can be integer or
        floating point values.

        If center==True, then the coordinates are mapped such that the
        integer pixel begins in the center of the square when the image
        is zoomed in past 1X.  This is the specification of the FITS image
        standard, that the pixel is centered on the integer row/column.
        """
        # Account for user specified transforms
        if self._swapXY:
            data_x, data_y = data_y, data_x
        if self._flipY:
            data_y = self.height - 1 - data_y
        if self._flipX:
            data_x = self.width - 1 - data_x

        # Account for fractional pixels if zoomed in
        if isinstance(data_x, float):
            frac_x = data_x - int(data_x)
            data_x = int(data_x)
            frac_y = data_y - int(data_y)
            data_y = int(data_y)
        else:
            frac_x = 0.0
            frac_y = 0.0
            
        off_x = data_x - self._org_x1
        off_y = data_y - self._org_y1

        if self._org_fac > 0:
            off_x *= self._org_fac
            off_y *= self._org_fac
        elif self._org_fac < 0:
            off_x /= abs(self._org_fac)
            off_y /= abs(self._org_fac)
        
        win_x = self._off_x + off_x
        win_y = self._off_y + off_y
        # (invert Y-axis for graphics coords)
        win_y = (self._imgwin_ht - 1) - win_y

        if self._org_fac > 0:
            #<= View is zoomed in greater than 1X
            po_x = int(self._org_fac * frac_x)
            po_y = int(self._org_fac * frac_y)
            if center:
                win_x += (self._org_fac // 2) + po_x
                win_y -= (self._org_fac // 2) + po_y
            else:
                win_x += po_x
                win_y -= po_y
            
        self.logger.debug("win_x=%d win_y=%d" % (win_x, win_y))

##         if (win_x < 0) or (win_x >= self._imgwin_wd) or \
##                (win_y < 0) or (win_y >= self._imgwin_ht):
##             raise FitsImageCoordsError("Data coords (%d, %d) out of range of window (%d, %d)" % (
##                 win_x, win_y, self._imgwin_wd-1, self._imgwin_ht-1))

        return (win_x, win_y)
        

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
    
    def apply_data_transforms1(self):
        newdata = self.image.get_data()
        self.logger.debug("data shape is %s" % str(newdata.shape))
        
        if self._swapXY:
            newdata = newdata.swapaxes(0, 1)
        if self._flipY:
            newdata = numpy.flipud(newdata)
        if self._flipX:
            newdata = numpy.fliplr(newdata)

        self.data = newdata
        self.width, self.height = self.get_dims(newdata)
        self.logger.debug("new data shape is %dx%d" % (self.width, self.height))

    def apply_data_transforms2(self, data, vmin, vmax):
        # apply other transforms
        # Flip Y for natural natural Y-axis inversion between FITS coords
        # and screen coords
        newdata = numpy.flipud(data)

        newdata = self._cut_levels(newdata, self.t_locut, self.t_hicut,
                                   vmin=vmin, vmax=vmax)
        return newdata

        
    def zoom_to(self, zoomlevel, no_reset=False, redraw=True):
        if zoomlevel > self.t_zoom_max:
            self.logger.debug("max zoom reached")
            return
        if zoomlevel < self.t_zoom_min:
            self.logger.debug("min zoom reached")
            return
        self.t_zoomlevel = zoomlevel

        if zoomlevel >= 1.0:
            self._scalefactor = zoomlevel
        elif zoomlevel < -1.0:
            self._scalefactor = 1.0 / float(abs(zoomlevel))
        else:
            # wierd condition?--reset to 1:1
            self._scalefactor = 1.0
            self.t_zoomlevel = 1.0

        # If user specified override for auto zoom, then turn off
        # auto zoom now that they have set the zoom manually
        if (not no_reset) and (self.t_autoscale == 'override'):
            value = 'off'
            self.t_autoscale = value
            self.make_callback('autozoom', value)

        self.make_callback('zoom-set', self.t_zoomlevel, self._scalefactor)
        if redraw:
            self.redraw()

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
        zoomx = float(wwidth) / float(self.width)
        zoomy = float(wheight) / float(self.height)
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
        return self._scalefactor

    def get_scale_text(self):
        if self._scalefactor >= 1.0:
            text = '%dx' % (int(self._scalefactor))
        else:
            text = '1/%dx' % (int(1.0/self._scalefactor))
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
    
    def set_pan(self, x_factor, y_factor, redraw=True):
        assert (0 <= x_factor <= 1.0), \
               FitsImageError("Bad X pan factor: %f" % (x_factor))
        assert (0 <= y_factor <= 1.0), \
               FitsImageError("Bad Y pan factor: %f" % (y_factor))

        # Account for user specified transforms
        if self._swapXY:
            x_factor, y_factor = y_factor, x_factor
        if self._flipX:
            x_factor = 1.0 - x_factor
        if self._flipY:
            y_factor = 1.0 - y_factor

        self.t_panx = x_factor
        self.t_pany = y_factor
        self.logger.info("pan set to t_panx=%f t_pany=%f" % (
            x_factor, y_factor))
        if redraw:
            self.redraw(whence=0)

    def get_pan(self):
        return (self.t_panx, self.t_pany)
    
    def panset_xy(self, data_x, data_y, redraw=True):
        data_wd, data_ht = self.get_data_size()
        panx = float(data_x) / float(data_wd)
        pany = float(data_y) / float(data_ht)

        self.set_pan(panx, pany, redraw=redraw)

    def get_transforms(self):
        return (self._flipX, self._flipY, self._swapXY)

    def get_minmax(self):
        return self.image.get_minmax()
        
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
        # Adjust pan position to account for previous state of
        # transformations
        self.logger.debug("before adjustment: %s t_panx=%f t_pany=%f" % (
            self.name, self.t_panx, self.t_pany))
        if flipy != self._flipY:
            self.t_pany = 1.0 - self.t_pany
        if flipx != self._flipX:
            self.t_panx = 1.0 - self.t_panx
        self.logger.debug("after adjustment: %s t_panx=%f t_pany=%f" % (
            self.name, self.t_panx, self.t_pany))

        self._flipX = flipx
        self._flipY = flipy
        self._swapXY = swapxy
        self.logger.debug("flipx=%s flipy=%s swapXY=%s" % (
            self._flipX, self._flipY, self._swapXY))
        # NOTE [A]
        self.apply_data_transforms1()

        self.make_callback('transform')
        if redraw:
            self.redraw(whence=0)

    def histogram(self, x1, y1, x2, y2, numbins=2048):
        data = self.data[y1:y2, x1:x2]
        width, height = self.get_dims(data)
        self.logger.debug("Histogram analysis array is %dx%d" % (
            width, height))

        minval = data.min()
        if numpy.isnan(minval):
            self.logger.warn("NaN's found in data, using workaround for histogram")
            minval = numpy.nanmin(data)
            maxval = numpy.nanmax(data)
            substval = (minval + maxval)/2.0
            # Oh crap, the array has a NaN value.  We have to workaround
            # this by making a copy of the array and substituting for
            # the NaNs, otherwise numpy's histogram() cannot handle it
            data = data.copy()
            data[numpy.isnan(data)] = substval
            dist, bins = numpy.histogram(data, bins=numbins,
                                         density=False)
        else:
            dist, bins = numpy.histogram(data, bins=numbins,
                                         density=False)

        return dist, bins

    def copy_attributes(self, dst_fi, attrlist, redraw=False):
        """Copy interesting attributes of our configuration to another
        instance of a FitsImage."""

        if 'transforms' in attrlist:
            dst_fi.transform(self._flipX, self._flipY, self._swapXY,
                             redraw=False)

        if 'cutlevels' in attrlist:
            dst_fi.cut_levels(self.t_locut, self.t_hicut,
                              redraw=False)

        if 'rgbmap' in attrlist:
            #dst_fi.set_rgbmap(self.rgbmap, redraw=False)
            dst_fi.rgbmap = self.rgbmap

        if 'zoom' in attrlist:
            dst_fi.zoom_to(self.t_zoomlevel, redraw=False)

        if 'pan' in attrlist:
            dst_fi.set_pan(self.t_panx, self.t_pany, redraw=False)

        if redraw:
            dst_fi.redraw(whence=0)
            
#END
