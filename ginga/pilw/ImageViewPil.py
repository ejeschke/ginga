#
# ImageViewPil.py -- a backend for Ginga using Python Imaging Library
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from io import BytesIO

import numpy as np
from PIL import Image

from ginga import ImageView

from . import PilHelp  # noqa
from .CanvasRenderPil import CanvasRenderer


class ImageViewPilError(ImageView.ImageViewError):
    pass


class ImageViewPil(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        self.rgb_order = 'RGBA'

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

        # get window contents as a buffer and paste it into the PIL surface
        # TODO: allow greater bit depths when support is better in PIL
        rgb_arr = self.getwin_array(order=self.rgb_order, dtype=np.uint8)
        p_image = Image.fromarray(rgb_arr)

        if p_image.size != canvas.size:
            # window size must have changed out from underneath us!
            width, height = self.get_window_size()
            canvas = Image.new("RGB", (width, height), color=0)
            assert p_image.size == canvas.size, \
                ImageViewPilError("Rendered image does not match window size")
            self.surface = canvas

        canvas.paste(p_image)

    def configure_surface(self, width, height):
        # create PIL surface the size of the window
        # NOTE: pillow needs an RGB image in order to draw with alpha
        # blending, not RGBA
        #self.surface = Image.new(self.rgb_order, (width, height), color=0)
        self.surface = Image.new("RGB", (width, height), color=0)

        # inform the base class about the actual window size
        self.configure(width, height)

    def get_image_as_array(self):
        if self.surface is None:
            raise ImageViewPilError("No PIL surface defined")

        # TODO: could these have changed between the time that self.surface
        # was last updated?
        wd, ht = self.get_window_size()

        # Get PIL surface
        p_image = self.get_surface()
        arr8 = np.array(p_image, dtype=np.uint8)
        arr8 = arr8.reshape((ht, wd, 3))
        return arr8

    def get_rgb_image_as_buffer(self, output=None, format='png', quality=90):
        if self.surface is None:
            raise ImageViewPilError("No PIL surface defined")

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        # Get PIL surface
        p_image = self.get_surface()

        p_image.save(obuf, format=format, quality=quality)
        if output is not None:
            return None
        return obuf

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        buf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return buf.getvalue()

    def update_image(self):
        # subclass implements this method to actually update a widget
        # from the PIL surface
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


class CanvasView(ImageViewPil):
    """This class is defined to provide a non-event handling invisible
    viewer.
    """

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewPil.__init__(self, logger=logger, settings=settings,
                              rgbmap=rgbmap)
        self.defer_redraw = False

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas

    def update_image(self):
        # no widget to update
        pass

    def configure_window(self, width, height):
        return super(CanvasView, self).configure_surface(width, height)

# END
