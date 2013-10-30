#
# ImageViewCanvasTypesQt.py -- drawing classes for ImageViewCanvas widget
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from ginga.qtw.QtHelp import QtGui, QtCore

from ginga.ImageViewCanvas import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors

class QtCanvasMixin(object):

    def __get_color(self, color):
        clr = QtGui.QColor()
        if isinstance(color, tuple):
            clr.setRgbF(color[0], color[1], color[2])
        else:
            r, g, b = colors.lookup_color(color)
            clr.setRgbF(r, g, b)
        return clr
        
    def set_color(self, cr, color):
        clr = self.__get_color(color)
        pen = cr.pen()
        pen.setColor(clr)
        cr.setPen(pen)

    def fill(self, cr, onoff, color=None):
        if onoff:
            if color == None:
                color = self.color
            color = self.__get_color(color)
            cr.setBrush(color)
        else:
            cr.setBrush(QtCore.Qt.NoBrush)
            
    def setup_cr(self):
        cr = QtGui.QPainter(self.fitsimage.pixmap)

        pen = QtGui.QPen()
        if hasattr(self, 'linewidth'):
            pen.setWidth(self.linewidth)
        else:
            pen.setWidth(1)

        if hasattr(self, 'linestyle'):
            if self.linestyle == 'dash':
                pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
                pen.setDashOffset(5.0)

        color = self.__get_color(self.color)
        pen.setColor(color)
        cr.setPen(pen)

        if hasattr(self, 'fill') and self.fill:
            if hasattr(self, 'fillcolor') and self.fillcolor:
                color = self.fillcolor
            else:
                color = self.color
            if not color:
                cr.setBrush(QtCore.Qt.NoBrush)
            else:
                color = self.__get_color(color)
                cr.setBrush(color)
        else:
            cr.setBrush(QtCore.Qt.NoBrush)
            
        return cr

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        self.fill(cr, True)
        cr.pen().setJoinStyle(QtCore.Qt.MiterJoin)
        cr.drawPolygon(QtGui.QPolygonF([QtCore.QPointF(x2, y2),
                                        QtCore.QPointF(i1, j1),
                                        QtCore.QPointF(i2, j2)]))
        cr.pen().setJoinStyle(QtCore.Qt.BevelJoin)
        self.fill(cr, False)
        
    def draw_cap(self, cr, cap, x, y, radius=2):
        if cap == 'ball':
            self.fill(cr, True)
            cr.drawEllipse(x-radius, y-radius, radius*2, radius*2)
            self.fill(cr, False)
        
    def draw_caps(self, cr, cap, points, radius=2):
        for x, y in points:
            self.draw_cap(cr, cap, x, y, radius=radius)
        
    def text_extents(self, cr, text):
        rect = cr.boundingRect(0, 0, 1000, 1000, 0, text)
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
        return width, height


class Text(TextBase, QtCanvasMixin):

    def draw(self):
        cx, cy = self.canvascoords(self.x, self.y)

        cr = self.setup_cr()
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QtGui.QFont(self.font, pointSize=fontsize))
        cr.drawText(cx, cy, self.text)


class Polygon(PolygonBase, QtCanvasMixin):

    def draw(self):
        cpoints = map(lambda p: self.canvascoords(p[0], p[1]), self.points)
        cr = self.setup_cr()

        qpoints = map(lambda p: QtCore.QPoint(p[0], p[1]),
                      cpoints + [cpoints[0]])
        qpoly = QtGui.QPolygon(qpoints)

        cr.drawPolygon(qpoly)

        if self.cap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, QtCanvasMixin):
        
    def draw(self):
        cpoints = map(lambda p: self.canvascoords(p[0], p[1]),
                      ((self.x1, self.y1), (self.x2, self.y1),
                       (self.x2, self.y2), (self.x1, self.y2)))
        #qpoints = map(lambda p: QtCore.QPoint(p[0], p[1]), cpoints)
        qpoints = map(lambda p: QtCore.QPoint(p[0], p[1]),
                      cpoints + [cpoints[0]])
        qpoly = QtGui.QPolygon(qpoints)

        cr = self.setup_cr()
        cr.drawPolygon(qpoly)

        if self.cap:
            self.draw_caps(cr, self.cap, cpoints)

        if self.drawdims:
            fontsize = self.scale_font()
            cr.setFont(QtGui.QFont(self.font, pointSize=fontsize))

            cx1, cy1 = cpoints[0]
            cx2, cy2 = cpoints[2]

            # draw label on X dimension
            cx = cx1 + (cx2 - cx1) // 2
            cy = cy2 + -4
            cr.drawText(cx, cy, "%d" % (self.x2 - self.x1))

            # draw label on Y dimension
            cy = cy1 + (cy2 - cy1) // 2
            cx = cx2 + 4
            cr.drawText(cx, cy, "%d" % (self.y2 - self.y1))


class Square(SquareBase, Rectangle):
    pass


class Circle(CircleBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)

        cr = self.setup_cr()
        cr.drawEllipse(cx1-cradius, cy1-cradius, cradius*2, cradius*2)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Point(PointBase, QtCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr()
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)
        cr.drawLine(cx1, cy2, cx2, cy1)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Line(LineBase, QtCanvasMixin):
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), (cx2, cy2)))


class Compass(CompassBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)
        cx3, cy3 = self.canvascoords(self.x3, self.y3)

        cr = self.setup_cr()

        # draw North line and arrowhead
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)

        # draw East line and arrowhead
        cr.drawLine(cx1, cy1, cx3, cy3)
        self.draw_arrowhead(cr, cx1, cy1, cx3, cy3)

        # draw "N" & "E"
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QtGui.QFont('Sans Serif', pointSize=fontsize))
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2)
        cr.drawText(cx, cy, 'N')
        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3)
        cr.drawText(cx, cy, 'E')

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

        
class Triangle(TriangleBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()

        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)
        cr.drawLine(cx1, cy1, cx2, cy1)
        cr.drawLine(cx2, cy1, cx2, cy2)

        if self.cap:
            self.draw_caps(cr, self.cap,
                           ((cx1, cy1), (cx2, cy2), (cx2, cy1)))

class Ruler(RulerBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QtGui.QFont(self.font, pointSize=fontsize))

        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

        pen = cr.pen()

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
        cr.drawText(xd, yd, self.text_h)

        pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
        pen.setDashOffset(5.0)
        cr.setPen(pen)
        if self.color2:
            self.set_color(cr, self.color2)
                
        # draw X plumb line
        cr.drawLine(cx1, cy1, cx2, cy1)

        # draw Y plumb line
        cr.drawLine(cx2, cy1, cx2, cy2)

        # draw X plum line label
        xh -= xtwd // 2
        cr.drawText(xh, y, self.text_x)

        # draw Y plum line label
        cr.drawText(x, yh, self.text_y)

        if self.cap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
                    CanvasObjectBase, QtCanvasMixin,
                    Mixins.UIMixin, Callback.Callbacks):
    def __init__(self):
        CanvasObjectBase.__init__(self)
        QtCanvasMixin.__init__(self)
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
