#
# ImageViewCanvasTypesMpl.py -- drawing classes for ImageViewCanvas widget
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

import matplotlib.patches as patches
import matplotlib.lines as lines
import matplotlib.text as text
from matplotlib.path import Path as MplPath
import numpy

from . import MplHelp
from ginga.canvas.mixins import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors
from ginga.util.six.moves import map, zip


class MplCanvasMixin(object):

    def setup_cr(self, **kwdargs):
        cr = MplHelp.MplContext(self.viewer.ax_util)
        cr.kwdargs.update(kwdargs)
        return cr

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        # i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        # kwdargs = dict(fill=True, closed=True,
        #                facecolor=cr.get_color(self.color, 1.0))
        # xy = numpy.array(((x2, y2), (i1, j1), (i2, j2)))
        # p = patches.Polygon(xy, **kwdargs)
        # cr.axes.add_patch(p)
        pass
        
    def _draw_cap(self, cr, cap, x, y, radius=None):
        if radius is None:
            radius = self.cap_radius
        if cap == 'ball':
            alpha = getattr(self, 'alpha', 1.0)
            alpha = getattr(self, 'fillalpha', alpha)
            color = cr.get_color(self.color, alpha)
            p = patches.Circle((x, y), radius=radius, transform=None,
                               edgecolor=color, 
                               fill=True, facecolor=color)
            cr.axes.add_patch(p)
        
    def draw_caps(self, cr, cap, points, radius=None):
        for x, y in points:
            self._draw_cap(cr, cap, x, y, radius=radius)
        
    def draw_edit(self, cr):
        cpoints = self.get_cpoints(points=self.get_edit_points())
        self.draw_caps(cr, 'ball', cpoints)

    def text_extents(self, cr, text, font):
        return cr.text_extents(text, font)


class Text(TextBase, MplCanvasMixin):

    def draw(self):
        cx, cy = self.canvascoords(self.x, self.y)

        cr = self.setup_cr()
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        alpha = getattr(self, 'alpha', 1.0)
        font = cr.get_font(self.font, fontsize, self.color,
                           alpha=alpha)

        cr.axes.text(cx, cy, self.text, fontdict=font)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))

    def get_dimensions(self):
        cr = self.setup_cr()
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        font = cr.get_font(self.font, fontsize, self.color)
        return self.text_extents(cr, self.text, font)


class Polygon(PolygonBase, MplCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()

        cr = self.setup_cr(closed=True, transform=None)
        cr.update_patch(self)
        
        xy = numpy.array(cpoints)
            
        p = patches.Polygon(xy, **cr.kwdargs)
        cr.axes.add_patch(p)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, MplCanvasMixin):

    def draw(self):
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           ((self.x1, self.y1), (self.x2, self.y1),
                            (self.x2, self.y2), (self.x1, self.y2))))

        cr = self.setup_cr(closed=True, transform=None)
        cr.update_patch(self)
        
        xy = numpy.array(cpoints)
            
        p = patches.Polygon(xy, **cr.kwdargs)
        cr.axes.add_patch(p)
        
        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

        if self.drawdims:
            fontsize = self.scale_font()
            alpha = getattr(self, 'alpha', 1.0)
            font = cr.get_font(self.font, fontsize, self.color,
                               alpha=alpha)

            cx1, cy1 = cpoints[0]
            cx2, cy2 = cpoints[2]
            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) / 2
            cy = cy2 + -4
            text = "%d" % (self.x2 - self.x1)
            cr.axes.text(cx, cy, text, fontdict=font)

            cy = cy1 + (cy2 - cy1) / 2
            cx = cx2 + 4
            text = "%d" % (self.y2 - self.y1)
            cr.axes.text(cx, cy, text, fontdict=font)


class Square(Rectangle):
    pass


class Circle(CircleBase, MplCanvasMixin):
    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)

        cr = self.setup_cr(radius=cradius, transform=None)
        cr.update_patch(self)
        
        xy = (cx1, cy1)
            
        p = patches.Circle(xy, **cr.kwdargs)
        cr.axes.add_patch(p)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Ellipse(EllipseBase, MplCanvasMixin):

    def draw(self):
        cr = self.setup_cr(transform=None)
        cr.update_patch(self)

        # draw 4 bezier curves to make the ellipse
        verts = self.get_cpoints(points=self.get_bezier_pts())
        codes = [ MplPath.MOVETO,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  MplPath.CURVE4, MplPath.CURVE4, MplPath.CURVE4,
                  ]
        path = MplPath(verts, codes)

        p = patches.PathPatch(path, **cr.kwdargs)
        cr.axes.add_patch(p)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            cpoints = self.get_cpoints()
            self.draw_caps(cr, self.cap, cpoints)


class Box(BoxBase, MplCanvasMixin):
        
    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr(closed=True, transform=None)
        cr.update_patch(self)
        
        xy = numpy.array(cpoints)
            
        p = patches.Polygon(xy, **cr.kwdargs)
        cr.axes.add_patch(p)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Point(PointBase, MplCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr(transform=None)
        cr.update_line(self)

        if self.style == 'cross':
            l = lines.Line2D((cx1, cx2), (cy1, cy2), **cr.kwdargs)
            cr.axes.add_line(l)
            l = lines.Line2D((cx1, cx2), (cy2, cy1), **cr.kwdargs)
            cr.axes.add_line(l)
        else:
            l = lines.Line2D((cx1, cx2), (cy, cy), **cr.kwdargs)
            cr.axes.add_line(l)
            l = lines.Line2D((cx, cx), (cy1, cy2), **cr.kwdargs)
            cr.axes.add_line(l)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Line(LineBase, MplCanvasMixin):
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr(transform=None)
        cr.update_line(self)
        
        l = lines.Line2D((cx1, cx2), (cy1, cy2), **cr.kwdargs)
        cr.axes.add_line(l)

        # TODO: arrow heads
        if self.arrow == 'end':
            #self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = [(cx1, cy1)]
        elif self.arrow == 'start':
            #self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            caps = [(cx2, cy2)]
        elif self.arrow == 'both':
            #self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            #self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = []
        else:
            caps = [(cx1, cy1), (cx2, cy2)]

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, caps)


class Path(PathBase, MplCanvasMixin):
        
    def draw(self):
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           self.points))

        cr = self.setup_cr(transform=None)
        cr.update_line(self)
        
        # TODO: see if there is a path type in aggdraw and if so, use it
        for i in range(len(cpoints) - 1):
            cx1, cy1 = cpoints[i]
            cx2, cy2 = cpoints[i+1]
            l = lines.Line2D((cx1, cx2), (cy1, cy2), **cr.kwdargs)
            cr.axes.add_line(l)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Compass(CompassBase, MplCanvasMixin):

    def draw(self):
        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints()

        cr = self.setup_cr(transform=None, head_width=10, head_length=15,
                           length_includes_head=True, overhang=0.20)
        cr.set(facecolor=cr.get_color(self.color, self.alpha))
        cr.update_line(self)

        # draw North line and arrowhead
        dx, dy = cx2 - cx1, cy2 - cy1
        p = patches.FancyArrow(cx1, cy1, dx, dy, **cr.kwdargs)
        cr.axes.add_patch(p)

        # draw East line and arrowhead
        dx, dy = cx3 - cx1, cy3 - cy1
        p = patches.FancyArrow(cx1, cy1, dx, dy, **cr.kwdargs)
        cr.axes.add_patch(p)

        # draw "N" & "E"
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        alpha = getattr(self, 'alpha', 1.0)
        font = cr.get_font(self.font, fontsize, self.color,
                           alpha=alpha)
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2, font)
        cr.axes.text(cx, cy, 'N', fontdict=font)

        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3, font)
        cr.axes.text(cx, cy, 'E', fontdict=font)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))

    def get_textpos(self, cr, text, cx1, cy1, cx2, cy2, font):
        htwd, htht = self.text_extents(cr, text, font)

        diag_xoffset = 0
        diag_yoffset = 0
        xplumb_yoffset = 0
        yplumb_xoffset = 0

        diag_yoffset = 14
        if abs(cy1 - cy2) < 5:
            pass
        elif cy1 < cy2:
            xplumb_yoffset = -4
        else:
            xplumb_yoffset = 14
            diag_yoffset = -4
        
        if abs(cx1 - cx2) < 5:
            diag_xoffset = -(4 + htwd)
        elif (cx1 < cx2):
            diag_xoffset = -(4 + htwd)
            yplumb_xoffset = 4
        else:
            diag_xoffset = 4
            yplumb_xoffset = -(4 + 0)

        xh = min(cx1, cx2); y = cy1 + xplumb_yoffset
        xh += (max(cx1, cx2) - xh) / 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) / 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        return (xd, yd)

        
class RightTriangle(RightTriangleBase, MplCanvasMixin):

    def draw(self):
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           ((self.x1, self.y1), (self.x2, self.y2),
                            (self.x2, self.y1))))

        cr = self.setup_cr(closed=True, transform=None)
        cr.update_patch(self)
        
        xy = numpy.array(cpoints)
            
        p = patches.Polygon(xy, **cr.kwdargs)
        cr.axes.add_patch(p)
        
        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(TriangleBase, MplCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr(closed=True, transform=None)
        cr.update_patch(self)
        
        xy = numpy.array(cpoints)
            
        p = patches.Polygon(xy, **cr.kwdargs)
        cr.axes.add_patch(p)
        
        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Ruler(RulerBase, MplCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        text_x, text_y, text_h = self.get_ruler_distances()

        dx, dy = cx2 - cx1, cy2 - cy1
        
        cr = self.setup_cr(transform=None, head_width=10, head_length=15,
                           length_includes_head=True, overhang=0.20)
        cr.set(facecolor=cr.get_color(self.color, self.alpha))
        cr.update_line(self)
        
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        alpha = getattr(self, 'alpha', 1.0)
        font = cr.get_font(self.font, fontsize, self.color,
                           alpha=alpha)

        # draw the line connecting the start and end drag points
        # and add arrows on each end
        #cr.set_line_cap(cairo.LINE_CAP_ROUND)
        p = patches.FancyArrow(cx1, cy1, dx, dy, **cr.kwdargs)
        cr.axes.add_patch(p)
        #cr.axes.arrow(cx1, cy1, dx, dy, **cr.kwdargs)
        
        cr.init(transform=None)
        cr.update_line(self)
        cr.set(linestyle='dashdot', dash_joinstyle='round')

        # calculate offsets and positions for drawing labels
        # try not to cover anything up
        xtwd, xtht = self.text_extents(cr, text_x, font)
        ytwd, ytht = self.text_extents(cr, text_y, font)
        htwd, htht = self.text_extents(cr, text_h, font)

        diag_xoffset = 0
        diag_yoffset = 0
        xplumb_yoffset = 0
        yplumb_xoffset = 0

        diag_yoffset = 14
        if abs(cy1 - cy2) < 5:
            show_angle = 0
        elif cy1 < cy2:
            #xplumb_yoffset = -4
            xplumb_yoffset = -16
        else:
            #xplumb_yoffset = 14
            xplumb_yoffset = 4
            diag_yoffset = -4
        
        if abs(cx1 - cx2) < 5:
            diag_xoffset = -(4 + htwd)
            show_angle = 0
        elif (cx1 < cx2):
            diag_xoffset = -(4 + htwd)
            yplumb_xoffset = 4
        else:
            diag_xoffset = 4
            yplumb_xoffset = -(4 + ytwd)

        xh = min(cx1, cx2); y = cy1 + xplumb_yoffset
        xh += (max(cx1, cx2) - xh) / 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) / 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        cr.axes.text(xd, yd, text_h, fontdict=font)

        if self.showplumb:
            if self.color2:
                cr.set(color=cr.get_color(self.color2, self.alpha))
                font = cr.get_font(self.font, fontsize, self.color2,
                                   alpha=alpha)

            # draw X plumb line
            #cr.canvas.line((cx1, cy1, cx2, cy1), pen)
            l = lines.Line2D((cx1, cx2), (cy1, cy1), **cr.kwdargs)
            cr.axes.add_line(l)

            # draw Y plumb line
            #cr.canvas.line((cx2, cy1, cx2, cy2), pen)
            l = lines.Line2D((cx2, cx2), (cy1, cy2), **cr.kwdargs)
            cr.axes.add_line(l)

            # draw X plum line label
            xh -= xtwd / 2
            cr.axes.text(xh, y, text_x, fontdict=font)

            # draw Y plum line label
            cr.axes.text(x, yh, text_y, fontdict=font)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Image(ImageBase, MplCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        # TODO: bug here--fix!
        # if self.linewidth > 0:
        #     xy = numpy.array(cpoints)
        #     p = patches.Polygon(xy, **cr.kwdargs)
        #     cr.axes.add_patch(p)
        
        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class NormImage(NormImageBase, MplCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        # TODO: bug here--fix!
        # if self.linewidth > 0:
        #     xy = numpy.array(cpoints)
        #     p = patches.Polygon(xy, **cr.kwdargs)
        #     cr.axes.add_patch(p)
        
        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
                    CanvasObjectBase, MplCanvasMixin, 
                    Mixins.UIMixin, Callback.Callbacks):
    def __init__(self):
        CanvasObjectBase.__init__(self)
        MplCanvasMixin.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        Callback.Callbacks.__init__(self)
        Mixins.UIMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)
        self.kind = 'drawingcanvas'


drawCatalog = dict(text=Text, rectangle=Rectangle, circle=Circle,
                   line=Line, point=Point, polygon=Polygon, box=Box,
                   path=Path, square=Square, ellipse=Ellipse,
                   triangle=Triangle, righttriangle=RightTriangle,
                   ruler=Ruler, compass=Compass,
                   compoundobject=CompoundObject, canvas=Canvas,
                   drawingcanvas=DrawingCanvas,
                   image=Image, normimage=NormImage)

        
#END
