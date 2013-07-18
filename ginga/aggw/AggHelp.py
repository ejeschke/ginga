#
# AggHelp.py -- help classes for the Agg drawing
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import aggdraw as agg

from ginga import colors


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
    
    def get_pen(self, color, linewidth=1):
        # if hasattr(self, 'linestyle'):
        #     if self.linestyle == 'dash':
        #         cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
                
        p = agg.Pen(self.get_color(color), width=linewidth)
        return p
    
    def get_brush(self, color):
        p = agg.Brush(self.get_color(color))
        return p
    
    def get_font(self, name, size, color):
        color = self.get_color(color)
        filename = '/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf'
        f = agg.Font(color, filename, size=size)
        return f
    
    def text_extents(self, text, font):
        wd, ht = self.canvas.textsize(text, font)
        return wd, ht

#END

