#! /usr/bin/env python
#
# example2_mpl.py -- Simple, configurable FITS viewer using a matplotlib
#                      QtAgg backend for Ginga and embedded in a Qt program.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
Usage:
   example2_mpl.py [fits file]

You need Qt4 with python bindings (or pyside) installed to run this example.
"""
from __future__ import print_function
import sys, os
from ginga.qtw.QtHelp import QtGui, QtCore

from ginga import AstroImage
from matplotlib.figure import Figure
from ginga.mplw.ImageViewCanvasMpl import ImageViewCanvas
from ginga.mplw.FigureCanvasQt import FigureCanvas
from ginga.misc import log
from ginga import colors


class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger
        self.drawcolors = colors.get_colors()

        fig = Figure()
        w = FigureCanvas(fig)

        fi = ImageViewCanvas(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.enable_draw(False)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi
        fi.set_figure(fig)

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        DrawingCanvas = fi.getDrawClass('drawingcanvas')
        canvas = DrawingCanvas()
        canvas.enable_draw(True)
        #canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.setSurface(fi)
        self.canvas = canvas
        # add canvas to view
        fi.add(canvas)
        canvas.ui_setActive(True)

        w.resize(512, 512)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        self.readout = QtGui.QLabel("")
        vbox.addWidget(self.readout, stretch=0,
                       alignment=QtCore.Qt.AlignCenter)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wdrawtype = QtGui.QComboBox()
        self.drawtypes = fi.get_drawtypes()
        for name in self.drawtypes:
            wdrawtype.addItem(name)
        index = self.drawtypes.index('rectangle')
        wdrawtype.setCurrentIndex(index)
        wdrawtype.activated.connect(self.set_drawparams)
        self.wdrawtype = wdrawtype

        wdrawcolor = QtGui.QComboBox()
        for name in self.drawcolors:
            wdrawcolor.addItem(name)
        index = self.drawcolors.index('lightblue')
        wdrawcolor.setCurrentIndex(index)
        wdrawcolor.activated.connect(self.set_drawparams)
        self.wdrawcolor = wdrawcolor

        wfill = QtGui.QCheckBox("Fill")
        wfill.stateChanged.connect(self.set_drawparams)
        self.wfill = wfill

        walpha = QtGui.QDoubleSpinBox()
        walpha.setRange(0.0, 1.0)
        walpha.setSingleStep(0.1)
        walpha.setValue(1.0)
        walpha.valueChanged.connect(self.set_drawparams)
        self.walpha = walpha

        wclear = QtGui.QPushButton("Clear Canvas")
        wclear.clicked.connect(self.clear_canvas)
        wopen = QtGui.QPushButton("Open File")
        wopen.clicked.connect(self.open_file)
        wquit = QtGui.QPushButton("Quit")
        wquit.clicked.connect(self.close)

        hbox.addStretch(1)
        for w in (wopen, wdrawtype, wdrawcolor, wfill,
                  QtGui.QLabel('Alpha:'), walpha, wclear, wquit):
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
        fill = (self.wfill.checkState() != 0)
        alpha = self.walpha.value()

        params = { 'color': self.drawcolors[index],
                   'alpha': alpha,
                   }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.deleteAllObjects()

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.fitsimage.set_image(image)
        self.setWindowTitle(filepath)

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
        #print(fileName)
        self.load_file(fileName)

    def motion(self, fitsimage, button, data_x, data_y):

        # Get the value under the data coordinates
        try:
            #value = fitsimage.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = fitsimage.get_data(int(data_x+0.5), int(data_y+0.5))

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
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.setText(text)

def main(options, args):

    QtGui.QApplication.setGraphicsSystem('raster')
    app = QtGui.QApplication(args)
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                app, QtCore.SLOT('quit()'))

    logger = log.get_logger(name="example2", options=options)
    w = FitsViewer(logger)
    w.resize(524, 540)
    w.show()
    app.setActiveWindow(w)
    w.raise_()
    w.activateWindow()

    if len(args) > 0:
        w.load_file(args[0])

    app.exec_()

if __name__ == "__main__":

    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=None,
                      help="Set logging level to LEVEL")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")

    (options, args) = optprs.parse_args(sys.argv[1:])

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
