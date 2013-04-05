#
# FitsImageCanvasGtk.py -- A FITS image widget with canvas drawing in Gtk
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import FitsImage
import Mixins
import FitsImageGtk
from FitsImageCanvasTypesGtk import *

    
class FitsImageCanvasError(FitsImageGtk.FitsImageGtkError):
    pass

class FitsImageCanvas(FitsImageGtk.FitsImageZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, settings=None):
        FitsImageGtk.FitsImageZoom.__init__(self, logger=logger,
                                            settings=settings)
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
        super(FitsImageCanvas, self).redraw_data(whence=whence)

        if not self.surface:
            return
        self.draw()


#END
