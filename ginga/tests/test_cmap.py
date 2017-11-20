"""Unit Tests for the cmap.py functions"""

import numpy as np
import pytest

import ginga.cmap
from ginga.cmap import ColorMap


class TestCmap(object):

    def setup_class(self):
        pass

    def test_ColorMap_init(self):
        test_clst = tuple([(x, x, x)
                           for x in np.linspace(0, 1, ginga.cmap.min_cmap_len)])
        test_color_map = ColorMap('test-name', test_clst)

        expected = 'test-name'
        actual = test_color_map.name
        assert expected == actual

        expected = ginga.cmap.min_cmap_len
        actual = len(test_color_map.clst)
        assert expected == actual

        expected = (0.0, 0.0, 0.0)
        actual = test_color_map.clst[0]
        assert np.allclose(expected, actual)

        expected = (1.0, 1.0, 1.0)
        actual = test_color_map.clst[-1]
        assert np.allclose(expected, actual)

    def test_ColorMap_init_exception(self):
        with pytest.raises(TypeError):
            ColorMap('test-name')

    def test_cmaps(self):
        count = 0
        for attribute_name in dir(ginga.cmap):
            if attribute_name.startswith('cmap_'):
                count = count + 1

        expected = count
        actual = len(ginga.cmap.cmaps)  # Can include matplotlib colormaps
        assert expected <= actual

    def test_add_cmap(self):
        test_clst = tuple([(x, x, x)
                           for x in np.linspace(0, 1, ginga.cmap.min_cmap_len)])
        ginga.cmap.add_cmap('test-name', test_clst)

        expected = ColorMap('test-name', test_clst)
        actual = ginga.cmap.cmaps['test-name']
        assert expected.name == actual.name
        assert expected.clst == actual.clst

        # Teardown
        del ginga.cmap.cmaps['test-name']

    def test_add_cmap_exception(self):
        test_clst = ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0))
        with pytest.raises(AssertionError):
            ginga.cmap.add_cmap('test-name', test_clst)

    def test_get_cmap(self):
        test_clst = tuple([(x, x, x)
                           for x in np.linspace(0, 1, ginga.cmap.min_cmap_len)])
        ginga.cmap.add_cmap('test-name', test_clst)

        expected = ColorMap('test-name', test_clst)
        actual = ginga.cmap.get_cmap('test-name')
        assert expected.name == actual.name
        assert expected.clst == actual.clst

        # Teardown
        del ginga.cmap.cmaps['test-name']

    def test_get_cmap_exception(self):
        with pytest.raises(KeyError):
            ginga.cmap.get_cmap('non-existent-name')

    def test_get_names(self):
        names = []
        for attribute_name in dir(ginga.cmap):
            if attribute_name.startswith('cmap_'):
                names.append(attribute_name[5:])

        expected = set(names)
        actual = set(ginga.cmap.get_names())  # Can include matplotlib names
        assert expected <= actual

    # TODO: Add tests for matplotlib functions

# END
