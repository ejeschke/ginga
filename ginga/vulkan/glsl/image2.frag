#version 450
/*
 * image2.frag -- fragment shader for the Style-2 multi-image pipeline.
 * The low nibble of image_type selects the mode:
 *   0 = monochrome normimage: cut levels + colormap (pseudocolor)
 *   1 = native RGB[A] image (kind 'image'): sampled directly, no RGB map
 *   2 = RGB[A] normimage: per-channel cut levels + colormap (like the GL
 *       renderer's image_type 0x1|0x4), so cut levels / distribution / rgbmap
 *       stay interactive
 * Bits 4-5 (image_type >> 4) select the display interpolation:
 *   0 = nearest, 1 = bilinear, 2 = bicubic (Catmull-Rom), 3 = Lanczos-3.
 * All are done in-shader (a NEAREST sampler is used -- float textures cannot
 * rely on hardware linear filtering), gathering the source texels manually.
 *
 * The image is a single sampler2D (R32_SFLOAT mono, R8G8B8A8_UNORM native, or
 * R32G32B32A32_SFLOAT RGB normimage) plus a per-image colormap texel buffer.
 * The output alpha is the image's per-pixel alpha times the object alpha.
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

const float PI = 3.14159265358979;

float cut_levels(float value, float vmax)
{
    float hi = max(prm.loval, prm.hival);
    float delta = hi - prm.loval;
    if (delta > 0.0) {
        return clamp((value - prm.loval) / delta * vmax, 0.0, vmax);
    }
    return (value - prm.loval > 0.0) ? vmax : 0.0;
}

// Catmull-Rom cubic weight (interpolating, sharp)
float w_cubic(float x)
{
    x = abs(x);
    if (x < 1.0) return 1.5 * x * x * x - 2.5 * x * x + 1.0;
    if (x < 2.0) return -0.5 * x * x * x + 2.5 * x * x - 4.0 * x + 2.0;
    return 0.0;
}

// Lanczos-3 windowed-sinc weight
float w_lanczos(float x)
{
    if (x == 0.0) return 1.0;
    if (abs(x) >= 3.0) return 0.0;
    float px = PI * x;
    return (3.0 * sin(px) * sin(px / 3.0)) / (px * px);
}

vec4 bilinear(vec2 uv)
{
    vec2 sz = vec2(textureSize(img_texture, 0));
    vec2 duv = 1.0 / sz;
    vec2 t = uv * sz - 0.5;
    vec2 f = fract(t);
    vec2 uv0 = (floor(t) + 0.5) * duv;
    vec4 c00 = texture(img_texture, uv0);
    vec4 c10 = texture(img_texture, uv0 + vec2(duv.x, 0.0));
    vec4 c01 = texture(img_texture, uv0 + vec2(0.0, duv.y));
    vec4 c11 = texture(img_texture, uv0 + duv);
    return mix(mix(c00, c10, f.x), mix(c01, c11, f.x), f.y);
}

vec4 bicubic(vec2 uv)
{
    vec2 sz = vec2(textureSize(img_texture, 0));
    vec2 duv = 1.0 / sz;
    vec2 t = uv * sz - 0.5;
    vec2 base = floor(t);
    vec2 f = t - base;
    vec4 sum = vec4(0.0);
    float wsum = 0.0;
    for (int j = -1; j <= 2; ++j) {
        float wy = w_cubic(float(j) - f.y);
        for (int i = -1; i <= 2; ++i) {
            float w = w_cubic(float(i) - f.x) * wy;
            vec2 suv = (base + vec2(float(i), float(j)) + 0.5) * duv;
            sum += texture(img_texture, suv) * w;
            wsum += w;
        }
    }
    return sum / wsum;
}

vec4 lanczos3(vec2 uv)
{
    vec2 sz = vec2(textureSize(img_texture, 0));
    vec2 duv = 1.0 / sz;
    vec2 t = uv * sz - 0.5;
    vec2 base = floor(t);
    vec2 f = t - base;
    vec4 sum = vec4(0.0);
    float wsum = 0.0;
    for (int j = -2; j <= 3; ++j) {
        float wy = w_lanczos(float(j) - f.y);
        for (int i = -2; i <= 3; ++i) {
            float w = w_lanczos(float(i) - f.x) * wy;
            vec2 suv = (base + vec2(float(i), float(j)) + 0.5) * duv;
            sum += texture(img_texture, suv) * w;
            wsum += w;
        }
    }
    return sum / wsum;
}

vec4 sample_img(vec2 uv, int interp)
{
    if (interp == 1) return bilinear(uv);
    if (interp == 2) return bicubic(uv);
    if (interp == 3) return lanczos3(uv);
    return texture(img_texture, uv);   // 0 = nearest
}

void main()
{
    int itype = prm.image_type & 0xF;
    int interp = (prm.image_type >> 4) & 0x3;
    vec4 texel = sample_img(v_uv, interp);
    float a = prm.obj_alpha;

    if (itype == 1) {
        // native RGB[A]: UNORM texture already in 0..1
        outColor = vec4(texel.rgb, texel.a * a);

    } else if (itype == 2) {
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
