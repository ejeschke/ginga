#
# PilHelp.py -- help classes for the PIL drawing
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import os.path
from PIL import ImageFont, ImageDraw

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
    def __init__(self, color='black', linewidth=1, alpha=1.0):
        self.color = color
        self.linewidth = linewidth
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
        self.font = get_cached_font(self.fontname, self.fontsize)


class PilContext(object):

    def __init__(self, surface):
        self.ctx = ImageDraw.Draw(surface)

    def set_canvas(self, surface):
        self.ctx = ImageDraw.Draw(surface)

    def get_color(self, color, alpha=1.0):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (int(r*255), int(g*255), int(b*255), int(alpha*255))

    def get_pen(self, color, linewidth=1, alpha=1.0):
        # if hasattr(self, 'linestyle'):
        #     if self.linestyle == 'dash':
        #         cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
        #op = int(alpha * 255)
        color = self.get_color(color, alpha=alpha)
        return Pen(color=color, linewidth=linewidth, alpha=alpha)

    def get_brush(self, color, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Brush(color=color, fill=True, alpha=alpha)

    def get_font(self, name, size, color, linewidth=1, alpha=1.0):
        color = self.get_color(color, alpha=alpha)
        return Font(fontname=name, fontsize=size, color=color,
                    linewidth=linewidth, alpha=alpha)

    def text_extents(self, text, font):
        retval = self.ctx.textsize(text, font.font)
        wd, ht = retval
        return wd, ht

    def text(self, pt, text, font, pen):
        x, y = pt
        self.ctx.text((x, y), text, fill=pen.color, font=font.font)

    def line(self, pt1, pt2, pen):
        x1, y1 = int(round(pt1[0])), int(round(pt1[1]))
        x2, y2 = int(round(pt2[0])), int(round(pt2[1]))
        self.ctx.line(((x1, y1), (x2, y2)), fill=pen.color,
                      width=pen.linewidth)

    def circle(self, pt, radius, pen, brush):
        x, y = pt
        radius = int(radius)
        if (brush is not None) and brush.fill:
            self.ctx.ellipse(((x-radius, y-radius), (x+radius, y+radius)),
                             fill=brush.color, outline=pen.color)
        else:
            self.ctx.ellipse(((x-radius, y-radius), (x+radius, y+radius)),
                             outline=pen.color)

    ## def rectangle(self, pt1, pt2, pen, brush):
    ##     x1, y1 = pt1
    ##     x2, y2 = pt2
    ##     self.ctx.polygon(((x1, y1), (x1, y2), (x2, y2), (x2, y1)),
    ##                      fill=brush.color, outline=pen.color)

    def ellipse(self, pt, xr, yr, theta, pen, brush):
        x, y = pt
        if (brush is not None) and brush.fill:
            self.ctx.ellipse(((x-xr, y-yr), (x+xr, y+yr)),
                             fill=brush.color, outline=pen.color)
        else:
            self.ctx.ellipse(((x-xr, y-yr), (x+xr, y+yr)),
                             outline=pen.color)

    def polygon(self, points, pen, brush):
        if (brush is not None) and brush.fill:
            self.ctx.polygon(points, fill=brush.color, outline=pen.color)
        else:
            self.ctx.polygon(points, outline=pen.color)

    def path(self, points, pen):
        p0 = points[0]
        for pt in points[1:]:
            self.line(p0, pt, pen)
            p0 = pt

#END
