#
# ImageViewCanvasTypesCairo.py -- drawing classes for ImageViewCanvas widget
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import cairo

from ginga.ImageViewCanvas import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors

class CairoCanvasMixin(object):

    def set_color(self, cr, color):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        cr.set_source_rgb(r, g, b)

    def setup_cr(self):
        cr = self.fitsimage.get_offscreen_context()

        self.set_color(cr, self.color)

        if hasattr(self, 'linewidth'):
            cr.set_line_width(self.linewidth)
        else:
            cr.set_line_width(1)

        if hasattr(self, 'linestyle'):
            if self.linestyle == 'dash':
                cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
                
        return cr

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        cr.move_to (x2, y2)
        cr.line_to (i1, j1)
        cr.line_to (i2, j2)
        cr.close_path()
        cr.stroke_preserve()
        cr.fill()
        
    def draw_cap(self, cr, cap, x, y, radius=2):
        if cap == 'ball':
            cr.arc(x, y, radius, 0, 2*math.pi)
            cr.fill()
        
    def draw_caps(self, cr, cap, points, radius=2):
        for x, y in points:
            self.draw_cap(cr, cap, x, y, radius=radius)
        
    def text_extents(self, cr, text):
        a, b, wd, ht, i, j = cr.text_extents(text)
        return wd, ht


class Text(TextBase, CairoCanvasMixin):

    def draw(self):
        cx, cy = self.canvascoords(self.x, self.y)

        cr = self.setup_cr()
        cr.select_font_face(self.font)
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.set_font_size(fontsize)
        cr.move_to(cx, cy)
        cr.show_text(self.text)


class Polygon(PolygonBase, CairoCanvasMixin):

    def draw(self):
        cpoints = map(lambda p: self.canvascoords(p[0], p[1]), self.points)
        cr = self.setup_cr()

        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        if self.fill:
            if self.fillcolor:
                self.set_color(cr, self.fillcolor)
            cr.fill()
            self.set_color(cr, self.color)

        if self.cap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, CairoCanvasMixin):

    def draw(self):
        cr = self.setup_cr()
        cpoints = map(lambda p: self.canvascoords(p[0], p[1]),
                      ((self.x1, self.y1), (self.x2, self.y1),
                       (self.x2, self.y2), (self.x1, self.y2)))
        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        if self.fill:
            if self.fillcolor:
                self.set_color(cr, self.fillcolor)
            cr.fill()
            self.set_color(cr, self.color)

        if self.cap:
            self.draw_caps(cr, self.cap, cpoints)

        if self.drawdims:
            cr.select_font_face(self.font)
            fontsize = self.scale_font()
            cr.set_font_size(fontsize)

            cx1, cy1 = cpoints[0]
            cx2, cy2 = cpoints[2]
            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) // 2
            cy = cy2 + -4
            cr.move_to(cx, cy)
            cr.show_text("%d" % (self.x2 - self.x1))

            cy = cy1 + (cy2 - cy1) // 2
            cx = cx2 + 4
            cr.move_to(cx, cy)
            cr.show_text("%d" % (self.y2 - self.y1))


class Square(SquareBase, Rectangle):
    pass


class Circle(CircleBase, CairoCanvasMixin):
    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)

        cr = self.setup_cr()
        cr.arc(cx1, cy1, cradius, 0, 2*math.pi)
        cr.stroke_preserve()
        if self.fill:
            if self.fillcolor:
                self.set_color(cr, self.fillcolor)
            cr.fill()
            self.set_color(cr, self.color)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Point(PointBase, CairoCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()
        cr.move_to(cx1, cy2)
        cr.line_to(cx2, cy1)
        cr.stroke()

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Line(LineBase, CairoCanvasMixin):
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), (cx2, cy2)))


class Compass(CompassBase, CairoCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)
        cx3, cy3 = self.canvascoords(self.x3, self.y3)

        cr = self.setup_cr()

        # draw North line and arrowhead
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)

        # draw East line and arrowhead
        cr.move_to(cx1, cy1)
        cr.line_to(cx3, cy3)
        cr.stroke()
        self.draw_arrowhead(cr, cx1, cy1, cx3, cy3)

        # draw "N" & "E"
        cr.select_font_face('Sans Serif')
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.set_font_size(fontsize)
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2)
#        cr.move_to(cx2, cy2)
        cr.move_to(cx, cy)
        cr.show_text('N')
        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3)
#        cr.move_to(cx3, cy3)
        cr.move_to(cx, cy)
        cr.show_text('E')

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))

    def get_textpos(self, cr, text, cx1, cy1, cx2, cy2):
        htwd, htht = self.text_extents(cr, text)

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
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) // 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        return (xd, yd)

        
class Triangle(TriangleBase, CairoCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()

        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy1)
        cr.stroke()

        cr.move_to(cx2, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()

        if self.cap:
            self.draw_caps(cr, self.cap,
                           ((cx1, cy1), (cx2, cy2), (cx2, cy1)))

class Ruler(RulerBase, CairoCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        
        cr.select_font_face(self.font)
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.set_font_size(fontsize)

        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

        cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)

        # calculate offsets and positions for drawing labels
        # try not to cover anything up
        xtwd, xtht = self.text_extents(cr, self.text_x)
        ytwd, ytht = self.text_extents(cr, self.text_y)
        htwd, htht = self.text_extents(cr, self.text_h)

        diag_xoffset = 0
        diag_yoffset = 0
        xplumb_yoffset = 0
        yplumb_xoffset = 0

        diag_yoffset = 14
        if abs(cy1 - cy2) < 5:
            show_angle = 0
        elif cy1 < cy2:
            xplumb_yoffset = -4
        else:
            xplumb_yoffset = 14
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
        xh += (max(cx1, cx2) - xh) // 2
        yh = min(cy1, cy2); x = cx2 + yplumb_xoffset
        yh += (max(cy1, cy2) - yh) // 2

        xd = xh + diag_xoffset
        yd = yh + diag_yoffset
        cr.move_to(xd, yd)
        cr.show_text(self.text_h)

        if self.color2:
            self.set_color(cr, self.color2)
            
        # draw X plumb line
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy1)
        cr.stroke()

        # draw Y plumb line
        cr.move_to(cx2, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()

        # draw X plum line label
        xh -= xtwd // 2
        cr.move_to(xh, y)
        cr.show_text(self.text_x)

        # draw Y plum line label
        cr.move_to(x, yh)
        cr.show_text(self.text_y)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
                    CanvasObjectBase, CairoCanvasMixin, 
                    Mixins.UIMixin, Callback.Callbacks):
    def __init__(self):
        CanvasObjectBase.__init__(self)
        CairoCanvasMixin.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        Callback.Callbacks.__init__(self)
        Mixins.UIMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)
        self.kind = 'drawingcanvas'


drawCatalog = dict(text=Text, rectangle=Rectangle, circle=Circle,
                   line=Line, point=Point, polygon=Polygon,
                   triangle=Triangle, ruler=Ruler, compass=Compass,
                   compoundobject=CompoundObject, canvas=Canvas,
                   drawingcanvas=DrawingCanvas)

        
#END
