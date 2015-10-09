#! /usr/bin/env python
#
# example5_mpl.py -- Load a fits file into a Ginga widget with a
#          matplotlib backend.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
#
"""
   $ ./example5_mpl.py [fits file]

This example program shows to capture button and keypress events
for your own use.  After loading a FITS file use the following keys:

Press 'x' to turn on capture of events and bypass most normal keystroke
processing. Press it again to resume normal processing.  An on-screen
message will tell you which mode you are in.

While in 'capture mode' you can draw points with the right mouse button.
Press 'c' to clear the canvas of drawn points.
"""
from __future__ import print_function
import sys, os
import platform
# just in case you want to use qt
os.environ['QT_API'] = 'pyqt'

import matplotlib
options = ['Qt4Agg', 'GTK', 'GTKAgg', 'MacOSX', 'GTKCairo', 'WXAgg',
           'TkAgg', 'QtAgg', 'FltkAgg', 'WX']
# Force a specific toolkit on mac
macos_ver = platform.mac_ver()[0]
if len(macos_ver) > 0:
    # change this to "pass" if you want to force a different backend
    # On Mac OS X I found the default choice for matplotlib is not stable
    # with ginga
    matplotlib.use('Qt4Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

from ginga.mplw.ImageViewCanvasMpl import ImageViewCanvas
from ginga.mplw.ImageViewCanvasTypesMpl import DrawingCanvas
from ginga.AstroImage import AstroImage
from ginga.misc import log
from ginga import cmap

# Set to True to get diagnostic logging output
use_logger = False

class MyGingaFigure(object):
    def __init__(self, logger, fig):
        self.logger = logger
        # create a ginga object and tell it about the figure
        fi = ImageViewCanvas(logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.add_callback('key-press', self.key_press_ginga)
        fi.set_figure(fig)
        self.fitsimage = fi

        # enable all interactive features
        fi.get_bindings().enable_all(True)

        canvas = DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_callback('button-press', self.btn_down)
        #canvas.set_callback('motion', self.drag)
        canvas.set_callback('button-release', self.btn_up)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_event)
        canvas.add_callback('key-press', self.key_press)
        canvas.setSurface(self.fitsimage)
        canvas.ui_setActive(True)
        self.canvas = canvas

    def load(self, fitspath):
        # load an image
        image = AstroImage(self.logger)
        image.load_file(fitspath)
        self.fitsimage.set_image(image)

    def capture(self):
        """
        Insert our canvas so that we intercept all events before they reach
        processing by the bindings layer of Ginga.
        """
        # insert the canvas 
        self.fitsimage.add(self.canvas, tag='mycanvas')

    def release(self):
        """
        Remove our canvas so that we no longer intercept events.
        """
        # retract the canvas 
        self.fitsimage.deleteObjectByTag('mycanvas')

    def clear(self):
        """
        Clear the canvas of any drawing made on it.
        """
        self.canvas.deleteAllObjects()

    def get_wcs(self, data_x, data_y):
        """Return (re_deg, dec_deg) for the (data_x, data_y) position
        based on any WCS associated with the loaded image.
        """
        img = self.fitsimage.get_image()
        ra, dec = img.pixtoradec(data_x, data_y)
        return ra, dec

    # CALLBACKS
    # NOTE: return values on callbacks are important: if True then lower
    # layer Ginga canvas items will not get events

    def key_press(self, canvas, keyname):
        if keyname == 'x':
            self.fitsimage.onscreen_message("Moving to regular mode",
                                            delay=1.0)
            self.release()
        elif keyname == 'c':
            self.clear()
            return True
        
        fi = canvas.fitsimage
        data_x, data_y = fi.get_last_data_xy()
        ra, dec = self.get_wcs(data_x, data_y)
        print("key %s pressed at data %d,%d ra=%s dec=%s" % (
            keyname, data_x, data_y, ra, dec))
        return True

    def key_press_ginga(self, fitsimage, keyname):
        if keyname == 'x':
            self.fitsimage.onscreen_message("Moving to capture mode",
                                            delay=1.0)
            self.capture()
        return True

    def btn_down(self, canvas, button, data_x, data_y):
        ra, dec = self.get_wcs(data_x, data_y)
        print("button %s pressed at data %d,%d ra=%s dec=%s" % (
            button, data_x, data_y, ra, dec))
        return False

    def btn_up(self, canvas, button, data_x, data_y):
        ra, dec = self.get_wcs(data_x, data_y)
        print("button %s released at data %d,%d ra=%s dec=%s" % (
            button, data_x, data_y, ra, dec))
        return False

    def draw_event(self, canvas, tag):
        obj = canvas.getObjectByTag(tag)
        data_x, data_y = obj.x, obj.y
        ra, dec = self.get_wcs(data_x, data_y)
        print("A %s was drawn at data %d,%d ra=%s dec=%s" % (
            obj.kind, data_x, data_y, ra, dec))
        return True


# create a regular matplotlib figure
fig = plt.figure()

# Here is our object
logger = log.get_logger(null=not use_logger, log_stderr=True)
foo = MyGingaFigure(logger, fig)

# load an image, if one was provided
if len(sys.argv) > 1:
    foo.load(sys.argv[1])

# Press 'x' to turn on capture of events. Press it again to resume normal
#   processing of events.
# Press 'c' to clear the canvas of drawn points.
plt.show()
