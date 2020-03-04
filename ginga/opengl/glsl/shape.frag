#version 330 core

out vec4 outputColor;

uniform vec4 fg_clr;

void main()
{
    // pass thru
    outputColor = fg_clr;

}
