"""Unit Tests for the ginga.util.mock_sky functions"""

import numpy as np

from ginga.util import mock_sky as ms


class TestMockSky(object):

    def setup_class(self):
        self.arr = np.zeros((150, 150), dtype=np.uint16)

    def test_add_bg(self):
        expected_mean = 2000
        expected_sdev = 15
        ms.add_bg(self.arr, expected_mean, expected_sdev)
        assert np.isclose(np.mean(self.arr), expected_mean, atol=1)
        assert np.isclose(np.std(self.arr), expected_sdev, atol=1)

    def test_add_star(self):
        ms.add_bg(self.arr, 2000, 15)
        expected_pos = (31.0, 74.1)
        ms.add_star(self.arr, expected_pos, 100.0, ellip=1.0)

    def test_mk_star_image(self):
        expected_num = 5
        locs = ms.mk_star_image(self.arr, expected_num)
        # should produce the number of expected stars
        assert len(locs) == expected_num
