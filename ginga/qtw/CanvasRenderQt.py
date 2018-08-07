#
# CanvasRenderQt.py -- for rendering into a ImageViewQt widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.qtw.QtHelp import (QtCore, QPainter, QPen, QPolygon, QColor,
                              QPainterPath, QImage, QPixmap, get_font)

from ginga import colors
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa


class RenderContext(object):

    def __init__(self, viewer, surface):
        self.viewer = viewer

        self.cr = QPainter(surface)
        self.cr.setRenderHint(QPainter.Antialiasing)

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
                pen.setDashPattern([3.0, 4.0, 6.0, 4.0])
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
            font = get_font(shape.font, fontsize)
            self.cr.setFont(font)

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
            pen.setDashPattern([3.0, 4.0, 6.0, 4.0])
            pen.setDashOffset(5.0)
        self.cr.setPen(pen)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.cr.setBrush(QtCore.Qt.NoBrush)
        else:
            color = self.__get_color(color, alpha)
            self.cr.setBrush(color)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        self.set_line(color, alpha=alpha)
        font = get_font(fontname, fontsize)
        self.cr.setFont(font)

    def text_extents(self, text):
        fm = self.cr.fontMetrics()
        width = fm.width(text)
        height = fm.height()
        return width, height

    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.save()
        self.cr.translate(cx, cy)
        self.cr.rotate(-rot_deg)

        self.cr.drawText(0, 0, text)

        self.cr.restore()

    def draw_polygon(self, cpoints):
        qpoints = [QtCore.QPoint(p[0], p[1]) for p in cpoints]
        p = cpoints[0]
        qpoints.append(QtCore.QPoint(p[0], p[1]))
        qpoly = QPolygon(qpoints)

        self.cr.drawPolygon(qpoly)

    def draw_circle(self, cx, cy, cradius):
        # this is necessary to work around a bug in Qt--radius of 0
        # causes a crash
        cradius = max(cradius, 0.000001)
        pt = QtCore.QPointF(cx, cy)
        self.cr.drawEllipse(pt, float(cradius), float(cradius))

    def draw_bezier_curve(self, cp):
        path = QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.cr.drawPath(path)

    def draw_ellipse_bezier(self, cp):
        # draw 4 bezier curves to make the ellipse
        path = QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        path.cubicTo(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        path.cubicTo(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        path.cubicTo(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        self.cr.drawPath(path)

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        self.cr.drawLine(cx1, cy1, cx2, cy2)

    def draw_path(self, cp):
        self.cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        pts = [QtCore.QLineF(QtCore.QPointF(cp[i][0], cp[i][1]),
                             QtCore.QPointF(cp[i + 1][0], cp[i + 1][1]))
               for i in range(len(cp) - 1)]
        self.cr.drawLines(pts)


class CanvasRenderer(render.RendererBase):

    def __init__(self, viewer, surface_type='qimage'):
        render.RendererBase.__init__(self, viewer)

        self.kind = 'qt'
        # Qt needs this to be in BGRA
        self.rgb_order = 'BGRA'
        self.qimg_fmt = QImage.Format_ARGB32
        self.surface_type = surface_type
        # the offscreen drawing surface
        self.surface = None

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))
        if self.surface_type == 'qpixmap':
            self.surface = QPixmap(width, height)
        else:
            self.surface = QImage(width, height, self.qimg_fmt)

    def _get_qimage(self, rgb_data):
        ht, wd, channels = rgb_data.shape

        result = QImage(rgb_data.data, wd, ht, self.qimg_fmt)
        # Need to hang on to a reference to the array
        result.ndarray = rgb_data
        return result

    def _get_color(self, r, g, b):
        # TODO: combine with the method from the RenderContext?
        n = 255.0
        clr = QColor(int(r * n), int(g * n), int(b * n))
        return clr

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        *** internal method-- do not use ***
        """
        self.logger.debug("redraw surface=%s" % (self.surface))
        if self.surface is None:
            return
        self.logger.debug("drawing to surface")

        # Prepare array for rendering
        # TODO: what are options for high bit depth under Qt?
        data = rgbobj.get_array(self.rgb_order, dtype=np.uint8)
        (height, width) = data.shape[:2]

        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # Get qimage for copying pixel data
        qimage = self._get_qimage(data)
        drawable = self.surface

        painter = QPainter(drawable)
        #painter.setWorldMatrixEnabled(True)

        # fill surface with background color
        #imgwin_wd, imgwin_ht = self.viewer.get_window_size()
        size = drawable.size()
        sf_wd, sf_ht = size.width(), size.height()
        bg = self.viewer.img_bg
        bgclr = self._get_color(*bg)
        painter.fillRect(QtCore.QRect(0, 0, sf_wd, sf_ht), bgclr)

        # draw image data from buffer to offscreen pixmap
        painter.drawImage(QtCore.QRect(dst_x, dst_y, width, height),
                          qimage,
                          QtCore.QRect(0, 0, width, height))

    def get_surface_as_array(self, order=None):
        if self.surface_type == 'qpixmap':
            qimg = self.surface.toImage()
        else:
            qimg = self.surface
        #qimg = qimg.convertToFormat(QImage.Format_RGBA32)

        width, height = qimg.width(), qimg.height()

        if hasattr(qimg, 'bits'):
            # PyQt
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
        else:
            # PySide
            ptr = qimg.constBits()

        arr = np.array(ptr).reshape(height, width, 4)

        # adjust according to viewer's needed order
        return self.reorder(order, arr)

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

#END
