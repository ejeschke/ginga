#version 330 core
/*
 * image.frag -- fragment shader for Ginga images
 *
 * This is open-source software licensed under a BSD license.
 * Please see the file LICENSE.txt for details.
 *
 */
out vec4 outputColor;

in vec2 o_tex_coord;

uniform sampler2D img_texture;
uniform usamplerBuffer color_map;

// for cut levels
uniform float loval;
uniform float hival;

uniform int image_type;

float cut_levels(float value)
{
    float f, delta, _hival;
    const float vmin = 0.0;
    const float vmax = 255.0;

    // ensure hival >= loval
    _hival = max(loval, hival);
    delta = _hival - loval;
    if (delta > 0.0) {
        f = ((value - loval) / delta) * vmax;
        f = clamp(f, 0.0, vmax);
        return f;
    }

    // hival == loval, so thresholding operation
    f = clamp(value - loval, 0.0, vmax);
    if (f > 0.0) { f = vmax; }
    return f;
}

void main()
{
    vec4 color;
    
    if (image_type == 0) {
        // RGBA traditional image, no interactive RGB map
        color = texture(img_texture, o_tex_coord);
    }
    else if (image_type == 1) {
        // color image to be colored
        vec4 value = texture(img_texture, o_tex_coord);

        // cut levels
        // RGBA textures are normalized to 0..1 when unpacked
        int idx_r = int(cut_levels(value.r * 256.0));
        int idx_g = int(cut_levels(value.g * 256.0));
        int idx_b = int(cut_levels(value.b * 256.0));
        
        // apply RGB mapping
        float r = texelFetch(color_map, idx_r).r / 255.0;
        float g = texelFetch(color_map, idx_g).g / 255.0;
        float b = texelFetch(color_map, idx_b).b / 255.0;
        color = vec4(r, g, b, value.a);
    }
    else if (image_type == 2) {
        // monochrome image to be colored
        // get source value, passed in single red channel
        float value = texture(img_texture, o_tex_coord).r;

        // cut levels
        int idx = int(cut_levels(value));
        
        // apply RGB mapping
        uvec4 clr = texelFetch(color_map, idx);
        color = vec4(clr.r / 255.0, clr.g / 255.0, clr.b / 255.0,
                     clr.a / 255.0);
    }
    outputColor = color;
}
