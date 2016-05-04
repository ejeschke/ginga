#! /usr/bin/env python
#
# example3_mpl.py -- Copy attributes from a Ginga Qt widget into a Matplotlib
#                       figure.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
#
"""
   $ ./example3_mpl.py [fits file]

example3 displays a native ginga widget beside a matplotlib figure as two
panes.  A fits file can be dropped into the left pane and manipulated using
the standard Ginga interactive controls
see (http://ginga.readthedocs.io/en/latest/quickref.html).
Drop down boxes allow the color map to be changed.

The right pane has two buttons under it: pressing each button sets up a
different kind of plot in the mpl pane based on the current state of the
ginga pane.

You need Qt4 with python bindings (or pyside) installed to run this example.
"""
from __future__ import print_function
import sys
import numpy

from ginga.qtw.ImageViewCanvasQt import ImageViewCanvas
from ginga.qtw import ColorBar
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga import AstroImage
from ginga import cmap, imap
from ginga.misc import log
from ginga.util.six.moves import map, zip

import matplotlib
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import ListedColormap

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

class FitsViewer(QtGui.QMainWindow):

    def __init__(self, logger):
        super(FitsViewer, self).__init__()
        self.logger = logger

        menubar = self.menuBar()

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.addMenu("File")

        item = QtGui.QAction("Open File", menubar)
        item.triggered.connect(self.open_file)
        filemenu.addAction(item)

        sep = QtGui.QAction(menubar)
        sep.setSeparator(True)
        filemenu.addAction(sep)

        item = QtGui.QAction("Quit", menubar)
        item.triggered.connect(self.close)
        filemenu.addAction(item)

        # Add matplotlib color maps to our built in ones
        cmap.add_matplotlib_cmaps()
        self.cmaps = cmap.get_names()
        self.imaps = imap.get_names()

        wd, ht = 500, 500

        # Create a Ginga widget
        fi = ImageViewCanvas(logger, render='widget')
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.enable_draw(False)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        # enable various key and mouse controlled actions
        bd = fi.get_bindings()
        bd.enable_all(True)

        self.cp_tag = 'compass'

        # pack widget into layout
        gingaw = fi.get_widget()
        gingaw.resize(wd, ht)

        vbox1 = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        layout.addWidget(gingaw, stretch=1)

        self.cm = cmap.get_cmap('gray')
        self.im = imap.get_imap('ramp')

        # add color bar
        rgbmap = fi.get_rgbmap()
        rgbmap.set_hash_size(256)
        cbar = ColorBar.ColorBar(self.logger, rgbmap=rgbmap,
                                 link=True)
        cbar.resize(-1, 15)
        #cbar.show()
        self.colorbar = cbar
        layout.addWidget(cbar, stretch=0)

        settings = fi.get_settings()
        settings.getSetting('cuts').add_callback('set',
                                                 self.change_range_cb, fi,
                                                 self.colorbar)

        # color map selection widget
        wcmap = QtGui.QComboBox()
        for name in self.cmaps:
            wcmap.addItem(name)
        index = self.cmaps.index('gray')
        wcmap.setCurrentIndex(index)
        wcmap.activated.connect(self.set_cmap_cb)
        self.wcmap = wcmap

        # intensity map selection widget
        wimap = QtGui.QComboBox()
        for name in self.imaps:
            wimap.addItem(name)
        index = self.imaps.index('ramp')
        wimap.setCurrentIndex(index)
        wimap.activated.connect(self.set_cmap_cb)
        self.wimap = wimap

        #wopen = QtGui.QPushButton("Open File")
        #wopen.clicked.connect(self.open_file)

        # add buttons to layout
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))
        hbox.addStretch(1)
        for w in (wcmap, wimap):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        layout.addWidget(hw, stretch=0)
        vbox1.setLayout(layout)

        # Create a matplotlib Figure
        #self.fig = matplotlib.figure.Figure(figsize=(wd, ht))
        self.fig = matplotlib.figure.Figure()
        self.canvas = FigureCanvas(self.fig)

        vbox2 = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        # scrw = QtGui.QScrollArea()
        # scrw.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        # scrw.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        # scrw.setWidgetResizable(True)
        # layout.addWidget(scrw, stretch=1)
        # scrw.setWidget(self.canvas)
        layout.addWidget(self.canvas, stretch=1)

        # Add matplotlib buttons
        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wgetimg = QtGui.QPushButton("Get Data")
        wgetimg.clicked.connect(self.get_image)
        wgetrgb = QtGui.QPushButton("Get RGB")
        wgetrgb.clicked.connect(self.get_rgb_image)
        #wquit = QtGui.QPushButton("Quit")
        #wquit.clicked.connect(self.close)

        hbox.addStretch(1)
        for w in (wgetimg, wgetrgb):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        layout.addWidget(hw, stretch=0)
        vbox2.setLayout(layout)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)

        w = QtGui.QWidget()
        layout = QtGui.QHBoxLayout()
        layout.addWidget(vbox1, stretch=1.0)
        layout.addWidget(vbox2, stretch=1.0)
        w.setLayout(layout)

        vbox.addWidget(w, stretch=1)

        self.readout = QtGui.QLabel("")
        vbox.addWidget(self.readout, stretch=0,
                       alignment=QtCore.Qt.AlignCenter)

        vw = QtGui.QWidget()
        vw.setLayout(vbox)
        self.setCentralWidget(vw)

    def set_cmap_cb(self, kind):
        index = self.wcmap.currentIndex()
        cmap_name = self.cmaps[index]
        self.cm = cmap.get_cmap(cmap_name)
        index = self.wimap.currentIndex()
        imap_name = self.imaps[index]
        self.im = imap.get_imap(imap_name)

        self.fitsimage.set_cmap(self.cm)
        self.fitsimage.set_imap(self.im)

    def change_range_cb(self, setting, value, fitsimage, cbar):
        loval, hival = value
        cbar.set_range(loval, hival)

    def clear_canvas(self):
        self.fitsimage.deleteAllObjects()

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.fitsimage.set_image(image)
        self.setWindowTitle(filepath)

        # create compass
        try:
            try:
                self.fitsimage.deleteObjectByTag(self.cp_tag)
            except KeyError:
                pass
            (x, y, xn, yn, xe, ye) = image.calc_compass_center()
            self.logger.debug("x=%d y=%d xn=%d yn=%d xe=%d ye=%d" % (
                x, y, xn, yn, xe, ye))
            Compass = self.fitsimage.getDrawClass('compass')
            self.fitsimage.add(Compass(
                x, y, xn, yn, xe, ye, color='skyblue',
                fontsize=14), tag=self.cp_tag)
        except Exception as e:
            self.logger.warning("Can't calculate compass: %s" % (
                str(e)))


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

    def closeEvent(self, ce):
        self.close()

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

    def calculate_aspect(self, shape, extent):
        dx = abs(extent[1] - extent[0]) / float(shape[1])
        dy = abs(extent[3] - extent[2]) / float(shape[0])
        return dx / dy

    def make_mpl_colormap(self, fitsimage):
        # make the equivalent color map for matplotlib
        # (takes into account any cmap warps, etc.)
        idx = numpy.array(list(range(256)), dtype='uint')
        idx = idx.reshape((256, 1))
        rgbmap = fitsimage.get_rgbmap()
        carr = rgbmap.get_rgbarray(idx).get_array('RGB').astype('float')
        carr = carr / 256.0
        carr = carr.reshape((256, 3))
        cm = ListedColormap(carr, N=256)
        return cm

    def get_wcs_extent(self, image, x0, y0, x1, y1):
        # WCS of the area
        ra0, dec0 = image.pixtoradec(x0, y0, format='deg', coords='data')
        ra1, dec1 = image.pixtoradec(x1, y1, format='deg', coords='data')
        extent = (ra0, ra1, dec0, dec1)
        return extent

    def get_rgb_image(self):
        fi = self.fitsimage
        # clear previous image
        self.fig.clf()

        # Grab the RGB array for the current image and place it in the
        # matplotlib figure axis
        arr = fi.getwin_array(order='RGB')

        # force aspect ratio of figure to match
        wd, ht = fi.get_window_size()

        # Get the data extents
        x0, y0 = fi.get_data_xy(0, 0)
        x1, y1 = fi.get_data_xy(wd-1, ht-1)
        flipx, flipy, swapxy = fi.get_transforms()
        if swapxy:
            x0, x1, y0, y1 = y0, y1, x0, x1
            xlabel = 'dec'
            ylabel = 'ra'
        else:
            xlabel = 'ra'
            ylabel = 'dec'

        #extent = (x0, x1, y1, y0)
        image = fi.get_image()
        extent = self.get_wcs_extent(image, x0, x1, y1, y0)
        #print "extent=%s" % (str(extent))

        # Calculate aspect ratio
        aspect = self.calculate_aspect(arr.shape, extent)

        #ax = self.fig.add_subplot(111, adjustable='box', aspect=aspect)
        ax = self.fig.add_subplot(111)
        ax.autoscale(True, tight=True)
        ax.set_anchor('C')
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        # make the equivalent color map for matplotlib
        cm = self.make_mpl_colormap(fi)

        img = ax.imshow(arr, interpolation="nearest", origin="upper",
                        vmin=0, vmax=255,
                        extent=extent,
                        aspect=aspect)

        # force an update of the figure
        self.fig.canvas.draw()

    def get_image(self):
        fi = self.fitsimage
        # clear previous image
        self.fig.clf()

        ax = self.fig.add_subplot(111)
        ax.autoscale(True, tight=True)

        x0, y0, x1, y1 = tuple(map(int, fi.get_datarect()))
        #extent = (x0, x1, y0, y1)

        image = fi.get_image()
        arr = image.cutout_data(x0, y0, x1, y1)

        extent = self.get_wcs_extent(image, x0, y0, x1, y1)

        # get cut levels
        loval, hival = fi.get_cut_levels()

        # make the equivalent color map for matplotlib
        cm = self.make_mpl_colormap(fi)

        # add the image to the figure
        interp = 'nearest'
        img = ax.imshow(arr, interpolation=interp, origin="lower",
                        vmin=loval, vmax=hival, cmap=cm,
                        aspect="equal", extent=extent)

        # add a colorbar
        self.fig.colorbar(img, orientation='vertical')

        # force an update of the figure
        self.fig.canvas.draw()


def main(options, args):

    QtGui.QApplication.setGraphicsSystem('raster')
    app = QtGui.QApplication(args)
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                app, QtCore.SLOT('quit()'))

    logger = log.get_logger(name="example3", options=options)
    w = FitsViewer(logger)
    w.resize(1024, 540)
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
