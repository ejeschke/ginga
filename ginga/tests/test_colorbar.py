"""Tests for the canvas ColorBar rendering across color depths.

The color bar must render the *whole* color map regardless of the
distribution resolution (``color_depth``), and must not draw more color
swatches than the bar is wide (which would be both wrong and slow at
color depths > 8).
"""

import logging

import numpy as np

from ginga.pilw.ImageViewPil import CanvasView
from ginga.canvas.types import utils
from ginga import cmap as gcmap


class TestColorBar:

    def setup_class(self):
        self.logger = logging.getLogger("TestColorBar")

    def _make_viewer(self, width=512, height=36, cmap='rainbow'):
        v = CanvasView(logger=self.logger)
        v.configure_surface(width, height)
        v.enable_autozoom('off')
        v.enable_autocuts('off')
        v.cut_levels(0.0, 100.0)
        rgbmap = v.get_rgbmap()
        rgbmap.set_cmap(gcmap.get_cmap(cmap))
        cbar = utils.ColorBar(offset=0, height=height, rgbmap=rgbmap,
                              showrange=False)
        v.get_canvas().add(cbar, tag='colorbar')
        return v, rgbmap

    def _mid_row(self, v):
        v.redraw_now(whence=0)
        arr = v.get_image_as_array()[:, :, :3]
        return arr[arr.shape[0] // 2]

    def test_spans_full_colormap_at_all_depths(self):
        # the ends of the bar are the ends of the color map, regardless
        # of color depth
        v, rgbmap = self._make_viewer()
        rgbmap.set_color_depth(8)
        row8 = self._mid_row(v)
        first8, last8 = row8[0].astype(int), row8[-1].astype(int)
        # The ends must land on the *same ends of the color map* at every
        # depth.  We allow a small tolerance rather than exact equality: the
        # map is sampled at a different resolution per depth and the very last
        # pixel column is subject to rasterization rounding, so the endpoint
        # color can wobble by a few levels across platforms.  The original bug
        # (only ~1/16 of the map shown) put the far end on a completely
        # different hue, hundreds of levels away, so this still catches it.
        for depth in (10, 12, 16):
            rgbmap.set_color_depth(depth)
            row = self._mid_row(v)
            assert np.allclose(row[0].astype(int), first8, atol=16)
            assert np.allclose(row[-1].astype(int), last8, atol=16)

    def test_higher_depth_shows_more_distinct_colors(self):
        # a wide bar reveals more of a colorful map's gradient at higher depth
        v, rgbmap = self._make_viewer(width=512, cmap='rainbow')
        rgbmap.set_color_depth(8)
        d8 = len(np.unique(self._mid_row(v), axis=0))
        rgbmap.set_color_depth(12)
        d12 = len(np.unique(self._mid_row(v), axis=0))
        assert d12 > d8

    def test_swatches_bounded_by_bar_width(self):
        # distinct colors can never exceed the bar's pixel width, even at
        # very high color depth (this is what keeps drawing fast)
        width = 300
        v, rgbmap = self._make_viewer(width=width, cmap='rainbow')
        rgbmap.set_color_depth(16)
        distinct = len(np.unique(self._mid_row(v), axis=0))
        assert distinct <= width

    def test_showrange_renders_without_error(self):
        v = CanvasView(logger=self.logger)
        v.configure_surface(512, 48)
        v.enable_autozoom('off')
        v.enable_autocuts('off')
        v.cut_levels(0.0, 100.0)
        rgbmap = v.get_rgbmap()
        rgbmap.set_cmap(gcmap.get_cmap('rainbow'))
        cbar = utils.ColorBar(offset=0, height=36, rgbmap=rgbmap,
                              showrange=True)
        v.get_canvas().add(cbar, tag='colorbar')
        for depth in (8, 12, 16):
            rgbmap.set_color_depth(depth)
            v.redraw_now(whence=0)
            # just assert we produced an image of the expected shape
            arr = v.get_image_as_array()
            assert arr.shape[0] > 0 and arr.shape[1] == 512
