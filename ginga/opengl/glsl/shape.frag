#version 330 core
/*
 * shape.frag -- fragment shader for Ginga shapes
 *
 * This is open-source software licensed under a BSD license.
 * Please see the file LICENSE.txt for details.
 *
 */
out vec4 outputColor;

uniform vec4 fg_clr;

void main()
{
    // pass thru
    outputColor = fg_clr;

}
