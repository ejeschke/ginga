#
# QtHelp.py -- customized Qt widgets and convenience functions
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import os
import math

import ginga.toolkit

have_pyqt4 = False
have_pyside = False
have_pyqt5 = False
configured = False

toolkit = ginga.toolkit.toolkit

if toolkit in ('qt5', 'choose') and (not configured):
    try:
        from PyQt5 import QtCore
        from PyQt5 import QtWidgets as QtGui
        from PyQt5.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QPainterPath
        from PyQt5.QtCore import QItemSelectionModel
        from PyQt5.QtWidgets import QApplication
        have_pyqt5 = True
        try:
            from PyQt5 import QtWebKit
            from PyQt5.QtWebKitWidgets import QWebView
        except ImportError as e:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyqt5'
        configured = True
    except ImportError as e:
        pass

if toolkit in ('qt4', 'choose') and (not configured):
    try:
        import sip
        for cl in ('QString', 'QVariant'):
            sip.setapi(cl, 2)

        from PyQt4 import QtCore, QtGui
        from PyQt4.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QItemSelectionModel, QPainterPath, QApplication
        have_pyqt4 = True
        try:
            from PyQt4 import QtWebKit
            from PyQt4.QtWebKit import QWebView
        except ImportError:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyqt'
        configured = True
    except ImportError as e:
        pass

if toolkit in ('pyside', 'choose') and (not configured):
    try:
        from PySide import QtCore, QtGui
        from PySide.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
             QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
             QDrag, QItemSelectionModel, QPainterPath
        have_pyside = True
        try:
            from PySide import QtWebKit
            from PySide.QtWebKit import QWebView
        except ImportError:
            pass

        # for Matplotlib
        os.environ['QT_API'] = 'pyside'
        configured = True
    except ImportError:
        pass

if have_pyqt5:
    ginga.toolkit.use('qt5')
elif have_pyqt4:
    ginga.toolkit.use('qt4')
elif have_pyside:
    ginga.toolkit.use('pyside')
else:
    raise ImportError("Failed to import qt4, qt5 or pyside. There may be an issue with the toolkit module or it is not installed")


tabwidget_style = """
QTabWidget::pane { margin: 0px,0px,0px,0px; padding: 0px; }
QMdiSubWindow { margin: 0px; padding: 2px; }
"""


class TopLevel(QtGui.QWidget):

    app = None
    ## def __init__(self, *args, **kwdargs):
    ##     return super(TopLevel, self).__init__(self, *args, **kwdargs)

    def closeEvent(self, event):
        if not (self.app is None):
            self.app.quit()

    def setApp(self, app):
        self.app = app

class ComboBox(QtGui.QComboBox):

    def insert_alpha(self, text):
        index = 0
        while True:
            itemText = self.itemText(index)
            if len(itemText) == 0:
                break
            if itemText > text:
                self.insertItem(index, text)
                return
            index += 1
        self.addItem(text)

    def delete_alpha(self, text):
        index = self.findText(text)
        self.removeItem(index)

    def show_text(self, text):
        index = self.findText(text)
        self.setCurrentIndex(index)

    def append_text(self, text):
        self.addItem(text)

class VBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(VBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QVBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)

class HBox(QtGui.QWidget):
    def __init__(self, *args, **kwdargs):
        super(HBox, self).__init__(*args, **kwdargs)

        layout = QtGui.QHBoxLayout()
        # because of ridiculous defaults
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    def addWidget(self, w, **kwdargs):
        self.layout().addWidget(w, **kwdargs)

    def setSpacing(self, val):
        self.layout().setSpacing(val)


class FileSelection(object):

    def __init__(self, parent_w, action=None):
        # Create a new file selection widget
        self.filew = QtGui.QFileDialog(parent_w, directory=os.curdir)
        #self.filew.setFileMode(QtGui.QFileDialog.ExistingFile)
        self.filew.setViewMode(QtGui.QFileDialog.Detail)

    def popup(self, title, callfn, initialdir=None,
              filename=None):
        self.cb = callfn
        if self.filew.exec_():
            filename = list(map(str, list(self.filew.selectedFiles())))[0]
            self.cb(filename)


def cmap2pixmap(cmap, steps=50):
    """Convert a Ginga colormap into a QPixmap
    """
    inds = numpy.linspace(0, 1, steps)
    n = len(cmap.clst) - 1
    tups = [ cmap.clst[int(x*n)] for x in inds ]
    rgbas = [QColor(int(r * 255), int(g * 255),
                    int(b * 255), 255).rgba() for r, g, b in tups]
    im = QImage(steps, 1, QImage.Format_Indexed8)
    im.setColorTable(rgbas)
    for i in range(steps):
        im.setPixel(i, 0, i)
    im = im.scaled(128, 32)
    pm = QPixmap.fromImage(im)
    return pm

def get_scroll_info(event):
    """
    Returns the (degrees, direction) of a scroll motion Qt event.
    """

    # 15 deg is standard 1-click turn for a wheel mouse
    # delta() usually returns 120
    if have_pyqt5:
        # TODO: use pixelDelta() for better handling on hi-res devices
        point = event.angleDelta()
        delta = math.sqrt(point.x() ** 2 + point.y() ** 2)
        if point.y() < 0:
            delta = -delta
        orientation = QtCore.Qt.Vertical
    else:
        delta = event.delta()
        orientation = event.orientation()
    numDegrees = abs(delta) / 8.0

    direction = None
    if orientation == QtCore.Qt.Horizontal:
        if delta > 0:
            direction = 270.0
        elif delta < 0:
            direction = 90.0
    else:
        if delta > 0:
            direction = 0.0
        elif delta < 0:
            direction = 180.0

    return (numDegrees, direction)

def get_icon(iconpath, size=None):
    image = QImage(iconpath)
    if size is not None:
        qsize = QtCore.QSize(*size)
        image = image.scaled(qsize)
    pixmap = QPixmap.fromImage(image)
    iconw = QIcon(pixmap)
    return iconw

def get_font(font_family, point_size):
    font = QFont(font_family, point_size)
    return font

#END
