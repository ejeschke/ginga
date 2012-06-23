#
# ColorBar.py -- color bar widget
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:48:12 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from PyQt4 import QtGui, QtCore

import Callback
import RGBMap

class ColorBarError(Exception):
    pass

# Create a QWidget widget on which we will draw
class ColorBar(Callback.Callbacks, QtGui.QWidget):
#class ColorBar(QtGui.QWidget):

    def __init__(self, logger, rgbmap=None):
        self.logger = logger
        self.pixmap = None
        
        if not rgbmap:
            rgbmap = RGBMap.RGBMapper()
        self.set_rgbmap(rgbmap)
        
        self._start_x = 0

        QtGui.QWidget.__init__(self)
        Callback.Callbacks.__init__(self)

        # For callbacks
        for name in ('motion', 'scroll'):
            self.enable_callback(name)

        hpolicy = QtGui.QSizePolicy.MinimumExpanding
        vpolicy = QtGui.QSizePolicy.MinimumExpanding
        self.setSizePolicy(hpolicy, vpolicy)


    def get_rgbmap(self):
        return self.rgbmap
        
    def set_rgbmap(self, rgbmap):
        self.rgbmap = rgbmap
        # TODO
        #rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw()

    # TODO: deprecate these two?
    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)

    def get_size(self):
        rect = self.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        #print "x1,y1=%d,%d x2,y2=%d,%d" % (x1, y1, x2, y2)
        width = x2 - x1
        height = y2 - y1
        return width, height
    
    def resizeEvent(self, event):
        width, height = self.get_size()
        #print "making pixmap of %dx%d" % (width, height)
        pixmap = QtGui.QPixmap(width, height)
        #pixmap.fill(QtGui.QColor("black"))
        self.pixmap = pixmap

        self.redraw()
       
    def paintEvent(self, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        if not self.pixmap:
            return
        rect = event.rect()
        self.repaint(rect)

    def sizeHint(self):
        return QtCore.QSize(100, 16)
    
    def repaint(self, rect):
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        # redraw the screen from backing pixmap
        #print "copying pixmap to widget"
        painter = QtGui.QPainter(self)
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)
        
    def setup_cr(self):
        cr = QtGui.QPainter(self.pixmap)
        pen = QtGui.QPen()
        pen.setWidth(1)
        cr.setPen(pen)
        return cr


    def _draw(self, cr):
        width, height = self.get_size()
        #print "window size is %d,%d" % (width, height)

        x1 = 0; x2 = width
        clr_wd = width // 256
        rem_px = x2 - (clr_wd * 256)
        if rem_px > 0:
            ival = 256 // rem_px
        else:
            ival = 0
        clr_ht = height
        #print "clr is %dx%d width=%d rem=%d ival=%d" % (
        #    width, height, clr_wd, rem_px, ival)

        j = ival; off = 0
        for i in range(256):
            
            wd = clr_wd    
            if rem_px > 0:
                j -= 1
                if j == 0:
                    rem_px -= 1
                    j = ival
                    wd += 1
            x = off

            (r, g, b) = self.rgbmap.get_rgbval(i)

            color = QtGui.QColor(r, g, b)
            cr.fillRect(QtCore.QRect(x, 0, wd, clr_ht), color)
            off += wd

    def draw(self):
        cr = self.setup_cr()
        self._draw(cr)

    def redraw(self):
        if not self.pixmap:
            return
        # redraw pixmap
        self.draw()

        # and copy to window
        ## rect = self.geometry()
        ## self.repaint(rect)
        self.update()
        
    def shift_colormap(self, pct):
        if pct > 0.0:
            self.rgbmap.rshift(pct)
        else:
            self.rgbmap.lshift(math.fabs(pct))

        self.redraw()

    def rgbmap_cb(self, rgbmap):
        self.redraw()
    
    def mousePressEvent(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        if buttons & QtCore.Qt.LeftButton:
            self._start_x = x
                
    def mouseReleaseEvent(self, event):
        # note: for mouseRelease this needs to be button(), not buttons()!
        buttons = event.button()
        x, y = event.x(), event.y()
        if buttons & QtCore.Qt.LeftButton:
            dx = x - self._start_x
            wd, ht = self.get_size()
            pct = float(dx) / float(wd)
            #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
            self.shift_colormap(pct)

        elif buttons & QtCore.Qt.RightButton:
            #print "resetting cmap!"
            self.rgbmap.reset_cmap()

    def mouseMoveEvent(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        if buttons & QtCore.Qt.LeftButton:
            dx = x - self._start_x
            wd, ht = self.get_size()
            pct = float(dx) / float(wd)
            #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
            self.shift_colormap(pct)
        
        self.make_callback('motion', event)

    def wheelEvent(self, event):
        delta = event.delta()
        direction = None
        if delta > 0:
            direction = 'up'
        elif delta < 0:
            direction = 'down'
            
        self.make_callback('scroll', event)

#END
