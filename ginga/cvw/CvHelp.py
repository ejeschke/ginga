#
# CvHelp.py -- help classes for the Cv drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy as np
import cv2

from ginga.fonts import font_asst


def get_cached_font(fontname, fontsize):
    key = ('opencv', fontname, fontsize)
    try:
        return font_asst.get_cache(key)

    except KeyError:
        # see if we can build the font
        info = font_asst.get_font_info(fontname, subst_ok=True)

        font = cv2.freetype.createFreeType2()
        font.loadFontData(info.font_path, id=0)
        font_asst.add_cache(key, font)

        return font


def load_font(font_name, font_file):
    if not font_asst.have_font(font_name):
        font_asst.add_font(font_file, font_name=font_name)
    return font_name


class CvContext(object):

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
