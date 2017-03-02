#
# ImageViewQtGL.py -- a backend for Ginga using Qt's QGLWidget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy
from io import BytesIO

from ginga.qtw.QtHelp import QtCore
from ginga.qtw import ImageViewQt
from ginga import Mixins, Bindings
import ginga.util.six as six
from ginga.util.six.moves import map, zip

# GL imports
# TODO: find how to import this from qtpy
if six.PY2:
    from PyQt4.QtOpenGL import QGLWidget as QOpenGLWidget
else:
    from PyQt5.QtOpenGL import QGLWidget as QOpenGLWidget

# Local imports
from ginga.opengl.CanvasRenderGL import CanvasRenderer


class ImageViewQtGLError(ImageViewQt.ImageViewQtError):
    pass


class RenderGLWidget(QOpenGLWidget):

    def __init__(self, *args, **kwdargs):
        QOpenGLWidget.__init__(self, *args, **kwdargs)

        self.viewer = None
        self._drawing = False

    def initializeGL(self):
        self.viewer.renderer.gl_initialize()

    def resizeGL(self, width, height):
        self.viewer.renderer.gl_resize(width, height)

    def paintGL(self):
        self.viewer.renderer.gl_paint()

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)


class ImageViewQtGL(ImageViewQt.ImageViewQt):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewQt.ImageViewQt.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        self.imgwin = RenderGLWidget()
        self.imgwin.viewer = self
        # Qt expects 32bit BGRA data for color images
        self.rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        """
        pos = (0, 0)
        arr = self.getwin_array(order=self.rgb_order, alpha=1.0)
        ## pos = (dst_x, dst_y)
        ## arr = rgbobj.get_array(self.rgb_order)
        self.renderer.gl_set_image(arr, pos)

    def configure_window(self, width, height):
        self.logger.debug("window size reconfigured to %dx%d" % (
            width, height))
        self.configure(width, height)

    def get_rgb_image_as_widget(self):
        return self.imgwin.grabFrameBuffer()

    def get_rgb_image_as_buffer(self, output=None, format='png',
                                quality=90):
        ibuf = output
        if ibuf is None:
            ibuf = BytesIO()

        qimg = self.get_rgb_image_as_widget()
        res = qimg.save(ibuf, format=format, quality=quality)
        return ibuf

    def update_image(self):
        if self.imgwin is None:
            return

        self.logger.debug("updating window")
        self.imgwin.update()

    def gl_update(self):
        self.imgwin.update()


class RenderGLWidgetZoom(ImageViewQt.RenderMixin, RenderGLWidget):
    pass


class ImageViewEvent(ImageViewQtGL, ImageViewQt.QtEventMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewQtGL.__init__(self, logger=logger, rgbmap=rgbmap,
                               settings=settings)

        # replace the widget our parent provided
        imgwin = RenderGLWidgetZoom()

        imgwin.viewer = self
        self.imgwin = imgwin

        ImageViewQt.QtEventMixin.__init__(self)


class ImageViewZoom(Mixins.UIMixin, ImageViewEvent):

    # class variables for binding map and bindings can be set
    bindmapClass = Bindings.BindingMapper
    bindingsClass = Bindings.ImageViewBindings

    @classmethod
    def set_bindingsClass(cls, klass):
        cls.bindingsClass = klass

    @classmethod
    def set_bindmapClass(cls, klass):
        cls.bindmapClass = klass

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, settings=settings,
                                rgbmap=rgbmap)
        Mixins.UIMixin.__init__(self)

        self.ui_setActive(True)

        if bindmap is None:
            bindmap = ImageViewZoom.bindmapClass(self.logger)
        self.bindmap = bindmap
        bindmap.register_for_events(self)

        if bindings is None:
            bindings = ImageViewZoom.bindingsClass(self.logger)
        self.set_bindings(bindings)

    def get_bindmap(self):
        return self.bindmap

    def get_bindings(self):
        return self.bindings

    def set_bindings(self, bindings):
        self.bindings = bindings
        bindings.set_bindings(self)


class CanvasView(ImageViewZoom):

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


#END
