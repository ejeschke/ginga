#
# ginga.vulkan -- Vulkan renderer for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Vulkan renderer for Ginga.

A toolkit-agnostic, GPU-native Vulkan renderer that mirrors the OpenGL
renderer (``ginga.opengl``): an offscreen ``VkImage`` core that any backend
can consume via the CPU-array path.  See ``CanvasRenderVk.CanvasRendererGPU``.
"""
