#
# BokehHelp.py -- help classes for Bokeh drawing
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import colors


class Pen(object):
    def __init__(self, color='black', linewidth=1, linestyle='solid'):
        self.color = color
        self.linewidth = linewidth
        self.linestyle = linestyle

class Brush(object):
    def __init__(self, color='black', fill=False):
        self.color = color
        self.fill = fill

class Font(object):
    def __init__(self, fontname='sans', fontsize=12.0, color='black'):
        self.fontname = fontname
        self.fontsize = fontsize
        self.color = color


class BokehContext(object):

    def __init__(self, plot):
        self.plot = plot
        self.kwdargs = dict()

    def set_canvas(self, plot):
        self.plot = plot

    def init(self, **kwdargs):
        self.kwdargs = dict()
        self.kwdargs.update(kwdargs)

    def set(self, **kwdargs):
        self.kwdargs.update(kwdargs)

    def update_fill(self, brush):
        if brush is not None:
            # NOTE: alpha is taken care of in brush.color
            self.kwdargs['fill_alpha'] = 1.0
            self.kwdargs['fill_color'] = brush.color
        else:
            self.kwdargs['fill_alpha'] = 0.0

    def update_line(self, pen):
        self.kwdargs['line_color'] = pen.color
        self.kwdargs['line_width'] = pen.linewidth
        if pen.linestyle == 'dash':
            self.kwdargs['line_dash'] = [3, 2, 3, 2]
            self.kwdargs['line_dash_offset'] = 0

    def update_patch(self, pen, brush):
        self.update_line(pen)
        self.update_fill(brush)

    def update_font(self, pen, font):
        self.kwdargs['text_font'] = font.fontname
        # Bokeh expects font size specified as a string
        self.kwdargs['text_font_size'] = str(font.fontsize)
        self.kwdargs['text_color'] = pen.color

    def get_color(self, color, alpha):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 4-tuple of RGBA values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        # from the Bokeh docs:
        # "a 4-tuple of (r,g,b,a) where r, g, b are integers between
        #  0 and 255 and a is a floating point value between 0 and 1"
        ri, gi, bi = int(255*r), int(255*g), int(255*b)

        return (ri, gi, bi, alpha)

    def get_pen(self, color, alpha=1.0, linewidth=1, linestyle='solid'):
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, linestyle=linestyle)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True)

    def get_font(self, name, size, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color)

    def text_extents(self, text, font):
        # This is not completely accurate because it depends a lot
        # on the renderer used, but that is complicated under Bokeh
        t = textpath.TextPath((0, 0), text, size=font.fontsize,
                              prop=font.fontname)
        bb = t.get_extents()
        wd, ht = bb.width, bb.height
        return (wd, ht)

#END
