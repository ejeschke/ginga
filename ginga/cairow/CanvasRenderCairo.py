#
# CanvasRenderCairo.py -- for rendering into a ImageViewCairo widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys
import math

import numpy as np
import cairo

from ginga import colors
from ginga.fonts import font_asst
from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        self.cr = cairo.Context(surface)

        self.fill = False
        self.fill_color = None
        self.fill_alpha = 1.0

    def __get_color(self, color, alpha):
        if color is not None:
            r, g, b = colors.resolve_color(color)
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
                self.cr.set_dash([3.0, 4.0, 6.0, 4.0], 5.0)

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
            if (hasattr(shape, 'fontsize') and shape.fontsize is not None and
                not getattr(shape, 'fontscale', False)):
                fontsize = shape.fontsize
            else:
                fontsize = shape.scale_font(self.viewer)
            fontname = font_asst.resolve_alias(shape.font, shape.font)
            self.cr.select_font_face(fontname)
            fontsize = self.scale_fontsize(fontsize)
            self.cr.set_font_size(fontsize)

    def initialize_from_shape(self, shape, line=True, fill=True, font=True):
        if font:
            self.set_font_from_shape(shape)
        if line:
            self.set_line_from_shape(shape)
        if fill:
            self.set_fill_from_shape(shape)

    def set_line(self, color, alpha=1.0, linewidth=1, style='solid'):

        self._set_color(color, alpha=alpha)
        self.cr.set_line_width(linewidth)

        if style == 'dash':
            self.cr.set_dash([3.0, 4.0, 6.0, 4.0], 5.0)

    def set_fill(self, color, alpha=1.0):
        if color is None:
            self.fill = False
        else:
            self.fill = True
            self.fill_color = color
            self.fill_alpha = alpha

    def set_font(self, fontname, fontsize, color='black', alpha=1.0):
        fontname = font_asst.resolve_alias(fontname, fontname)
        self.cr.select_font_face(fontname)
        fontsize = self.scale_fontsize(fontsize)
        self.cr.set_font_size(fontsize)
        self._set_color(color, alpha=alpha)

    def text_extents(self, text):
        a, b, wd, ht, i, j = self.cr.text_extents(text)
        # NOTE: in cairo it seems we have to a apply a small
        # "fudge factor" to computed text height to get reasonable
        # height value
        ht *= 1.2
        return wd, ht

    def setup_pen_brush(self, pen, brush):
        if pen is not None:
            self.set_line(pen.color, alpha=pen.alpha, linewidth=pen.linewidth,
                          style=pen.linestyle)

        if brush is None:
            self.fill = False
        else:
            self.set_fill(brush.color, alpha=brush.alpha)

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0):
        self.cr.save()
        self.cr.translate(cx, cy)
        self.cr.move_to(0, 0)
        self.cr.rotate(-math.radians(rot_deg))
        self.cr.show_text(text)
        self.cr.restore()
        self.cr.new_path()

    def draw_polygon(self, cpoints):
        (cx0, cy0) = cpoints[-1][:2]
        self.cr.move_to(cx0, cy0)
        for cpt in cpoints:
            cx, cy = cpt[:2]
            self.cr.line_to(cx, cy)
        self.cr.close_path()
        self.cr.stroke_preserve()

        self._draw_fill()
        self.cr.new_path()

    def draw_circle(self, cx, cy, cradius):
        self.cr.arc(cx, cy, cradius, 0, 2 * math.pi)
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
        (cx0, cy0) = cpoints[0][:2]
        self.cr.move_to(cx0, cy0)
        for cpt in cpoints[1:]:
            cx, cy = cpt[:2]
            self.cr.line_to(cx, cy)
        self.cr.stroke()
        self.cr.new_path()


class CanvasRenderer(render.StandardPipelineRenderer):

    def __init__(self, viewer):
        render.StandardPipelineRenderer.__init__(self, viewer)

        self.kind = 'cairo'
        if sys.byteorder == 'little':
            self.rgb_order = 'BGRA'
        else:
            self.rgb_order = 'ARGB'
        self.surface = None
        self.surface_arr = None

    def resize(self, dims):
        """Resize our drawing area to encompass a space defined by the
        given dimensions.
        """
        width, height = dims[:2]
        self.logger.debug("renderer reconfigured to %dx%d" % (
            width, height))

        # create cairo surface the size of the window
        #surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        depth = len(self.rgb_order)
        self.surface_arr = np.zeros((height, width, depth), dtype=np.uint8)

        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            width)
        surface = cairo.ImageSurface.create_for_data(self.surface_arr,
                                                     cairo.FORMAT_ARGB32,
                                                     width, height, stride)
        self.surface = surface

        # fill surface with background color;
        # this reduces unwanted garbage in the resizing window
        cr = cairo.Context(self.surface)

        # fill surface with background color
        cr.rectangle(0, 0, width, height)
        r, g, b = self.viewer.get_bg()
        cr.set_source_rgba(r, g, b)
        cr.fill()

        super(CanvasRenderer, self).resize(dims)

    def render_image(self, arr, order, win_coord):
        """Render the image represented by (data) at (win_coord)
        in the pixel space.
        *** internal method-- do not use ***
        """
        self.logger.debug("redraw surface")
        if self.surface is None:
            return

        dst_x, dst_y = win_coord[:2]

        daht, dawd, depth = arr.shape
        self.logger.debug("arr shape is %dx%dx%d" % (dawd, daht, depth))

        cr = cairo.Context(self.surface)
        # TODO: is it really necessary to hang on to this context?
        self.cr = cr

        # fill surface with background color
        imgwin_wd, imgwin_ht = self.viewer.get_window_size()
        cr.rectangle(0, 0, imgwin_wd, imgwin_ht)
        r, g, b = self.viewer.get_bg()
        cr.set_source_rgba(r, g, b)
        cr.fill()

        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            dawd)
        img_surface = cairo.ImageSurface.create_for_data(arr,
                                                         cairo.FORMAT_ARGB32,
                                                         dawd, daht, stride)

        cr.set_source_surface(img_surface, dst_x, dst_y)
        cr.set_operator(cairo.OPERATOR_SOURCE)

        cr.mask_surface(img_surface, dst_x, dst_y)
        cr.fill()

    def get_surface_as_array(self, order=None):
        if self.surface_arr is None:
            raise render.RenderError("No cairo surface defined")

        # adjust according to viewer's needed order
        src_order = self.get_rgb_order()
        return self.reorder(order, self.surface_arr, src_order=src_order)

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.initialize_from_shape(shape, font=False)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        cr.set_font_from_shape(shape)
        return cr.text_extents(shape.text)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.set_font(font.fontname, font.fontsize, color=font.color,
                    alpha=font.alpha)
        return cr.text_extents(text)

# END
