#
# GingaCanvasQt.py -- classes for the display of FITS files in
#                             Matplotlib FigureCanvas
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as QtFigureCanvas
from ginga.qtw.QtHelp import QtGui, QtCore


def setup_Qt(widget, fitsimage):

    def resizeEvent(*args):
        print args
        rect = widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        #print "RESIZE %dx%d" % (width, height)
        if fitsimage != None:
            fitsimage.configure(width, height)
        
    widget.setFocusPolicy(QtCore.Qt.FocusPolicy(
        QtCore.Qt.TabFocus |
        QtCore.Qt.ClickFocus |
        QtCore.Qt.StrongFocus |
        QtCore.Qt.WheelFocus))
    widget.setMouseTracking(True)
    widget.setAcceptDrops(True)

    # Matplotlib has a bug where resize events are not reported
    widget.connect(widget, QtCore.SIGNAL('resizeEvent()'),
                   resizeEvent)


class FigureCanvas(QtFigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    """
    def __init__(self, fig, parent=None, width=5, height=4, dpi=100):
        QtFigureCanvas.__init__(self, fig)
        
        self.fitsimage = None
        
        setup_Qt(self, None)

        self.setParent(parent)
        
        FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        
    def resizeEvent(self, event):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        if self.fitsimage != None:
            #print "RESIZE %dx%d" % (width, height)
            self.fitsimage.configure(width, height)
        
        return super(FigureCanvas, self).resizeEvent(event)

    def sizeHint(self):
        width, height = 300, 300
        if self.fitsimage != None:
            width, height = self.fitsimage.get_desired_size()
        return QtCore.QSize(width, height)

    def set_fitsimage(self, fitsimage):
        self.fitsimage = fitsimage
        
#END
