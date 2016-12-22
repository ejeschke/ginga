#
# QtHelp.py -- customized Qt widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import glob
import os
import math

import ginga.toolkit
from ginga.util import iohelper

configured = False

toolkit = ginga.toolkit.toolkit

# if user wants to force a toolkit
if toolkit == 'qt5':
    os.environ['QT_API'] = 'pyqt5'

elif toolkit == 'qt4':
    os.environ['QT_API'] = 'pyqt'

elif toolkit == 'pyside':
    os.environ['QT_API'] = 'pyside'

have_pyqt4 = False
have_pyqt5 = False
have_pyside = False

try:
    from qtpy import QtCore
    from qtpy import QtWidgets as QtGui
    from qtpy.QtGui import QImage, QColor, QFont, QPixmap, QIcon, \
         QCursor, QPainter, QPen, QPolygonF, QPolygon, QTextCursor, \
         QDrag, QPainterPath, QBrush
    from qtpy.QtCore import QItemSelectionModel
    from qtpy.QtWidgets import QApplication
    try:
        from qtpy.QtWebEngineWidgets import QWebEngineView as QWebView
    except ImportError as e:
        pass

    # Let's see what qtpy configured for us...
    from qtpy import PYQT4, PYQT5, PYSIDE
    have_pyqt4 = PYQT4
    have_pyqt5 = PYQT5
    have_pyside = PYSIDE

    configured = True
except ImportError as e:
    pass

if have_pyqt5:
    ginga.toolkit.use('qt5')
    os.environ['QT_API'] = 'pyqt5'
elif have_pyqt4:
    ginga.toolkit.use('qt4')
    os.environ['QT_API'] = 'pyqt'
elif have_pyside:
    ginga.toolkit.use('pyside')
    os.environ['QT_API'] = 'pyside'
else:
    raise ImportError("Failed to configure qt4, qt5 or pyside. Is the 'qtpy' package installed?")


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


class Timer(object):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, ival_sec, expire_cb, data=None):
        """Create a timer set to expire after `ival_sec` and which will
        call the callable `expire_cb` when it expires.
        """
        self.ival_sec = ival_sec
        self.data = data
        self.timer = QtCore.QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(lambda: expire_cb(self))

    def start(self, ival_sec=None):
        """Start the timer.  If `ival_sec` is not None, it should
        specify the time to expiration in seconds.
        """
        if ival_sec is None:
            ival_sec = self.ival_sec

        # QTimer set in milliseconds
        ms = int(ival_sec * 1000.0)
        self.timer.start(ms)

    def set(self, time_sec):
        self.start(ival_sec=time_sec)

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        try:
            self.timer.stop()
        except:
            pass

    clear = cancel


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
        dx, dy = point.x(), point.y()
        delta = math.sqrt(dx ** 2 + dy ** 2)
        if dy < 0:
            delta = -delta

        ang_rad = math.atan2(dy, dx)
        direction = math.degrees(ang_rad) - 90.0
        direction = math.fmod(direction + 360.0, 360.0)

    else:
        delta = event.delta()
        orientation = event.orientation()

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

    num_degrees = abs(delta) / 8.0

    return (num_degrees, direction)


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
