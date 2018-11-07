import numpy as np
import pytest

from ginga.util import iqcalc


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
