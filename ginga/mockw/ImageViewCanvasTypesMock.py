#
# ImageViewCanvasTypesMock.py -- drawing classes for ImageViewCanvas widget
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from ginga.canvas.mixins import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors
from ginga.util.six.moves import map, zip

class MockCanvasMixin(object):

    def __get_color(self, color, alpha):
        # return a color in the widget's native object
        # color is either a string or a 3-tuple of floats in 0-1 range
        clr = None
        return clr
        
    def set_color(self, cr, color, alpha=1.0):
        clr = self.__get_color(color, alpha)
        # prepare a pen in the context
        #pen = cr.pen()
        #pen.setColor(clr)
        #cr.setPen(pen)

    def set_fill(self, cr, onoff, color=None, alpha=1.0):
        if onoff:
            if color is None:
                color = self.color
            color = self.__get_color(color, alpha)
            #cr.setBrush(color)
        else:
            #cr.setBrush(QtCore.Qt.NoBrush)
            pass
            
    def setup_cr(self):
        # prepare to draw on self.viewer.pixmap
        # make a context
        #cr = GraphicsContext(self.viewer.pixmap)
        cr = None

        #pen = QPen()
        #pen.setWidth(getattr(self, 'linewidth', 1))

        if hasattr(self, 'linestyle'):
            if self.linestyle == 'dash':
                #pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
                #pen.setDashOffset(5.0)
                pass

        alpha = getattr(self, 'alpha', 1.0)
        color = self.__get_color(self.color, alpha)
        #pen.setColor(color)
        #cr.setPen(pen)

        fill = getattr(self, 'fill', False)
        if fill:
            if hasattr(self, 'fillcolor') and self.fillcolor:
                color = self.fillcolor
            else:
                color = self.color
            if not color:
                #cr.setBrush(QtCore.Qt.NoBrush)
                pass
            else:
                alpha = getattr(self, 'fillalpha', alpha)
                color = self.__get_color(color, alpha)
                #cr.setBrush(color)
        else:
            #cr.setBrush(QtCore.Qt.NoBrush)
            pass
            
        return cr

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        alpha = getattr(self, 'alpha', 1.0)
        self.set_fill(cr, True, alpha=alpha)
        #cr.draw_polygon([(x2, y2), (i1, j1), (i2, j2)])
        self.set_fill(cr, False)
        
    def draw_cap(self, cr, cap, x, y, radius=None):
        if radius is None:
            radius = self.cap_radius
        alpha = getattr(self, 'alpha', 1.0)
        if cap == 'ball':
            self.set_fill(cr, True, alpha=alpha)
            #cr.draw_ellipse(x-radius, y-radius, radius*2, radius*2)
            self.set_fill(cr, False)
        
    def draw_caps(self, cr, cap, points, radius=None):
        for x, y in points:
            self.draw_cap(cr, cap, x, y, radius=radius)
        
    def draw_edit(self, cr):
        cpoints = self.get_cpoints(points=self.get_edit_points())
        self.draw_caps(cr, 'ball', cpoints)

    def text_extents(self, cr, text):
        # calculate the width and height of drawing `text` on this
        # canvas with current parameters
        #width = x2 - x1
        width = 100
        #height = y2 - y1
        height = 40
        return width, height


class Text(TextBase, MockCanvasMixin):

    def draw(self):
        cx, cy = self.canvascoords(self.x, self.y)

        cr = self.setup_cr()
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QFont(self.font, pointSize=fontsize))
        cr.drawText(cx, cy, self.text)

    def get_dimensions(self):
        cr = self.setup_cr()
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QFont(self.font, pointSize=fontsize))
        return self.text_extents(cr, self.text)

class Polygon(PolygonBase, MockCanvasMixin):

    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            self.points))
        cr = self.setup_cr()

        #cr.draw_polygon(cpoints)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, MockCanvasMixin):
        
    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            ((self.x1, self.y1), (self.x2, self.y1),
                             (self.x2, self.y2), (self.x1, self.y2))))
        cr = self.setup_cr()

        #cr.draw_polygon(cpoints)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

        if self.drawdims:
            fontsize = self.scale_font()
            #cr.set_font(Font(self.font, pointSize=fontsize))

            cx1, cy1 = cpoints[0]
            cx2, cy2 = cpoints[2]

            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) // 2
            cy = cy2 + -4
            #cr.draw_text(cx, cy, "%d" % (self.x2 - self.x1))

            # draw label on Y dimension
            cy = cy1 + (cy2 - cy1) // 2
            cx = cx2 + 4
            #cr.draw_text(cx, cy, "%d" % (self.y2 - self.y1))


class Square(Rectangle):
    pass


class Circle(CircleBase, MockCanvasMixin):

    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)

        cr = self.setup_cr()
        #cr.draw_ellipse(cx1, cy1, float(cradius), float(cradius))

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Ellipse(EllipseBase, MockCanvasMixin):

    def draw(self):
        # get scale and rotation for special hack (see below)
        cx, cy, cxr, cyr, rot_deg = self.get_center_radii_rot()

        cr = self.setup_cr()
        # Special hack for ellipses to deal with rotated canvas
        #cr.translate(cx, cy)
        #cr.rotate(-rot_deg)

        #cr.draw_ellipse(pt, float(cxr), float(cyr))

        if self.cap:
            self.draw_caps(cr, self.cap, ((0, 0), ))

        #cr.translate(-cx, -cy)
        

class Box(BoxBase, MockCanvasMixin):
        
    def draw(self):
        cpoints = self.get_cpoints()

        cr = self.setup_cr()
        #cr.draw_polygon(cpoints)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Point(PointBase, MockCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr()
        if self.style == 'cross':
            #cr.draw_line(cx1, cy1, cx2, cy2)
            #cr.draw_line(cx1, cy2, cx2, cy1)
            pass
        else:
            #cr.draw_line(cx1, cy, cx2, cy)
            #cr.draw_line(cx, cy1, cx, cy2)
            pass

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Line(LineBase, MockCanvasMixin):
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        #cr.draw_line(cx1, cy1, cx2, cy2)

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


class Path(PathBase, MockCanvasMixin):

    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            self.points))
        cr = self.setup_cr()
        for i in range(len(cpoints) - 1):
            cx1, cy1 = cpoints[i]
            cx2, cy2 = cpoints[i+1]
            #cr.draw_line(cx1, cy1, cx2, cy2)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Compass(CompassBase, MockCanvasMixin):

    def draw(self):
        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints()
        cr = self.setup_cr()

        # draw North line and arrowhead
        #cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)

        # draw East line and arrowhead
        #cr.draw_line(cx1, cy1, cx3, cy3)
        self.draw_arrowhead(cr, cx1, cy1, cx3, cy3)

        # draw "N" & "E"
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        #cr.set_font(Font('Sans Serif', pointSize=fontsize))
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2)
        #cr.draw_text(cx, cy, 'N')
        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3)
        #cr.draw_text(cx, cy, 'E')

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

        
class RightTriangle(RightTriangleBase, MockCanvasMixin):

    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            ((self.x1, self.y1), (self.x2, self.y2),
                             (self.x2, self.y1))))

        cr = self.setup_cr()
        #cr.draw_polygon(cpoints)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(TriangleBase, MockCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr()
        #cr.draw_polygon(cpoints)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Ruler(RulerBase, MockCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        text_x, text_y, text_h = self.get_ruler_distances()

        cr = self.setup_cr()
        
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        #cr.set_font(Font(self.font, pointSize=fontsize))

        #cr.draw_line(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

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
        #cr.draw_text(xd, yd, text_h)

        if self.showplumb:
            ## pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
            ## pen.setDashOffset(5.0)
            ## cr.setPen(pen)
            if self.color2:
                alpha = getattr(self, 'alpha', 1.0)
                self.set_color(cr, self.color2, alpha=alpha)

            # draw X plumb line
            #cr.draw_line(cx1, cy1, cx2, cy1)

            # draw Y plumb line
            #cr.draw_line(cx2, cy1, cx2, cy2)

            # draw X plum line label
            xh -= xtwd // 2
            #cr.draw_text(xh, y, text_x)

            # draw Y plum line label
            #cr.draw_text(x, yh, text_y)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Image(ImageBase, MockCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            #cr.draw_polygon(cpoints)
            pass

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class NormImage(NormImageBase, MockCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            #cr.draw_polygon(cpoints)
            pass

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
                    CanvasObjectBase, MockCanvasMixin,
                    Mixins.UIMixin, Callback.Callbacks):
    def __init__(self):
        CanvasObjectBase.__init__(self)
        MockCanvasMixin.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        Callback.Callbacks.__init__(self)
        Mixins.UIMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)
        self.kind = 'drawingcanvas'

drawCatalog = dict(text=Text, rectangle=Rectangle, circle=Circle,
                   line=Line, point=Point, polygon=Polygon, path=Path,
                   righttriangle=RightTriangle, triangle=Triangle,
                   ellipse=Ellipse, square=Square,
                   box=Box, ruler=Ruler, compass=Compass,
                   compoundobject=CompoundObject, canvas=Canvas,
                   drawingcanvas=DrawingCanvas,
                   image=Image, normimage=NormImage)


#END
