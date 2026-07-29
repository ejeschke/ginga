#
# vkcore.py -- core Vulkan engine helpers for the Ginga Vulkan renderer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Toolkit-agnostic Vulkan engine primitives.

A minimal device/queue :class:`VulkanContext` and an
:class:`OffscreenColorTarget` (a color ``VkImage`` render target with CPU
readback).  There is no window or surface here -- this is the headless core
the renderer (and CI, via Mesa Lavapipe) build on.
"""
import numpy as np

try:
    import vulkan as vk
    have_vulkan = True
except ImportError:
    have_vulkan = False


class VulkanError(Exception):
    pass


def _s(name):
    """``_s('IMAGE_CREATE_INFO') -> vk.VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO``."""
    return getattr(vk, 'VK_STRUCTURE_TYPE_' + name)


class VulkanContext:
    """Owns a ``VkInstance``, a physical/logical device with a graphics queue,
    a command pool, and memory/buffer/image/command helpers.

    Parameters
    ----------
    app_name : str
        Application name reported to the driver.
    prefer_cpu : bool
        If True, prefer a CPU (software, e.g. Lavapipe) device -- useful for
        deterministic, GPU-free headless/CI rendering.  Otherwise a GPU is
        preferred when present.
    """

    def __init__(self, app_name='ginga', prefer_cpu=False):
        if not have_vulkan:
            raise VulkanError("the 'vulkan' Python package is not installed; "
                              "cannot use the Vulkan renderer")
        self.instance = None
        self.device = None
        self.command_pool = None
        try:
            self._init(app_name, prefer_cpu)
        except Exception:
            self.destroy()
            raise

    def _init(self, app_name, prefer_cpu):
        app = vk.VkApplicationInfo(sType=_s('APPLICATION_INFO'),
                                   pApplicationName=app_name,
                                   apiVersion=vk.VK_API_VERSION_1_0)
        self.instance = vk.vkCreateInstance(
            vk.VkInstanceCreateInfo(sType=_s('INSTANCE_CREATE_INFO'),
                                    pApplicationInfo=app), None)
        self.physical, self.graphics_qf = self._pick_device(prefer_cpu)
        self.dev_props = vk.vkGetPhysicalDeviceProperties(self.physical)
        self.mem_props = vk.vkGetPhysicalDeviceMemoryProperties(self.physical)
        dqi = vk.VkDeviceQueueCreateInfo(
            sType=_s('DEVICE_QUEUE_CREATE_INFO'),
            queueFamilyIndex=self.graphics_qf, queueCount=1,
            pQueuePriorities=[1.0])
        self.device = vk.vkCreateDevice(self.physical, vk.VkDeviceCreateInfo(
            sType=_s('DEVICE_CREATE_INFO'), queueCreateInfoCount=1,
            pQueueCreateInfos=[dqi]), None)
        self.queue = vk.vkGetDeviceQueue(self.device, self.graphics_qf, 0)
        self.command_pool = vk.vkCreateCommandPool(
            self.device, vk.VkCommandPoolCreateInfo(
                sType=_s('COMMAND_POOL_CREATE_INFO'),
                queueFamilyIndex=self.graphics_qf), None)

    def _pick_device(self, prefer_cpu):
        best = None   # (rank, device, queue_family)
        for d in vk.vkEnumeratePhysicalDevices(self.instance):
            qf = None
            for i, q in enumerate(
                    vk.vkGetPhysicalDeviceQueueFamilyProperties(d)):
                if q.queueFlags & vk.VK_QUEUE_GRAPHICS_BIT:
                    qf = i
                    break
            if qf is None:
                continue
            is_cpu = (vk.vkGetPhysicalDeviceProperties(d).deviceType ==
                      vk.VK_PHYSICAL_DEVICE_TYPE_CPU)
            # prefer an exact prefer_cpu match, then (tie-break) a real GPU
            rank = (2 if is_cpu == prefer_cpu else 0) + (0 if is_cpu else 1)
            if best is None or rank > best[0]:
                best = (rank, d, qf)
        if best is None:
            raise VulkanError("no graphics-capable Vulkan device found")
        return best[1], best[2]

    def device_name(self):
        n = self.dev_props.deviceName
        return n.decode() if isinstance(n, bytes) else str(n)

    # ---- memory / resource helpers ---------------------------------------

    def find_memory_type(self, type_bits, flags):
        for i in range(self.mem_props.memoryTypeCount):
            if (type_bits & (1 << i)) and \
               (self.mem_props.memoryTypes[i].propertyFlags & flags) == flags:
                return i
        raise VulkanError("no suitable memory type (bits=0x%x flags=0x%x)"
                          % (type_bits, flags))

    def create_buffer(self, size, usage, mem_flags):
        buf = vk.vkCreateBuffer(self.device, vk.VkBufferCreateInfo(
            sType=_s('BUFFER_CREATE_INFO'), size=size, usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE), None)
        req = vk.vkGetBufferMemoryRequirements(self.device, buf)
        mem = vk.vkAllocateMemory(self.device, vk.VkMemoryAllocateInfo(
            sType=_s('MEMORY_ALLOCATE_INFO'), allocationSize=req.size,
            memoryTypeIndex=self.find_memory_type(req.memoryTypeBits,
                                                  mem_flags)), None)
        vk.vkBindBufferMemory(self.device, buf, mem, 0)
        return buf, mem

    def create_image(self, width, height, fmt, usage, mem_flags):
        img = vk.vkCreateImage(self.device, vk.VkImageCreateInfo(
            sType=_s('IMAGE_CREATE_INFO'), imageType=vk.VK_IMAGE_TYPE_2D,
            format=fmt, extent=vk.VkExtent3D(width, height, 1), mipLevels=1,
            arrayLayers=1, samples=vk.VK_SAMPLE_COUNT_1_BIT,
            tiling=vk.VK_IMAGE_TILING_OPTIMAL, usage=usage,
            sharingMode=vk.VK_SHARING_MODE_EXCLUSIVE,
            initialLayout=vk.VK_IMAGE_LAYOUT_UNDEFINED), None)
        req = vk.vkGetImageMemoryRequirements(self.device, img)
        mem = vk.vkAllocateMemory(self.device, vk.VkMemoryAllocateInfo(
            sType=_s('MEMORY_ALLOCATE_INFO'), allocationSize=req.size,
            memoryTypeIndex=self.find_memory_type(req.memoryTypeBits,
                                                  mem_flags)), None)
        vk.vkBindImageMemory(self.device, img, mem, 0)
        return img, mem

    def create_shader_module(self, spv):
        """Create a ``VkShaderModule`` from SPIR-V ``bytes``."""
        return vk.vkCreateShaderModule(self.device, vk.VkShaderModuleCreateInfo(
            sType=_s('SHADER_MODULE_CREATE_INFO'), codeSize=len(spv),
            pCode=spv), None)

    def create_image_view(self, image, fmt):
        return vk.vkCreateImageView(self.device, vk.VkImageViewCreateInfo(
            sType=_s('IMAGE_VIEW_CREATE_INFO'), image=image,
            viewType=vk.VK_IMAGE_VIEW_TYPE_2D, format=fmt,
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT, baseMipLevel=0,
                levelCount=1, baseArrayLayer=0, layerCount=1)), None)

    def create_buffer_view(self, buffer, fmt, size):
        """Create a ``VkBufferView`` (texel buffer) over the whole buffer."""
        return vk.vkCreateBufferView(self.device, vk.VkBufferViewCreateInfo(
            sType=_s('BUFFER_VIEW_CREATE_INFO'), buffer=buffer, format=fmt,
            offset=0, range=size), None)

    def create_sampler(self, mag_filter=None):
        f = vk.VK_FILTER_NEAREST if mag_filter is None else mag_filter
        clamp = vk.VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE
        return vk.vkCreateSampler(self.device, vk.VkSamplerCreateInfo(
            sType=_s('SAMPLER_CREATE_INFO'), magFilter=f, minFilter=f,
            mipmapMode=vk.VK_SAMPLER_MIPMAP_MODE_NEAREST, addressModeU=clamp,
            addressModeV=clamp, addressModeW=clamp,
            anisotropyEnable=vk.VK_FALSE,
            unnormalizedCoordinates=vk.VK_FALSE), None)

    def image_barrier(self, cmd, image, old_layout, new_layout):
        """Record a conservative image layout transition (broad masks)."""
        b = vk.VkImageMemoryBarrier(
            sType=_s('IMAGE_MEMORY_BARRIER'), oldLayout=old_layout,
            newLayout=new_layout, srcAccessMask=vk.VK_ACCESS_MEMORY_WRITE_BIT,
            dstAccessMask=(vk.VK_ACCESS_MEMORY_READ_BIT |
                           vk.VK_ACCESS_MEMORY_WRITE_BIT),
            srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED, image=image,
            subresourceRange=vk.VkImageSubresourceRange(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT, baseMipLevel=0,
                levelCount=1, baseArrayLayer=0, layerCount=1))
        vk.vkCmdPipelineBarrier(
            cmd, vk.VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            vk.VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, None, 0, None, 1, [b])

    def create_texture_2d(self, width, height, fmt, data):
        """Create a device-local sampled 2D image, upload ``data`` via a
        staging buffer, and leave it in SHADER_READ_ONLY_OPTIMAL.

        Returns ``(image, memory, view)``.
        """
        if not isinstance(data, (bytes, bytearray)):
            data = np.ascontiguousarray(data).tobytes()
        img, mem = self.create_image(
            width, height, fmt,
            vk.VK_IMAGE_USAGE_SAMPLED_BIT | vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT,
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)
        staging, stg_mem = self.create_buffer(
            len(data), vk.VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        self.upload(stg_mem, data)
        cmd = self.begin_commands()
        self.image_barrier(cmd, img, vk.VK_IMAGE_LAYOUT_UNDEFINED,
                           vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL)
        vk.vkCmdCopyBufferToImage(
            cmd, staging, img, vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1,
            [vk.VkBufferImageCopy(
                imageSubresource=vk.VkImageSubresourceLayers(
                    aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT, mipLevel=0,
                    baseArrayLayer=0, layerCount=1),
                imageExtent=vk.VkExtent3D(width, height, 1))])
        self.image_barrier(cmd, img,
                           vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                           vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL)
        self.submit_wait(cmd)
        vk.vkDestroyBuffer(self.device, staging, None)
        vk.vkFreeMemory(self.device, stg_mem, None)
        return img, mem, self.create_image_view(img, fmt)

    def upload(self, mem, data, size=None):
        """Copy ``bytes``/ndarray ``data`` into a mapped host-visible ``mem``."""
        if not isinstance(data, (bytes, bytearray)):
            data = np.ascontiguousarray(data).tobytes()
        size = len(data) if size is None else size
        ptr = vk.vkMapMemory(self.device, mem, 0, size, 0)
        ptr[0:size] = data[:size]
        vk.vkUnmapMemory(self.device, mem)

    def read(self, mem, size):
        """Return ``size`` bytes of a mapped host-visible ``mem`` as uint8."""
        ptr = vk.vkMapMemory(self.device, mem, 0, size, 0)
        arr = np.frombuffer(ptr, np.uint8, count=size).copy()
        vk.vkUnmapMemory(self.device, mem)
        return arr

    # ---- one-time command submission -------------------------------------

    def begin_commands(self):
        cmd = vk.vkAllocateCommandBuffers(
            self.device, vk.VkCommandBufferAllocateInfo(
                sType=_s('COMMAND_BUFFER_ALLOCATE_INFO'),
                commandPool=self.command_pool,
                level=vk.VK_COMMAND_BUFFER_LEVEL_PRIMARY,
                commandBufferCount=1))[0]
        vk.vkBeginCommandBuffer(cmd, vk.VkCommandBufferBeginInfo(
            sType=_s('COMMAND_BUFFER_BEGIN_INFO'),
            flags=vk.VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT))
        return cmd

    def submit_wait(self, cmd):
        vk.vkEndCommandBuffer(cmd)
        vk.vkQueueSubmit(self.queue, 1, [vk.VkSubmitInfo(
            sType=_s('SUBMIT_INFO'), commandBufferCount=1,
            pCommandBuffers=[cmd])], vk.VK_NULL_HANDLE)
        vk.vkQueueWaitIdle(self.queue)
        vk.vkFreeCommandBuffers(self.device, self.command_pool, 1, [cmd])

    def destroy(self):
        if not have_vulkan:
            return
        if getattr(self, 'command_pool', None) is not None:
            vk.vkDestroyCommandPool(self.device, self.command_pool, None)
            self.command_pool = None
        if getattr(self, 'device', None) is not None:
            vk.vkDestroyDevice(self.device, None)
            self.device = None
        if getattr(self, 'instance', None) is not None:
            vk.vkDestroyInstance(self.instance, None)
            self.instance = None


class OffscreenColorTarget:
    """A ``width`` x ``height`` color image usable as a render target, with a
    host-visible readback buffer and a tracked layout.
    """

    def __init__(self, ctx, width, height, fmt=None):
        self.ctx = ctx
        self.width = width
        self.height = height
        self.fmt = fmt if fmt is not None else vk.VK_FORMAT_R8G8B8A8_UNORM
        self.layout = vk.VK_IMAGE_LAYOUT_UNDEFINED
        usage = (vk.VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                 vk.VK_IMAGE_USAGE_TRANSFER_SRC_BIT |
                 vk.VK_IMAGE_USAGE_TRANSFER_DST_BIT)
        self.image, self.image_mem = ctx.create_image(
            width, height, self.fmt, usage,
            vk.VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT)
        self.view = ctx.create_image_view(self.image, self.fmt)
        self._nbytes = width * height * 4
        self.readbuf, self.readbuf_mem = ctx.create_buffer(
            self._nbytes, vk.VK_BUFFER_USAGE_TRANSFER_DST_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)

    def _full_range(self):
        return vk.VkImageSubresourceRange(
            aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT, baseMipLevel=0,
            levelCount=1, baseArrayLayer=0, layerCount=1)

    def transition(self, cmd, new_layout):
        """Record a conservative layout transition and update the tracked
        layout.  (Broad access/stage masks -- correctness over speed; this
        renderer serializes with a queue-wait per submission anyway.)"""
        barrier = vk.VkImageMemoryBarrier(
            sType=_s('IMAGE_MEMORY_BARRIER'), oldLayout=self.layout,
            newLayout=new_layout,
            srcAccessMask=vk.VK_ACCESS_MEMORY_WRITE_BIT,
            dstAccessMask=(vk.VK_ACCESS_MEMORY_READ_BIT |
                           vk.VK_ACCESS_MEMORY_WRITE_BIT),
            srcQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            dstQueueFamilyIndex=vk.VK_QUEUE_FAMILY_IGNORED,
            image=self.image, subresourceRange=self._full_range())
        vk.vkCmdPipelineBarrier(
            cmd, vk.VK_PIPELINE_STAGE_ALL_COMMANDS_BIT,
            vk.VK_PIPELINE_STAGE_ALL_COMMANDS_BIT, 0, 0, None, 0, None, 1,
            [barrier])
        self.layout = new_layout

    def clear(self, color=(0.0, 0.0, 0.0, 1.0)):
        cmd = self.ctx.begin_commands()
        self.transition(cmd, vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL)
        vk.vkCmdClearColorImage(
            cmd, self.image, vk.VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            vk.VkClearColorValue(float32=list(color)), 1, [self._full_range()])
        self.ctx.submit_wait(cmd)

    def read_rgba(self):
        """Return the image as an ``(H, W, 4)`` uint8 RGBA array."""
        cmd = self.ctx.begin_commands()
        self.transition(cmd, vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL)
        region = vk.VkBufferImageCopy(
            imageSubresource=vk.VkImageSubresourceLayers(
                aspectMask=vk.VK_IMAGE_ASPECT_COLOR_BIT, mipLevel=0,
                baseArrayLayer=0, layerCount=1),
            imageExtent=vk.VkExtent3D(self.width, self.height, 1))
        vk.vkCmdCopyImageToBuffer(
            cmd, self.image, vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            self.readbuf, 1, [region])
        self.ctx.submit_wait(cmd)
        return self.ctx.read(self.readbuf_mem, self._nbytes).reshape(
            self.height, self.width, 4)

    def destroy(self):
        d = self.ctx.device
        vk.vkDestroyImageView(d, self.view, None)
        vk.vkDestroyImage(d, self.image, None)
        vk.vkFreeMemory(d, self.image_mem, None)
        vk.vkDestroyBuffer(d, self.readbuf, None)
        vk.vkFreeMemory(d, self.readbuf_mem, None)
