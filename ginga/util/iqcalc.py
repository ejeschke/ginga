#
# iqcalc.py -- image quality calculations on FITS data
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import math
import logging
import numpy
import threading
try:
    import scipy.optimize as optimize
    import scipy.ndimage as ndimage
    import scipy.ndimage.filters as filters
    have_scipy = True
except ImportError:
    have_scipy = False
    
from ginga.misc import Bunch


def get_mean(data_np):
    mdata = numpy.ma.masked_array(data_np, numpy.isnan(data_np))
    return numpy.mean(mdata)

def get_median(data_np):
    mdata = numpy.ma.masked_array(data_np, numpy.isnan(data_np))
    return numpy.median(mdata)


class IQCalcError(Exception):
    """Base exception for raising errors in this module."""
    pass


class IQCalc(object):

    def __init__(self, logger=None):
        if not logger:
            logger = logging.getLogger('IQCalc')
        self.logger = logger

        # for mutex around scipy.optimize, which seems to be non-threadsafe
        self.lock = threading.RLock()

        # for adjustments to background level
        self.skylevel_magnification = 1.05
        self.skylevel_offset = 40.0

    # FWHM CALCULATION

    def gaussian(self, x, p):
        """Gaussian fitting function in 1D.  Makes a sine function with
        amplitude determined by maxv.  See calc_fwhm().

        p[0]==mean, p[1]==sdev, p[2]=maxv
        """
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
        X = numpy.array(list(range(N)))
        Y = arr1d
        # Fitting works more reliably if we do the following
        # a. subtract sky background
        if medv is None:
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
        with self.lock:
            # NOTE: without this mutex, optimize.leastsq causes a fatal error
            # sometimes--it appears not to be thread safe.
            # The error is:
            # "SystemError: null argument to internal routine"
            # "Fatal Python error: GC object already tracked"
            p1, success = optimize.leastsq(errfunc, p0[:], args=(X, Y))

        if not success:
            raise IQCalcError("FWHM gaussian fitting failed")

        mu, sdev, maxv = p1
        self.logger.debug("mu=%f sdev=%f maxv=%f" % (mu, sdev, maxv))

        # Now that we have the sdev from fitting, we can calculate FWHM
        # (fwhm = sdev * sqrt(8*log(2)) ?)
        fwhm = 2.0 * numpy.sqrt(2.0 * numpy.log(2.0)) * sdev
        #return (fwhm, mu, sdev, maxv)
        return (float(fwhm), float(mu), float(sdev), maxv)

    def get_fwhm(self, x, y, radius, data, medv=None):
        """
        """
        if medv is None:
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
        return (fwhm_x, fwhm_y, ctr_x, ctr_y, sdx, sdy, maxx, maxy)


    def starsize(self, fwhm_x, deg_pix_x, fwhm_y, deg_pix_y):
        cdelta1 = math.fabs(deg_pix_x)
        cdelta2 = math.fabs(deg_pix_y)
        fwhm = (fwhm_x * cdelta1 + fwhm_y * cdelta2) / 2.0
        fwhm = fwhm * 3600.0
        return fwhm

    def centroid(self, data, xc, yc, radius):
        x0, y0, arr = self.cut_region(self, xc, yc, radius, data)
        cy, cx = ndimage.center_of_mass(arr)
        return (cx, cy)


    # FINDING BRIGHT PEAKS

    def get_threshold(self, data, sigma=5.0):
        median = numpy.median(data)
        # NOTE: for this method a good default sigma is 5.0
        dist = numpy.fabs(data - median).mean()
        threshold = median + sigma * dist
        # NOTE: for this method a good default sigma is 2.0
        ## std = numpy.std(data - median)
        ## threshold = median + sigma * std
        self.logger.debug("calc threshold=%f" % (threshold))
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
        if threshold is None:
            # set threshold to default if none provided
            threshold = self.get_threshold(data, sigma=sigma)
            self.logger.debug("threshold defaults to %f (sigma=%f)" % (
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


    def brightness(self, x, y, radius, medv, data):
        """Return the brightness value found in a region (radius) pixels away
        from (x, y) in (data).
        """
        x0, y0, arr = self.cut_region(x, y, radius, data)
        arr2 = numpy.sort(arr.flat)
        idx = int(len(arr2) * 0.8)
        res = arr2[idx] - medv
        return float(res)


    def fwhm_data(self, x, y, data, radius=15):
        return self.get_fwhm(x, y, radius, data)


    # EVALUATION ON A FIELD
    
    def evaluate_peaks(self, peaks, data, bright_radius=2, fwhm_radius=15,
                       fwhm_method=1, cb_fn=None, ev_intr=None):

        height, width = data.shape
        hh = float(height) / 2.0
        ht = float(height)
        h4 = float(height) * 4.0
        wh = float(width) / 2.0
        wd = float(width)
        w4 = float(width) * 4.0

        # Find the median (sky/background) level
        median = float(numpy.median(data))
        #skylevel = median
        # Old SOSS qualsize() applied this calculation to skylevel
        skylevel = median * self.skylevel_magnification + self.skylevel_offset

        # Form a list of objects and their characteristics
        objlist = []
        for x, y in peaks:
            if ev_intr and ev_intr.isSet():
                raise IQCalcError("Evaluation interrupted!")
            
            # Find the fwhm in x and y
            try:
                if fwhm_method == 1:
                    (fwhm_x, fwhm_y, ctr_x, ctr_y,
                     sdx, sdy, maxx, maxy) = self.fwhm_data(x, y, data,
                                                            radius=fwhm_radius)

                    ## # Average the X and Y gaussian fitting near the peak
                    bx = self.gaussian(round(ctr_x), (ctr_x, sdx, maxx))
                    by = self.gaussian(round(ctr_y), (ctr_y, sdy, maxy))
                    ## ## bx = self.gaussian(ctr_x, (ctr_x, sdx, maxx))
                    ## ## by = self.gaussian(ctr_y, (ctr_y, sdy, maxy))
                    bright = float((bx + by)/2.0)

                else:
                    raise IQCalcError("Method (%d) not supported for fwhm calculation!" %(
                        fwhm_method))

            except Exception as e:
                # Error doing FWHM, skip this object
                self.logger.debug("Error doing FWHM on object at %.2f,%.2f: %s" % (
                    x, y, str(e)))
                continue

            self.logger.debug("orig=%f,%f  ctr=%f,%f  fwhm=%f,%f bright=%f" % (
                x, y, ctr_x, ctr_y, fwhm_x, fwhm_y, bright))
            # overall measure of fwhm as a single value
            #fwhm = math.sqrt(fwhm_x*fwhm_x + fwhm_y*fwhm_y)
            #fwhm = (math.fabs(fwhm_x) + math.fabs(fwhm_y)) / 2.0
            fwhm = (math.sqrt(fwhm_x*fwhm_x + fwhm_y*fwhm_y) *
                    (1.0 / math.sqrt(2.0)) )

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

            obj = Bunch.Bunch(objx=ctr_x, objy=ctr_y, pos=pos, 
                              fwhm_x=fwhm_x, fwhm_y=fwhm_y,
                              fwhm=fwhm, fwhm_radius=fwhm_radius,
                              brightness=bright, elipse=elipse,
                              x=int(x), y=int(y),
                              skylevel=skylevel, background=median)
            objlist.append(obj)

            if cb_fn is not None:
                cb_fn(obj)

        return objlist

    # def _compare(self, obj1, obj2):
    #     val1 = obj1.brightness * obj1.pos/math.sqrt(obj1.fwhm)
    #     val2 = obj2.brightness * obj2.pos/math.sqrt(obj2.fwhm)
    #     if val1 > val2:
    #         return -1
    #     elif val2 > val1:
    #         return 1
    #     else:
    #         return 0

    def _sortkey(self, obj):
        val = obj.brightness * obj.pos/math.sqrt(obj.fwhm)
        return val
            
    def objlist_select(self, objlist, width, height,
                        minfwhm=2.0, maxfwhm=150.0, minelipse=0.5,
                        edgew=0.01):

        results = []
        count = 0
        for obj in objlist:
            count += 1
            self.logger.debug("%d obj x,y=%.2f,%.2f fwhm=%.2f bright=%.2f" % (
                count, obj.objx, obj.objy, obj.fwhm, obj.brightness))
            # If peak has a minfwhm < fwhm < maxfwhm and the object
            # is inside the frame by edgew pct
            if ((minfwhm < obj.fwhm) and (obj.fwhm < maxfwhm) and
                (minelipse < obj.elipse) and (width*edgew < obj.x) and
                (height*edgew < obj.y) and (width*(1.0-edgew) > obj.x) and
                (height*(1.0-edgew) > obj.y)):
                results.append(obj)

        #results.sort(cmp=self._compare)
        results.sort(key=self._sortkey, reverse=True)
        return results

    def pick_field(self, data, peak_radius=5, bright_radius=2, fwhm_radius=15,
                   threshold=None,
                   minfwhm=2.0, maxfwhm=50.0, minelipse=0.5,
                   edgew=0.01):

        height, width = data.shape

        # Find the bright peaks in the image
        peaks = self.find_bright_peaks(data, radius=peak_radius,
                                       threshold=threshold)
        #print "peaks=", peaks
        self.logger.info("peaks=%s" % str(peaks))
        if len(peaks) == 0:
            raise IQCalcError("Cannot find bright peaks")

        # Evaluate those peaks
        objlist = self.evaluate_peaks(peaks, data,
                                      bright_radius=bright_radius,
                                      fwhm_radius=fwhm_radius)
        if len(objlist) == 0:
            raise IQCalcError("Error evaluating bright peaks")
        
        results = self.objlist_select(objlist, width, height,
                                      minfwhm=minfwhm, maxfwhm=maxfwhm,
                                      minelipse=minelipse, edgew=edgew)
        if len(results) == 0:
            raise IQCalcError("No object matches selection criteria")

        return results[0]


    def qualsize(self, image, x1=None, y1=None, x2=None, y2=None,
                 radius=5, bright_radius=2, fwhm_radius=15, threshold=None, 
                 minfwhm=2.0, maxfwhm=50.0, minelipse=0.5,
                 edgew=0.01):
        
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        data = image.cutout_data(x1, y1, x2, y2, astype='float32')

        qs = self.pick_field(data, peak_radius=radius,
                             bright_radius=bright_radius,
                             fwhm_radius=fwhm_radius,
                             threshold=threshold,
                             minfwhm=minfwhm, maxfwhm=maxfwhm,
                             minelipse=minelipse, edgew=edgew)

        # Add back in offsets into image to get correct values with respect
        # to the entire image
        qs.x += x1
        qs.y += y1
        qs.objx += x1
        qs.objy += y1
        self.logger.debug("obj=%f,%f fwhm=%f sky=%f bright=%f" % (
            qs.objx, qs.objy, qs.fwhm, qs.skylevel, qs.brightness))

        return qs
     
#END
