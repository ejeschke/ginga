#
# GlHelp.py -- help classes for OpenGL drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import os.path

from ginga import colors
import ginga.fonts
from ginga.canvas import transform

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
        from PIL import ImageFont

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
        self.fontsize = fontsize * 2.0
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
        if color is not None:
            r, g, b = colors.resolve_color(color)
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


def get_transforms(v):
    tform = {
        # CHANGED
        'window_to_native': (transform.CartesianWindowTransform(v).invert() +
                             transform.RotationTransform(v).invert() +
                             #transform.FlipSwapTransform(v).invert() +
                             transform.ScaleTransform(v).invert()
                             #transform.ScaleTransform(v)
                             ),
        'cartesian_to_window': (transform.FlipSwapTransform(v) +
                                transform.CartesianWindowTransform(v)),
        # CHANGED
        'cartesian_to_native': (transform.FlipSwapTransform(v) +
                                transform.RotationTransform(v) +
                                transform.CartesianNativeTransform(v)),
        'data_to_cartesian': (transform.DataCartesianTransform(v) +
                              transform.ScaleTransform(v)),
        'data_to_scrollbar': (transform.DataCartesianTransform(v) +
                              transform.FlipSwapTransform(v) +
                              transform.RotationTransform(v)),
        ## 'window_to_data': (transform.CartesianWindowTransform(v).invert() +
        ##                    transform.FlipSwapTransform(v) +
        ##                    transform.RotationTransform(v).invert()
        ##                    ),
        'data_to_window': (transform.DataCartesianTransform(v) +
                           transform.ScaleTransform(v) +
                           transform.FlipSwapTransform(v) +
                           transform.RotationTransform(v) +
                           transform.CartesianWindowTransform(v)
                           ),
        'data_to_percentage': (transform.DataCartesianTransform(v) +
                               transform.ScaleTransform(v) +
                               transform.FlipSwapTransform(v) +
                               transform.RotationTransform(v) +
                               transform.CartesianWindowTransform(v) +
                               transform.WindowPercentageTransform(v)),
        # CHANGED
        'data_to_native': (transform.DataCartesianTransform(v) +
                           transform.FlipSwapTransform(v)
                           ),
        'wcs_to_data': transform.WCSDataTransform(v),
        # CHANGED
        'wcs_to_native': (transform.WCSDataTransform(v) +
                          transform.DataCartesianTransform(v) +
                          transform.FlipSwapTransform(v)),
    }
    return tform


#END
