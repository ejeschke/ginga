#
# ImageViewCairo.py -- classes for the display of Ginga canvases
#                         in Cairo surfaces
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys
import numpy as np
from io import BytesIO

import cairo

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
            self.rgb_order = 'BGRA'
            self._alpha_idx = 3
        else:
            self.rgb_order = 'ARGB'
            self._alpha_idx = 0

        self.renderer = CanvasRenderer(self)

        self.cr = None

    def _render_offscreen(self, surface, data, dst_x, dst_y,
                          width, height):
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        cr = cairo.Context(surface)
        self.cr = cr

        # fill surface with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        cr.rectangle(0, 0, imgwin_wd, imgwin_ht)
        r, g, b = self.get_bg()
        cr.set_source_rgba(r, g, b)
        cr.fill()

        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            width)

        img_surface = cairo.ImageSurface.create_for_data(data,
                                                         cairo.FORMAT_ARGB32,
                                                         dawd, daht, stride)

        cr.set_source_surface(img_surface, dst_x, dst_y)
        cr.set_operator(cairo.OPERATOR_SOURCE)

        cr.mask_surface(img_surface, dst_x, dst_y)
        cr.fill()

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
        arr = rgbobj.get_array(self.rgb_order)

        (height, width) = arr.shape[:2]
        return self._render_offscreen(self.surface, arr, dst_x, dst_y,
                                      width, height)

    def configure_surface(self, width, height):
        #surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        arr8 = np.zeros(height * width * 4, dtype=np.uint8)

        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32,
                                                            width)
        surface = cairo.ImageSurface.create_for_data(arr8,
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
        self.surface.write_to_png(ibuf)
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

    ## def pix2canvas(self, pt):
    ##     x, y = pt
    ##     x, y = self.cr.device_to_user(x, y)
    ##     return (x, y, 0)

    ## def canvas2pix(self, pt):
    ##     x, y, z = pt
    ##     x, y = self.cr.user_to_device(x, y)
    ##     return (x, y)


# END
