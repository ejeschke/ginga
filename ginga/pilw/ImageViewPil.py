#
# ImageViewPil.py -- a backend for Ginga using Python Imaging Library
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

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

        # NOTE: pillow needs an RGB image in order to draw with alpha
        # blending, not RGBA
        self.rgb_order = 'RGB'

        self.renderer = CanvasRenderer(self)

    def reschedule_redraw(self, time_sec):
        # subclass implements this method to call delayed_redraw() after
        # time_sec
        self.delayed_redraw()

    def update_widget(self):
        # no widget to update
        pass

    def configure_window(self, width, height):
        self.configure(width, height)


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

# END
