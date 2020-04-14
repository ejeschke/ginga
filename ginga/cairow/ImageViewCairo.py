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
        else:
            self.rgb_order = 'ARGB'

        self.renderer = CanvasRenderer(self)
        self.cr = None

    def configure_surface(self, width, height):
        self.renderer.resize((width, height))

        #surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        depth = len(self.rgb_order)
        arr8 = np.zeros((height, width, depth), dtype=np.uint8)

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

    def update_widget(self):
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


# END
