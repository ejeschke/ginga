#
# FitsImageGtk.py -- classes for the display of FITS files in Gtk widgets
# 
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Fri Jun 22 13:41:32 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import gobject
import gtk
import cairo

import warnings
warnings.filterwarnings("ignore")

import FitsImage
import Mixins

class FitsImageGtkError(FitsImage.FitsImageError):
    pass

class FitsImageGtk(FitsImage.FitsImageBase):

    def __init__(self, logger=None):
        #super(FitsImageGtk, self).__init__(logger=logger)
        FitsImage.FitsImageBase.__init__(self, logger=logger)

        imgwin = gtk.DrawingArea()
        imgwin.connect("expose_event", self.expose_event)
        imgwin.connect("configure_event", self.configure_event)
        imgwin.set_events(gtk.gdk.EXPOSURE_MASK)
        self.imgwin = imgwin
        self.gc = None
        self.pixmap = None
        self.imgwin.show_all()

        self.message = None
        self.msgtask = None
        self.set_bg(0.5, 0.5, 0.5, redraw=False)
        self.set_fg(1.0, 1.0, 1.0, redraw=False)
        
        # cursors
        self.cursor = {}

    def get_widget(self):
        return self.imgwin

    def _render_offscreen(self, drawable, gc, data, dst_x, dst_y,
                          width, height):
        # NOTE [A]
        daht, dawd, depth = data.shape
        self.logger.debug("data shape is %dx%dx%d" % (dawd, daht, depth))

        # Get RGB buffer for copying pixel data
        rgb_buf = self._get_rgbbuf(data)
                              
        # fill pixmap with background color
        imgwin_wd, imgwin_ht = self.get_window_size()
        drawable.draw_rectangle(gc, True, 0, 0,
                                imgwin_wd, imgwin_ht)

        # draw image data from buffer to offscreen pixmap
        drawable.draw_rgb_image(gc, dst_x, dst_y, width,
                                height, gtk.gdk.RGB_DITHER_NORMAL,
                                rgb_buf, dawd*3)

        # render self.message
        if self.message:
            self.draw_message(drawable, imgwin_wd, imgwin_ht,
                              self.message)

    def draw_message(self, drawable, width, height, message):
        cr = drawable.cairo_create()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.select_font_face('Sans Serif')
        cr.set_font_size(24.0)
        a, b, wd, ht, i, j = cr.text_extents(message)
        y = ((height // 3) * 2) - (ht // 2)
        x = (width // 2) - (wd // 2)
        cr.move_to(x, y)
        cr.show_text(self.message)
        

    def render_offscreen(self, data, dst_x, dst_y, width, height):
        self.logger.debug("redraw pixmap=%s gc=%s" % (self.pixmap, self.gc))
        if (self.pixmap == None) or (self.gc == None):
            return
        self.logger.debug("drawing to pixmap")
        return self._render_offscreen(self.pixmap, self.gc, data, dst_x, dst_y,
                                      width, height)


    def configure(self, width, height):
        #pixmap = gtk.gdk.Pixmap(widget.window, width, height)
        pixmap = gtk.gdk.Pixmap(None, width, height, 24)
        self.gc = self._get_gc(pixmap)
        pixmap.draw_rectangle(self.gc, True, 0, 0, width, height)
        self.pixmap = pixmap
        self.set_window_size(width, height, redraw=True)
        
    def get_image_as_pixbuf(self):
        arr = self.get_rgb_array()
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_array(arr, gtk.gdk.COLORSPACE_RGB,
                                                   8)
        except Exception, e:
            # pygtk might have been compiled without numpy support
            daht, dawd, depth = arr.shape
            rgb_buf = self._get_rgbbuf(arr)
            pixbuf = gtk.gdk.pixbuf_new_from_data(rgb_buf, gtk.gdk.COLORSPACE_RGB,
                                                  False, 8, dawd, daht, dawd*3)
            
        return pixbuf

    def get_image_as_widget(self):
        pixbuf = self.get_image_as_pixbuf()
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def save_image_as_file(self, filepath, format='png', quality=90):
        pixbuf = self.get_image_as_pixbuf()
        options = {}
        if format == 'jpeg':
            options['quality'] = quality
        pixbuf.save(filepath, format, options)
    
    def update_image(self):
        if not self.pixmap:
            return
        if not self.gc:
            self.gc = self._get_gc(self.pixmap)
            
        win = self.imgwin.window
        if win != None and self.pixmap != None:
            #imgwin_wd, imgwin_ht = self.get_window_size()
            win.invalidate_rect(None, True)
            # Process expose events right away so window is responsive
            # to scrolling
            win.process_updates(True)


    def expose_event(self, widget, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen pixmap to that area.
        """
        x , y, width, height = event.area
        self.logger.debug("pixmap is %s" % self.pixmap)
        if self.pixmap != None:
            # redraw the screen from backing pixmap
            if not self.gc:
                self.gc = self._get_gc(widget)
            self.logger.debug("updating window from pixmap")
            widget.window.draw_drawable(self.gc, self.pixmap, x, y, x, y,
                                        width, height)
        return False
        

    def configure_event(self, widget, event):
        self.pixmap = None
        x, y, width, height = widget.get_allocation()
        self.logger.debug("allocation is %d,%d %dx%d" % (
            x, y, width, height))
        self.configure(width, height)
        return True

    def set_cursor(self, cursor):
        win = self.imgwin.window
        if win != None:
            win.set_cursor(cursor)
        
    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor
        
    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])
        
    def _get_rgbbuf(self, data):
        buf = data.tostring(order='C')
        return buf

    def _get_gc(self, drawable, color=None):
        if not color:
            color = self.img_bg
        gc = drawable.new_gc()
        #cmap = drawable.get_colormap()
        cmap = gtk.gdk.colormap_get_system()
        clr = cmap.alloc_color(color)
        gc.set_foreground(clr)
        #gc.set_rgb_fg_color(self.img_bg)
        self.logger.debug("returning gc=%s" % str(gc))
        return gc

    def _get_color(self, r, g, b):
        n = 65535.0
        clr = gtk.gdk.Color(int(r*n), int(g*n), int(b*n))
        return clr
        
    def set_bg(self, r, g, b, redraw=True):
        self.img_bg = self._get_color(r, g, b)
        if not self.pixmap:
            return
        self.gc = self.pixmap.new_gc()
        cmap = self.pixmap.get_colormap()
        clr = cmap.alloc_color(self.bg)
        self.gc.set_foreground(clr)

        if redraw:
            self.redraw(whence=3)
        
    def set_fg(self, r, g, b, redraw=True):
        self.img_fg = self._get_color(r, g, b)
        if redraw:
            self.redraw(whence=3)
        
    def onscreen_message(self, text, delay=None, redraw=True):
        if self.msgtask:
            try:
                gobject.source_remove(self.msgtask)
            except:
                pass
        self.message = text
        if redraw:
            self.redraw(whence=3)
        if delay:
            ms = int(delay * 1000.0)
            self.msgtask = gobject.timeout_add(ms, self.onscreen_message, None)


class FitsImageEvent(FitsImageGtk):

    def __init__(self, logger=None):
        #super(FitsImageEvent, self).__init__(logger=logger)
        FitsImageGtk.__init__(self, logger=logger)

        imgwin = self.imgwin
        imgwin.set_flags(gtk.CAN_FOCUS)
        imgwin.connect("map_event", self.map_event)
        imgwin.connect("focus_in_event", self.focus_event, True)
        imgwin.connect("focus_out_event", self.focus_event, False)
        imgwin.connect("enter_notify_event", self.enter_notify_event)
        imgwin.connect("leave_notify_event", self.leave_notify_event)
        imgwin.connect("motion_notify_event", self.motion_notify_event)
        imgwin.connect("button_press_event", self.button_press_event)
        imgwin.connect("button_release_event", self.button_release_event)
        imgwin.connect("key_press_event", self.key_press_event)
        imgwin.connect("key_release_event", self.key_release_event)
        imgwin.connect("scroll_event", self.scroll_event)
        mask = imgwin.get_events()
        imgwin.set_events(mask
                         | gtk.gdk.ENTER_NOTIFY_MASK
                         | gtk.gdk.LEAVE_NOTIFY_MASK
                         | gtk.gdk.FOCUS_CHANGE_MASK
                         | gtk.gdk.STRUCTURE_MASK
                         | gtk.gdk.BUTTON_PRESS_MASK
                         | gtk.gdk.BUTTON_RELEASE_MASK
                         | gtk.gdk.KEY_PRESS_MASK
                         | gtk.gdk.KEY_RELEASE_MASK
                         | gtk.gdk.POINTER_MOTION_MASK
                         | gtk.gdk.POINTER_MOTION_HINT_MASK
                         | gtk.gdk.SCROLL_MASK)

        # Set up widget as a drag and drop destination
        self.TARGET_TYPE_TEXT = 80
        toImage = [ ( "text/plain", 0, self.TARGET_TYPE_TEXT ) ]
        imgwin.connect("drag_data_received", self.drop_event)
        imgwin.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                             toImage, gtk.gdk.ACTION_COPY)
        
        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0
        # Does widget accept focus when mouse enters window
        self.follow_focus = True

        # User-defined keyboard mouse mask
        self.kbdmouse_mask = 0

        # @$%&^(_)*&^ gnome!!
        self._keytbl = {
            'shift_l': 'shift_l',
            'shift_r': 'shift_r',
            'control_l': 'control_l',
            'control_r': 'control_r',
            'asciitilde': '~',
            'grave': 'backquote',
            'exclam': '!',
            'at': '@',
            'numbersign': '#',
            'percent': '%%',
            'asciicircum': '^',
            'ampersand': '&',
            'asterisk': '*',
            'parenleft': '(',
            'parenright': ')',
            'underscore': '_',
            'minus': '-',
            'plus': '+',
            'equal': '=',
            'braceleft': '{',
            'braceright': '}',
            'bracketleft': '[',
            'bracketright': ']',
            'bar': '|',
            'colon': ':',
            'semicolon': ';',
            'quotedbl': 'doublequote',
            'apostrophe': 'singlequote',
            'backslash': 'backslash',
            'less': '<',
            'greater': '>',
            'comma': ',',
            'period': '.',
            'question': '?',
            'slash': '/',
            'space': 'space',
            'escape': 'escape',
            'return': 'return',
            'tab': 'tab',
            'f1': 'f1',
            'f2': 'f2',
            'f3': 'f3',
            'f4': 'f4',
            'f5': 'f5',
            'f6': 'f6',
            'f7': 'f7',
            'f8': 'f8',
            'f9': 'f9',
            'f10': 'f10',
            'f11': 'f11',
            'f12': 'f12',
            }
        
        # Define cursors for pick and pan
        self.define_cursor('pan', gtk.gdk.Cursor(gtk.gdk.FLEUR))
        co = thinCrossCursor('aquamarine')
        self.define_cursor('pick', co.cur)

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop', 
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     ):
            self.enable_callback(name)

    def transkey(self, keyname):
        try:
            return self._keytbl[keyname.lower()]

        except KeyError:
            return keyname

    def set_kbdmouse_mask(self, mask):
        self.kbdmouse_mask |= mask
        
    def reset_kbdmouse_mask(self, mask):
        self.kbdmouse_mask &= ~mask
        
    def get_kbdmouse_mask(self):
        return self.kbdmouse_mask
        
    def clear_kbdmouse_mask(self):
        self.kbdmouse_mask = 0
        
    def set_followfocus(self, tf):
        self.followfocus = tf
        
    def map_event(self, widget, event):
        super(FitsImageZoom, self).configure_event(widget, event)
        return self.make_callback('map')
            
    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)
            
    def enter_notify_event(self, widget, event):
        if self.follow_focus:
            widget.grab_focus()
        return self.make_callback('enter')
    
    def leave_notify_event(self, widget, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')
    
    def key_press_event(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))
            
        data_x, data_y = self.get_data_xy(x, y)
        return self.make_callback('button-release', button, data_x, data_y)

    def motion_notify_event(self, widget, event):
        button = self.kbdmouse_mask
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x, y, state = event.x, event.y, event.state
        self.last_win_x, self.last_win_y = x, y
        
        if state & gtk.gdk.BUTTON1_MASK:
            button |= 0x1
        elif state & gtk.gdk.BUTTON2_MASK:
            button |= 0x2
        elif state & gtk.gdk.BUTTON3_MASK:
            button |= 0x4
        # self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_callback('motion', button, data_x, data_y)

    def scroll_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        direction = None
        if event.direction == gtk.gdk.SCROLL_UP:
            direction = 'up'
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            direction = 'down'
        elif event.direction == gtk.gdk.SCROLL_LEFT:
            direction = 'left'
        elif event.direction == gtk.gdk.SCROLL_RIGHT:
            direction = 'right'
        self.logger.debug("scroll at %dx%d event=%s" % (x, y, str(event)))

        # TODO: how about amount of scroll?
        return self.make_callback('scroll', direction)

    def drop_event(self, widget, context, x, y, selection, targetType,
                   time):
        if targetType != self.TARGET_TYPE_TEXT:
            return False
        paths = selection.data.split('\n')
        self.logger.debug("dropped filename(s): %s" % (str(paths)))
        return self.make_callback('drag-drop', paths)


class FitsImageZoom(FitsImageEvent, Mixins.FitsImageZoomMixin):

    def __init__(self, logger=None):
        FitsImageEvent.__init__(self, logger=logger)
        Mixins.FitsImageZoomMixin.__init__(self)
        
        
class thinCrossCursor(object):
    def __init__(self, color='red'):
        pm = gtk.gdk.Pixmap(None,16,16,1)
        mask = gtk.gdk.Pixmap(None,16,16,1)
        colormap = gtk.gdk.colormap_get_system()
        black = colormap.alloc_color('black')
        white = colormap.alloc_color('white')
        
        bgc = pm.new_gc(foreground=black)
        wgc = pm.new_gc(foreground=white)
        
        mask.draw_rectangle(bgc,True,0,0,16,16)
        pm.draw_rectangle(wgc,True,0,0,16,16)
        
        mask.draw_line(wgc,0,6,5,6)
        mask.draw_line(wgc,0,8,5,8)
        
        mask.draw_line(wgc,10,6,15,6)
        mask.draw_line(wgc,10,8,15,8)
        
        mask.draw_line(wgc,6,0,6,5)
        mask.draw_line(wgc,8,0,8,5)
        
        mask.draw_line(wgc,6,10,6,15)
        mask.draw_line(wgc,8,10,8,15)
        
        #mask.draw_line(wgc,0,5,0,9)
        #mask.draw_line(wgc,15,5,15,9)
        #mask.draw_line(wgc,5,0,9,0)
        #mask.draw_line(wgc,5,15,9,15)
        #mask.draw_arc(wgc,False,3,3,8,8,0,64*360)
        self.color = color
        self.cur = gtk.gdk.Cursor(pm,mask,
                                  gtk.gdk.color_parse(self.color),
                                  gtk.gdk.Color(),8,8)
        
#END
