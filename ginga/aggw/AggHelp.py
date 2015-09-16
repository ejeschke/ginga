#
# AggHelp.py -- help classes for the Agg drawing
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import os.path

import aggdraw as agg

from ginga import colors
import ginga.fonts

# Set up known fonts
fontdir, xx = os.path.split(ginga.fonts.__file__)
known_font = os.path.join(fontdir, 'Roboto', 'Roboto-Regular.ttf')

class AggContext(object):

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def get_color(self, color):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (int(r*255), int(g*255), int(b*255))

    def get_pen(self, color, linewidth=1, alpha=1.0):
        # if hasattr(self, 'linestyle'):
        #     if self.linestyle == 'dash':
        #         cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
        op = int(alpha * 255)

        p = agg.Pen(self.get_color(color), width=linewidth,
                    opacity=op)
        return p

    def get_brush(self, color, alpha=1.0):
        op = int(alpha * 255)
        b = agg.Brush(self.get_color(color), opacity=op)
        return b

    def get_font(self, name, size, color, alpha=1.0):
        color = self.get_color(color)
        op = int(alpha * 255)

        # TODO: try to lookup font before overriding
        filepath = known_font

        f = agg.Font(color, filepath, size=size, opacity=op)
        return f

    def text_extents(self, text, font):
        wd, ht = self.canvas.textsize(text, font)
        return wd, ht

#END
