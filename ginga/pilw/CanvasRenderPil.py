#
# CanvasRenderPil.py -- for rendering into a PIL Image
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

from PIL import Image, ImageDraw, ImageFont
from . import PilHelp
from itertools import chain
# force registration of all canvas types
import ginga.canvas.types.all

class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer

        # TODO: encapsulate this drawable
        self.cr = PilHelp.PilContext(self.viewer.get_surface())

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
        x, y = 0, 0          # old center
        nx, ny = cx, cy      # new center
        sx = sy = 1.0        # new scale
        cosine = math.cos(math.radians(rot_deg))
        sine = math.sin(math.radians(rot_deg))
        a = cosine / sx
        b = sine / sx
        c = x - nx*a - ny*b
        d = -sine / sy
        e = cosine / sy
        f = y - nx*d - ny*e
        return (a, b, c, d, e, f)

    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):

        wd, ht = self.cr.text_extents(text, self.font)

        self.cr.text((cx, cy-ht), text, self.font, self.pen)

    def draw_polygon(self, cpoints):
        self.cr.polygon(cpoints, self.pen, self.brush)

    def draw_circle(self, cx, cy, cradius):
        self.cr.circle((cx, cy), cradius, self.pen, self.brush)

    def draw_ellipse(self, cx, cy, cxradius, cyradius, theta):
        # NOTE: theta currently not supported with PIL renderer
        self.cr.ellipse((cx, cy), cxradius, cyradius, theta,
                        self.pen, self.brush)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.line((cx1, cy1), (cx2, cy2), self.pen)

    def draw_path(self, cpoints):
        self.cr.path(cpoints, self.pen)


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
