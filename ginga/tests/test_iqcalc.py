import logging

import numpy as np
import pytest
from numpy.testing import assert_allclose, assert_array_equal

from ginga.AstroImage import AstroImage
from ginga.util import iqcalc, iqcalc_astropy
from ginga.util.iqcalc import have_scipy  # noqa
from ginga.util.iqcalc_astropy import have_photutils  # noqa


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
    assert_allclose(iqcalc.get_mean(m_arr), 5.0)


def test_get_median_mask():
    """Test that a partially masked array works with get_median()"""
    arr = np.array([-5, 4, 0, 3, 1, -2, 7, 10, -10, 5, 6, -1])
    m_arr = np.ma.masked_where(arr < 0, arr)
    assert_allclose(iqcalc.get_median(m_arr), 4.5)


class TestIQCalcNoInherit:
    """IQCalc tests that do not need corresponding tests for Astropy.
    If the method is re-implemented in iqcalc_astropy, move the test method
    to `TestIQCalc`.
    """
    def setup_class(self):
        logger = logging.getLogger("TestIQCalc")
        self.iqcalc = iqcalc.IQCalc(logger=logger)
        self.data = np.arange(100).reshape((10, 10))

    def test_starsize(self):
        fwhm = self.iqcalc.starsize(1.0, -1.6e-5, 3.5, 1.5e-5)
        assert_allclose(fwhm, 0.12329999999999999)

    def test_cut_region(self):
        x0, y0, arr = self.iqcalc.cut_region(5, 7, 5, self.data)
        assert (x0, y0) == (0, 2)
        assert_array_equal(arr, self.data[2:, :])

    def test_cut_cross(self):
        x0, y0, xarr, yarr = self.iqcalc.cut_cross(1, 4, 3, self.data)
        assert x0 == 0
        assert y0 == 1
        assert_array_equal(xarr, [40, 41, 42, 43, 44])
        assert_array_equal(yarr, [11, 21, 31, 41, 51, 61, 71])

    def test_brightness(self):
        assert_allclose(self.iqcalc.brightness(5, 4, 3, 0, self.data), 66)

    @pytest.mark.skipif('not have_scipy')
    def test_ee_odd(self):
        data = np.ma.array(
            [[0, 0, 0, 0, 0, 0, 0],
             [0, 1, 1, 1, 1, 1, 0],
             [0, 1, 1, 10, 1, 1, 0],
             [0, 1, 2, 3, 2, 1, 0],
             [0, 1, 1, 1, 1, 1, 0],
             [0, 1, 1, 1, 1, 1, 0],
             [0, 0, 0, 100, 0, 0, 0]],
            mask=[[False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False],
                  [False, False, False, True, False, False, False],
                  [False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False],
                  [False, False, False, True, False, False, False]])
        for fn in (self.iqcalc.ensquared_energy, self.iqcalc.encircled_energy):
            interp_fn = fn(data)
            assert_allclose(interp_fn.x, [0, 1, 2, 3])
            assert_allclose(interp_fn.y, [0.10714286, 0.42857143, 1, 1])

    @pytest.mark.skipif('not have_scipy')
    def test_ee_even(self):
        data = np.ma.array(
            [[0, 0, 0, 0, 0, 0, 0, 0],
             [0, 1, 1, 1, 1, 1, 1, 0],
             [0, 1, 2, 2, 2, 2, 1, 0],
             [0, 1, 2, 3, 10, 2, 1, 0],
             [0, 1, 2, 3, 3, 2, 1, 0],
             [0, 1, 2, 2, 2, 2, 1, 0],
             [0, 1, 1, 1, 1, 1, 1, 0],
             [0, 0, 0, 100, 0, 0, 0, 0]],
            mask=[[False, False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False, False],
                  [False, False, False, False, True, False, False, False],
                  [False, False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False, False],
                  [False, False, False, False, False, False, False, False],
                  [False, False, False, True, False, False, False, False]])
        fn_sq = self.iqcalc.ensquared_energy(data)
        assert_allclose(fn_sq.x, [0, 1, 2, 3])
        assert_allclose(fn_sq.y, [0.16981132, 0.62264151, 1, 1])
        fn_circ = self.iqcalc.encircled_energy(data)
        assert_allclose(fn_circ.x, [0, 1, 2, 3])
        assert_allclose(fn_circ.y, [0.16981132, 0.47169811, 0.9245283, 1])


@pytest.mark.skipif('not have_scipy')
class TestIQCalcPhot:
    # Shared attributes that subclass can access.
    logger = logging.getLogger("TestIQCalc")
    # This is taken from subset of array mentioned in
    # https://photutils.readthedocs.io/en/stable/detection.html#detecting-stars
    data = np.array(
        [[3961, 4143, 3780, 3871, 3871, 3871, 3508, 3780, 3780, 3780, 3780],
         [3961, 3961, 3598, 3961, 3961, 3780, 3780, 3780, 3780, 3780, 3780],
         [3961, 3961, 3598, 3961, 3961, 4143, 4143, 3780, 3780, 3780, 3780],
         [3780, 3961, 3961, 4143, 4506, 5776, 5413, 3961, 3961, 3961, 3961],
         [3780, 3961, 3961, 4143, 5232, 9043, 7954, 4687, 3961, 3598, 3598],
         [3939, 4302, 4302, 4211, 5300, 7659, 6933, 4710, 3984, 3621, 3621],
         [3939, 3939, 3939, 3848, 4211, 4392, 4392, 3984, 3984, 3621, 3621],
         [3757, 3757, 3757, 4029, 3666, 4029, 3666, 3803, 3803, 3621, 3621],
         [3757, 3757, 3757, 3666, 4029, 4029, 3666, 3803, 3803, 3621, 3621],
         [4120, 3939, 3576, 3757, 3757, 3576, 3576, 3712, 3712, 3530, 3530],
         [4120, 3939, 3576, 3757, 3757, 3576, 3576, 3712, 3712, 3530, 3530]])
    # This is taken from photutils find_peaks test.
    PEAKDATA = np.array([[1, 0, 0], [0, 0, 0], [0, 0, 1]]).astype(float)
    PEAKREF1 = [(0, 0), (2, 2)]

    def setup_class(self):
        self.iqcalc = iqcalc.IQCalc(logger=self.logger)

    def test_centroid(self):
        # We are not testing cut region here, so we use all the data.
        xycen = self.iqcalc.centroid(self.data, 5, 5, 5)
        assert_allclose(xycen, (4.960327886939483, 4.922639686006575))

    def test_find_bright_peaks_default_pars(self):
        # Also tests get_threshold indirectly.
        peaks = self.iqcalc.find_bright_peaks(self.data)
        max_xy = [(5, 4)]
        assert_array_equal(peaks, max_xy)

    def test_find_bright_peaks_no_mask(self):
        peaks = self.iqcalc.find_bright_peaks(
            self.PEAKDATA, threshold=0.1, radius=1)
        assert_array_equal(peaks, self.PEAKREF1)

    def test_find_bright_peaks_masked(self):
        mask = np.zeros(self.PEAKDATA.shape, dtype=bool)
        mask[0, 0] = True
        data = np.ma.array(self.PEAKDATA, mask=mask)
        peaks = self.iqcalc.find_bright_peaks(data, threshold=0.1, radius=1)
        assert_array_equal(peaks, [self.PEAKREF1[1]])

    def test_fwhm_data(self):
        fwhm_x, fwhm_y, ctr_x, ctr_y, x_res, y_res = self.iqcalc.fwhm_data(
            5, 4, self.data, radius=3, method_name='gaussian')
        # Relax tolerance for TestIQCalcPhotAstropy
        assert_allclose(fwhm_x, 1.9671665379707803, rtol=2e-7)
        assert_allclose(fwhm_y, 2.054971090163851, rtol=2e-7)
        assert_allclose(ctr_x, 5.353724230524191, rtol=2e-7)
        assert_allclose(ctr_y, 4.248692873436124, rtol=2e-7)
        assert_allclose(x_res['sdev'], 0.8353787127478465, rtol=2e-7)
        assert_allclose(y_res['sdev'], 0.8726658729188976, rtol=2e-7)

    def test_photometry(self):
        objlist = self.iqcalc.evaluate_peaks(
            [(5, 4)], self.data, fwhm_radius=1.5, ee_total_radius=3)
        assert len(objlist) == 1
        result_1 = objlist[0]

        result_2 = self.iqcalc.pick_field(
            self.data, fwhm_radius=1.5, ee_total_radius=3)

        astroim = AstroImage(data_np=self.data, logger=self.iqcalc.logger)
        result_3 = self.iqcalc.qualsize(
            astroim, fwhm_radius=1.5, ee_total_radius=3)

        # Relax tolerance for TestIQCalcPhotAstropy
        for res in (result_1, result_2, result_3):
            assert_allclose(res.objx, 5.353330481192139)
            assert_allclose(res.objy, 4.2480576624213455)
            assert_allclose(res.pos, 0.9967616536846655)
            assert_allclose(res.oid_x, 5.091012868410129)
            assert_allclose(res.oid_y, 4.072592361975923)
            assert_allclose(res.fwhm_x, 1.9625726210572922, rtol=5e-7)
            assert_allclose(res.fwhm_y, 2.0491919125821827, rtol=5e-7)
            assert_allclose(res.fwhm, 2.0063497685493314, rtol=5e-7)
            assert res.fwhm_radius == 1.5
            assert_allclose(res.brightness, 5234.639533977552)
            assert_allclose(res.elipse, 0.9577300247024001, rtol=1e-6)
            assert res.x == 5
            assert res.y == 4
            assert_allclose(res.skylevel, 4033.15)
            assert_allclose(res.background, 3803)
            assert_allclose(res.encircled_energy_fn(1.5), 0.88921253)
            assert_allclose(res.ensquared_energy_fn(1.5), 0.88976561)

        result_4 = self.iqcalc.qualsize(astroim, x1=1, y1=1, x2=10, y2=10, fwhm_radius=1.5, minfwhm=1.8)

        # A bit different for result_4 due to slightly truncated data.
        # Relax tolerance for TestIQCalcPhotAstropy
        assert_allclose(result_4.objx, 5.35505379856564)
        assert_allclose(result_4.objy, 4.25153281221611)
        assert_allclose(result_4.pos, 0.9951892891389722)
        assert_allclose(result_4.oid_x, 4.091012868410129)
        assert_allclose(result_4.oid_y, 3.072592361975923)
        assert_allclose(result_4.fwhm_x, 1.8788622094597287, rtol=5e-7)
        assert_allclose(result_4.fwhm_y, 1.9727658817644915, rtol=5e-7)
        assert_allclose(result_4.fwhm, 1.926386309439247, rtol=5e-7)
        assert result_4.fwhm_radius == 1.5
        assert_allclose(result_4.brightness, 5097.983320858308)
        assert_allclose(result_4.elipse, 0.9523999917208762, rtol=1e-6)
        assert result_4.x == 5
        assert result_4.y == 4
        assert_allclose(result_4.skylevel, 4199.05)
        assert_allclose(result_4.background, 3961)
        assert result_4.encircled_energy_fn is None
        assert result_4.ensquared_energy_fn is None

        result = self.iqcalc.objlist_select(
            objlist, self.data.shape[1], self.data.shape[0])
        assert len(result) == 1

        result = self.iqcalc.objlist_select(
            objlist, self.data.shape[1], self.data.shape[0], minfwhm=1.0, maxfwhm=2.0)
        assert len(result) == 0


# NOTE: Inherited test methods also must satisfy inherited dependency checks
# from parent test class above. Not ideal if dependency is different but
# this avoids test code repetition.
@pytest.mark.skipif('not have_photutils')
class TestIQCalcPhotAstropy(TestIQCalcPhot):
    def setup_class(self):
        """Customize for Astropy implementation."""
        self.iqcalc = iqcalc_astropy.IQCalc(logger=self.logger)


@pytest.mark.skipif('not have_scipy')
class TestIQCalcFWHM:
    # Shared attributes that subclass can access.
    logger = logging.getLogger("TestIQCalc")
    input_arrays = (
        np.array([0., 0., 11., 12., 8., 9., 37., 96., 289., 786.,
                  1117., 795., 286., 86., 26., 18., 0., 8., 0., 0.]),
        np.array([0., 9., 0., 0., 0., 34., 25., 60., 196., 602.,
                  1117., 1003., 413., 135., 29., 0., 3., 0., 4., 3.]))

    def setup_class(self):
        self.iqcalc = iqcalc.IQCalc(logger=self.logger)
        self.fwhm_funcs = (self.iqcalc.calc_fwhm_gaussian,
                           self.iqcalc.calc_fwhm_moffat)
        self.answers = ((2.8551, 2.7732),  # Gaussian
                        (2.77949, 2.6735)  # Moffat
                        )

    def test_fwhm(self):
        """Test FWHM measuring function in 1D."""
        for i, func in enumerate(self.fwhm_funcs):
            for j, arr1d in enumerate(self.input_arrays):
                res = func(arr1d)
                assert_allclose(res.fwhm, self.answers[i][j], atol=1e-4)


class TestIQCalcFWHMAstropy(TestIQCalcFWHM):
    def setup_class(self):
        """Customize for Astropy implementation."""
        self.iqcalc = iqcalc_astropy.IQCalc(logger=self.logger)
        self.fwhm_funcs = (self.iqcalc.calc_fwhm_gaussian,
                           self.iqcalc.calc_fwhm_moffat,
                           self.iqcalc.calc_fwhm_lorentz)
        self.answers = ((2.8551, 2.7732),  # Gaussian
                        (2.77949, 2.6735),  # Moffat
                        (1.9570, 1.8113)  # Lorentz
                        )
