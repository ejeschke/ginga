#
# PilHelp.py -- help classes for the PIL drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

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
                    font = load_font(font_tup2, font_size)
                    break
                except Exception as e:
                    continue

    if font is None:
        try:
            # if all is lost, try the Pillow "default font"
            font = ImageFont.load_default(font_size)
        except Exception as e:
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


def text_size(text, font):
    f = get_font(font.fontname, font.fontsize)
    if hasattr(f, 'getbbox'):
        # PIL v10.0
        l, t, r, b = f.getbbox(text)
        wd_px, ht_px = int(abs(round(r - l))), int(abs(round(b - t)))
    else:
        wd_px, ht_px = f.getsize(text)
    return wd_px, ht_px


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
