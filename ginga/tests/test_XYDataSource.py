"""Unit Tests for some time series helper functions"""

import pytest
import numpy as np
from numpy.testing import assert_allclose

from ginga.plot.data_source import XYDataSource


class TestXYDataSource:

    def setup_class(self):
        self.n = 7
        self.test_pts = [(x, x**2) for x in range(0, self.n)]
        self.test_arr = np.array(self.test_pts, dtype=int)

    def test_initialize_points(self):
        expected = self.test_arr
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=expected)

        actual = dsrc.points
        assert_allclose(actual, expected)

    def test_set_points(self):
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int))

        expected = self.test_arr
        dsrc.set_points(expected)

        actual = dsrc.get_points()
        assert_allclose(actual, expected)

    def test_full_exception(self):
        expected = self.test_arr
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=expected, overwrite=False)

        with pytest.raises(ValueError):
            dsrc.add((8, 8**2))

    def test_is_full(self):
        expected = self.test_arr
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=expected, overwrite=False)

        assert dsrc.is_fullp()

    def test_overwrite(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        to_add = [(8, 8**2), (9, 9**2)]
        for pt in to_add:
            dsrc.add(pt)

        expected = np.array(points[len(to_add):] + to_add, dtype=int)
        actual = dsrc.get_points()
        assert_allclose(actual, expected)

    def test_add_points(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        to_add = [(8, 8**2), (9, 9**2)]
        dsrc.add_points(to_add)

        expected = np.array(points[len(to_add):] + to_add, dtype=int)
        actual = dsrc.get_points()
        assert_allclose(actual, expected)

    def test_peek(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        expected = points[-1]
        actual = dsrc.peek()
        assert_allclose(actual, expected)

    def test_peek_rear(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        expected = points[0]
        actual = dsrc.peek_rear()
        assert_allclose(actual, expected)

    def test_pop(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        expected = points[-1]
        actual = dsrc.pop()
        assert_allclose(actual, expected)

        assert len(dsrc.get_points()) == self.n - 1

    def test_pop_rear(self):
        points = self.test_pts
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=points, overwrite=True)

        expected = points[0]
        actual = dsrc.pop_rear()
        assert_allclose(actual, expected)

        assert len(dsrc.get_points()) == self.n - 1

    def test_points_property(self):
        expected = self.test_arr
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            points=expected, overwrite=True)

        actual = dsrc.points
        assert_allclose(actual, expected)

        assert len(dsrc) == self.n

    def test_limits(self):
        n = 100
        y_arr = np.random.randint(0, high=1000, size=n)
        x_arr = np.arange(0, n)
        points = np.array((x_arr, y_arr)).T
        dsrc = XYDataSource(np.zeros((n, 2), dtype=int),
                            points=points, overwrite=False)

        expected = np.array([(x_arr.min(), y_arr.min()),
                             (x_arr.max(), y_arr.max())])
        actual = dsrc.get_limits()
        assert_allclose(actual, expected)

    def test_empty_exception(self):
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            none_for_empty=False)

        with pytest.raises(ValueError):
            dsrc.peek()

        with pytest.raises(ValueError):
            dsrc.peek_rear()

        with pytest.raises(ValueError):
            dsrc.pop()

        with pytest.raises(ValueError):
            dsrc.pop_rear()

    def test_none_for_empty(self):
        dsrc = XYDataSource(np.zeros((self.n, 2), dtype=int),
                            none_for_empty=True)
        expected = None
        actual = dsrc.peek()
        assert actual == expected

        actual = dsrc.peek_rear()
        assert actual == expected

        actual = dsrc.pop()
        assert actual == expected

        actual = dsrc.pop_rear()
        assert actual == expected
