#
# FitsImageCanvasQt.py -- A FITS image widget with canvas drawing in Qt
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:48:12 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import FitsImage
import Mixins
import FitsImageQt
from FitsImageCanvasTypesQt import *


class FitsImageCanvasError(FitsImageQt.FitsImageQtError):
    pass

class FitsImageCanvas(Mixins.UIMixin, FitsImageQt.FitsImageZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, render='widget'):
        #super(FitsImageCanvas, self).__init__(logger=logger)
        FitsImageQt.FitsImageZoom.__init__(self, logger=logger,
                                           render=render)
        Mixins.UIMixin.__init__(self)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self, drawCatalog)

        self.setSurface(self)
        self.ui_setActive(True)

        self.drawbutton = 3

    def canvascoords(self, x, y, center=True):
        a, b = self.get_canvas_xy(x, y, center=center)
        return (a, b)

    def redraw_data(self, whence=0):
        super(FitsImageCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()

        
#END
