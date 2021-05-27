#
# CanvasRenderPil.py -- for rendering into a Ginga widget with pillow
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import numpy as np

from PIL import Image

from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc

from . import PilHelp


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # TODO: encapsulate this drawable
        self.cr = PilHelp.PilContext(surface)

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
            alpha = getattr(shape, 'alpha', 1.0)
            fontsize = self.scale_fontsize(fontsize)
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
        # TODO: support line width and style
        self.pen = self.cr.get_pen(color, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def setup_pen_brush(self, pen, brush):
        # pen, brush are from ginga.vec
        self.pen = self.cr.get_pen(pen.color, alpha=pen.alpha,
                                   linewidth=pen.linewidth)
        if brush is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(brush.color, alpha=brush.alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontsize = self.scale_fontsize(fontsize)
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)

    def get_affine_transform(self, cx, cy, rot_deg):
        x, y = 0, 0          # old center
        nx, ny = cx, cy      # new center
        sx = sy = 1.0        # new scale
        cosine = math.cos(math.radians(rot_deg))
        sine = math.sin(math.radians(rot_deg))
        a = cosine / sx
        b = sine / sx
        c = x - nx * a - ny * b
        d = -sine / sy
        e = cosine / sy
        f = y - nx * d - ny * e
        return (a, b, c, d, e, f)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        wd, ht = self.cr.text_extents(text, self.font)

        # NOTE: rotation ignored in PIL, for now
        self.cr.text((cx, cy - ht), text, self.font, self.pen)

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

        self.kind = 'pil'
        self.rgb_order = 'RGBA'
        self.surface = None
        self.dims = ()

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))

        # create PIL surface the size of the window
        # NOTE: pillow needs an RGB surface in order to draw with alpha
        # blending, not RGBA
        self.surface = Image.new('RGB', (width, height), color=0)

        super(CanvasRenderer, self).resize(dims)

    ## def finalize(self):
    ##     cr = RenderContext(self, self.viewer, self.surface)
    ##     self.draw_vector(cr)

    def render_image(self, rgb_arr, order, win_coord):
        """Render the image represented by (data) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        if self.surface is None:
            return
        self.logger.debug("redraw surface")

        # get window contents as a buffer and paste it into the PIL surface
        # TODO: allow greater bit depths when support is better in PIL
        p_image = Image.fromarray(rgb_arr)

        if self.surface is None or p_image.size != self.surface.size:
            # window size must have changed out from underneath us!
            width, height = self.viewer.get_window_size()
            self.resize((width, height))
            if p_image.size != self.surface.size:
                raise render.RenderError("Rendered image does not match window size")

        self.surface.paste(p_image)

    def get_surface_as_array(self, order=None):
        if self.surface is None:
            raise render.RenderError("No PIL surface defined")

        # TODO: could these have changed between the time that self.surface
        # was last updated?
        wd, ht = self.dims[:2]

        # Get PIL surface as a numpy array
        arr8 = np.frombuffer(self.surface.tobytes(), dtype=np.uint8)
        arr8 = arr8.reshape((ht, wd, 3))

        # adjust according to viewer's needed order
        arr8 = self.reorder(order, arr8, 'RGB')
        return arr8

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
