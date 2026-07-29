#version 450
/*
 * image2.frag -- fragment shader for the Style-2 multi-image pipeline.
 * Selected per draw by the image_type push constant:
 *   0 = monochrome normimage: cut levels + colormap (pseudocolor)
 *   1 = native RGB[A] image (kind 'image'): sampled directly, no RGB map
 *   2 = RGB[A] normimage: per-channel cut levels + colormap (like the GL
 *       renderer's image_type 0x1|0x4), so cut levels / distribution / rgbmap
 *       stay interactive
 * The image is a single sampler2D: R32_SFLOAT (mono), R8G8B8A8_UNORM (native,
 * 0..1) or R32G32B32A32_SFLOAT (RGB normimage, raw RGB + normalized alpha).
 * The output alpha is the image's per-pixel alpha times the object alpha
 * (obj_alpha); the pipeline blends it against the target.
 */
layout(location = 0) in vec2 v_uv;
layout(location = 0) out vec4 outColor;

layout(set = 0, binding = 0) uniform sampler2D img_texture;
layout(set = 0, binding = 1) uniform usamplerBuffer color_map;

layout(push_constant) uniform Params {
    layout(offset = 128) float loval;
    float hival;
    int image_type;
    float obj_alpha;
} prm;

float cut_levels(float value, float vmax)
{
    float hi = max(prm.loval, prm.hival);
    float delta = hi - prm.loval;
    if (delta > 0.0) {
        return clamp((value - prm.loval) / delta * vmax, 0.0, vmax);
    }
    return (value - prm.loval > 0.0) ? vmax : 0.0;
}

void main()
{
    vec4 texel = texture(img_texture, v_uv);
    float a = prm.obj_alpha;

    if (prm.image_type == 1) {
        // native RGB[A]: UNORM texture already in 0..1
        outColor = vec4(texel.rgb, texel.a * a);

    } else if (prm.image_type == 2) {
        // RGB normimage: per-channel cut levels then colormap (per channel);
        // texel.a is the pre-normalized (0..1) image alpha
        int clen = textureSize(color_map);
        float imax = float(clen - 1);
        int ir = int(cut_levels(texel.r, imax));
        int ig = int(cut_levels(texel.g, imax));
        int ib = int(cut_levels(texel.b, imax));
        float r = float(texelFetch(color_map, ir).r) / 255.0;
        float g = float(texelFetch(color_map, ig).g) / 255.0;
        float b = float(texelFetch(color_map, ib).b) / 255.0;
        outColor = vec4(r, g, b, texel.a * a);

    } else {
        // monochrome: cut levels index into the (distribution-baked) colormap
        int clen = textureSize(color_map);
        float imax = float(clen - 1);
        int idx = int(cut_levels(texel.r, imax));
        uvec4 clr = texelFetch(color_map, idx);
        outColor = vec4(vec3(clr.rgb) / 255.0, a);
    }
}
