#! /usr/bin/env python
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, os
import logging

from ginga import AstroImage, colors
import ginga.toolkit as ginga_toolkit
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.util.toolbox import ModeIndicator
from ginga.misc import log


class FitsViewer(object):

    def __init__(self, logger):
        self.logger = logger
        self.drawcolors = colors.get_colors()
        self.dc = get_canvas_types()

        from ginga.gw import Widgets, Viewers

        self.app = Widgets.Application(logger=logger)
        #self.app.add_callback('shutdown', self.quit)
        self.top = self.app.make_window("Ginga shared canvas example")
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        hbox = Widgets.HBox()
        hbox.set_border_width(2)
        hbox.set_spacing(4)

        v1 = Viewers.CanvasView(logger)
        v1.enable_autocuts('on')
        v1.set_autocut_params('zscale')
        v1.enable_autozoom('on')
        v1.set_zoom_algorithm('rate')
        v1.set_zoomrate(1.4)
        v1.show_pan_mark(True)
        v1.set_callback('drag-drop', self.drop_file)
        v1.set_callback('none-move', self.motion)
        v1.set_bg(0.2, 0.2, 0.2)
        v1.ui_setActive(True)
        v1.set_name('tweedledee')
        self.viewer1 = v1
        self._mi1 = ModeIndicator(v1)

        bd = v1.get_bindings()
        bd.enable_all(True)

        # shared canvas between the two viewers
        shcanvas = self.dc.DrawingCanvas()
        # Tell viewer1 to use this canvas
        v1.set_canvas(shcanvas)

        v1.set_desired_size(300, 300)
        iw = Viewers.GingaViewerWidget(viewer=v1)
        hbox.add_widget(iw, stretch=1)

        # Add a second viewer viewing the same canvas
        v2 = Viewers.CanvasView(logger)
        v2.enable_autocuts('on')
        v2.set_autocut_params('zscale')
        v2.enable_autozoom('on')
        v2.set_zoom_algorithm('rate')
        v2.set_zoomrate(1.4)
        v2.show_pan_mark(True)
        v2.set_callback('drag-drop', self.drop_file)
        v2.set_callback('none-move', self.motion)
        v2.set_bg(0.2, 0.2, 0.2)
        v2.ui_setActive(True)
        v1.set_name('tweedledum')
        self.viewer2 = v2
        self._mi2 = ModeIndicator(v2)

        # Tell viewer2 to use this same canvas
        v2.set_canvas(shcanvas)

        bd = v2.get_bindings()
        bd.enable_all(True)

        v2.set_desired_size(300, 300)
        iw = Viewers.GingaViewerWidget(viewer=v2)
        hbox.add_widget(iw, stretch=1)

        # 2nd canvas as a subcanvas of the shared canvas
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.register_for_cursor_drawing(v1)
        canvas.register_for_cursor_drawing(v2)
        canvas.set_drawtype('rectangle', color='lightblue')
        self.canvas = canvas
        shcanvas.add(self.canvas)
        shcanvas.ui_setActive(True)
        canvas.ui_setActive(True)
        canvas.set_surface(v1)

        self.drawtypes = canvas.get_drawtypes()
        self.drawtypes.sort()

        vbox.add_widget(hbox, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        hbox = Widgets.HBox()
        hbox.set_border_width(2)

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
        wopen = Widgets.Button("Open File")
        wopen.add_callback('activated', lambda w: self.open_file())
        wquit = Widgets.Button("Quit")
        wquit.add_callback('activated', lambda w: self.quit())

        hbox.add_widget(Widgets.Label(''), stretch=1)
        for w in (wopen, wdrawtype, wdrawcolor, wfill,
                  Widgets.Label('Alpha:'), walpha, wclear, wquit):
            hbox.add_widget(w, stretch=0)

        vbox.add_widget(hbox, stretch=0)

        mode = self.canvas.get_draw_mode()
        hbox = Widgets.HBox()
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

        ## btn3 = Widgets.CheckBox("I'm using a trackpad")
        ## btn3.add_callback('activated', lambda w, tf: self.use_trackpad_cb(tf))
        ## hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        self.top.set_widget(vbox)

    def set_drawparams(self):
        index = self.wdrawtype.get_index()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.get_index()
        fill = self.wfill.get_state()
        alpha = self.walpha.get_value()
        coord = 'data'

        params = { 'color': self.drawcolors[index],
                   'alpha': alpha,
                   'coord': coord,
                   }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.delete_all_objects()

    def load_file(self, viewer, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        viewer.set_image(image)
        self.top.set_title(filepath)

    def open_file(self):
        res = Widgets.FileDialog.getOpenFileName(self, "Open FITS file",
                                                     ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(self.viewer1, fileName)

    def drop_file(self, viewer, paths):
        fileName = paths[0]
        #print(fileName)
        self.load_file(viewer, fileName)

    def motion(self, viewer, button, data_x, data_y):

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
            self.logger.warning("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

    def set_mode_cb(self, mode, tf):
        self.logger.info("canvas mode changed (%s) %s" % (mode, tf))
        if not (tf is False):
            self.canvas.set_draw_mode(mode)
        return True

    def closed(self, w):
        self.logger.info("Top window closed.")
        self.top = None
        sys.exit()

    def quit(self, *args):
        self.logger.info("Attempting to shut down the application...")
        if not self.top is None:
            self.top.close()
        sys.exit()

    def mainloop(self):
        while True:
            self.app.process_events()


def main(options, args):

    logger = log.get_logger("example2", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    viewer = FitsViewer(logger)

    viewer.top.resize(700, 540)

    if len(args) > 0:
        viewer.load_file(viewer.viewer1, args[0])

    viewer.top.show()
    viewer.top.raise_()

    try:
        app = viewer.top.get_app()
        app.mainloop()

    except KeyboardInterrupt:
        print("Terminating viewer...")
        if viewer.top is not None:
            viewer.top.close()

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
                      type='int', default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                      default='qt',
                      help="Choose GUI toolkit (gtk|qt)")
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
