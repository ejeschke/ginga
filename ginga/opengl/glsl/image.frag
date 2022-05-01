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

// image type, interpolation type
uniform int image_type;
uniform int interp;


float cut_levels(float value, float vmax)
{
    float f, delta, _hival;
    const float vmin = 0.0;

    // ensure hival >= loval
    _hival = max(loval, hival);
    delta = _hival - loval;
    if (delta > 0.0)
    {
        f = ((value - loval) / delta) * vmax;
        f = clamp(f, 0.0, vmax);
        return f;
    }

    // hival == loval, so thresholding operation
    f = clamp(value - loval, 0.0, vmax);
    if (f > 0.0) { f = vmax; }
    return f;
}

// see https://www.codeproject.com/Articles/236394/Bi-Cubic-and-Bi-Linear-Interpolation-with-GLSL

/*
 * Bicubic interpolation, using a bell-curve weighting in the kernel.
 */
float bell_func(float x)
{
    // Converting -2 to +2 to -1.5 to +1.5
    float f = ( x / 2.0 ) * 1.5;
    if (f > -1.5 && f < -0.5)
    {
        return 0.5 * pow(f + 1.5, 2.0);
    }
    else if (f > -0.5 && f < 0.5)
    {
        return 3.0 / 4.0 - ( f * f );
    }
    else if (f > 0.5 && f < 1.5)
    {
        return 0.5 * pow(f - 1.5, 2.0);
    }
    return 0.0;
}

vec4 bicubic(sampler2D tex_sampler, vec2 tex_coord)
{
    // size of one texel in X/Y
    vec2 tex_size = textureSize(tex_sampler, 0);
    vec2 inv_size = 1.0 / tex_size;
    vec4 nsum = vec4(0.0, 0.0, 0.0, 0.0);
    vec4 ndenom = vec4(0.0, 0.0, 0.0, 0.0);

    // get the decimal part
    float a = fract(tex_coord.x * tex_size.x);
    float b = fract(tex_coord.y * tex_size.y);

    for (int m = -1; m <=2; m++)
    {
        for (int n =-1; n<= 2; n++)
        {
            vec4 vecData = texture(tex_sampler,
                                   tex_coord + vec2(inv_size.x * float(m),
                                                    inv_size.y * float(n)));
            float f = bell_func(float(m) - a);
            vec4 vcoef1 = vec4(f, f, f, f);
            float f1 = bell_func(-(float(n) - b));
            vec4 vcoef2 = vec4(f1, f1, f1, f1);
            nsum = nsum + (vecData * vcoef2 * vcoef1);
            ndenom = ndenom + ((vcoef2 * vcoef1));
        }
    }
    return nsum / ndenom;
}

/*
 * Bilinear interpolation sampling the nearest four texels.
 */
vec4 bilinear(sampler2D tex_sampler, vec2 tex_coord)
{
    // size of one texel in X/Y
    vec2 tex_size = textureSize(tex_sampler, 0);
    vec2 inv_size = 1.0 / tex_size;

    vec4 p0q0 = texture(tex_sampler, tex_coord);
    vec4 p1q0 = texture(tex_sampler, tex_coord + vec2(inv_size.x, 0));

    vec4 p0q1 = texture(tex_sampler, tex_coord + vec2(0, inv_size.y));
    vec4 p1q1 = texture(tex_sampler, tex_coord + vec2(inv_size.x, inv_size.y));

    // get Interpolation factor for X direction
    float a = fract(tex_coord.x * tex_size.x);
    vec4 pInterp_q0 = mix(p0q0, p1q0, a); // interpolates top row in X
    vec4 pInterp_q1 = mix(p0q1, p1q1, a); // interpolates bottom row in X

    // get Interpolation factor for Y direction
    float b = fract(tex_coord.y * tex_size.y);
    return mix(pInterp_q0, pInterp_q1, b); // Interpolate in Y direction.
}


vec4 interpolate(sampler2D tex_sampler, vec2 tex_coord)
{
    if (interp == 1)
    {
        return bilinear(tex_sampler, tex_coord);
    }
    else if (interp == 2)
    {
        return bicubic(tex_sampler, tex_coord);
    };

    // default to nearest neighbor
    return texture(tex_sampler, tex_coord);
}

void main()
{
    vec4 color;
    int clen = textureSize(color_map);
    float vmax = clen - 1;
    
    if ((image_type & 0x1) == 0)
    {
        // RGBA traditional image, no interactive RGB map
        color = interpolate(img_texture, o_tex_coord);
    }
    else
    {   // employ interactive RGB map
        if ((image_type & 0x4) != 0)
        {   // RGB[A] image to be colored
            vec4 value = interpolate(img_texture, o_tex_coord);

            // cut levels
            // RGB[A] mapped textures are NOT normalized to 0..1
            // but sent as float
            int idx_r = int(cut_levels(value.r, vmax));
            int idx_g = int(cut_levels(value.g, vmax));
            int idx_b = int(cut_levels(value.b, vmax));
        
            // apply RGB mapping
            float r = texelFetch(color_map, idx_r).r / vmax;
            float g = texelFetch(color_map, idx_g).g / vmax;
            float b = texelFetch(color_map, idx_b).b / vmax;
            color = vec4(r, g, b, value.a);
        }
        else
        {   // monochrome image to be colored
            if ((image_type & 0x2) == 0)
            {   // no alpha channel
                // get source value, passed in single red channel
                // a float and *not normalized*
                float value = interpolate(img_texture, o_tex_coord).r;

                // cut levels
                int idx = int(cut_levels(value, vmax));

                // apply RGB mapping
                uvec4 clr = texelFetch(color_map, idx);
                color = vec4(clr.r / vmax, clr.g / vmax, clr.b / vmax,
                             clr.a / vmax);
            }
            else
            {   // get source and alpha value, passed in red and green channels
                // both floats and *not normalized*
                vec2 value = interpolate(img_texture, o_tex_coord).rg;

                // cut levels
                int idx = int(cut_levels(value.r, vmax));

                // apply RGB mapping
                uvec4 clr = texelFetch(color_map, idx);
                color = vec4(clr.r / vmax, clr.g / vmax, clr.b / vmax,
                             value.g);
            }
        }
    }
    outputColor = color;
}
