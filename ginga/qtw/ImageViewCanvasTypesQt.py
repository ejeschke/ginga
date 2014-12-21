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

from ginga.qtw.QtHelp import QtGui, QtCore, QFont, QPainter, QPen, \
     QPolygonF, QPolygon, QColor

from ginga.canvas.mixins import *
from ginga import Mixins
from ginga.misc import Callback, Bunch
from ginga import colors
from ginga.util.six.moves import map, zip

class QtCanvasMixin(object):

    def __get_color(self, color, alpha):
        clr = QColor()
        if isinstance(color, tuple):
            clr.setRgbF(color[0], color[1], color[2], alpha)
        else:
            r, g, b = colors.lookup_color(color)
            clr.setRgbF(r, g, b, alpha)
        return clr
        
    def set_color(self, cr, color, alpha=1.0):
        clr = self.__get_color(color, alpha)
        pen = cr.pen()
        pen.setColor(clr)
        cr.setPen(pen)

    def set_fill(self, cr, onoff, color=None, alpha=1.0):
        if onoff:
            if color is None:
                color = self.color
            color = self.__get_color(color, alpha)
            cr.setBrush(color)
        else:
            cr.setBrush(QtCore.Qt.NoBrush)
            
    def setup_cr(self):
        cr = QPainter(self.viewer.pixmap)

        pen = QPen()
        pen.setWidthF(getattr(self, 'linewidth', 1.0))

        if hasattr(self, 'linestyle'):
            if self.linestyle == 'dash':
                pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
                pen.setDashOffset(5.0)

        alpha = getattr(self, 'alpha', 1.0)
        color = self.__get_color(self.color, alpha)
        pen.setColor(color)
        cr.setPen(pen)

        fill = getattr(self, 'fill', False)
        if fill:
            if hasattr(self, 'fillcolor') and self.fillcolor:
                color = self.fillcolor
            else:
                color = self.color
            if not color:
                cr.setBrush(QtCore.Qt.NoBrush)
            else:
                alpha = getattr(self, 'fillalpha', alpha)
                color = self.__get_color(color, alpha)
                cr.setBrush(color)
        else:
            cr.setBrush(QtCore.Qt.NoBrush)
            
        return cr

    def draw_arrowhead(self, cr, x1, y1, x2, y2):
        i1, j1, i2, j2 = self.calcVertexes(x1, y1, x2, y2)
        alpha = getattr(self, 'alpha', 1.0)
        self.set_fill(cr, True, alpha=alpha)
        cr.pen().setJoinStyle(QtCore.Qt.MiterJoin)
        cr.drawPolygon(QPolygonF([QtCore.QPointF(x2, y2),
                                        QtCore.QPointF(i1, j1),
                                        QtCore.QPointF(i2, j2)]))
        cr.pen().setJoinStyle(QtCore.Qt.BevelJoin)
        self.set_fill(cr, False)
        
    def draw_cap(self, cr, cap, x, y, radius=None):
        if radius is None:
            radius = self.cap_radius
        alpha = getattr(self, 'alpha', 1.0)
        if cap == 'ball':
            self.set_fill(cr, True, alpha=alpha)
            cr.drawEllipse(x-radius, y-radius, radius*2, radius*2)
            self.set_fill(cr, False)
        
    def draw_caps(self, cr, cap, points, radius=None):
        for x, y in points:
            self.draw_cap(cr, cap, x, y, radius=radius)
        
    def draw_edit(self, cr):
        cpoints = self.get_cpoints(points=self.get_edit_points())
        self.draw_caps(cr, 'ball', cpoints)

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
        cr.setFont(QFont(self.font, pointSize=fontsize))
        cr.drawText(cx, cy, self.text)

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
        cr.setFont(QFont(self.font, pointSize=fontsize))
        return self.text_extents(cr, self.text)


class Polygon(PolygonBase, QtCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                            (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Rectangle(RectangleBase, QtCanvasMixin):
        
    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            ((self.x1, self.y1), (self.x2, self.y1),
                             (self.x2, self.y2), (self.x1, self.y2))))
        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                           (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        cr = self.setup_cr()
        cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)

        if self.drawdims:
            fontsize = self.scale_font()
            cr.setFont(QFont(self.font, pointSize=fontsize))

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


class Square(Rectangle):
        pass


class Circle(CircleBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1, cradius = self.calc_radius(self.x, self.y, self.radius)
        # this is necessary to work around a bug in Qt--radius of 0
        # causes a crash
        cradius = max(cradius, 0.000001)

        cr = self.setup_cr()
        pt = QtCore.QPointF(cx1, cy1)
        cr.drawEllipse(pt, float(cradius), float(cradius))

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx1, cy1), ))


class Ellipse(EllipseBase, QtCanvasMixin):

    def draw(self):
        cp = self.get_cpoints(points=self.get_bezier_pts())
        cr = self.setup_cr()

        # draw 4 bezier curves to make the ellipse
        path = QtGui.QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        path.cubicTo(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        path.cubicTo(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        path.cubicTo(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        cr.drawPath(path)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            cpoints = self.get_cpoints()
            self.draw_caps(cr, self.cap, cpoints)
        

class Box(BoxBase, QtCanvasMixin):
        
    def draw(self):
        cpoints = self.get_cpoints()
        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                           (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        cr = self.setup_cr()
        cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Point(PointBase, QtCanvasMixin):

    def draw(self):
        cx, cy, cradius = self.calc_radius(self.x, self.y, self.radius)
        cx1, cy1 = cx - cradius, cy - cradius
        cx2, cy2 = cx + cradius, cy + cradius

        cr = self.setup_cr()
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)

        if self.style == 'cross':
            cr.drawLine(cx1, cy1, cx2, cy2)
            cr.drawLine(cx1, cy2, cx2, cy1)
        else:
            cr.drawLine(cx1, cy, cx2, cy)
            cr.drawLine(cx, cy1, cx, cy2)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx, cy), ))


class Line(LineBase, QtCanvasMixin):
        
    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        cr = self.setup_cr()
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)

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


class Path(PathBase, QtCanvasMixin):

    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            self.points))
        cr = self.setup_cr()
        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        for i in range(len(cpoints) - 1):
            cx1, cy1 = cpoints[i]
            cx2, cy2 = cpoints[i+1]
            cr.drawLine(cx1, cy1, cx2, cy2)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Compass(CompassBase, QtCanvasMixin):

    def draw(self):
        (cx1, cy1), (cx2, cy2), (cx3, cy3) = self.get_cpoints()
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
        cr.setFont(QFont('Sans Serif', pointSize=fontsize))
        cx, cy = self.get_textpos(cr, 'N', cx1, cy1, cx2, cy2)
        cr.drawText(cx, cy, 'N')
        cx, cy = self.get_textpos(cr, 'E', cx1, cy1, cx3, cy3)
        cr.drawText(cx, cy, 'E')

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

        
class RightTriangle(RightTriangleBase, QtCanvasMixin):

    def draw(self):
        cpoints = tuple(map(lambda p: self.canvascoords(p[0], p[1]),
                            ((self.x1, self.y1), (self.x2, self.y2),
                             (self.x2, self.y1))))
        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                           (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        cr = self.setup_cr()
        cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class Triangle(TriangleBase, QtCanvasMixin):

    def draw(self):
        cpoints = self.get_cpoints()
        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                           (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        cr = self.setup_cr()
        cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


## class EquilateralTriangle(Triangle):
##     pass

class Ruler(RulerBase, QtCanvasMixin):

    def draw(self):
        cx1, cy1 = self.canvascoords(self.x1, self.y1)
        cx2, cy2 = self.canvascoords(self.x2, self.y2)

        text_x, text_y, text_h = self.get_ruler_distances()

        cr = self.setup_cr()
        
        if not self.fontsize:
            fontsize = self.scale_font()
        else:
            fontsize = self.fontsize
        cr.setFont(QFont(self.font, pointSize=fontsize))

        cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        cr.drawLine(cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx1, cy1, cx2, cy2)
        self.draw_arrowhead(cr, cx2, cy2, cx1, cy1)

        pen = cr.pen()

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
        cr.drawText(xd, yd, text_h)

        if self.showplumb:
            pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
            pen.setDashOffset(5.0)
            cr.setPen(pen)
            if self.color2:
                alpha = getattr(self, 'alpha', 1.0)
                self.set_color(cr, self.color2, alpha=alpha)

            # draw X plumb line
            cr.drawLine(cx1, cy1, cx2, cy1)

            # draw Y plumb line
            cr.drawLine(cx2, cy1, cx2, cy2)

            # draw X plum line label
            xh -= xtwd // 2
            cr.drawText(xh, y, text_x)

            # draw Y plum line label
            cr.drawText(x, yh, text_y)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, ((cx2, cy1), ))


class Image(ImageBase, QtCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                               cpoints))
            qpoly = QPolygon(qpoints)
            cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


class NormImage(NormImageBase, QtCanvasMixin):

    def draw(self):
        # currently, drawing of images is handled in base class
        # here we just draw the caps
        ImageBase.draw(self)
        
        cpoints = self.get_cpoints()
        cr = self.setup_cr()

        # draw border
        if self.linewidth > 0:
            qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                               cpoints))
            qpoly = QPolygon(qpoints)
            cr.drawPolygon(qpoly)

        if self.editing:
            self.draw_edit(cr)
        elif self.showcap:
            self.draw_caps(cr, self.cap, cpoints)


## class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
##                     CanvasObjectBase, QtCanvasMixin,
##                     Mixins.UIMixin, Callback.Callbacks):
##     def __init__(self):
##         CanvasObjectBase.__init__(self)
##         QtCanvasMixin.__init__(self)
##         CompoundMixin.__init__(self)
##         CanvasMixin.__init__(self)
##         Callback.Callbacks.__init__(self)
##         Mixins.UIMixin.__init__(self)
##         DrawingMixin.__init__(self, drawCatalog)
##         self.kind = 'drawingcanvas'

class DrawingCanvas(DrawingMixin, CanvasMixin, CompoundMixin,
                    CanvasObjectBase, Mixins.UIMixin):
    def __init__(self):
        CanvasObjectBase.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        Mixins.UIMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)
        self.kind = 'drawingcanvas'
        self.editable = False

drawCatalog = dict(text=Text, rectangle=Rectangle, circle=Circle,
                   line=Line, point=Point, polygon=Polygon, path=Path,
                   righttriangle=RightTriangle, triangle=Triangle,
                   #equilateraltriangle=EquilateralTriangle,
                   ellipse=Ellipse, square=Square,
                   box=Box, ruler=Ruler, compass=Compass,
                   compoundobject=CompoundObject, canvas=Canvas,
                   drawingcanvas=DrawingCanvas,
                   image=Image, normimage=NormImage)


#END
