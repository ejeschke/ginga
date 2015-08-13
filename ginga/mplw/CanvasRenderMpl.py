#
# ImageViewCanvasTypesMpl.py -- for rendering into a ImageViewMpl widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import matplotlib.patches as patches
import matplotlib.lines as lines
import matplotlib.text as text
from matplotlib.path import Path as MplPath
import numpy

from . import MplHelp
from ginga.canvas.mixins import *
# force registration of all canvas types
import ginga.canvas.types.all


class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer
        self.shape = None

        # TODO: encapsulate this drawable
        self.cr = MplHelp.MplContext(self.viewer.ax_util)

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
        fontdict = self.font.get_fontdict()
        self.cr.axes.text(cx, cy, text, fontdict=fontdict)

    def draw_polygon(self, cpoints):
        self.cr.init(closed=True, transform=None)
        self.cr.update_patch(self.pen, self.brush)

        xy = numpy.array(cpoints)

        p = patches.Polygon(xy, **self.cr.kwdargs)
        self.cr.axes.add_patch(p)

    def draw_circle(self, cx, cy, cradius):
        self.cr.init(radius=cradius, transform=None)
        self.cr.update_patch(self.pen, self.brush)

        xy = (cx, cy)

        p = patches.Circle(xy, **self.cr.kwdargs)
        self.cr.axes.add_patch(p)

    def draw_bezier_curve(self, verts):
        self.cr.init(transform=None)
        self.cr.update_patch(self.pen, None)

        codes = [ MplPath.MOVETO,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  ]
        path = MplPath(verts, codes)

        p = patches.PathPatch(path, **self.cr.kwdargs)
        self.cr.axes.add_patch(p)

    def draw_ellipse_bezier(self, verts):
        self.cr.init(transform=None)
        self.cr.update_patch(self.pen, self.brush)

        # draw 4 bezier curves to make the ellipse
        codes = [ MplPath.MOVETO,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  ]
        path = MplPath(verts, codes)

        p = patches.PathPatch(path, **self.cr.kwdargs)
        self.cr.axes.add_patch(p)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.init(transform=None)
        self.cr.update_line(self.pen)

        l = lines.Line2D((cx1, cx2), (cy1, cy2), **self.cr.kwdargs)
        self.cr.axes.add_line(l)

    def draw_path(self, cpoints):
        self.cr.init(closed=False, transform=None)
        self.cr.update_patch(self.pen, None)

        xy = numpy.array(cpoints)

        p = patches.Polygon(xy, **self.cr.kwdargs)
        self.cr.axes.add_patch(p)


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
