#
# AggHelp.py -- help classes for the Agg drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import aggdraw as agg

from ginga import colors
from ginga.fonts import font_asst


def get_cached_font(fontname, fontsize, color, alpha):
    key = ('agg', fontname, fontsize, color, alpha)
    try:
        return font_asst.get_cache(key)

    except KeyError:
        # see if we can build the font
        info = font_asst.get_font_info(fontname, subst_ok=True)

        font = agg.Font(color, info.font_path, size=fontsize, opacity=alpha)
        font_asst.add_cache(key, font)

        return font


def load_font(font_name, font_file):
    # try to load it as a sanity check
    #agg.Font('black', font_file, size=10, opacity=255)

    if not font_asst.have_font(font_name):
        font_asst.add_font(font_file, font_name=font_name)
    return font_name


class AggContext(object):

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def get_color(self, color):
        if color is not None:
            r, g, b = colors.resolve_color(color)
        else:
            r, g, b = 1.0, 1.0, 1.0

        return (int(r * 255), int(g * 255), int(b * 255))

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

        name = font_asst.resolve_alias(name, name)
        font = get_cached_font(name, size, color, op)
        return font

    def text_extents(self, text, font):
        wd, ht = self.canvas.textsize(text, font)
        return wd, ht

# END
