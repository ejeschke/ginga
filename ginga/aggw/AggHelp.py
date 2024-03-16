#
# AggHelp.py -- help classes for the Agg drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import aggdraw as agg

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

    def _get_font(self, font, fill):
        color = fill.render.color[:3]
        op = fill.render.color[3]

        font = get_cached_font(font.fontname, font.fontsize, color, op)
        return font

    def text_extents(self, text, _font):
        # _font is an Agg font
        wd, ht = self.canvas.textsize(text, _font)
        return wd, ht

# END
