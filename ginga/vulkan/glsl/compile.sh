#!/bin/bash
# Regenerate the shipped SPIR-V (.spv) from the GLSL sources.
# Requires glslangValidator (e.g. the conda 'glslang' package).
set -e
cd "$(dirname "$0")"
for s in *.vert *.frag; do
    [ -e "$s" ] || continue
    glslangValidator -V "$s" -o "$s.spv"
    echo "  $s -> $s.spv"
done
