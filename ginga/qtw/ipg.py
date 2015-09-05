#! /usr/bin/env python
#
# ipg.py -- Example of Ginga widget interaction with IPython.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# CREDIT:
# Contains code from IPython tutorial programs "qtapp_ip.py" and "kapp.py".
# Author not listed.
#
import sys, os
import logging

from ginga import AstroImage
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw.ImageViewCanvasQt import ImageViewCanvas
from ginga.canvas.types.all import DrawingCanvas
from ginga.qtw.Readout import Readout
from ginga.misc import log, Settings
from ginga.util import paths

from IPython.lib.kernel import connect_qtconsole
try:
    # older IPython releases
    from IPython.zmq.ipkernel import IPKernelApp

except ImportError:
    # newer releases
    from IPython.kernel.zmq.kernelapp import IPKernelApp

import matplotlib
# Hack to force matplotlib to not use any Xwindows backend.
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from IPython.display import Image
from io import BytesIO


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

# global ref to keep an object from being collected
app_ref = None

# workaround for suppressing logging to stdout in ipython notebook
# on Macs
use_null_logger = True


class IPyNbImageView(ImageViewCanvas):

    def show(self):
        return Image(data=bytes(self.get_rgb_image_as_bytes(format='png')),
                     format='png', embed=True)

    def load(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.set_image(image)

    def add_canvas(self, tag=None):
        # add a canvas to the view
        canvas = DrawingCanvas()
        # enable drawing on the canvas
        canvas.enable_draw(True)
        canvas.ui_setActive(True)
        canvas.setSurface(self)
        # add the canvas to the view.
        self.add(canvas, tag=tag)
        return canvas

class SimpleKernelApp(object):
    """A minimal object that uses an IPython kernel and has a few methods
    to manipulate a namespace and open Qt consoles tied to the kernel.

    Code is modified from IPython tutorial programs 'qtapp_ip.py' and
    'kapp.py'.
    """

    def __init__(self, gui, shell):
        self.shell = shell
        self.logger = None

        if shell is None:
            # Start IPython kernel with GUI event loop support
            self.ipkernel = IPKernelApp.instance()
            self.ipkernel.initialize(['python', '--gui=%s' % gui,
                                      #'--log-level=10'  # for debugging
                                      ])
            # This application will also act on the shell user namespace
            self.namespace = self.ipkernel.shell.user_ns

        else:
            self.ipkernel = shell.config.IPKernelApp
            self.namespace = shell.user_ns

        # To create and track active qt consoles
        self.consoles = []


    def new_qt_console(self, evt=None):
        """start a new qtconsole connected to our kernel"""
        try:
            if hasattr(self.ipkernel, 'profile'):
                return connect_qtconsole(self.ipkernel.connection_file,
                                         profile=self.ipkernel.profile)
            else:
                return connect_qtconsole(self.ipkernel.connection_file)

        except Exception as e:
            if self.logger:
                self.logger.error("Couldn't start QT Console: %s" % (
                    str(e)))

    def cleanup_consoles(self, evt=None):
        for c in self.consoles:
            c.kill()

    def start(self):
        if self.shell is None:
            self.ipkernel.start()


class StartMenu(QtGui.QMainWindow):

    def __init__(self, logger, app, kapp, prefs):
        super(StartMenu, self).__init__()
        self.logger = logger
        self.preferences = prefs
        self.count = 0
        self.viewers = {}
        self.app = app
        self.kapp = kapp
        self.app.aboutToQuit.connect(self.quit)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        console = QtGui.QPushButton('Qt Console')
        if self.kapp.ipkernel is None:
            console.setEnabled(False)
        console.clicked.connect(self.kapp.new_qt_console)

        newfits = QtGui.QPushButton('New Viewer')
        newfits.clicked.connect(self.new_viewer)

        wquit = QtGui.QPushButton("Quit")
        wquit.clicked.connect(self.quit)

        hbox.addStretch(1)
        for w in (console, newfits, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw = QtGui.QWidget()
        self.setCentralWidget(vw)
        vw.setLayout(vbox)
        self.setWindowTitle("Ginga IPython Console")
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def new_viewer(self, name=None, settings=None):
        if not name:
            self.count += 1
            name = 'v%d' % self.count

        if settings is None:
            settings = self.preferences.createCategory('ipg_viewer')
            settings.load(onError='silent')
            settings.addDefaults(autocut_method='zscale')

        # instantiate bindings loaded with users preferences
        bclass = IPyNbImageView.bindingsClass
        bindprefs = self.preferences.createCategory('bindings')
        bd = bclass(self.logger, settings=bindprefs)

        # create a ginga basic object for user interaction
        fi = IPyNbImageView(self.logger, settings=settings,
                            render='widget', bindings=bd)
        fi.enable_draw(False)
        fi.set_callback('drag-drop', self.drop_file, name)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)

        # expose the fits viewer to the shared namespace
        self.kapp.namespace[name] = fi

        # enable various interactive operations
        bd = fi.get_bindings()
        bd.enable_all(True)

        # get the ginga Qt widget
        w = fi.get_widget()
        w.resize(512, 512)

        # pack it into a qt window with a couple other buttons
        vw = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(QtCore.QMargins(2, 2, 2, 2))
        vbox.setSpacing(1)
        vbox.addWidget(w, stretch=1)

        # for simple WCS readout
        self.readout = Readout(-1, 16)
        readout = self.readout.get_widget()
        fi.set_callback('none-move', self.motion, self.readout)
        vbox.addWidget(readout, stretch=0,
                       alignment=QtCore.Qt.AlignCenter)

        hbox = QtGui.QHBoxLayout()
        hbox.setContentsMargins(QtCore.QMargins(4, 2, 4, 2))

        wopen = QtGui.QPushButton("Open File")
        def _open_file(name):
            return lambda: self.open_file(name)
        wopen.clicked.connect(_open_file(name))
        wquit = QtGui.QPushButton("Close")
        def _close(name):
            return lambda: self.close_viewer(name)
        wquit.clicked.connect(_close(name))

        hbox.addStretch(1)
        for w in (wopen, wquit):
            hbox.addWidget(w, stretch=0)

        hw = QtGui.QWidget()
        hw.setLayout(hbox)
        vbox.addWidget(hw, stretch=0)

        vw.setLayout(vbox)
        vw.resize(524, 540)
        vw.setWindowTitle("Ginga: %s" % name)
        self.viewers[name] = vw
        vw.showNormal()
        vw.raise_()
        vw.activateWindow()

    def close_viewer(self, name):
        w = self.viewers[name]
        del self.viewers[name]
        # remove variable from namespace
        del self.kapp.namespace[name]
        w.setParent(None)
        w.deleteLater()

    def load_file(self, filepath, name):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        fi = self.kapp.namespace[name]
        fi.set_image(image)

    def open_file(self, name):
        res = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        self.load_file(fileName, name)

    def drop_file(self, viewer, paths, name):
        fileName = paths[0]
        self.load_file(fileName, name)

    def motion(self, viewer, button, data_x, data_y, readout):

        # Get the value under the data coordinates
        try:
            #value = viewer.get_data(data_x, data_y)
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x+0.5), int(data_y+0.5))

        except Exception:
            value = None

        fits_x, fits_y = data_x + 1, data_y + 1

        # Calculate WCS RA
        try:
            # NOTE: image function operates on DATA space coords
            image = viewer.get_image()
            if image is None:
                # No image loaded
                return
            ra_txt, dec_txt = image.pixtoradec(fits_x, fits_y,
                                               format='str', coords='fits')
        except Exception as e:
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        readout.set_text(text)

    def quit(self):
        names = list(self.viewers.keys())
        for name in names:
            self.close_viewer(name)
        self.kapp.cleanup_consoles()
        self.setParent(None)
        self.deleteLater()


def start(kapp):
    global app_ref

    if use_null_logger:
        logger = log.NullLogger()
    else:
        logger = logging.getLogger("ipg")
        logger.setLevel(logging.INFO)
        fmt = logging.Formatter(STD_FORMAT)
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)
        fileHdlr = logging.FileHandler("ipg.log")
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)
    kapp.logger = logger

    # Get settings (preferences)
    basedir = paths.ginga_home
    if not os.path.exists(basedir):
        try:
            os.mkdir(basedir)
        except OSError as e:
            logger.warn("Couldn't create ginga settings area (%s): %s" % (
                basedir, str(e)))
            logger.warn("Preferences will not be able to be saved")

    # Set up preferences
    prefs = Settings.Preferences(basefolder=basedir, logger=logger)
    settings = prefs.createCategory('general')
    settings.load(onError='silent')
    settings.setDefaults(useMatplotlibColormaps=False)
    bindprefs = prefs.createCategory('bindings')
    bindprefs.load(onError='silent')

    # So we can find our plugins
    sys.path.insert(0, basedir)
    moduleHome = os.path.split(sys.modules['ginga.version'].__file__)[0]
    childDir = os.path.join(moduleHome, 'misc', 'plugins')
    sys.path.insert(0, childDir)
    childDir = os.path.join(basedir, 'plugins')
    sys.path.insert(0, childDir)

    # User configuration (custom star catalogs, etc.)
    try:
        import ipg_config

        ipg_config.pre_gui_config(kapp)
    except Exception as e:
        try:
            (type, value, tb) = sys.exc_info()
            tb_str = "\n".join(traceback.format_tb(tb))

        except Exception:
            tb_str = "Traceback information unavailable."

        logger.error("Error importing Ginga config file: %s" % (
            str(e)))
        logger.error("Traceback:\n%s" % (tb_str))

    # create Qt app
    # Note: workaround for pyside bug where QApplication is not deleted
    app = QtGui.QApplication.instance()
    if not app:
        app = QtGui.QApplication([])
        app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                    app, QtCore.SLOT('quit()'))

    # here is our little launcher
    w = StartMenu(logger, app, kapp, prefs)
    app_ref = w
    w.show()
    app.setActiveWindow(w)

    #app.exec_()
    # Very important, IPython-specific step: this gets GUI event loop
    # integration going, and it replaces calling app.exec_()
    kapp.start()
    return w

# Some boilderplate to display matplotlib plots in notebook
# If QT GUI could interact nicely with --pylab=inline we wouldn't need this

def showplt():
    buf = BytesIO()
    plt.savefig(buf, bbox_inches=0)
    img = Image(data=bytes(buf.getvalue()),
                   format='png', embed=True)
    buf.close()
    return img

def nb_start():
    """Call this function if importing from Qt notebook."""
    kapp = SimpleKernelApp('qt', get_ipython())
    return start(kapp)

def main(options, args):
    """Call this function if running as standalone app."""
    kapp = SimpleKernelApp('qt', None)
    return start(kapp)


if __name__ == '__main__':
    main(None, sys.argv[1:])

# END
