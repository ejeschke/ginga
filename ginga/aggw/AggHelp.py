#
# AggHelp.py -- help classes for the Agg drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import aggdraw as agg

from ginga.fonts import font_asst


def get_font(font_spec, font_size, color='black', alpha=1.0):
    """Function to obtain a native font for the Agg backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : agg truetype font
        The desired font in native backend form
    """
    key = ('agg', font_spec, font_size, color, alpha)
    try:
        return font_asst.get_cache(key)

    except KeyError:
        pass

    if isinstance(font_spec, str):
        font_tup = font_asst.parse_font(font_spec)
    elif isinstance(font_spec, font_asst.Font):
        font_tup = font_spec
    else:
        raise ValueError("not a valid font spec: {}".format(str(font_spec)))

    # font not loaded? try and load it
    font = None
    if font_asst.have_loadable_font(font_tup):
        try:
            info = font_asst.get_font_info(font_tup)

            font = agg.Font(color, info.font_path, size=font_size,
                            opacity=alpha)

        except Exception as e:
            pass

    if font is None:
        # try to create the font from the family name directly, plus in any
        # other substitute fonts
        families = font_asst.get_substitutes(font_tup.family)
        for family in families:
            font_tup2 = font_asst.Font(family=family, style=font_tup.style,
                                       weight=font_tup.weight)
            if font_asst.have_loadable_font(font_tup2):
                try:
                    info = font_asst.get_font_info(font_tup2)
                    font = agg.Font(color, info.font_path, size=font_size,
                                    opacity=alpha)
                    break
                except Exception as e:
                    continue

    # TODO: return Agg's "default font"

    if font is not None:
        font_asst.add_cache(key, font)
        if isinstance(font_spec, str):
            # also store the font under a secondary key
            key2 = ('agg', font_tup, font_size, color, alpha)
            font_asst.add_cache(key2, font)
        return font

    raise ValueError(f"Couldn't create font for family '{font_tup.family}', "
                     f"style={font_tup.style}, weight={font_tup.weight}")


class AggContext:

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def _get_font(self, font, fill):
        color = fill.render.color[:3]
        op = fill.render.color[3]

        font = get_font(font.fontname, font.fontsize, color, op)
        return font

    def text_extents(self, text, _font):
        # _font is an Agg font
        wd, ht = self.canvas.textsize(text, _font)
        return wd, ht

# END
