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

    def test_ColorMap_init_exception(self):
        self.assertRaises(TypeError, ColorMap, 'test-name')

    def test_cmap(self):
        count = 0
        for attribute_name in dir(ginga.cmap):
            if attribute_name.startswith('cmap_'):
                count = count + 1

        expected = count
        actual = len(ginga.cmap.cmaps)
        assert expected == actual

    def test_add_cmap(self):
        test_clst = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))

        ginga.cmap.add_cmap('test-name', test_clst)

        expected = ColorMap('test-name', test_clst)
        actual = ginga.cmap.cmaps['test-name']
        assert expected.name == actual.name
        assert expected.clst == actual.clst

        # Teardown
        del ginga.cmap.cmaps['test-name']

    def test_get_cmap(self):
        test_clst = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))

        ginga.cmap.add_cmap('test-name', test_clst)

        expected = ColorMap('test-name', test_clst)
        actual = ginga.cmap.get_cmap('test-name')
        assert expected.name == actual.name
        assert expected.clst == actual.clst

        # Teardown
        del ginga.cmap.cmaps['test-name']

    def test_get_cmap_exception(self):
        self.assertRaises(KeyError, ginga.cmap.get_cmap, 'non-existent-name')

    def test_get_names(self):
        names = []
        for attribute_name in dir(ginga.cmap):
            if attribute_name.startswith('cmap_'):
                names.append(attribute_name[5:])

        expected = sorted(names, key=lambda s: s.lower())
        actual = ginga.cmap.get_names()
        assert expected == actual

    # TODO: Add tests for matplotlib functions

    def tearDown(self):
        pass

if __name__ == '__main__':
    unittest.main()

# END
