#
# PilHelp.py -- help classes for the PIL drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

import numpy as np
from PIL import Image, ImageFont, ImageDraw

from ginga import colors
from ginga.fonts import font_asst


def get_font(font_spec, font_size):
    """Function to obtain a native font for the Pil backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : pillow truetype font
        The desired font in native backend form
    """
    key = ('pil', font_spec, font_size)
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
            font = load_font(font_tup, font_size)

        except Exception:
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
                    font = load_font(font_tup2, font_size)
                    break
                except Exception:
                    continue

    if font is None:
        try:
            # if all is lost, try the Pillow "default font"
            font = ImageFont.load_default(font_size)
        except Exception:
            raise ValueError(f"Couldn't create font for family '{font_tup.family}', "
                             f"style={font_tup.style}, weight={font_tup.weight}")

    font_asst.add_cache(key, font)
    if isinstance(font_spec, str):
        # also store the font under a secondary key
        key2 = ('pil', font_tup, font_size)
        font_asst.add_cache(key2, font)

    return font


def load_font(font_tup, font_size):
    info = font_asst.get_font_info(font_tup)
    return ImageFont.truetype(info.font_path, font_size)


def text_metrics(text, font):
    """Return (width, ascent, descent) of `text` in `font`, in pixels.

    The ascent/descent are the *font's*, not this particular string's ink
    extent, so that every string drawn in a given font shares one baseline
    and one box height.
    """
    f = get_font(font.fontname, font.fontsize)
    ascent, descent = f.getmetrics()
    if hasattr(f, 'getlength'):
        wd_px = int(round(f.getlength(text)))
    elif hasattr(f, 'getbbox'):
        l, t, r, b = f.getbbox(text)
        wd_px = int(abs(round(r - l)))
    else:
        wd_px = f.getsize(text)[0]
    return wd_px, int(ascent), int(descent)


def text_ink_bbox(text, font):
    """Return the ink bbox of `text` as offsets from its baseline anchor."""
    f = get_font(font.fontname, font.fontsize)
    ascent, descent = f.getmetrics()
    if hasattr(f, 'getbbox'):
        # getbbox() is relative to the "la" (ascender) origin; shift onto
        # the baseline
        l, t, r, b = f.getbbox(text)
        return int(l), int(t - ascent), int(r), int(b - ascent)
    wd, ht = f.getsize(text)
    return 0, -ascent, int(wd), int(descent)


def text_size(text, font):
    wd_px, ascent, descent = text_metrics(text, font)
    return wd_px, ascent + descent


def rasterize_text(text, pil_font, color=(1.0, 1.0, 1.0, 1.0)):
    """Rasterize ``text`` to an ``(H, W, 4)`` uint8 RGBA array: a transparent
    tile with the glyphs drawn in ``color`` (an RGB or RGBA tuple in 0..1).

    ``pil_font`` is a loaded Pillow truetype font (e.g. from :func:`get_font`).
    Returns ``(arr, width, height, dx, dy)``, where ``(dx, dy)`` is the offset
    of the tile's top-left corner from the text's *baseline* anchor, y
    increasing downward (so ``dy`` is normally negative).  Used by the GPU
    renderers to blit text as a textured quad: placing the tile at
    ``(cx + dx, cy + dy)`` puts the glyphs where the CPU renderers draw them
    for the same ``(cx, cy)``.

    NOTE: the tile is cropped to the string's ink, so its height varies with
    which glyphs the string contains.  Anchoring the tile by an edge rather
    than by ``(dx, dy)`` therefore slides the baseline around from string to
    string.
    """
    dummy = ImageDraw.Draw(Image.new('RGBA', (4, 4)))
    try:
        l, t, r, b = dummy.textbbox((0, 0), text, font=pil_font)
    except Exception:
        w0, h0 = dummy.textsize(text, font=pil_font)
        l, t, r, b = 0, 0, w0, h0
    w, h = max(1, r - l), max(1, b - t)
    pad = 2
    img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    rr, gg, bb = (int(c * 255) for c in color[:3])
    aa = int((color[3] if len(color) > 3 else 1.0) * 255)
    ImageDraw.Draw(img).text((pad - l, pad - t), text, font=pil_font,
                             fill=(rr, gg, bb, aa))
    arr = np.ascontiguousarray(np.asarray(img, dtype=np.uint8))
    # textbbox() is measured from the "la" (ascender) origin; shift onto the
    # baseline, then out by the tile's transparent margin
    ascent = pil_font.getmetrics()[0]
    dx, dy = l - pad, t - ascent - pad
    return arr, arr.shape[1], arr.shape[0], dx, dy


def text_to_array(text, font, rot_deg=0.0):
    wd, ht = text_size(text, font)
    f = get_font(font.fontname, font.fontsize)
    color = get_color(font.color)
    i = Image.new('RGBA', (wd, ht))
    d = ImageDraw.Draw(i, 'RGBA')
    d.text((0, 0), text, font=f, fill=color)
    i.rotate(rot_deg, expand=1)
    arr8 = np.frombuffer(i.tobytes(), dtype=np.uint8)
    arr8 = arr8.reshape((ht, wd, 4))
    return arr8


def get_color(color, alpha=1.0):
    if color is not None:
        r, g, b = colors.resolve_color(color)
    else:
        r, g, b = 1.0, 1.0, 1.0

    return (int(r * 255), int(g * 255), int(b * 255), int(alpha * 255))


class PilContext:

    def __init__(self, surface):
        self.set_canvas(surface)

    def set_canvas(self, surface):
        self.surface = surface
        self.ctx = ImageDraw.Draw(surface, 'RGBA')

    def _cvt_points(self, points):
        # PIL seems to have trouble with numpy arrays as sequences
        # of points, so just convert to a list

        # TODO: this doesn't work--would be more efficient if it did
        # if isinstance(points, np.ndarray):
        #     return points.tolist()
        # return points
        return [(p[0], p[1]) for p in points]

    def _get_font(self, font):
        font = get_font(font.fontname, font.fontsize)
        return font

    def text_extents(self, text, font):
        return text_size(text, font)

    def text_metrics(self, text, font):
        return text_metrics(text, font)

    def image(self, pt, rgb_arr):
        p_image = Image.fromarray(rgb_arr)

        self.surface.paste(p_image)

    def text(self, pt, text, font, line, fill):
        x, y = pt
        kwargs = dict()
        if font is not None:
            kwargs['font'] = font.render.font
        if fill is not None:
            kwargs['fill'] = fill.render.color
        if line is not None:
            kwargs['stroke_width'] = int(line.linewidth)
            kwargs['stroke_fill'] = line.render.color
        self.ctx.text((x, y), text, **kwargs)

    def text_rotated(self, pt, wd, ascent, descent, text, font, line, fill,
                     rot_deg):
        """Draw ``text`` rotated by ``rot_deg`` degrees about the anchor
        ``pt`` (the left end of the unrotated text's baseline).

        PIL's ``ImageDraw.text`` cannot rotate, so we render the string onto
        a transparent square scratch tile with the anchor at the tile's
        center, rotate the tile about that center (``expand=False`` keeps the
        center fixed), and paste it so the center lands on the anchor.  Only
        used when a rotation is actually requested; unrotated text takes the
        fast direct-draw path in :meth:`text`.
        """
        cx, cy = pt
        kwargs = dict()
        if font is not None:
            kwargs['font'] = font.render.font
        if fill is not None:
            kwargs['fill'] = fill.render.color
        if line is not None:
            kwargs['stroke_width'] = int(line.linewidth)
            kwargs['stroke_fill'] = line.render.color

        # Square tile big enough to hold the string at any rotation.  The
        # anchor sits at the tile center and the text box extends up to
        # hypot(wd, ht) away from it (its far corner), so the tile radius
        # must be that far corner distance, plus a margin for the stroke.
        pad = int(line.linewidth) + 2 if line is not None else 2
        ht = ascent + descent
        radius = int(math.ceil(math.hypot(wd, ht))) + pad
        side = 2 * radius
        ctr = radius

        tile = Image.new('RGBA', (side, side), (0, 0, 0, 0))
        # place the text so the left end of its baseline (the anchor) is at
        # the center; ImageDraw.text() positions by the ascender line
        ImageDraw.Draw(tile, 'RGBA').text((ctr, ctr - ascent), text, **kwargs)

        # PIL rotates counter-clockwise for a positive angle, matching Ginga's
        # rot_deg convention (cf. the cairo/agg backends).  expand=False keeps
        # the tile size (and thus the center) fixed.
        tile = tile.rotate(rot_deg, resample=Image.BICUBIC, expand=False)

        # paste so the tile center (= the anchor) lands on (cx, cy)
        self.surface.paste(tile, (int(round(cx - ctr)), int(round(cy - ctr))),
                           tile)

    def line(self, pt1, pt2, line):
        if line is not None:
            x1, y1 = int(np.round(pt1[0])), int(np.round(pt1[1]))
            x2, y2 = int(np.round(pt2[0])), int(np.round(pt2[1]))
            self.ctx.line(((x1, y1), (x2, y2)), fill=line.render.color,
                          width=line.linewidth)

    def circle(self, pt, radius, line, fill):
        x, y = pt
        radius = int(radius)
        kwargs = dict()
        if fill is not None:
            kwargs['fill'] = fill.render.color
        if line is not None:
            kwargs['width'] = line.linewidth
            kwargs['outline'] = line.render.color
        self.ctx.ellipse(((x - radius, y - radius), (x + radius, y + radius)),
                         **kwargs)

    def polygon(self, points, line, fill):
        points = self._cvt_points(points)

        kwargs = dict()
        if fill is not None:
            kwargs['fill'] = fill.render.color
        if line is not None:
            kwargs['width'] = line.linewidth
            kwargs['outline'] = line.render.color
        self.ctx.polygon(points, **kwargs)

    def path(self, points, line):
        points = self._cvt_points(points)

        p0 = points[0]
        for pt in points[1:]:
            self.line(p0, pt, line)
            p0 = pt

#END
