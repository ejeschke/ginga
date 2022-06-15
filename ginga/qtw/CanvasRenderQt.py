#
# CanvasRenderQt.py -- for rendering into a ImageViewQt widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.qtw.QtHelp import (QtCore, QPen, QPolygonF, QColor, QFontMetrics,
                              QPainterPath, QImage, QPixmap, get_font,
                              get_painter)

from ginga import colors
from ginga.vec import CanvasRenderVec as vec
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        self.cr = get_painter(surface)

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
            if (hasattr(shape, 'fontsize') and shape.fontsize is not None and
                not getattr(shape, 'fontscale', False)):
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            fontsize = self.scale_fontsize(fontsize)
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
        fontsize = self.scale_fontsize(fontsize)
        font = get_font(fontname, fontsize)
        self.cr.setFont(font)

    def text_extents(self, text):
        fm = self.cr.fontMetrics()
        if hasattr(fm, 'horizontalAdvance'):
            width = fm.horizontalAdvance(text)
        else:
            width = fm.width(text)
        height = fm.height()
        return width, height

    def setup_pen_brush(self, pen, brush):
        if pen is not None:
            self.set_line(pen.color, alpha=pen.alpha, linewidth=pen.linewidth,
                          style=pen.linestyle)

        self.cr.setBrush(QtCore.Qt.NoBrush)
        if brush is not None:
            self.set_fill(brush.color, alpha=brush.alpha)

    ##### DRAWING OPERATIONS #####

    ## def draw_image(self, cvs_img, cpoints, cache, whence, order='RGBA'):
    ##     # no-op for this renderer
    ##     pass

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.save()
        self.cr.translate(cx, cy)
        self.cr.rotate(-rot_deg)

        self.cr.drawText(0, 0, text)

        self.cr.restore()

    def draw_polygon(self, cpoints):
        ## cpoints = trcalc.strip_z(cpoints)
        qpoints = [QtCore.QPointF(p[0], p[1]) for p in cpoints]
        p = cpoints[0]
        qpoints.append(QtCore.QPointF(p[0], p[1]))
        qpoly = QPolygonF(qpoints)

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
        self.cr.drawLine(QtCore.QLineF(QtCore.QPointF(cx1, cy1),
                                       QtCore.QPointF(cx2, cy2)))

    def draw_path(self, cp):
        ## cp = trcalc.strip_z(cp)
        self.cr.pen().setCapStyle(QtCore.Qt.RoundCap)
        pts = [QtCore.QLineF(QtCore.QPointF(cp[i][0], cp[i][1]),
                             QtCore.QPointF(cp[i + 1][0], cp[i + 1][1]))
               for i in range(len(cp) - 1)]
        self.cr.drawLines(pts)


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer, surface_type='qimage'):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'qt'
        # Qt needs this to be in BGRA
        self.rgb_order = 'BGRA'
        self.qimg_fmt = QImage.Format_RGB32
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
        new_wd, new_ht = width * 2, height * 2

        if self.surface_type == 'qpixmap':
            if ((self.surface is None) or (self.surface.width() < width) or
                (self.surface.height() < height)):
                self.surface = QPixmap(new_wd, new_ht)
        else:
            self.surface = QImage(width, height, self.qimg_fmt)

        super(CanvasRenderer, self).resize(dims)

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

        # rendering surface is usually larger than window, so cutout
        # just enough to show what has been drawn
        win_wd, win_ht = self.dims[:2]
        arr = np.ascontiguousarray(arr[:win_ht, :win_wd, :])

        # adjust according to viewer's needed order
        return self.reorder(order, arr)

    def render_image(self, data, order, win_coord):
        """Render the image represented by (data) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        self.logger.debug("redraw surface")
        if self.surface is None:
            return
        self.logger.debug("drawing to surface")

        if data is None:
            return
        win_x, win_y = win_coord
        # Prepare array for rendering

        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # Get qimage for copying pixel data
        qimage = self._get_qimage(data)
        drawable = self.surface

        painter = get_painter(drawable)

        # fill surface with background color (not-strictly necessary,
        # since image should cover entire window, but to be safe, I guess...)
        ## size = drawable.size()
        ## sf_wd, sf_ht = size.width(), size.height()
        ## bg = self.viewer.img_bg
        ## bgclr = self._get_color(*bg)
        ## painter.fillRect(QtCore.QRect(0, 0, sf_wd, sf_ht), bgclr)

        # draw image data from buffer to offscreen pixmap
        painter.drawImage(QtCore.QRect(win_x, win_y, dawd, daht),
                          qimage,
                          QtCore.QRect(0, 0, dawd, daht))

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

    def text_extents(self, text, font):
        qfont = get_font(font.fontname, font.fontsize)
        fm = QFontMetrics(qfont)
        if hasattr(fm, 'horizontalAdvance'):
            width = fm.horizontalAdvance(text)
        else:
            width = fm.width(text)
        height = fm.height()
        return width, height


class VectorCanvasRenderer(vec.VectorRenderMixin, CanvasRenderer):

    def __init__(self, viewer, surface_type='qimage'):
        CanvasRenderer.__init__(self, viewer, surface_type=surface_type)
        vec.VectorRenderMixin.__init__(self)

        self._img_args = None

    def initialize(self):
        self.rl = []
        self._img_args = None

    def finalize(self):
        if self._img_args is not None:
            super(VectorCanvasRenderer, self).render_image(*self._img_args)

        cr = RenderContext(self, self.viewer, self.surface)
        self.draw_vector(cr)

    def render_image(self, rgbobj, win_x, win_y):
        # just save the parameters to be called at finalize()
        self._img_args = (rgbobj, win_x, win_y)

    def setup_cr(self, shape):
        # special cr that just stores up a render list
        cr = vec.RenderContext(self, self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = super(VectorCanvasRenderer, self).setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

#END
