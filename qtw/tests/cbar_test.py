import sys
sys.path.insert(0, '..')
sys.path.insert(0, '../..')
from QtHelp import QtGui, QtCore

import ColorBar as ColorBar
import cmap, imap
import logging

app = QtGui.QApplication([])

logger = logging.getLogger('cbar')
w = ColorBar.ColorBar(logger)
w.set_cmap(cmap.get_cmap('rainbow'))
w.set_imap(imap.get_imap('ramp'))
w.show()

app.exec_()
