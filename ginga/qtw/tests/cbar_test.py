import sys
from ginga.qtw.QtHelp import QtGui, QtCore

from ginga.qtw import ColorBar
from ginga import cmap, imap
import logging

if __name__ == "__main__":
    app = QtGui.QApplication([])

    logger = logging.getLogger('cbar')
    w = ColorBar.ColorBar(logger)
    w.set_cmap(cmap.get_cmap('rainbow'))
    w.set_imap(imap.get_imap('ramp'))
    w.show()

    app.exec_()
