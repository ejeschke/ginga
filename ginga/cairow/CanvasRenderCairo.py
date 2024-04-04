#
# CanvasRenderCairo.py -- for rendering into a ImageViewCairo widget
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys

import numpy as np
import cairo

from ginga.canvas import render
# force registration of all canvas types
import ginga.canvas.types.all  # noqa

from . import CairoHelp


class RenderContext(render.RenderContextBase):

    def __init__(self, renderer, viewer, surface):
        render.RenderContextBase.__init__(self, renderer, viewer)

        self.ctx = cairo.Context(surface)
        # set up antialiasing
        fo = cairo.FontOptions()
        fo.set_antialias(cairo.ANTIALIAS_DEFAULT)
        self.ctx.set_font_options(fo)

        # special scaling for Cairo text drawing to normalize it relative
        # to other backends
        self._font_scale_factor = 1.75

    def setup_line(self, line):
        r, g, b, a = line._color_4tup
        self.ctx.set_source_rgba(r, g, b, a)
        self.ctx.set_line_width(line.linewidth)
        if line.linestyle == 'dash':
            self.ctx.set_dash([3.0, 4.0, 6.0, 4.0], 5.0)

    def setup_fill(self, fill):
        r, g, b, a = fill._color_4tup
        self.ctx.set_source_rgba(r, g, b, a)

    def setup_font(self, font):
        self.ctx.select_font_face(font.fontname)
        self.ctx.set_font_size(font.fontsize)

    def text_extents(self, text, font=None):
        if font is None:
            font = self.font
        wd, ht = CairoHelp.text_size(text, font)
        return wd, ht

    ##### DRAWING OPERATIONS #####

    def draw_image(self, cvs_img, cpoints, rgb_arr, whence, order='RGBA'):
        # no-op for this renderer
        pass

    def draw_text(self, cx, cy, text, rot_deg=0.0, font=None, line=None,
                  fill=None):
        self.ctx.save()
        self.ctx.translate(cx, cy)
        self.ctx.move_to(0, 0)
        self.ctx.rotate(-np.radians(rot_deg))
        if font is not None:
            self.setup_font(font)
        if line is not None:
            self.setup_line(line)
            self.ctx.text_path(text)
            self.ctx.stroke_preserve()
            if fill is not None:
                self.setup_fill(fill)
                self.ctx.fill()
        else:
            # NOTE: show_text() is more efficient if we have a lot of text,
            # according to Cairo docs, so use it instead if we are not
            # stroking a path outline
            if fill is not None:
                self.setup_fill(fill)
                self.ctx.show_text(text)

        self.ctx.restore()
        self.ctx.new_path()

    def draw_polygon(self, cpoints, line=None, fill=None):
        (cx0, cy0) = cpoints[-1][:2]
        self.ctx.move_to(cx0, cy0)
        for cpt in cpoints:
            cx, cy = cpt[:2]
            self.ctx.line_to(cx, cy)
        self.ctx.close_path()
        if line is not None:
            self.setup_line(line)
            self.ctx.stroke_preserve()
        if fill is not None:
            self.setup_fill(fill)
            self.ctx.fill()
        self.ctx.new_path()

    def draw_circle(self, cx, cy, cradius, line=None, fill=None):
        self.ctx.arc(cx, cy, cradius, 0, 2 * np.pi)
        if line is not None:
            self.setup_line(line)
            self.ctx.stroke_preserve()
        if fill is not None:
            self.setup_fill(fill)
            self.ctx.fill()
        self.ctx.new_path()

    def draw_bezier_curve(self, cp, line=None):
        self.ctx.move_to(cp[0][0], cp[0][1])
        self.ctx.curve_to(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])

        if line is not None:
            self.setup_line(line)
            self.ctx.stroke()
        self.ctx.new_path()

    def draw_ellipse_bezier(self, cp, line=None, fill=None):
        # draw 4 bezier curves to make the ellipse
        self.ctx.move_to(cp[0][0], cp[0][1])
        self.ctx.curve_to(cp[1][0], cp[1][1], cp[2][0], cp[2][1], cp[3][0], cp[3][1])
        self.ctx.curve_to(cp[4][0], cp[4][1], cp[5][0], cp[5][1], cp[6][0], cp[6][1])
        self.ctx.curve_to(cp[7][0], cp[7][1], cp[8][0], cp[8][1], cp[9][0], cp[9][1])
        self.ctx.curve_to(cp[10][0], cp[10][1], cp[11][0], cp[11][1], cp[12][0], cp[12][1])
        if line is not None:
            self.setup_line(line)
            self.ctx.stroke_preserve()

        if fill is not None:
            self.setup_fill(fill)
            self.ctx.fill()
        self.ctx.new_path()

    def draw_line(self, cx1, cy1, cx2, cy2, line=None):
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.move_to(cx1, cy1)
        self.ctx.line_to(cx2, cy2)
        if line is not None:
            self.setup_line(line)
            self.ctx.stroke()
        self.ctx.new_path()

    def draw_path(self, cpoints, line=None):
        (cx0, cy0) = cpoints[0][:2]
        self.ctx.move_to(cx0, cy0)
        for cpt in cpoints[1:]:
            cx, cy = cpt[:2]
            self.ctx.line_to(cx, cy)
        if line is not None:
            self.setup_line(line)
            self.ctx.stroke()
        self.ctx.new_path()


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
        ctx = cairo.Context(self.surface)

        # fill surface with background color
        ctx.rectangle(0, 0, width, height)
        r, g, b = self.viewer.get_bg()
        ctx.set_source_rgba(r, g, b)
        ctx.fill()

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

        ctx = cairo.Context(self.surface)
        # TODO: is it really necessary to hang on to this context?
        self.ctx = ctx

        # fill surface with background color
        imgwin_wd, imgwin_ht = self.viewer.get_window_size()
        ctx.rectangle(0, 0, imgwin_wd, imgwin_ht)
        r, g, b = self.viewer.get_bg()
        ctx.set_source_rgba(r, g, b)
        ctx.fill()

        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            dawd)
        img_surface = cairo.ImageSurface.create_for_data(arr,
                                                         cairo.FORMAT_ARGB32,
                                                         dawd, daht, stride)

        ctx.set_source_surface(img_surface, dst_x, dst_y)
        ctx.set_operator(cairo.OPERATOR_SOURCE)

        ctx.mask_surface(img_surface, dst_x, dst_y)
        ctx.fill()

    def get_surface_as_array(self, order=None):
        if self.surface_arr is None:
            raise render.RenderError("No cairo surface defined")

        # adjust according to viewer's needed order
        src_order = self.get_rgb_order()
        return self.reorder(order, self.surface_arr, src_order=src_order)

    def setup_cr(self, shape):
        cr = RenderContext(self, self.viewer, self.surface)
        return cr

    def get_dimensions(self, shape):
        cr = self.setup_cr(shape)
        font = cr.get_font_from_shape(shape)
        return cr.text_extents(shape.text, font=font)

    def text_extents(self, text, font):
        cr = RenderContext(self, self.viewer, self.surface)
        cr.setup_font(font)
        return cr.text_extents(text)

# END
