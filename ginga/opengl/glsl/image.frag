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
uniform sampler1D color_map;

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
        // RGBA traditional image
        color = texture(img_texture, o_tex_coord);
    }
    else {
        // monochrome image to be colored
        // get source value, passed in single red channel
        float value = texture(img_texture, o_tex_coord).r;

        // cut levels
        int idx = int(cut_levels(value));

        // apply RGB mapping
        color = texelFetch(color_map, idx, 0);
    }
    outputColor = color;
}
