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

# NOTE: we need GLU, but even if we didn't we should import it to
#   workaround for a bug: http://bugs.python.org/issue26245
from OpenGL import GLU as glu
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

        # size of our window, and therefore viewport
        # these will change when the resizeGL() is called
        self.wd, self.ht = 10, 10

        self.camera = Camera()
        self.camera.set_scene_radius(2)
        #self.camera.set_camera_home_position((0, 0, -self.wd))
        self.camera.reset()

        self.draw_wrapper = False
        self.draw_spines = True
        self.mode3d = False

        # initial values, will be recalculated at window map/resize
        self.lim_x, self.lim_y = 10, 10
        self.mn_x, self.mx_x = -self.lim_x, self.lim_x
        self.mn_y, self.mx_y = -self.lim_y, self.lim_y

    def get_camera(self):
        return self.camera

    def setup_3D(self, mode3d):
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()

        if mode3d:
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glEnable(gl.GL_DEPTH_TEST)

            self.camera.set_gl_transform()
        else:
            gl.glDisable(gl.GL_DEPTH_TEST)
            gl.glOrtho(self.mn_x, self.mx_x, self.mn_y, self.mx_y,
                       -1.0, 100.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def initializeGL(self):
        r, g, b = self.viewer.img_bg
        gl.glClearColor(r, g, b, 1.0)
        gl.glClearDepth(1.0)

        gl.glDisable(gl.GL_CULL_FACE)
        gl.glFrontFace(gl.GL_CCW)
        gl.glDisable(gl.GL_LIGHTING)
        gl.glShadeModel(gl.GL_FLAT)
        #gl.glShadeModel(gl.GL_SMOOTH)

        self.setup_3D(self.mode3d)

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

    def gl_set_image(self, img_np, dst_x, dst_y):
        # TODO: can we avoid this transformation?
        data = numpy.flipud(img_np[0:self.ht, 0:self.wd])
        ht, wd = data.shape[:2]
        #print("received image %dx%d" % (wd, ht))

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, wd, ht, 0, gl.GL_RGB,
                        gl.GL_UNSIGNED_BYTE, data)

    def resizeGL(self, width, height):
        #print("resize to %dx%d" % (width, height))
        self.wd, self.ht = width, height
        self.lim_x, self.lim_y = width / 2.0, height / 2.0

        self.mn_x, self.mx_x = -self.lim_x, self.lim_x
        self.mn_y, self.mx_y = -self.lim_y, self.lim_y

        self.camera.set_viewport_dimensions(width, height)
        gl.glViewport(0, 0, width, height)

        self.viewer.configure_window(width, height)
        #self.update()

    def paintGL(self):
        self._drawing = True
        try:
            #print('paint!')
            self.setup_3D(self.mode3d)

            r, g, b = self.viewer.img_bg
            gl.glClearColor(r, g, b, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            # Draw the image portion of the plot
            gl.glColor4f(1, 1, 1, 1.0)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glBegin(gl.GL_POLYGON)
            try:
                gl.glTexCoord(0, 0)
                gl.glVertex(self.mn_x, self.mn_y)
                gl.glTexCoord(1, 0)
                gl.glVertex(self.mx_x, self.mn_y)
                gl.glTexCoord(1, 1)
                gl.glVertex(self.mx_x, self.mx_y)
                gl.glTexCoord(0, 1)
                gl.glVertex(self.mn_x, self.mx_y)
            finally:
                gl.glEnd()

            gl.glDisable(gl.GL_TEXTURE_2D)
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

            lim = max(self.lim_x, self.lim_y)

            if self.mode3d and self.draw_wrapper:
                # draw orienting wrapper around scene
                gl.glColor(1.0, 1.0, 1.0)
                gl.glBegin(gl.GL_LINE_STRIP)
                gl.glVertex(-lim, -lim, -lim)
                gl.glVertex( lim, -lim, -lim)
                gl.glVertex( lim, lim, -lim)
                gl.glVertex(-lim, lim, -lim)
                gl.glVertex(-lim, -lim, lim)
                gl.glVertex( lim, -lim, lim)
                gl.glVertex( lim, lim, lim)
                gl.glVertex(-lim, lim, lim)
                gl.glEnd()

            if self.mode3d and self.draw_spines:
                # draw orienting spines radiating in x, y and z
                gl.glColor(1.0, 0.0, 0.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( -lim, 0, 0)
                gl.glVertex( lim, 0, 0)
                gl.glEnd()
                gl.glColor(0.0, 1.0, 0.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( 0, -lim, 0)
                gl.glVertex( 0, lim, 0)
                gl.glEnd()
                gl.glColor(0.0, 0.0, 1.0)
                gl.glBegin(gl.GL_LINES)
                gl.glVertex( 0, 0, -lim)
                gl.glVertex( 0, 0, lim)
                gl.glEnd()

            # Draw the overlays
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

    def pix2canvas(self, pt):
        """Takes a 2-tuple of (x, y) in window coordinates and gives
        the (cx, cy, cz) coordinates on the canvas.
        """
        x, y = pt
        mm = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
        pm = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
        vp = gl.glGetIntegerv(gl.GL_VIEWPORT)

        win_x, win_y = float(x), float(vp[3] - y)
        win_z = gl.glReadPixels(int(x), int(win_y), 1, 1, gl.GL_DEPTH_COMPONENT,
                                gl.GL_FLOAT)
        pos = glu.gluUnProject(win_x, win_y, win_z, mm, pm, vp)
        return pos

    def canvas2pix(self, pos):
        """Takes a 3-tuple of (cx, cy, cz) in canvas coordinates and gives
        the (x, y, z) pixel coordinates in the window.
        """
        x, y, z = pos
        mm = gl.glGetDoublev(gl.GL_MODELVIEW_MATRIX)
        pm = gl.glGetDoublev(gl.GL_PROJECTION_MATRIX)
        vp = gl.glGetIntegerv(gl.GL_VIEWPORT)

        pt = glu.gluProject(x, y, z, mm, pm, vp)
        return pt

    def get_bbox(self):
        return (self.pix2canvas((0, 0)),
                self.pix2canvas((self.wd, 0)),
                self.pix2canvas((self.wd, self.ht)),
                self.pix2canvas((0, self.ht))
                )

class ImageViewQtGL(ImageViewQt.ImageViewQt):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewQt.ImageViewQt.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        self.imgwin = RenderGLWidget()
        self.imgwin.viewer = self
        # Qt expects 32bit BGRA data for color images
        self._rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        """
        arr = self.getwin_array()
        self.imgwin.gl_set_image(arr, 0, 0)
        #arr = rgbobj.get_array(self._rgb_order)
        #self.imgwin.gl_set_image(arr, dst_x, dst_y)

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
