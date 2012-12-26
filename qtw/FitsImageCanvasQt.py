#
# FitsImageCanvasQt.py -- A FITS image widget with canvas drawing in Qt
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Wed Dec 26 13:00:56 HST 2012
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

    def __init__(self, logger=None, render=None):
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

    def canvascoords(self, data_x, data_y, center=True):
        # data->canvas space coordinate conversion
        x, y = self.get_canvas_xy(data_x, data_y, center=center)
        return (x, y)

    def redraw_data(self, whence=0):
        super(FitsImageCanvas, self).redraw_data(whence=whence)

        if not self.pixmap:
            return
        self.draw()

        
#END
