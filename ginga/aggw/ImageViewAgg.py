#
# ImageViewAgg.py -- a backend for Ginga using the aggdraw library
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga import ImageView
from ginga.aggw.CanvasRenderAgg import CanvasRenderer


class ImageViewAgg(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap,
                                         settings=settings)

        self.surface = None
        self.rgb_order = 'RGBA'

        self.renderer = CanvasRenderer(self)

    def update_widget(self):
        pass

    def configure_window(self, width, height):
        self.configure(width, height)


class CanvasView(ImageViewAgg):
    """This class is defined to provide a non-event handling invisible
    viewer.
    """

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        # NOTE: bindmap, bindings are ignored
        ImageViewAgg.__init__(self, logger=logger, settings=settings,
                              rgbmap=rgbmap)
        self.defer_redraw = False

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas

# END
