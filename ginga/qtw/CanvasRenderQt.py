#
# CanvasRenderQt.py -- for rendering into a ImageViewQt widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore, QFont, QPainter, QPen, \
     QPolygonF, QPolygon, QColor

from ginga import colors
from ginga.util.six.moves import map, zip
# force registration of all canvas types
import ginga.canvas.types.all


class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer

        # TODO: encapsulate this drawable
        self.cr = QPainter(self.viewer.pixmap)

    def __get_color(self, color, alpha):
        clr = QColor()
        if isinstance(color, tuple):
            clr.setRgbF(color[0], color[1], color[2], alpha)
        else:
            r, g, b = colors.lookup_color(color)
            clr.setRgbF(r, g, b, alpha)
        return clr

    def set_line_from_shape(self, shape):
        pen = QPen()
        pen.setWidthF(getattr(shape, 'linewidth', 1.0))

        if hasattr(shape, 'linestyle'):
            if shape.linestyle == 'dash':
                pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
                pen.setDashOffset(5.0)

        alpha = getattr(shape, 'alpha', 1.0)
        color = self.__get_color(shape.color, alpha)
        pen.setColor(color)
        self.cr.setPen(pen)

    def set_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                color = shape.fillcolor
            else:
                color = shape.color

            if color is None:
                self.cr.setBrush(QtCore.Qt.NoBrush)
            else:
                alpha = getattr(shape, 'alpha', None)
                fillalpha = getattr(shape, 'fillalpha', alpha)
                color = self.__get_color(color, fillalpha)
                self.cr.setBrush(color)
        else:
            self.cr.setBrush(QtCore.Qt.NoBrush)

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            self.cr.setFont(QFont(shape.font, pointSize=fontsize))

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        clr = self.__get_color(color, alpha)
        pen = self.cr.pen()
        pen.setColor(clr)
        pen.setWidthF(float(linewidth))
        if style == 'dash':
            pen.setDashPattern([ 3.0, 4.0, 6.0, 4.0])
            pen.setDashOffset(5.0)
        self.cr.setPen(pen)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.cr.setBrush(QtCore.Qt.NoBrush)
        else:
            color = self.__get_color(color, alpha)
            self.cr.setBrush(color)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        # TODO: setting color a matter of setting the pen?
        self.cr.setFont(QFont(fontname, pointSize=fontsize))

    def text_extents(self, text):
        rect = self.cr.boundingRect(0, 0, 1000, 1000, 0, text)
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
        return width, height

    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.save()
        self.cr.translate(cx, cy)
        self.cr.rotate(-rot_deg)

        self.cr.drawText(0, 0, text)

        self.cr.restore()

    def draw_polygon(self, cpoints):
        qpoints = list(map(lambda p: QtCore.QPoint(p[0], p[1]),
                            (cpoints + (cpoints[0],))))
        qpoly = QPolygon(qpoints)

        self.cr.drawPolygon(qpoly)

    def draw_circle(self, cx, cy, cradius):
        # this is necessary to work around a bug in Qt--radius of 0
        # causes a crash
        cradius = max(cradius, 0.000001)
        pt = QtCore.QPointF(cx, cy)
        self.cr.drawEllipse(pt, float(cradius), float(cradius))

    def draw_bezier_curve(self, cp):
        path = QtGui.QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.cr.drawPath(path)

    def draw_ellipse_bezier(self, cp):
        # draw 4 bezier curves to make the ellipse
        path = QtGui.QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        path.cubicTo(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        path.cubicTo(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        path.cubicTo(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        self.cr.drawPath(path)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        self.cr.drawLine(cx1, cy1, cx2, cy2)

    def draw_path(self, cpoints):
        self.cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        for i in range(len(cpoints) - 1):
            cx1, cy1 = cpoints[i]
            cx2, cy2 = cpoints[i+1]
            self.cr.drawLine(cx1, cy1, cx2, cy2)


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
