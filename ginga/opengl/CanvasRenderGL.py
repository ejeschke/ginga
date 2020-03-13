#
# CanvasRenderGL.py -- for rendering into a OpenGL widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import os.path
import numpy as np
import ctypes

from OpenGL import GL as gl

from ginga.vec import CanvasRenderVec as vec
from ginga.canvas import render, transform
from ginga.cairow import CairoHelp
from ginga import trcalc

# Local imports
from .Camera import Camera
from . import GlHelp
from .glsl import __file__
shader_dir, _ = os.path.split(__file__)

# NOTE: we update the version later in gl_initialize()
opengl_version = 3.0


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
                                   linewidth=pen.linewidth,
                                   linestyle=pen.linestyle)
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

    def draw_image(self, cvs_img, cp, rgb_arr, whence, order='RGB'):
        """Render the image represented by (rgb_arr) at (cx, cy)
        in the pixel space.
        """
        cp = np.asarray(cp, dtype=np.float32)

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

        self.renderer.gl_draw_image(cvs_img, cp)

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
            # NOTE: since non-convex polygons are not filled correctly, it
            # doesn't work to set any fill here
            self.set_fill(None)
            self.draw_polygon(pts)

    def draw_polygon(self, cpoints):
        self.renderer.gl_draw_shape(gl.GL_LINE_LOOP, cpoints,
                                    self.brush, self.pen)

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

        self.renderer.gl_draw_shape(gl.GL_LINE_LOOP, cpoints,
                                    self.brush, self.pen)

    def draw_line(self, cx1, cy1, cx2, cy2):
        cpoints = [(cx1, cy1), (cx2, cy2)]
        self.renderer.gl_draw_shape(gl.GL_LINES, cpoints,
                                    self.brush, self.pen)

    def draw_path(self, cpoints):
        self.renderer.gl_draw_shape(gl.GL_LINE_STRIP, cpoints,
                                    self.brush, self.pen)


class CanvasRenderer(vec.VectorRenderMixin, render.StandardPixelRenderer):

    def __init__(self, viewer):
        render.StandardPixelRenderer.__init__(self, viewer)
        vec.VectorRenderMixin.__init__(self)

        self.kind = 'opengl'
        self.rgb_order = 'RGBA'
        self.surface = self.viewer.get_widget()
        self.use_offscreen_fbo = False

        # size of our GL viewport
        # these will change when the resize() is called
        self.wd, self.ht = 10, 10

        self.camera = Camera()
        self.camera.set_scene_radius(2)
        self.camera.set_camera_home_position((0, 0, 1000))
        self.camera.reset()

        self.mode3d = True
        self._drawing = False
        self._initialized = False
        self._tex_cache = dict()
        self._levels = (0.0, 0.0)
        self._rgbmap_created = False
        self.max_texture_dimension = 0

        self.pgm_mgr = GlHelp.ShaderManager(self.logger)

        self.fbo = None
        self.color_buf = None
        self.depth_buf = None

    def set_3dmode(self, tf):
        self.mode3d = tf
        self.gl_resize(self.wd, self.ht)
        scales = self.viewer.get_scale_xy()
        self.scale(scales)

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        if self._initialized:
            self._resize(dims)

            width, height = dims[:2]
            self.gl_resize(width, height)

            self.viewer.update_image()

            # this is necessary for other widgets to get the same kind of
            # callback as for the standard pixel renderer
            self.viewer.make_callback('redraw', 0.0)

    def scale(self, scales):
        self.camera.scale_2d(scales[:2])

        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 0.0)

    def pan(self, pos):
        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 0.0)

    def rotate_2d(self, ang_deg):
        self.camera.rotate_2d(ang_deg)

        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 2.6)

    def rgbmap_change(self, rgbmap):
        self.gl_set_cmap(rgbmap)

        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 2.0)

    def bg_change(self, bg):
        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 3.0)

    def levels_change(self, levels):
        self._levels = levels

        self.viewer.update_image()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 1.0)

    def _common_draw(self, cvs_img, cache, whence):
        # internal common drawing phase for all images
        image = cvs_img.image
        if image is None:
            return
        viewer = self.viewer

        if (whence <= 0.0) or (cache.cutout is None) or (not cvs_img.optimize):
            # TODO: images larger than self.max_texture_dim in any
            # dimension need to be downsampled to fit!

            # get destination location in data_coords
            dst_x, dst_y = cvs_img.crdmap.to_data((cvs_img.x, cvs_img.y))

            a1, b1, a2, b2 = 0, 0, image.width - 1, image.height - 1

            # scale by our scale
            _scale_x, _scale_y = cvs_img.scale_x, cvs_img.scale_y

            interp = cvs_img.interpolation
            if interp is None:
                t_ = viewer.get_settings()
                interp = t_.get('interpolation', 'basic')

            # previous choice might not be available if preferences
            # were saved when opencv was being used (and not used now);
            # if so, silently default to "basic"
            if interp not in trcalc.interpolation_methods:
                interp = 'basic'
            res = image.get_scaled_cutout2((a1, b1), (a2, b2),
                                           (_scale_x, _scale_y),
                                           method=interp)
            data = res.data

            if cvs_img.flipy:
                data = np.flipud(data)

            if len(data.shape) == 2:
                # <-- monochrome image
                dtype = np.float32
            else:
                dtype = np.uint8

            cache.cutout = np.ascontiguousarray(data, dtype=dtype)

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

        print('prepare norm image', whence)
        if (whence <= 0.0) or (not cvs_img.optimize):
            # if image has an alpha channel, then strip it off and save
            # it until it is recombined later with the colorized output
            # this saves us having to deal with an alpha band in the
            # cuts leveling and RGB mapping routines
            img_arr = cache.cutout
            print('cutout', img_arr.shape, img_arr.dtype)
            if 'A' not in image_order:
                cache.alpha = None
            else:
                # normalize alpha array to the final output range
                mn, mx = trcalc.get_minmax_dtype(img_arr.dtype)
                a_idx = image_order.index('A')
                cache.alpha = (img_arr[..., a_idx] / mx *
                               rgbmap.maxc).astype(rgbmap.dtype)
                cache.cutout = img_arr[..., 0:a_idx]

        if cvs_img.rgbmap is not None or len(cache.cutout.shape) > 2:

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

        ## #cache.imgarr = trcalc.add_alpha(cache.rgbarr, alpha=255)

        cache.drawn = True
        t5 = time.time()
        self.logger.debug("draw: t2=%.4f t3=%.4f t4=%.4f t5=%.4f total=%.4f" % (
            t2 - t1, t3 - t2, t4 - t3, t5 - t4, t5 - t1))

    def prepare_image(self, cvs_img, cache, whence):
        if cvs_img.kind == 'image':
            self._prepare_image(cvs_img, cache, whence)
            img_arr = cache.rgbarr
            cache.image_type = 0

        elif cvs_img.kind == 'normimage':
            self._prepare_norm_image(cvs_img, cache, whence)
            if len(cache.cutout.shape) == 2:
                # <-- monochrome image with adjustable RGB map
                img_arr = cache.cutout
                cache.image_type = 2
            else:
                img_arr = cache.rgbarr
                cache.image_type = 1
            print('img_arr', img_arr.dtype, img_arr.shape)

        else:
            raise render.RenderError("I don't know how to render canvas type '{}'".format(cvs_img.kind))

        tex_id = self.get_texture_id(cvs_img.image_id)
        self.gl_set_image(tex_id, img_arr)

    def get_texture_id(self, image_id):
        tex_id = self._tex_cache.get(image_id, None)
        if tex_id is None:
            context = self.viewer.make_context_current()
            print('get_texture_id', image_id)
            tex_id = gl.glGenTextures(1)
            self._tex_cache[image_id] = tex_id
        return tex_id

    def render_whence(self, whence):
        if whence <= 2.0:
            p_canvas = self.viewer.get_private_canvas()
            self._overlay_images(p_canvas, whence=whence)

    def get_camera(self):
        return self.camera

    def getOpenGLInfo(self):
        self.max_texture_dim = gl.glGetIntegerv(gl.GL_MAX_TEXTURE_SIZE)
        info = dict(vendor=gl.glGetString(gl.GL_VENDOR).decode(),
                    renderer=gl.glGetString(gl.GL_RENDERER).decode(),
                    opengl_version=gl.glGetString(gl.GL_VERSION).decode(),
                    shader_version=gl.glGetString(gl.GL_SHADING_LANGUAGE_VERSION).decode(),
                    max_tex="{}x{}".format(self.max_texture_dim,
                                           self.max_texture_dim))
        return info

    def gl_initialize(self):
        global opengl_version
        print('gl_initialize')
        context = self.viewer.make_context_current()

        d = self.getOpenGLInfo()
        self.logger.info("OpenGL info--Vendor: '%(vendor)s'  "
                         "Renderer: '%(renderer)s'  "
                         "Version: '%(opengl_version)s'  "
                         "Shader: '%(shader_version)s' "
                         "Max texture: '%(max_tex)s'" % d)

        opengl_version = float(d['opengl_version'].split(' ')[0])

        if self.use_offscreen_fbo:
            self.create_offscreen_fbo()

        ## r, g, b = self.viewer.img_bg
        ## gl.glClearColor(r, g, b, 1.0)
        ## gl.glClearDepth(1.0)

        # --- line drawing shaders ---
        self.pgm_mgr.load_program('shape', shader_dir)

        # --- setup VAO for line drawing ---
        shader = self.pgm_mgr.setup_program('shape')

        # Create a new VAO (Vertex Array Object) and bind it
        self.vao_line = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao_line)

        # Generate buffers to hold our vertices
        self.vbo_line = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_line)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, None, gl.GL_DYNAMIC_DRAW)
        # Get the position of the 'position' in parameter of our shader
        # and bind it.
        _pos = gl.glGetAttribLocation(shader, 'position')
        gl.glEnableVertexAttribArray(_pos)
        # Describe the position data layout in the buffer
        gl.glVertexAttribPointer(_pos, 3, gl.GL_FLOAT, False, 0,
                                 ctypes.c_void_p(0))

        # Unbind the VAO first (important)
        gl.glBindVertexArray(0)
        #gl.glDisableVertexAttribArray(_pos)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.pgm_mgr.setup_program(None)

        # --- image drawing shaders ---
        self.pgm_mgr.load_program('image', shader_dir)
        shader = self.pgm_mgr.setup_program('image')

        # --- setup VAO for image drawing ---
        self.vao_img = gl.glGenVertexArrays(1)
        gl.glBindVertexArray(self.vao_img)

        # Generate buffers to hold our vertices
        self.vbo_img = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_img)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, None, gl.GL_DYNAMIC_DRAW)
        # Get the position of the 'position' in parameter of our shader
        # and bind it.
        _pos = gl.glGetAttribLocation(shader, 'position')
        gl.glEnableVertexAttribArray(_pos)
        # Describe the position data layout in the buffer
        gl.glVertexAttribPointer(_pos, 3, gl.GL_FLOAT, False, 5 * 4,
                                 ctypes.c_void_p(0))
        _pos2 = gl.glGetAttribLocation(shader, 'i_tex_coord')
        gl.glEnableVertexAttribArray(_pos2)
        gl.glVertexAttribPointer(_pos2, 2, gl.GL_FLOAT, False, 5 * 4,
                                 ctypes.c_void_p(3 * 4))

        # Unbind the VAO first
        gl.glBindVertexArray(0)
        #gl.glDisableVertexAttribArray(_pos)
        #gl.glDisableVertexAttribArray(_pos2)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.pgm_mgr.setup_program(None)

        self.cmap_buf = gl.glGenBuffers(1)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.cmap_buf)
        gl.glBufferData(gl.GL_TEXTURE_BUFFER, 256 * 4, None, gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, 0)

        rgbmap = self.viewer.get_rgbmap()
        self.gl_set_cmap(rgbmap)

        gl.glDisable(gl.GL_CULL_FACE)
        gl.glFrontFace(gl.GL_CCW)
        self._initialized = True

    def gl_set_image(self, tex_id, img_arr):
        """NOTE: this is a slow operation--downloading a texture."""
        print('gl_set_image')
        context = self.viewer.make_context_current()

        ht, wd = img_arr.shape[:2]

        gl.glActiveTexture(gl.GL_TEXTURE0 + 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER,
                           gl.GL_NEAREST)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_R,
                           gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S,
                           gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T,
                           gl.GL_CLAMP_TO_EDGE)

        if len(img_arr.shape) > 2:
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, wd, ht, 0,
                            gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_arr)
            print('uploaded rgbarr')
        else:
            gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_R32F, wd, ht, 0,
                            gl.GL_RED, gl.GL_FLOAT, img_arr)
            print('uploaded mono')
        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def gl_set_cmap(self, rgbmap):
        # TODO: this does not work with 'histeq' color distribution or
        # when hashsize != 256
        idx = rgbmap.get_hasharray(np.arange(0, 256))
        img_arr = np.ascontiguousarray(rgbmap.arr[rgbmap.sarr[idx]],
                                       dtype=np.uint8)

        # append alpha channel
        wd = img_arr.shape[0]
        alpha = np.full((wd, 1), 255, dtype=np.uint8)
        img_arr = np.concatenate((img_arr, alpha), axis=1)
        rgbmap_id = "{}_rgbmap".format(self.viewer.viewer_id)
        map_id = self.get_texture_id(rgbmap_id)

        # transfer colormap info to GPU buffer
        print('gl_set_cmap', img_arr.shape, img_arr.dtype)
        context = self.viewer.make_context_current()
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.cmap_buf)
        gl.glBufferSubData(gl.GL_TEXTURE_BUFFER, 0, img_arr)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, 0)

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

    def gl_draw_image(self, cvs_img, cp):
        if not self._drawing:
            # this test ensures that we are not trying to draw before
            # the OpenGL context is set for us correctly
            return

        cache = cvs_img.get_cache(self.viewer)
        # TODO: put tex_id in cache?
        tex_id = self.get_texture_id(cvs_img.image_id)
        rgbmap_id = "{}_rgbmap".format(self.viewer.viewer_id)
        map_id = self.get_texture_id(rgbmap_id)
        self.pgm_mgr.setup_program('image')
        gl.glBindVertexArray(self.vao_img)

        _loc = self.pgm_mgr.get_uniform_loc("projection")
        gl.glUniformMatrix4fv(_loc, 1, False, self.camera.proj_mtx)
        _loc = self.pgm_mgr.get_uniform_loc("view")
        gl.glUniformMatrix4fv(_loc, 1, False, self.camera.view_mtx)

        gl.glActiveTexture(gl.GL_TEXTURE0 + 0)
        gl.glBindTexture(gl.GL_TEXTURE_2D, tex_id)
        _loc = self.pgm_mgr.get_uniform_loc("img_texture")
        gl.glUniform1i(_loc, 0)

        gl.glActiveTexture(gl.GL_TEXTURE0 + 1)
        gl.glBindTexture(gl.GL_TEXTURE_BUFFER, map_id)
        gl.glTexBuffer(gl.GL_TEXTURE_BUFFER, gl.GL_RGBA8UI, self.cmap_buf)
        _loc = self.pgm_mgr.get_uniform_loc("color_map")
        gl.glUniform1i(_loc, 1)

        print('cache image type', cache.image_type)
        _loc = self.pgm_mgr.get_uniform_loc("image_type")
        gl.glUniform1i(_loc, cache.image_type)

        # TODO: if image has set levels, use those
        _loc = self.pgm_mgr.get_uniform_loc("loval")
        gl.glUniform1f(_loc, self._levels[0])

        _loc = self.pgm_mgr.get_uniform_loc("hival")
        gl.glUniform1f(_loc, self._levels[1])

        # pad with z=0 coordinate if lacking
        vertices = trcalc.pad_z(cp, dtype=np.float32)

        # Send the data over to the buffer
        # NOTE: we swap elements 0 and 1, because we will also swap
        # vertices 0 and 1, this allows us to draw two triangles to complete
        # the image
        texcoord = np.array([(1.0, 0.0), (0.0, 0.0),
                             (1.0, 1.0), (0.0, 1.0)], dtype=np.float32)
        # swap vertices of rows 0 and 1
        vertices[[0, 1]] = vertices[[1, 0]]
        data = np.concatenate((vertices, texcoord), axis=1)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_img)
        # see https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming
        #gl.glBufferData(gl.GL_ARRAY_BUFFER, None, gl.GL_DYNAMIC_DRAW)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, data, gl.GL_DYNAMIC_DRAW)

        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

        # See NOTE above
        gl.glDrawArrays(gl.GL_TRIANGLES, 0, 3)
        gl.glDrawArrays(gl.GL_TRIANGLES, 1, 4)

        gl.glBindVertexArray(0)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.pgm_mgr.setup_program(None)

    def gl_draw_shape(self, gl_shape, cpoints, brush, pen):

        if not self._drawing:
            # this test ensures that we are not trying to draw before
            # the OpenGL context is set for us correctly
            return

        # pad with z=0 coordinate if lacking
        z_pts = trcalc.pad_z(cpoints, dtype=np.float32)

        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        self.pgm_mgr.setup_program('shape')
        gl.glBindVertexArray(self.vao_line)

        # Update the vertices data in the VBO
        vertices = z_pts.astype(np.float32)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_line)
        # see https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming
        #gl.glBufferData(gl.GL_ARRAY_BUFFER, None, gl.GL_DYNAMIC_DRAW)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, vertices, gl.GL_DYNAMIC_DRAW)

        _loc = self.pgm_mgr.get_uniform_loc("projection")
        gl.glUniformMatrix4fv(_loc, 1, False, self.camera.proj_mtx)
        _loc = self.pgm_mgr.get_uniform_loc("view")
        gl.glUniformMatrix4fv(_loc, 1, False, self.camera.view_mtx)

        # update color uniform
        _loc = self.pgm_mgr.get_uniform_loc("fg_clr")

        # draw fill, if any
        if brush is not None and brush.color is not None:
            _c = brush.color
            gl.glUniform4f(_loc, _c[0], _c[1], _c[2], _c[3])

            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

            # TODO: this will not fill in non-convex polygons correctly
            gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, len(vertices))

        # draw line, if any
        # TODO: support line stippling (dash)
        if pen is not None and pen.linewidth > 0:
            _c = pen.color
            gl.glUniform4f(_loc, _c[0], _c[1], _c[2], _c[3])

            # draw outline
            gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_LINE)
            gl.glLineWidth(pen.linewidth)

            gl.glDrawArrays(gl_shape, 0, len(vertices))

        gl.glBindVertexArray(0)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.pgm_mgr.setup_program(None)

    def gl_resize(self, width, height):
        print('gl_resize')
        self.wd, self.ht = width, height

        context = self.viewer.make_context_current()

        gl.glViewport(0, 0, width, height)

        self.camera.set_viewport_dimensions(width, height)
        self.camera.calc_gl_transform()

        if self.use_offscreen_fbo:
            self.create_offscreen_fbo()

    def gl_paint(self):
        print('gl_paint')
        context = self.viewer.make_context_current()
        self._drawing = True
        try:
            gl.glDepthFunc(gl.GL_LEQUAL)
            gl.glEnable(gl.GL_DEPTH_TEST)

            r, g, b = self.viewer.img_bg
            gl.glClearColor(r, g, b, 1.0)
            gl.glClearDepth(1.0)
            gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)

            cr = RenderContext(self, self.viewer, self.surface)
            self.draw_vector(cr)

        finally:
            self._drawing = False
            gl.glFlush()

    def create_offscreen_fbo(self):
        if self.fbo is not None:
            self.delete_fbo_buffers()
        width, height = self.dims
        self.color_buf = gl.glGenRenderbuffers(1)
        self.depth_buf = gl.glGenRenderbuffers(1)

        # binds created FBO to context both for read and draw
        self.fbo = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)

        # bind color render buffer
        gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.color_buf)
        gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_RGBA8, width, height)
        gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_COLOR_ATTACHMENT0,
                                     gl.GL_RENDERBUFFER, self.color_buf)

        # bind depth render buffer
        ## gl.glBindRenderbuffer(gl.GL_RENDERBUFFER, self.depth_buf)
        ## gl.glRenderbufferStorage(gl.GL_RENDERBUFFER, gl.GL_DEPTH_COMPONENT,
        ##                          width, height)
        ## gl.glFramebufferRenderbuffer(gl.GL_FRAMEBUFFER, gl.GL_DEPTH_ATTACHMENT,
        ##                              gl.GL_RENDERBUFFER, self.depth_buf)

        gl.glDrawBuffers(1, [gl.GL_COLOR_ATTACHMENT0])

        # check FBO status
        status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER);
        if status != gl.GL_FRAMEBUFFER_COMPLETE:
            raise render.RenderError("Error initializing offscreen framebuffer: status={}".format(status))

    def delete_fbo_buffers(self):
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)
        if self.color_buf is not None:
            gl.glDeleteRenderbuffers(1, [self.color_buf])
            self.color_buf = None
        if self.depth_buf is not None:
            gl.glDeleteRenderbuffers(1, [self.depth_buf])
            self.depth_buf = None
        if self.fbo is not None:
            gl.glDeleteFramebuffers(1, [self.fbo])
            self.fbo = None

    def get_surface_as_array(self, order='RGBA'):
        print('get_surface_as_array')
        width, height = self.dims
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        if self.use_offscreen_fbo:
            gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)
        img_buf = gl.glReadPixels(0, 0, width, height, gl.GL_RGBA,
                                  gl.GL_UNSIGNED_BYTE)
        img_np = np.frombuffer(img_buf, dtype=np.uint8).reshape(height,
                                                                width, 4)
        img_np = np.flipud(img_np)

        if order is None or order == 'RGBA':
            return img_np

        img_np = trcalc.reorder_image(order, img_np, 'RGBA')
        return img_np

    def initialize(self):
        self.rl = []

    def finalize(self):
        # for this renderer, this is handled in gl_paint()
        pass

    def setup_cr(self, shape):
        # special cr that just stores up a render list
        cr = vec.RenderContext(self, self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font(font.fontname, font.fontsize, color=font.color,
                    alpha=font.alpha)
        return cr.text_extents(text)

    def get_dimensions(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)
