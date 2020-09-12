"""Module to handle image quality calculations using ``astropy``."""

import numpy as np
from astropy.modeling import models, fitting

from ginga.misc import Bunch

# Reuse shared items from the old module until we can merge old and new together.
from ginga.util.iqcalc import IQCalcError, get_median, have_scipy
from ginga.util.iqcalc import IQCalc as _IQCalc

# Import the rest into namespace so we can use this module like iqcalc.
from ginga.util.iqcalc import get_mean  # noqa

try:
    from photutils.centroids import centroid_com
    from photutils.detection import find_peaks
    have_photutils = True
except ImportError:
    have_photutils = False

__all__ = ['IQCalc']


# TODO: Use photutils for source finding.
class IQCalc(_IQCalc):
    """This is `ginga.util.iqcalc.IQCalc` that uses ``astropy``.

    This subclass has an extra ``self.fitter`` attribute for ``astropy``
    fitting.

    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fitter = fitting.LevMarLSQFitter()

    # FWHM CALCULATION

    def _prep_for_fitting(self, arr1d, medv):
        if not have_scipy:
            raise IQCalcError("Please install the 'scipy' module "
                              "to use this function")

        N = len(arr1d)
        X = np.array(list(range(N)))
        Y = np.asarray(arr1d)

        # Fitting works more reliably if we do the following
        # a. subtract sky background
        if medv is None:
            medv = get_median(Y)
        Y = Y - medv
        maxv = Y.max()
        # b. clamp to 0..max (of the sky subtracted field)
        Y = Y.clip(0, maxv)

        return N, X, Y, maxv

    def gaussian(self, x, p):
        """Evaluate Gaussian function in 1D.

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
        g = models.Gaussian1D(amplitude=p[2], mean=p[0], stddev=p[1])
        return g(x)

    def calc_fwhm_gaussian(self, arr1d, medv=None, **kwargs):
        """FWHM calculation on a 1D array by using least square fitting of
        a Gaussian function on the data.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        kwargs : dict
            Not used; for backward-compatible API call only.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        IQCalcError
            Fitting failed.

        """
        N, X, Y, maxv = self._prep_for_fitting(arr1d, medv)

        # Gaussian model with initial guess
        m_init = models.Gaussian1D(
            amplitude=maxv, mean=N * 0.5, stddev=(N * 0.25))

        # NOTE: without this mutex, optimize.leastsq causes a fatal error
        # sometimes--it appears not to be thread safe.
        # The error is:
        # "SystemError: null argument to internal routine"
        # "Fatal Python error: GC object already tracked"
        with self.lock:
            try:
                m = self.fitter(m_init, X, Y)
            except Exception:
                raise IQCalcError("FWHM Gaussian fitting failed")

        # Now that we have the sdev from fitting, we can calculate FWHM
        fwhm = m.fwhm
        # Some routines choke on numpy values and need "pure" Python floats
        # e.g. when marshalling through a remote procedure interface
        mu = m.mean.value
        sdev = m.stddev.value
        maxv = m.amplitude.value

        self.logger.debug('mu={} sdev={} maxv={}'.format(mu, sdev, maxv))

        res = Bunch.Bunch(fwhm=fwhm, mu=mu, sdev=sdev, maxv=maxv,
                          fit_fn=self.gaussian, fit_args=[mu, sdev, maxv])
        return res

    def moffat(self, x, p):
        """Evaluate Moffat function in 1D.

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
        m = models.Moffat1D(amplitude=p[3], x_0=p[0], gamma=p[1], alpha=p[2])
        return m(x)

    def calc_fwhm_moffat(self, arr1d, medv=None, **kwargs):
        """FWHM calculation on a 1D array by using least square fitting of
        a Moffat function on the data.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        kwargs : dict
            Not used; for backward-compatible API call only.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        IQCalcError
            Fitting failed.

        """
        N, X, Y, maxv = self._prep_for_fitting(arr1d, medv)

        # Moffat model with initial guess
        m_init = models.Moffat1D(
            amplitude=maxv, x_0=(N * 0.5), gamma=(N * 0.25), alpha=2)

        # NOTE: without this mutex, optimize.leastsq causes a fatal error
        # sometimes--it appears not to be thread safe.
        # The error is:
        # "SystemError: null argument to internal routine"
        # "Fatal Python error: GC object already tracked"
        with self.lock:
            try:
                m = self.fitter(m_init, X, Y)
            except Exception:
                raise IQCalcError("FWHM Moffat fitting failed")

        fwhm = m.fwhm

        # Some routines choke on numpy values and need "pure" Python floats
        # e.g. when marshalling through a remote procedure interface
        mu = m.x_0.value
        width = np.abs(m.gamma.value)
        power = m.alpha.value
        maxv = m.amplitude.value

        self.logger.debug('mu={} width={} power={} maxv={}'.format(
            mu, width, power, maxv))

        res = Bunch.Bunch(fwhm=fwhm, mu=mu, width=width, power=power,
                          maxv=maxv, fit_fn=self.moffat,
                          fit_args=[mu, width, power, maxv])
        return res

    def lorentz(self, x, p):
        """Evaluate Lorentz function in 1D.

        Parameters
        ----------
        x : array-like
            X values.

        p : tuple of float
            Parameters for Lorentz, i.e., ``(x_0, fwhm, amplitude)``.

        Returns
        -------
        y : array-like
            Y values.

        """
        m = models.Lorentz1D(amplitude=p[2], x_0=p[0], fwhm=p[1])
        return m(x)

    def calc_fwhm_lorentz(self, arr1d, medv=None, **kwargs):
        """FWHM calculation on a 1D array by using least square fitting of
        a Lorentz function on the data.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        kwargs : dict
            Not used; for backward-compatible API call only.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        IQCalcError
            Fitting failed.

        """
        N, X, Y, maxv = self._prep_for_fitting(arr1d, medv)

        # Lorentz model with initial guess
        m_init = models.Lorentz1D(
            amplitude=maxv, x_0=(N * 0.5), fwhm=(N * 0.25))

        # NOTE: without this mutex, optimize.leastsq causes a fatal error
        # sometimes--it appears not to be thread safe.
        # The error is:
        # "SystemError: null argument to internal routine"
        # "Fatal Python error: GC object already tracked"
        with self.lock:
            try:
                m = self.fitter(m_init, X, Y)
            except Exception:
                raise IQCalcError("FWHM Lorentz fitting failed")

        # Some routines choke on numpy values and need "pure" Python floats
        # e.g. when marshalling through a remote procedure interface
        fwhm = m.fwhm.value
        mu = m.x_0.value
        maxv = m.amplitude.value

        self.logger.debug('mu={} fwhm={} maxv={}'.format(mu, fwhm, maxv))

        res = Bunch.Bunch(fwhm=fwhm, mu=mu, maxv=maxv, fit_fn=self.lorentz,
                          fit_args=[mu, fwhm, maxv])
        return res

    def calc_fwhm(self, arr1d, medv=None, method_name='gaussian'):
        """Calculate FWHM for the given input array.

        Parameters
        ----------
        arr1d : array-like
            1D array cut in either X or Y direction on the object.

        medv : float or `None`
            Median of the data. If not given, it is calculated from ``arr1d``.

        method_name : {'gaussian', 'moffat', 'lorentz'}
            Function to use for fitting.

        Returns
        -------
        res : `~ginga.misc.Bunch.Bunch`
            Fitting results.

        Raises
        ------
        NotImplementedError
            Given function is not supported.

        """
        if method_name == 'gaussian':
            fwhm_fn = self.calc_fwhm_gaussian
        elif method_name == 'moffat':
            fwhm_fn = self.calc_fwhm_moffat
        elif method_name == 'lorentz':
            fwhm_fn = self.calc_fwhm_lorentz
        else:
            raise NotImplementedError(
                'Fitting with {} is unsupported'.format(method_name))

        return fwhm_fn(arr1d, medv=medv)

    def centroid(self, data, xc, yc, radius):
        if not have_photutils:
            raise IQCalcError("Please install the 'photutils' package "
                              "to use this function")

        x0, y0, arr = self.cut_region(int(xc), int(yc), int(radius), data)
        cx, cy = centroid_com(np.asarray(arr))  # Return (X, Y), not (Y, X)
        return (x0 + cx, y0 + cy)

    def find_bright_peaks(self, data, threshold=None, sigma=5, radius=5):
        if not have_photutils:
            raise IQCalcError("Please install the 'photutils' package "
                              "to use this function")

        if threshold is None:
            # set threshold to default if none provided
            threshold = self.get_threshold(data, sigma=sigma)
            self.logger.debug(f"threshold defaults to {threshold} (sigma={sigma})")

        if np.ma.is_masked(data):
            mask = data.mask
            data = data.data
        else:
            mask = None

        out_tab = find_peaks(data, threshold, box_size=(radius * 2), mask=mask)
        peaks = list(zip(out_tab['x_peak'], out_tab['y_peak']))

        self.logger.debug(f"peaks={peaks}")
        return peaks

    # TODO: Perhaps evaluate_peaks or pick_field can also use photutils.
    # https://github.com/astropy/photutils/issues/1074
