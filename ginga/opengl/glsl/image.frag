#version 330 core

out vec4 outputColor;

in vec2 o_tex_coord;

uniform sampler2D img_texture;

void main()
{
    outputColor = texture(img_texture, o_tex_coord);
}
