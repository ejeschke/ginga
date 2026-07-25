"""Unit Tests for the cmap.py functions"""

import numpy as np
import pytest

import ginga.cmap
from ginga.cmap import ColorMap


class TestCmap:

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
        # a ColorMap needs one of clst / ctrl_pts / fn
        from ginga.cmap import ColorMapError
        with pytest.raises(ColorMapError):
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
        # a colormap now accepts any length >= 2 (interpolated as needed);
        # fewer than 2 entries is the error case
        test_clst = ((0.5, 0.5, 0.5), )
        with pytest.raises(ValueError):
            ginga.cmap.add_cmap('test-name', test_clst)

    def test_add_cmap_two_entries(self):
        # a 2-entry map is valid and interpolates to any resolution
        ginga.cmap.add_cmap('test-2', ((0.0, 0.0, 0.0), (1.0, 1.0, 1.0)))
        cm = ginga.cmap.cmaps['test-2']
        mid = cm.get_colors(3)[1]
        assert np.allclose(mid, (0.5, 0.5, 0.5))
        del ginga.cmap.cmaps['test-2']

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


class TestColorMapResolution:
    """Resolution-independent sampling via ColorMap.get_colors()."""

    def test_get_colors_identity(self):
        # sampling a discrete map at its own length returns it unchanged
        cm = ginga.cmap.get_cmap('rainbow')
        got = cm.get_colors(ginga.cmap.min_cmap_len)
        ref = np.asarray(cm.clst, dtype=float)[:, :3]
        assert got.shape == ref.shape
        np.testing.assert_allclose(got, ref)

    def test_get_colors_interpolates(self):
        cm = ginga.cmap.get_cmap('rainbow')
        clst = np.asarray(cm.clst, dtype=float)
        hi = cm.get_colors(65536)
        assert hi.shape == (65536, 3)
        # endpoints preserved; values stay in range
        np.testing.assert_allclose(hi[0], clst[0, :3])
        np.testing.assert_allclose(hi[-1], clst[-1, :3])
        assert hi.min() >= 0.0 and hi.max() <= 1.0

    def test_from_control_points(self):
        cm = ColorMap.from_control_points(
            'cp', [(0.0, (0, 0, 0)), (0.5, (1, 0, 0)), (1.0, (1, 1, 1))])
        c = cm.get_colors(5)
        np.testing.assert_allclose(c[0], (0, 0, 0))
        np.testing.assert_allclose(c[2], (1, 0, 0))     # midpoint control
        np.testing.assert_allclose(c[4], (1, 1, 1))
        # a discrete .clst is derived for backward compatibility
        assert len(cm.clst) == ginga.cmap.min_cmap_len

    def test_from_function(self):
        cm = ColorMap.from_function(
            'fn', lambda x: np.stack([x, x, x], axis=-1))
        c = cm.get_colors(3)
        np.testing.assert_allclose(c, [(0, 0, 0), (0.5, 0.5, 0.5),
                                       (1, 1, 1)])

    def test_matplotlib_cmap_smooth_and_mpl_free(self):
        mpl = pytest.importorskip('matplotlib')
        if not ginga.cmap.has_cmap('viridis'):
            pytest.skip('viridis not registered')
        cm = ginga.cmap.get_cmap('viridis')
        # captured as a discrete list -- retains no matplotlib reference
        assert cm._fn is None
        # 256-sample reproduces matplotlib's native lookup table
        old = mpl.colormaps['viridis'](np.arange(256) / 255.0)[:, :3]
        np.testing.assert_allclose(cm.get_colors(256), old, atol=1e-12)
        # interpolates to higher resolution (not re-quantized to 256)
        assert len(np.unique(cm.get_colors(65536), axis=0)) > 256

# END
