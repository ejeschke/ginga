#
# iqcalc.py -- image quality calculations on FITS data
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import math
import logging
import threading

import numpy as np

try:
    import scipy.optimize as optimize
    import scipy.ndimage as ndimage
    import scipy.ndimage.filters as filters
    have_scipy = True
except ImportError:
    have_scipy = False

from ginga.misc import Bunch


def get_mean(data_np):
    """Calculate mean for valid values.

    Parameters
    ----------
    data_np : ndarray
        Input array.

    Returns
    -------
    result : float
        Mean of array values that are finite.
        If array contains no finite values, returns NaN.

    """
    i = np.isfinite(data_np)
    if not np.any(i):
        return np.nan
    return np.mean(data_np[i])


def get_median(data_np):
    """Like :func:`get_mean` but for median."""
    i = np.isfinite(data_np)
    if not np.any(i):
        return np.nan
    return np.median(data_np[i])


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
        y = (1.0 / (p[1] * np.sqrt(2 * np.pi)) *
             np.exp(-(x - p[0]) ** 2 / (2 * p[1] ** 2))) * p[2]
        return y

    def calc_fwhm_gaussian(self, arr1d, medv=None, gauss_fn=None):
        """FWHM calculation on a 1D array by using least square fitting of
        a gaussian function on the data.  arr1d is a 1D array cut in either
        X or Y direction on the object.
        """
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")
        if gauss_fn is None:
            gauss_fn = self.gaussian

        N = len(arr1d)
        X = np.array(list(range(N)))
        Y = arr1d
        # Fitting works more reliably if we do the following
        # a. subtract sky background
        if medv is None:
            medv = get_median(Y)
        Y = Y - medv
        maxv = Y.max()
        # b. clamp to 0..max (of the sky subtracted field)
        Y = Y.clip(0, maxv)

        # Fit a gaussian
        p0 = [0, N - 1, maxv]              # Inital guess
        # Distance to the target function
        errfunc = lambda p, x, y: gauss_fn(x, p) - y  # noqa
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
        fwhm = 2.0 * np.sqrt(2.0 * np.log(2.0)) * sdev
        # some routines choke on numpy values and need "pure" Python floats
        # e.g. when marshalling through a remote procedure interface
        fwhm = float(fwhm)
        mu = float(mu)
        sdev = float(sdev)
        maxv = float(maxv)

        res = Bunch.Bunch(fwhm=fwhm, mu=mu, sdev=sdev, maxv=maxv,
                          fit_fn=gauss_fn, fit_args=[mu, sdev, maxv])
        return res

    def moffat(self, x, p):
        """Moffat fitting function in 1D.
        p[0]==mean, p[1]==corewidth(gamma), p[2]=power(alpha), p[3]=maxv
        """
        y = (1.0 + (x - p[0]) ** 2 / p[1] ** 2) ** (-1.0 * p[2]) * p[3]
        return y

    def calc_fwhm_moffat(self, arr1d, medv=None, moffat_fn=None):
        """FWHM calculation on a 1D array by using least square fitting of
        a Moffat function on the data.  arr1d is a 1D array cut in either
        X or Y direction on the object.
        """
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")
        if moffat_fn is None:
            moffat_fn = self.moffat

        N = len(arr1d)
        X = np.array(list(range(N)))
        Y = arr1d
        # Fitting works more reliably if we do the following
        # a. subtract sky background
        if medv is None:
            medv = get_median(Y)
        Y = Y - medv
        maxv = Y.max()
        # b. clamp to 0..max (of the sky subtracted field)
        Y = Y.clip(0, maxv)

        # Fit a moffat
        p0 = [0, N - 1, 2, maxv]              # Inital guess
        # Distance to the target function
        errfunc = lambda p, x, y: moffat_fn(x, p) - y  # noqa
        # Least square fit to the gaussian
        with self.lock:
            # NOTE: without this mutex, optimize.leastsq causes a fatal error
            # sometimes--it appears not to be thread safe.
            # The error is:
            # "SystemError: null argument to internal routine"
            # "Fatal Python error: GC object already tracked"
            p1, success = optimize.leastsq(errfunc, p0[:], args=(X, Y))

        if not success:
            raise IQCalcError("FWHM moffat fitting failed")

        mu, width, power, maxv = p1
        width = np.abs(width)
        self.logger.debug("mu=%f width=%f power=%f maxv=%f" % (
            mu, width, power, maxv))

        fwhm = 2.0 * width * np.sqrt(2.0 ** (1.0 / power) - 1.0)

        # some routines choke on numpy values and need "pure" Python floats
        # e.g. when marshalling through a remote procedure interface
        fwhm = float(fwhm)
        mu = float(mu)
        width = float(width)
        power = float(power)
        maxv = float(maxv)

        res = Bunch.Bunch(fwhm=fwhm, mu=mu, width=width, power=power,
                          maxv=maxv, fit_fn=moffat_fn,
                          fit_args=[mu, width, power, maxv])
        return res

    def calc_fwhm(self, arr1d, medv=None, method_name='gaussian'):

        # Calculate FWHM in each direction
        fwhm_fn = self.calc_fwhm_gaussian
        if method_name == 'moffat':
            fwhm_fn = self.calc_fwhm_moffat

        return fwhm_fn(arr1d, medv=medv)

    def get_fwhm(self, x, y, radius, data, medv=None, method_name='gaussian'):
        """Get the FWHM value of the object at the coordinates (x, y) using
        radius.
        """
        if medv is None:
            medv = get_median(data)

        # Get two cuts of the data, one in X and one in Y
        x0, y0, xarr, yarr = self.cut_cross(x, y, radius, data)

        # Calculate FWHM in each direction
        x_res = self.calc_fwhm(xarr, medv=medv, method_name=method_name)
        fwhm_x, cx = x_res.fwhm, x_res.mu

        y_res = self.calc_fwhm(yarr, medv=medv, method_name=method_name)
        fwhm_y, cy = y_res.fwhm, y_res.mu

        ctr_x = x0 + cx
        ctr_y = y0 + cy
        self.logger.debug("fwhm_x,fwhm_y=%f,%f center=%f,%f" % (
            fwhm_x, fwhm_y, ctr_x, ctr_y))
        return (fwhm_x, fwhm_y, ctr_x, ctr_y, x_res, y_res)

    def starsize(self, fwhm_x, deg_pix_x, fwhm_y, deg_pix_y):
        cdelta1 = math.fabs(deg_pix_x)
        cdelta2 = math.fabs(deg_pix_y)
        fwhm = (fwhm_x * cdelta1 + fwhm_y * cdelta2) / 2.0
        fwhm = fwhm * 3600.0
        return fwhm

    def centroid(self, data, xc, yc, radius):
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")
        xc, yc = int(xc), int(yc)
        x0, y0, arr = self.cut_region(xc, yc, int(radius), data)
        # See https://stackoverflow.com/questions/25369982/center-of-mass-for-roi-in-python
        cp_arr = np.asarray(arr)
        cy, cx = ndimage.center_of_mass(cp_arr)
        return (x0 + cx, y0 + cy)

    # FINDING BRIGHT PEAKS

    def get_threshold(self, data, sigma=5.0):
        # remove masked elements
        fdata = data[np.logical_not(np.ma.getmaskarray(data))]
        # remove Inf or NaN
        fdata = fdata[np.isfinite(fdata)]

        # find the median
        median = get_median(fdata)

        # NOTE: for this method a good default sigma is 5.0
        dist = np.fabs(fdata - median).mean()
        threshold = median + sigma * dist

        # NOTE: for this method a good default sigma is 2.0
        ## std = np.std(fdata - median)
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
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")
        if threshold is None:
            # set threshold to default if none provided
            threshold = self.get_threshold(data, sigma=sigma)
            self.logger.debug("threshold defaults to %f (sigma=%f)" % (
                threshold, sigma))

        #self.logger.debug("filtering")
        data_max = filters.maximum_filter(data, radius)
        maxima = (data == data_max)
        diff = data_max > threshold
        maxima[diff == 0] = 0

        #self.logger.debug("finding")
        labeled, num_objects = ndimage.label(maxima)
        slices = ndimage.find_objects(labeled)
        peaks = []
        for dy, dx in slices:
            xc = (dx.start + dx.stop - 1) / 2.0
            yc = (dy.start + dy.stop - 1) / 2.0

            # This is only an approximate center; use FWHM or centroid
            # calculation to refine further
            peaks.append((xc, yc))

        self.logger.debug("peaks=%s" % (str(peaks)))
        return peaks

    def cut_region(self, x, y, radius, data):
        """Return a cut region (radius) pixels away from (x, y) in (data).
        """
        n = radius
        ht, wd = data.shape
        x0, x1 = max(0, x - n), min(wd - 1, x + n)
        y0, y1 = max(0, y - n), min(ht - 1, y + n)
        arr = data[y0:y1 + 1, x0:x1 + 1]
        return (x0, y0, arr)

    def cut_cross(self, x, y, radius, data):
        """Cut two data subarrays that have a center at (x, y) and with
        radius (radius) from (data).  Returns the starting pixel (x0, y0)
        of each cut and the respective arrays (xarr, yarr).
        """
        n = int(round(radius))
        ht, wd = data.shape
        x, y = int(round(x)), int(round(y))
        x0, x1 = int(max(0, x - n)), int(min(wd - 1, x + n))
        y0, y1 = int(max(0, y - n)), int(min(ht - 1, y + n))
        xarr = data[y, x0:x1 + 1]
        yarr = data[y0:y1 + 1, x]
        return (x0, y0, xarr, yarr)

    def brightness(self, x, y, radius, medv, data):
        """Return the brightness value found in a region (radius) pixels away
        from (x, y) in (data).
        """
        x0, y0, arr = self.cut_region(x, y, radius, data)
        arr2 = np.sort(arr.flat)
        idx = int(len(arr2) * 0.8)
        res = arr2[idx] - medv
        return float(res)

    def fwhm_data(self, x, y, data, radius=15, method_name='gaussian'):
        return self.get_fwhm(x, y, radius, data, method_name=method_name)

    # EVALUATION ON A FIELD

    def evaluate_peaks(self, peaks, data, bright_radius=2, fwhm_radius=15,
                       fwhm_method='gaussian', cb_fn=None, ev_intr=None):

        height, width = data.shape
        hh = float(height) / 2.0
        ht = float(height)
        h4 = float(height) * 4.0
        wh = float(width) / 2.0
        wd = float(width)
        w4 = float(width) * 4.0

        # Find the median (sky/background) level
        median = float(get_median(data))
        #skylevel = median
        # Old SOSS qualsize() applied this calculation to skylevel
        skylevel = median * self.skylevel_magnification + self.skylevel_offset

        # Form a list of objects and their characteristics
        objlist = []
        for x, y in peaks:
            if ev_intr and ev_intr.is_set():
                raise IQCalcError("Evaluation interrupted!")

            # Find the fwhm in x and y
            try:
                res = self.fwhm_data(x, y, data, radius=fwhm_radius,
                                     method_name=fwhm_method)
                fwhm_x, fwhm_y, ctr_x, ctr_y, x_res, y_res = res

                bx = x_res.fit_fn(round(ctr_x),
                                  (ctr_x,) + tuple(x_res.fit_args[1:]))
                by = y_res.fit_fn(round(ctr_y),
                                  (ctr_y,) + tuple(y_res.fit_args[1:]))
                bright = float((bx + by) / 2.0)

            except Exception as e:
                # Error doing FWHM, skip this object
                self.logger.debug("Error doing FWHM on object at %.2f,%.2f: %s" % (
                    x, y, str(e)))
                continue

            oid_x, oid_y = None, None
            try:
                oid_x, oid_y = self.centroid(data, x, y, fwhm_radius)

            except Exception as e:
                # Error doing centroid
                self.logger.debug("Error doing centroid on object at %.2f,%.2f: %s" % (
                    x, y, str(e)))

            self.logger.debug("orig=%f,%f  ctr=%f,%f  fwhm=%f,%f bright=%f" % (
                x, y, ctr_x, ctr_y, fwhm_x, fwhm_y, bright))
            # overall measure of fwhm as a single value
            fwhm = (math.sqrt(fwhm_x * fwhm_x + fwhm_y * fwhm_y) *
                    (1.0 / math.sqrt(2.0)))

            # calculate a measure of ellipticity
            elipse = math.fabs(min(fwhm_x, fwhm_y) / max(fwhm_x, fwhm_y))

            # calculate a measure of distance from center of image
            dx = wh - ctr_x
            dy = hh - ctr_y
            dx2 = dx * dx / wd / w4
            dy2 = dy * dy / ht / h4
            if dx2 > dy2:
                pos = 1.0 - dx2
            else:
                pos = 1.0 - dy2

            obj = Bunch.Bunch(objx=ctr_x, objy=ctr_y, pos=pos,
                              oid_x=oid_x, oid_y=oid_y,
                              fwhm_x=fwhm_x, fwhm_y=fwhm_y,
                              fwhm=fwhm, fwhm_radius=fwhm_radius,
                              brightness=bright, elipse=elipse,
                              x=int(x), y=int(y),
                              skylevel=skylevel, background=median)
            objlist.append(obj)

            if cb_fn is not None:
                cb_fn(obj)

        return objlist

    def _sortkey(self, obj):
        val = obj.brightness * obj.pos / math.sqrt(obj.fwhm)
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
                    (minelipse < obj.elipse) and (width * edgew < obj.x) and
                    (height * edgew < obj.y) and
                    (width * (1.0 - edgew) > obj.x) and
                    (height * (1.0 - edgew) > obj.y)):
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
        self.logger.debug("peaks=%s" % str(peaks))
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
        data = image.cutout_data(x1, y1, x2, y2, astype=np.float)

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
