"""End-to-end tests: a headless ImageView using the GPU-native Vulkan
renderer.

Drives the GPU path: no standard CPU pipeline stages run; images are
colormapped in the fragment shader and shapes/lines/text are drawn by the
Vulkan pipelines, all via vector replay.

Requires the optional ``vulkan`` binding + a device (Lavapipe suffices).
"""
import logging

import numpy as np
import pytest

pytest.importorskip('vulkan')
from ginga import ImageView, AstroImage       # noqa: E402
from ginga.vulkan import vkcore                # noqa: E402
from ginga.vulkan.CanvasRenderVk import CanvasRendererGPU  # noqa: E402
from ginga.canvas.CanvasObject import get_canvas_types    # noqa: E402

# register the geometry draw types (line, rectangle, text, path, ...) used by
# canvas.get_draw_class() below
get_canvas_types()

logger = logging.getLogger('test_vulkan_viewer2')


class VulkanView(ImageView.ImageViewBase):
    """A minimal, invisible ImageView backed by the GPU-native Vulkan renderer."""

    def __init__(self, logger=None, settings=None):
        super().__init__(logger=logger, settings=settings)
        self.rgb_order = 'RGB'
        self.defer_redraw = False
        self.renderer = CanvasRendererGPU(self)

    def reschedule_redraw(self, time_sec):
        self.delayed_redraw()

    def update_widget(self):
        pass

    def configure_window(self, width, height):
        self.configure(width, height)


@pytest.fixture(scope='module')
def viewer():
    try:
        vkcore.VulkanContext(prefer_cpu=True).destroy()
    except vkcore.VulkanError as e:
        pytest.skip("no usable Vulkan device: %s" % e)
    v = VulkanView(logger=logger)
    v.enable_autozoom('on')
    v.enable_autocuts('on')
    v.set_desired_size(80, 60)
    v.configure(80, 60)
    yield v


def _render(viewer, data):
    img = AstroImage.AstroImage(logger=logger)
    img.set_data(data)
    viewer.set_image(img)
    viewer.redraw_now(whence=0)
    return viewer.renderer.get_surface_as_array('RGBA')


def test_uniform_image_renders(viewer):
    img = AstroImage.AstroImage(logger=logger)
    img.set_data(np.full((20, 20), 1000.0, dtype=np.float32))
    viewer.set_image(img)
    viewer.cut_levels(0.0, 2000.0)               # explicit (min==max is black)
    viewer.redraw_now(whence=0)
    arr = viewer.renderer.get_surface_as_array('RGBA')
    assert arr.shape == (60, 80, 4)
    # the constant image (GPU-colormapped) renders as a uniform, non-black
    # grayscale region
    rgb = arr[..., :3].reshape(-1, 3)
    nonblack = rgb[rgb.max(axis=1) > 0]
    assert len(nonblack) > (60 * 80) // 4
    vals, counts = np.unique(nonblack, axis=0, return_counts=True)
    dom = vals[counts.argmax()]
    assert dom[0] == dom[1] == dom[2] and int(dom[0]) > 0


def test_gradient_image_varies_across_frame(viewer):
    # left-dark / right-bright ramp -> rendered frame varies left-to-right
    ramp = np.tile(np.linspace(0, 1000, 40, dtype=np.float32), (30, 1))
    arr = _render(viewer, ramp)
    left = int(arr[30, 8, :3].mean())
    right = int(arr[30, 72, :3].mean())
    assert right - left > 40


def test_shape_drawn_on_gpu(viewer):
    """A canvas shape (drawn by the shape pipeline via vector replay) appears
    over the image."""
    ramp = np.tile(np.linspace(0, 1000, 40, dtype=np.float32), (30, 1))
    _render(viewer, ramp)

    canvas = viewer.get_canvas()
    canvas.delete_all_objects()
    # a filled red box in data coords near image center
    Box = canvas.get_draw_class('rectangle')
    canvas.add(Box(15, 10, 25, 20, color='red', fill=True, fillcolor='red',
                   fillalpha=1.0))
    viewer.redraw_now(whence=0)
    arr = viewer.renderer.get_surface_as_array('RGBA')

    # somewhere in the frame there should be a strongly-red pixel from the box
    rgb = arr[..., :3].astype(int)
    red = ((rgb[..., 0] > 180) & (rgb[..., 1] < 80) & (rgb[..., 2] < 80))
    assert red.any()
    canvas.delete_all_objects()


def test_zoom_uses_transform_not_recut(viewer):
    """Zoom must stretch the cached texture via the quad (like GL's frustum),
    not re-cut/re-upload the image."""
    ramp = np.tile(np.linspace(0, 1000, 10, dtype=np.float32), (10, 1))
    img = AstroImage.AstroImage(logger=logger)
    img.set_data(ramp)
    viewer.configure(80, 60)
    viewer.enable_autozoom('off')                # test explicit zoom levels
    viewer.set_image(img)

    def find_img(canvas):
        for o in canvas.get_objects():
            if hasattr(o, 'prepare_image'):
                return o
            if o.is_compound():
                r = find_img(o)
                if r is not None:
                    return r
        return None
    obj = find_img(viewer.get_private_canvas())

    # measure the bright part of the image (the default bg is mid-grey, so
    # count clearly-bright pixels rather than "non-black")
    def bright_px(arr):
        return int((arr[..., :3].astype(int).mean(axis=2) > 160).sum())

    viewer.scale_to(2.0, 2.0)                     # 10px image -> 20px on screen
    viewer.redraw_now(whence=0)
    n1 = bright_px(viewer.renderer.get_surface_as_array('RGBA'))
    cut1 = obj.get_cache(viewer).cutout.shape

    # count GPU texture uploads across a pure zoom
    engine = viewer.renderer._engine
    uploads = [0]
    orig = engine.upload_image
    engine.upload_image = lambda d: (uploads.__setitem__(0, uploads[0] + 1),
                                     orig(d))[1]
    try:
        viewer.scale_to(5.0, 5.0)              # -> renderer.scale (whence 2.6)
        viewer.redraw_now(whence=viewer._whence)
        arr = viewer.renderer.get_surface_as_array('RGBA')
    finally:
        engine.upload_image = orig

    n2 = bright_px(arr)
    cut2 = obj.get_cache(viewer).cutout.shape

    assert cut1 == cut2                        # cutout not re-cut on zoom
    assert n2 > n1 * 2                          # image covers much more area
    assert uploads[0] == 0                      # texture NOT re-uploaded
    viewer.enable_autozoom('on')


def test_wide_line_is_thicker_than_thin(viewer):
    """A wide canvas line (drawn as expanded triangles) covers more pixels
    than a width-1 line."""
    ramp = np.tile(np.linspace(0, 1000, 40, dtype=np.float32), (30, 1))
    _render(viewer, ramp)
    canvas = viewer.get_canvas()
    Line = canvas.get_draw_class('line')

    def line_px(width):
        canvas.delete_all_objects()
        # cyan is distinguishable from the grayscale image (B >> R)
        canvas.add(Line(5, 15, 35, 15, color='cyan', linewidth=width))
        viewer.redraw_now(whence=0)
        a = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
        return int(((a[..., 2] - a[..., 0]) > 60).sum())      # cyan-ish

    thin = line_px(1)
    thick = line_px(7)
    canvas.delete_all_objects()
    assert thick > thin * 3


def test_dashed_line_renders_fewer_px_than_solid(viewer):
    ramp = np.tile(np.linspace(0, 1000, 40, dtype=np.float32), (30, 1))
    _render(viewer, ramp)
    canvas = viewer.get_canvas()
    Line = canvas.get_draw_class('line')

    def line_px(style):
        canvas.delete_all_objects()
        canvas.add(Line(3, 15, 37, 15, color='cyan', linewidth=3,
                        linestyle=style))
        viewer.redraw_now(whence=0)
        a = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
        return int(((a[..., 2] - a[..., 0]) > 60).sum())

    solid = line_px('solid')
    dash = line_px('dash')
    canvas.delete_all_objects()
    assert 0 < dash < solid * 0.85                  # visibly gapped


def test_native_text_renders(viewer):
    """Text canvas objects are rasterized and blitted (multiple tiles per
    frame via per-draw descriptor sets)."""
    img = AstroImage.AstroImage(logger=logger)
    img.set_data(np.zeros((40, 60), dtype=np.float32))
    viewer.configure(120, 80)
    viewer.enable_autozoom('off')
    viewer.set_image(img)
    viewer.cut_levels(0, 1)
    canvas = viewer.get_canvas()
    canvas.delete_all_objects()
    Text = canvas.get_draw_class('text')
    canvas.add(Text(5, 20, text="Hello", color='yellow', fontsize=16))
    canvas.add(Text(5, 10, text="Vulkan", color='cyan', fontsize=14))
    viewer.redraw_now(whence=0)
    a = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    yellow = int(((a[..., 0] > 150) & (a[..., 1] > 150) &
                  (a[..., 2] < 100)).sum())
    cyan = int(((a[..., 0] < 100) & (a[..., 1] > 150) &
                (a[..., 2] > 150)).sum())
    canvas.delete_all_objects()
    viewer.enable_autozoom('on')
    assert yellow > 20 and cyan > 20               # both labels present


def test_multiple_mono_images(viewer):
    """A second (mono) image overlay is colormapped on the GPU alongside the
    main image, each with its own cached texture."""
    viewer.configure(120, 90)
    viewer.enable_autozoom('off')
    main = AstroImage.AstroImage(logger=logger)
    main.set_data(np.full((60, 80), 800.0, dtype=np.float32))
    viewer.set_image(main)
    viewer.cut_levels(0, 1000)
    viewer.scale_to(1.0, 1.0)

    # NOTE: set_image() places the main image on this (user) canvas, so we
    # must NOT delete_all_objects() here -- that would remove the main image.
    # Add a second image alongside it.
    canvas = viewer.get_canvas()
    NormImage = canvas.get_draw_class('normimage')
    ov = AstroImage.AstroImage(logger=logger)
    ov.set_data(np.full((15, 15), 1000.0, dtype=np.float32))   # brighter
    canvas.add(NormImage(5, 5, ov))
    viewer.redraw_now(whence=0)

    arr = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    gray = ((arr[..., 0] == arr[..., 1]) & (arr[..., 1] == arr[..., 2]))
    # both images are grayscale; the main (~0.8) and overlay (~1.0) show up as
    # two distinct bright levels (plus the mid-grey background)
    bright = np.unique(arr[gray & (arr[..., 0] > 150)][:, 0])
    canvas.delete_all_objects()
    viewer.enable_autozoom('on')
    assert len(bright) >= 2


def test_rgb_image_overlay(viewer):
    """An RGB image is drawn natively (no colormap) via the image_type path."""
    from ginga.RGBImage import RGBImage

    viewer.configure(120, 90)
    viewer.enable_autozoom('off')
    main = AstroImage.AstroImage(logger=logger)
    main.set_data(np.zeros((60, 80), dtype=np.float32))
    viewer.set_image(main)
    viewer.cut_levels(0, 1)
    viewer.scale_to(1.0, 1.0)

    canvas = viewer.get_canvas()
    canvas.delete_all_objects()
    Image = canvas.get_draw_class('image')
    rgb = RGBImage(data_np=np.tile(np.array([220, 20, 20], np.uint8),
                                   (15, 15, 1)))
    canvas.add(Image(40, 30, rgb))
    viewer.redraw_now(whence=0)

    arr = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    red = ((arr[..., 0] > 180) & (arr[..., 1] < 80) & (arr[..., 2] < 80)).sum()
    canvas.delete_all_objects()
    viewer.enable_autozoom('on')
    assert int(red) > 100          # ~15x15 red tile rendered natively


def test_rgb_normimage_interactive_cuts(viewer):
    """An RGB image shown through normimage gets per-channel cut levels applied
    live in-shader (image_type 2), like the OpenGL renderer -- so the usual cut
    controls work without re-preparing the texture."""
    from ginga.RGBImage import RGBImage

    viewer.configure(80, 60)
    viewer.enable_autozoom('off')
    data = np.zeros((40, 60, 3), np.uint8)
    data[..., 0] = np.linspace(0, 255, 60).astype(np.uint8)   # R ramp
    data[..., 1] = 128                                         # G const
    img = RGBImage(data_np=data)
    viewer.set_image(img)                    # -> main normimage, RGB

    def find(c):
        for o in c.get_objects():
            if hasattr(o, 'prepare_image'):
                return o
            if o.is_compound():
                r = find(o)
                if r is not None:
                    return r
        return None
    assert find(viewer.get_private_canvas()).kind == 'normimage'

    viewer.cut_levels(0, 255)
    viewer.redraw_now(whence=0)
    a1 = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    # tightening the cut levels must change the rendered image WITHOUT a
    # re-prepare (whence follows the levels_change path)
    viewer.cut_levels(0, 64)
    viewer.redraw_now(whence=viewer._whence)
    a2 = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    changed = int((np.abs(a2 - a1).sum(axis=2) > 20).sum())
    viewer.enable_autozoom('on')
    assert changed > 500                     # cut levels are live/interactive


def test_rgba_image_alpha_blends(viewer):
    """A per-pixel alpha channel in an RGBA image blends over what is beneath
    it (SRC_ALPHA blending)."""
    from ginga.RGBImage import RGBImage

    viewer.configure(80, 60)
    viewer.enable_autozoom('off')
    main = AstroImage.AstroImage(logger=logger)
    main.set_data(np.full((60, 80), 1000.0, dtype=np.float32))
    viewer.set_image(main)
    viewer.cut_levels(0, 1000)                 # main renders ~white (254)
    viewer.scale_to(1.0, 1.0)

    canvas = viewer.get_canvas()
    Image = canvas.get_draw_class('image')
    rgba = np.zeros((20, 30, 4), np.uint8)
    rgba[..., 1] = 255                         # green
    rgba[..., 3] = 128                         # 50% alpha
    canvas.add(Image(10, 10, RGBImage(data_np=rgba)))
    viewer.redraw_now(whence=0)

    arr = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    # 0.5*green + 0.5*white ~ (127, 255, 127): green stays high, R and B ~half
    blend = ((arr[..., 1] > 200) & (arr[..., 0] > 90) & (arr[..., 0] < 180) &
             (arr[..., 2] > 90) & (arr[..., 2] < 180))
    canvas.delete_all_objects()
    viewer.enable_autozoom('on')
    assert int(blend.sum()) > 200              # ~600 px overlap, blended


def test_per_image_rgbmap(viewer):
    """A normimage overlay with its own rgbmap is colormapped with that map
    (its own GPU colormap buffer), independent of the viewer's."""
    from ginga import RGBMap, cmap

    viewer.configure(120, 60)
    viewer.enable_autozoom('off')
    main = AstroImage.AstroImage(logger=logger)
    main.set_data(np.full((40, 80), 300.0, dtype=np.float32))
    viewer.set_image(main)
    viewer.cut_levels(0, 1000)
    viewer.scale_to(1.0, 1.0)

    canvas = viewer.get_canvas()
    NormImage = canvas.get_draw_class('normimage')
    rm = RGBMap.RGBMapper(logger)
    rm.set_cmap(cmap.get_cmap('rainbow'))
    ov = AstroImage.AstroImage(logger=logger)
    ov.set_data(np.full((15, 15), 900.0, dtype=np.float32))
    # own rgbmap AND own cut levels
    canvas.add(NormImage(5, 5, ov, rgbmap=rm, cuts=(0, 1000)))
    viewer.redraw_now(whence=0)

    arr = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    colored = (~((arr[..., 0] == arr[..., 1]) & (arr[..., 1] == arr[..., 2])))
    # two distinct colormap buffers on the GPU: viewer gray + overlay rainbow
    n_cmaps = len(viewer.renderer._engine.image._cmaps)
    canvas.delete_all_objects()
    viewer.enable_autozoom('on')
    assert int(colored.sum()) > 100        # overlay rendered in color
    assert n_cmaps >= 2                     # not sharing the viewer's colormap


def test_interpolation_methods(viewer):
    """The in-shader display interpolation kernels (bilinear/bicubic/lanczos)
    all smooth a zoomed low-res image far more than nearest, and are distinct
    kernels (not aliased to one another)."""
    viewer.configure(100, 40)
    viewer.enable_autozoom('off')
    data = np.tile(np.linspace(0, 1000, 5, dtype=np.float32), (3, 1))
    img = AstroImage.AstroImage(logger=logger)
    img.set_data(data)
    viewer.set_image(img)
    viewer.cut_levels(0, 1000)
    viewer.scale_to(18.0, 18.0)

    def frame(interp):
        viewer.get_settings().set(interpolation=interp)
        viewer.redraw_now(whence=0)
        return viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)

    def gray_levels(a):
        g = a[(a[..., 0] == a[..., 1]) & (a[..., 1] == a[..., 2])]
        return len(np.unique(g[:, 0]))

    nlev = gray_levels(frame('nearest'))
    bil, bic, lan = frame('linear'), frame('bicubic'), frame('lanczos')
    # each interpolated kernel is much smoother (many more levels) than nearest
    assert min(gray_levels(bil), gray_levels(bic),
               gray_levels(lan)) > nlev * 3
    # and the three kernels produce visibly different results
    assert (bic != bil).any() and (lan != bil).any() and (lan != bic).any()

    viewer.get_settings().set(interpolation='basic')
    viewer.scale_to(1.0, 1.0)
    viewer.enable_autozoom('on')


def test_camera_mode_3d(viewer):
    """3D camera mode: shapes with z coordinates are projected by the camera,
    and orbiting the camera changes the rendered frame."""
    viewer.configure(160, 160)
    canvas = viewer.get_canvas()
    canvas.delete_all_objects()
    Path = canvas.get_draw_class('path')
    Polygon = canvas.get_draw_class('polygon')
    r = 100
    # a 3D octahedron face + a ring in the z=0 plane
    A = [0.18, 0.72, 0.67]
    B = [-0.65, -0.42, 0.63]
    E = [-0.73, 0.55, -0.40]
    canvas.add(Polygon([np.asarray(p) * r for p in (E, A, B)], color='yellow',
                       fill=True, fillcolor='yellow', fillalpha=0.5))
    th = np.linspace(0, 2 * np.pi, 24)
    ring = np.stack([r * np.cos(th), r * np.sin(th), np.zeros_like(th)], axis=1)
    canvas.add(Path(ring, color='cyan'))

    viewer.renderer.mode3d = True
    cam = viewer.renderer.camera
    cam.scale_2d((1.0, 1.0))
    cam.calc_gl_transform()
    viewer.redraw_now(whence=0)
    arr = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)

    def colored(a):
        return ((a.max(axis=2) > 60) &
                ~((a[..., 0] == a[..., 1]) & (a[..., 1] == a[..., 2])))
    n1 = int(colored(arr).sum())
    before = arr.copy()

    cam.orbit(80, 80, 120, 100)                 # tumble the camera
    cam.calc_gl_transform()
    viewer.redraw_now(whence=0)
    arr2 = viewer.renderer.get_surface_as_array('RGBA')[..., :3].astype(int)
    changed = int((np.abs(arr2 - before).sum(axis=2) > 30).sum())

    # restore 2D mode + clean up for later tests
    viewer.renderer.mode3d = False
    canvas.delete_all_objects()

    assert n1 > 100                             # the 3D scene rendered
    assert changed > 100                        # orbit changed the view


def test_resize_reallocates(viewer):
    _render(viewer, np.full((10, 10), 500.0, dtype=np.float32))
    viewer.configure(48, 32)
    arr = viewer.renderer.get_surface_as_array('RGBA')
    assert arr.shape == (32, 48, 4)
