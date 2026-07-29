#version 450
/*
 * image.vert -- vertex shader for Ginga images (Vulkan).  A textured quad:
 * clip-space position (via view/projection push constants, shared layout
 * with shape.vert) plus a passthrough texture coordinate.
 */
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 texcoord;

layout(push_constant) uniform PushConstants {
    mat4 view;
    mat4 projection;
} pc;

layout(location = 0) out vec2 v_uv;

void main()
{
    gl_Position = pc.projection * pc.view * vec4(position, 0.0, 1.0);
    v_uv = texcoord;
}
