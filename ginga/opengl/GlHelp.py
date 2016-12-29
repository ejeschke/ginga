#
# GlHelp.py -- help classes for OpenGL drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import os.path

from ginga import colors
import ginga.fonts

# Set up known fonts
fontdir, xx = os.path.split(ginga.fonts.__file__)
known_font = os.path.join(fontdir, 'Roboto', 'Roboto-Regular.ttf')

font_cache = {}

def get_cached_font(fontpath, fontsize):
    global font_cache

    key = (fontpath, fontsize)
    try:
        return font_cache[key]

    except KeyError:
        # TODO: try to lookup font before overriding
        fontpath = known_font

        font = ImageFont.truetype(fontpath, fontsize)
        font_cache[key] = font
        return font


class Pen(object):
    def __init__(self, color='black', alpha=1.0, linewidth=1,
                 linestyle='solid'):
        self.color = color
        self.linewidth = linewidth
        self.linestyle = linestyle
        self.alpha = alpha

class Brush(object):
    def __init__(self, color='black', fill=False, alpha=1.0):
        self.color = color
        self.fill = fill
        self.alpha = alpha

class Font(object):
    def __init__(self, fontname='ariel', fontsize=12.0, color='black',
                 linewidth=1, alpha=1.0):
        self.fontname = fontname
        self.fontsize = int(fontsize)
        self.color = color
        self.linewidth = linewidth
        # scale relative to a 12pt font
        self.scale = fontsize / 12.0
        self.alpha = alpha
        # TODO: currently there is only support for some simple built-in
        # fonts.  What kind of fonts/lookup can we use for this?
        #self.font = get_cached_font(self.fontname, self.fontsize)


class GlContext(object):

    def __init__(self, widget):
        #self.set_canvas(widget)
        self.widget = widget

    def get_color(self, color, alpha=1.0):
        if isinstance(color, str) or isinstance(color, type(u"")):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (r, g, b, alpha)

    def get_pen(self, color, linewidth=1, linestyle='solid', alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, linestyle=linestyle,
                   alpha=alpha)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True, alpha=alpha)

    def get_font(self, name, size, color, linewidth=1, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color,
                    linewidth=linewidth, alpha=alpha)

    def text_extents(self, text, font):
        # TODO: we need a better approximation
        wd = len(text) * font.fontsize
        ht = font.fontsize
        return wd, ht

#END
