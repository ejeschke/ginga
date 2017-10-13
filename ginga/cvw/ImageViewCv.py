#
# ImageViewCv.py -- a backend for Ginga using OpenCv surfaces
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import numpy
from io import BytesIO

import cv2  # noqa

from ginga import ImageView
from ginga.cvw.CanvasRenderCv import CanvasRenderer

try:
    import PIL.Image as PILimage
    have_PIL = True
except ImportError:
    have_PIL = False


class ImageViewCvError(ImageView.ImageViewError):
    pass


class ImageViewCv(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        # According to OpenCV documentation:
        # "If you are using your own image rendering and I/O functions,
        # you can use any channel ordering. The drawing functions process
        # each channel independently and do not depend on the channel
        # order or even on the used color space."
        #self.rgb_order = 'BGRA'
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

        # get window contents as an array and store it into the CV surface
        rgb_arr = self.getwin_array(order=self.rgb_order)
        # TODO: is there a faster way to copy this array in?
        canvas[:, :, :] = rgb_arr

        # for debugging
        #self.save_rgb_image_as_file('/tmp/temp.png', format='png')

    def configure_surface(self, width, height):
        # create cv surface the size of the window
        # (cv just uses numpy arrays!)
        depth = len(self.rgb_order)
        self.surface = numpy.zeros((height, width, depth), numpy.uint8)

        # inform the base class about the actual window size
        self.configure(width, height)

    def get_image_as_array(self):
        if self.surface is None:
            raise ImageViewCvError("No OpenCv surface defined")

        arr8 = self.get_surface()
        return numpy.copy(arr8)

    def get_rgb_image_as_buffer(self, output=None, format='png', quality=90):
        if not have_PIL:
            raise ImageViewCvError("Please install PIL to use this method")

        if self.surface is None:
            raise ImageViewCvError("No CV surface defined")

        obuf = output
        if obuf is None:
            obuf = BytesIO()

        # make a PIL image
        image = PILimage.fromarray(self.surface)

        image.save(obuf, format=format, quality=quality)
        return obuf

    def get_rgb_image_as_bytes(self, format='png', quality=90):
        buf = self.get_rgb_image_as_buffer(format=format, quality=quality)
        return buf.getvalue()

    def update_image(self):
        # subclass implements this method to actually update a widget
        # from the cv surface
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


class CanvasView(ImageViewCv):
    """This class is defined to provide a non-event handling invisible
    viewer.
    """

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewCv.__init__(self, logger=logger, settings=settings,
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

#END
