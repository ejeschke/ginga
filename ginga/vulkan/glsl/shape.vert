#version 450
/*
 * shape.vert -- vertex shader for Ginga shapes (Vulkan port of
 * ginga/opengl/glsl/shape.vert).  The GL global `view`/`projection` uniforms
 * become a push-constant block (offset 0..127); the fragment stage's color
 * lives at offset 128 (see shape.frag).
 */
layout(location = 0) in vec3 position;

layout(push_constant) uniform PushConstants {
    mat4 view;
    mat4 projection;
} pc;

void main()
{
    gl_Position = pc.projection * pc.view * vec4(position, 1.0);
}
