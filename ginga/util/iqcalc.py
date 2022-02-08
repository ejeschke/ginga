"""Module to handle image quality calculations."""
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
    from scipy.ndimage import maximum_filter
    from scipy.interpolate import interp1d
    have_scipy = True
except ImportError:
    have_scipy = False

from ginga.misc import Bunch

__all__ = ['get_mean', 'get_median', 'IQCalcError', 'IQCalc']


def get_mean(data_np):
    """Calculate mean for valid values.

    Parameters
    ----------
    data_np : ndarray
        Input array. Can contain masked values.

    Returns
    -------
    result : float
        Mean of array values that are finite.
        If array contains no finite values, returns NaN.

    """
    i = np.isfinite(data_np)
    if not np.any(i):
        return np.nan
    # NOTE: we use "ma" version of mean because this can be used with
    # masked arrays created by cutting out non-rectangular shapes
    return np.ma.mean(data_np[i])


def get_median(data_np):
    """Like :func:`get_mean` but for median."""
    i = np.isfinite(data_np)
    if not np.any(i):
        return np.nan
    # NOTE: we use "ma" version of median because this can be used with
    # masked arrays created by cutting out non-rectangular shapes
    return np.ma.median(data_np[i])


class IQCalcError(Exception):
    """Base exception for raising errors in this module."""
    pass


class IQCalc(object):
    """Class to handle model fitting and FWHM calculations.

    Parameters
    ----------
    logger : obj or `None`
        Python logger. If not given, one will be created.

    Attributes
    ----------
    lock : :py:class:`threading.RLock`
        For mutex around `scipy.optimize`, which seems to be non-threadsafe.

    skylevel_magnification, skylevel_offset : float
        For adjustments to sky background level.

    """
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
        """Evaluate Gaussian function in 1D. See :meth:`calc_fwhm`.

        Parameters
        ----------
        x : array-like
            X values.

        p : tuple of float
            Parameters for Gaussian, i.e., ``(mean, stddev, amplitude)``.

        Returns
        -------
        y : array-like
            Y values.

        """
        y = (1.0 / (p[1] * np.sqrt(2 * np.pi)) *
             np.exp(-(x - p[0]) ** 2 / (2 * p[1] ** 2))) * p[2]
        return y

    def calc_fwhm_gaussian(self, arr1d, medv=None, gauss_fn=None):
        """FWHM calculation on a 1D array by using least square fitting of
        a Gaussian function on the data.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        gauss_fn : func or `None`
            Gaussian function for fitting. If not given, :meth:`gaussian`
            is used.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        IQCalcError
            Fitting failed.

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
            raise IQCalcError("FWHM Gaussian fitting failed")

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
        """Evaluate Moffat function in 1D. See :meth:`calc_fwhm`.

        Parameters
        ----------
        x : array-like
            X values.

        p : tuple of float
            Parameters for Moffat, i.e., ``(x_0, gamma, alpha, amplitude)``,
            where ``x_0`` a.k.a. mean and ``gamma`` core width.

        Returns
        -------
        y : array-like
            Y values.

        """
        y = (1.0 + (x - p[0]) ** 2 / p[1] ** 2) ** (-1.0 * p[2]) * p[3]
        return y

    def calc_fwhm_moffat(self, arr1d, medv=None, moffat_fn=None):
        """FWHM calculation on a 1D array by using least square fitting of
        a Moffat function on the data.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        moffat_fn : func or `None`
            Moffat function for fitting. If not given, :meth:`moffat` is used.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        IQCalcError
            Fitting failed.

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
            raise IQCalcError("FWHM Moffat fitting failed")

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
        """Calculate FWHM for the given input array.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        method_name : {'gaussian', 'moffat'}
            Function to use for fitting.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        """
        # Calculate FWHM in each direction
        fwhm_fn = self.calc_fwhm_gaussian
        if method_name == 'moffat':
            fwhm_fn = self.calc_fwhm_moffat

        return fwhm_fn(arr1d, medv=medv)

    def get_fwhm(self, x, y, radius, data, medv=None, method_name='gaussian'):
        """Get the FWHM values of the object at the given coordinates and
        radius.

        Parameters
        ----------
        x, y : int
            Indices of the object location in data array.

        radius : float
            Radius of the region encompassing the object.

        data : array-like
            Data array.

        medv, method_name
            See :meth:`calc_fwhm`.

        Returns
        -------
        fwhm_x, fwhm_y : float
            FWHM in X and Y, respectively.

        ctr_x, ctr_y : float
            Center in X and Y, respectively.

        x_res, y_res : dict
            Fit results from :meth:`calc_fwhm` in X and Y, respectively.

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
        """Calculate average FWHM in arcseconds.

        Parameters
        ----------
        fwhm_x : float
            FWHM in X (pixels).

        deg_pix_x : float
            Plate scale from CDELT1 in degrees per pixel.

        fwhm_y : float
            FWHM in Y (pixels).

        deg_pix_y : float
            Plate scale from CDELT2 in degrees per pixel.

        Returns
        -------
        fwhm : float
            Average FWHM in arcseconds.

        """
        cdelta1 = math.fabs(deg_pix_x)
        cdelta2 = math.fabs(deg_pix_y)
        fwhm = (fwhm_x * cdelta1 + fwhm_y * cdelta2) / 2.0
        fwhm = fwhm * 3600.0
        return fwhm

    def centroid(self, data, xc, yc, radius):
        """Calculate centroid from center of mass.

        Parameters
        ----------
        data : array-like
            Data array.

        xc, yc : int
            X and Y indices of the approximate center.

        radius : float
            Half-width of the region to consider around the given center.

        Returns
        -------
        x, y : float
            Centroid indices.

        Raises
        ------
        IQCalcError
            Missing dependency.

        """
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
        """Calculate threshold for :meth:`find_bright_peaks`.

        Parameters
        ----------
        data : array-like
            Data array.

        sigma : float
            Sigma for the threshold.

        Returns
        -------
        threshold : float
            Threshold based on good data, its median, and the given sigma.

        """
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
        """Find bright peak candidates in in the given data.

        Parameters
        ----------
        data : array-like
            Input data to find peaks from.

        threshold : float or `None`
            Detection threshold. Below this value, an object is not
            considered a candidate. If not given, a default is calculated
            using :meth:`get_threshold` with the given ``sigma``.

        sigma : float
            Sigma for the threshold.

        radius : float
            Pixel radius for determining local maxima. If the
            desired objects are larger in size, specify a larger radius.

        Returns
        -------
        peaks : list of tuple
            A list of candidate object coordinate tuples ``(x, y)`` in data.

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
        data_max = maximum_filter(data, radius)
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
        """Return a cut region.

        Parameters
        ----------
        x, y : int
            Indices of central pixel.

        radius : int
            Half-width in both X and Y directions.

        data : array-like
            Data array to cut from.

        Returns
        -------
        x0, y0 : int
            Origin of the region.

        arr : array-like
            Cut region (a view, not copy).

        """
        n = radius
        ht, wd = data.shape
        x0, x1 = max(0, x - n), min(wd - 1, x + n)
        y0, y1 = max(0, y - n), min(ht - 1, y + n)
        arr = data[y0:y1 + 1, x0:x1 + 1]
        return (x0, y0, arr)

    def cut_cross(self, x, y, radius, data):
        """Cut data vertically and horizontally at the given position
        with the given radius.

        Parameters
        ----------
        x, y : int
            Indices where vertical and horizontal cuts meet.

        radius : float
            Radius of both cuts.

        data : array-like
            Data array to cut from.

        Returns
        -------
        x0 : array-like
            Starting pixel of horizontal cut (in X).

        y0 : array-like
            Starting pixel of vertical cut (in Y).

        xarr : array-like
            Horizontal cut (in X).

        yarr : array-like
            Vertical cut (in Y).

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
        """Return the brightness value found in a region defined by input
        location and radius. Region is cut using :meth:`cut_region`.

        Parameters
        ----------
        x, y : int
            Indices of central pixel.

        radius : int
            Half-width in both X and Y directions.

        medv : float
            Background to subtract off.

        data : array-like
            Data array.

        Returns
        -------
        res : float
            Brightness.

        """
        x0, y0, arr = self.cut_region(x, y, radius, data)
        arr2 = np.sort(arr.flat)
        idx = int(len(arr2) * 0.8)
        res = arr2[idx] - medv
        return float(res)

    def fwhm_data(self, x, y, data, radius=15, method_name='gaussian'):
        """Equivalent to :meth:`get_fwhm`."""
        return self.get_fwhm(x, y, radius, data, method_name=method_name)

    # Encircled and ensquared energies (EE)

    def ensquared_energy(self, data):
        """Return a function of ensquared energy across pixel indices.

        Ideally, data is already a masked array and is assumed to be centered.

        """
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")

        tot = data.sum()
        ny, nx = data.shape
        cen_x = int(nx // 2)
        cen_y = int(ny // 2)
        ee = []

        if ny > nx:
            n_max = ny
            cen = cen_y
        else:
            n_max = nx
            cen = cen_x

        if n_max % 2 == 0:  # Even
            delta_i1 = -1
        else:  # Odd
            delta_i1 = 0

        xr = range(n_max - cen)

        for i in xr:
            ix1 = cen_x - i + delta_i1
            if ix1 < 0:
                ix1 = 0
            ix2 = cen_x + i + 1
            if ix2 > nx:
                ix2 = nx
            iy1 = cen_y - i + delta_i1
            if iy1 < 0:
                iy1 = 0
            iy2 = cen_y + i + 1
            if iy2 > ny:
                iy2 = ny
            ee.append(data[iy1:iy2, ix1:ix2].sum() / tot)

        return interp1d(xr, ee, kind='cubic', bounds_error=False,
                        assume_sorted=True)

    # This is adapted from poppy package. See licenses/POPPY_LICENSE.md .
    def encircled_energy(self, data):
        """Return a function of encircled energy across pixel indices.

        Ideally, data is already a masked array and is assumed to be centered.

        """
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")

        y, x = np.indices(data.shape, dtype=float)
        cen = tuple((i - 1) * 0.5 for i in data.shape[::-1])
        x -= cen[0]
        y -= cen[1]
        r = np.sqrt(x * x + y * y)

        ind = np.argsort(r.flat)
        sorted_r = r.flat[ind]
        sorted_data = data.flat[ind]

        # data is already masked
        csim = sorted_data.cumsum(dtype=float)

        sorted_r_int = sorted_r.astype(int)
        deltar = sorted_r_int[1:] - sorted_r_int[:-1]  # assume all radii represented
        rind = np.where(deltar)[0]

        ee = csim[rind] / sorted_data.sum()  # Normalize
        if isinstance(ee, np.ma.MaskedArray):
            ee.set_fill_value(0)
            ee = ee.filled()

        return interp1d(range(ee.size), ee, kind='cubic', bounds_error=False,
                        assume_sorted=True)

    # EVALUATION ON A FIELD

    def evaluate_peaks(self, peaks, data, bright_radius=2, fwhm_radius=15,
                       fwhm_method='gaussian', ee_total_radius=10,
                       cb_fn=None, ev_intr=None):
        """Evaluate photometry for given peaks in data array.

        Parameters
        ----------
        peaks : list of tuple
            List of ``(x, y)`` tuples containing indices of peaks.

        data : array-like
            Data array that goes with the given peaks.

        bright_radius : int
            **This is not used.**

        fwhm_radius, fwhm_method
            See :meth:`get_fwhm`.

        ee_total_radius : float
            Radius, in pixels, where encircled and ensquared energy fractions
            are defined as 1.

        cb_fn : func or `None`
            If applicable, provide a callback function that takes a
            `ginga.misc.Bunch.Bunch` containing the result for each peak.
            It should not return anything.

        ev_intr : :py:class:`threading.Event` or `None`
            For threading, if applicable.

        Returns
        -------
        objlist : list of `ginga.misc.Bunch.Bunch`
            A list of successful results for the given peaks.
            Each result contains the following keys:

            * ``objx``, ``objy``: Fitted centroid from :meth:`get_fwhm`.
            * ``pos``: A measure of distance from the center of the image.
            * ``oid_x``, ``oid_y``: Center-of-mass centroid from :meth:`centroid`.
            * ``fwhm_x``, ``fwhm_y``: Fitted FWHM from :meth:`get_fwhm`.
            * ``fwhm``: Overall measure of fwhm as a single value.
            * ``fwhm_radius``: Input FWHM radius.
            * ``brightness``: Average peak value based on :meth:`get_fwhm` fits.
            * ``elipse``: A measure of ellipticity.
            * ``x``, ``y``: Input indices of the peak.
            * ``skylevel``: Sky level estimated from median of data array and
              ``skylevel_magnification`` and ``skylevel_offset`` attributes.
            * ``background``: Median of the input array.
            * ``ensquared_energy_fn``: Function of ensquared energy for different pixel radii.
            * ``encircled_energy_fn``: Function of encircled energy for different pixel radii.

        """
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

            # centroid calculation on local peak
            oid_x, oid_y = None, None
            try:
                oid_x, oid_y = self.centroid(data, x, y, fwhm_radius)

            except Exception as e:
                # Error doing centroid
                self.logger.debug("Error doing centroid on object at %.2f,%.2f: %s" % (
                    x, y, str(e)))

            # Find the fwhm in x and y, using local peak
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

            # EE on background subtracted image
            ee_sq_fn = None
            ee_circ_fn = None
            iy1 = int(ctr_y - ee_total_radius)
            iy2 = int(ctr_y + ee_total_radius) + 1
            ix1 = int(ctr_x - ee_total_radius)
            ix2 = int(ctr_x + ee_total_radius) + 1

            if iy1 < 0 or iy2 > height or ix1 < 0 or ix2 > width:
                self.logger.debug("Error calculating EE on object at %.2f,%.2f: Box out of range with radius=%.2f" % (x, y, ee_total_radius))
            else:
                ee_data = data[iy1:iy2, ix1:ix2] - median
                try:
                    ee_sq_fn = self.ensquared_energy(ee_data)
                except Exception as e:
                    self.logger.debug("Error calculating ensquared energy on object at %.2f,%.2f: %s" % (x, y, str(e)))
                try:
                    ee_circ_fn = self.encircled_energy(ee_data)
                except Exception as e:
                    self.logger.debug("Error calculating encircled energy on object at %.2f,%.2f: %s" % (x, y, str(e)))

            obj = Bunch.Bunch(objx=ctr_x, objy=ctr_y, pos=pos,
                              oid_x=oid_x, oid_y=oid_y,
                              fwhm_x=fwhm_x, fwhm_y=fwhm_y,
                              fwhm=fwhm, fwhm_radius=fwhm_radius,
                              brightness=bright, elipse=elipse,
                              x=int(x), y=int(y),
                              skylevel=skylevel, background=median,
                              ensquared_energy_fn=ee_sq_fn,
                              encircled_energy_fn=ee_circ_fn)
            objlist.append(obj)

            if cb_fn is not None:
                cb_fn(obj)

        return objlist

    def _sortkey(self, obj):
        """For sorting of result in :meth:`objlist_select`."""
        val = obj.brightness * obj.pos / math.sqrt(obj.fwhm)
        return val

    def objlist_select(self, objlist, width, height,
                       minfwhm=2.0, maxfwhm=150.0, minelipse=0.5,
                       edgew=0.01):
        """Filter output from :meth:`evaluate_peaks`.

        Parameters
        ----------
        objlist : list of `ginga.misc.Bunch.Bunch`
            Output from :meth:`evaluate_peaks`.

        width, height : int
            Dimension of data array from which ``objlist`` was derived.

        minfwhm, maxfwhm : float
            Limits for desired FWHM, where ``(minfwhm, maxfwhm)``.

        minelipse : float
            Minimum value of desired ellipticity (not inclusive).

        edgew : float
            Factor between 0 and 1 that determines if a location is too close to the edge or not.

        Returns
        -------
        results : list of `ginga.misc.Bunch.Bunch`
            Elements of ``objlist`` that contain desired FWHM, ellipticity,
            and not too close to the edge.

        """
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
                   edgew=0.01, ee_total_radius=10):
        """Pick the first good object within the given field.

        Parameters
        ----------
        data : array-like
            Data array of the field.

        peak_radius, threshold
            See :meth:`find_bright_peaks`.

        bright_radius, fwhm_radius, ee_total_radius
            See :meth:`evaluate_peaks`.

        minfwhm, maxfwhm, minelipse, edgew
            See :meth:`objlist_select`.

        Returns
        -------
        result : `ginga.misc.Bunch.Bunch`
            This is a single element of ``objlist`` as described in
            :meth:`evaluate_peaks`.

        Raises
        ------
        IQCalcError
            No object matches selection criteria.

        """
        height, width = data.shape

        # Find the bright peaks in the image
        peaks = self.find_bright_peaks(data, radius=peak_radius,
                                       threshold=threshold)
        self.logger.debug("peaks=%s" % str(peaks))
        if len(peaks) == 0:
            raise IQCalcError("Cannot find bright peaks")

        # Evaluate those peaks
        objlist = self.evaluate_peaks(peaks, data,
                                      bright_radius=bright_radius,
                                      fwhm_radius=fwhm_radius,
                                      ee_total_radius=ee_total_radius)
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
                 edgew=0.01, ee_total_radius=10):
        """Run :meth:`pick_field` on the given image.

        Parameters
        ----------
        image : `ginga.AstroImage.AstroImage`
            Image to process.

        x1, y1, x2, y2 : int
            See :meth:`ginga.BaseImage.BaseImage.cutout_data`.

        radius, threshold
            See :meth:`find_bright_peaks`.

        bright_radius, fwhm_radius, ee_total_radius
            See :meth:`evaluate_peaks`.

        minfwhm, maxfwhm, minelipse, edgew
            See :meth:`objlist_select`.

        Returns
        -------
        qs : `ginga.misc.Bunch.Bunch`
            This is a single element of ``objlist`` as described in
            :meth:`evaluate_peaks`.

        """
        if x1 is None:
            x1 = 0
        if y1 is None:
            y1 = 0
        if x2 is None:
            x2 = image.width
        if y2 is None:
            y2 = image.height

        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        data = image.cutout_data(x1, y1, x2, y2, astype=float)

        qs = self.pick_field(data, peak_radius=radius,
                             bright_radius=bright_radius,
                             fwhm_radius=fwhm_radius,
                             threshold=threshold,
                             minfwhm=minfwhm, maxfwhm=maxfwhm,
                             minelipse=minelipse, edgew=edgew,
                             ee_total_radius=ee_total_radius)

        # Add back in offsets into image to get correct values with respect
        # to the entire image
        qs.x += x1
        qs.y += y1
        qs.objx += x1
        qs.objy += y1
        self.logger.debug("obj=%f,%f fwhm=%f sky=%f bright=%f" % (
            qs.objx, qs.objy, qs.fwhm, qs.skylevel, qs.brightness))

        return qs

# END
