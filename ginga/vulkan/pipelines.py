#
# pipelines.py -- graphics pipelines for the Ginga Vulkan renderer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Graphics pipelines that render into an :class:`~ginga.vulkan.vkcore.
OffscreenColorTarget`.

Provides :class:`ShapePipeline` (solid-colour polygons, lines and paths),
:class:`MultiImagePipeline` (any number of images per frame, colormapped
in-shader like the OpenGL image path) and :class:`GlyphPipeline` (RGBA text
tiles).  :class:`~ginga.vulkan.CanvasRenderVk.CanvasRendererGPU` drives these.
"""
import numpy as np

from .vkcore import have_vulkan, _s, VulkanError
from . import shaders

if have_vulkan:
    import vulkan as vk

    # topologies we support (Vulkan has no LINE_LOOP; close loops manually)
    TRIANGLE_FAN = vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_FAN
    TRIANGLE_LIST = vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST
    LINE_STRIP = vk.VK_PRIMITIVE_TOPOLOGY_LINE_STRIP
    LINE_LIST = vk.VK_PRIMITIVE_TOPOLOGY_LINE_LIST


def _verts3(pts):
    """Return an ``(N, 3)`` float32 array from ``(N, 2)`` or ``(N, 3)`` input
    (2D points get z=0)."""
    a = np.ascontiguousarray(pts, dtype=np.float32)
    if a.ndim != 2 or a.shape[1] not in (2, 3):
        raise VulkanError("vertices must be (N, 2) or (N, 3)")
    if a.shape[1] == 2:
        a = np.column_stack([a, np.zeros(len(a), dtype=np.float32)])
    return np.ascontiguousarray(a, dtype=np.float32)


def _mats(view, projection):
    """Pack ``view`` + ``projection`` (4x4, or None=identity) into the 128-byte
    vertex push constant."""
    view = np.eye(4, dtype=np.float32) if view is None else view
    projection = np.eye(4, dtype=np.float32) if projection is None \
        else projection
    return (np.ascontiguousarray(view, np.float32).tobytes() +
            np.ascontiguousarray(projection, np.float32).tobytes())


def _textured_quad_pipeline(ctx, vmod, fmod, layout, render_pass, width,
                            height):
    """Create a graphics pipeline for a textured quad: vertex input is
    ``vec2 position`` + ``vec2 texcoord`` (stride 16), triangle strip, alpha
    blending."""
    stages = [
        vk.VkPipelineShaderStageCreateInfo(
            sType=_s('PIPELINE_SHADER_STAGE_CREATE_INFO'),
            stage=vk.VK_SHADER_STAGE_VERTEX_BIT, module=vmod, pName="main"),
        vk.VkPipelineShaderStageCreateInfo(
            sType=_s('PIPELINE_SHADER_STAGE_CREATE_INFO'),
            stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT, module=fmod, pName="main")]
    vin = vk.VkPipelineVertexInputStateCreateInfo(
        sType=_s('PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO'),
        vertexBindingDescriptionCount=1, pVertexBindingDescriptions=[
            vk.VkVertexInputBindingDescription(
                binding=0, stride=16,
                inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX)],
        vertexAttributeDescriptionCount=2, pVertexAttributeDescriptions=[
            vk.VkVertexInputAttributeDescription(
                location=0, binding=0,
                format=vk.VK_FORMAT_R32G32_SFLOAT, offset=0),
            vk.VkVertexInputAttributeDescription(
                location=1, binding=0,
                format=vk.VK_FORMAT_R32G32_SFLOAT, offset=8)])
    blend = vk.VkPipelineColorBlendAttachmentState(
        colorWriteMask=0xF, blendEnable=vk.VK_TRUE,
        srcColorBlendFactor=vk.VK_BLEND_FACTOR_SRC_ALPHA,
        dstColorBlendFactor=vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA,
        colorBlendOp=vk.VK_BLEND_OP_ADD,
        srcAlphaBlendFactor=vk.VK_BLEND_FACTOR_ONE,
        dstAlphaBlendFactor=vk.VK_BLEND_FACTOR_ZERO,
        alphaBlendOp=vk.VK_BLEND_OP_ADD)
    ci = vk.VkGraphicsPipelineCreateInfo(
        sType=_s('GRAPHICS_PIPELINE_CREATE_INFO'), stageCount=2,
        pStages=stages, pVertexInputState=vin,
        pInputAssemblyState=vk.VkPipelineInputAssemblyStateCreateInfo(
            sType=_s('PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO'),
            topology=vk.VK_PRIMITIVE_TOPOLOGY_TRIANGLE_STRIP),
        pViewportState=vk.VkPipelineViewportStateCreateInfo(
            sType=_s('PIPELINE_VIEWPORT_STATE_CREATE_INFO'),
            viewportCount=1, pViewports=[vk.VkViewport(0, 0, width, height,
                                                       0, 1)],
            scissorCount=1, pScissors=[vk.VkRect2D(
                offset=vk.VkOffset2D(0, 0),
                extent=vk.VkExtent2D(width, height))]),
        pRasterizationState=vk.VkPipelineRasterizationStateCreateInfo(
            sType=_s('PIPELINE_RASTERIZATION_STATE_CREATE_INFO'),
            polygonMode=vk.VK_POLYGON_MODE_FILL, cullMode=vk.VK_CULL_MODE_NONE,
            frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE, lineWidth=1.0),
        pMultisampleState=vk.VkPipelineMultisampleStateCreateInfo(
            sType=_s('PIPELINE_MULTISAMPLE_STATE_CREATE_INFO'),
            rasterizationSamples=vk.VK_SAMPLE_COUNT_1_BIT),
        pColorBlendState=vk.VkPipelineColorBlendStateCreateInfo(
            sType=_s('PIPELINE_COLOR_BLEND_STATE_CREATE_INFO'),
            attachmentCount=1, pAttachments=[blend]),
        layout=layout, renderPass=render_pass, subpass=0)
    return vk.vkCreateGraphicsPipelines(
        ctx.device, vk.VK_NULL_HANDLE, 1, [ci], None)[0]


class ShapePipeline:
    """Renders solid-colour shapes into ``target`` (an ``OffscreenColorTarget``).

    Push constants carry the ``view``/``projection`` matrices (vertex stage,
    offset 0) and the shape colour (fragment stage, offset 128), matching
    ``glsl/shape.{vert,frag}``.  Alpha blending is enabled.
    """

    def __init__(self, ctx, target):
        self.ctx = ctx
        self.target = target
        self.width, self.height = target.width, target.height
        self._pipelines = {}      # topology -> VkPipeline
        self._scratch = []        # per-frame vertex buffers, freed by caller

        # render pass: clear at begin, leave the image ready for readback
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

        self.vmod = ctx.create_shader_module(shaders.load_spv('shape.vert'))
        self.fmod = ctx.create_shader_module(shaders.load_spv('shape.frag'))
        self.layout = vk.vkCreatePipelineLayout(
            ctx.device, vk.VkPipelineLayoutCreateInfo(
                sType=_s('PIPELINE_LAYOUT_CREATE_INFO'),
                pushConstantRangeCount=2, pPushConstantRanges=[
                    vk.VkPushConstantRange(
                        stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
                        offset=0, size=128),
                    vk.VkPushConstantRange(
                        stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
                        offset=128, size=16)]), None)

    def _pipeline_for(self, topology):
        pipe = self._pipelines.get(topology)
        if pipe is not None:
            return pipe
        ctx = self.ctx
        stages = [
            vk.VkPipelineShaderStageCreateInfo(
                sType=_s('PIPELINE_SHADER_STAGE_CREATE_INFO'),
                stage=vk.VK_SHADER_STAGE_VERTEX_BIT, module=self.vmod,
                pName="main"),
            vk.VkPipelineShaderStageCreateInfo(
                sType=_s('PIPELINE_SHADER_STAGE_CREATE_INFO'),
                stage=vk.VK_SHADER_STAGE_FRAGMENT_BIT, module=self.fmod,
                pName="main")]
        vin = vk.VkPipelineVertexInputStateCreateInfo(
            sType=_s('PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO'),
            vertexBindingDescriptionCount=1, pVertexBindingDescriptions=[
                vk.VkVertexInputBindingDescription(
                    binding=0, stride=12,
                    inputRate=vk.VK_VERTEX_INPUT_RATE_VERTEX)],
            vertexAttributeDescriptionCount=1, pVertexAttributeDescriptions=[
                vk.VkVertexInputAttributeDescription(
                    location=0, binding=0,
                    format=vk.VK_FORMAT_R32G32B32_SFLOAT, offset=0)])
        blend = vk.VkPipelineColorBlendAttachmentState(
            colorWriteMask=0xF, blendEnable=vk.VK_TRUE,
            srcColorBlendFactor=vk.VK_BLEND_FACTOR_SRC_ALPHA,
            dstColorBlendFactor=vk.VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA,
            colorBlendOp=vk.VK_BLEND_OP_ADD,
            srcAlphaBlendFactor=vk.VK_BLEND_FACTOR_ONE,
            dstAlphaBlendFactor=vk.VK_BLEND_FACTOR_ZERO,
            alphaBlendOp=vk.VK_BLEND_OP_ADD)
        ci = vk.VkGraphicsPipelineCreateInfo(
            sType=_s('GRAPHICS_PIPELINE_CREATE_INFO'), stageCount=2,
            pStages=stages, pVertexInputState=vin,
            pInputAssemblyState=vk.VkPipelineInputAssemblyStateCreateInfo(
                sType=_s('PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO'),
                topology=topology),
            pViewportState=vk.VkPipelineViewportStateCreateInfo(
                sType=_s('PIPELINE_VIEWPORT_STATE_CREATE_INFO'),
                viewportCount=1, pViewports=[
                    vk.VkViewport(0, 0, self.width, self.height, 0, 1)],
                scissorCount=1, pScissors=[vk.VkRect2D(
                    offset=vk.VkOffset2D(0, 0),
                    extent=vk.VkExtent2D(self.width, self.height))]),
            pRasterizationState=vk.VkPipelineRasterizationStateCreateInfo(
                sType=_s('PIPELINE_RASTERIZATION_STATE_CREATE_INFO'),
                polygonMode=vk.VK_POLYGON_MODE_FILL,
                cullMode=vk.VK_CULL_MODE_NONE,
                frontFace=vk.VK_FRONT_FACE_COUNTER_CLOCKWISE, lineWidth=1.0),
            pMultisampleState=vk.VkPipelineMultisampleStateCreateInfo(
                sType=_s('PIPELINE_MULTISAMPLE_STATE_CREATE_INFO'),
                rasterizationSamples=vk.VK_SAMPLE_COUNT_1_BIT),
            pColorBlendState=vk.VkPipelineColorBlendStateCreateInfo(
                sType=_s('PIPELINE_COLOR_BLEND_STATE_CREATE_INFO'),
                attachmentCount=1, pAttachments=[blend]),
            layout=self.layout, renderPass=self.render_pass, subpass=0)
        pipe = vk.vkCreateGraphicsPipelines(
            ctx.device, vk.VK_NULL_HANDLE, 1, [ci], None)[0]
        self._pipelines[topology] = pipe
        return pipe

    def record(self, cmd, shapes, mats_bytes):
        """Record shape draws into an active (caller-managed) render pass.

        ``shapes`` is a list of ``(topology, vertices, rgba)``; ``vertices`` is
        ``(N, 2)`` or ``(N, 3)`` in the shaders' input space.  Scratch vertex
        buffers accumulate until :meth:`free_scratch`.
        """
        vk.vkCmdPushConstants(
            cmd, self.layout, vk.VK_SHADER_STAGE_VERTEX_BIT, 0, 128,
            vk.ffi.cast('void*', vk.ffi.from_buffer(mats_bytes)))
        for topology, verts, rgba in shapes:
            v = _verts3(verts)
            if len(v) == 0:
                continue
            vbuf, vmem = self.ctx.create_buffer(
                v.nbytes, vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
                vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
            self.ctx.upload(vmem, v)
            self._scratch.append((vbuf, vmem))
            color = np.ascontiguousarray(rgba, np.float32).tobytes()
            vk.vkCmdBindPipeline(cmd, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                                 self._pipeline_for(topology))
            vk.vkCmdBindVertexBuffers(cmd, 0, 1, [vbuf], [0])
            vk.vkCmdPushConstants(
                cmd, self.layout, vk.VK_SHADER_STAGE_FRAGMENT_BIT, 128, 16,
                vk.ffi.cast('void*', vk.ffi.from_buffer(color)))
            vk.vkCmdDraw(cmd, len(v), 1, 0, 0)

    def free_scratch(self):
        for vbuf, vmem in self._scratch:
            vk.vkDestroyBuffer(self.ctx.device, vbuf, None)
            vk.vkFreeMemory(self.ctx.device, vmem, None)
        self._scratch = []

    def render(self, shapes, clear_color=(0.0, 0.0, 0.0, 1.0),
               view=None, projection=None):
        """Self-contained render into the target (own render pass + submit).

        Used standalone/in tests; the renderer composites via :meth:`record`
        in a shared render pass.
        """
        ctx = self.ctx
        cmd = ctx.begin_commands()
        vk.vkCmdBeginRenderPass(cmd, vk.VkRenderPassBeginInfo(
            sType=_s('RENDER_PASS_BEGIN_INFO'), renderPass=self.render_pass,
            framebuffer=self.framebuffer, renderArea=vk.VkRect2D(
                offset=vk.VkOffset2D(0, 0),
                extent=vk.VkExtent2D(self.width, self.height)),
            clearValueCount=1, pClearValues=[vk.VkClearValue(
                color=vk.VkClearColorValue(float32=list(clear_color)))]),
            vk.VK_SUBPASS_CONTENTS_INLINE)
        self.record(cmd, shapes, _mats(view, projection))
        vk.vkCmdEndRenderPass(cmd)
        ctx.submit_wait(cmd)
        self.target.layout = vk.VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL
        self.free_scratch()

    def destroy(self):
        d = self.ctx.device
        for pipe in self._pipelines.values():
            vk.vkDestroyPipeline(d, pipe, None)
        self._pipelines.clear()
        vk.vkDestroyPipelineLayout(d, self.layout, None)
        vk.vkDestroyShaderModule(d, self.vmod, None)
        vk.vkDestroyShaderModule(d, self.fmod, None)
        vk.vkDestroyFramebuffer(d, self.framebuffer, None)
        vk.vkDestroyRenderPass(d, self.render_pass, None)


class GlyphPipeline:
    """Blits many pre-colored RGBA tiles (e.g. rasterized text) in a single
    render pass, each with its own texture + descriptor set allocated per
    draw (an arbitrary number of tiles per frame); the descriptor pool is
    reset and the scratch textures freed by :meth:`free_scratch`.

    Uses ``image.vert`` + ``blit.frag`` (RGBA sampler, alpha blended), a
    linear sampler for smooth text, and the shared view/projection push
    constants.
    """

    def __init__(self, ctx, target, max_tiles=256):
        self.ctx = ctx
        self.target = target
        self.width, self.height = target.width, target.height
        self.max_tiles = max_tiles
        self._scratch_tex = []      # (image, mem, view) per tile
        self._scratch_buf = []      # (buffer, mem) vertex buffers
        self._nsets = 0

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

        self.sampler = ctx.create_sampler(vk.VK_FILTER_LINEAR)
        self.dsl = vk.vkCreateDescriptorSetLayout(
            ctx.device, vk.VkDescriptorSetLayoutCreateInfo(
                sType=_s('DESCRIPTOR_SET_LAYOUT_CREATE_INFO'), bindingCount=1,
                pBindings=[vk.VkDescriptorSetLayoutBinding(
                    binding=0, descriptorCount=1,
                    stageFlags=vk.VK_SHADER_STAGE_FRAGMENT_BIT,
                    descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER
                )]), None)
        self.pool = vk.vkCreateDescriptorPool(
            ctx.device, vk.VkDescriptorPoolCreateInfo(
                sType=_s('DESCRIPTOR_POOL_CREATE_INFO'), maxSets=max_tiles,
                poolSizeCount=1, pPoolSizes=[vk.VkDescriptorPoolSize(
                    type=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                    descriptorCount=max_tiles)]), None)
        self.layout = vk.vkCreatePipelineLayout(
            ctx.device, vk.VkPipelineLayoutCreateInfo(
                sType=_s('PIPELINE_LAYOUT_CREATE_INFO'), setLayoutCount=1,
                pSetLayouts=[self.dsl], pushConstantRangeCount=1,
                pPushConstantRanges=[vk.VkPushConstantRange(
                    stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT, offset=0,
                    size=128)]), None)
        self.vmod = ctx.create_shader_module(shaders.load_spv('image.vert'))
        self.fmod = ctx.create_shader_module(shaders.load_spv('blit.frag'))
        self.pipeline = _textured_quad_pipeline(
            ctx, self.vmod, self.fmod, self.layout, self.render_pass,
            self.width, self.height)

    def record(self, cmd, rgba2d, quad_pos, quad_uv, mats_bytes):
        """Record one RGBA tile draw into an active render pass.  Allocates a
        scratch texture + descriptor set (freed/reset by :meth:`free_scratch`).
        """
        if self._nsets >= self.max_tiles:
            return          # frame exceeded tile budget; drop extras
        ctx = self.ctx
        arr = np.ascontiguousarray(rgba2d, dtype=np.uint8)
        h, w = arr.shape[:2]
        img, mem, view = ctx.create_texture_2d(
            w, h, vk.VK_FORMAT_R8G8B8A8_UNORM, arr)
        self._scratch_tex.append((img, mem, view))
        dset = vk.vkAllocateDescriptorSets(
            ctx.device, vk.VkDescriptorSetAllocateInfo(
                sType=_s('DESCRIPTOR_SET_ALLOCATE_INFO'), descriptorPool=self.pool,
                descriptorSetCount=1, pSetLayouts=[self.dsl]))[0]
        self._nsets += 1
        vk.vkUpdateDescriptorSets(ctx.device, 1, [vk.VkWriteDescriptorSet(
            sType=_s('WRITE_DESCRIPTOR_SET'), dstSet=dset, dstBinding=0,
            descriptorCount=1,
            descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            pImageInfo=[vk.VkDescriptorImageInfo(
                sampler=self.sampler, imageView=view,
                imageLayout=vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL)])],
            0, None)
        pos = np.ascontiguousarray(quad_pos, np.float32).reshape(-1, 2)
        uv = np.ascontiguousarray(quad_uv, np.float32).reshape(-1, 2)
        verts = np.ascontiguousarray(np.hstack([pos, uv]), np.float32)
        vbuf, vmem = ctx.create_buffer(
            verts.nbytes, vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        ctx.upload(vmem, verts)
        self._scratch_buf.append((vbuf, vmem))
        vk.vkCmdBindPipeline(cmd, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                             self.pipeline)
        vk.vkCmdBindDescriptorSets(
            cmd, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.layout, 0, 1,
            [dset], 0, None)
        vk.vkCmdPushConstants(
            cmd, self.layout, vk.VK_SHADER_STAGE_VERTEX_BIT, 0, 128,
            vk.ffi.cast('void*', vk.ffi.from_buffer(mats_bytes)))
        vk.vkCmdBindVertexBuffers(cmd, 0, 1, [vbuf], [0])
        vk.vkCmdDraw(cmd, len(verts), 1, 0, 0)

    def free_scratch(self):
        d = self.ctx.device
        for img, mem, view in self._scratch_tex:
            vk.vkDestroyImageView(d, view, None)
            vk.vkDestroyImage(d, img, None)
            vk.vkFreeMemory(d, mem, None)
        for vbuf, vmem in self._scratch_buf:
            vk.vkDestroyBuffer(d, vbuf, None)
            vk.vkFreeMemory(d, vmem, None)
        self._scratch_tex = []
        self._scratch_buf = []
        if self._nsets > 0:
            vk.vkResetDescriptorPool(d, self.pool, 0)
            self._nsets = 0

    def destroy(self):
        d = self.ctx.device
        self.free_scratch()
        vk.vkDestroyPipeline(d, self.pipeline, None)
        vk.vkDestroyShaderModule(d, self.vmod, None)
        vk.vkDestroyShaderModule(d, self.fmod, None)
        vk.vkDestroyPipelineLayout(d, self.layout, None)
        vk.vkDestroyDescriptorPool(d, self.pool, None)
        vk.vkDestroyDescriptorSetLayout(d, self.dsl, None)
        vk.vkDestroySampler(d, self.sampler, None)
        vk.vkDestroyFramebuffer(d, self.framebuffer, None)
        vk.vkDestroyRenderPass(d, self.render_pass, None)


class MultiImagePipeline:
    """Draws any number of images per frame, each with its own persistent
    texture + descriptor set (cached by ``image_id`` and re-uploaded only when
    the image data changes -- like the OpenGL renderer's texture cache, so
    zoom/pan don't re-upload).  Handles both monochrome images (cut levels +
    colormap on the GPU) and native RGB[A] images, selected per draw by the
    ``image_type`` push constant (``image2.frag``).

    Descriptor set 0: binding 0 image sampler (R32F mono or RGBA8 native),
    binding 1 the shared colormap texel buffer.  Push constants: view/proj
    (vertex, 0..128, ``image.vert``) + loval/hival/image_type (fragment, 128).
    """

    def __init__(self, ctx, target, max_images=64):
        self.ctx = ctx
        self.target = target
        self.width, self.height = target.width, target.height
        self.max_images = max_images
        self._images = {}     # image_id -> dict(image, mem, view, dset, cmap_gen)
        self._cmap = None     # (buffer, mem, view)
        self._cmap_gen = 0
        self._scratch = []    # per-frame vertex buffers

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

        self.sampler = ctx.create_sampler(vk.VK_FILTER_NEAREST)
        frag = vk.VK_SHADER_STAGE_FRAGMENT_BIT
        self.dsl = vk.vkCreateDescriptorSetLayout(
            ctx.device, vk.VkDescriptorSetLayoutCreateInfo(
                sType=_s('DESCRIPTOR_SET_LAYOUT_CREATE_INFO'), bindingCount=2,
                pBindings=[
                    vk.VkDescriptorSetLayoutBinding(
                        binding=0, descriptorCount=1, stageFlags=frag,
                        descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER),
                    vk.VkDescriptorSetLayoutBinding(
                        binding=1, descriptorCount=1, stageFlags=frag,
                        descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER)]),
            None)
        self.pool = vk.vkCreateDescriptorPool(
            ctx.device, vk.VkDescriptorPoolCreateInfo(
                sType=_s('DESCRIPTOR_POOL_CREATE_INFO'), maxSets=max_images,
                poolSizeCount=2, pPoolSizes=[
                    vk.VkDescriptorPoolSize(
                        type=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                        descriptorCount=max_images),
                    vk.VkDescriptorPoolSize(
                        type=vk.VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER,
                        descriptorCount=max_images)]), None)
        self.layout = vk.vkCreatePipelineLayout(
            ctx.device, vk.VkPipelineLayoutCreateInfo(
                sType=_s('PIPELINE_LAYOUT_CREATE_INFO'), setLayoutCount=1,
                pSetLayouts=[self.dsl], pushConstantRangeCount=2,
                pPushConstantRanges=[
                    vk.VkPushConstantRange(
                        stageFlags=vk.VK_SHADER_STAGE_VERTEX_BIT,
                        offset=0, size=128),
                    vk.VkPushConstantRange(
                        stageFlags=frag, offset=128, size=16)]), None)
        self.vmod = ctx.create_shader_module(shaders.load_spv('image.vert'))
        self.fmod = ctx.create_shader_module(shaders.load_spv('image2.frag'))
        self.pipeline = _textured_quad_pipeline(
            ctx, self.vmod, self.fmod, self.layout, self.render_pass,
            self.width, self.height)

    def set_colormap(self, rgba_u8):
        """Set the shared colormap (``(N, 4)`` uint8).  Existing per-image
        descriptor sets rebind it lazily on their next :meth:`record`."""
        cm = np.ascontiguousarray(rgba_u8, dtype=np.uint8)
        if self._cmap is not None:
            self._destroy_cmap()
        buf, mem = self.ctx.create_buffer(
            cm.nbytes, vk.VK_BUFFER_USAGE_UNIFORM_TEXEL_BUFFER_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        self.ctx.upload(mem, cm)
        view = self.ctx.create_buffer_view(buf, vk.VK_FORMAT_R8G8B8A8_UINT,
                                           cm.nbytes)
        self._cmap = (buf, mem, view)
        self._cmap_gen += 1

    def has_image(self, image_id):
        return image_id in self._images

    def upload_image(self, image_id, data, image_type):
        """(Re)create the texture for ``image_id``.  ``data`` is a 2D float32
        array (image_type 0, mono), an ``(H, W, 4)`` uint8 array (1, native
        RGBA) or an ``(H, W, 4)`` float32 array (2, RGB normimage -- raw
        values, cut/colormapped per channel in the shader)."""
        ctx = self.ctx
        if image_type == 1:
            arr = np.ascontiguousarray(data, dtype=np.uint8)
            fmt = vk.VK_FORMAT_R8G8B8A8_UNORM
        elif image_type == 2:
            arr = np.ascontiguousarray(data, dtype=np.float32)
            fmt = vk.VK_FORMAT_R32G32B32A32_SFLOAT
        else:
            arr = np.ascontiguousarray(data, dtype=np.float32)
            fmt = vk.VK_FORMAT_R32_SFLOAT
        h, w = arr.shape[:2]
        img, mem, view = ctx.create_texture_2d(w, h, fmt, arr)
        ent = self._images.get(image_id)
        if ent is None:
            if len(self._images) >= self.max_images:
                # out of descriptor sets; drop the texture and skip
                vk.vkDestroyImageView(ctx.device, view, None)
                vk.vkDestroyImage(ctx.device, img, None)
                vk.vkFreeMemory(ctx.device, mem, None)
                return
            dset = vk.vkAllocateDescriptorSets(
                ctx.device, vk.VkDescriptorSetAllocateInfo(
                    sType=_s('DESCRIPTOR_SET_ALLOCATE_INFO'),
                    descriptorPool=self.pool, descriptorSetCount=1,
                    pSetLayouts=[self.dsl]))[0]
            ent = dict(dset=dset, image=None, mem=None, view=None, cmap_gen=-1)
            self._images[image_id] = ent
        else:
            self._destroy_tex(ent)
        ent['image'], ent['mem'], ent['view'] = img, mem, view
        vk.vkUpdateDescriptorSets(ctx.device, 1, [vk.VkWriteDescriptorSet(
            sType=_s('WRITE_DESCRIPTOR_SET'), dstSet=ent['dset'], dstBinding=0,
            descriptorCount=1,
            descriptorType=vk.VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            pImageInfo=[vk.VkDescriptorImageInfo(
                sampler=self.sampler, imageView=view,
                imageLayout=vk.VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL)])],
            0, None)

    def record(self, cmd, image_id, quad_pos, quad_uv, loval, hival,
               image_type, obj_alpha, mats_bytes):
        """Record one image draw (image must have been uploaded)."""
        ent = self._images.get(image_id)
        if ent is None:
            return
        ctx = self.ctx
        # (re)bind the shared colormap into this set if it changed
        if ent['cmap_gen'] != self._cmap_gen and self._cmap is not None:
            vk.vkUpdateDescriptorSets(ctx.device, 1, [vk.VkWriteDescriptorSet(
                sType=_s('WRITE_DESCRIPTOR_SET'), dstSet=ent['dset'],
                dstBinding=1, descriptorCount=1,
                descriptorType=vk.VK_DESCRIPTOR_TYPE_UNIFORM_TEXEL_BUFFER,
                pTexelBufferView=[self._cmap[2]])], 0, None)
            ent['cmap_gen'] = self._cmap_gen

        pos = np.ascontiguousarray(quad_pos, np.float32).reshape(-1, 2)
        uv = np.ascontiguousarray(quad_uv, np.float32).reshape(-1, 2)
        verts = np.ascontiguousarray(np.hstack([pos, uv]), np.float32)
        vbuf, vmem = ctx.create_buffer(
            verts.nbytes, vk.VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            vk.VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
            vk.VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)
        ctx.upload(vmem, verts)
        self._scratch.append((vbuf, vmem))
        params = (np.array([loval, hival], np.float32).tobytes() +
                  np.array([int(image_type)], np.int32).tobytes() +
                  np.array([obj_alpha], np.float32).tobytes())
        vk.vkCmdBindPipeline(cmd, vk.VK_PIPELINE_BIND_POINT_GRAPHICS,
                             self.pipeline)
        vk.vkCmdBindDescriptorSets(
            cmd, vk.VK_PIPELINE_BIND_POINT_GRAPHICS, self.layout, 0, 1,
            [ent['dset']], 0, None)
        vk.vkCmdPushConstants(
            cmd, self.layout, vk.VK_SHADER_STAGE_VERTEX_BIT, 0, 128,
            vk.ffi.cast('void*', vk.ffi.from_buffer(mats_bytes)))
        vk.vkCmdPushConstants(
            cmd, self.layout, vk.VK_SHADER_STAGE_FRAGMENT_BIT, 128, 16,
            vk.ffi.cast('void*', vk.ffi.from_buffer(params)))
        vk.vkCmdBindVertexBuffers(cmd, 0, 1, [vbuf], [0])
        vk.vkCmdDraw(cmd, len(verts), 1, 0, 0)

    def free_scratch(self):
        for vbuf, vmem in self._scratch:
            vk.vkDestroyBuffer(self.ctx.device, vbuf, None)
            vk.vkFreeMemory(self.ctx.device, vmem, None)
        self._scratch = []

    def _destroy_tex(self, ent):
        d = self.ctx.device
        if ent['view'] is not None:
            vk.vkDestroyImageView(d, ent['view'], None)
            vk.vkDestroyImage(d, ent['image'], None)
            vk.vkFreeMemory(d, ent['mem'], None)
            ent['image'] = ent['mem'] = ent['view'] = None

    def _destroy_cmap(self):
        buf, mem, view = self._cmap
        vk.vkDestroyBufferView(self.ctx.device, view, None)
        vk.vkDestroyBuffer(self.ctx.device, buf, None)
        vk.vkFreeMemory(self.ctx.device, mem, None)
        self._cmap = None

    def destroy(self):
        d = self.ctx.device
        self.free_scratch()
        for ent in self._images.values():
            self._destroy_tex(ent)
        self._images = {}
        if self._cmap is not None:
            self._destroy_cmap()
        vk.vkDestroyPipeline(d, self.pipeline, None)
        vk.vkDestroyShaderModule(d, self.vmod, None)
        vk.vkDestroyShaderModule(d, self.fmod, None)
        vk.vkDestroyPipelineLayout(d, self.layout, None)
        vk.vkDestroyDescriptorPool(d, self.pool, None)
        vk.vkDestroyDescriptorSetLayout(d, self.dsl, None)
        vk.vkDestroySampler(d, self.sampler, None)
        vk.vkDestroyFramebuffer(d, self.framebuffer, None)
        vk.vkDestroyRenderPass(d, self.render_pass, None)
