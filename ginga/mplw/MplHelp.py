#
# MplHelp.py -- help classes for Matplotlib drawing
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import colors

import matplotlib.textpath as textpath


class MplContext(object):

    def __init__(self, axes):
        self.axes = axes
        self.kwdargs = dict()

    def set_canvas(self, axes):
        self.axes = axes

    def init(self, **kwdargs):
        self.kwdargs = dict()
        self.kwdargs.update(kwdargs)

    def set(self, **kwdargs):
        self.kwdargs.update(kwdargs)

    def update_fill(self, obj):
        if hasattr(obj, 'fill'):
            self.kwdargs['fill'] = obj.fill
            if obj.fill:
                self.kwdargs['facecolor'] = self.get_color(obj.fillcolor)
            else:
                self.kwdargs['facecolor'] = self.get_color(obj.color)

    def update_line(self, obj):
        self.kwdargs['color'] = self.get_color(obj.color)

        if hasattr(obj, 'linewidth'):
            self.kwdargs['linewidth'] = obj.linewidth
                
        if hasattr(obj, 'linestyle'):
            self.kwdargs['linestyle'] = obj.linestyle

    def update_patch(self, obj):
        self.kwdargs['edgecolor'] = self.get_color(obj.color)
        if hasattr(obj, 'linewidth'):
            self.kwdargs['linewidth'] = obj.linewidth
                
        if hasattr(obj, 'linestyle'):
            self.kwdargs['linestyle'] = obj.linestyle

        self.update_fill(obj)
                
    def update_text(self, obj):
        self.kwdargs['color'] = self.get_color(obj.color)
        if hasattr(obj, 'font'):
            self.kwdargs['family'] = obj.font
        if hasattr(obj, 'fontsize'):
            self.kwdargs['size'] = obj.fontsize
    
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
    
    def get_font(self, name, size, color):
        color = self.get_color(color)
        fontdict = dict(color=color, family=name, size=size,
                        transform=None)
        return fontdict
    
    def text_extents(self, text, font):
        size = font.get('size', 16)
        name = font.get('name', 'Sans')
        # This is not completely accurate because it depends a lot
        # on the renderer used, but that is complicated under Mpl
        t = textpath.TextPath((0, 0), text, size=size, prop=name)
        bb = t.get_extents()
        wd, ht = bb.width, bb.height
        return (wd, ht)

#END

