"""Tests for the Vulkan shape pipeline (ginga.vulkan.pipelines.ShapePipeline).

Require the optional ``vulkan`` binding + a device (Lavapipe suffices); skip
cleanly otherwise.
"""
import numpy as np
import pytest

pytest.importorskip('vulkan')
from ginga.vulkan import vkcore, pipelines  # noqa: E402


@pytest.fixture(scope='module')
def ctx():
    try:
        c = vkcore.VulkanContext(prefer_cpu=True)
    except vkcore.VulkanError as e:
        pytest.skip("no usable Vulkan device: %s" % e)
    yield c
    c.destroy()


@pytest.fixture
def target(ctx):
    t = vkcore.OffscreenColorTarget(ctx, 64, 64)
    yield t
    t.destroy()


# clip-space triangle (Vulkan y points down); covers the image center
TRI = np.array([[0.0, -0.5], [0.5, 0.5], [-0.5, 0.5]], dtype=np.float32)


def test_filled_triangle(ctx, target):
    sp = pipelines.ShapePipeline(ctx, target)
    try:
        sp.render([(pipelines.TRIANGLE_FAN, TRI, (1.0, 0.0, 0.0, 1.0))],
                  clear_color=(0.0, 0.0, 0.0, 1.0))
        arr = target.read_rgba()
        assert tuple(int(x) for x in arr[32, 32][:3]) == (255, 0, 0)  # center
        assert tuple(int(x) for x in arr[0, 0][:3]) == (0, 0, 0)      # corner
        assert int(np.count_nonzero(arr[..., 0] > 200)) > 100
    finally:
        sp.destroy()


def test_line_strip(ctx, target):
    sp = pipelines.ShapePipeline(ctx, target)
    try:
        line = np.array([[-0.9, 0.0], [0.9, 0.0]], dtype=np.float32)
        sp.render([(pipelines.LINE_STRIP, line, (0.0, 1.0, 0.0, 1.0))])
        arr = target.read_rgba()
        # the horizontal line lands on the middle row (clip y=0 -> device
        # y=32.0, which rasterizes onto an adjacent row); check a small band
        assert int(np.count_nonzero(arr[30:34, :, 1] > 200)) > 10
        # ...and nothing far from the middle
        assert int(np.count_nonzero(arr[:20, :, 1] > 200)) == 0
    finally:
        sp.destroy()


def test_alpha_blending(ctx, target):
    sp = pipelines.ShapePipeline(ctx, target)
    try:
        # translucent red over a blue clear -> ~50/50 blend at the center
        sp.render([(pipelines.TRIANGLE_FAN, TRI, (1.0, 0.0, 0.0, 0.5))],
                  clear_color=(0.0, 0.0, 1.0, 1.0))
        r, g, b = (int(x) for x in target.read_rgba()[32, 32][:3])
        assert 110 < r < 145 and g < 10 and 110 < b < 145
    finally:
        sp.destroy()
