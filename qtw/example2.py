#! /usr/bin/env python
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:48:15 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import logging
import pyfits
from PyQt4 import QtGui, QtCore

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
widgetHome = os.path.join(moduleHome, '..')
sys.path.insert(0, widgetHome)
sys.path.insert(0, moduleHome)

import AstroImage
from FitsImageCanvasQt import FitsImageCanvas

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger
        self.drawcolors = ['white', 'black', 'red', 'yellow', 'blue', 'green']

        fi = FitsImageCanvas(logger, render='widget')
        fi.enable_autolevels('on')
        fi.enable_zoom('on')
        fi.enable_cuts(True)
        fi.enable_flip(True)
        fi.enable_draw(True)
        fi.set_drawtype('ruler')
        fi.set_drawcolor('blue')
        fi.set_callback('drag-drop', self.drop_file)
        self.fitsimage = fi

        w = fi.get_widget()
        w.resize(512, 512)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wdrawtype = QtGui.QComboBox()
        self.drawtypes = fi.get_drawtypes()
        for name in self.drawtypes:
            wdrawtype.addItem(name)
        index = self.drawtypes.index('ruler')
        wdrawtype.setCurrentIndex(index)
        self.connect(wdrawtype, QtCore.SIGNAL("activated(QString)"),
                     self.set_drawparams)
        self.wdrawtype = wdrawtype

        wdrawcolor = QtGui.QComboBox()
        for name in self.drawcolors:
            wdrawcolor.addItem(name)
        index = self.drawcolors.index('blue')
        wdrawcolor.setCurrentIndex(index)
        self.connect(wdrawcolor, QtCore.SIGNAL("activated(QString)"),
                     self.set_drawparams)
        self.wdrawcolor = wdrawcolor

        wclear = QtGui.QPushButton("Clear Canvas")
        self.connect(wclear, QtCore.SIGNAL("clicked()"), self.clear_canvas)
        wopen = QtGui.QPushButton("Open File")
        self.connect(wopen, QtCore.SIGNAL("clicked()"), self.open_file)
        wquit = QtGui.QPushButton("Quit")
        self.connect(wquit, QtCore.SIGNAL("clicked()"),
                     self, QtCore.SLOT("close()"))

        hbox.addStretch(1)
        for w in (wopen, wdrawtype, wdrawcolor, wclear, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)

    def set_drawparams(self, kind):
        index = self.wdrawtype.currentIndex()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.currentIndex()

        params = { 'color': self.drawcolors[index], }
        self.fitsimage.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.fitsimage.deleteAllObjects()

    def load_file(self, filepath):
        image = AstroImage.AstroImage()
        image.load_file(filepath)

        self.fitsimage.set_image(image)
        self.setWindowTitle(filepath)

    def open_file(self):
        fileName = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                     ".", "FITS files (*.fits)")
        self.load_file(str(fileName))

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

def main(options, args):

    QtGui.QApplication.setGraphicsSystem('raster')
    app = QtGui.QApplication(args)
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                app, QtCore.SLOT('quit()'))

    logger = logging.getLogger("example2")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(STD_FORMAT)
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setFormatter(fmt)
    logger.addHandler(stderrHdlr)

    w = FitsViewer(logger)
    w.resize(524, 540)
    w.show()
    app.setActiveWindow(w)

    if len(args) > 0:
        w.load_file(args[0])

    app.exec_()

if __name__ == '__main__':
    main(None, sys.argv[1:])

# END


