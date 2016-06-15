#! /usr/bin/env python
#
# example2.py -- Simple, configurable FITS viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, os
import logging
import threading

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

        from ginga.gw import Widgets, Viewers, GwHelp

        self.app = Widgets.Application(logger=logger)
        self.app.add_callback('shutdown', self.quit)
        self.top = self.app.make_window("Ginga example2")
        self.top.add_callback('close', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        fi = Viewers.CanvasView(logger=logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # add a color bar
        fi.private_canvas.add(self.dc.ColorBar(side='bottom', offset=10))

        # add little mode indicator that shows modal states in
        # lower left hand corner
        fi.private_canvas.add(self.dc.ModeIndicator(corner='ur', fontsize=14))
        # little hack necessary to get correct operation of the mode indicator
        # in all circumstances
        bm = fi.get_bindmap()
        bm.add_callback('mode-set', lambda *args: fi.redraw(whence=3))

        # canvas that we will draw on
        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.enable_edit(True)
        canvas.set_drawtype('rectangle', color='lightblue', coord='data')
        canvas.setSurface(fi)
        self.canvas = canvas
        # add canvas to view
        fi.get_canvas().add(canvas)
        canvas.ui_setActive(True)
        canvas.register_for_cursor_drawing(fi)
        canvas.add_callback('draw-event', self.draw_cb)

        self.drawtypes = canvas.get_drawtypes()
        self.drawtypes.sort()

        fi.set_desired_size(512, 512)
        iw = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(iw, stretch=1)

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

        btn3 = Widgets.RadioButton("Pick", group=btn1)
        btn3.set_state(mode == 'pick')
        btn3.add_callback('activated', lambda w, val: self.set_mode_cb('pick', val))
        btn3.set_tooltip("Choose this to pick things on the canvas")
        hbox.add_widget(btn3)

        hbox.add_widget(Widgets.Label(''), stretch=1)
        vbox.add_widget(hbox, stretch=0)

        self.top.set_widget(vbox)

        self.fs = None
        if hasattr(GwHelp, 'FileSelection'):
            self.fs = GwHelp.FileSelection(self.top.get_widget())

    def set_drawparams(self):
        index = self.wdrawtype.get_index()
        kind = self.drawtypes[index]
        index = self.wdrawcolor.get_index()
        fill = self.wfill.get_state()
        alpha = self.walpha.get_value()

        params = { 'color': self.drawcolors[index],
                   'alpha': alpha,
                   }
        if kind in ('circle', 'rectangle', 'polygon', 'triangle',
                    'righttriangle', 'ellipse', 'square', 'box'):
            params['fill'] = fill
            params['fillalpha'] = alpha

        self.canvas.set_drawtype(kind, **params)

    def clear_canvas(self):
        self.canvas.deleteAllObjects()

    def load_file(self, filepath):
        image = AstroImage.AstroImage(logger=self.logger)
        image.load_file(filepath)

        self.fitsimage.set_image(image)
        self.top.set_title(filepath)

    def open_file(self):
        self.fs.popup("Open FITS file", self.load_file)

    def drop_file(self, fitsimage, paths):
        fileName = paths[0]
        #print(fileName)
        self.load_file(fileName)

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

    def draw_cb(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
        obj.add_callback('pick-down', self.pick_cb)
        obj.add_callback('edited', self.edit_cb)

    def pick_cb(self, obj, canvas, event, pt):
        self.logger.info("pick point is %s" % (str(pt)))
        return True

    def edit_cb(self, obj):
        self.logger.info("object %s has been edited" % (obj.kind))
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


def main(options, args):

    logger = log.get_logger("example2", options=options)

    if options.toolkit is None:
        logger.error("Please choose a GUI toolkit with -t option")

    # decide our toolkit, then import
    ginga_toolkit.use(options.toolkit)

    viewer = FitsViewer(logger)

    viewer.top.resize(700, 540)

    if len(args) > 0:
        viewer.load_file(args[0])

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
    optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                      default='qt',
                      help="Choose GUI toolkit (gtk|qt)")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    log.addlogopts(optprs)

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
