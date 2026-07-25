"""Unit tests for RGBMap.RGBMapper color-depth (resolution) handling.

These cover the decoupling of the pseudocolor *distribution resolution*
(``color_depth``) from the RGB *output* depth (``bpp``): the color/
intensity/distribution tables are sized to ``2 ** color_depth`` while the
produced RGB stays at ``2 ** bpp`` (8-bit for the display).
"""

import logging

import numpy as np
import pytest

from ginga.RGBMap import RGBMapper
from ginga.misc import Settings

logger = logging.getLogger('test_rgbmap')


def _mapper(bpp=8, color_depth=None, cmap='rainbow', algo='linear'):
    rgb = RGBMapper(logger, bpp=bpp, color_depth=color_depth)
    rgb.set_color_algorithm(algo)
    rgb.set_color_map(cmap)
    return rgb


def _distinct(rgb):
    """Number of distinct output colors across the whole index range."""
    n = rgb.get_hash_size()
    out = rgb.get_rgb_array(np.arange(n, dtype=np.uint32))
    return len(np.unique(out[:, :3], axis=0))


class TestColorDepth:

    def test_default_is_8bit(self):
        rgb = _mapper(bpp=8)
        assert rgb.bpp == 8 and rgb.color_depth == 8
        assert rgb.maxc == 255 and rgb.res_maxc == 255
        assert rgb.get_hash_size() == 256
        out = rgb.get_rgb_array(np.arange(256, dtype=np.uint32))
        assert out.dtype == np.uint8
        assert out[:, :3].max() <= 255

    def test_decoupled_resolution_keeps_8bit_output(self):
        rgb = _mapper(bpp=8, color_depth=12)
        # resolution is 12-bit, output stays 8-bit
        assert rgb.color_depth == 12
        assert rgb.res_maxc == 4095 and rgb.maxc == 255
        assert rgb.get_hash_size() == 4096
        out = rgb.get_rgb_array(np.arange(4096, dtype=np.uint32))
        assert out.dtype == np.uint8
        assert out[:, :3].max() <= 255

    def test_higher_depth_more_distinct_colors(self):
        # a colorful map gains many more distinct colors with higher depth
        d8 = _distinct(_mapper(color_depth=8, cmap='rainbow'))
        d12 = _distinct(_mapper(color_depth=12, cmap='rainbow'))
        assert d8 <= 256
        assert d12 > 2 * d8

    def test_gray_barely_affected_by_depth(self):
        # a short-RGB-path map (gray) can't gain much beyond 256 8-bit colors
        d8 = _distinct(_mapper(color_depth=8, cmap='gray'))
        d12 = _distinct(_mapper(color_depth=12, cmap='gray'))
        assert abs(d12 - d8) <= 5

    def test_color_depth_clamped_to_bpp(self):
        rgb = _mapper(bpp=8)
        rgb.set_color_depth(4)
        assert rgb.color_depth == 8 and rgb.res_maxc == 255

    def test_set_color_depth_preserves_colormap_and_roundtrips(self):
        rgb = _mapper(bpp=8, cmap='rainbow')
        d8 = _distinct(rgb)
        rgb.set_color_depth(12)
        d12 = _distinct(rgb)
        # color map preserved (still colorful) and resolution increased
        assert d12 > 2 * d8
        # going back reproduces the original 8-bit result exactly
        rgb.set_color_depth(8)
        assert _distinct(rgb) == d8

    def test_settings_drive_color_depth(self):
        st = Settings.SettingGroup(logger=logger)
        st.set(color_depth=12)
        rgb = RGBMapper(logger, settings=st)
        assert rgb.color_depth == 12 and rgb.res_maxc == 4095
        assert rgb.maxc == 255

    def test_output_stays_uint8_across_depths(self):
        for cd in (8, 10, 12, 16):
            rgb = _mapper(bpp=8, color_depth=cd)
            out = rgb.get_rgb_array(
                np.arange(rgb.get_hash_size(), dtype=np.uint32))
            assert out.dtype == np.uint8

    @pytest.mark.parametrize('bpp,out_dtype', [(8, np.uint8), (16, np.uint16)])
    def test_output_dtype_follows_bpp(self, bpp, out_dtype):
        rgb = _mapper(bpp=bpp)
        out = rgb.get_rgb_array(
            np.arange(rgb.get_hash_size(), dtype=np.uint32))
        assert out.dtype == out_dtype

    def test_get_rgb_index_range(self):
        rgb = _mapper(bpp=8, color_depth=12)
        # valid indices span the resolution range
        assert len(rgb.get_rgb(0)) == 3
        assert len(rgb.get_rgb(rgb.res_maxc)) == 3
        with pytest.raises(Exception):
            rgb.get_rgb(rgb.res_maxc + 1)
