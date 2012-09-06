#
# ColorBar.py -- color bar widget
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Wed Sep  5 15:08:09 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import math

import gtk, gobject, cairo

import Callback
import RGBMap

class ColorBarError(Exception):
    pass

# Create a GTK+ widget on which we will draw using Cairo
class ColorBar(gtk.DrawingArea, Callback.Callbacks):

    # Draw in response to an expose-event
    #__gsignals__ = { "expose-event": "override" }

    def __init__(self, logger, rgbmap=None):
        gtk.DrawingArea.__init__(self)
        Callback.Callbacks.__init__(self)
        
        self.pixmap = None
        self.gc = None
        self.logger = logger

        if not rgbmap:
            rgbmap = RGBMap.RGBMapper()
        self.set_rgbmap(rgbmap)

        self._start_x = 0
        # for drawing range
        self.t_showrange = True
        self.t_font = 'Sans Serif'
        self.t_fontsize = 10
        self.t_spacing = 40
        self.loval = 0
        self.hival = 0
        self._interval = {}
        self._avg_pixels_per_range_num = 70.0
        
        # For callbacks
        for name in ('motion', 'scroll'):
            self.enable_callback(name)

        self.connect("expose_event", self.expose_event)
        self.connect("configure_event", self.configure_event)
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
        # TODO
        #rgbmap.add_callback('changed', self.rgbmap_cb)
        self.redraw()

    # TODO: deprecate these two?
    def set_cmap(self, cm):
        self.rgbmap.set_cmap(cm)

    def set_imap(self, im, reset=False):
        self.rgbmap.set_imap(im)
        
    def set_range(self, loval, hival, redraw=True):
        self.loval = loval
        self.hival = hival
        # Calculate reasonable spacing for range numbers
        cr = self.window.cairo_create()
        text = "%d" % (int(hival))
        a, b, _wd, _ht, _i, _j = cr.text_extents(text)
        self._avg_pixels_per_range_num = self.t_spacing + _wd
        if self.t_showrange and redraw:
            self.redraw()
        
    def configure_event(self, widget, event):
        self.pixmap = None
        x, y, width, height = widget.get_allocation()
        pixmap = gtk.gdk.Pixmap(None, width, height, 24)
        self.gc = pixmap.new_gc()
        pixmap.draw_rectangle(self.gc, True, 0, 0, width, height)
        self.pixmap = pixmap
        self.width = width
        self.height = height
        # calculate intervals for range numbers
        nums = width // self._avg_pixels_per_range_num
        spacing = 256 // nums
        self._interval = {}
        for i in xrange(nums):
            self._interval[i*spacing] = True
        self.logger.debug("nums=%d spacing=%d intervals=%s" % (
            nums, spacing, self._interval))

        self.redraw()

    def expose_event(self, widget, event):
        # When an area of the window is exposed, we just copy out of the
        # server-side, off-screen pixmap to that area.
        x , y, width, height = event.area
        self.logger.debug("pixmap is %s" % self.pixmap)
        if self.pixmap != None:
            # redraw the screen from backing pixmap
            if not self.gc:
                self.gc = widget.new_gc()
            widget.window.draw_drawable(self.gc, self.pixmap, x, y, x, y,
                                        width, height)
        return False

    # Handle the expose-event by drawing
    def do_expose_event(self, event):

        # Create the cairo context
        cr = self.window.cairo_create()

        # TODO:
        ## # Restrict Cairo to the exposed area; avoid extra work
        ## cr.rectangle(event.area.x, event.area.y,
        ##              event.area.width, event.area.height)
        ## cr.clip()

        ## self.draw(cr, *self.window.get_size())
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
        #print "clr is %dx%d width=%d rem=%d ival=%d" % (
        #    rect.width, rect.height, clr_wd, rem_px, ival)

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
            if self.t_showrange and self._interval.has_key(i):
                pct = float(i) / 256.0
                val = int(self.loval + pct * (self.hival - self.loval))
                text = "%d" % (val)
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
            cr.stroke_preserve()
            #cr.fill()
            # number
            cr.move_to(x, y)
            cr.show_text(text)

    def draw(self, cr):
        return self._draw(cr)


    def redraw(self):
        ## if not self.window:
        ##     return
        ## cr = self.window.cairo_create()
        if not self.pixmap:
            return
        cr = self.pixmap.cairo_create()
        self.draw(cr)

        win = self.window
        win.invalidate_rect(None, True)
        # Process expose events right away so window is responsive
        # to scrolling
        win.process_updates(True)

    def shift_colormap(self, pct):
        if pct > 0.0:
            self.rgbmap.rshift(pct)
        else:
            self.rgbmap.lshift(math.fabs(pct))

        self.redraw()

    def rgbmap_cb(self, rgbmap):
        self.redraw()
    
    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = event.button
        ## print "button event at %dx%d, button=%d" % (x, y, button)
        if button == 1:
            self._start_x = x
            return True
                
        ## return self.make_callback('button-press', event)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = event.button
        #print "button release at %dx%d button=%d" % (x, y, button)
        if button == 1:
            dx = x - self._start_x
            wd, ht = self.window.get_size()
            pct = float(dx) / float(wd)
            #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
            self.shift_colormap(pct)
            return True

        elif button == 3:
            self.rgbmap.reset_cmap()
            return True
            
        ## return self.make_callback('button-release', event)

    def motion_notify_event(self, widget, event):
        button = 0
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x, y, state = event.x, event.y, event.state

        btn1_down = state & gtk.gdk.BUTTON1_MASK
        if btn1_down:
            dx = x - self._start_x
            wd, ht = self.window.get_size()
            pct = float(dx) / float(wd)
            #print "dx=%f wd=%d pct=%f" % (dx, wd, pct)
            self.shift_colormap(pct)
            return True

        pct = float(x) / float(self.width)
        value = int(self.loval + pct * (self.hival - self.loval))
        return self.make_callback('motion', value, event)

    def scroll_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        #print "scroll at %dx%d event=%s" % (x, y, str(event))

        return self.make_callback('scroll', event)

#END
