#! /usr/bin/env python
#
# example2.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import sys

from ginga.gtk4w import GtkHelp
from ginga.gtk4w.ImageViewGtk import CanvasView, ScrolledView
from ginga.canvas.CanvasObject import get_canvas_types
from ginga import colors
from ginga.misc import log
from ginga.util.loader import load_data
from ginga.locale.localize import _tr

from gi.repository import Gtk
#from gi.repository import GLib

STD_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'


class FitsViewer(object):

    def __init__(self, logger, render='widget'):
        self.logger = logger
        self.render = render
        self.app = Gtk.Application()
        self.app.connect('activate', self.on_activate_cb)

        self.gui_up = False

    def on_activate_cb(self, app):
        root = Gtk.ApplicationWindow(application=app)
        root.set_title("Gtk4 CanvasView Example")
        #root.set_border_width(2)
        #root.connect("delete_event", lambda w, e: quit(w))
        self.root = root
        self.select = GtkHelp.FileSelection(root)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_spacing(2)

        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        fi = CanvasView(self.logger, render=self.render)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.set_callback('drag-drop', self.drop_file_cb)
        fi.set_callback('cursor-changed', self.cursor_cb)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.set_enter_focus(True)
        # add little mode indicator that shows keyboard modal states
        fi.show_mode_indicator(True, corner='ur')
        # add a color bar
        #fi.show_color_bar(True)
        #fi.show_focus_indicator(True)
        self.viewer = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.register_for_cursor_drawing(fi)
        canvas.set_draw_mode('draw')
        canvas.set_surface(fi)
        canvas.ui_set_active(True)
        self.canvas = canvas

        # add our new canvas to viewers default canvas
        fi.get_canvas().add(canvas)

        self.drawtypes = canvas.get_drawtypes()
        self.drawtypes.sort()

        try:
            w = self.viewer.get_widget()
            w.set_size_request(512, 512)

            # add scrollbar interface around this viewer
            si = ScrolledView(fi)
            si.scroll_bars(horizontal='auto', vertical='auto')

            vbox.append(si)

            self.readout = Gtk.Label(label="")
            #self.readout.hexpand(True)
            vbox.append(self.readout)

            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            hbox.set_spacing(5)
            hbox.set_margin_start(4)
            hbox.set_margin_end(4)
            hbox.set_margin_top(4)
            hbox.set_margin_bottom(4)

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

            wfill = GtkHelp.CheckButton(label=_tr("Fill"))
            wfill.sconnect('toggled', self.set_drawparams)
            self.wfill = wfill

            walpha = GtkHelp.SpinButton()
            adj = walpha.get_adjustment()
            adj.configure(0.0, 0.0, 1.0, 0.1, 0.1, 0)
            walpha.set_value(1.0)
            walpha.set_digits(1)
            walpha.sconnect('value-changed', self.set_drawparams)
            self.walpha = walpha

            wclear = Gtk.Button(label=_tr("Clear Canvas"))
            wclear.connect('clicked', self.clear_canvas)

            wopen = Gtk.Button(label=_tr("Open File"))
            wopen.connect('clicked', self.open_file)
            wquit = Gtk.Button(label=_tr("Quit"))
            wquit.connect('clicked', quit)

            for w in (wquit, wclear, walpha, Gtk.Label(label=_tr("Alpha") + ":"),
                      wfill, wdrawcolor, wdrawtype, wopen):
                hbox.prepend(w)

            vbox.append(hbox)

            root.set_child(vbox)
            root.present()

            print("finishing gui")
            self.gui_up = True
        except Exception as e:
            self.logger.error(f"error bringing up GUI: {e}", exc_info=True)
            #sys.exit(1)

        return True

    def get_widget(self):
        return self.root

    def set_drawparams(self, w):
        if not self.gui_up:
            return
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
        self.canvas.delete_all_objects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.viewer.set_image(image)
        self.root.set_title(filepath)

    def open_file(self, w):
        self.select.popup(_tr("Open FITS file"), self.load_file)

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
            self.logger.warning(_tr("Bad coordinate conversion") + ": %s" % (
                str(e)))
            ra_txt = _tr('BAD WCS')
            dec_txt = _tr('BAD WCS')

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def quit(self, w):
        self.app.quit()
        return True

    # def mainloop(self):
    #     context = GLib.main_context_default()
    #     while True:
    #         while context.pending():
    #             try:
    #                 context.iteration()
    #             except Exception as e:
    #                 self.logger.error("Exception in main_iteration() loop: %s" %
    #                                   (str(e)))

    def mainloop(self):
        self.app.run(None)


def main(options, args):

    logger = log.get_logger("example2", options=options)

    print('example RENDER  is', options.render)
    fv = FitsViewer(logger, render=options.render)
    # root = fv.get_widget()
    # root.show()

    # if len(args) > 0:
    #     fv.load_file(args[0])

    #fv.app.run(None)
    fv.mainloop()
    print("application finished")


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("-r", "--render", dest="render", default='widget',
                        help="Set render type {widget|opengl}")
    log.addlogopts(argprs)

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)
