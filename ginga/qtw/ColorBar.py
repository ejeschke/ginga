#
# ColorBar.py -- color bar widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import math

from ginga.qtw.QtHelp import QtGui, QtCore, QFont, QColor, QPainter, \
     QPen, QPixmap, get_scroll_info

from ginga.misc import Callback
from ginga import RGBMap

class ColorBarError(Exception):
    pass

# Create a QWidget widget on which we will draw
class ColorBar(Callback.Callbacks, QtGui.QWidget):

    def __init__(self, logger, rgbmap=None, link=False):
        QtGui.QWidget.__init__(self)
        Callback.Callbacks.__init__(self)

        self.logger = logger
        self.pixmap = None
        self.link_rgbmap = link

        if not rgbmap:
            rgbmap = RGBMap.RGBMapper(logger)
        self.set_rgbmap(rgbmap)

        self._start_x = 0
        # for drawing range
        self.t_showrange = True
        self.t_font = 'Sans Serif'
        self.t_fontsize = 8
        self.t_spacing = 40
        self.loval = 0.0
        self.hival = 0.0
        self._interval = {}
        self._avg_pixels_per_range_num = 70

        # For callbacks
        for name in ('motion', 'scroll'):
            self.enable_callback(name)

        hpolicy = QtGui.QSizePolicy.MinimumExpanding
        vpolicy = QtGui.QSizePolicy.MinimumExpanding
        self.setSizePolicy(hpolicy, vpolicy)

        # in order to generate mouse events with no buttons down
        self.setMouseTracking(True)

    def get_rgbmap(self):
        return self.rgbmap

    def set_rgbmap(self, rgbmap):
        self.rgbmap = rgbmap
        # TODO: figure out if we can get rid of this link option
        if self.link_rgbmap:
            rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw()

    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)
        self.redraw()

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)
        self.redraw()

    def set_range(self, loval, hival):
        self.loval = float(loval)
        self.hival = float(hival)
        # Calculate reasonable spacing for range numbers
        if self.pixmap is not None:
            cr = self.setup_cr()
            text = "%.4g" % (hival)
            rect = cr.boundingRect(0, 0, 1000, 1000, 0, text)
            x1, y1, x2, y2 = rect.getCoords()
            _wd = x2 - x1
            _ht = y2 - y1
            self._avg_pixels_per_range_num = self.t_spacing + _wd
            # dereference this painter or we get an error redrawing
            cr = None

            if self.t_showrange:
                self.redraw()

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
        pixmap = QPixmap(width, height)
        #pixmap.fill(QColor("black"))
        self.pixmap = pixmap
        # calculate intervals for range numbers
        nums = max(int(width // self._avg_pixels_per_range_num), 1)
        spacing = 256 // nums
        self._interval = {}
        for i in range(nums):
            self._interval[i*spacing] = True
        self.logger.debug("nums=%d spacing=%d intervals=%s" % (
            nums, spacing, self._interval))

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
        painter = QPainter(self)
        rect = QtCore.QRect(x1, y1, width, height)
        painter.drawPixmap(rect, self.pixmap, rect)

    def setup_cr(self):
        cr = QPainter(self.pixmap)
        pen = QPen()
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

        dist = self.rgbmap.get_dist()

        j = ival; off = 0
        range_pts = []
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

            color = QColor(r, g, b)
            cr.fillRect(QtCore.QRect(x, 0, wd, clr_ht), color)

            # Draw range scale if we are supposed to
            if self.t_showrange and i in self._interval:
                #cb_pct = float(i) / 256.0
                cb_pct = float(x) / width
                # get inverse of distribution function and calculate value
                # at this position
                rng_pct = dist.get_dist_pct(cb_pct)
                val = float(self.loval + (rng_pct * (self.hival - self.loval)))
                text = "%.4g" % (val)
                rect = cr.boundingRect(0, 0, 1000, 1000, 0, text)
                x1, y1, x2, y2 = rect.getCoords()
                _wd = x2 - x1
                _ht = y2 - y1
                # override?
                _ht = 14

                rx = x
                ry = _ht - 2
                range_pts.append((rx, ry, text))

            off += wd

        # draw range
        pen = cr.pen()
        cr.setFont(QFont(self.t_font, pointSize=self.t_fontsize))
        color = QColor()
        color.setRgbF(0.0, 0.0, 0.0)
        pen.setColor(color)
        cr.setPen(pen)

        for (x, y, text) in range_pts:
            # tick
            cr.drawLine(x, 0, x, 2)
            # number
            cr.drawText(x, y, text)


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
        self.rgbmap.set_sarr(self._sarr, callback=False)
        self.rgbmap.shift(pct)
        self.redraw()

    def stretch_colormap(self, pct):
        self.rgbmap.stretch(pct)
        self.redraw()

    def rgbmap_cb(self, rgbmap):
        self.redraw()

    def mousePressEvent(self, event):
        buttons = event.buttons()
        x, y = event.x(), event.y()

        if buttons & QtCore.Qt.LeftButton:
            self._start_x = x
            sarr = self.rgbmap.get_sarr()
            self._sarr = sarr.copy()

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
            return

        dist = self.rgbmap.get_dist()
        width, height = self.get_size()
        pct = float(x) / float(width)
        rng_pct = dist.get_dist_pct(pct)
        value = float(self.loval + (rng_pct * (self.hival - self.loval)))
        self.make_callback('motion', value, event)

    def wheelEvent(self, event):
        num_degrees, direction = get_scroll_info(event)

        if (direction < 90.0) or (direction > 270.0):
            # up
            scale_factor = 1.1
        else:
            # not up!
            scale_factor = 0.9

        self.stretch_colormap(scale_factor)

        self.make_callback('scroll', event)

#END
