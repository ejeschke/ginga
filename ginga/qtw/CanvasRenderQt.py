#
# CanvasRenderQt.py -- for rendering into a ImageViewQt widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy as np

from ginga.qtw.QtHelp import (QtCore, QPen, QBrush, QPolygonF, QColor,
                              QFontMetrics,
                              QPainterPath, QImage, QPixmap, get_font,
                              get_painter)

from ginga.vec import CanvasRenderVec as vec
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        self.ctx = get_painter(surface)

        # special scaling for Qt text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.0

    def get_line(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        line = super().get_line(color, alpha=alpha, linewidth=linewidth,
                                linestyle=linestyle)

        if (line.color is None or np.isclose(line.linewidth, 0) or
            np.isclose(line.alpha, 0.0)):
            pen = QPen(QtCore.Qt.NoPen)
        else:
            pen = QPen()
            pen.setWidthF(line.linewidth)

            if line.linestyle == 'dash':
                pen.setDashPattern([3.0, 4.0, 6.0, 4.0])
                pen.setDashOffset(5.0)

            color = QColor()
            color.setRgbF(*line._color_4tup)
            pen.setColor(color)

        line.render.pen = pen
        return line

    def get_fill(self, color, alpha=1.0):
        fill = super().get_fill(color, alpha=alpha)

        if fill.color is None or np.isclose(fill.alpha, 0.0):
            brush = QBrush(QtCore.Qt.NoBrush)
        else:
            color = QColor()
            color.setRgbF(*fill._color_4tup)
            brush = QBrush(color)

        fill.render.brush = brush
        return fill

    def get_font(self, fontname, **kwargs):
        font = super().get_font(fontname, **kwargs)

        # NOTE: QFont needs integer point size
        font.render.font = get_font(font.fontname, int(font.fontsize))
        return font

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        fm = QFontMetrics(font.render.font)
        rect = fm.boundingRect(text)
        width, height = rect.width(), fm.ascent()  # rect.height()
        return width, height

    ##### DRAWING OPERATIONS #####

    ## def draw_image(self, cvs_img, cpoints, cache, whence, order='RGBA'):
    ##     # no-op for this renderer
    ##     pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        self.ctx.save()
        self.ctx.translate(cx, cy)
        self.ctx.rotate(-rot_deg)

        if font is not None:
            self.ctx.setFont(font.render.font)
        qfont = self.ctx.font()
        self.ctx.setBrush(QtCore.Qt.NoBrush if fill is None
                          else fill.render.brush)

        if line is not None:
            self.ctx.setPen(line.render.pen)
            path = QPainterPath()
            path.addText(QtCore.QPointF(0, 0), qfont, text)
            self.ctx.drawPath(path)
        else:
            # NOTE: drawText() is more efficient if we have a lot of text,
            # so use it instead if we are not stroking a path outline.
            # When we use drawText(), we need to set the color by the pen
            pen = QPen()
            color = QColor()
            color.setRgbF(*fill._color_4tup)
            pen.setColor(color)
            self.ctx.setPen(pen)
            self.ctx.drawText(0, 0, text)

        self.ctx.restore()

    def draw_polygon(self, cpoints, line=None, fill=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)
        self.ctx.setBrush(QtCore.Qt.NoBrush if fill is None
                          else fill.render.brush)

        ## cpoints = trcalc.strip_z(cpoints)
        qpoints = [QtCore.QPointF(p[0], p[1]) for p in cpoints]
        p = cpoints[0]
        qpoints.append(QtCore.QPointF(p[0], p[1]))
        qpoly = QPolygonF(qpoints)

        self.ctx.drawPolygon(qpoly)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)
        self.ctx.setBrush(QtCore.Qt.NoBrush if fill is None
                          else fill.render.brush)

        # this is necessary to work around a bug in Qt--radius of 0
        # causes a crash
        cradius = max(cradius, 0.000001)
        pt = QtCore.QPointF(cx, cy)
        self.ctx.drawEllipse(pt, float(cradius), float(cradius))

    def draw_bezier_curve(self, cp, line=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)

        path = QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.ctx.drawPath(path)

    def draw_ellipse_bezier(self, cp, line=None, fill=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)
        self.ctx.setBrush(QtCore.Qt.NoBrush if fill is None
                          else fill.render.brush)

        # draw 4 bezier curves to make the ellipse
        path = QPainterPath()
        path.moveTo(cp[0][0], cp[0][1])
        path.cubicTo(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        path.cubicTo(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        path.cubicTo(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        path.cubicTo(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        self.ctx.drawPath(path)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)
        self.ctx.pen().setCapStyle(QtCore.Qt.RoundCap)

        self.ctx.drawLine(QtCore.QLineF(QtCore.QPointF(cx1, cy1),
                                        QtCore.QPointF(cx2, cy2)))

    def draw_path(self, cp, line=None):

        self.ctx.setPen(QtCore.Qt.NoPen if line is None
                        else line.render.pen)
        self.ctx.pen().setCapStyle(QtCore.Qt.RoundCap)

        ## cp = trcalc.strip_z(cp)
        pts = [QtCore.QLineF(QtCore.QPointF(cp[i][0], cp[i][1]),
                             QtCore.QPointF(cp[i + 1][0], cp[i + 1][1]))
               for i in range(len(cp) - 1)]
        self.ctx.drawLines(pts)


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

    def get_surface_as_array(self, order=None):

        if self.surface_type == 'qpixmap':
            qimg = self.surface.toImage()
        else:
            qimg = self.surface
        #qimg = qimg.convertToFormat(QImage.Format_RGBA32)

        width, height = qimg.width(), qimg.height()

        if hasattr(qimg, 'bits'):
            # PyQt and newer PySide
            ptr = qimg.bits()
            if hasattr(ptr, 'setsize'):
                if hasattr(qimg, 'byteCount'):
                    # Qt 5
                    ptr.setsize(qimg.byteCount())
                else:
                    # Qt 6
                    ptr.setsize(qimg.sizeInBytes())
        else:
            # older PySide
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
        font = cr.get_font_from_shape(shape)
        return cr.text_extents(shape.text, font=font)

    def text_extents(self, text, font):
        qfont = get_font(font.fontname, font.fontsize)
        fm = QFontMetrics(qfont)
        rect = fm.boundingRect(text)
        width, height = rect.width(), fm.ascent()   # rect.height()
        return width, height


class VectorRenderContext(vec.RenderContext, RenderContext):

    def __init__(self, renderer, viewer, surface):
        vec.RenderContext.__init__(self, renderer, viewer, surface)
        RenderContext.__init__(self, renderer, viewer, surface)


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

        CanvasRenderer.initialize(self)
        cr = RenderContext(self, self.viewer, self.surface)
        self.draw_vector(cr)

    def render_image(self, rgbobj, win_x, win_y):
        # just save the parameters to be called at finalize()
        self._img_args = (rgbobj, win_x, win_y)

    def setup_cr(self, shape):
        # special cr that just stores up a render list
        cr = VectorRenderContext(self, self.viewer, self.surface)
        return cr

    def get_dimensions(self, shape):
        cr = CanvasRenderer.setup_cr(self, shape)
        font = cr.get_font_from_shape(shape)
        return cr.text_extents(shape.text, font=font)

#END
