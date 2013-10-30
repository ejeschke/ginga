#
# ImageViewCanvasGtk.py -- A FITS image widget with canvas drawing in Gtk
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga import ImageView
from ginga import Mixins
from ginga.gtkw import ImageViewGtk
from ginga.gtkw.ImageViewCanvasTypesGtk import *

    
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
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def redraw_data(self, whence=0):
        super(ImageViewCanvas, self).redraw_data(whence=whence)

        if not self.surface:
            return
        self.draw()


#END
