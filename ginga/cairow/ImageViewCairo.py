#
# ImageViewCairo.py -- classes for the display of Ginga canvases
#                         in Cairo surfaces
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys, re
import cairo
import numpy
import threading
import math
from io import BytesIO

from ginga import ImageView
from ginga.cairow.CanvasRenderCairo import CanvasRenderer

class ImageViewCairoError(ImageView.ImageViewError):
    pass

class ImageViewCairo(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        self.dst_surface = None

        if sys.byteorder == 'little':
            self._rgb_order = 'BGRA'
            self._alpha_idx = 3
        else:
            self._rgb_order = 'ARGB'
            self._alpha_idx = 0

        self.renderer = CanvasRenderer(self)

        self.cr = None
        self.message = None

        self.t_.setDefaults(show_pan_position=False,
                            onscreen_ff='Sans Serif')


    def _render_offscreen(self, surface, data, dst_x, dst_y,
                          width, height):
        # NOTE [A]
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        cr = cairo.Context(surface)
        self.cr = cr

        # fill surface with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        cr.rectangle(0, 0, imgwin_wd, imgwin_ht)
        r, g, b = self.get_bg()
        cr.set_source_rgba(r, g, b)
        #cr.set_operator(cairo.OPERATOR_OVER)
        cr.fill()

        ## arr8 = data.astype(numpy.uint8).flatten()
        arr8 = data

        ## stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24,
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            width)

        img_surface = cairo.ImageSurface.create_for_data(arr8,
                                                         #cairo.FORMAT_RGB24,
                                                         cairo.FORMAT_ARGB32,
                                                         dawd, daht, stride)

        cr.set_source_surface(img_surface, dst_x, dst_y)
        cr.set_operator(cairo.OPERATOR_SOURCE)

        cr.mask_surface(img_surface, dst_x, dst_y)
        #cr.rectangle(dst_x, dst_y, dawd, daht)
        cr.fill()

        # Draw a cross in the center of the window in debug mode
        if self.t_['show_pan_position']:
            cr.set_source_rgb(1.0, 0.0, 0.0)
            cr.set_line_width(1)
            ctr_x, ctr_y = self.get_center()
            cr.move_to(ctr_x - 10, ctr_y)
            cr.line_to(ctr_x + 10, ctr_y)
            cr.move_to(ctr_x, ctr_y - 10)
            cr.line_to(ctr_x, ctr_y + 10)
            cr.close_path()
            cr.stroke_preserve()

        # render self.message
        if self.message:
            self.draw_message(cr, imgwin_wd, imgwin_ht,
                              self.message)


    def draw_message(self, cr, width, height, message):
        r, g, b = self.img_fg
        #cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.set_source_rgb(r, g, b)
        cr.select_font_face(self.t_['onscreen_ff'])
        cr.set_font_size(24.0)
        a, b, wd, ht, i, j = cr.text_extents(message)
        y = ((height // 3) * 2) - (ht // 2)
        x = (width // 2) - (wd // 2)
        cr.move_to(x, y)
        cr.show_text(message)

    def get_offscreen_context(self):
        if self.surface is None:
            raise ImageViewCairoError("No offscreen surface defined")
        cr = cairo.Context(self.surface)
        return cr

    def get_offscreen_surface(self):
        return self.surface

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        """
        self.logger.debug("redraw surface")
        if self.surface is None:
            return

        # Prepare array for Cairo rendering
        arr = rgbobj.get_array(self._rgb_order)

        (height, width) = arr.shape[:2]
        return self._render_offscreen(self.surface, arr, dst_x, dst_y,
                                      width, height)

    def configure_surface(self, width, height):
        arr8 = numpy.zeros(height*width*4, dtype=numpy.uint8)
        #stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24,
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            width)

        surface = cairo.ImageSurface.create_for_data(arr8,
                                                     #cairo.FORMAT_RGB24,
                                                     cairo.FORMAT_ARGB32,
                                                     width, height, stride)
        self.surface = surface
        self.configure(width, height)

    def save_image_as_surface(self, surface):
        try:
            self.dst_surface = surface
            self.redraw()

        finally:
            self.dst_surface = None

    def get_png_image_as_buffer(self, output=None):
        ibuf = output
        if ibuf is None:
            ibuf = BytesIO()
        qimg = self.surface.write_to_png(ibuf)
        return ibuf

    def update_image(self):
        if not self.surface:
            return
        if not self.dst_surface:
            #raise ImageViewCairoError("Please set up the output destination")
            self.logger.error("Please set up the output destination")
            return

        cr = cairo.Context(self.dst_surface)

        self.logger.debug("updating destination cairo surface")
        # redraw the surface from backing surface
        cr.set_source_surface(self.surface, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def set_cursor(self, cursor):
        pass

    def define_cursor(self, ctype, cursor):
        pass

    def get_cursor(self, ctype):
        return self.cursor[ctype]

    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])

    def get_rgb_order(self):
        return self._rgb_order

    def onscreen_message(self, text, delay=None):
        pass

    def show_pan_mark(self, tf):
        self.t_.set(show_pan_position=tf)
        self.redraw(whence=3)

    def pix2canvas(self, x, y):
        x, y = self.cr.device_to_user(x, y)
        return (x, y)

    def canvas2pix(self, x, y):
        x, y = self.cr.user_to_device(x, y)
        return (x, y)



#END
