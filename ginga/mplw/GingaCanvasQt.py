#
# GingaCanvasQt.py -- classes for the display of FITS files in
#                             Matplotlib FigureCanvas
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from ginga.qtw.QtHelp import QtGui, QtCore

class GingaCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    """
    def __init__(self, fig, parent=None, width=5, height=4, dpi=100):
        FigureCanvas.__init__(self, fig)
        
        self.fitsimage = None
        
        # For message drawing
        self._msg_timer = QtCore.QTimer()

        # For optomized redrawing
        self._defer_timer = QtCore.QTimer()
        self._defer_timer.setSingleShot(True)

        w = self
        w.setFocusPolicy(QtCore.Qt.FocusPolicy(
            QtCore.Qt.TabFocus |
            QtCore.Qt.ClickFocus |
            QtCore.Qt.StrongFocus |
            QtCore.Qt.WheelFocus))
        w.setMouseTracking(True)
        w.setAcceptDrops(True)

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
        
        return super(GingaCanvas, self).resizeEvent(event)

    def sizeHint(self):
        width, height = 300, 300
        if self.fitsimage != None:
            width, height = self.fitsimage.get_desired_size()
        return QtCore.QSize(width, height)

    def set_fitsimage(self, fitsimage):
        self.fitsimage = fitsimage
        
        self._msg_timer.timeout.connect(fitsimage.onscreen_message_off)
        self._defer_timer.timeout.connect(fitsimage.delayed_redraw)

    def onscreen_message(self, text, delay=None, redraw=True):
        try:
            self._msg_timer.stop()
        except:
            pass

        if self.fitsimage != None:
            self.fitsimage.message = text
            if redraw:
                self.fitsimage.redraw(whence=3)

            if delay:
                ms = int(delay * 1000.0)
                self._msg_timer.start(ms)

    def reschedule_redraw(self, time_sec):
        try:
            self._defer_timer.stop()
        except:
            pass

        time_ms = int(time_sec * 1000)
        self._defer_timer.start(time_ms)


#END
