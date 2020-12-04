#
# CanvasRenderMock.py -- for rendering into a ImageViewMock widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.canvas import render
from ginga.fonts import font_asst
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # TODO: encapsulate this drawable
        #self.cr = GraphicsContext(surface)
        self.cr = None

    def __get_color(self, color, alpha):
        # return a color in the widget's native object
        # color is either a string or a 3-tuple of floats in 0-1 range
        clr = None
        return clr

    def set_line_from_shape(self, shape):
        pass

    def set_fill_from_shape(self, shape):
        pass

    def set_font_from_shape(self, shape):
        pass

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if font:
            self.set_font_from_shape(shape)
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        pass

    def set_fill(self, color, alpha=1.0):
        pass

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontname = font_asst.resolve_alias(fontname, fontname)
        fontsize = self.scale_fontsize(fontsize)

    def text_extents(self, text):
        # TODO: how to mock this?
        width = 200
        height = 15
        return width, height

    def setup_pen_brush(self, pen, brush):
        pass

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        #self.cr.draw_text(cx, cy, text)
        pass

    def draw_polygon(self, cpoints):
        cpoints = trcalc.strip_z(cpoints)
        #self.cr.draw_polygon(cpoints)
        pass

    def draw_circle(self, cx, cy, cradius):
        cradius = float(cradius)
        self.draw_ellipse(cx, cy, cradius, cradius, 0.0)

    def draw_ellipse(self, cx, cy, cradius, cyradius, theta):
        #self.cr.draw_ellipse((cx, cy), (cxradius, cyradius), theta)
        pass

    def draw_line(self, cx1, cy1, cx2, cy2):
        #self.cr.draw_line(cx1, cy1, cx2, cy2)
        pass

    def draw_path(self, cpoints):
        cpoints = trcalc.strip_z(cpoints)
        for i in range(len(cpoints) - 1):
            cx1, cy1 = cpoints[i]
            cx2, cy2 = cpoints[i + 1]
            #self.cr.draw_line(cx1, cy1, cx2, cy2)

    def draw_bezier_curve(self, cp):
        pass


class CanvasRenderer(render.StandardPixelRenderer):

    def __init__(self, viewer):
        render.StandardPixelRenderer.__init__(self, viewer)

        self.kind = 'mock'
        self.rgb_order = 'RGBA'
        self.surface = None
        self._rgb_arr = None

    def resize(self, dims):
        super(CanvasRenderer, self).resize(dims)

    def get_surface_as_array(self, order=None):
        # adjust according to viewer's needed order
        return self.reorder(order, self._rgb_arr)

    def render_image(self, data, order, win_coord):
        self._rgb_arr = data

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
