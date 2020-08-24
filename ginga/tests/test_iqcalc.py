import logging
import numpy as np
import pytest

from ginga.util import iqcalc

try:
    from scipy import optimize  # noqa
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@pytest.mark.parametrize(
    ('arr', 'ans'),
    [(np.arange(5), 2),
     (np.array([1, np.inf, 3, np.nan, 5]), 3),
     (np.arange(10).reshape(2, 5), 4.5)])
def test_get_mean_median(arr, ans):
    assert iqcalc.get_mean(arr) == ans
    assert iqcalc.get_median(arr) == ans


def test_get_mean_median_nan():
    arr = np.array([np.nan, np.inf])
    assert np.isnan(iqcalc.get_mean(arr))
    assert np.isnan(iqcalc.get_median(arr))


def test_get_mean_mask():
    """Test that a partially masked array works with get_mean()"""
    arr = np.array([-5, 4, 0, 3, -2, 7, 10, -10, 5, 6])
    m_arr = np.ma.masked_where(arr < 0, arr)
    assert np.isclose(iqcalc.get_mean(m_arr), 5.0)


def test_get_median_mask():
    """Test that a partially masked array works with get_median()"""
    arr = np.array([-5, 4, 0, 3, 1, -2, 7, 10, -10, 5, 6, -1])
    m_arr = np.ma.masked_where(arr < 0, arr)
    assert np.isclose(iqcalc.get_median(m_arr), 4.5)


@pytest.mark.skipif('not HAS_SCIPY')
class TestIQCalc:

    def setup_class(self):
        logger = logging.getLogger("TestIQCalc")
        self.iqcalc = iqcalc.IQCalc(logger=logger)

    def test_fwhm_gaussian(self):
        """Test FHWM gaussian measuring function in 1D."""
        x = np.array([0., 0., 11., 12., 8., 9., 37., 96., 289., 786.,
                      1117., 795., 286., 86., 26., 18., 0., 8., 0., 0.])
        y = np.array([0., 9., 0., 0., 0., 34., 25., 60., 196., 602.,
                      1117., 1003., 413., 135., 29., 0., 3., 0., 4., 3.])

        res = self.iqcalc.calc_fwhm_gaussian(x)
        assert np.isclose(res.fwhm, 2.8551, atol=1e-04)
        res = self.iqcalc.calc_fwhm_gaussian(y)
        assert np.isclose(res.fwhm, 2.7732, atol=1e-04)

    def test_fwhm_moffat(self):
        """Test FWHM moffat measuring function in 1D."""
        x = np.array([0., 0., 11., 12., 8., 9., 37., 96., 289., 786.,
                      1117., 795., 286., 86., 26., 18., 0., 8., 0., 0.])
        y = np.array([0., 9., 0., 0., 0., 34., 25., 60., 196., 602.,
                      1117., 1003., 413., 135., 29., 0., 3., 0., 4., 3.])

        res = self.iqcalc.calc_fwhm_moffat(x)
        assert np.isclose(res.fwhm, 2.77949, atol=1e-04)
        res = self.iqcalc.calc_fwhm_moffat(y)
        assert np.isclose(res.fwhm, 2.6735, atol=1e-04)
