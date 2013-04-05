#! /usr/bin/env python
#
# example1.py -- Simple, configurable FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import logging
import pyfits
import gtk

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
widgetHome = os.path.join(moduleHome, '..')
sys.path.insert(0, widgetHome)
sys.path.insert(0, moduleHome)

from FitsImageGtk import FitsImageZoom
import FileSelection

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

class FitsViewer(object):

    def __init__(self, logger):

        self.logger = logger
        root = gtk.Window(gtk.WINDOW_TOPLEVEL)
        root.set_title("FitsImageZoom Example")
        root.set_border_width(2)
        root.connect("delete_event", lambda w, e: self.quit(w))
        self.root = root
        
        self.select = FileSelection.FileSelection()
        vbox = gtk.VBox(spacing=2)

        fi = FitsImageZoom(logger)
        fi.enable_autocuts('on')
        fi.enable_zoom('on')
        fi.enable_cuts(True)
        fi.enable_flip(True)
        fi.enable_rotate(True)
        fi.set_callback('drag-drop', self.drop_file)
        self.fitsimage = fi

        w = fi.get_widget()
        w.set_size_request(512, 512)

        vbox.pack_start(w, fill=True, expand=True)

        hbox = gtk.HButtonBox()
        hbox.set_layout(gtk.BUTTONBOX_END)

        wopen = gtk.Button("Open File")
        wopen.connect('clicked', self.open_file)
        wquit = gtk.Button("Quit")
        wquit.connect('clicked', self.quit)

        for w in (wopen, wquit):
            hbox.add(w)

        vbox.pack_start(hbox, fill=False, expand=False)
        root.add(vbox)

    def get_widget(self):
        return self.root

    def load_file(self, filepath):
        in_f = pyfits.open(filepath, 'readonly')
        data = in_f[0].data
        # compressed FITS file?
        if (data == None) and (len(in_f) > 1) and \
           isinstance(in_f[1], pyfits.core.CompImageHDU):
            data = in_f[1].data
        in_f.close()

        self.fitsimage.set_data(data)
        self.root.set_title(filepath)

    def open_file(self, w):
        self.select.popup("Open FITS file", self.load_file)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)
        
    def quit(self, w):
        gtk.main_quit()
        return True

        
def main(options, args):

    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(STD_FORMAT)
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setFormatter(fmt)
    logger.addHandler(stderrHdlr)

    fv = FitsViewer(logger)
    root = fv.get_widget()
    root.show_all()

    if len(args) > 0:
        fv.load_file(fi, args[0])

    gtk.mainloop()

    
if __name__ == '__main__':
    main(None, sys.argv[1:])
    
# END

