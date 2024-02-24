#! /usr/bin/env python
#
# example5_mpl.py -- Load a fits file into a Ginga widget with a
#          matplotlib backend.
#
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

import sys
import matplotlib.pyplot as plt

from ginga.mplw.ImageViewMpl import CanvasView
from ginga.canvas.CanvasObject import get_canvas_types
from ginga.misc import log
from ginga.util.loader import load_data

# Set to True to get diagnostic logging output
use_logger = False


class MyGingaFigure(object):
    def __init__(self, logger, fig):
        self.logger = logger
        # create a ginga object and tell it about the figure
        fi = CanvasView(logger=logger)
        fi.enable_autocuts('on')
        fi.set_autocut_params('zscale')
        fi.set_figure(fig)
        fi.show_mode_indicator(True, corner='ur')
        self.fitsimage = fi

        p_canvas = fi.get_canvas()
        p_canvas.add_callback('key-down-none', self.key_press_ginga)

        self.dc = get_canvas_types()

        # enable all interactive features
        fi.get_bindings().enable_all(True)

        canvas = self.dc.DrawingCanvas()
        canvas.enable_draw(True)
        canvas.set_draw_mode('draw')
        canvas.set_callback('btn-down-none', self.btn_down)
        canvas.set_callback('btn-up-none', self.btn_up)
        canvas.set_drawtype('point', color='cyan')
        canvas.set_callback('draw-event', self.draw_event)
        canvas.add_callback('key-down-none', self.key_press)
        canvas.set_surface(self.fitsimage)
        canvas.ui_set_active(True)
        self.canvas = canvas

    def load(self, fitspath):
        # load an image
        image = load_data(fitspath, logger=self.logger)
        self.fitsimage.set_image(image)

    def capture(self):
        """
        Insert our canvas so that we intercept all events before they reach
        processing by the bindings layer of Ginga.
        """
        # insert the canvas
        p_canvas = self.fitsimage.get_canvas()
        p_canvas.add(self.canvas, tag='mycanvas')

    def release(self):
        """
        Remove our canvas so that we no longer intercept events.
        """
        # retract the canvas
        p_canvas = self.fitsimage.get_canvas()
        p_canvas.delete_object_by_tag('mycanvas')

    def clear(self):
        """
        Clear the canvas of any drawing made on it.
        """
        self.canvas.delete_all_objects()

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

    def key_press(self, canvas, event, data_x, data_y):
        keyname = event.key
        if keyname == 'x':
            self.fitsimage.onscreen_message("Moving to regular mode",
                                            delay=1.0)
            self.release()
            return True
        elif keyname == 'c':
            self.clear()
            return True

        fi = self.fitsimage
        data_x, data_y = fi.get_last_data_xy()
        ra, dec = self.get_wcs(data_x, data_y)
        print("key %s pressed at data %d,%d ra=%s dec=%s" % (
            keyname, data_x, data_y, ra, dec))
        return True

    def key_press_ginga(self, canvas, event, data_x, data_y):
        keyname = event.key
        if keyname == 'x':
            self.fitsimage.onscreen_message("Moving to capture mode",
                                            delay=1.0)
            self.capture()
        return True

    def btn_down(self, canvas, event, data_x, data_y):
        ra, dec = self.get_wcs(data_x, data_y)
        print("button %s pressed at data %d,%d ra=%s dec=%s" % (
            event.button, data_x, data_y, ra, dec))
        return False

    def btn_up(self, canvas, event, data_x, data_y):
        ra, dec = self.get_wcs(data_x, data_y)
        print("button %s released at data %d,%d ra=%s dec=%s" % (
            event.button, data_x, data_y, ra, dec))
        return False

    def draw_event(self, canvas, tag):
        obj = canvas.get_object_by_tag(tag)
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
