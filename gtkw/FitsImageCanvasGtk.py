#
# FitsImageCanvasGtk.py -- A FITS image widget with canvas drawing in Gtk
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:41:31 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import FitsImage
import Mixins
import FitsImageGtk
from FitsImageCanvasTypesGtk import *

    
class FitsImageCanvasError(FitsImageGtk.FitsImageGtkError):
    pass

class FitsImageCanvas(Mixins.UIMixin, FitsImageGtk.FitsImageZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None):
        FitsImageGtk.FitsImageZoom.__init__(self, logger=logger)
        Mixins.UIMixin.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

    def canvascoords(self, x, y, center=True):
        a, b = self.get_canvas_xy(x, y, center=center)
        return (a, b)

    def redraw_data(self, whence=0):
        super(FitsImageCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()


#END
