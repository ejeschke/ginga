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
            alpha = getattr(obj, 'alpha', 1.0)
            alpha = getattr(obj, 'fillalpha', alpha)

            if obj.fillcolor:
                self.kwdargs['facecolor'] = self.get_color(obj.fillcolor,
                                                           alpha)
            else:
                self.kwdargs['facecolor'] = self.get_color(obj.color,
                                                           alpha)

    def update_line(self, obj):
        alpha = getattr(obj, 'alpha', 1.0)
        self.kwdargs['color'] = self.get_color(obj.color,
                                                   alpha)

        if hasattr(obj, 'linewidth'):
            self.kwdargs['linewidth'] = obj.linewidth
                
        if hasattr(obj, 'linestyle'):
            self.kwdargs['linestyle'] = obj.linestyle

    def update_patch(self, obj):
        self.update_fill(obj)

        line_color_attr = 'facecolor'
        if 'facecolor' in self.kwdargs:
            line_color_attr = 'edgecolor'

        alpha = getattr(obj, 'alpha', 1.0)
        self.kwdargs[line_color_attr] = self.get_color(obj.color,
                                                       alpha)
        if hasattr(obj, 'linewidth'):
            self.kwdargs['linewidth'] = obj.linewidth
                
        if hasattr(obj, 'linestyle'):
            self.kwdargs['linestyle'] = obj.linestyle

        #print (self.kwdargs)
                
    def update_text(self, obj):
        alpha = getattr(obj, 'alpha', 1.0)
        self.kwdargs['color'] = self.get_color(obj.color, alpha)
        if hasattr(obj, 'font'):
            self.kwdargs['family'] = obj.font
        if hasattr(obj, 'fontsize'):
            self.kwdargs['size'] = obj.fontsize
    
    def get_color(self, color, alpha):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 4-tuple of RGBA values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (r, g, b, alpha)
    
    def get_font(self, name, size, color, alpha=1.0):
        color = self.get_color(color, alpha)
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

