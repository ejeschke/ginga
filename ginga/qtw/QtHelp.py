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
import glob
import os
import math

import ginga.toolkit
from ginga.util import iohelper

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
             QDrag, QPainterPath, QBrush
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
             QDrag, QItemSelectionModel, QPainterPath, QApplication, \
             QBrush
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
             QDrag, QItemSelectionModel, QPainterPath, QBrush
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
    raise ImportError("Failed to import qt4, qt5 or pyside. There may be an "
                      "issue with the toolkit module or it is not installed")


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
    """Handle Load Image file dialog from File menu."""
    def __init__(self, parent_w):
        self.parent = parent_w
        self.cb = None

    def popup(self, title, callfn, initialdir=None, filename=None):
        """Let user select and load file(s). This allows wildcards and
        extensions, like in FBrowser.

        Parameters
        ----------
        title : str
            Title for the file dialog.

        callfn : func
            Function used to open the file(s).

        initialdir : str or `None`
            Directory for file dialog.

        filename : str
            Filter for file dialog.

        """
        self.cb = callfn
        filenames = QtGui.QFileDialog.getOpenFileNames(
            self.parent, title, initialdir, filename)

        # Special handling for PyQt5, see
        # https://www.reddit.com/r/learnpython/comments/2xhagb/pyqt5_trouble_with_openinggetting_the_name_of_the/
        if ginga.toolkit.get_toolkit() == 'qt5':
            filenames = filenames[0]

        for filename in filenames:

            # Special handling for wildcard or extension.
            # This is similar to open_files() in FBrowser plugin.
            if '*' in filename or '[' in filename:
                info = iohelper.get_fileinfo(filename)
                ext = iohelper.get_hdu_suffix(info.numhdu)
                files = glob.glob(info.filepath)  # Expand wildcard
                paths = ['{0}{1}'.format(f, ext) for f in files]

                # NOTE: Using drag-drop callback here might give QPainter
                # warnings.
                for path in paths:
                    self.cb(path)

            # Normal load
            else:
                self.cb(filename)


class DirectorySelection(object):
    """Handle directory selection dialog."""
    def __init__(self, parent_w):
        self.parent = parent_w
        self.cb = None

    def popup(self, title, callfn, initialdir=None):
        """Let user select a directory.

        Parameters
        ----------
        title : str
            Title for the dialog.

        callfn : func
            Function used to handle selected directory.

        initialdir : str or `None`
            Directory for dialog.

        """
        self.cb = callfn
        dirname = QtGui.QFileDialog.getExistingDirectory(
            self.parent, title, initialdir)
        if dirname:
            self.cb(dirname)


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
