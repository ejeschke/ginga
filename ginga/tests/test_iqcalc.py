import numpy as np
import pytest

from ginga.misc import log
from ginga.util import iqcalc
from ginga.util import mock_sky as ms

try:
    import scipy   # noqa
    have_scipy = True
except ImportError:
    have_scipy = False


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


class Test_IQCalc(object):

    def setup_class(self):
        self.arr = np.zeros((100, 100), dtype=np.float)
        self.logger = log.NullLogger()
        self.iqcalc = iqcalc.IQCalc(logger=self.logger)

    def set_bg(self, arr, bg_mean):
        arr.fill(bg_mean)

    def test_cut_region(self):
        pos = (35, 55)
        x0, y0, cutout = self.iqcalc.cut_region(pos[0], pos[1], 10, self.arr)
        # (x0, y0) is corner of cutout
        assert (x0, y0) == (25, 45)
        assert cutout.shape == (21, 21)

    def test_cut_cross(self):
        pos = (35, 55)
        x0, y0, xarr, yarr = self.iqcalc.cut_cross(pos[0], pos[1], 10,
                                                   self.arr)
        assert x0 == 25 and y0 == 45
        assert xarr.shape == (21,) and yarr.shape == (21,)

    @pytest.mark.skipif(not have_scipy, reason="requires scipy package")
    def test_centroid(self):
        self.set_bg(self.arr, 2000)
        pos = (50, 50)
        ms.add_star(self.arr, pos, 100.0, ellip=1.0)

        xc, yc = self.iqcalc.centroid(self.arr, pos[0], pos[1], 10)
        assert (np.isclose(xc, pos[0], atol=0.1) and
                np.isclose(yc, pos[1], atol=0.1))

    def test_get_threshold(self):
        self.set_bg(self.arr, 2000.0)
        pos = (31.7, 64.1)
        ms.add_star(self.arr, pos, 100.0, ellip=1.0)
        th = self.iqcalc.get_threshold(self.arr)
        assert np.isclose(th, 2001.25, atol=0.1)

    @pytest.mark.skipif(not have_scipy, reason="requires scipy package")
    def test_get_fwhm(self):
        self.set_bg(self.arr, 2000.0)
        pos = (31, 64)
        ms.add_star(self.arr, pos, 400.0, ellip=1.0)
        res = self.iqcalc.get_fwhm(pos[0], pos[1], 10, self.arr)
        # star fwhm roughly matches
        assert (np.isclose(res[0], 4.71, atol=0.1) and
                np.isclose(res[1], 4.71, atol=0.1))

    @pytest.mark.skipif(not have_scipy, reason="requires scipy package")
    def test_pick_field(self):
        self.set_bg(self.arr, 2000.0)
        pos = (31.0, 64.0)
        ms.add_star(self.arr, pos, 100.0, ellip=1.0)
        obj = self.iqcalc.pick_field(self.arr)
        assert (np.isclose(obj.objx, pos[0], atol=0.1) and
                np.isclose(obj.objy, pos[1], atol=0.1))
        # star fwhm roughly matches
        assert (np.isclose(obj.fwhm_x, 4.71, atol=0.1) and
                np.isclose(obj.fwhm_y, 4.71, atol=0.1))
