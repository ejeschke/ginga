#
# CanvasRenderCv.py -- for rendering into a Ginga widget with OpenCv
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy as np

import cv2  # noqa
from . import CvHelp

from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # special scaling for Cv text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.33

        # TODO: encapsulate this drawable
        self.ctx = CvHelp.CvContext(surface)

    def get_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        line = super().get_line(color, alpha=alpha, linewidth=linewidth,
                                linestyle=linestyle)

        line.render.color = line.get_bpp_color(8)
        return line

    def get_fill(self, color, alpha=1.0):
        fill = super().get_fill(color, alpha=alpha)

        fill.render.color = fill.get_bpp_color(8)
        return fill

    def get_font(self, fontname, **kwargs):
        font = super().get_font(fontname, **kwargs)

        font.render.scale = int(round(font.fontsize * self._font_scale_factor))
        font.render.font = CvHelp.get_cached_font(font.fontname, font.fontsize)
        return font

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        _font, _scale = font.render.font, font.render.scale
        retval, baseline = _font.getTextSize(text, _scale, -1)
        wd_px, ht_px = retval
        return wd_px, ht_px

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        self.ctx.text((cx, cy), text, font, line, fill)

    def draw_polygon(self, cpoints, line=None, fill=None):
        cpoints = trcalc.strip_z(cpoints)
        self.ctx.polygon(cpoints, line, fill)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        self.ctx.circle((cx, cy), cradius, line, fill)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        self.ctx.line((cx1, cy1), (cx2, cy2), line)

    def draw_path(self, cpoints, line=None):
        cpoints = trcalc.strip_z(cpoints)
        self.ctx.path(cpoints, line)


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'opencv'
        # According to OpenCV documentation:
        # "If you are using your own image rendering and I/O functions,
        # you can use any channel ordering. The drawing functions process
        # each channel independently and do not depend on the channel
        # order or even on the used color space."
        # NOTE: OpenCv does not seem to be happy using anti-aliasing on
        # transparent arrays
        self.rgb_order = 'RGB'
        self.surface = None
        self.dims = ()

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))

        # create cv surface the size of the window
        # (cv just uses numpy arrays!)
        depth = len(self.rgb_order)
        self.surface = np.zeros((height, width, depth), dtype=np.uint8)

        super(CanvasRenderer, self).resize(dims)

    def render_image(self, rgb_arr, order, win_coord):
        """Render the image represented by (rgb_arr) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        if self.surface is None:
            return
        self.logger.debug("redraw surface")

        # TODO: is there a faster way to copy this array in?
        self.surface[:, :, :] = rgb_arr[:, :, 0:3]

    def get_surface_as_array(self, order=None):
        if self.surface is None:
            raise render.RenderError("No OpenCv surface defined")

        # adjust according to viewer's needed order
        return self.reorder(order, self.surface)

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font(font.fontname, font.fontsize)
        return cr.text_extents(text)

#END
