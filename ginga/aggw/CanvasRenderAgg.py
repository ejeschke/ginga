#
# CanvasRenderAgg.py -- for rendering into a ImageViewAgg widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
from itertools import chain

import aggdraw as agg

from . import AggHelp
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga import trcalc


class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer

        # TODO: encapsulate this drawable
        self.cr = AggHelp.AggContext(self.viewer.get_surface())

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
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
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
        # TODO: support line width and style
        self.pen = self.cr.get_pen(color, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)

    def get_affine_transform(self, cx, cy, rot_deg):
        x, y = cx, cy        # old center
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

    def draw_text(self, cx, cy, text, rot_deg=0.0):

        wd, ht = self.cr.text_extents(text, self.font)

        _cx, _cy = cx, cy - ht
        affine = self.get_affine_transform(_cx, _cy, rot_deg)
        self.cr.canvas.settransform(affine)
        try:
            self.cr.canvas.text((_cx, _cy), text, self.font)
        finally:
            # reset default transform
            self.cr.canvas.settransform()

    def draw_polygon(self, cpoints):
        cpoints = trcalc.strip_z(cpoints)
        self.cr.canvas.polygon(list(chain.from_iterable(cpoints)),
                               self.pen, self.brush)

    def draw_circle(self, cx, cy, cradius):
        self.cr.canvas.ellipse(
            (cx - cradius, cy - cradius, cx + cradius, cy + cradius),
            self.pen, self.brush)

    def draw_bezier_curve(self, cp):
        # there is a bug in path handling of some versions of aggdraw--
        # aggdraw here is ok:
        path = agg.Path()
        path.moveto(cp[0][0], cp[0][1])
        path.curveto(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.cr.canvas.path(path, self.pen, self.brush)

    def draw_ellipse_bezier(self, cp):
        # draw 4 bezier curves to make the ellipse because there seems
        # to be a bug in aggdraw ellipse drawing function
        path = agg.Path()
        path.moveto(cp[0][0], cp[0][1])
        path.curveto(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        path.curveto(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        path.curveto(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        path.curveto(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        self.cr.canvas.path(path, self.pen, self.brush)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.canvas.line((cx1, cy1, cx2, cy2), self.pen)

    def draw_path(self, cpoints):
        cp = trcalc.strip_z(cpoints)
        # TODO: is there a more efficient way in aggdraw to do this?
        path = agg.Path()
        path.moveto(cp[0][0], cp[0][1])
        for pt in cp[1:]:
            path.lineto(pt[0], pt[1])
        self.cr.canvas.path(path, self.pen, self.brush)


class CanvasRenderer(object):

    def __init__(self, viewer):
        self.viewer = viewer

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

#END
