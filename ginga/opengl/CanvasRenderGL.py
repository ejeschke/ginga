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
import threading
from distutils.version import LooseVersion

from OpenGL import GL as gl

from ginga.vec import CanvasRenderVec as vec
from ginga.canvas import render, transform
from ginga.cairow import CairoHelp
from ginga import trcalc, RGBMap
from ginga.util import rgb_cms

# Local imports
from .Camera import Camera
from . import GlHelp
from .glsl import __file__
shader_dir, _ = os.path.split(__file__)

# NOTE: we update the version later in gl_initialize()
opengl_version = LooseVersion('3.0')


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

    def draw_image(self, cvs_img, cp, cache, whence, order='RGB'):
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


class CanvasRenderer(vec.VectorRenderMixin, render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)
        vec.VectorRenderMixin.__init__(self)

        self.kind = 'opengl'
        self.rgb_order = 'RGBA'
        self.surface = self.viewer.get_widget()
        self.use_offscreen_fbo = True

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
        self._cmap_len = 256
        self.max_texture_dim = 0
        self.image_uploads = []
        self.cmap_uploads = []

        self.pgm_mgr = GlHelp.ShaderManager(self.logger)

        self.fbo = None
        self.fbo_size = (0, 0)
        self.color_buf = None
        self.depth_buf = None
        self.lock = threading.RLock()

    def set_3dmode(self, tf):
        self.mode3d = tf
        self.gl_resize(self.wd, self.ht)
        scales = self.viewer.get_scale_xy()
        self.scale(scales)

    def _overlay_images(self, canvas, whence=0.0):
        #if not canvas.is_compound():
        if not hasattr(canvas, 'objects'):
            return

        for obj in canvas.get_objects():
            if hasattr(obj, 'prepare_image'):
                obj.prepare_image(self.viewer, whence)
            elif obj.is_compound() and (obj != canvas):
                self._overlay_images(obj, whence=whence)

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        if self._initialized:
            self._resize(dims)

            width, height = dims[:2]
            self.gl_resize(width, height)

            self.viewer.update_widget()

            # this is necessary for other widgets to get the same kind of
            # callback as for the standard pixel renderer
            self.viewer.make_callback('redraw', 0.0)

    def scale(self, scales):
        self.camera.scale_2d(scales[:2])

        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 0.0)

    def pan(self, pos):
        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 0.0)

    def rotate_2d(self, ang_deg):
        self.camera.rotate_2d(ang_deg)

        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 2.6)

    def rgbmap_change(self, rgbmap):
        if rgbmap not in self.cmap_uploads:
            self.cmap_uploads.append(rgbmap)
        #self.gl_set_cmap(rgbmap)

        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 2.0)

    def bg_change(self, bg):
        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 3.0)

    def levels_change(self, levels):
        self._levels = levels

        self.viewer.update_widget()
        # this is necessary for other widgets to get the same kind of
        # callback as for the standard pixel renderer
        self.viewer.make_callback('redraw', 1.0)

    def icc_profile_change(self):
        self.viewer.redraw(whence=0.1)

    def interpolation_change(self, interp):
        self.viewer.redraw(whence=0.0)

    def _common_draw(self, cvs_img, cache, whence):
        # internal common drawing phase for all images
        image = cvs_img.image
        if image is None:
            return
        viewer = self.viewer

        if (whence <= 0.0) or (cache.cutout is None) or (not cvs_img.optimize):

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

            if interp in ('basic', 'nearest'):
                cache.interp = 0
            elif interp in ('linear', 'bilinear'):
                cache.interp = 1
            elif interp in ('cubic', 'bicubic'):
                cache.interp = 2
            elif interp == 'lanczos':
                # TODO
                self.logger.warning("'lanczos' interpolation not yet implemented"
                                    " for this renderer--using 'bicubic' instead")
                #cache.interp = 3
                cache.interp = 2
            else:
                cache.interp = 0

            # We are limited by maximum texture size supported for the
            # OpenGl implementation.  Images larger than the maximum
            # in any dimension need to be downsampled to fit.
            ht, wd = data.shape[:2]
            extra = max(wd, ht) - self.max_texture_dim
            if extra > 0:
                new_wd, new_ht = wd - extra, ht - extra
                tup = trcalc.get_scaled_cutout_wdht(data, 0, 0, wd, ht,
                                                    new_wd, new_ht,
                                                    logger=self.logger)
                data = tup[0]

            if cvs_img.flipy:
                data = np.flipud(data)

            # calculate our offset
            pan_off = viewer.data_off
            cvs_x, cvs_y = dst_x - pan_off, dst_y - pan_off

            cache.cutout = data
            cache.cvs_pos = (cvs_x, cvs_y)

    def _prep_rgb_image(self, cvs_img, cache, whence):
        image = cvs_img.get_image()
        image_order = image.get_order()

        if whence <= 0.1 or cache.rgbarr is None:
            rgbarr = cache.cutout

            # convert to output ICC profile, if one is specified
            working_profile = rgb_cms.working_profile
            output_profile = self.viewer.t_.get('icc_output_profile', None)

            if working_profile is not None and output_profile is not None:
                if rgbarr is cache.cutout:
                    rgbarr = np.copy(rgbarr)
                self.convert_via_profile(rgbarr, image_order,
                                         working_profile, output_profile)
            else:
                rgbarr = self.reorder(self.rgb_order, rgbarr, image_order)

            ## depth = rgbarr.shape[2]
            ## if depth < 4:
            ##     # add an alpha channel if missing
            ##     _mn, _mx = trcalc.get_minmax_dtype(rgbarr.dtype)
            ##     rgbarr = trcalc.add_alpha(rgbarr, alpha=_mx)
            ## cache.image_type |= 0x2

            # array needs to be contiguous to transfer properly as buffer
            # to OpenGL
            cache.rgbarr = np.ascontiguousarray(rgbarr, dtype=rgbarr.dtype)

    def _prepare_image(self, cvs_img, cache, whence):
        self._common_draw(cvs_img, cache, whence)

        cache.image_type = 0x0     # no RGB mapping
        self._prep_rgb_image(cvs_img, cache, whence)

        if (whence <= 0.1) or (not cvs_img.optimize):
            # we can upload either 8 bpp or 16 bpp images
            if cache.rgbarr.dtype != np.dtype(np.uint8):
                cache.rgbarr = cache.rgbarr.astype(np.uint16)

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

        cache.image_type = 0x1     # use RGB mapping
        image = cvs_img.get_image()
        image_order = image.get_order()

        if (whence <= 0.1) or (cache.rgbarr is None) or (not cvs_img.optimize):

            img_arr = cache.cutout

            if len(img_arr.shape) == 2:
                # <-- monochrome image with no alpha
                cache.rgbarr = img_arr.astype(np.float32)

            elif img_arr.shape[2] < 3:
                # <-- monochrome image with alpha
                cache.image_type |= 0x2
                cache.rgbarr = img_arr.astype(np.float32)

            else:
                # <-- RGB[A] image
                self._prep_rgb_image(cvs_img, cache, whence)
                cache.image_type |= 0x4
                cache.rgbarr = cache.rgbarr.astype(np.float32)

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
            raise render.RenderError("I don't know how to render canvas type '{}'".format(cvs_img.kind))

        img_arr = cache.rgbarr
        self.image_uploads.append((cvs_img.image_id, img_arr, cache.image_type))

    def convert_via_profile(self, data_np, order, inprof_name, outprof_name):
        """Convert the given RGB data from the working ICC profile
        to the output profile in-place.

        Parameters
        ----------
        data_np : ndarray
            RGB image data to be displayed.

        order : str
            Order of channels in the data (e.g. "BGRA").

        inprof_name, outprof_name : str
            ICC profile names (see :func:`ginga.util.rgb_cms.get_profiles`).

        """
        t_ = self.viewer.get_settings()
        # get rest of necessary conversion parameters
        to_intent = t_.get('icc_output_intent', 'perceptual')
        proofprof_name = t_.get('icc_proof_profile', None)
        proof_intent = t_.get('icc_proof_intent', 'perceptual')
        use_black_pt = t_.get('icc_black_point_compensation', False)

        try:
            rgbobj = RGBMap.RGBPlanes(data_np, order)
            arr_np = rgbobj.get_array('RGB')

            arr = rgb_cms.convert_profile_fromto(arr_np, inprof_name, outprof_name,
                                                 to_intent=to_intent,
                                                 proof_name=proofprof_name,
                                                 proof_intent=proof_intent,
                                                 use_black_pt=use_black_pt,
                                                 logger=self.logger)
            ri, gi, bi = rgbobj.get_order_indexes('RGB')

            out = data_np
            out[..., ri] = arr[..., 0]
            out[..., gi] = arr[..., 1]
            out[..., bi] = arr[..., 2]

            self.logger.debug("Converted from '%s' to '%s' profile" % (
                inprof_name, outprof_name))

        except Exception as e:
            self.logger.warning("Error converting output from working profile: %s" % (str(e)))
            # TODO: maybe should have a traceback here
            self.logger.info("Output left unprofiled")

    def get_texture_id(self, image_id):
        tex_id = self._tex_cache.get(image_id, None)
        if tex_id is None:
            context = self.viewer.make_context_current()
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
        context = self.viewer.make_context_current()

        d = self.getOpenGLInfo()
        self.logger.info("OpenGL info--Vendor: '%(vendor)s'  "
                         "Renderer: '%(renderer)s'  "
                         "Version: '%(opengl_version)s'  "
                         "Shader: '%(shader_version)s' "
                         "Max texture: '%(max_tex)s'" % d)

        opengl_version = LooseVersion(d['opengl_version'].split(' ')[0])

        if self.use_offscreen_fbo:
            self.create_offscreen_fbo()

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
        gl.glBufferData(gl.GL_TEXTURE_BUFFER, self._cmap_len * 4, None,
                        gl.GL_DYNAMIC_DRAW)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, 0)

        rgbmap = self.viewer.get_rgbmap()
        if rgbmap not in self.cmap_uploads:
            self.cmap_uploads.append(rgbmap)

        gl.glDisable(gl.GL_CULL_FACE)
        gl.glFrontFace(gl.GL_CCW)
        self._initialized = True

    def gl_set_image(self, tex_id, img_arr, image_type):
        """NOTE: this is a slow operation--downloading a texture."""
        #context = self.viewer.make_context_current()

        ht, wd = img_arr.shape[:2]

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

        # see image_type in image fragment shader
        if image_type & 0x1 == 0:
            # "native" image colors--3 color image, no RGBMAP
            if img_arr.dtype == np.dtype(np.uint8):
                if img_arr.shape[2] == 3:
                    # 8bpp RGB
                    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
                    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, wd, ht, 0,
                                    gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_arr)
                    self.logger.debug("uploaded 8 bpp RGB as texture {}".format(tex_id))
                elif img_arr.shape[2] == 4:
                    # 8bpp RGBA
                    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 1)
                    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA, wd, ht, 0,
                                    gl.GL_RGBA, gl.GL_UNSIGNED_BYTE, img_arr)
                    self.logger.debug("uploaded 8 bpp RGBA as texture {}".format(tex_id))
            elif img_arr.dtype == np.dtype(np.uint16):
                if img_arr.shape[2] == 3:
                    # 16bpp RGB
                    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 2)
                    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB16, wd, ht, 0,
                                    gl.GL_RGB, gl.GL_UNSIGNED_SHORT, img_arr)
                    self.logger.debug("uploaded 16 bpp RGB as texture {}".format(tex_id))
                elif img_arr.shape[2] == 4:
                    # 16bpp RGBA
                    gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 2)
                    gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA16, wd, ht, 0,
                                    gl.GL_RGBA, gl.GL_UNSIGNED_SHORT, img_arr)
                    self.logger.debug("uploaded 16 bpp RGBA as texture {}".format(tex_id))
            else:
                raise ValueError("unknown image type: {}".format(hex(image_type)))

            self.logger.debug("uploaded rgbarr as texture {}".format(tex_id))

        else:
            if len(img_arr.shape) < 3 or img_arr.shape[2] == 1:
                # mono, no alpha
                gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_R32F, wd, ht, 0,
                                gl.GL_RED, gl.GL_FLOAT, img_arr)
                self.logger.debug("uploaded mono as texture {}".format(tex_id))
            elif len(img_arr.shape) == 3 and img_arr.shape[2] == 2:
                # mono, with alpha
                gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RG32F, wd, ht, 0,
                                gl.GL_RG, gl.GL_FLOAT, img_arr)
                self.logger.debug("uploaded mono w/alpha as texture {}".format(tex_id))
            elif len(img_arr.shape) == 3 and img_arr.shape[2] == 3:
                # RGB, no alpha
                gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB32F, wd, ht, 0,
                                gl.GL_RGB, gl.GL_FLOAT, img_arr)
                self.logger.debug("uploaded RGB as texture {}".format(tex_id))
            elif len(img_arr.shape) == 3 and img_arr.shape[2] == 4:
                # RGBA
                gl.glPixelStorei(gl.GL_UNPACK_ALIGNMENT, 4)
                gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGBA32F, wd, ht, 0,
                                gl.GL_RGBA, gl.GL_FLOAT, img_arr)
                self.logger.debug("uploaded RGBA as texture {}".format(tex_id))

            else:
                raise ValueError("unknown image type: {}".format(hex(image_type)))

        gl.glBindTexture(gl.GL_TEXTURE_2D, 0)

    def gl_set_cmap(self, rgbmap):
        # TODO: this does not yet work with 'histeq' color distribution
        # Downsample color distribution hash to our opengl colormap length
        hashsize = rgbmap.get_hash_size()
        idx = rgbmap.get_hasharray(np.arange(0, hashsize))
        xi = (np.arange(0, self._cmap_len) * (hashsize / self._cmap_len)).clip(0, hashsize).astype(np.uint)
        if len(xi) != self._cmap_len:
            raise render.RenderError("Error generating color hash table index: size mismatch {} != {}".format(len(xi), self._cmap_len))

        idx = idx[xi]
        img_arr = np.ascontiguousarray(rgbmap.arr[rgbmap.sarr[idx]],
                                       dtype=np.uint8)

        # append alpha channel
        wd = img_arr.shape[0]
        alpha = np.full((wd, 1), self._cmap_len - 1, dtype=np.uint8)
        img_arr = np.concatenate((img_arr, alpha), axis=1)
        map_id = self.get_texture_id(rgbmap.mapper_id)

        # transfer colormap info to GPU buffer
        #context = self.viewer.make_context_current()
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, self.cmap_buf)
        gl.glBufferSubData(gl.GL_TEXTURE_BUFFER, 0, img_arr)
        gl.glBindBuffer(gl.GL_TEXTURE_BUFFER, 0)
        self.logger.debug("uploaded cmap as texture buffer {}".format(map_id))

    def gl_draw_image(self, cvs_img, cp):
        if not self._drawing:
            # this test ensures that we are not trying to draw before
            # the OpenGL context is set for us correctly
            return

        cache = cvs_img.get_cache(self.viewer)
        # TODO: put tex_id in cache?
        tex_id = self.get_texture_id(cvs_img.image_id)
        rgbmap = self.viewer.get_rgbmap()
        map_id = self.get_texture_id(rgbmap.mapper_id)
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

        _loc = self.pgm_mgr.get_uniform_loc("image_type")
        gl.glUniform1i(_loc, cache.image_type)

        _loc = self.pgm_mgr.get_uniform_loc("interp")
        gl.glUniform1i(_loc, cache.interp)

        # if image has fixed cut levels, use those
        cuts = getattr(cvs_img, 'cuts', None)
        if cuts is not None:
            loval, hival = cuts
        else:
            loval, hival = self._levels

        _loc = self.pgm_mgr.get_uniform_loc("loval")
        gl.glUniform1f(_loc, loval)

        _loc = self.pgm_mgr.get_uniform_loc("hival")
        gl.glUniform1f(_loc, hival)

        # pad with z=0 coordinate if lacking
        vertices = trcalc.pad_z(cp, dtype=np.float32)

        # Send the data over to the buffer
        texcoord = np.array([(0.0, 0.0), (1.0, 0.0),
                             (1.0, 1.0), (0.0, 1.0)], dtype=np.float32)
        data = np.concatenate((vertices, texcoord), axis=1)

        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, self.vbo_img)
        # see https://www.khronos.org/opengl/wiki/Buffer_Object_Streaming
        #gl.glBufferData(gl.GL_ARRAY_BUFFER, None, gl.GL_DYNAMIC_DRAW)
        gl.glBufferData(gl.GL_ARRAY_BUFFER, data, gl.GL_DYNAMIC_DRAW)

        gl.glPolygonMode(gl.GL_FRONT_AND_BACK, gl.GL_FILL)

        gl.glDrawArrays(gl.GL_TRIANGLE_FAN, 0, 4)

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
            # > 1.0 not guaranteed to be supported as of OpenGL 4.2
            # TODO
            # gl.glLineWidth(pen.linewidth)
            gl.glLineWidth(1.0)

            gl.glDrawArrays(gl_shape, 0, len(vertices))

        gl.glBindVertexArray(0)
        gl.glBindBuffer(gl.GL_ARRAY_BUFFER, 0)
        self.pgm_mgr.setup_program(None)

    def show_errors(self):
        while True:
            err = gl.glGetError()
            if err == gl.GL_NO_ERROR:
                return
            self.logger.error("gl error: {}".format(err))

    def gl_resize(self, width, height):
        self.wd, self.ht = width, height

        context = self.viewer.make_context_current()

        gl.glViewport(0, 0, width, height)

        self.camera.set_viewport_dimensions(width, height)
        self.camera.calc_gl_transform()

    def gl_paint(self):
        with self.lock:
            context = self.viewer.make_context_current()

            # perform any necessary image updates
            uploads, self.image_uploads = self.image_uploads, []
            for image_id, img_arr, image_type in uploads:
                tex_id = self.get_texture_id(image_id)
                self.gl_set_image(tex_id, img_arr, image_type)

            # perform any necessary rgbmap updates
            rgbmap = self.viewer.get_rgbmap()
            if rgbmap not in self.cmap_uploads:
                self.cmap_uploads.append(rgbmap)
            uploads, self.cmap_uploads = self.cmap_uploads, []
            for rgbmap in uploads:
                self.gl_set_cmap(rgbmap)

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
                self.show_errors()

    def create_offscreen_fbo(self):
        if self.fbo is not None:
            self.delete_fbo_buffers()
        width, height = self.dims
        self.fbo_size = self.dims
        self.color_buf = gl.glGenRenderbuffers(1)
        self.depth_buf = gl.glGenRenderbuffers(1)

        # binds created FBO to context both for read and draw
        self.fbo = gl.glGenFramebuffers(1)
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glViewport(0, 0, width, height)

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

        self.drawbuffers = [gl.GL_COLOR_ATTACHMENT0]
        gl.glDrawBuffers(1, self.drawbuffers)

        # check FBO status
        # TODO: returning a non-zero status, even though it seems to be working
        # fine.
        ## status = gl.glCheckFramebufferStatus(gl.GL_FRAMEBUFFER)
        ## if status != gl.GL_FRAMEBUFFER_COMPLETE:
        ##     raise render.RenderError("Error initializing offscreen framebuffer: status={}".format(status))
        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, 0)

    def delete_fbo_buffers(self):
        if self.color_buf is not None:
            gl.glDeleteRenderbuffers(1, [self.color_buf])
            self.color_buf = None
        if self.depth_buf is not None:
            gl.glDeleteRenderbuffers(1, [self.depth_buf])
            self.depth_buf = None
        if self.fbo is not None:
            gl.glDeleteFramebuffers(1, [self.fbo])
            self.fbo = None
        self.fbo_size = (0, 0)

    def get_surface_as_array(self, order='RGBA'):
        if self.dims != self.fbo_size:
            self.create_offscreen_fbo()
        width, height = self.dims

        context = self.viewer.make_context_current()

        # some widget sets use a non-default FBO for rendering, so save
        # and restore
        cur_fbo = gl.glGetIntegerv(gl.GL_FRAMEBUFFER_BINDING)

        gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, self.fbo)
        gl.glViewport(0, 0, width, height)
        ## if self.use_offscreen_fbo:
        ##     gl.glReadBuffer(gl.GL_COLOR_ATTACHMENT0)

        try:
            self.gl_paint()
            img_buf = gl.glReadPixels(0, 0, width, height, gl.GL_RGBA,
                                      gl.GL_UNSIGNED_BYTE)
        finally:
            gl.glBindFramebuffer(gl.GL_FRAMEBUFFER, cur_fbo)

        # seems to be necessary to redraw the main window
        self.viewer.update_widget()

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

    def calc_const_len(self, clen):
        # zoom is accomplished by viewing distance in OpenGL, so we
        # have to adjust clen by scale to get a constant size
        scale = self.viewer.get_scale_max()
        return clen / scale

    def scale_fontsize(self, fontsize):
        return fontsize

    def get_dimensions(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)
