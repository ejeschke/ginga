#version 330 core
/*
 * shape.vert -- vertex shader for Ginga shapes
 *
 * This is open-source software licensed under a BSD license.
 * Please see the file LICENSE.txt for details.
 *
 */
layout (location = 0) in vec3 position;

// uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main()
{
    // note that we read the multiplication from right to left
    // gl_Position = projection * view * model * vec4(aPos, 1.0);
    gl_Position = projection * view * vec4(position, 1.0);

}
