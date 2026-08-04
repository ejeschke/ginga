#
# AggHelp.py -- help classes for the Agg drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
"""Helper classes for the Agg backend.

Historically this backend rendered with the (now poorly maintained)
``aggdraw`` package.  It is now implemented on top of the Anti-Grain
Geometry rasterizer that ships inside matplotlib
(``matplotlib.backends.backend_agg.RendererAgg``) -- the same AGG library
``aggdraw`` wrapped, but via a well maintained dependency that Ginga
already requires.
"""
from matplotlib.backends.backend_agg import RendererAgg
from matplotlib.font_manager import FontProperties

from ginga.fonts import font_asst

# Render at 72 dpi so that a point equals a pixel; this keeps font point
# sizes and line widths (which Ginga specifies in pixels) 1:1 with the
# output raster, and makes text metrics match what gets drawn.
dpi = 72.0

# A tiny standalone renderer used solely for text measurement.  Glyph
# metrics depend only on the FontProperties and the dpi, not on the size
# of the drawing surface, so a shared 1x1 renderer gives correct extents
# even before the real surface has been allocated.
_meas_renderer = RendererAgg(1, 1, dpi)


def get_font(font_spec, font_size):
    """Function to obtain a native font for the Agg backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : `matplotlib.font_manager.FontProperties`
        The desired font in native (matplotlib) backend form
    """
    key = ('mpl_agg', font_spec, font_size)
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

    # font not loaded? try and load it, building a FontProperties bound to
    # the exact TrueType file Ginga resolved (so all backends render the
    # same glyphs).
    font = None
    if font_asst.have_loadable_font(font_tup):
        try:
            info = font_asst.get_font_info(font_tup)
            font = FontProperties(fname=info.font_path, size=font_size)
        except Exception:
            pass

    if font is None:
        # try to create the font from the family name directly, plus any
        # other substitute fonts
        families = font_asst.get_substitutes(font_tup.family)
        for family in families:
            font_tup2 = font_asst.Font(family=family, style=font_tup.style,
                                       weight=font_tup.weight)
            if font_asst.have_loadable_font(font_tup2):
                try:
                    info = font_asst.get_font_info(font_tup2)
                    font = FontProperties(fname=info.font_path,
                                          size=font_size)
                    break
                except Exception:
                    continue

    if font is not None:
        font_asst.add_cache(key, font)
        if isinstance(font_spec, str):
            # also store the font under a secondary key
            key2 = ('mpl_agg', font_tup, font_size)
            font_asst.add_cache(key2, font)
        return font

    raise ValueError(f"Couldn't create font for family '{font_tup.family}', "
                     f"style={font_tup.style}, weight={font_tup.weight}")


class AggContext:

    def __init__(self, surface):
        # surface is a matplotlib RendererAgg (or None until allocated)
        self.canvas = surface

    def set_canvas(self, surface):
        self.canvas = surface

    def _get_font(self, font):
        # font is a ginga.canvas.render.Font
        return get_font(font.fontname, font.fontsize)

    def text_extents(self, text, prop):
        # prop is a matplotlib FontProperties
        wd, ht, descent = _meas_renderer.get_text_width_height_descent(
            text, prop, False)
        return wd, ht

# END
