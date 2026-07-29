#version 450
/*
 * blit.frag -- sample a pre-colored RGBA image texture and output it.
 * Used by GlyphPipeline to composite rasterized text tiles (GPU
 * colormap-from-raw for images is MultiImagePipeline/image2.frag).
 */
layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D tex;

void main()
{
    outColor = texture(tex, v_uv);
}
