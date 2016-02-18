#
# Unit Tests for the colors.py functions
#
# Rajul Srivastava  (rajul09@gmail.com)
#
import unittest
import logging
import numpy as np

import ginga.cmap
from ginga.cmap import ColorMap


class TestError(Exception):
    pass


class TestCmap(unittest.TestCase):

    def setUp(self):
        pass

    def test_ColorMap_init(self):
        test_clst = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        test_color_map = ColorMap('test-name', test_clst)

        expected = 'test-name'
        actual = test_color_map.name
        assert expected == actual

        expected = 2
        actual = len(test_color_map.clst)
        assert expected == actual

        expected = (0.0, 0.0, 0.0)
        actual = test_color_map.clst[0]
        assert np.allclose(expected, actual)

        expected = (1.0, 1.0, 1.0)
        actual = test_color_map.clst[1]
        assert np.allclose(expected, actual)

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# END
