#
# MplHelp.py -- help classes for Matplotlib drawing
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import colors


class MplContext(object):

    def __init__(self, axes):
        self.axes = axes

    def set_canvas(self, axes):
        self.axes = axes
        
    def get_color(self, color):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        #return (int(r*255), int(g*255), int(b*255))
        return (r, g, b)
    
    def get_brush(self, obj, kwdargs):
        kwdargs['fill'] = obj.fill
        if obj.fill:
            if obj.fillcolor:
                kwdargs['facecolor'] = self.get_color(obj.fillcolor)
            else:
                kwdargs['facecolor'] = self.get_color(obj.color)
    
    def get_pen(self, obj, kwdargs):
        kwdargs['edgecolor'] = self.get_color(obj.color)

        if hasattr(obj, 'linewidth'):
            kwdargs['linewidth'] = obj.linewidth
                
        if hasattr(obj, 'linestyle'):
            kwdargs['linestyle'] = obj.linestyle
                
    
    def get_font(self, name, size, color):
        color = self.get_color(color)
        filename = '/usr/share/fonts/truetype/ttf-dejavu/DejaVuSans.ttf'
        f = agg.Font(color, filename, size=size)
        return f
    
    def text_extents(self, text, font):
        wd, ht = self.canvas.textsize(text, font)
        return wd, ht

#END

