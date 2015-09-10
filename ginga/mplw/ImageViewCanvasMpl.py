#
# ImageViewCanvasMpl.py -- A FITS image widget with canvas drawing in Matplotlib
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.mplw import ImageViewMpl
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.util.toolbox import ModeIndicator


class ImageViewCanvasError(ImageViewMpl.ImageViewMplError):
    pass

class ImageViewCanvas(ImageViewMpl.ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewMpl.ImageViewZoom.__init__(self, logger=logger,
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

    def redraw_data(self, whence=0):
        super(ImageViewCanvas, self).redraw_data(whence=whence)

        # refresh the matplotlib canvas
        self.figure.canvas.draw()

#END
