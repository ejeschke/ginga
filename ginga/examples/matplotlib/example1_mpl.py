#! /usr/bin/env python
#
# example1_mpl.py -- Simple, configurable FITS viewer using a matplotlib
#                      QtAgg backend for Ginga and embedded in a Qt program.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Usage:
   example1_mpl.py [fits file]

You need Qt5 or Qt6 with pyqt bindings (or pyside) installed to run this
example.
"""

import sys

from matplotlib.figure import Figure

from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp
from ginga.mplw.ImageViewMpl import CanvasView
from ginga.mplw.FigureCanvasQt import FigureCanvas
from ginga.misc import log
from ginga.util.loader import load_data


class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger

        fig = Figure()
        w = FigureCanvas(fig)

        fi = CanvasView(logger=self.logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_auto_orient(True)
        fi.enable_autozoom('on')
        #fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.set_figure(fig)
        fi.show_mode_indicator(True, corner='ur')
        self.fitsimage = fi

        fi.get_bindings().enable_all(True)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)

        vbox.addWidget(w, stretch=1)

        self.readout = QtGui.QLabel("")
        vbox.addWidget(self.readout, stretch=0,
                       alignment=QtCore.Qt.AlignCenter)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wopen = QtGui.QPushButton("Open File")
        wopen.clicked.connect(self.open_file)
        wquit = QtGui.QPushButton("Quit")
        wquit.clicked.connect(self.close)

        hbox.addStretch(1)
        for w in (wopen, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)

        fi.configure(512, 512)

    def get_fitsimage(self):
        return self.fitsimage

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)

    def open_file(self):
        res = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(fileName)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def motion(self, fitsimage, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            #value = fitsimage.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = fitsimage.get_data(int(data_x + 0.5), int(data_y + 0.5))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = fitsimage.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.setText(text)


def main(options, args):

    if QtHelp.have_pyqt6 or QtHelp.have_pyside6:
        QtGui.QApplication.setHighDpiScaleFactorRoundingPolicy(
            QtCore.Qt.HighDpiScaleFactorRoundingPolicy.Floor)
    app = QtGui.QApplication(args)

    logger = log.get_logger(name="example1", options=options)
    viewer = FitsViewer(logger)
    viewer.resize(524, 540)
    viewer.show()
    app.setActiveWindow(viewer)

    if len(args) > 0:
        viewer.load_file(args[0])

    app.exec_()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
