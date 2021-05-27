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

        # TODO: encapsulate this drawable
        self.cr = CvHelp.CvContext(surface)

        self.pen = None
        self.brush = None
        self.font = None

    def set_line_from_shape(self, shape):
        # TODO: support line width and style
        alpha = getattr(shape, 'alpha', 1.0)
        self.pen = self.cr.get_pen(shape.color, alpha=alpha)

    def set_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                color = shape.fillcolor
            else:
                color = shape.color
            alpha = getattr(shape, 'alpha', 1.0)
            alpha = getattr(shape, 'fillalpha', alpha)
            self.brush = self.cr.get_brush(color, alpha=alpha)
        else:
            self.brush = None

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if (hasattr(shape, 'fontsize') and shape.fontsize is not None and
                not getattr(shape, 'fontscale', False)):
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            fontsize = self.scale_fontsize(fontsize)
            alpha = getattr(shape, 'alpha', 1.0)
            self.font = self.cr.get_font(shape.font, fontsize, shape.color,
                                         alpha=alpha)
        else:
            self.font = None

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        # TODO: support style
        self.pen = self.cr.get_pen(color, linewidth=linewidth, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontsize = self.scale_fontsize(fontsize)
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)

    def setup_pen_brush(self, pen, brush):
        if pen is not None:
            self.set_line(pen.color, alpha=pen.alpha, linewidth=pen.linewidth,
                          style=pen.linestyle)

        if brush is None:
            self.brush = None
        else:
            self.set_fill(brush.color, alpha=brush.alpha)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.text((cx, cy), text, self.font)

    def draw_polygon(self, cpoints):
        cpoints = trcalc.strip_z(cpoints)
        self.cr.polygon(cpoints, self.pen, self.brush)

    def draw_circle(self, cx, cy, cradius):
        self.cr.circle((cx, cy), cradius, self.pen, self.brush)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.line((cx1, cy1), (cx2, cy2), self.pen)

    def draw_path(self, cpoints):
        cpoints = trcalc.strip_z(cpoints)
        self.cr.path(cpoints, self.pen)


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
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font(font.fontname, font.fontsize, color=font.color,
                    alpha=font.alpha)
        return cr.text_extents(text)

#END
