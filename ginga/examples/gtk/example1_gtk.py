#! /usr/bin/env python
#
# example1_gtk.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os
import logging

from ginga.gtkw.ImageViewCanvasGtk import ImageViewCanvas
from ginga.gtkw.ImageViewGtk import ScrolledView
from ginga.gtkw import GtkHelp
from ginga import AstroImage

import gtk


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(object):

    def __init__(self, logger):

        self.logger = logger
        root = gtk.Window(gtk.WINDOW_TOPLEVEL)
        root.set_title("ImageViewZoom Example")
        root.set_border_width(2)
        root.connect("delete_event", lambda w, e: self.quit(w))
        self.root = root

        self.select = GtkHelp.FileSelection(root)
        vbox = gtk.VBox(spacing=2)

        # create the ginga viewer and configure it
        fi = ImageViewCanvas(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        # enable some user interaction
        bd = fi.get_bindings()
        bd.enable_all(True)

        w = fi.get_widget()
        w.set_size_request(512, 512)

        # add scrollbar interface around this viewer
        si = ScrolledView(fi)

        vbox.pack_start(si, fill=True, expand=True)

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
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)
        self.fitsimage.set_image(image)
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
        fv.load_file(args[0])

    gtk.main()

if __name__ == '__main__':
    main(None, sys.argv[1:])

# END
