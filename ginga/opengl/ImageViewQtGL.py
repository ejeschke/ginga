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
    # workaround for a bug: http://bugs.python.org/issue26245
    import OpenGL.GLU

from OpenGL import GL as gl

# Local imports
from ginga.opengl.Camera import Camera
from ginga.opengl.CanvasRenderGL import CanvasRenderer


class ImageViewQtGLError(ImageViewQt.ImageViewQtError):
    pass


class RenderGLWidget(QOpenGLWidget):

    def __init__(self, *args, **kwdargs):
        QOpenGLWidget.__init__(self, *args, **kwdargs)

        self.viewer = None
        self._drawing = False

        self.camera = Camera()
        self.camera.set_camera_home_position((0, 0, -1.6))
        self.camera.reset()

        self.draw_wrapper = False
        self.draw_spines = True

    def get_camera(self):
        return self.camera

    def initializeGL(self):
        r, g, b = self.viewer.img_bg
        gl.glClearColor(r, g, b, 1.0)
        gl.glClearDepth(1.0)

        gl.glDepthFunc(gl.GL_LEQUAL)
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glDisable(gl.GL_CULL_FACE)
        gl.glFrontFace(gl.GL_CCW)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glShadeModel(gl.GL_FLAT)
        #gl.glShadeModel(gl.GL_SMOOTH)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        self.camera.set_gl_transform()
        gl.glMatrixMode(gl.GL_MODELVIEW)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        self.tex_id = gl.glGenTextures(1)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex_id)
        ## gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
        ##                    gl.GL_CLAMP)
        ## gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
        ##                    gl.GL_CLAMP)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_NEAREST)

    def gl_set_image(self, img_np):
        ht, wd = img_np.shape[:2]
        # TODO: can we avoid this transformation?
        data = numpy.flipud(img_np[0:self.ht, 0: self.wd])
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, wd, ht, 0, gl.GL_RGB,
                        gl.GL_UNSIGNED_BYTE, data)

    def resizeGL(self, width, height):
        self.wd, self.ht = width, height
        self.camera.set_viewport_dimensions(width, height)
        gl.glViewport(0, 0, width, height)

        self.viewer.configure_window(width, height)

    def paintGL(self):
        self._drawing = True
        try:
            #print('paint!')
            gl.glMatrixMode(gl.GL_PROJECTION)
            gl.glLoadIdentity()
            self.camera.set_gl_transform()
            gl.glMatrixMode(gl.GL_MODELVIEW)
            gl.glLoadIdentity()

            r, g, b = self.viewer.img_bg
            gl.glClearColor(r, g, b, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            # calculate vertexes accounting for aspect ratio
            ln = float(max(self.wd, self.ht))
            wd_ln, ht_ln = self.wd / ln, self.ht / ln

            gl.glColor4f(1, 1, 1, 1.0)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glBegin(gl.GL_POLYGON)
            try:
                gl.glTexCoord(0, 0)
                gl.glVertex(wd_ln,  -ht_ln)
                gl.glTexCoord(1, 0)
                gl.glVertex(-wd_ln,  -ht_ln)
                gl.glTexCoord(1, 1)
                gl.glVertex(-wd_ln, ht_ln)
                gl.glTexCoord(0, 1)
                gl.glVertex(wd_ln, ht_ln)
            finally:
                gl.glEnd()

            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

            if self.draw_wrapper:
                # draw orienting wrapper around scene
                gl.glColor(1.0, 1.0, 1.0)
                gl.glBegin(gl.GL_LINE_STRIP)
                gl.glVertex(-1,-1,-1)
                gl.glVertex( 1,-1,-1)
                gl.glVertex( 1, 1,-1)
                gl.glVertex(-1, 1,-1)
                gl.glVertex(-1,-1, 1)
                gl.glVertex( 1,-1, 1)
                gl.glVertex( 1, 1, 1)
                gl.glVertex(-1, 1, 1)
                gl.glEnd()

            if self.draw_spines:
                # draw orienting spines radiating in x, y and z
                gl.glColor(1.0, 0.0, 0.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( -1, 0, 0)
                gl.glVertex( 1, 0, 0)
                gl.glEnd()
                gl.glColor(0.0, 1.0, 0.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( 0, -1, 0)
                gl.glVertex( 0, 1, 0)
                gl.glEnd()
                gl.glColor(0.0, 0.0, 1.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( 0, 0, -1)
                gl.glVertex( 0, 0, 1)
                gl.glEnd()

            p_canvas = self.viewer.get_private_canvas()
            p_canvas.draw(self.viewer)

        finally:
            self._drawing = False
            #print('paint done!')
            gl.glFlush()

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
        self._rgb_order = 'BGRA'

        self.renderer = CanvasRenderer(self)

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        """
        arr = self.getwin_array()
        self.imgwin.gl_set_image(arr)

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
        if not self.imgwin:
            return

        self.logger.debug("updating window")
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
