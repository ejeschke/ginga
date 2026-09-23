#
# CairoHelp.py -- help classes for the cairo-based operations
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import itertools

import numpy as np

have_cairo = False
try:
    import cairo
    have_cairo = True
except ImportError:
    pass


def text_size(text, font):
    """Calculate the size of text at a given font.

    Parameters
    ----------
    text : str
        A text string

    font : `~ginga.opengl.GlHelp.Font` or compatible object
        A Ginga font descriptor

    Returns
    -------
    (wd, ht) : tuple of int
        Size the text would occupy in pixels.
    """
    wd, ascent, descent = text_metrics(text, font)
    return wd, ascent + descent


def text_metrics(text, font):
    """Calculate (width, ascent, descent) of text at a given font.

    Parameters
    ----------
    text : str
        A text string

    font : `~ginga.opengl.GlHelp.Font` or compatible object
        A Ginga font descriptor

    Returns
    -------
    (wd, ascent, descent) : tuple of int
        Advance width of the string, and the font's ascent above and
        descent below the baseline, in pixels.
    """
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
    ctx = cairo.Context(surface)
    ctx.select_font_face(font.fontname, cairo.FONT_SLANT_NORMAL)
    ctx.set_font_size(font.fontsize)
    # x_advance, not the ink width, so trailing spaces count
    wd = int(round(ctx.text_extents(text)[4]))
    # font_extents(): (ascent, descent, height, max_x_adv, max_y_adv)
    ascent, descent = ctx.font_extents()[:2]
    return wd, int(round(ascent)), int(round(descent))


def text_ink_bbox(text, font):
    """Return the ink bbox of `text` as offsets from its baseline anchor."""
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0)
    ctx = cairo.Context(surface)
    ctx.select_font_face(font.fontname, cairo.FONT_SLANT_NORMAL)
    ctx.set_font_size(font.fontsize)
    # (x_bearing, y_bearing, width, height, x_advance, y_advance); the
    # bearings are already relative to the baseline origin
    xb, yb, wd, ht = ctx.text_extents(text)[:4]
    return (int(np.floor(xb)), int(np.floor(yb)),
            int(np.ceil(xb + wd)), int(np.ceil(yb + ht)))


def text_to_paths(text, font, cx=0, cy=0, rot_deg=0.0, flip_y=False):
    """Convert a text string into paths.

    Parameters
    ----------
    text : str
        A text string

    font :
        A Ginga font descriptor

    cx : int (optional, default 0)
        X offset to add to each path point generated

    cy : int (optional, default 0)
        Y offset to add to each path point generated

    rot_deg : float (optional, default 0.0)
        Amount to rotate the text counterclockwise

    flip_y : bool (optional, default False)
        Whether to flip the coordinates in Y before

    Returns
    -------
    paths : list of ndarray
        A list of paths represented by numpy arrays of (x, y) points;
        the paths can be drawn to render the text
    """
    wd, ht = text_size(text, font)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, wd, ht)
    ctx = cairo.Context(surface)
    ctx.move_to(0, 0)
    ctx.rotate(-np.radians(rot_deg))

    ctx.select_font_face(font.fontname, cairo.FONT_SLANT_NORMAL)
    ctx.set_font_size(font.fontsize)

    ctx.text_path(text)

    p = ctx.copy_path_flat()
    c_paths = [pt if i != cairo.PATH_CLOSE_PATH else None for (i, pt) in p]

    paths = []
    for k, g in itertools.groupby(c_paths, key=lambda t: t is not None):
        lg = list(g)
        if lg[0] is not None and len(lg[0]) > 1:
            pts = np.array(lg)
            off = 0
            if flip_y:
                max_y = ht
                pts.T[1] = max_y - pts.T[1]
                off = ht
            pts = np.add(pts, (cx, cy - off))
            paths.append(pts)

    return paths
