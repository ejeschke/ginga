#
# CanvasRenderBokeh.py -- for rendering into a Bokeh widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy

from . import BokehHelp
from ginga.canvas.mixins import *
# force registration of all canvas types
import ginga.canvas.types.all

# Bokeh imports
from bokeh.plotting import figure


class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer
        self.shape = None

        # TODO: encapsulate this drawable
        self.cr = BokehHelp.BokehContext(self.viewer.figure)

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
        # TODO: support style
        self.pen = self.cr.get_pen(color, alpha=alpha, linewidth=linewidth,
                                   linestyle=style)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize):
        self.font = self.cr.get_font(fontname, fontsize, 'black',
                                     alpha=1.0)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)


    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.init(angle=[numpy.radians(rot_deg)])
        self.cr.update_font(self.pen, self.font)

        self.cr.plot.text(x=[cx], y=[cy], text=[text], **self.cr.kwdargs)

    def draw_polygon(self, cpoints):
        self.cr.init()
        self.cr.update_patch(self.pen, self.brush)

        xy = numpy.array(cpoints)

        self.cr.plot.patches(xs=[xy.T[0]], ys=[xy.T[1]], **self.cr.kwdargs)

    def draw_circle(self, cx, cy, cradius):
        self.cr.init()
        self.cr.update_patch(self.pen, self.brush)

        self.cr.plot.circle(x=[cx], y=[cy], radius=[cradius],
                            **self.cr.kwdargs)

    def draw_bezier_curve(self, verts):
        self.cr.init()
        self.cr.update_line(self.pen)

        cx, cy = verts.T[0], verts.T[1]

        self.cr.plot.bezier(x0=[cx[0]], y0=[cy[0]],
                            x1=[cx[3]], y1=[cy[3]],
                            cx0=[cx[1]], cy0=[cy[1]],
                            cx1=[cx[2]], cy1=[cy[2]],
                            **self.cr.kwdargs)

    def draw_ellipse(self, cx, cy, cxradius, cyradius, theta):
        self.cr.init()
        self.cr.update_patch(self.pen, self.brush)

        self.cr.plot.oval(x=[cx], y=[cy],
                          width=[cxradius*2.0], height=[cyradius*2.0],
                          angle=[numpy.radians(theta)], **self.cr.kwdargs)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.init()
        self.cr.update_line(self.pen)

        self.cr.plot.line(x=[cx1, cx2], y=[cy1, cy2], **self.cr.kwdargs)

    def draw_path(self, cpoints):
        self.cr.init()

        self.cr.update_line(self.pen)

        xy = numpy.array(cpoints)

        self.cr.plot.line(x=xy.T[0], y=xy.T[1], **self.cr.kwdargs)


class CanvasRenderer(object):

    def __init__(self, viewer):
        self.viewer = viewer

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer)
        cr.initialize_from_shape(shape)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)


#END
