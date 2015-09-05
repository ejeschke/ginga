#! /usr/bin/env python
#
# example2.py -- Simple, configurable FITS viewer.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, os
import logging

from ginga import AstroImage, colors
import ginga.toolkit as ginga_toolkit
from ginga.misc import log


class FitsViewer(object):

    def __init__(self, logger):
        self.logger = logger

        from ginga.gw import Widgets, Viewers

        self.app = Widgets.Application()
        self.app.add_callback('shutdown', self.quit)
        self.top = self.app.window("Ginga example2")
        self.top.add_callback('closed', self.closed)

        vbox = Widgets.VBox()
        vbox.set_border_width(2)
        vbox.set_spacing(1)

        self.drawcolors = colors.get_colors()

        fi = Viewers.ImageViewCanvas(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.enable_autozoom('on')
        fi.set_zoom_algorithm('rate')
        fi.set_zoomrate(1.4)
        fi.show_pan_mark(True)
        fi.enable_draw(False)
        fi.set_callback('drag-drop', self.drop_file)
        fi.set_callback('none-move', self.motion)
        fi.set_bg(0.2, 0.2, 0.2)
        fi.ui_setActive(True)
        self.fitsimage = fi

        bd = fi.get_bindings()
        bd.enable_all(True)

        # canvas that we will draw on
        DrawingCanvas = fi.getDrawClass('drawingcanvas')
        canvas = DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_drawtype('rectangle', color='lightblue')
        canvas.setSurface(fi)
        self.canvas = canvas
        # add canvas to view
        fi.add(canvas)
        canvas.ui_setActive(True)

        fi.set_desired_size(512, 512)
        vbox.add_widget(fi, stretch=1)

        self.readout = Widgets.Label("")
        vbox.add_widget(self.readout, stretch=0)

        hbox = Widgets.HBox()
        hbox.set_border_width(2)

        wdrawtype = Widgets.ComboBox()
        self.drawtypes = fi.get_drawtypes()
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

        self.top.set_widget(vbox)

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
        res = Widgets.FileDialog.getOpenFileName(self, "Open FITS file",
                                                     ".", "FITS files (*.fits)")
        if isinstance(res, tuple):
            fileName = res[0]
        else:
            fileName = str(res)
        if len(fileName) != 0:
            self.load_file(fileName)

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
            self.logger.warn("Bad coordinate conversion: %s" % (
                str(e)))
            ra_txt  = 'BAD WCS'
            dec_txt = 'BAD WCS'

        text = "RA: %s  DEC: %s  X: %.2f  Y: %.2f  Value: %s" % (
            ra_txt, dec_txt, fits_x, fits_y, value)
        self.readout.set_text(text)

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
        w.load_file(args[0])

    viewer.top.show()
    viewer.top.raise_()

    try:
        viewer.app.mainloop()

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
