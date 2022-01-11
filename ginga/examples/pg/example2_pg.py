#! /usr/bin/env python
#
# example2.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import sys
import logging

from ginga import colors
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.canvas import render
from ginga.misc import log
from ginga.web.pgw import Widgets, Viewers
from ginga.util.loader import load_data


class FitsViewer(object):

    def __init__(self, logger, window):
        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        self.top = window
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()
        vbox.set_margins(2, 2, 2, 2)
        vbox.set_spacing(1)

        fi = Viewers.CanvasView(logger)
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
        w = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(w, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        hbox = Widgets.HBox()
        hbox.set_margins(2, 2, 2, 2)
        hbox.set_spacing(4)

        wdrawtype = Widgets.ComboBox()
        for name in self.drawtypes:
            wdrawtype.append_text(name)
        index = self.drawtypes.index('rectangle')
        wdrawtype.set_index(index)
        wdrawtype.add_callback('activated', lambda w, idx: self.set_drawparams())
        self.wdrawtype = wdrawtype

        wdrawcolor = Widgets.ComboBox()
        for name in self.drawcolors:
            wdrawcolor.append_text(name)
        index = self.drawcolors.index('lightblue')
        wdrawcolor.set_index(index)
        wdrawcolor.add_callback('activated', lambda w, idx: self.set_drawparams())
        self.wdrawcolor = wdrawcolor

        wfill = Widgets.CheckBox("Fill")
        wfill.add_callback('activated', lambda w, tf: self.set_drawparams())
        self.wfill = wfill

        walpha = Widgets.SpinBox(dtype=float)
        walpha.set_limits(0.0, 1.0, incr_value=0.1)
        walpha.set_value(1.0)
        walpha.set_decimals(2)
        walpha.add_callback('value-changed', lambda w, val: self.set_drawparams())
        self.walpha = walpha

        wclear = Widgets.Button("Clear Canvas")
        wclear.add_callback('activated', lambda w: self.clear_canvas())
        ## wopen = Widgets.Button("Open File")
        ## wopen.add_callback('activated', lambda w: self.open_file())
        ## wquit = Widgets.Button("Quit")
        ## wquit.add_callback('activated', lambda w: self.quit())

        hbox.add_widget(Widgets.Label(''), stretch=1)
        for w in (wdrawtype, wdrawcolor, wfill,
                  Widgets.Label('Alpha:'), walpha, wclear):
            hbox.add_widget(w, stretch=0)

        vbox.add_widget(hbox, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
        hbox.set_spacing(4)
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

        hbox.add_widget(Widgets.Label('Zoom sensitivity: '))
        slider = Widgets.Slider(orientation='horizontal', dtype=float)
        slider.add_callback('value-changed',
                            lambda w, val: self.adjust_scrolling_accel_cb(val))
        slider.set_limits(0.0, 12.0, 0.005)
        slider.set_value(8.0)
        hbox.add_widget(slider, stretch=1)

        # hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        # need to put this in an hbox with an expanding label or the
        # browser wants to resize the canvas
        hbox = Widgets.HBox()
        hbox.add_widget(vbox, stretch=0)
        hbox.add_widget(Widgets.Label(''), stretch=1)

        self.top.set_widget(hbox)

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
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.delete_all_objects()

    def load_file(self, filepath):
        image = load_data(filepath, logger=self.logger)
        self.fitsimage.set_image(image)
        self.top.set_title(filepath)

    def open_file(self):
        res = Widgets.FileDialog.getOpenFileName(self, "Open FITS file",
                                                 ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(fileName)

    def drop_file_cb(self, viewer, paths):
        filename = paths[0]
        self.load_file(filename)

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
        self.logger.debug("slider value is %f, setting will be %f" % (val, val2))
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


def main(options, args):

    logger = log.get_logger("example2", options=options)

    #base_url = "http://%s:%d/app" % (options.host, options.port)

    # establish our widget application
    app = Widgets.Application(logger=logger,
                              host=options.host, port=options.port)

    #  create top level window
    window = app.make_window("Ginga web example2")

    # our own viewer object, customized with methods (see above)
    viewer = FitsViewer(logger, window)
    #server.add_callback('shutdown', viewer.quit)

    if options.renderer is not None:
        render_class = render.get_render_class(options.renderer)
        viewer.fitsimage.set_renderer(render_class(viewer.fitsimage))

    window.resize(700, 540)

    if len(args) > 0:
        viewer.load_file(args[0])

    #window.show()
    #window.raise_()

    try:
        app.mainloop()

    except KeyboardInterrupt:
        logger.info("Terminating viewer...")
        window.close()


if __name__ == "__main__":

    # Parse command line options
    from argparse import ArgumentParser

    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False, action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--host", dest="host", metavar="HOST",
                        default='localhost',
                        help="Listen on HOST for connections")
    argprs.add_argument("--log", dest="logfile", metavar="FILE",
                        help="Write logging output to FILE")
    argprs.add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                        type=int, default=logging.INFO,
                        help="Set logging level to LEVEL")
    argprs.add_argument("--port", dest="port", metavar="PORT",
                        type=int, default=9909,
                        help="Listen on PORT for connections")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")
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
