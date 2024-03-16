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
        self.ctx = PilHelp.PilContext(surface)

        # special scaling for PIL text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.75

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

        font.render.font = self.ctx._get_font(font)
        return font

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        _font = font.render.font
        if hasattr(_font, 'getbbox'):
            # PIL v10.0
            l, t, r, b = _font.getbbox(text)
            wd_px, ht_px = int(abs(round(r - l))), int(abs(round(b - t)))
        else:
            wd_px, ht_px = _font.getsize(text)
        return wd_px, ht_px

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

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        wd, ht = self.ctx.text_extents(text, font=font)

        # NOTE: rotation ignored in PIL, for now
        self.ctx.text((cx, cy - ht), text, font, line, fill)

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
