#
# shaders.py -- SPIR-V shader loading for the Ginga Vulkan renderer
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Load the shipped, pre-compiled SPIR-V shaders.

The ``.spv`` files under ``glsl/`` are built from the GLSL sources by
``glsl/compile.sh`` (needs ``glslangValidator``); shipping them means the
renderer has no runtime shader-compiler dependency.
"""
import os.path

glsl_dir = os.path.join(os.path.dirname(__file__), 'glsl')


def load_spv(name):
    """Return the SPIR-V ``bytes`` for shader ``name`` (e.g. ``'shape.vert'``)."""
    with open(os.path.join(glsl_dir, name + '.spv'), 'rb') as in_f:
        return in_f.read()
