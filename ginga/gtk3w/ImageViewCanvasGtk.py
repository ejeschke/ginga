#
# ImageViewCanvasGtk.py -- A FITS image widget with canvas drawing in Gtk
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtk3w import ImageViewGtk
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.util.toolbox import ModeIndicator


class ImageViewCanvasError(ImageViewGtk.ImageViewGtkError):
    pass

class ImageViewCanvas(ImageViewGtk.ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewGtk.ImageViewZoom.__init__(self, logger=logger,
                                            rgbmap=rgbmap,
                                            settings=settings,
                                            bindmap=bindmap,
                                            bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self)

        # we are both a viewer and a canvas
        self.set_canvas(self, private_canvas=self)

        self._mi = ModeIndicator(self)

#END
