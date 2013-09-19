#! /usr/bin/env python
#
# ipg.py -- Example of Ginga widget interaction with IPython.
#
# Eric Jeschke (eric@naoj.org)
#
# Contains code from IPython tutorial programs "qtapp_ip.py" and "kapp.py".
#
import sys, os
import logging

from ginga import AstroImage
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw.FitsImageCanvasQt import FitsImageCanvas

from IPython.lib.kernel import connect_qtconsole
try:
    # older IPython releases
    from IPython.zmq.ipkernel import IPKernelApp
    
except ImportError:
    # newer 
    from IPython.kernel.zmq.kernelapp import IPKernelApp

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

# global ref to keep an object from being collected
app_ref = None


class SimpleKernelApp(object):
    """A minimal object that uses an IPython kernel and has a few methods
    to manipulate a namespace and open Qt consoles tied to the kernel.

    Code is modified from IPython tutorial programs 'qtapp_ip.py' and
    'kapp.py'.
    """

    def __init__(self, gui, shell):
        self.shell = shell
        
        if shell == None:
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
        if hasattr(self.ipkernel, 'profile'):
            return connect_qtconsole(self.ipkernel.connection_file, 
                                     profile=self.ipkernel.profile)
        else:
            return connect_qtconsole(self.ipkernel.connection_file)

    def cleanup_consoles(self, evt=None):
        for c in self.consoles:
            c.kill()

    def start(self):
        if self.shell == None:
            self.ipkernel.start()


class StartMenu(QtGui.QMainWindow):

    def __init__(self, logger, app, kapp):
        super(StartMenu, self).__init__()
        self.logger = logger
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
        if self.kapp.ipkernel == None:
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

    def new_viewer(self, name=None):
        if not name:
            self.count += 1
            name = 'v%d' % self.count

        # create a ginga basic object for user interaction
        fi = FitsImageCanvas(self.logger, render='widget')
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.enable_draw(True)
        fi.set_drawtype('ruler')
        fi.set_drawcolor('blue')
        fi.set_callback('drag-drop', self.drop_file, name)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)

        # expose the fits viewer to the shared namespace
        self.kapp.namespace[name] = fi

        # enable various interactive operations
        bd = fi.get_bindings()
        bd.enable_pan(True)
        bd.enable_zoom(True)
        bd.enable_cuts(True)
        bd.enable_flip(True)
        bd.enable_rotate(True)
        bd.enable_cmap(True)

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
        readout = QtGui.QLabel("")
        fi.set_callback('none-move', self.motion, readout)
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
        vw.show()

    def close_viewer(self, name):
        w = self.viewers[name]
        del self.viewers[name]
        # remove variable from namespace
        del self.kapp.namespace[name]
        w.close()
        
    def load_file(self, filepath, name):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        fi = self.kapp.namespace[name]
        fi.set_image(image)

    def open_file(self, name):
        res = QtGui.QFileDialog.getOpenFileName(self, "Open FITS file",
                                                ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0].encode('ascii')
        else:
            fileName = str(res)
        self.load_file(fileName, name)

    def drop_file(self, fitsimage, paths, name):
        fileName = paths[0]
        self.load_file(fileName, name)

    def motion(self, fitsimage, button, data_x, data_y, readout):

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
            if image == None:
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
        readout.setText(text)

    def quit(self):
        names = list(self.viewers.keys())
        for name in names:
            self.close_viewer(name)
        self.kapp.cleanup_consoles()
        self.close()

        
def start(kapp):
    global app_ref
    
    # create Qt app
    app = QtGui.QApplication([])
    app.connect(app, QtCore.SIGNAL('lastWindowClosed()'),
                app, QtCore.SLOT('quit()'))

    # create a logger
    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(STD_FORMAT)
    # stderrHdlr = logging.StreamHandler()
    # stderrHdlr.setFormatter(fmt)
    # logger.addHandler(stderrHdlr)
    fileHdlr = logging.FileHandler("/dev/null")
    fileHdlr.setFormatter(fmt)
    logger.addHandler(fileHdlr)

    # here is our little launcher
    w = StartMenu(logger, app, kapp)
    app_ref = w
    w.show()
    app.setActiveWindow(w)

    #app.exec_()
    # Very important, IPython-specific step: this gets GUI event loop
    # integration going, and it replaces calling app.exec_()
    kapp.start()
    return w

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
