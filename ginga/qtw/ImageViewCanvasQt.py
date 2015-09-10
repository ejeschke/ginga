#
# ImageViewCanvasQt.py -- A FITS image widget with canvas drawing in Qt
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw import ImageViewQt
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.util.toolbox import ModeIndicator

class ImageViewCanvasError(ImageViewQt.ImageViewQtError):
    pass

class ImageViewCanvas(ImageViewQt.ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, settings=None, render=None,
                 rgbmap=None, bindmap=None, bindings=None):
        ImageViewQt.ImageViewZoom.__init__(self, logger=logger,
                                           settings=settings,
                                           render=render,
                                           rgbmap=rgbmap,
                                           bindmap=bindmap,
                                           bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self)

        # we are both a viewer and a canvas
        self.set_canvas(self, private_canvas=self)

        self._mi = ModeIndicator(self)

#END
