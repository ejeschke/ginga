#
# ImageViewAgg.py -- a backend for Ginga using the aggdraw library
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy
from io import BytesIO

import aggdraw as agg
from . import AggHelp

from ginga import ImageView
from ginga.aggw.CanvasRenderAgg import CanvasRenderer

try:
    import PIL.Image as PILimage
    have_PIL = True
except ImportError:
    have_PIL = False


class ImageViewAggError(ImageView.ImageViewError):
    pass

class ImageViewAgg(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        self._rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

    def get_surface(self):
        return self.surface

    def render_image(self, rgbobj, dst_x, dst_y):
        """Render the image represented by (rgbobj) at dst_x, dst_y
        in the pixel space.
        """
        if self.surface is None:
            return
        canvas = self.surface
        self.logger.debug("redraw surface")

        # get window contents as a buffer and load it into the AGG surface
        rgb_buf = self.getwin_buffer(order=self._rgb_order)
        canvas.fromstring(rgb_buf)

        # for debugging
        #self.save_rgb_image_as_file('/tmp/temp.png', format='png')

    def configure_surface(self, width, height):
        # create agg surface the size of the window
        self.surface = agg.Draw("RGBA", (width, height), 'black')

        # inform the base class about the actual window size
        self.configure(width, height)

    def get_image_as_array(self):
        if self.surface is None:
            raise ImageViewAggError("No AGG surface defined")

        # TODO: could these have changed between the time that self.surface
        # was last updated?
        wd, ht = self.get_window_size()

        # Get agg surface as a numpy array
        surface = self.get_surface()
        arr8 = numpy.fromstring(surface.tostring(), dtype=numpy.uint8)
        arr8 = arr8.reshape((ht, wd, 4))
        return arr8

    def get_image_as_buffer(self, output=None):
        if self.surface is None:
            raise ImageViewAggError("No AGG surface defined")

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        surface = self.get_surface()
        obuf.write(surface.tostring())
        return obuf

    def get_rgb_image_as_buffer(self, output=None, format='png', quality=90):
        if not have_PIL:
            raise ImageViewAggError("Please install PIL to use this method")

        if self.surface is None:
            raise ImageViewAggError("No AGG surface defined")

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        # Get current surface as an array
        arr8 = self.get_image_as_array()

        # make a PIL image
        image = PILimage.fromarray(arr8)

        image.save(obuf, format=format, quality=quality)
        if not (output is None):
            return None
        return obuf.getvalue()

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        buf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return buf

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        if not have_PIL:
            raise ImageViewAggError("Please install PIL to use this method")
        if self.surface is None:
            raise ImageViewAggError("No AGG surface defined")

        with open(filepath, 'w') as out_f:
            self.get_rgb_image_as_buffer(output=out_f, format=format,
                                          quality=quality)
        self.logger.debug("wrote %s file '%s'" % (format, filepath))

    def update_image(self):
        # subclass implements this method to actually update a widget
        # from the agg surface
        self.logger.warning("Subclass should override this method")
        return False

    def set_cursor(self, cursor):
        # subclass implements this method to actually set a defined
        # cursor on a widget
        self.logger.warning("Subclass should override this method")

    def reschedule_redraw(self, time_sec):
        # subclass implements this method to call delayed_redraw() after
        # time_sec
        self.delayed_redraw()

    def get_rgb_order(self):
        return self._rgb_order


#END
