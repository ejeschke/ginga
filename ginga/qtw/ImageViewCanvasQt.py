#
# ImageViewCanvasQt.py -- A FITS image widget with canvas drawing in Qt
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import ImageView, Mixins
from ginga.qtw import ImageViewQt
from ginga.qtw.ImageViewCanvasTypesQt import *


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
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def redraw_data(self, whence=0):
        super(ImageViewCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()

        
#END
