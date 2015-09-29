#
# CanvasRenderCairo.py -- for rendering into a ImageViewCairo widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import cairo

from ginga import colors
# force registration of all canvas types
import ginga.canvas.types.all

class RenderContext(object):

    def __init__(self, viewer):
        self.viewer = viewer

        self.cr = viewer.get_offscreen_context()

        self.fill = False
        self.fill_color = None
        self.fill_alpha = 1.0

    def __get_color(self, color, alpha):
        if isinstance(color, str):
            r, g, b = colors.lookup_color(color)
        elif isinstance(color, tuple):
            # color is assumed to be a 3-tuple of RGB values as floats
            # between 0 and 1
            r, g, b = color
        else:
            r, g, b = 1.0, 1.0, 1.0
        return (r, g, b, alpha)

    def _set_color(self, color, alpha=1.0):
        r, g, b, a = self.__get_color(color, alpha)
        self.cr.set_source_rgba(r, g, b, a)

    def _reset_path(self):
        self.cr.new_path()

    def _draw_fill(self):
        if self.fill:
            self._set_color(self.fill_color, alpha=self.fill_alpha)
            self.cr.fill()

    def set_line_from_shape(self, shape):
        alpha = getattr(shape, 'alpha', 1.0)
        self._set_color(shape.color, alpha=alpha)

        linewidth = getattr(shape, 'linewidth', 1)
        self.cr.set_line_width(linewidth)

        if hasattr(shape, 'linestyle'):
            if shape.linestyle == 'dash':
                self.cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)

    def set_fill_from_shape(self, shape):
        self.fill = getattr(shape, 'fill', False)
        if self.fill:
            color = getattr(shape, 'fillcolor', None)
            if color is None:
                color = shape.color
            self.fill_color = color

            alpha = getattr(shape, 'alpha', 1.0)
            self.fill_alpha = getattr(shape, 'fillalpha', alpha)

    def set_font_from_shape(self, shape):
        if hasattr(shape, 'font'):
            if hasattr(shape, 'fontsize') and shape.fontsize is not None:
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            self.cr.select_font_face(shape.font)
            self.cr.set_font_size(fontsize)

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)
        if font:
            self.set_font_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):

        self._set_color(color, alpha=alpha)
        self.cr.set_line_width(linewidth)

        if style == 'dash':
            self.cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.fill = False
        else:
            self.fill = True
            self.fill_color = color
            self.fill_alpha = alpha

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        self.cr.select_font_face(fontname)
        self.cr.set_font_size(fontsize)
        self._set_color(color, alpha=alpha)

    def text_extents(self, text):
        a, b, wd, ht, i, j = self.cr.text_extents(text)
        return wd, ht

    ##### DRAWING OPERATIONS #####

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.save()
        self.cr.translate(cx, cy)
        self.cr.move_to(0, 0)
        self.cr.rotate(-math.radians(rot_deg))
        self.cr.show_text(text)
        self.cr.restore()
        self.cr.new_path()

    def draw_polygon(self, cpoints):
        (cx0, cy0) = cpoints[-1]
        self.cr.move_to(cx0, cy0)
        for cx, cy in cpoints:
            self.cr.line_to(cx, cy)
            #cr.move_to(cx, cy)
        self.cr.close_path()
        self.cr.stroke_preserve()

        self._draw_fill()
        self.cr.new_path()

    def draw_circle(self, cx, cy, cradius):
        self.cr.arc(cx, cy, cradius, 0, 2*math.pi)
        self.cr.stroke_preserve()

        self._draw_fill()
        self.cr.new_path()

    def draw_bezier_curve(self, cp):
        self.cr.move_to(cp[0][0], cp[0][1])
        self.cr.curve_to(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])

        self.cr.stroke()
        self.cr.new_path()

    def draw_ellipse_bezier(self, cp):
        # draw 4 bezier curves to make the ellipse
        self.cr.move_to(cp[0][0], cp[0][1])
        self.cr.curve_to(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.cr.curve_to(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        self.cr.curve_to(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        self.cr.curve_to(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        self.cr.stroke_preserve()

        self._draw_fill()
        self.cr.new_path()

    def draw_line(self, cx1, cy1, cx2, cy2):
        self.cr.set_line_cap(cairo.LINE_CAP_ROUND)
        self.cr.move_to(cx1, cy1)
        self.cr.line_to(cx2, cy2)
        self.cr.stroke()
        self.cr.new_path()

    def draw_path(self, cpoints):
        (cx0, cy0) = cpoints[0]
        self.cr.move_to(cx0, cy0)
        for cx, cy in cpoints[1:]:
            self.cr.line_to(cx, cy)
        self.cr.stroke()
        self.cr.new_path()


class CanvasRenderer(object):

    def __init__(self, viewer):
        self.viewer = viewer

    def setup_cr(self, shape):
        cr = RenderContext(self.viewer)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)


#END
