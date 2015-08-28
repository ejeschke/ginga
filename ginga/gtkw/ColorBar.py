#
# ColorBar.py -- color bar widget
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math
import numpy

from ginga.gtkw import gtksel
from ginga.gtkw.GtkHelp import get_scroll_info
import gtk, gobject, cairo

from ginga.misc import Callback
from ginga import RGBMap

class ColorBarError(Exception):
    pass

# Create a GTK+ widget on which we will draw using Cairo
class ColorBar(gtk.DrawingArea, Callback.Callbacks):

    # Draw in response to an expose-event
    #__gsignals__ = { "expose-event": "override" }

    def __init__(self, logger, rgbmap=None, link=False):
        gtk.DrawingArea.__init__(self)
        Callback.Callbacks.__init__(self)

        self.surface = None
        self.logger = logger
        self.link_rgbmap = link

        if not rgbmap:
            rgbmap = RGBMap.RGBMapper(logger)
        self.set_rgbmap(rgbmap)

        self._start_x = 0
        # for drawing range
        self.t_showrange = True
        self.t_font = 'Sans Serif'
        self.t_fontsize = 10
        self.t_spacing = 40
        self.loval = 0.0
        self.hival = 0.0
        self._interval = {}
        self._avg_pixels_per_range_num = 70
        self.mark_pos = None

        # For callbacks
        for name in ('motion', 'scroll'):
            self.enable_callback(name)

        if not gtksel.have_gtk3:
            self.connect("expose_event", self.expose_event)
        else:
            self.connect("draw", self.draw_event)
        self.connect("configure_event", self.configure_event)
        self.connect("size-request", self.size_request)
        self.connect("motion_notify_event", self.motion_notify_event)
        self.connect("button_press_event", self.button_press_event)
        self.connect("button_release_event", self.button_release_event)
        self.connect("scroll_event", self.scroll_event)
        mask = self.get_events()
        self.set_events(mask
                        | gtk.gdk.EXPOSURE_MASK
                        | gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK
                        | gtk.gdk.POINTER_MOTION_MASK
                        | gtk.gdk.POINTER_MOTION_HINT_MASK
                        | gtk.gdk.SCROLL_MASK)


    def get_rgbmap(self):
        return self.rgbmap

    def set_rgbmap(self, rgbmap):
        self.rgbmap = rgbmap
        # TODO: figure out if we can get rid of this link option
        if self.link_rgbmap:
            rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw()

    # TODO: deprecate these two?
    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)
        self.redraw()

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)
        self.redraw()

    def set_range(self, loval, hival):
        self.loval = float(loval)
        self.hival = float(hival)
        # Calculate reasonable spacing for range numbers
        text = "%.4g" % (hival)
        try:
            win = self.get_window()
            if win is not None:
                cr = win.cairo_create()
                a, b, _wd, _ht, _i, _j = cr.text_extents(text)
                self._avg_pixels_per_range_num = self.t_spacing + _wd
        except Exception as e:
            self.logger.error("Error getting text extents: %s" % (
                str(e)))
        if self.t_showrange:
            self.redraw()

    def configure_event(self, widget, event):
        self.surface = None
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height
        arr8 = numpy.zeros(height*width*4).astype(numpy.uint8)
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_RGB24,
                                                            width)
        surface = cairo.ImageSurface.create_for_data(arr8,
                                                     cairo.FORMAT_RGB24,
                                                     width, height, stride)
        self.surface = surface
        self.width = width
        self.height = height
        # calculate intervals for range numbers
        nums = max(int(width // self._avg_pixels_per_range_num), 1)
        spacing = 256 // nums
        self._interval = {}
        for i in range(nums):
            self._interval[i*spacing] = True
        self.logger.debug("nums=%d spacing=%d intervals=%s" % (
            nums, spacing, self._interval))

        self.redraw()

    def size_request(self, widget, requisition):
        """Callback function to request our desired size.
        """
        requisition.width = -1
        requisition.height = 15
        return True

    # For Gtk3
    def draw_event(self, widget, cr):
        if self.surface is not None:
            self.logger.debug("surface is %s" % self.surface)
            cr.set_source_surface(self.surface, 0, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
        return False

    def expose_event(self, widget, event):
        # When an area of the window is exposed, we just copy out of the
        # server-side, off-screen pixmap to that area.
        x , y, width, height = event.area
        self.logger.debug("surface is %s" % self.surface)
        if self.surface is not None:
            win = widget.get_window()
            cr = win.cairo_create()
            # set clip area for exposed region
            cr.rectangle(x, y, width, height)
            cr.clip()
            # repaint from off-screen surface
            cr.set_source_surface(self.surface, 0, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()
        return False

    # Handle the expose-event by drawing
    def do_expose_event(self, event):

        # Create the cairo context
        win = self.get_window()
        cr = win.cairo_create()

        # TODO:
        ## # Restrict Cairo to the exposed area; avoid extra work
        ## cr.rectangle(event.area.x, event.area.y,
        ##              event.area.width, event.area.height)
        ## cr.clip()

        ## win = self.get_window()
        ## self.draw(cr, *win.get_size())
        self.draw(cr)


    def _draw(self, cr):
        rect = self.get_allocation()

        # TODO: fill with white?

        x1 = 0; x2 = rect.width
        clr_wd = rect.width // 256
        rem_px = x2 - (clr_wd * 256)
        if rem_px > 0:
            ival = 256 // rem_px
        else:
            ival = 0
        clr_ht = rect.height
        #print("clr is %dx%d width=%d rem=%d ival=%d" % (
        #    rect.width, rect.height, clr_wd, rem_px, ival))

        dist = self.rgbmap.get_dist()

        j = ival; off = 0
        range_pts = []
        for i in range(256):

            wd = clr_wd
            if rem_px > 0:
                j -= 1
                if j == 0:
                    rem_px -= 1
                    j = ival
                    wd += 1
            x = off

            (r, g, b) = self.rgbmap.get_rgbval(i)
            r = float(r) / 255.0
            g = float(g) / 255.0
            b = float(b) / 255.0
            cr.set_source_rgb(r, g, b)
            cr.rectangle(x, 0, wd, clr_ht)
            cr.fill()

            # Draw range scale if we are supposed to
            if self.t_showrange and i in self._interval:
                #cb_pct = float(i) / 256.0
                cb_pct = float(x) / rect.width
                # get inverse of distribution function and calculate value
                # at this position
                rng_pct = dist.get_dist_pct(cb_pct)
                val = float(self.loval + (rng_pct * (self.hival - self.loval)))
                text = "%.4g" % (val)
                a, b, _wd, _ht, _i, _j = cr.text_extents(text)

                rx = x
                ry = 4 + _ht
                range_pts.append((rx, ry, text))

            off += wd

        # draw range
        cr.select_font_face(self.t_font)
        cr.set_font_size(self.t_fontsize)
        cr.set_source_rgb(0.0, 0.0, 0.0)
        cr.set_line_width(1)

        for (x, y, text) in range_pts:
            # tick
            cr.move_to (x, 0)
            cr.line_to (x, 2)
            cr.close_path()
            cr.stroke()
            #cr.fill()
            # number
            cr.move_to(x, y)
            cr.show_text(text)

        # Draw moving value wedge
        if self.mark_pos is not None:
            cr.set_source_rgb(1.0, 0.0, 0.0)
            cr.set_line_width(3)
            cr.move_to (self.mark_pos-4, self.height)
            cr.line_to (self.mark_pos, self.height//2)
            cr.line_to (self.mark_pos+4, self.height)
            cr.line_to (self.mark_pos-4, self.height)
            cr.fill()

    def draw(self, cr):
        return self._draw(cr)


    def redraw(self):
        win = self.get_window()
        ## if not win:
        ##     return
        ## cr = win.cairo_create()
        if not self.surface:
            return
        cr = cairo.Context(self.surface)
        self.draw(cr)

        win.invalidate_rect(None, True)
        # Process expose events right away so window is responsive
        # to scrolling
        win.process_updates(True)

    def set_current_value(self, value):
        range = self.hival - self.loval
        if value < self.loval:
            value = self.loval
        elif value > self.hival:
            value = self.hival

        pct = float(value - self.loval) / float(range)
        self.mark_pos = int(pct * self.width)
        #print("mark position is %d (%.2f)" % (self.mark_pos, pct))
        self.redraw()

    def shift_colormap(self, pct):
        self.rgbmap.set_sarr(self._sarr, callback=False)
        self.rgbmap.shift(pct)
        self.redraw()

    def stretch_colormap(self, pct):
        self.rgbmap.stretch(pct)
        self.redraw()

    def rgbmap_cb(self, rgbmap):
        self.redraw()

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = event.button
        ## print("button event at %dx%d, button=%d" % (x, y, button))
        if button == 1:
            self._start_x = x
            sarr = self.rgbmap.get_sarr()
            self._sarr = sarr.copy()
            return True

        ## return self.make_callback('button-press', event)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = event.button
        win = self.get_window()
        #print("button release at %dx%d button=%d" % (x, y, button))
        if button == 1:
            dx = x - self._start_x
            #wd, ht = win.get_size()
            geom = win.get_geometry()
            wd, ht = geom[2], geom[3]
            pct = float(dx) / float(wd)
            #print("dx=%f wd=%d pct=%f" % (dx, wd, pct))
            self.shift_colormap(pct)
            return True

        elif button == 3:
            self.rgbmap.reset_cmap()
            return True

        ## return self.make_callback('button-release', event)

    def motion_notify_event(self, widget, event):
        button = 0
        if event.is_hint:
            tup = event.window.get_pointer()
            if gtksel.have_gtk3:
                xx, x, y, state = tup
            else:
                x, y, state = tup
        else:
            x, y, state = event.x, event.y, event.state

        btn1_down = state & gtk.gdk.BUTTON1_MASK
        if btn1_down:
            win = self.get_window()
            dx = x - self._start_x
            #wd, ht = win.get_size()
            geom = win.get_geometry()
            wd, ht = geom[2], geom[3]
            pct = float(dx) / float(wd)
            #print("dx=%f wd=%d pct=%f" % (dx, wd, pct))
            self.shift_colormap(pct)
            return True

        dist = self.rgbmap.get_dist()
        pct = float(x) / float(self.width)
        rng_pct = dist.get_dist_pct(pct)
        value = float(self.loval + (rng_pct * (self.hival - self.loval)))
        return self.make_callback('motion', value, event)

    def scroll_event(self, widget, event):
        # event.button, event.x, event.y
        num_degrees, direction = get_scroll_info(event)

        if (direction < 90.0) or (direction > 270.0):
            # up
            scale_factor = 1.1
        else:
            # not up!
            scale_factor = 0.9

        self.stretch_colormap(scale_factor)

        return self.make_callback('scroll', event)

#END
