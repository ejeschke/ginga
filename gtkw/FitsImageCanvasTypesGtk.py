#
# FitsImageCanvasTypesGtk.py -- drawing classes for FitsImageCanvas widget
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Mon Oct  1 18:55:21 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

import gtk, re
import cairo

from FitsImageCanvas import *
import Mixins
import Callback
import Bunch

class CanvasObject(CanvasObjectBase):

    def set_color(self, cr, color):
        if isinstance(color, str):
            color = gtk.gdk.color_parse(color)
            rgb_s = color.to_string()
            match = re.match(r'^#(\w{4})(\w{4})(\w{4})$', rgb_s)
            r, g, b = map(lambda s: float(int(s, 16))/65535.0, match.groups())
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


class CompoundObject(CompoundMixin, CanvasObject):
    """Compound object on a FitsImageCanvas.
    Parameters are:
    the child objects making up the compound object.  Objects are drawn
    in the order listed.
    Example:
      CompoundObject(Point(x, y, radius, ...),
      Circle(x, y, radius, ...))
    This makes a point inside a circle.
    """

    def __init__(self, *objects):
        CanvasObject.__init__(self)
        CompoundMixin.__init__(self)
        self.kind = 'compound'
        self.objects = list(objects)

class Canvas(CanvasMixin, CompoundObject, CanvasObject):
    def __init__(self, *objects):
        CanvasObject.__init__(self)
        CompoundObject.__init__(self, *objects)
        CanvasMixin.__init__(self)
        self.kind = 'canvas'


class Text(CanvasObject):
    """Draws text on a FitsImageCanvas.
    Parameters are:
    x, y: 0-based coordinates in the data space
    text: the text to draw
    Optional parameters for fontsize, color, etc.
    """

    def __init__(self, x, y, text, font='Sans Serif', fontsize=None,
                 color='yellow'):
        self.kind = 'text'
        super(Text, self).__init__(color=color,
                                   x=x, y=y, font=font, fontsize=fontsize,
                                   text=text)

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

    def rotate(self, theta, xoff=0, yoff=0):
        self.x, self.y = self.rotate_pt(self.x, self.y, theta,
                                        xoff=xoff, yoff=yoff)

class Polygon(CanvasObject):
    """Draws a polygon on a FitsImageCanvas.
    Parameters are:
    List of (x, y) points in the polygon.  The last one is assumed to
    be connected to the first.
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, points, color='red',
                 linewidth=1, linestyle='solid', cap=None,
                 fill=False, fillcolor=None):
        self.kind = 'polygon'
        
        super(Polygon, self).__init__(points=points, color=color,
                                      linewidth=linewidth, cap=cap,
                                      linestyle=linestyle,
                                      fill=fill, fillcolor=fillcolor)
        
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

    def contains(self, x, y):
        # NOTE: we use a version of the ray casting algorithm
        # See: http://alienryderflex.com/polygon/
        result = False
        xj, yj = self.points[-1]
        for (xi, yi) in self.points:
            if ((((yi < y) and (yj >= y)) or
                 ((yj < y) and (yi >= y))) and
                ((xi <= x) or (xj <= x))):
                cross = (xi + float(y - yi)/(yj - yi)*(xj - xi)) < x
                result ^= cross
            xj, yj = xi, yi

        return result
            
    def rotate(self, theta, xoff=0, yoff=0):
        newpts = map(lambda p: self.rotate_pt(p[0], p[1], theta,
                                              xoff=xoff, yoff=yoff),
                     self.points)
        self.points = newpts


class Rectangle(CanvasObject):
    """Draws a rectangle on a FitsImageCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one corner in the data space
    x2, y2: 0-based coordinates of the opposing corner in the data space
    Optional parameters for linesize, color, etc.

    PLEASE NOTE: that the coordinates will be arranged in the final
    object such that x1, y1 always refers to the lower-left corner.
    """

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', cap=None,
                 fill=False, fillcolor=None,
                 drawdims=False, font='Sans Serif'):
        self.kind = 'rectangle'
        # ensure that rectangles are always bounded LL to UR
        x1, y1, x2, y2 = self.swapxy(x1, y1, x2, y2)
        
        super(Rectangle, self).__init__(color=color,
                                        x1=x1, y1=y1, x2=x2, y2=y2,
                                        linewidth=linewidth, cap=cap,
                                        linestyle=linestyle,
                                        fill=fill, fillcolor=fillcolor,
                                        drawdims=drawdims, font=font)
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)
        width  = cx2 - cx1 + 1
        height = cy2 - cy1 + 1
        
        cr = self.setup_cr()
        cr.rectangle(cx1, cy1, width, height)
        cr.stroke_preserve()
        if self.fill:
            if self.fillcolor:
                self.set_color(cr, self.fillcolor)
            cr.fill()
            self.set_color(cr, self.color)

        if self.cap:
            self.draw_caps(cr, self.cap,
                           ((cx1, cy1), (cx1, cy2), (cx2, cy1), (cx2, cy2)))

        if self.drawdims:
            cr.select_font_face(self.font)
            fontsize = self.scale_font()
            cr.set_font_size(fontsize)

            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) // 2
            cy = cy2 + -4
            cr.move_to(cx, cy)
            cr.show_text("%d" % (self.x2 - self.x1))

            cy = cy1 + (cy2 - cy1) // 2
            cx = cx2 + 4
            cr.move_to(cx, cy)
            cr.show_text("%d" % (self.y2 - self.y1))

    def contains(self, x, y):
        if ((x >= self.x1) and (x <= self.x2) and
            (y >= self.y1) and (y <= self.y2)):
            return True
        return False

    def rotate(self, theta, xoff=0, yoff=0):
        x1, y1 = self.rotate_pt(self.x1, self.y1, theta,
                                xoff=xoff, yoff=yoff)
        x2, y2 = self.rotate_pt(self.x2, self.y2, theta,
                                xoff=xoff, yoff=yoff)
        self.x1, self.y1, self.x2, self.y2 = self.swapxy(x1, y1, x2, y2)


class Square(Rectangle):
    """Draws a square on a FitsImageCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    length: size of a side (pixels in data space)
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x, y, length, color='red',
                 linewidth=1, linestyle='solid', cap=None,
                 fill=False, fillcolor=None,
                 drawdims=False, font='Sans Serif'):
        super(Square, self).__init__(x1=x, y1=y, x2=x-length, y2=y-length,
                                     color=color,
                                     linewidth=linewidth, cap=cap,
                                     linestyle=linestyle,
                                     fill=fill, fillcolor=fillcolor,
                                     drawdims=drawdims, font=font)
        self.kind = 'square'
        

class Circle(CanvasObject):
    """Draws a circle on a FitsImageCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x, y, radius, color='yellow',
                 linewidth=1, linestyle='solid', cap=None,
                 fill=False, fillcolor=None):
        super(Circle, self).__init__(color=color,
                                     linewidth=linewidth, cap=cap,
                                     linestyle=linestyle,
                                     fill=fill, fillcolor=fillcolor,
                                     x=x, y=y, radius=radius)
        self.kind = 'circle'

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

    def contains(self, x, y):
        radius = math.sqrt(math.fabs(x - self.x)**2 + math.fabs(y - self.y)**2)
        if radius <= self.radius:
            return True
        return False

    def rotate(self, theta, xoff=0, yoff=0):
        self.x, self.y = self.rotate_pt(self.x, self.y, theta,
                                        xoff=xoff, yoff=yoff)

class Point(CanvasObject):
    """Draws a point on a FitsImageCanvas.
    Parameters are:
    x, y: 0-based coordinates of the center in the data space
    radius: radius based on the number of pixels in data space
    Optional parameters for linesize, color, etc.

    PLEASE NOTE: currently on the 'cross' style of point is drawn.
    """

    def __init__(self, x, y, radius, style='cross', color='yellow',
                 linewidth=1, linestyle='solid', cap=None):
        self.kind = 'point'
        super(Point, self).__init__(color=color,
                                    linewidth=linewidth,
                                    linestyle=linestyle,
                                    x=x, y=y, radius=radius,
                                    cap=cap)
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x - self.radius, self.y - self.radius)
        cx2, cy2 = self.canvascoords(self.x + self.radius, self.y + self.radius)

        cr = self.setup_cr()
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(cx1, cy1)
        cr.line_to(cx2, cy2)
        cr.stroke()
        cr.move_to(cx1, cy2)
        cr.line_to(cx2, cy1)
        cr.stroke()

        if self.cap:
            cx, cy = self.canvascoords(self.x, self.y)
            self.draw_caps(cr, self.cap, ((cx, cy), ))

    def contains(self, x, y):
        if (x == self.x) and (y == self.y):
            return True
        return False

    def rotate(self, theta, xoff=0, yoff=0):
        self.x, self.y = self.rotate_pt(self.x, self.y, theta,
                                        xoff=xoff, yoff=yoff)

class Line(CanvasObject):
    """Draws a line on a FitsImageCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end in the data space
    x2, y2: 0-based coordinates of the opposing end in the data space
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x1, y1, x2, y2, color='red',
                 linewidth=1, linestyle='solid', cap=None):
        self.kind = 'line'
        super(Line, self).__init__(color=color,
                                   linewidth=linewidth, cap=cap,
                                   linestyle=linestyle,
                                   x1=x1, y1=y1, x2=x2, y2=y2)
        
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

    def rotate(self, theta, xoff=0, yoff=0):
        self.x1, self.y1 = self.rotate_pt(self.x1, self.y1, theta,
                                          xoff=xoff, yoff=yoff)
        self.x2, self.y2 = self.rotate_pt(self.x2, self.y2, theta,
                                          xoff=xoff, yoff=yoff)

class Compass(CanvasObject):
    """Draws a WCS compass on a FitsImageCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of the center in the data space
    x2, y2: 0-based coordinates of the 'North' end in the data space
    x3, y3: 0-based coordinates of the 'East' end in the data space
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x1, y1, x2, y2, x3, y3, color='skyblue',
                 linewidth=1, fontsize=None, cap='ball'):
        self.kind = 'compass'
        super(Compass, self).__init__(color=color,
                                      linewidth=linewidth, cap=cap,
                                      x1=x1, y1=y1, x2=x2, y2=y2, x3=x3, y3=y3,
                                      fontsize=fontsize)

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

        
class Triangle(CanvasObject):
    """Draws a right triangle on a FitsImageCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end of the diagonal in the data space
    x2, y2: 0-based coordinates of the opposite end of the diagonal
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x1, y1, x2, y2, color='pink',
                 linewidth=1, linestyle='solid', cap=None):
        self.kind='triangle'
        super(Triangle, self).__init__(color=color,
                                       linewidth=linewidth, cap=cap,
                                       linestyle=linestyle,
                                       x1=x1, y1=y1, x2=x2, y2=y2)

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

class Ruler(CanvasObject):
    """Draws a WCS ruler (like a right triangle) on a FitsImageCanvas.
    Parameters are:
    x1, y1: 0-based coordinates of one end of the diagonal in the data space
    x2, y2: 0-based coordinates of the opposite end of the diagonal
    Optional parameters for linesize, color, etc.
    """

    def __init__(self, x1, y1, x2, y2, color='red', color2='yellow',
                 linewidth=1, cap='ball', units='arcsec',
                 font='Sans Serif', fontsize=None,
                 text_x='kon', text_y='ban', text_h='wa'):
        self.kind = 'ruler'
        super(Ruler, self).__init__(color=color, color2=color2,
                                    linewidth=linewidth, cap=cap,
                                    x1=x1, y1=y1, x2=x2, y2=y2,
                                    font=font, fontsize=fontsize,
                                    text_x=text_x, text_y=text_y,
                                    text_h=text_h)

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

drawCatalog = {
    'rectangle': Rectangle,
    'circle': Circle,
    'line': Line,
    'point': Point,
    'ruler': Ruler,
    'triangle': Triangle,
    }

class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin, CanvasObject, 
                    Mixins.UIMixin, Callback.Callbacks):
    def __init__(self):
        CanvasObject.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        Callback.Callbacks.__init__(self)
        Mixins.UIMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)
        self.kind = 'drawingcanvas'

        
#END
