#! /usr/bin/env python
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import logging
import pyfits
from QtHelp import QtGui, QtCore

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
widgetHome = os.path.join(moduleHome, '..')
sys.path.insert(0, widgetHome)
sys.path.insert(0, moduleHome)

from FitsImageQt import FitsImageZoom

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger

        fi = FitsImageZoom(self.logger, render='widget')
        fi.enable_autocuts('on')
        fi.enable_zoom('on')
        fi.enable_cuts(True)
        fi.enable_flip(True)
        fi.enable_rotate(True)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        w = fi.get_widget()
        w.resize(512, 512)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wopen = QtGui.QPushButton("Open File")
        self.connect(wopen, QtCore.SIGNAL("clicked()"), self.open_file)
        wquit = QtGui.QPushButton("Quit")
        self.connect(wquit, QtCore.SIGNAL("clicked()"),
                     self, QtCore.SLOT("close()"))

        hbox.addStretch(1)
        for w in (wopen, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)

    def load_file(self, filepath):
        fitsobj = pyfits.open(filepath, 'readonly')
        data = fitsobj[0].data
        # compressed FITS file?
        if (data == None) and (len(fitsobj) > 1) and \
           isinstance(fitsobj[1], pyfits.core.CompImageHDU):
            data = fitsobj[1].data
        fitsobj.close()

        self.fitsimage.set_data(data)
        self.setWindowTitle(filepath)

    def open_file(self):
        res = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0].encode('ascii')
        else:
            fileName = str(res)
        self.load_file(fileName)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

        
def main(options, args):
    
    app = QtGui.QApplication(sys.argv)
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                app, QtCore.SLOT('quit()'))

    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
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
