#version 330 core
layout (location = 0) in vec3 position;
layout (location = 1) in vec2 i_tex_coord;

out vec2 o_tex_coord;

// uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main()
{
    // note that we read the multiplication from right to left
    // gl_Position = projection * view * model * vec4(aPos, 1.0);
    gl_Position = projection * view * vec4(position, 1.0);

    o_tex_coord = i_tex_coord;
}
