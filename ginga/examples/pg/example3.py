#! /usr/bin/env python
#
# example3.py -- Simple, configurable FITS viewer in a web browser.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example loads widgets directly from pgwidgets-python, not Ginga
wrappers.
"""

import sys
import logging
from argparse import ArgumentParser

from pgwidgets.sync import Application
#from pgwidgets.extras.file_browser import FileBrowser

from ginga import colors
from ginga.AstroImage import AstroImage
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.canvas import render
from ginga.misc import log
from ginga.web.pgw.ImageViewPg import CanvasView, ScrolledViewPg
from ginga.util.loader import load_data


class FitsViewer(object):

    def __init__(self, logger, session):
        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()
        self.format = 'png'

        self.session = session
        Widgets = session.get_widgets()

        self.top = Widgets.TopLevel(title="FitsViewer PGW", resizable=True)
        #self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox(spacing=1, padding=2)

        fi = CanvasView(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        #fi.set_callback('drag-drop', self.drop_file_cb)
        fi.set_callback('cursor-changed', self.cursor_cb)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_set_active(True)
        fi.set_enter_focus(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # so trackpad scrolling can be adjusted
        settings = bd.get_settings()
        settings.set(scroll_zoom_direct_scale=True,
                     scroll_zoom_acceleration=0.07)

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.set_surface(fi)
        self.canvas = canvas
        # add canvas to view
        private_canvas = fi.get_canvas()
        private_canvas.add(canvas)
        canvas.ui_set_active(True)
        canvas.register_for_cursor_drawing(fi)
        self.drawtypes = canvas.get_drawtypes()
        self.drawtypes.sort()

        # add a color bar
        fi.show_color_bar(True)

        # add little mode indicator that shows keyboard modal states
        fi.show_mode_indicator(True, corner='ur')

        fi.set_desired_size(512, 512)
        w_canvas = Widgets.Image(interactive=True, use_animation_frame=True)
        w_canvas.on("drop-end", self.drop_file_cb)

        fi.set_widget(w_canvas)
        sw = ScrolledViewPg(session, fi)
        vbox.add_widget(sw, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout)

        hbox = Widgets.HBox(padding=2, spacing=4)

        wdrawtype = Widgets.ComboBox()
        for name in self.drawtypes:
            wdrawtype.append_text(name)
        index = self.drawtypes.index('rectangle')
        wdrawtype.set_index(index)
        wdrawtype.add_callback('activated', lambda *args: self.set_drawparams())
        self.wdrawtype = wdrawtype

        wdrawcolor = Widgets.ComboBox()
        for name in self.drawcolors:
            wdrawcolor.append_text(name)
        index = self.drawcolors.index('lightblue')
        wdrawcolor.set_index(index)
        wdrawcolor.add_callback('activated', lambda *args: self.set_drawparams())
        self.wdrawcolor = wdrawcolor

        wfill = Widgets.CheckBox("Fill")
        wfill.add_callback('activated', lambda w, tf: self.set_drawparams())
        self.wfill = wfill

        walpha = Widgets.SpinBox(dtype='float')
        walpha.set_limits(0.0, 1.0, 0.1)
        walpha.set_value(1.0)
        walpha.set_decimals(2)
        walpha.add_callback('activated', lambda w, val: self.set_drawparams())
        self.walpha = walpha

        wclear = Widgets.Button("Clear Canvas")
        wclear.add_callback('activated', lambda w: self.clear_canvas())

        hbox.add_widget(Widgets.Label(''), stretch=1)
        for w in (wdrawtype, wdrawcolor, wfill,
                  Widgets.Label('Alpha:'), walpha, wclear):
            hbox.add_widget(w)

        vbox.add_widget(hbox)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox(padding=2, spacing=6)
        btn1 = Widgets.RadioButton("Draw")
        btn1.set_state(mode == 'draw')
        btn1.add_callback('activated', lambda w, val: self.set_mode_cb('draw', val))
        btn1.set_tooltip("Choose this to draw on the canvas")
        hbox.add_widget(btn1)

        btn2 = Widgets.RadioButton("Edit", group=btn1)
        btn2.set_state(mode == 'edit')
        btn2.add_callback('activated', lambda w, val: self.set_mode_cb('edit', val))
        btn2.set_tooltip("Choose this to edit things on the canvas")
        hbox.add_widget(btn2)

        self.open_dialog = Widgets.FileDialog(mode="file", accept=".fits")
        # self.open_dialog = FileBrowser(session, mode="file", title="Open File")
        # self.open_dialog.add_ext_filter("Images", "fits")
        self.open_dialog.on('activated', self.drop_file_cb)
        btn3 = Widgets.Button("Upload File")
        btn3.add_callback('activated', lambda w: self.open_dialog.popup())
        hbox.add_widget(btn3)

        drop_lbl = Widgets.Label("[Drop file here]")
        hbox.add_widget(drop_lbl)
        drop_lbl.set_halign("center")
        drop_lbl.set_color("#e8f0fe", "#4a86c8")
        drop_lbl.set_font(None, 14)
        drop_lbl.on('drop-end', self.drop_file_cb)

        prog = Widgets.ProgressBar()
        drop_lbl.on('drop-progress', self.update_download_cb, prog)
        w_canvas.on('drop-progress', self.update_download_cb, prog)
        hbox.add_widget(prog, stretch=1)

        hbox.add_widget(Widgets.Label('Zoom sensitivity: '))
        spin = Widgets.SpinBox(dtype='float')
        spin.add_callback('activated',
                          lambda w, val: self.adjust_scrolling_accel_cb(val))
        spin.set_limits(0.0, 12.0, 0.005)
        spin.set_value(8.0)
        hbox.add_widget(spin, stretch=1)

        # hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox)

        self.statusbar = Widgets.Label("")
        vbox.add_widget(self.statusbar)

        self.top.set_widget(vbox)

    def set_drawparams(self):
        index = self.wdrawtype.get_index()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.get_index()
        fill = self.wfill.get_state()
        alpha = self.walpha.get_value()

        params = {'color': self.drawcolors[index],
                  'alpha': alpha,
                  }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box',
                    'squarebox'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.delete_all_objects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)
        self.top.set_title(filepath)

    def load_buffer(self, name, buf):
        from astropy.io import fits
        hdu_l = fits.HDUList.fromstring(buf)
        image = AstroImage(logger=self.logger)
        image.load_hdu(hdu_l[0])
        self.fitsimage.set_image(image)
        self.top.set_title(name)

    def open_file(self):
        Widgets = self.session.get_widgets()
        res = Widgets.FileDialog(mode='file', accept=".fits")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(fileName)

    def drop_file_cb(self, evt):
        f = evt["files"][0]
        name = f['name']
        if f.get("data"):
            # data is a raw buffer of the file
            buf = f['data']
            self.load_buffer(name, buf)

    def update_download_cb(self, evt, prog):
        pct = evt['transferred_bytes'] / evt['total_bytes']
        prog.set_value(pct)

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

    def set_mode_cb(self, mode, tf):
        self.logger.info("canvas mode changed (%s) %s" % (mode, tf))
        if not (tf is False):
            self.canvas.set_draw_mode(mode)
        return True

    def adjust_scrolling_accel_cb(self, val):
        def f(x):
            return (1.0 / 2.0**(10.0 - x))
        val2 = f(val)
        self.logger.debug("spin value is %f, setting will be %f" % (val, val2))
        settings = self.fitsimage.get_bindings().get_settings()
        settings.set(scroll_zoom_acceleration=val2)
        return True

    def closed(self, w):
        self.logger.info("Top window closed.")
        w.delete()
        self.top = None
        sys.exit()

    def quit(self, *args):
        self.readout.set_text("Quitting!")
        self.logger.info("Attempting to shut down the application...")
        if self.top is not None:
            self.top.close()
        sys.exit()


def do_session(logger, session, options, args):
    """Run a session for this fits viewer application.
    Is called when a session is created.
    """
    # our own viewer object, customized with methods (see above)
    viewer = FitsViewer(logger, session)
    #session.add_callback('close', viewer.quit)

    if options.renderer is not None:
        render_class = render.get_render_class(options.renderer)
        viewer.fitsimage.set_renderer(render_class(viewer.fitsimage))

    logger.debug("showing toplevel")
    viewer.top.resize(850, 800)
    viewer.top.show()

    # base_url = session.get_url()
    # logger.info(f"visit {base_url} to view the application")


def main(options, args):

    logger = log.get_logger("example3", options=options)

    # establish our widget application
    app = Application(max_sessions=options.max_sessions,
                      logger=logger,
                      host=options.host, http_port=options.port,
                      ws_port=options.port + 1)

    @app.on_connect
    def on_session(session):
        do_session(logger, session, options, args)

    app.start()

    logger.info("entering event loop...")
    try:
        app.run()

    except KeyboardInterrupt:
        logger.info("terminating viewer...")


if __name__ == "__main__":

    # Parse command line options
    argprs = ArgumentParser()

    argprs.add_argument("--host", dest="host", metavar="HOST",
                        default='localhost',
                        help="Listen on HOST for connections")
    argprs.add_argument("--log", dest="logfile", metavar="FILE",
                        help="Write logging output to FILE")
    argprs.add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                        type=int, default=logging.INFO,
                        help="Set logging level to LEVEL")
    argprs.add_argument("--max-sessions", dest="max_sessions", metavar="N",
                        type=int, default=4,
                        help="Limit number of active sessions to N")
    argprs.add_argument("--port", dest="port", metavar="PORT",
                        type=int, default=9909,
                        help="Listen on PORT for connections")
    argprs.add_argument("-r", "--renderer", dest="renderer", metavar="NAME",
                        default=None,
                        help="Choose renderer (pil|agg|opencv|cairo)")
    argprs.add_argument("--stderr", dest="logstderr", default=False,
                        action="store_true",
                        help="Copy logging also to stderr")
    argprs.add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                        default='qt',
                        help="Choose GUI toolkit (gtk|qt)")

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)
