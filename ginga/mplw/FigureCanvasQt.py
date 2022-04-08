#
# GingaCanvasQt.py -- classes for the display of FITS files in
#                             Matplotlib FigureCanvas
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.toolkit import toolkit
if toolkit in ('qt6', 'pyside6'):
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as QtFigureCanvas
else:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as QtFigureCanvas


def setup_Qt(widget, viewer):

    _resizeEvent = widget.resizeEvent

    def resizeEvent(*args):
        rect = widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1

        if viewer is not None:
            viewer.configure_window(width, height)

        _resizeEvent(*args)

    widget.setFocusPolicy(QtCore.Qt.FocusPolicy(
        QtCore.Qt.TabFocus |
        QtCore.Qt.ClickFocus |
        QtCore.Qt.StrongFocus |
        QtCore.Qt.WheelFocus))
    widget.setMouseTracking(True)
    widget.setAcceptDrops(True)

    # Matplotlib has a bug where resize events are not reported
    widget.resizeEvent = resizeEvent


class FigureCanvas(QtFigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.).
    """
    def __init__(self, fig, parent=None, width=5, height=4, dpi=100):
        QtFigureCanvas.__init__(self, fig)

        self.viewer = None

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

        if self.viewer is not None:
            self.viewer.configure_window(width, height)

        return super(FigureCanvas, self).resizeEvent(event)

    def sizeHint(self):
        width, height = 300, 300
        if self.viewer is not None:
            width, height = self.viewer.get_desired_size()
        return QtCore.QSize(width, height)

    def set_viewer(self, viewer):
        self.viewer = viewer

#END
