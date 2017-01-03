#
# CanvasRenderGL.py -- for rendering into a OpenGL widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import numpy

# NOTE: we need GLU, but even if we didn't we should import it to
#   workaround for a bug: http://bugs.python.org/issue26245
from OpenGL import GLU as glu
from OpenGL import GL as gl

from ginga import colors
from ginga.util.six.moves import map, zip
# force registration of all canvas types
import ginga.canvas.types.all

# Local imports
from .Camera import Camera
from . import GlHelp

class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer
        self.renderer = viewer.renderer

        # TODO: encapsulate this drawable
        self.cr = GlHelp.GlContext(viewer.get_widget())

        self.pen = None
        self.brush = None
        self.font = None

    def set_line_from_shape(self, shape):
        alpha = getattr(shape, 'alpha', 1.0)
        linewidth = getattr(shape, 'linewidth', 1.0)
        linestyle = getattr(shape, 'linestyle', 'solid')
        self.pen = self.cr.get_pen(shape.color, linewidth=linewidth,
                                   linestyle=linestyle, alpha=alpha)

    def set_fill_from_shape(self, shape):
        fill = getattr(shape, 'fill', False)
        if fill:
            if hasattr(shape, 'fillcolor') and shape.fillcolor:
                color = shape.fillcolor
            else:
                color = shape.color
            alpha = getattr(shape, 'alpha', 1.0)
            alpha = getattr(shape, 'fillalpha', alpha)
            self.brush = self.cr.get_brush(color, alpha=alpha)
        else:
            self.brush = None

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            alpha = getattr(shape, 'alpha', 1.0)
            self.font = self.cr.get_font(shape.font, fontsize, shape.color,
                                         alpha=alpha)
        else:
            self.font = None

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):
        self.pen = self.cr.get_pen(color, linewidth=linewidth,
                                   linestyle=style, alpha=alpha)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(color, alpha=alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)


    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        # TODO
        pass

    def cvs_to_gl(self, pt):
        x, y = pt
        sx, sy = x - self.renderer.lim_x, self.renderer.lim_y - y
        sz = 1 if not self.renderer.mode3d else 10
        return (sx, sy, sz)

    def _draw_pts(self, shape, cpoints):

        if not self.renderer._drawing:
            # this test ensures that we are not trying to draw before
            # the OpenGL context is set for us correctly
            return

        #print('drawing canvas')

        z_pts = numpy.array(list(map(self.cvs_to_gl, cpoints)))

        gl.glEnableClientState(gl.GL_VERTEX_ARRAY)

        # draw fill, if any
        if self.brush is not None:
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glColor4f(*self.brush.color)

            gl.glVertexPointerf(z_pts)
            gl.glDrawArrays(shape, 0, len(z_pts))

        if self.pen is not None and self.pen.linewidth > 0:
            # draw outline
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
            gl.glColor4f(*self.pen.color)
            gl.glLineWidth(self.pen.linewidth)

            if self.pen.linestyle == 'dash':
                gl.glEnable(gl.GL_LINE_STIPPLE)
                gl.glLineStipple(3, 0x1C47)

            gl.glVertexPointerf(z_pts)
            gl.glDrawArrays(shape, 0, len(z_pts))

            if self.pen.linestyle == 'dash':
                gl.glDisable(gl.GL_LINE_STIPPLE)

        gl.glDisableClientState(gl.GL_VERTEX_ARRAY)

    def draw_polygon(self, cpoints):
        self._draw_pts(gl.GL_POLYGON, cpoints)

    def draw_circle(self, cx, cy, cradius):
        # we have to approximate a circle in OpenGL
        # TODO: there is a more efficient algorithm described here:
        # http://slabode.exofire.net/circle_draw.shtml
        num_segments = 360
        z_pts = []
        for i in range(0, num_segments):
            theta = 2.0 * numpy.pi * i / float(num_segments)
            dx = cradius * numpy.cos(theta)
            dy = cradius * numpy.sin(theta)
            z_pts.append((cx + dx, cy + dy))

        self._draw_pts(gl.GL_LINE_LOOP, z_pts)

    def draw_line(self, cx1, cy1, cx2, cy2):
        z_pts = [(cx1, cy1), (cx2, cy2)]
        self._draw_pts(gl.GL_LINES, z_pts)

    def draw_path(self, cpoints):
        self._draw_pts(gl.GL_LINE_STRIP, cpoints)

class CanvasRenderer(object):

    def __init__(self, viewer):
        self.viewer = viewer

        # size of our GL viewport
        # these will change when the resize() is called
        self.wd, self.ht = 10, 10

        self.camera = Camera()
        self.camera.set_scene_radius(2)
        #self.camera.set_camera_home_position((0, 0, -self.wd))
        self.camera.reset()

        self.draw_wrapper = False
        self.draw_spines = True
        self.mode3d = False
        self._drawing = False

        # initial values, will be recalculated at window map/resize
        self.lim_x, self.lim_y = 10, 10
        self.mn_x, self.mx_x = -self.lim_x, self.lim_x
        self.mn_y, self.mx_y = -self.lim_y, self.lim_y

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

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

    def gl_initialize(self):
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

    def gl_set_image(self, img_np, pos):
        dst_x, dst_y = pos
        # TODO: can we avoid this transformation?
        data = numpy.flipud(img_np[0:self.ht, 0:self.wd])
        ht, wd = data.shape[:2]

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, wd, ht, 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, data)

    def gl_resize(self, width, height):
        self.wd, self.ht = width, height
        self.lim_x, self.lim_y = width / 2.0, height / 2.0

        self.mn_x, self.mx_x = -self.lim_x, self.lim_x
        self.mn_y, self.mx_y = -self.lim_y, self.lim_y

        self.camera.set_viewport_dimensions(width, height)
        gl.glViewport(0, 0, width, height)

    def gl_paint(self):
        self._drawing = True
        try:
            self.setup_3D(self.mode3d)

            r, g, b = self.viewer.img_bg
            gl.glClearColor(r, g, b, 1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            # Draw the image portion of the plot
            gl.glColor4f(1, 1, 1, 1.0)
            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
            gl.glBegin(gl.GL_QUADS)
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
            gl.glFlush()

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

#END
