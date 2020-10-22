#
# CvHelp.py -- help classes for the Cv drawing
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy as np
import cv2

from ginga import colors
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
        fontname = font_asst.resolve_alias(fontname, fontname)
        self.fontname = fontname
        self.fontsize = fontsize
        self.color = color
        # text is not filled unless linewidth value is negative
        self.linewidth = -linewidth
        # fonts are scaled by specifying a height--this should be
        # related to the fontsize more accurately here
        self.scale = int(round(fontsize * 1.5))
        self.alpha = alpha
        # note: opencv scales the fonts dynamically, so always
        # specify a 0 for caching
        self.font = get_cached_font(self.fontname, 0)


class CvContext(object):

    def __init__(self, canvas):
        self.canvas = canvas

    def set_canvas(self, canvas):
        self.canvas = canvas

    def get_color(self, color, alpha=1.0):
        if color is not None:
            r, g, b = colors.resolve_color(color)
        else:
            r, g, b = 1.0, 1.0, 1.0

        # According to documentation, OpenCV expects colors as BGRA tuple
        # BUT, seems we need to specify RGBA--I suppose we need to match
        # what is defined as rgb_order attribute in ImageViewCv class
        #return (int(alpha*255), int(b*255), int(g*255), int(r*255))
        return (int(r * 255), int(g * 255), int(b * 255), int(alpha * 255))

    def get_pen(self, color, linewidth=1, alpha=1.0):
        # TODO: support line styles
        # if hasattr(self, 'linestyle'):
        #     if self.linestyle == 'dash':
        #         cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
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
        retval, baseline = font.font.getTextSize(text, font.scale,
                                                 font.linewidth)
        wd, ht = retval
        return wd, ht

    def image(self, pt, rgb_arr):
        # TODO: is there a faster way to copy this array in?
        cx, cy = pt[:2]
        daht, dawd, depth = rgb_arr.shape

        self.canvas[cy:cy + daht, cx:cx + dawd, :] = rgb_arr

    def text(self, pt, text, font):
        x, y = pt
        font.font.putText(self.canvas, text, (x, y), font.scale,
                          font.color, thickness=font.linewidth,
                          line_type=cv2.LINE_AA, bottomLeftOrigin=True)

    def line(self, pt1, pt2, pen):
        x1, y1 = int(round(pt1[0])), int(round(pt1[1]))
        x2, y2 = int(round(pt2[0])), int(round(pt2[1]))
        cv2.line(self.canvas, (x1, y1), (x2, y2), pen.color, pen.linewidth)

    def circle(self, pt, radius, pen, brush):
        x, y = pt
        radius = int(radius)
        if (brush is not None) and brush.fill:
            cv2.circle(self.canvas, (x, y), radius, brush.color, -1)
        cv2.circle(self.canvas, (x, y), radius, pen.color, pen.linewidth)

    def polygon(self, points, pen, brush):
        pts = np.array(points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(self.canvas, [pts], True, pen.color, pen.linewidth)
        if (brush is not None) and brush.fill:
            cv2.fillPoly(self.canvas, [pts], brush.color)

    def path(self, points, pen):
        pts = np.array(points, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(self.canvas, [pts], False, pen.color, pen.linewidth)


# END
