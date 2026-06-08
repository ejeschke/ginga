#
# CvHelp.py -- help classes for the Cv drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy as np
import cv2

from ginga.fonts import font_asst


def get_font(font_spec, font_size):
    """Function to obtain a native font for the OpenCv backend.

    Parameters
    ----------
    font_spec : str or `~ginga.fonts.font_asst.Font`
        The desired font

    font_size : int
        The point size requested for the given font

    Returns
    -------
    font : OpenCv truetype font
        The desired font in native backend form
    """
    key = ('opencv', font_spec, font_size)
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

            font = cv2.freetype.createFreeType2()
            font.loadFontData(info.font_path, id=0)

        except Exception as e:
            pass

    if font is not None:
        font_asst.add_cache(key, font)
        if isinstance(font_spec, str):
            # also store the font under a secondary key
            key2 = ('opencv', font_tup, font_size)
            font_asst.add_cache(key2, font)
        return font

    raise ValueError(f"Couldn't create font for family '{font_tup.family}', "
                     f"style={font_tup.style}, weight={font_tup.weight}")


class CvContext:

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def text_extents(self, text, font):
        _font, _scale = font.render.font, font.render.scale
        retval, baseline = _font.getTextSize(text, _scale, -1)
        wd_px, ht_px = retval
        return wd_px, ht_px

    def image(self, pt, rgb_arr):
        # TODO: is there a faster way to copy this array in?
        cx, cy = pt[:2]
        daht, dawd, depth = rgb_arr.shape

        self.canvas[cy:cy + daht, cx:cx + dawd, :] = rgb_arr

    def text(self, pt, text, font, line, fill):
        x, y = pt
        if font is not None and fill is not None:
            _font, _scale = font.render.font, font.render.scale
            _font.putText(self.canvas, text, (x, y), _scale,
                          # text is not filled unless thickness is negative
                          fill.render.color, thickness=-1,
                          line_type=cv2.LINE_AA, bottomLeftOrigin=True)

    def line(self, pt1, pt2, line):
        if line is not None:
            x1, y1 = int(round(pt1[0])), int(round(pt1[1]))
            x2, y2 = int(round(pt2[0])), int(round(pt2[1]))
            cv2.line(self.canvas, (x1, y1), (x2, y2), line.render.color,
                     line.linewidth)

    def circle(self, pt, radius, line, fill):
        x, y = pt
        radius = int(radius)
        if fill is not None:
            cv2.circle(self.canvas, (x, y), radius, fill.render.color, -1)
        if line is not None:
            cv2.circle(self.canvas, (x, y), radius, line.render.color,
                       line.linewidth)

    def polygon(self, points, line, fill):
        pts = np.array(points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        if fill is not None:
            cv2.fillPoly(self.canvas, [pts], fill.render.color)
        if line is not None:
            cv2.polylines(self.canvas, [pts], True, line.render.color,
                          line.linewidth)

    def path(self, points, line):
        pts = np.array(points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        if line is not None:
            cv2.polylines(self.canvas, [pts], False, line.render.color,
                          line.linewidth)


# END
