#
# ImageViewGtk.py -- classes for the display of FITS files in Gtk widgets
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys, os

from ginga.gtkw import gtksel
from ginga.gtkw.GtkHelp import get_scroll_info
import gtk
import gobject
import cairo
import numpy

from ginga.cairow import ImageViewCairo
from ginga import Mixins, Bindings, colors

moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
icon_dir = os.path.abspath(os.path.join(moduleHome, '..', 'icons'))


class ImageViewGtkError(ImageViewCairo.ImageViewCairoError):
    pass

class ImageViewGtk(ImageViewCairo.ImageViewCairo):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewCairo.ImageViewCairo.__init__(self, logger=logger,
                                               rgbmap=rgbmap,
                                               settings=settings)

        imgwin = gtk.DrawingArea()
        if not gtksel.have_gtk3:
            imgwin.connect("expose_event", self.expose_event)
        else:
            imgwin.connect("draw", self.draw_event)
        imgwin.connect("configure-event", self.configure_event)
        imgwin.connect("size-request", self.size_request)
        imgwin.set_events(gtk.gdk.EXPOSURE_MASK)
        # prevents some flickering
        imgwin.set_double_buffered(True)
        imgwin.set_app_paintable(True)
        # prevents extra redraws, because we manually redraw on a size
        # change
        imgwin.set_redraw_on_allocate(False)
        self.imgwin = imgwin
        self.imgwin.show_all()

        # cursors
        self.cursor = {}

        # see reschedule_redraw() method
        self._defer_task = None
        self.msgtask = None


    def get_widget(self):
        return self.imgwin

    def get_image_as_pixbuf(self):
        #arr = self.getwin_array(order=self._rgb_order)
        arr = self.getwin_array(order='RGB')

        try:
            pixbuf = gtksel.pixbuf_new_from_array(arr, gtk.gdk.COLORSPACE_RGB,
                                                  8)
        except Exception as e:
            self.logger.warn("Error making pixbuf: %s" % (str(e)))
            # pygtk might have been compiled without numpy support
            daht, dawd, depth = arr.shape
            rgb_buf = self._get_rgbbuf(arr)
            pixbuf = gtksel.pixbuf_new_from_data(rgb_buf,
                                                 gtk.gdk.COLORSPACE_RGB,
                                                 False, 8, dawd, daht, dawd*3)

        return pixbuf

    def get_image_as_widget(self):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        pixbuf = self.get_image_as_pixbuf()
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def save_image_as_file(self, filepath, format='png', quality=90):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        pixbuf = self.get_image_as_pixbuf()
        options = {}
        if format == 'jpeg':
            options['quality'] = str(quality)
        pixbuf.save(filepath, format, options)

    def get_rgb_image_as_pixbuf(self):
        dawd = self.surface.get_width()
        daht = self.surface.get_height()
        rgb_buf = bytes(self.surface.get_data())
        pixbuf = gtksel.pixbuf_new_from_data(rgb_buf, gtk.gdk.COLORSPACE_RGB,
                                             False, 8, dawd, daht, dawd*3)

        return pixbuf

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        pixbuf = self.get_rgb_image_as_pixbuf()
        options = {}
        if format == 'jpeg':
            options['quality'] = str(quality)
        pixbuf.save(filepath, format, options)

    def reschedule_redraw(self, time_sec):
        time_ms = int(time_sec * 1000)
        try:
            if self._defer_task:
                gobject.source_remove(self._defer_task)
        except:
            pass
        self._defer_task = gobject.timeout_add(time_ms,
                                               self.delayed_redraw_gtk)

    def delayed_redraw_gtk(self):
        self._defer_task = None
        self.delayed_redraw()

    def update_image(self):
        if not self.surface:
            return

        win = self.imgwin.get_window()
        if win is not None and self.surface is not None:
            imgwin_wd, imgwin_ht = self.get_window_size()

            if gtksel.have_gtk3:
                self.imgwin.queue_draw_area(0, 0, imgwin_wd, imgwin_ht)
            else:
                win.invalidate_rect(None, True)
            # Process expose events right away so window is responsive
            # to scrolling
            win.process_updates(True)


    def draw_event(self, widget, cr):
        """GTK 3 event handler replacing expose_event().
        """
        self.logger.debug("updating window from surface")
        # redraw the screen from backing surface
        cr.set_source_surface(self.surface, 0, 0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def expose_event(self, widget, event):
        """When an area of the window is exposed, we just copy out of the
        server-side, off-screen surface to that area.
        """
        x , y, width, height = event.area
        self.logger.debug("surface is %s" % self.surface)
        if self.surface is not None:
            win = widget.get_window()
            cr = win.cairo_create()

            # set clip area for exposed region
            cr.rectangle(x, y, width, height)
            cr.clip()

            # Paint from off-screen surface
            cr.set_source_surface(self.surface, 0, 0)
            cr.set_operator(cairo.OPERATOR_SOURCE)
            cr.paint()

        return False

    def configure_window(self, width, height):
        self.configure_surface(width, height)

    def configure_event(self, widget, event):
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height

        if self.surface is not None:
            # This is a workaround for a strange bug in Gtk 3
            # where we get multiple configure callbacks even though
            # the size hasn't changed.  We avoid creating a new surface
            # if there is an old surface with the exact same size.
            # This prevents some flickering of the display on focus events.
            wwd, wht = self.get_window_size()
            if (wwd == width) and (wht == height):
                return True

        #self.surface = None
        self.logger.debug("allocation is %d,%d %dx%d" % (
            x, y, width, height))
        #width, height = width*2, height*2
        self.configure_window(width, height)
        return True

    def size_request(self, widget, requisition):
        """Callback function to request our desired size.
        """
        requisition.width, requisition.height = self.get_desired_size()
        return True

    def set_cursor(self, cursor):
        win = self.imgwin.get_window()
        if win is not None:
            win.set_cursor(cursor)

    def define_cursor(self, ctype, cursor):
        self.cursor[ctype] = cursor

    def get_cursor(self, ctype):
        return self.cursor[ctype]

    def switch_cursor(self, ctype):
        self.set_cursor(self.cursor[ctype])

    def _get_rgbbuf(self, data):
        buf = data.tostring(order='C')
        return buf

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
            self.msgtask = gobject.timeout_add(ms,
                                               self.clear_onscreen_message_gtk)

    def clear_onscreen_message_gtk(self):
        self.msgtask = None
        self.onscreen_message(None)

class ImageViewEvent(ImageViewGtk):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewGtk.__init__(self, logger=logger, rgbmap=rgbmap,
                              settings=settings)

        imgwin = self.imgwin
        imgwin.set_can_focus(True)
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
        imgwin.connect("drag-data-received", self.drop_event)
        imgwin.connect("drag-motion", self.drag_motion_cb)
        imgwin.connect("drag-drop", self.drag_drop_cb)
        if gtksel.have_gtk3:
            self.TARGET_TYPE_TEXT = 0
            imgwin.drag_dest_set(gtk.DestDefaults.ALL, [],
                                 gtk.gdk.DragAction.COPY)
            imgwin.drag_dest_add_text_targets()
        else:
            self.TARGET_TYPE_TEXT = 0
            self.TARGET_TYPE_THUMB = 1
            toImage = [ ( "text/plain", 0, self.TARGET_TYPE_TEXT ),
                        #( "text/uri-list", 0, self.TARGET_TYPE_TEXT ),
                        ( "text/thumb", gtk.TARGET_SAME_APP,
                          self.TARGET_TYPE_THUMB ),
                        ]
            imgwin.drag_dest_set(gtk.DEST_DEFAULT_ALL, toImage,
                                 gtk.gdk.ACTION_COPY)
            ## imgwin.drag_dest_set(0, toImage,  gtk.gdk.ACTION_COPY)
            ## imgwin.drag_dest_set(0, [],  0)

        # last known window mouse position
        self.last_win_x = 0
        self.last_win_y = 0
        # last known data mouse position
        self.last_data_x = 0
        self.last_data_y = 0
        # Does widget accept focus when mouse enters window
        self.follow_focus = True

        # @$%&^(_)*&^ gnome!!
        self._keytbl = {
            'shift_l': 'shift_l',
            'shift_r': 'shift_r',
            'control_l': 'control_l',
            'control_r': 'control_r',
            'alt_l': 'alt_l',
            'alt_r': 'alt_r',
            'super_l': 'super_l',
            'super_r': 'super_r',
            'meta_right': 'meta_right',
            'asciitilde': '~',
            'grave': 'backquote',
            'exclam': '!',
            'at': '@',
            'numbersign': '#',
            'percent': '%',
            'asciicircum': '^',
            'ampersand': '&',
            'asterisk': '*',
            'dollar': '$',
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

        # Define cursors
        for curname, filename in (('pan', 'openHandCursor.png'),
                               ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icon_dir, filename)
            cur = gtksel.make_cursor(self.imgwin, path, 8, 8)
            self.define_cursor(curname, cur)

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

    def get_keyTable(self):
        return self._keytbl

    def set_follow_focus(self, tf):
        self.follow_focus = tf

    def map_event(self, widget, event):
        super(ImageViewZoom, self).configure_event(widget, event)
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
        # without this we do not get key release events if the focus
        # changes to another window
        gtk.gdk.keyboard_grab(widget.get_window(), False)

        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        gtk.gdk.keyboard_ungrab()

        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        return self.make_ui_callback('button-release', button, data_x, data_y)

    def get_last_win_xy(self):
        return (self.last_win_x, self.last_win_y)

    def get_last_data_xy(self):
        return (self.last_data_x, self.last_data_y)

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

        return self.make_ui_callback('motion', button, data_x, data_y)

    def scroll_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y

        degrees, direction = get_scroll_info(event)
        self.logger.debug("scroll deg=%f direction=%f" % (
            degrees, direction))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('scroll', direction, degrees,
                                  data_x, data_y)

    def drag_drop_cb(self, widget, context, x, y, time):
        self.logger.debug('drag_drop_cb')
        # initiates a drop
        success = delete = False
        for mimetype in context.targets:
            if mimetype in ("text/thumb", "text/plain", "text/uri-list"):
                context.drop_reply(True, time)
                success = True
                return True

        self.logger.debug("dropped format type did not match known types")
        context.drop_reply(False, time)

        # api: context.finish(success, delete_data, time)
        #context.finish(success, delete, time)
        return True

    def drag_motion_cb(self, widget, context, x, y, time):
        self.logger.debug('drag_motion_cb')
        status = gtk.gdk.ACTION_COPY
        # checks whether a drop is possible
        for mimetype in context.targets:
            if mimetype in ("text/thumb", "text/plain", "text/uri-list"):
                context.drag_status(status, time)
                return True

        context.drag_status(0, time)
        self.logger.debug('drag_motion_cb done')
        return True

    def drop_event(self, widget, context, x, y, selection, targetType,
                   time):
        self.logger.debug('drop_event')
        if targetType != self.TARGET_TYPE_TEXT:
            return False
        paths = selection.get_text().strip().split('\n')
        self.logger.debug("dropped filename(s): %s" % (str(paths)))
        return self.make_ui_callback('drag-drop', paths)


class ImageViewZoom(Mixins.UIMixin, ImageViewEvent):

    # class variables for binding map and bindings can be set
    bindmapClass = Bindings.BindingMapper
    bindingsClass = Bindings.ImageViewBindings

    @classmethod
    def set_bindingsClass(cls, klass):
        cls.bindingsClass = klass

    @classmethod
    def set_bindmapClass(cls, klass):
        cls.bindmapClass = klass

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings)
        Mixins.UIMixin.__init__(self)

        self.ui_setActive(True)

        if bindmap is None:
            bindmap = ImageViewZoom.bindmapClass(self.logger)
        self.bindmap = bindmap
        bindmap.register_for_events(self)

        if bindings is None:
            bindings = ImageViewZoom.bindingsClass(self.logger)
        self.set_bindings(bindings)

    def get_bindmap(self):
        return self.bindmap

    def get_bindings(self):
        return self.bindings

    def set_bindings(self, bindings):
        self.bindings = bindings
        bindings.set_bindings(self)


class CanvasView(ImageViewZoom):

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


#END
