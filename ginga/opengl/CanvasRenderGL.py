#
# CanvasRenderGL.py -- for rendering into a OpenGL widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import numpy as np

# NOTE: we don't need GLU but we import it to workaround a
#   potential bug: http://bugs.python.org/issue26245
from OpenGL import GLU as glu
from OpenGL import GL as gl

from ginga.vec import CanvasRenderVec
from ginga.canvas import render, transform
# force registration of all canvas types
import ginga.canvas.types.all  # noqa
from ginga.canvas.transform import BaseTransform
from ginga.cairow import CairoHelp
from ginga import trcalc

# Local imports
from .Camera import Camera
from . import GlHelp

opengl_version = float("{}.{}".format(gl.glGetIntegerv(gl.GL_MAJOR_VERSION),
                                      gl.glGetIntegerv(gl.GL_MINOR_VERSION)))


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        # TODO: encapsulate this drawable
        self.cr = GlHelp.GlContext(surface)

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
            if (hasattr(shape, 'fontsize') and shape.fontsize is not None and
                not getattr(shape, 'fontscale', False)):
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            fontsize = self.scale_fontsize(fontsize)
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

    def setup_pen_brush(self, pen, brush):
        # pen, brush are from ginga.vec
        self.pen = self.cr.get_pen(pen.color, alpha=pen.alpha,
                                   linewidth=pen.linewidth)
        if brush is None:
            self.brush = None
        else:
            self.brush = self.cr.get_brush(brush.color, alpha=brush.alpha)

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontsize = self.scale_fontsize(fontsize)
        self.font = self.cr.get_font(fontname, fontsize, color,
                                     alpha=alpha)

    def text_extents(self, text):
        return self.cr.text_extents(text, self.font)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, image_id, cp, rgb_arr, whence, order='RGB'):
        """Render the image represented by (rgb_arr) at (cx, cy)
        in the pixel space.
        """
        cp = np.asarray(cp, dtype=np.float)

        # This bit is necessary because OpenGL assumes that pixels are
        # centered at 0.5 offsets from the start of the pixel.  Need to
        # follow the flip/swap transform of the viewer to make sure we
        # are applying the correct corner offset to each image corner
        # TODO: see if there is something we can set in OpenGL so that
        # we don't have to do this hack
        off = 0.5
        off = np.array(((-off, -off), (off, -off), (off, off), (-off, off)))
        tr = transform.FlipSwapTransform(self.viewer)
        cp += tr.to_(off)

        #if whence < 2.5:
        #    self.viewer.prepare_image(image_id, cp, rgb_arr, whence)

        gl.glColor4f(1, 1, 1, 1.0)
        gl.glEnable(gl.GL_TEXTURE_2D)
        # TODO: either image_id is the GL texture id or there is an accessible
        # mapping to one
        image_id = self.renderer.tex_id
        gl.glBindTexture(gl.GL_TEXTURE_2D, image_id)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)
        gl.glBegin(gl.GL_QUADS)
        try:
            gl.glTexCoord(0, 0)
            gl.glVertex(cp[0][0], cp[0][1])
            gl.glTexCoord(1, 0)
            gl.glVertex(cp[1][0], cp[1][1])
            gl.glTexCoord(1, 1)
            gl.glVertex(cp[2][0], cp[2][1])
            gl.glTexCoord(0, 1)
            gl.glVertex(cp[3][0], cp[3][1])
        finally:
            gl.glEnd()

        gl.glDisable(gl.GL_TEXTURE_2D)
        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        # TODO: this draws text as polygons, since there is no native
        # text support in OpenGL.  It uses cairo to convert the text to
        # paths.  Currently the paths are drawn, but not filled correctly.
        paths = CairoHelp.text_to_paths(text, self.font, flip_y=True,
                                        cx=cx, cy=cy, rot_deg=rot_deg)
        scale = self.viewer.get_scale()
        base = np.array((cx, cy))

        for pts in paths:
            # we have to rotate and scale the polygons to account for the
            # odd transform we use for OpenGL
            rot_deg = -self.viewer.get_rotation()
            if rot_deg != 0.0:
                pts = trcalc.rotate_coord(pts, [rot_deg], (cx, cy))
            pts = (pts - base) * (1 / scale) + base
            self.set_line(self.font.color, alpha=self.font.alpha)
            self.set_fill(None)
            self.draw_polygon(pts)

    def _draw_pts(self, shape, cpoints):

        if not self.renderer._drawing:
            # this test ensures that we are not trying to draw before
            # the OpenGL context is set for us correctly
            return

        z_pts = cpoints

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
        cpoints = []
        for i in range(0, num_segments):
            theta = 2.0 * np.pi * i / float(num_segments)
            dx = cradius * np.cos(theta)
            dy = cradius * np.sin(theta)
            cpoints.append((cx + dx, cy + dy))

        self._draw_pts(gl.GL_POLYGON, cpoints)

    def draw_line(self, cx1, cy1, cx2, cy2):
        cpoints = [(cx1, cy1), (cx2, cy2)]
        self._draw_pts(gl.GL_LINES, cpoints)

    def draw_path(self, cpoints):
        self._draw_pts(gl.GL_LINE_STRIP, cpoints)


class CanvasRenderer(CanvasRenderVec.CanvasRenderer):

    def __init__(self, viewer):
        CanvasRenderVec.CanvasRenderer.__init__(self, viewer)

        self.kind = 'gl'
        self.rgb_order = 'RGBA'
        self.surface = self.viewer.get_widget()

        # size of our GL viewport
        # these will change when the resize() is called
        self.wd, self.ht = 10, 10

        self.camera = Camera()
        self.camera.set_scene_radius(2)
        self.camera.set_camera_home_position((0, 0, 1000))
        self.camera.reset()

        self.draw_wrapper = False
        self.mode3d = True
        self.draw_spines = True
        self._drawing = False

        # initial values, will be recalculated at window map/resize
        self.lim_x, self.lim_y, self.lim_z = 1.0, 1.0, 1.0
        self.mn_x, self.mx_x = -self.lim_x, self.lim_x
        self.mn_y, self.mx_y = -self.lim_y, self.lim_y
        self.mn_z, self.mx_z = -self.lim_z, self.lim_z

    def set_3dmode(self, tf):
        self.mode3d = tf
        self.gl_resize(self.wd, self.ht)
        scales = self.viewer.get_scale_xy()
        self.scale(scales)

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        super(CanvasRenderer, self).resize(dims)

        width, height = dims[:2]
        self.gl_resize(width, height)

        self.viewer.redraw(whence=2.5)

    def reset_ortho_projection(self):
        pts = np.asarray(self.viewer.get_pan_rect())
        x, y = self.viewer.tform['data_to_native'].to_(pts).T

        self.mn_x, self.mx_x = x.min(), x.max()
        self.mn_y, self.mx_y = y.min(), y.max()
        self.mn_z, self.mx_z = 0.0, 1.0

    def scale(self, scales):
        if not self.mode3d:
            self.reset_ortho_projection()
            self.viewer.gl_update()
        else:
            self.camera.scale_2d(scales[:2])
            #self.viewer.gl_update()

        self.viewer.redraw(whence=2.5)
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', whence=0.0)

    def pan(self, pos):
        self.viewer.redraw(whence=2.5)
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', whence=0.0)

    def rotate_2d(self, ang_deg):
        if self.mode3d:
            self.camera.rotate_2d(ang_deg)
            #self.viewer.gl_update()

        self.viewer.redraw(whence=2.6)

    def transform_2d(self, state):
        self.viewer.redraw(whence=2.5)

    def _common_draw(self, cvs_img, cache, whence):
        # internal common drawing phase for all images
        image = cvs_img.image
        if image is None:
            return
        viewer = self.viewer

        if (whence <= 0.0) or (cache.cutout is None) or (not cvs_img.optimize):

            # get destination location in data_coords
            dst_x, dst_y = cvs_img.crdmap.to_data((cvs_img.x, cvs_img.y))

            ## a1, b1, a2, b2 = 0, 0, cvs_img.image.width - 1, cvs_img.image.height - 1

            ## # scale by our scale
            ## _scale_x, _scale_y = cvs_img.scale_x, cvs_img.scale_y

            ## interp = cvs_img.interpolation
            ## if interp is None:
            ##     t_ = viewer.get_settings()
            ##     interp = t_.get('interpolation', 'basic')

            ## # previous choice might not be available if preferences
            ## # were saved when opencv was being used (and not used now);
            ## # if so, silently default to "basic"
            ## if interp not in trcalc.interpolation_methods:
            ##     interp = 'basic'
            ## res = image.get_scaled_cutout2((a1, b1), (a2, b2),
            ##                                (_scale_x, _scale_y),
            ##                                method=interp)
            ## data = res.data

            data = image.get_data()

            if cvs_img.flipy:
                data = np.flipud(data)

            cache.cutout = data

            # calculate our offset
            pan_off = viewer.data_off
            cvs_x, cvs_y = dst_x - pan_off, dst_y - pan_off

            cache.cvs_pos = (cvs_x, cvs_y)

    def _prepare_image(self, cvs_img, cache, whence):
        self._common_draw(cvs_img, cache, whence)

        cache.rgbarr = trcalc.add_alpha(cache.cutout, alpha=255)
        cache.drawn = True

    def _prepare_norm_image(self, cvs_img, cache, whence):
        t1 = t2 = t3 = t4 = time.time()

        self._common_draw(cvs_img, cache, whence)

        if cache.cutout is None:
            return

        t2 = time.time()
        if cvs_img.rgbmap is not None:
            rgbmap = cvs_img.rgbmap
        else:
            rgbmap = self.viewer.get_rgbmap()

        image_order = cvs_img.image.get_order()

        if (whence <= 0.0) or (not cvs_img.optimize):
            # if image has an alpha channel, then strip it off and save
            # it until it is recombined later with the colorized output
            # this saves us having to deal with an alpha band in the
            # cuts leveling and RGB mapping routines
            img_arr = cache.cutout
            if 'A' not in image_order:
                cache.alpha = None
            else:
                # normalize alpha array to the final output range
                mn, mx = trcalc.get_minmax_dtype(img_arr.dtype)
                a_idx = image_order.index('A')
                cache.alpha = (img_arr[..., a_idx] / mx *
                               rgbmap.maxc).astype(rgbmap.dtype)
                cache.cutout = img_arr[..., 0:a_idx]

        if (whence <= 1.0) or (cache.prergb is None) or (not cvs_img.optimize):
            # apply visual changes prior to color mapping (cut levels, etc)
            vmax = rgbmap.get_hash_size() - 1
            newdata = self._apply_visuals(cvs_img, cache.cutout, 0, vmax)

            # result becomes an index array fed to the RGB mapper
            if not np.issubdtype(newdata.dtype, np.dtype('uint')):
                newdata = newdata.astype(np.uint)
            idx = newdata

            self.logger.debug("shape of index is %s" % (str(idx.shape)))
            cache.prergb = idx

        t3 = time.time()
        dst_order = self.viewer.get_rgb_order()

        if (whence <= 2.0) or (cache.rgbarr is None) or (not cvs_img.optimize):
            # get RGB mapped array
            rgbobj = rgbmap.get_rgbarray(cache.prergb, order=dst_order,
                                         image_order=image_order)
            cache.rgbarr = rgbobj.get_array(dst_order)

            if cache.alpha is not None and 'A' in dst_order:
                a_idx = dst_order.index('A')
                cache.rgbarr[..., a_idx] = cache.alpha

        t4 = time.time()

        #cache.rgbarr = trcalc.add_alpha(cache.rgbarr, alpha=255)

        cache.drawn = True
        t5 = time.time()
        self.logger.debug("draw: t2=%.4f t3=%.4f t4=%.4f t5=%.4f total=%.4f" % (
            t2 - t1, t3 - t2, t4 - t3, t5 - t4, t5 - t1))


    def prepare_image(self, cvs_img, cache, whence):
        if cvs_img.kind == 'image':
            self._prepare_image(cvs_img, cache, whence)
        elif cvs_img.kind == 'normimage':
            self._prepare_norm_image(cvs_img, cache, whence)
        else:
            raise RenderError("I don't know how to render canvas type '{}'".format(cvs_img.kind))

        image_id = self.tex_id
        self.gl_set_image(image_id, cache.rgbarr)

    ## def initialize(self):
    ##     self.rl = []

    def finalize(self):
        # a no-op for this renderer
        pass

    def get_surface_as_array(self, order=None):
        win_wd, win_ht = self.viewer.get_window_size()
        image_buffer = gl.glReadPixels(0, 0, width, height, gl.GL_RGB,
                                       gl.GL_UNSIGNED_BYTE)
        image = np.frombuffer(image_buffer, dtype=np.uint8).reshape(width,
                                                                    height, 3)
        return image

    def render_whence(self, whence):
        # a no-op for this renderer
        pass

    ## def setup_cr(self, shape):
    ##     cr = CanvasRenderVec.RenderContext(self, self.viewer, self.surface)
    ##     cr.initialize_from_shape(shape, font=False)
    ##     return cr

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font(font.fontname, font.fontsize, color=font.color,
                    alpha=font.alpha)
        return cr.text_extents(text)

    ## def get_dimensions(self, shape):
    ##     cr = self.setup_cr(shape)
    ##     cr.set_font_from_shape(shape)
    ##     return cr.text_extents(shape.text)

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
                       self.mn_z, self.mx_z)
            #gl.glRotatef(45.0, 0.0, 0.0, 0.0)

        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

    def getOpenGLInfo(self):
        info = dict(vendor=gl.glGetString(gl.GL_VENDOR).decode(),
                    renderer=gl.glGetString(gl.GL_RENDERER).decode(),
                    opengl_version=gl.glGetString(gl.GL_VERSION).decode(),
                    shader_version=gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).decode())
        return info

    def gl_initialize(self):
        d = self.getOpenGLInfo()
        self.logger.info("OpenGL info--Vendor: '%(vendor)s'  "
                         "Renderer: '%(renderer)s'  "
                         "Version: '%(opengl_version)s'  "
                         "Shader: '%(shader_version)s'" % d)

        r, g, b = self.viewer.img_bg
        gl.glClearColor(r, g, b, 1.0)
        gl.glClearDepth(1.0)

        gl.glDisable(gl.GL_CULL_FACE)
        gl.glFrontFace(gl.GL_CCW)
        if opengl_version < 4:
            gl.glDisable(gl.GL_LIGHTING)
            gl.glShadeModel(gl.GL_FLAT)
            #gl.glShadeModel(gl.GL_SMOOTH)

        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
        self.tex_id = gl.glGenTextures(1)

    def gl_set_image(self, image_id, rgb_arr):
        """NOTE: this is a slow operation--downloading a texture."""
        ht, wd = rgb_arr.shape[:2]

        gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex_id)
        ## gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
        ##                    gl.GL_CLAMP)
        ## gl.glTexParameterf(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
        ##                    gl.GL_CLAMP)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_NEAREST)

        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, wd, ht, 0,
                        gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, rgb_arr)

    ## def gl_set_image_interpolation(self, interp):
    ##     gl.glBindTexture(gl.GL_TEXTURE_2D, self.tex_id)
    ##     if interp in ['nearest', 'basic']:
    ##         gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
    ##                            gl.GL_NEAREST)
    ##         gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
    ##                            gl.GL_NEAREST)
    ##     elif interp in ['bilinear']:
    ##         gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
    ##                            gl.GL_LINEAR)
    ##         gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
    ##                            gl.GL_LINEAR)

    def gl_resize(self, width, height):
        self.wd, self.ht = width, height

        if not self.mode3d:
            self.reset_ortho_projection()

        else:
            self.camera.set_viewport_dimensions(width, height)

        gl.glViewport(0, 0, width, height)

    def gl_paint(self):
        self._drawing = True
        try:
            self.setup_3D(self.mode3d)

            r, g, b = self.viewer.img_bg
            gl.glClearColor(r, g, b, 1.0)
            gl.glClearDepth(1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            cr = RenderContext(self, self.viewer, self.surface)
            self.draw_vector(cr)

            if self.mode3d and self.draw_spines:
                # for debugging
                self._draw_spines()

        finally:
            self._drawing = False
            gl.glFlush()

    def _draw_spines(self):
        # draw orienting spines radiating in x, y and z
        gl.glColor(1.0, 0.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex(self.mn_x, 0, 0)
        gl.glVertex(self.mx_x, 0, 0)
        gl.glEnd()
        gl.glColor(0.0, 1.0, 0.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex(0, self.mn_y, 0)
        gl.glVertex(0, self.mx_y, 0)
        gl.glEnd()
        gl.glColor(0.0, 0.0, 1.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex(0, 0, self.mn_z)
        gl.glVertex(0, 0, self.mx_z)
        gl.glEnd()

# END
