#version 450
/*
 * shape.frag -- fragment shader for Ginga shapes (Vulkan port of
 * ginga/opengl/glsl/shape.frag).  The GL `fg_clr` uniform becomes a
 * push-constant at offset 128 (after the vertex stage's two mat4s).
 */
layout(location = 0) out vec4 outColor;

layout(push_constant) uniform PushConstants {
    layout(offset = 128) vec4 fg_clr;
} pc;

void main()
{
    outColor = pc.fg_clr;
}
