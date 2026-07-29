"""Tests for the Vulkan engine core (ginga.vulkan.vkcore).

These require the optional ``vulkan`` Python binding and a working Vulkan
loader/driver (Mesa Lavapipe suffices, so no GPU is needed).  They skip
cleanly when the binding or a usable device is unavailable, so the normal
test suite is unaffected.
"""
import numpy as np
import pytest

pytest.importorskip('vulkan')
from ginga.vulkan import vkcore  # noqa: E402


@pytest.fixture(scope='module')
def ctx():
    try:
        c = vkcore.VulkanContext(prefer_cpu=True)
    except vkcore.VulkanError as e:
        pytest.skip("no usable Vulkan device: %s" % e)
    yield c
    c.destroy()


def test_context_and_device(ctx):
    assert ctx.device is not None
    assert isinstance(ctx.device_name(), str) and ctx.device_name()


def test_offscreen_clear_readback(ctx):
    tgt = vkcore.OffscreenColorTarget(ctx, 32, 24)
    try:
        tgt.clear((0.1, 0.2, 0.3, 1.0))
        arr = tgt.read_rgba()
        assert arr.shape == (24, 32, 4) and arr.dtype == np.uint8
        expected = np.round(np.array([0.1, 0.2, 0.3, 1.0]) * 255).astype(
            np.uint8)
        assert np.all(arr == expected)
    finally:
        tgt.destroy()


def test_buffer_roundtrip(ctx):
    import vulkan as vk
    data = np.arange(64, dtype=np.uint8)
    buf, mem = ctx.create_buffer(
        data.nbytes, vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
        vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
        vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
    try:
        ctx.upload(mem, data)
        assert np.array_equal(ctx.read(mem, data.nbytes), data)
    finally:
        vk.vkDestroyBuffer(ctx.device, buf, None)
        vk.vkFreeMemory(ctx.device, mem, None)
