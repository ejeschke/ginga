#! /usr/bin/env python
#
# example2.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import sys

from ginga.gtk3w import GtkHelp
from ginga.gtk3w.ImageViewGtk import CanvasView
from ginga.canvas.CanvasObject import get_canvas_types
from ginga import colors
from ginga.misc import log
from ginga.util.loader import load_data

from gi.repository import Gtk

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(object):

    def __init__(self, logger, render='widget'):

        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        root = Gtk.Window(title="Gtk3 CanvasView Example")
        root.set_border_width(2)
        root.connect("delete_event", lambda w, e: quit(w))
        self.root = root
        self.select = GtkHelp.FileSelection(root)

        vbox = Gtk.VBox(spacing=2)

        fi = CanvasView(logger, render=render)
        fi.enable_autocuts('on')
        fi.set_autocut_params('histogram')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.set_callback('drag-drop', self.drop_file_cb)
        fi.set_callback('cursor-changed', self.cursor_cb)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.set_enter_focus(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.set_surface(fi)
        self.canvas = canvas
        # add canvas to view
        private_canvas = fi.get_canvas()
        private_canvas.register_for_cursor_drawing(fi)
        private_canvas.add(canvas)
        canvas.ui_set_active(True)
        self.drawtypes = canvas.get_drawtypes()
        self.drawtypes.sort()

        # add a color bar
        #fi.show_color_bar(True)

        #fi.show_focus_indicator(True)

        # add little mode indicator that shows keyboard modal states
        fi.show_mode_indicator(True, corner='ur')

        w = fi.get_widget()
        w.set_size_request(512, 512)

        vbox.pack_start(w, True, True, 1)

        self.readout = Gtk.Label(label="")
        vbox.pack_start(self.readout, False, False, 0)

        hbox = Gtk.HBox(spacing=5)

        wdrawtype = GtkHelp.combo_box_new_text()
        index = 0
        for name in self.drawtypes:
            wdrawtype.insert_text(index, name)
            index += 1
        index = self.drawtypes.index('rectangle')
        wdrawtype.set_active(index)
        wdrawtype.connect('changed', self.set_drawparams)
        self.wdrawtype = wdrawtype

        wdrawcolor = GtkHelp.combo_box_new_text()
        index = 0
        for name in self.drawcolors:
            wdrawcolor.insert_text(index, name)
            index += 1
        index = self.drawcolors.index('lightblue')
        wdrawcolor.set_active(index)
        wdrawcolor.connect('changed', self.set_drawparams)
        self.wdrawcolor = wdrawcolor

        wfill = GtkHelp.CheckButton(label="Fill")
        wfill.sconnect('toggled', self.set_drawparams)
        self.wfill = wfill

        walpha = GtkHelp.SpinButton()
        adj = walpha.get_adjustment()
        adj.configure(0.0, 0.0, 1.0, 0.1, 0.1, 0)
        walpha.set_value(1.0)
        walpha.set_digits(1)
        walpha.sconnect('value-changed', self.set_drawparams)
        self.walpha = walpha

        wclear = Gtk.Button(label="Clear Canvas")
        wclear.connect('clicked', self.clear_canvas)

        wopen = Gtk.Button(label="Open File")
        wopen.connect('clicked', self.open_file)
        wquit = Gtk.Button(label="Quit")
        wquit.connect('clicked', quit)

        for w in (wquit, wclear, walpha, Gtk.Label(label="Alpha:"),
                  wfill, wdrawcolor, wdrawtype, wopen):
            hbox.pack_end(w, False, False, 0)

        vbox.pack_start(hbox, False, False, 0)

        root.add(vbox)

    def get_widget(self):
        return self.root

    def set_drawparams(self, w):
        index = self.wdrawtype.get_active()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.get_active()
        fill = self.wfill.get_active()
        alpha = self.walpha.get_value()

        params = {'color': self.drawcolors[index],
                  'alpha': alpha,
                  #'cap': 'ball',
                  }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self, w):
        self.canvas.deleteAllObjects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)
        self.root.set_title(filepath)

    def open_file(self, w):
        self.select.popup("Open FITS file", self.load_file)

    def drop_file_cb(self, fitsimage, paths):
        fileName = paths[0]
        self.load_file(fileName)

    def cursor_cb(self, viewer, button, data_x, data_y):
        """This gets called when the data position relative to the cursor
        changes.
        """
        # Get the value under the data coordinates
        try:
            # We report the value across the pixel, even though the coords
            # change halfway across the pixel
            value = viewer.get_data(int(data_x + viewer.data_off),
                                    int(data_y + viewer.data_off))

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
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def quit(self, w):
        Gtk.main_quit()
        return True


def main(options, args):

    logger = log.get_logger("example2", options=options)

    # Check whether user wants to use OpenCL
    if options.opencl:
        from ginga import trcalc
        try:
            trcalc.use('opencl')
        except Exception as e:
            logger.warning("failed to set OpenCL preference: %s" % (str(e)))

    fv = FitsViewer(logger, render=options.render)
    root = fv.get_widget()
    root.show_all()

    if len(args) > 0:
        fv.load_file(args[0])

    Gtk.main()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--opencl", dest="opencl", default=False,
                        action="store_true",
                        help="Use OpenCL acceleration")
    argprs.add_argument("-r", "--render", dest="render", default='widget',
                        help="Set render type {widget|opengl}")
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
