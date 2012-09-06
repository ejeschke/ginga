#
# iqcalc.py -- image quality calculations on FITS data
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Wed Sep  5 18:05:41 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import math
import logging
import numpy
import scipy.optimize as optimize
import scipy.ndimage as ndimage
import scipy.ndimage.filters as filters

import Bunch

class IQCalcError(Exception):
    """Base exception for raising errors in this module."""
    pass


class IQCalc(object):

    def __init__(self, logger=None):
        if not logger:
            logger = logging.getLogger('IQCalc')
        self.logger = logger

        # for adjustments to background level
        self.skylevel_magnification = 1.05
        self.skylevel_offset = 40.0

    ## def histogram(self, data, numbins=20):
    ##     height, width = data.shape
    ##     minval = data.min()
    ##     if numpy.isnan(minval):
    ##         minval = numpy.nanmin(data)
    ##         maxval = numpy.nanmax(data)
    ##         substval = (minval + maxval)/2.0
    ##         # Oh crap, the array has a NaN value.  We have to workaround
    ##         # this by making a copy of the array and substituting for
    ##         # the NaNs, otherwise numpy's histogram() cannot handle it
    ##         data = data.copy()
    ##         data[numpy.isnan(data)] = substval
    ##         dist, bins = numpy.histogram(data, bins=numbins,
    ##                                      density=False)
    ##     else:
    ##         dist, bins = numpy.histogram(data, bins=numbins,
    ##                                      density=False)
    ##     return dist, bins

    # FWHM CALCULATION

    def gaussian(self, x, p):
        """Gaussian fitting function in 1D.  Makes a sine function with
        amplitude determined by maxv.  See calc_fwhm().

        p[0]==mean, p[1]==sdev, p[2]=maxv
        """
        #y = (1.0/(p[1]*numpy.sqrt(2*numpy.pi))*numpy.exp(-(x-p[0])**2/(2*p[1]**2))) * p[2]
        y = (1.0 / (p[1] * numpy.sqrt(2*numpy.pi)) *
             numpy.exp(-(x - p[0])**2 / (2*p[1]**2))) * p[2]
        return y


    def calc_fwhm(self, arr1d, medv=None, gauss_fn=None):
        """FWHM calculation on a 1D array by using least square fitting of
        a gaussian function on the data.  arr1d is a 1D array cut in either
        X or Y direction on the object.
        """
        if not gauss_fn:
            gauss_fn = self.gaussian
            
        N = len(arr1d)
        X = numpy.array(range(N))
        Y = arr1d
        # Fitting works more reliably if we do the following
        # a. subtract sky background
        if medv == None:
            medv = numpy.median(Y)
        Y = Y - medv
        maxv = Y.max()
        # b. clamp to 0..max (of the sky subtracted field)
        Y = Y.clip(0, maxv)

        # Fit a gaussian
        p0 = [0, N-1, maxv]              # Inital guess
        # Distance to the target function
        errfunc = lambda p, x, y: gauss_fn(x, p) - y
        # Least square fit to the gaussian
        p1, success = optimize.leastsq(errfunc, p0[:], args=(X, Y))

        if not success:
            raise IQCalcError("FWHM gaussian fitting failed")

        mu, sdev, maxv = p1
        self.logger.debug("mu=%f sdev=%f" % (mu, sdev))

        # Now that we have the sdev from fitting, we can calculate FWHM
        fwhm = 2.0 * numpy.sqrt(2.0 * numpy.log(2.0)) * sdev
        #return (fwhm, mu, sdev, maxv)
        return (float(fwhm), float(mu), float(sdev), maxv)


    def get_fwhm(self, x, y, radius, data, medv=None):
        """
        """
        if medv == None:
            medv = numpy.median(data)
            
        # Get two cuts of the data, one in X and one in Y
        x0, y0, xarr, yarr = self.cut_cross(x, y, radius, data)

        # Calculate FWHM in each direction
        fwhm_x, cx, sdx, maxx = self.calc_fwhm(xarr, medv=medv)
        fwhm_y, cy, sdy, maxy = self.calc_fwhm(yarr, medv=medv)
        
        ctr_x = x0 + cx
        ctr_y = y0 + cy
        self.logger.debug("fwhm_x,fwhm_y=%f,%f center=%f,%f" % (
            fwhm_x, fwhm_y, ctr_x, ctr_y))
        return (fwhm_x, fwhm_y, ctr_x, ctr_y, sdx, sdy)


    def starsize(self, fwhm_x, deg_pix_x, fwhm_y, deg_pix_y):
        cdelta1 = math.fabs(deg_pix_x)
        cdelta2 = math.fabs(deg_pix_y)
        fwhm = (fwhm_x * cdelta1 + fwhm_y * cdelta2) / 2.0
        fwhm = fwhm * 3600.0
        return fwhm


    # FINDING BRIGHT PEAKS

    def centroid(self, data, xc, yc, radius):
        # TODO
        return xc, yc

    def get_threshold(self, data, sigma=3, iterations=3):
        for i in xrange(iterations):
            median = numpy.ma.median(data)
            stdev = numpy.ma.std(data)
            locut = median - (sigma*stdev)
            hicut = median + (sigma*stdev)
            print "locut=%f hicut=%f" % (locut, hicut)
            data = numpy.ma.masked_outside(data, locut, hicut)

        threshold = hicut
        return threshold
        
    def get_threshold(self, data, sigma=5):
        median = numpy.median(data)
        # avoid dead pixels in threshold calculation
        maxval = data.max()
        dist = (data - median).clip(0, maxval)
        #dist = numpy.sqrt(numpy.var(dist))
        dist = numpy.fabs(data - median).mean()
        # tanaka-san says to try median instead of mean, but so far for
        # "real" images mean is working better
        #dist = numpy.median(numpy.fabs(data - median))
        threshold = median + sigma * dist
        return threshold
        
    def find_bright_peaks(self, data, threshold=None, sigma=5, radius=5):
        """
        Find bright peak candidates in (data).  (threshold) specifies a
        threshold value below which an object is not considered a candidate.
        If threshold is blank, a default is calculated using (sigma).
        (radius) defines a pixel radius for determining local maxima--if the
        desired objects are larger in size, specify a larger radius.

        The routine returns a list of candidate object coordinate tuples
        (x, y) in data.
        """
        if threshold == None:
            # set threshold to default if none provided
            threshold = self.get_threshold(data, sigma=sigma)
            self.logger.debug("threshold defaults to %f (sigma=%f)" % (
                threshold, sigma))
            print ("threshold defaults to %f (sigma=%f)" % (
                threshold, sigma))

        data_max = filters.maximum_filter(data, radius)
        maxima = (data == data_max)
        diff = data_max > threshold
        maxima[diff == 0] = 0

        labeled, num_objects = ndimage.label(maxima)
        slices = ndimage.find_objects(labeled)
        peaks = []
        for dy, dx in slices:
            xc = (dx.start + dx.stop - 1)/2.0
            yc = (dy.start + dy.stop - 1)/2.0

            # This is only an approximate center; use FWHM or centroid
            # calculation to refine further
            peaks.append((xc, yc))

        return peaks


    def cut_region(self, x, y, radius, data):
        """Return a cut region (radius) pixels away from (x, y) in (data).
        """
        n = radius
        ht, wd = data.shape
        x0, x1 = max(0, x-n), min(wd-1, x+n)
        y0, y1 = max(0, y-n), min(ht-1, y+n)
        arr = data[y0:y1+1, x0:x1+1]
        return (x0, y0, arr)


    def cut_cross(self, x, y, radius, data):
        """Cut two data subarrays that have a center at (x, y) and with
        radius (radius) from (data).  Returns the starting pixel (x0, y0)
        of each cut and the respective arrays (xarr, yarr).
        """
        n = radius
        ht, wd = data.shape
        x0, x1 = max(0, x-n), min(wd-1, x+n)
        y0, y1 = max(0, y-n), min(ht-1, y+n)
        xarr = data[y, x0:x1+1]
        yarr = data[y0:y1+1, x]
        return (x0, y0, xarr, yarr)


    def brightness(self, x, y, radius, data):
        """Return the maximum value found in a region (radius) pixels away
        from (x, y) in (data).
        """
        x0, y0, arr = self.cut_region(x, y, radius, data)
        res = numpy.nanmax(arr)
        ## arr2 = numpy.sort(arr.flat)
        ## idx = int(len(arr2) * 0.80)
        ## res = arr2[idx]
        return float(res)


    def fwhm_data(self, x, y, data, radius=10):
        return self.get_fwhm(x, y, radius, data)


    # EVALUATION ON A FIELD
    
    def evaluate_peaks(self, peaks, data, bright_radius=2, fwhm_radius=10):

        height, width = data.shape
        hh = float(height) / 2.0
        ht = float(height)
        h4 = float(height) * 4.0
        wh = float(width) / 2.0
        wd = float(width)
        w4 = float(width) * 4.0

        # Find the median (sky/background) level
        median = float(numpy.median(data))

        skylevel = median
        # Old SOSS qualsize() applies this adjustment to skylevel
        #skylevel = median * self.skylevel_magnification + self.skylevel_offset

        # Form a list of objects and their characteristics
        objlist = []
        for x, y in peaks:
            # Find the fwhm in x and y 
            (fwhm_x, fwhm_y, ctr_x, ctr_y,
             sdx, sdy) = self.fwhm_data(x, y, data, radius=fwhm_radius)
            self.logger.debug("orig=%f,%f  ctr=%f,%f  fwhm=%f,%f" % (
                x, y, ctr_x, ctr_y, fwhm_x, fwhm_y))

            # overall fwhm as a single value
            fwhm = math.sqrt(fwhm_x*fwhm_x + fwhm_y*fwhm_y)

            # calculate a measure of ellipticity
            elipse = math.fabs(min(fwhm_x, fwhm_y) / max(fwhm_x, fwhm_y))

            # calculate a measure of distance from center of image
            dx = wh - ctr_x
            dy = hh - ctr_y
            dx2 = dx*dx / wd / w4
            dy2 = dy*dy / ht / h4
            if dx2 > dy2:
                pos = 1.0 - dx2
            else:
                pos = 1.0 - dy2

            # brightness above background
            bv = self.brightness(int(x), int(y), bright_radius, data)
            bright = bv - median
            #bright = (maxx + maxy) / 2.0
            #print "brightness=%f" % bright

            obj = Bunch.Bunch(objx=ctr_x, objy=ctr_y, pos=pos, 
                              fwhm_x=fwhm_x, fwhm_y=fwhm_y,
                              fwhm=fwhm, fwhm_radius=fwhm_radius,
                              brightness=bright, elipse=elipse,
                              x=int(x), y=int(y),
                              skylevel=skylevel)
            objlist.append(obj)

        return objlist

    def objlist_select(self, objlist, width, height,
                        minfwhm=0.1, maxfwhm=50.0, minelipse=0.0,
                        edgew=0.01):

        maxval = 0.0
        best = None

        for obj in objlist:
            # If peak has a minfwhm < fwhm < maxfwhm and the object
            # is inside the frame by edgew pct
            if ((minfwhm < obj.fwhm) and (obj.fwhm < maxfwhm) and
                (minelipse < obj.elipse) and (width*edgew < obj.x) and
                (height*edgew < obj.y) and (width*(1.0-edgew) > obj.x) and
                (height*(1.0-edgew) > obj.y)):
                # then check 
                val = obj.brightness * obj.pos/math.sqrt(obj.fwhm)
                if maxval < val:
                    maxval = val
                    best = obj

        if best:
            return best
        raise IQCalcError("No object matches criteria")


    def pick_field(self, data, bright_radius=2, radius=10,
                   threshold=None):

        height, width = data.shape

        # Find the bright peaks in the image
        peaks = self.find_bright_peaks(data, radius=radius,
                                       threshold=threshold)
        #print "peaks=", peaks
        self.logger.info("peaks=%s" % str(peaks))
        if len(peaks) == 0:
            raise IQCalcError("Cannot find bright peaks")

        # Evaluate those peaks
        objlist = self.evaluate_peaks(peaks, data,
                                      bright_radius=bright_radius,
                                      fwhm_radius=radius)
        if len(objlist) == 0:
            raise IQCalcError("Error evaluating bright peaks")
        
        bnch = self.objlist_select(objlist, width, height)
        return bnch


#END
