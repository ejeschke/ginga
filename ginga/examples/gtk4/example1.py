#! /usr/bin/env python
#
# example1.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import logging

from ginga.gtk4w.ImageViewGtk import CanvasView, ScrolledView
from ginga.gtk4w import GtkHelp
from ginga.util.loader import load_data

from gi.repository import Gtk


STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(object):

    def __init__(self, logger):

        self.logger = logger
        self.app = Gtk.Application()
        self.app.connect('activate', self.on_activate_cb)

    def on_activate_cb(self, app):
        #root = Gtk.Window(title="ImageViewZoom Example")
        root = Gtk.ApplicationWindow(application=app)
        root.set_title("ImageViewZoom Example")
        #root.set_border_width(2)
        #root.connect("delete_event", lambda w, e: self.quit(w))
        self.root = root

        self.select = GtkHelp.FileSelection(root)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(2)

        # create the ginga viewer and configure it
        fi = CanvasView(self.logger)
        fi.set_enter_focus(True)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        #fi.set_desired_size(500, 500)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.enable_auto_orient(True)
        fi.show_mode_indicator(True, corner='ur')
        self.viewer = fi

        # enable some user interaction
        bd = fi.get_bindings()
        bd.enable_all(True)

        w = fi.get_widget()
        w.set_size_request(512, 512)

        # add scrollbar interface around this viewer
        si = ScrolledView(fi)
        si.scroll_bars(horizontal='auto', vertical='auto')

        #vbox.pack_start(si, True, True, 0)
        vbox.append(si)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_spacing(4)
        hbox.set_margin_start(4)
        hbox.set_margin_end(4)
        hbox.set_margin_top(4)
        hbox.set_margin_bottom(4)
        #hbox.set_layout(Gtk.ButtonBoxStyle.END)

        wopen = Gtk.Button(label="Open File")
        wopen.connect('clicked', self.open_file)
        wquit = Gtk.Button(label="Quit")
        wquit.connect('clicked', self.quit)

        for w in (wopen, wquit):
            hbox.append(w)

        #vbox.pack_start(hbox, False, False, 0)
        vbox.append(hbox)
        root.set_child(vbox)

        root.present()

    def get_widget(self):
        return self.root

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.viewer.set_image(image)
        self.root.set_title(filepath)

    def open_file(self, w):
        self.select.popup("Open FITS file", self.load_file)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def quit(self, w):
        self.app.quit()
        return True


def main(options, args):

    logger = logging.getLogger("example1")
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(STD_FORMAT)
    stderrHdlr = logging.StreamHandler()
    stderrHdlr.setFormatter(fmt)
    logger.addHandler(stderrHdlr)

    fv = FitsViewer(logger)
    #root = fv.get_widget()
    #root.show()

    # if len(args) > 0:
    #     fv.load_file(args[0])

    fv.app.run(None)


if __name__ == '__main__':
    main(None, sys.argv[1:])

# END
