#
# CanvasRenderVk.py -- Vulkan renderer for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""GPU-native Vulkan renderer for Ginga.

:class:`CanvasRendererGPU` mirrors the OpenGL renderer: it records the canvas
draw operations and replays them onto the GPU each frame (via a
:class:`VulkanReplayEngine` that drives the shape/image/glyph pipelines into a
shared render pass), rendering into an offscreen Vulkan image.
:meth:`~CanvasRendererGPU.get_surface_as_array` reads the result back as an
RGBA array, so any Ginga backend can consume it via the same CPU-array path
used by the PIL/agg renderers.  Images are colormapped in-shader (live cut
levels/distribution), and shapes, wide/dashed lines and text are all drawn on
the GPU.  A 3D camera mode (``mode3d``) reuses :class:`ginga.opengl.Camera`.
"""
from collections import namedtuple

import numpy as np

from ginga.vec import CanvasRenderVec as vec
from ginga.canvas import render, transform, stroke
from ginga.opengl.Camera import Camera
from ginga import trcalc
from .vkcore import have_vulkan, VulkanContext, OffscreenColorTarget, _s, \
    VulkanError
from . import pipelines
from .pipelines import ShapePipeline, GlyphPipeline, MultiImagePipeline

if have_vulkan:
    import vulkan as vk


# One image collected during vector replay, to be drawn this frame.  Using a
# named tuple (rather than a bare tuple) keeps the collect/draw sites readable
# and lets fields be added without renumbering every unpack.
_ImageDraw = namedtuple('_ImageDraw',
                        ['image_id', 'data', 'image_type', 'quad_pos',
                         'quad_uv', 'loval', 'hival', 'obj_alpha'])


def ortho_2d_push(width, height):
    """Return the 128-byte vertex push constant (view=identity, projection=
    orthographic) that maps window pixel coords ``[0,width]x[0,height]`` to
    Vulkan clip space ``[-1,1]x[-1,1]`` (both y-down).

    The projection is uploaded transposed because GLSL reads a ``mat4`` in
    column-major order.
    """
    view = np.eye(4, dtype=np.float32)
    proj = np.array([[2.0 / width, 0.0, 0.0, -1.0],
                     [0.0, 2.0 / height, 0.0, -1.0],
                     [0.0, 0.0, 1.0, 0.0],
                     [0.0, 0.0, 0.0, 1.0]], dtype=np.float32)
    return view.tobytes() + np.ascontiguousarray(proj.T, np.float32).tobytes()


# Vulkan clip-space correction applied to a GL projection matrix: flip Y
# (Vulkan clip is y-down) and remap depth from GL's [-1, 1] to Vulkan's
# [0, 1].  Camera matrices are stored column-major (``Matrix4x4.get()`` returns
# M^T), so we post-multiply by C^T to get the column-major bytes of C @ P.
_VK_CLIP_T = np.array([[1.0, 0.0, 0.0, 0.0],
                       [0.0, -1.0, 0.0, 0.0],
                       [0.0, 0.0, 0.5, 0.0],
                       [0.0, 0.0, 0.5, 1.0]], dtype=np.float32)


def camera_push(camera):
    """Return the 128-byte push constant (view + Vulkan-corrected projection)
    for a :class:`~ginga.opengl.Camera.Camera`.  The camera matrices are
    already column-major; the projection gets the Vulkan clip correction."""
    view = np.ascontiguousarray(camera.view_mtx, dtype=np.float32)
    proj = np.ascontiguousarray(np.dot(camera.proj_mtx, _VK_CLIP_T),
                                dtype=np.float32)
    return view.tobytes() + proj.tobytes()


def gl_transforms(v):
    """The OpenGL-style transform set (cartesian-data coordinates driven by a
    camera).  Copied from ``ginga.opengl.GlHelp.get_transforms`` to avoid
    importing that module (which pulls in PyOpenGL)."""
    return {
        'window_to_native': (transform.CartesianWindowTransform(v).invert() +
                             transform.RotationTransform(v).invert() +
                             transform.ScaleTransform(v).invert()),
        'cartesian_to_window': (transform.FlipSwapTransform(v) +
                                transform.CartesianWindowTransform(v)),
        'cartesian_to_native': (transform.FlipSwapTransform(v) +
                                transform.RotationTransform(v) +
                                transform.CartesianNativeTransform(v)),
        'data_to_cartesian': (transform.DataCartesianTransform(v) +
                              transform.ScaleTransform(v)),
        'data_to_scrollbar': (transform.DataCartesianTransform(v) +
                              transform.FlipSwapTransform(v) +
                              transform.RotationTransform(v)),
        'mouse_to_data': transform.InvertedTransform(
            transform.DataCartesianTransform(v) +
            transform.ScaleTransform(v) +
            transform.FlipSwapTransform(v) +
            transform.RotationTransform(v) +
            transform.CartesianWindowTransform(v)),
        'data_to_window': (transform.DataCartesianTransform(v) +
                           transform.ScaleTransform(v) +
                           transform.FlipSwapTransform(v) +
                           transform.RotationTransform(v) +
                           transform.CartesianWindowTransform(v)),
        'data_to_percentage': (transform.DataCartesianTransform(v) +
                               transform.ScaleTransform(v) +
                               transform.FlipSwapTransform(v) +
                               transform.RotationTransform(v) +
                               transform.CartesianWindowTransform(v) +
                               transform.WindowPercentageTransform(v)),
        'data_to_native': (transform.DataCartesianTransform(v) +
                           transform.FlipSwapTransform(v)),
        'wcs_to_data': transform.WCSDataTransform(v),
        'wcs_to_native': (transform.WCSDataTransform(v) +
                          transform.DataCartesianTransform(v) +
                          transform.FlipSwapTransform(v)),
    }


# ======================================================================
# GPU-native drawing (vector replay)
#
# Mirrors the OpenGL renderer (``ginga/opengl/CanvasRenderGL.py``): the
# standard CPU pipeline stages are *not* run; instead ``render_whence``
# prepares each image as a raw cutout, and drawing is recorded into a render
# list (via ``vec.RenderContext``) and replayed onto the GPU in
# ``get_surface_as_array``.  Images are colormapped on the GPU by the
# ``MultiImagePipeline`` (cut levels in-shader + a colormap texel buffer built
# from the viewer's ``rgbmap``, as in GL's ``gl_set_cmap``); shapes are drawn
# by the ``ShapePipeline`` and text by the ``GlyphPipeline``.
# ======================================================================


class VulkanReplayEngine:
    """Owns the offscreen target + shared render pass and the shape/image
    pipelines, and composites a frame recorded op-by-op.

    Usage: :meth:`set_colormap`, then :meth:`begin`, :meth:`record_image`
    and/or :meth:`record_shapes`, then :meth:`end`, then
    :meth:`get_surface_as_array`.
    """

    def __init__(self, ctx, width, height):
        if not have_vulkan:
            raise VulkanError("the 'vulkan' Python package is not installed")
        self.ctx = ctx
        self.width = width
        self.height = height
        self.target = OffscreenColorTarget(ctx, width, height)
        self.shape = ShapePipeline(ctx, self.target)
        self.image = MultiImagePipeline(ctx, self.target)
        self.glyph = GlyphPipeline(ctx, self.target)
        self._make_render_pass()
        self._cmd = None
        self._push = None

    def _make_render_pass(self):
        ctx, target = self.ctx, self.target
        att = vk.VkAttachmentDescription(
            format=target.fmt, samples=vk.VK_SAMPLE_COUNT_1_BIT,
            loadOp=vk.VK_ATTACHMENT_LOAD_OP_CLEAR,
            storeOp=vk.VK_ATTACHMENT_STORE_OP_STORE,
            stencilLoadOp=vk.VK_ATTACHMENT_LOAD_OP_DONT_CARE,
            stencilStoreOp=vk.VK_ATTACHMENT_STORE_OP_DONT_CARE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED,
            finalLayout=vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL)
        subpass = vk.VkSubpassDescription(
            pipelineBindPoint=vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
            colorAttachmentCount=1, pColorAttachments=[vk.VkAttachmentReference(
                attachment=0,
                layout=vk.VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL)])
        dep = vk.VkSubpassDependency(
            srcSubpass=0, dstSubpass=vk.VK_SUBPASS_EXTERNAL,
            srcStageMask=vk.VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
            dstStageMask=vk.VK_PIPELINE_STAGE_TRANSFER_BIT,
            srcAccessMask=vk.VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
            dstAccessMask=vk.VK_ACCESS_TRANSFER_READ_BIT)
        self.render_pass = vk.vkCreateRenderPass(
            ctx.device, vk.VkRenderPassCreateInfo(
                sType=_s('RENDER_PASS_CREATE_INFO'), attachmentCount=1,
                pAttachments=[att], subpassCount=1, pSubpasses=[subpass],
                dependencyCount=1, pDependencies=[dep]), None)
        self.framebuffer = vk.vkCreateFramebuffer(
            ctx.device, vk.VkFramebufferCreateInfo(
                sType=_s('FRAMEBUFFER_CREATE_INFO'), renderPass=self.render_pass,
                attachmentCount=1, pAttachments=[target.view],
                width=self.width, height=self.height, layers=1), None)

    def set_colormap(self, rgba_u8):
        self.image.set_colormap(rgba_u8)

    def begin(self, bg_color=(0.0, 0.0, 0.0, 1.0), push=None):
        self._push = (push if push is not None
                      else ortho_2d_push(self.width, self.height))
        cmd = self.ctx.begin_commands()
        vk.vkCmdBeginRenderPass(cmd, vk.VkRenderPassBeginInfo(
            sType=_s('RENDER_PASS_BEGIN_INFO'), renderPass=self.render_pass,
            framebuffer=self.framebuffer, renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(0, 0),
                extent=vk.VkExtent2D(self.width, self.height)),
            clearValueCount=1, pClearValues=[vk.VkClearValue(
                color=vk.VkClearColorValue(float32=list(bg_color)))]),
            vk.VK_SUBPASS_CONTENTS_INLINE)
        self._cmd = cmd

    def upload_image(self, image_id, data, image_type):
        """Upload/refresh the texture for ``image_id`` (slow; only when the
        image data changes -- zoom/pan reuse the cached texture)."""
        self.image.upload_image(image_id, data, image_type)

    def has_image(self, image_id):
        return self.image.has_image(image_id)

    def record_image(self, image_id, quad_pos, quad_uv, loval, hival,
                     image_type, obj_alpha):
        """Record an image draw using the cached texture for ``image_id``."""
        self.image.record(self._cmd, image_id, quad_pos, quad_uv, loval, hival,
                          image_type, obj_alpha, self._push)

    def record_shapes(self, shapes):
        if len(shapes) > 0:
            self.shape.record(self._cmd, shapes, self._push)

    def record_texts(self, texts):
        # texts: list of (rgba_tile, quad_pos, quad_uv)
        for rgba, quad_pos, quad_uv in texts:
            self.glyph.record(self._cmd, rgba, quad_pos, quad_uv, self._push)

    def end(self):
        vk.vkCmdEndRenderPass(self._cmd)
        self.ctx.submit_wait(self._cmd)
        self.target.layout = vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL
        self.image.free_scratch()
        self.shape.free_scratch()
        self.glyph.free_scratch()
        self._cmd = None

    def get_surface_as_array(self, order='RGBA'):
        arr = self.target.read_rgba()
        order = order.upper()
        if order == 'RGBA':
            return arr
        idx = ['RGBA'.index(c) for c in order]
        return np.ascontiguousarray(arr[..., idx])

    def destroy(self):
        d = self.ctx.device
        vk.vkDestroyFramebuffer(d, self.framebuffer, None)
        vk.vkDestroyRenderPass(d, self.render_pass, None)
        self.glyph.destroy()
        self.image.destroy()
        self.shape.destroy()
        self.target.destroy()


def _norm_alpha(a_channel, dtype):
    """Normalize an alpha channel to ``0..1`` floats based on its source dtype
    (integer types by their max; float assumed already in ``0..1``)."""
    al = np.asarray(a_channel, dtype=np.float32)
    if np.issubdtype(dtype, np.integer):
        al = al / float(np.iinfo(dtype).max)
    return np.clip(al, 0.0, 1.0)


class RenderContext(render.RenderContextBase):
    """Live drawing context used during vector replay: its draw ops feed the
    renderer's GPU pipelines (they do not record -- recording is done by
    ``vec.RenderContext`` in :meth:`CanvasRendererGPU.setup_cr`)."""

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        return self.renderer.text_extents(text, font)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, cache, whence, order='RGB'):
        self.renderer.vk_add_image(cvs_img, cpoints, cache)

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, fill=None,
                  line=None):
        self.renderer.vk_add_text(cx, cy, text, rot_deg, font, fill, line)

    def draw_polygon(self, cpoints, line=None, fill=None):
        self.renderer.vk_add_shape('polygon', cpoints, line, fill)

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        # approximate a circle with a polygon (as the GL renderer does)
        theta = np.linspace(0.0, 2.0 * np.pi, 360, endpoint=False)
        cpoints = np.stack([cx + cradius * np.cos(theta),
                            cy + cradius * np.sin(theta)], axis=1)
        self.renderer.vk_add_shape('polygon', cpoints, line, fill)

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        self.renderer.vk_add_shape('line', [(cx1, cy1), (cx2, cy2)], line, None)

    def draw_path(self, cpoints, line=None):
        self.renderer.vk_add_shape('path', cpoints, line, None)


class CanvasRendererGPU(vec.VectorRenderMixin, render.StandardPipelineRenderer):
    """Ginga Vulkan renderer -- GPU-native drawing.

    Subclasses :class:`~ginga.canvas.render.StandardPipelineRenderer` for its
    coordinate/transform bookkeeping (as the OpenGL renderer does) but does
    *not* run the CPU pipeline stages.  Drawing is recorded into a render list
    and replayed onto the GPU: images are colormapped in the fragment shader
    (:class:`~ginga.vulkan.pipelines.MultiImagePipeline`), shapes and
    wide/dashed lines by the :class:`~ginga.vulkan.pipelines.ShapePipeline`,
    and text by the :class:`~ginga.vulkan.pipelines.GlyphPipeline`.  A 3D
    camera mode is available via the ``mode3d`` attribute.
    """

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)
        vec.VectorRenderMixin.__init__(self)

        self.kind = 'vulkan'
        self.rgb_order = 'RGBA'
        # We composite to an offscreen Vulkan target rather than a CPU/toolkit
        # surface.  A non-None sentinel keeps array-consuming backends happy
        # (e.g. render.py's get_surface_as_rgb_format_buffer, and pg, guard on
        # ``surface is None``) while remaining un-recognized by the toolkit
        # fast paths (Qt QPixmap/QImage, Gtk cairo.ImageSurface isinstance
        # checks), so every backend falls through to get_surface_as_array().
        self.surface = True
        # cap on image texture size; Vulkan guarantees at least 4096, most
        # devices (incl. Lavapipe) support much more.  TODO: read the device
        # limit (maxImageDimension2D) instead.
        self.max_texture_dim = 8192

        self.ctx = VulkanContext(app_name='ginga')
        self.logger.info("Vulkan renderer (GPU) using device: %s" %
                         self.ctx.device_name())
        self._engine = None
        # per-frame replay collections
        self._images = []
        self._shapes = []
        self._texts = []
        # GPU upload gating (like GL: upload only on change, not on zoom/pan)
        self._img_dirty = set()       # image_ids needing (re)upload
        self._cmap_dirty = True

        # 3D camera (as in the OpenGL renderer).  Off by default: 2D image
        # viewing uses the window-pixel ortho path.  When enabled (mode3d),
        # the viewer switches to cartesian-data coordinates and the camera's
        # view/projection matrices drive the scene.
        self.camera = Camera()
        self.camera.set_scene_radius(2)
        self.camera.set_camera_home_position((0, 0, 1000))
        self.camera.reset()
        self._mode3d = False
        self._std_tform = None        # saved 2D transforms while in mode3d

    def get_camera(self):
        return self.camera

    @property
    def mode3d(self):
        return self._mode3d

    @mode3d.setter
    def mode3d(self, tf):
        tf = bool(tf)
        if tf == self._mode3d:
            return
        self._mode3d = tf
        if tf:
            # switch the viewer to camera (cartesian-data) coordinates
            self._std_tform = self.viewer.tform
            self.viewer.tform = gl_transforms(self.viewer)
            wd, ht = self.dims[:2]
            self.camera.set_viewport_dimensions(wd, ht)
            self.camera.scale_2d(self.viewer.get_scale_xy()[:2])
            self.camera.calc_gl_transform()
        elif self._std_tform is not None:
            self.viewer.tform = self._std_tform
        self.viewer.redraw(whence=0)

    # ---- engine lifecycle ------------------------------------------------

    def _ensure_engine(self, width, height):
        if (self._engine is not None and
                (self._engine.width, self._engine.height) == (width, height)):
            return
        if self._engine is not None:
            self._engine.destroy()
            self._engine = None
        if width > 0 and height > 0:
            self._engine = VulkanReplayEngine(self.ctx, width, height)
            # a fresh engine has no colormap uploaded yet; image textures are
            # re-uploaded lazily via the per-id engine.has_image() check
            self._cmap_dirty = True

    def resize(self, dims):
        self._resize(dims)
        if self._mode3d:
            self.camera.set_viewport_dimensions(*dims[:2])
            self.camera.calc_gl_transform()
        self.viewer.redraw(whence=0)

    # ---- transform / appearance changes ----------------------------------
    # These only need the render list rebuilt (fresh cpoints / cut levels /
    # colormap); they must NOT re-cut or re-upload the image, so they redraw
    # at a whence > 2.0 to skip the image-prepare (overlays) step -- the GPU
    # handles zoom/pan by stretching the cached texture over the new quad,
    # exactly as OpenGL does via the camera frustum.  In mode3d the camera's
    # view/projection matrices are updated instead.

    def scale(self, scales):
        if self._mode3d:
            self.camera.scale_2d(scales[:2])
        self.viewer.redraw(whence=2.6)

    def pan(self, pos):
        # in mode3d, panning is applied to the camera by modes/camera.py
        self.viewer.redraw(whence=2.6)

    def rotate_2d(self, ang_deg):
        if self._mode3d:
            self.camera.rotate_2d(ang_deg)
        self.viewer.redraw(whence=2.6)

    def transform_2d(self, state):
        self.viewer.redraw(whence=2.6)

    def levels_change(self, levels):
        # cut levels are read live in vk_add_image; just rebuild the list
        self.viewer.redraw(whence=2.5)

    def rgbmap_change(self, rgbmap):
        self._cmap_dirty = True
        self.viewer.redraw(whence=2.5)

    def bg_change(self, bg):
        self.viewer.redraw(whence=2.5)

    def fg_change(self, fg):
        self.viewer.redraw(whence=2.5)

    # ---- vector render mixin hooks ---------------------------------------

    def initialize(self):
        self.rl = []

    def finalize(self):
        # actual GPU paint happens in get_surface_as_array (as in GL)
        pass

    def setup_cr(self, shape):
        # recording context: stores drawing ops into self.rl
        cr = vec.RenderContext(self, self.viewer, None)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def render_whence(self, whence):
        # prepare (but do not draw) images; no standard pipeline stages
        if whence <= 2.0:
            p_canvas = self.viewer.get_private_canvas()
            self._overlay_images(p_canvas, whence=whence)

    def _overlay_images(self, canvas, whence=0.0):
        if not hasattr(canvas, 'objects'):
            return
        for obj in canvas.get_objects():
            if hasattr(obj, 'prepare_image'):
                obj.prepare_image(self.viewer, whence)
            elif obj.is_compound() and (obj != canvas):
                self._overlay_images(obj, whence=whence)

    # ---- image preparation (raw cutout for GPU colormapping) -------------

    def _common_draw(self, cvs_img, cache, whence):
        image = cvs_img.image
        if image is None:
            return
        viewer = self.viewer
        if (whence <= 0.0) or (cache.cutout is None) or (not cvs_img.optimize):
            dst_x, dst_y = cvs_img.crdmap.to_data((cvs_img.x, cvs_img.y))
            a1, b1, a2, b2 = 0, 0, image.width - 1, image.height - 1
            _scale_x, _scale_y = cvs_img.scale_x, cvs_img.scale_y

            interp = cvs_img.interpolation
            if interp is None:
                interp = viewer.get_settings().get('interpolation', 'basic')
            if interp not in trcalc.interpolation_methods:
                interp = 'basic'
            res = image.get_scaled_cutout2((a1, b1), (a2, b2),
                                           (_scale_x, _scale_y), method=interp)
            data = res.data

            ht, wd = data.shape[:2]
            extra = max(wd, ht) - self.max_texture_dim
            if extra > 0:
                new_wd, new_ht = wd - extra, ht - extra
                data = trcalc.get_scaled_cutout_wdht(data, 0, 0, wd, ht,
                                                     new_wd, new_ht,
                                                     logger=self.logger)[0]
            if cvs_img.flipy:
                data = np.flipud(data)

            pan_off = viewer.data_off
            cache.cutout = data
            cache.cvs_pos = (dst_x - pan_off, dst_y - pan_off)

    def prepare_image(self, cvs_img, cache, whence):
        self._common_draw(cvs_img, cache, whence)
        if cache.cutout is None:
            cache.vk_data = None
            return
        arr = cache.cutout
        if arr.ndim == 2:
            # monochrome normimage -> raw float texture, colormapped in-shader
            cache.vk_data = np.ascontiguousarray(arr, dtype=np.float32)
            cache.vk_type = 0
        elif cvs_img.kind == 'image':
            # kind 'image' -> native RGB[A], no interactive RGB map
            cache.vk_data = self._rgb_tile(cvs_img, arr)
            cache.vk_type = 1
        else:
            # RGB normimage -> raw float RGBA; per-channel cut levels + colormap
            # applied in-shader, so cut levels/distribution/rgbmap stay live
            cache.vk_data = self._rgb_float(cvs_img, arr)
            cache.vk_type = 2
        # image data was (re)prepared -> re-upload its texture
        self._img_dirty.add(cvs_img.image_id)
        cache.drawn = True

    def _rgb_float(self, cvs_img, arr):
        """Produce an ``(H, W, 4)`` float32 array of *raw* RGBA values from an
        RGB[A] cutout (honoring channel order), for the RGB-normimage path
        where cut levels + colormap are applied per channel in the shader."""
        image = cvs_img.get_image()
        order = (image.get_order() if image is not None else 'RGB').upper()
        a = np.asarray(arr, dtype=np.float32)
        nch = a.shape[2]
        idx = {c: i for i, c in enumerate(order) if i < nch}
        h, w = a.shape[:2]
        out = np.zeros((h, w, 4), dtype=np.float32)
        out[..., 0] = a[..., idx.get('R', 0)]
        out[..., 1] = a[..., idx.get('G', min(1, nch - 1))]
        out[..., 2] = a[..., idx.get('B', min(2, nch - 1))]
        # per-pixel alpha, normalized to 0..1 by the source dtype range
        if 'A' in idx:
            out[..., 3] = _norm_alpha(a[..., idx['A']], np.asarray(arr).dtype)
        else:
            out[..., 3] = 1.0
        return np.ascontiguousarray(out)

    def _rgb_tile(self, cvs_img, arr):
        """Produce an ``(H, W, 4)`` uint8 RGBA tile from an RGB[A] cutout,
        honoring the image's channel order.  Non-8-bit data is scaled through
        the cut levels (per channel)."""
        image = cvs_img.get_image()
        order = (image.get_order() if image is not None else 'RGB').upper()
        a = arr
        nch = a.shape[2]
        idx = {c: i for i, c in enumerate(order) if i < nch}
        if a.dtype == np.uint8:
            rgb8 = a
        else:
            # scale the colour channels to 8-bit through the cut levels
            loval, hival = self.viewer.get_cut_levels()
            cuts = getattr(cvs_img, 'cuts', None)
            if cuts is not None:
                loval, hival = cuts
            f = a.astype(np.float32)
            if hival > loval:
                f = (f - loval) / (hival - loval)
            rgb8 = np.clip(f * 255.0, 0, 255).astype(np.uint8)
        h, w = a.shape[:2]
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., 0] = rgb8[..., idx.get('R', 0)]
        out[..., 1] = rgb8[..., idx.get('G', min(1, nch - 1))]
        out[..., 2] = rgb8[..., idx.get('B', min(2, nch - 1))]
        # alpha is not cut-scaled: normalize by dtype then to 8-bit
        if 'A' in idx:
            out[..., 3] = (_norm_alpha(a[..., idx['A']], a.dtype) *
                           255.0).astype(np.uint8)
        else:
            out[..., 3] = 255
        return np.ascontiguousarray(out)

    # ---- colormap (mirror gl_set_cmap) -----------------------------------

    def _make_cmap_rgba(self):
        # TODO: support per-image RGBMaps.  All images currently share this
        # single colormap (the viewer's rgbmap); a canvas image may specify its
        # own ``cvs_img.rgbmap``, which is ignored here.  To honor it, the
        # colormap would need to become per-image -- e.g. a colormap texel
        # buffer per distinct rgbmap (cached/uploaded like the image textures)
        # and bound per draw in MultiImagePipeline (which already uses per-image
        # descriptor sets), instead of one shared ``set_colormap``.
        rgbmap = self.viewer.get_rgbmap()
        hashsize = rgbmap.get_hash_size()
        cmap_len = min(hashsize, 4096)
        idx = rgbmap.get_hasharray(np.arange(0, hashsize))
        if hashsize != cmap_len:
            xi = (np.arange(0, cmap_len) * (hashsize / cmap_len)).clip(
                0, hashsize - 1).astype(np.uint)
            idx = idx[xi]
        colors = np.ascontiguousarray(rgbmap.get_colors(), dtype=np.uint8)
        colors = colors[idx]
        alpha = np.full((colors.shape[0], 1), 255, dtype=np.uint8)
        return np.ascontiguousarray(np.concatenate([colors, alpha], axis=1))

    # ---- replay collection (called by the live RenderContext) ------------

    def vk_add_image(self, cvs_img, cpoints, cache):
        data = getattr(cache, 'vk_data', None)
        if data is None:
            return
        image_type = getattr(cache, 'vk_type', 0)
        cp = np.asarray(cpoints, dtype=np.float32)[:, :2]
        # get_points()/get_cpoints() give a quad loop [LL, LR, UR, UL] with
        # uv [(0,0),(1,0),(1,1),(0,1)] (matching the GL fan); reorder to a
        # triangle strip: [LL, LR, UL, UR] with uv [(0,0),(1,0),(0,1),(1,1)]
        quad_pos = cp[[0, 1, 3, 2]]
        quad_uv = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
        loval, hival = self.viewer.get_cut_levels()
        cuts = getattr(cvs_img, 'cuts', None)
        if cuts is not None:
            loval, hival = cuts
        obj_alpha = float(getattr(cvs_img, 'alpha', 1.0))
        # drawn in replay (canvas) order, each with its own cached texture
        self._images.append(_ImageDraw(
            image_id=cvs_img.image_id, data=data, image_type=image_type,
            quad_pos=quad_pos, quad_uv=quad_uv, loval=float(loval),
            hival=float(hival), obj_alpha=obj_alpha))

    def vk_add_shape(self, kind, cpoints, line, fill):
        if self._mode3d:
            self._vk_add_shape_3d(kind, cpoints, line, fill)
            return
        verts = trcalc.strip_z(np.asarray(cpoints, dtype=np.float32))
        if len(verts) == 0:
            return
        if fill is not None and getattr(fill, 'color', None) is not None:
            self._shapes.append((pipelines.TRIANGLE_FAN, verts,
                                 fill._color_4tup))
        if (line is not None and getattr(line, 'color', None) is not None and
                getattr(line, 'linewidth', 1) > 0):
            color = line._color_4tup
            lw = float(getattr(line, 'linewidth', 1))
            closed = kind not in ('line', 'path')     # polygon/circle loop
            dashed = getattr(line, 'linestyle', 'solid') == 'dash'

            def _emit(run_pts, run_closed):
                # draw one polyline run: wide -> expanded triangles, else the
                # cheap native line primitive
                if lw > 1.0:
                    tris = stroke.stroke_polyline(run_pts, lw, run_closed)
                    if len(tris) > 0:
                        self._shapes.append((pipelines.TRIANGLE_LIST, tris,
                                             color))
                elif len(run_pts) >= 2:
                    self._shapes.append((pipelines.LINE_STRIP, run_pts, color))

            if dashed:
                # break into "on" runs (each an open sub-polyline)
                for run in stroke.dash_polylines(verts, stroke.dash_pattern(lw), closed):
                    _emit(run, False)
            elif closed:
                _emit(np.vstack([verts, verts[:1]]), True)
            elif kind == 'line':
                # cheap width-1 line stays a LINE_LIST; wide handled by _emit
                if lw > 1.0:
                    _emit(verts, False)
                else:
                    self._shapes.append((pipelines.LINE_LIST, verts, color))
            else:
                _emit(verts, False)

    def _vk_add_shape_3d(self, kind, cpoints, line, fill):
        # 3D camera mode: keep z, draw with native (thin) primitives -- the
        # pixel-space stroke/dash expansion does not apply in 3D
        verts = trcalc.pad_z(np.asarray(cpoints, dtype=np.float32),
                             dtype=np.float32)
        if len(verts) == 0:
            return
        if fill is not None and getattr(fill, 'color', None) is not None:
            self._shapes.append((pipelines.TRIANGLE_FAN, verts,
                                 fill._color_4tup))
        if (line is not None and getattr(line, 'color', None) is not None and
                getattr(line, 'linewidth', 1) > 0):
            color = line._color_4tup
            if kind == 'line':
                self._shapes.append((pipelines.LINE_LIST, verts, color))
            elif kind == 'path':
                self._shapes.append((pipelines.LINE_STRIP, verts, color))
            else:
                self._shapes.append((pipelines.LINE_STRIP,
                                     np.vstack([verts, verts[:1]]), color))

    def _rasterize_text(self, text, font, color4):
        """Rasterize ``text`` to an RGBA tile (transparent background, colored
        glyphs) using PIL.  Returns ``(rgba, w, h)`` or ``None``."""
        from ginga.pilw import PilHelp
        fontname = getattr(font, 'fontname', 'sans')
        fontsize = max(1, int(round(getattr(font, 'fontsize', 12))))
        try:
            pil_font = PilHelp.get_font(fontname, fontsize)
        except Exception as e:
            self.logger.debug("Vulkan text: could not load font '%s': %s" %
                              (fontname, e))
            return None
        return PilHelp.rasterize_text(text, pil_font, color4)

    def vk_add_text(self, cx, cy, text, rot_deg, font, fill, line):
        if not text or font is None:
            return
        # text is drawn in the fill color (falling back to the line color)
        if fill is not None and getattr(fill, 'color', None) is not None:
            color = fill._color_4tup
        elif line is not None and getattr(line, 'color', None) is not None:
            color = line._color_4tup
        else:
            color = (1.0, 1.0, 1.0, 1.0)
        tile = self._rasterize_text(text, font, color)
        if tile is None:
            return
        rgba, w, h = tile
        # place the tile so its bottom-left sits at the (cx, cy) anchor
        x0, y0 = float(cx), float(cy) - h
        corners = np.array([[x0, y0], [x0 + w, y0],
                            [x0, y0 + h], [x0 + w, y0 + h]], dtype=np.float32)
        if abs(rot_deg) > 1e-3:
            corners = np.asarray(
                trcalc.rotate_coord(corners, [rot_deg], (float(cx), float(cy))),
                dtype=np.float32)[:, :2]
        quad_uv = np.array([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32)
        self._texts.append((rgba, corners, quad_uv))

    # ---- GPU paint / readback --------------------------------------------

    def get_surface_as_array(self, order=None):
        wd, ht = self.dims[:2]
        self._ensure_engine(wd, ht)
        if self._engine is None:
            raise render.RenderError("no Vulkan surface (zero-size window)")

        # (re)build the GPU colormap only when the rgbmap changed
        if self._cmap_dirty:
            self._engine.set_colormap(self._make_cmap_rgba())
            self._cmap_dirty = False

        # replay the render list into GPU draw collections
        self._images = []
        self._shapes = []
        self._texts = []
        cr = RenderContext(self, self.viewer, None)
        self.draw_vector(cr)

        # in 3D mode the camera's view/projection drive the scene; otherwise
        # the fixed window-pixel orthographic transform is used
        push = camera_push(self.camera) if self._mode3d else None
        r, g, b = self.viewer.img_bg[:3]
        self._engine.begin((r, g, b, 1.0), push)
        for im in self._images:
            # upload a texture only when its data changed (or the engine was
            # reallocated); zoom/pan reuse the cached texture
            if (im.image_id in self._img_dirty or
                    not self._engine.has_image(im.image_id)):
                self._engine.upload_image(im.image_id, im.data, im.image_type)
                self._img_dirty.discard(im.image_id)
            self._engine.record_image(im.image_id, im.quad_pos, im.quad_uv,
                                      im.loval, im.hival, im.image_type,
                                      im.obj_alpha)
        self._engine.record_shapes(self._shapes)
        self._engine.record_texts(self._texts)     # text on top
        self._engine.end()

        arr = self._engine.get_surface_as_array('RGBA')
        dst = 'RGBA' if order is None else order.upper()
        if dst == 'RGBA':
            return arr
        idx = ['RGBA'.index(c) for c in dst]
        return np.ascontiguousarray(arr[..., idx])

    # ---- text (stub until native text is implemented) --------------------

    def text_extents(self, text, font):
        from PIL import Image, ImageDraw
        from ginga.pilw import PilHelp
        fontname = getattr(font, 'fontname', 'sans')
        fontsize = max(1, int(round(getattr(font, 'fontsize', 12))))
        try:
            pil_font = PilHelp.get_font(fontname, fontsize)
            d = ImageDraw.Draw(Image.new('RGBA', (4, 4)))
            l, t, r, b = d.textbbox((0, 0), text, font=pil_font)
            return (max(1, r - l), max(1, b - t))
        except Exception:
            return (int(len(text) * fontsize * 0.5), int(fontsize))

    def get_dimensions(self, shape):
        cr = vec.RenderContext(self, self.viewer, None)
        font = cr.get_font_from_shape(shape)
        return self.text_extents(shape.text, font)

    def __del__(self):
        try:
            if getattr(self, '_engine', None) is not None:
                self._engine.destroy()
            if getattr(self, 'ctx', None) is not None:
                self.ctx.destroy()
        except Exception:
            pass
