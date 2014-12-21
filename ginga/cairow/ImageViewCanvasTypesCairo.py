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

from ginga.canvas.mixins import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors
from ginga.util.six.moves import map, zip

class CairoCanvasMixin(object):

    def __get_color(self, color, alpha):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0
        return (r, g, b, alpha)

    def set_color(self, cr, color, alpha=1.0):
        r, g, b, a = self.__get_color(color, alpha)
        cr.set_source_rgba(r, g, b, a)

    def setup_cr(self):
        cr = self.viewer.get_offscreen_context()

        alpha = getattr(self, 'alpha', 1.0)
        self.set_color(cr, self.color, alpha=alpha)

        linewidth = getattr(self, 'linewidth', 1)
        cr.set_line_width(linewidth)

        if hasattr(self, 'linestyle'):
            if self.linestyle == 'dash':
                cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
                
        return cr

    def draw_fill(self, cr):
        fill = getattr(self, 'fill', False)
        if fill:
            color = getattr(self, 'fillcolor', None)
            if color is None:
                color = self.color
            alpha = getattr(self, 'alpha', 1.0)
            fillalpha = getattr(self, 'fillalpha', alpha)

            self.set_color(cr, color, alpha=fillalpha)
            # do the fill
            cr.fill()

            # reset context to old color
            self.set_color(cr, self.color, alpha=alpha)
            
    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        cr.move_to (x2, y2)
        cr.line_to (i1, j1)
        cr.line_to (i2, j2)
        cr.close_path()
        cr.stroke_preserve()
        cr.fill()
        
    def draw_cap(self, cr, cap, x, y, radius=None):
        if radius is None:
            radius = self.cap_radius
        cr.new_path()
        if cap == 'ball':
            cr.arc(x, y, radius, 0, 2*math.pi)
            cr.fill()
        
    def draw_caps(self, cr, cap, points, radius=None):
        for x, y in points:
            self.draw_cap(cr, cap, x, y, radius=radius)
        
    def draw_edit(self, cr):
        cpoints = self.get_cpoints(points=self.get_edit_points())
        self.draw_caps(cr, 'ball', cpoints)

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
        cr.set_font_size(fontsize)
        return self.text_extents(cr, self.text)

class Polygon(PolygonBase, CairoCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, CairoCanvasMixin):

    def draw(self):
        cr = self.setup_cr()
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           ((self.x1, self.y1), (self.x2, self.y1),
                            (self.x2, self.y2), (self.x1, self.y2))))
        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
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


class Square(Rectangle):
    pass


class Circle(CircleBase, CairoCanvasMixin):
    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)

        cr = self.setup_cr()
        cr.arc(cx1, cy1, cradius, 0, 2*math.pi)
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Ellipse(EllipseBase, CairoCanvasMixin):

    def draw(self):
        cp = self.get_cpoints(points=self.get_bezier_pts())
        cr = self.setup_cr()

        # draw 4 bezier curves to make the ellipse
        cr.move_to(cp[0][0], cp[0][1])
        cr.curve_to(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        cr.curve_to(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        cr.curve_to(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        cr.curve_to(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            cpoints = self.get_cpoints()
            self.draw_caps(cr, self.cap, cpoints)
        

class Box(BoxBase, CairoCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr()
        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Point(PointBase, CairoCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        if self.style == 'cross':
            cr.move_to(cx1, cy1)
            cr.line_to(cx2, cy2)
            cr.stroke()
            cr.move_to(cx1, cy2)
            cr.line_to(cx2, cy1)
            cr.stroke()
        else:
            cr.move_to(cx1, cy)
            cr.line_to(cx2, cy)
            cr.stroke()
            cr.move_to(cx, cy1)
            cr.line_to(cx, cy2)
            cr.stroke()

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
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

        if self.arrow == 'end':
            self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = [(cx1, cy1)]
        elif self.arrow == 'start':
            self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            caps = [(cx2, cy2)]
        elif self.arrow == 'both':
            self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)
            self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
            caps = []
        else:
            caps = [(cx1, cy1), (cx2, cy2)]

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, caps)


class Path(PathBase, CairoCanvasMixin):

    def draw(self):
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           self.points))
        cr = self.setup_cr()

        (cx0, cy0) = cpoints[0]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints[1:]:
            cr.line_to(cx, cy)
        cr.stroke_preserve()

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Compass(CompassBase, CairoCanvasMixin):

    def draw(self):
        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints()
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

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
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

        
class RightTriangle(RightTriangleBase, CairoCanvasMixin):

    def draw(self):
        cr = self.setup_cr()
        cpoints = list(map(lambda p: self.canvascoords(p[0], p[1]),
                           ((self.x1, self.y1), (self.x2, self.y2),
                            (self.x2, self.y1))))
        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(TriangleBase, CairoCanvasMixin):

    def draw(self):
        cr = self.setup_cr()
        cpoints = self.get_cpoints()
        (cx0, cy0) = cpoints[-1]
        cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        cr.close_path()
        cr.stroke_preserve()

        self.draw_fill(cr)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Ruler(RulerBase, CairoCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        text_x, text_y, text_h = self.get_ruler_distances()

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
        xtwd, xtht = self.text_extents(cr, text_x)
        ytwd, ytht = self.text_extents(cr, text_y)
        htwd, htht = self.text_extents(cr, text_h)

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
        cr.show_text(text_h)

        if self.showplumb:
            if self.color2:
                alpha = getattr(self, 'alpha', 1.0)
                self.set_color(cr, self.color2, alpha=alpha)

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
            cr.show_text(text_x)

            # draw Y plum line label
            cr.move_to(x, yh)
            cr.show_text(text_y)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Image(ImageBase, CairoCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            (cx0, cy0) = cpoints[-1]
            cr.move_to(cx0, cy0)
            for cx, cy in cpoints:
                cr.line_to(cx, cy)
                #cr.move_to(cx, cy)
            cr.close_path()
            cr.stroke_preserve()

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class NormImage(NormImageBase, CairoCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            (cx0, cy0) = cpoints[-1]
            cr.move_to(cx0, cy0)
            for cx, cy in cpoints:
                cr.line_to(cx, cy)
                #cr.move_to(cx, cy)
            cr.close_path()
            cr.stroke_preserve()

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


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
                   line=Line, point=Point, polygon=Polygon, path=Path,
                   ellipse=Ellipse, square=Square, box=Box,
                   triangle=Triangle, righttriangle=RightTriangle,
                   ruler=Ruler, compass=Compass,
                   compoundobject=CompoundObject, canvas=Canvas,
                   drawingcanvas=DrawingCanvas,
                   image=Image, normimage=NormImage)

        
#END
