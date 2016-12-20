#
# ImageViewGtk.py -- a backend for Ginga using Gtk widgets and Cairo
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

import sys, os

import numpy

import gtk
import cairo

from ginga.gtkw import GtkHelp
from ginga.cairow import ImageViewCairo
from ginga import Mixins, Bindings, colors
from ginga.util.paths import icondir


class ImageViewGtkError(ImageViewCairo.ImageViewCairoError):
    pass

class ImageViewGtk(ImageViewCairo.ImageViewCairo):

    def __init__(self, logger=None, rgbmap=None, settings=None):
        ImageViewCairo.ImageViewCairo.__init__(self, logger=logger,
                                               rgbmap=rgbmap,
                                               settings=settings)

        imgwin = gtk.DrawingArea()
        imgwin.connect("expose_event", self.expose_event)
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

        # see reschedule_redraw() method
        self._defer_task = GtkHelp.Timer(0.0,
                                         lambda timer: self.delayed_redraw())
        self.msgtask = GtkHelp.Timer(0.0,
                                     lambda timer: self.onscreen_message(None))


    def get_widget(self):
        return self.imgwin

    def get_plain_image_as_pixbuf(self):
        #arr = self.getwin_array(order=self._rgb_order)
        arr = self.getwin_array(order='RGB')

        try:
            pixbuf = GtkHelp.pixbuf_new_from_array(arr, gtk.gdk.COLORSPACE_RGB,
                                                  8)
        except Exception as e:
            self.logger.warning("Error making pixbuf: %s" % (str(e)))
            # pygtk might have been compiled without numpy support
            daht, dawd, depth = arr.shape
            rgb_buf = self._get_rgbbuf(arr)
            pixbuf = GtkHelp.pixbuf_new_from_data(rgb_buf,
                                                  gtk.gdk.COLORSPACE_RGB,
                                                  False, 8, dawd, daht, dawd*3)

        return pixbuf

    def get_plain_image_as_widget(self):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        pixbuf = self.get_plain_image_as_pixbuf()
        image = gtk.Image()
        image.set_from_pixbuf(pixbuf)
        image.show()
        return image

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Used for generating thumbnails.  Does not include overlaid
        graphics.
        """
        pixbuf = self.get_plain_image_as_pixbuf()
        options = {}
        if format == 'jpeg':
            options['quality'] = str(quality)
        pixbuf.save(filepath, format, options)

    def get_rgb_image_as_pixbuf(self):
        dawd = self.surface.get_width()
        daht = self.surface.get_height()
        rgb_buf = bytes(self.surface.get_data())
        pixbuf = GtkHelp.pixbuf_new_from_data(rgb_buf, gtk.gdk.COLORSPACE_RGB,
                                              False, 8, dawd, daht, dawd*3)

        return pixbuf

    def save_rgb_image_as_file(self, filepath, format='png', quality=90):
        pixbuf = self.get_rgb_image_as_pixbuf()
        options = {}
        if format == 'jpeg':
            options['quality'] = str(quality)
        pixbuf.save(filepath, format, options)

    def reschedule_redraw(self, time_sec):
        self._defer_task.cancel()
        self._defer_task.start(time_sec)

    def update_image(self):
        if not self.surface:
            return

        win = self.imgwin.get_window()
        if win is not None and self.surface is not None:
            imgwin_wd, imgwin_ht = self.get_window_size()

            win.invalidate_rect(None, True)
            # Process expose events right away so window is responsive
            # to scrolling
            win.process_updates(True)


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

    def make_cursor(self, iconpath, x, y):
        cursor = GtkHelp.make_cursor(self.imgwin, iconpath, x, y)
        return cursor

    def center_cursor(self):
        if self.imgwin is None:
            return
        win_x, win_y = self.get_center()
        scrn_x, scrn_y = self.imgwin.window.get_origin()
        scrn_x, scrn_y = scrn_x + win_x, scrn_y + win_y

        # set the cursor position
        disp = self.imgwin.window.get_display()
        screen = self.imgwin.window.get_screen()
        disp.warp_pointer(screen, scrn_x, scrn_y)

    def position_cursor(self, data_x, data_y):
        if self.imgwin is None:
            return
        win_x, win_y = self.get_canvas_xy(data_x, data_y)
        scrn_x, scrn_y = self.imgwin.window.get_origin()
        scrn_x, scrn_y = scrn_x + win_x, scrn_y + win_y

        # set the cursor position
        disp = self.imgwin.window.get_display()
        screen = self.imgwin.window.get_screen()
        disp.warp_pointer(screen, scrn_x, scrn_y)

    def _get_rgbbuf(self, data):
        buf = data.tostring(order='C')
        return buf

    def onscreen_message(self, text, delay=None, redraw=True):
        self.msgtask.cancel()
        self.set_onscreen_message(text, redraw=redraw)
        if delay is not None:
            self.msgtask.start(delay)


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
        self.TARGET_TYPE_TEXT = 0
        self.TARGET_TYPE_THUMB = 1
        toImage = [ ( "text/plain", 0, self.TARGET_TYPE_TEXT ),
                    #( "text/uri-list", 0, self.TARGET_TYPE_TEXT ),
                    ( "text/thumb", gtk.TARGET_SAME_APP,
                      self.TARGET_TYPE_THUMB ),
                    ]
        imgwin.drag_dest_set(gtk.DEST_DEFAULT_ALL, toImage,
                             gtk.gdk.ACTION_COPY)

        # Does widget accept focus when mouse enters window
        self.enter_focus = self.t_.get('enter_focus', True)

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
            'right': 'right',
            'left': 'left',
            'up': 'up',
            'down': 'down',
            }

        # Define cursors
        for curname, filename in (('pan', 'openHandCursor.png'),
                                  ('pick', 'thinCrossCursor.png')):
            path = os.path.join(icondir, filename)
            cur = self.make_cursor(path, 8, 8)
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

    def set_enter_focus(self, tf):
        self.enter_focus = tf

    def map_event(self, widget, event):
        super(ImageViewZoom, self).configure_event(widget, event)
        return self.make_callback('map')

    def focus_event(self, widget, event, hasFocus):
        return self.make_callback('focus', hasFocus)

    def enter_notify_event(self, widget, event):
        if self.enter_focus:
            widget.grab_focus()
        return self.make_callback('enter')

    def leave_notify_event(self, widget, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, widget, event):
        # without this we do not get key release events if the focus
        # changes to another window
        #gtk.gdk.keyboard_grab(widget.get_window(), False)

        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key press event, key=%s" % (keyname))
        return self.make_ui_callback('key-press', keyname)

    def key_release_event(self, widget, event):
        #gtk.gdk.keyboard_ungrab()

        keyname = gtk.gdk.keyval_name(event.keyval)
        keyname = self.transkey(keyname)
        self.logger.debug("key release event, key=%s" % (keyname))
        return self.make_ui_callback('key-release', keyname)

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('button-press', button, data_x, data_y)

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        self.last_win_x, self.last_win_y = x, y

        button = 0
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.get_data_xy(x, y)
        self.last_data_x, self.last_data_y = data_x, data_y

        return self.make_ui_callback('button-release', button, data_x, data_y)

    def motion_notify_event(self, widget, event):
        button = 0
        if event.is_hint:
            tup = event.window.get_pointer()
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
        self.last_win_x, self.last_win_y = x, y

        degrees, direction = GtkHelp.get_scroll_info(event)
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


class ScrolledView1(gtk.ScrolledWindow):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, viewer, parent=None):
        self.viewer = viewer
        super(ScrolledView, self).__init__()

        # the window jiggles annoyingly as the scrollbar is alternately
        # shown and hidden if we use the default "automatic" policy, so
        # default to always showing them (user can change this after
        # calling the constructor, if desired)
        self.scroll_bars(horizontal='on', vertical='on')

        self.set_border_width(0)

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.upper_h = 100.0
        self.upper_v = 100.0

        # reparent the viewer widget
        self.v_w = viewer.get_widget()
        self.add(self.v_w)

        hsb = self.get_hadjustment()
        hsb.connect('value-changed', self._scroll_contents)
        vsb = self.get_vadjustment()
        vsb.connect('value-changed', self._scroll_contents)

        self.viewer.add_callback('redraw', self._calc_scrollbars)
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v))

    def get_widget(self):
        return self

    def _calc_scrollbars(self, viewer):
        """Calculate and set the scrollbar handles from the pan and
        zoom positions.
        """
        if self._scrolling:
            return

        # flag that suppresses a cyclical callback
        self._adjusting = True
        try:
            bd = self.viewer.get_bindings()
            res = bd.calc_pan_pct(self.viewer, pad=self.pad)
            if res is None:
                return

            hsb = self.get_hadjustment()
            vsb = self.get_vadjustment()

            page_h, page_v = (int(round(res.thm_pct_x * 100)),
                              int(round(res.thm_pct_y * 100)))

            self.upper_h, self.upper_v = 100 + page_h, 100 + page_v

            ## val_h, val_v = (int(round(res.pan_pct_x * 100)),
            ##                 int(round((1.0 - res.pan_pct_y) * 100)))
            val_h, val_v = (int(round(res.pan_pct_x * 100.0)),
                            int(round((1.0 - res.pan_pct_y) * 100.0)))

            hsb.configure(val_h, 0, self.upper_h, 1, page_h, page_h)
            vsb.configure(val_v, 0, self.upper_v, 1, page_v, page_v)

        finally:
            self._adjusting = False

    def _scroll_contents(self, adj):
        """Called when the scroll bars are adjusted by the user.
        """
        if self._adjusting:
            return

        self._scrolling = True
        try:
            hsb = self.get_hadjustment()
            vsb = self.get_vadjustment()

            pos_x = hsb.get_value()
            pos_y = vsb.get_value()

            pct_x = pos_x / 100.0
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - (pos_y / 100.0)

            bd = self.viewer.get_bindings()
            bd.pan_by_pct(self.viewer, pct_x, pct_y, pad=self.pad)

        finally:
            self._scrolling = False

    def scroll_bars(self, horizontal='on', vertical='on'):
        if horizontal == 'on':
            hpolicy = gtk.POLICY_ALWAYS
        elif horizontal == 'off':
            hpolicy = gtk.POLICY_NEVER
        elif horizontal == 'auto':
            hpolicy = gtk.POLICY_AUTOMATIC
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (horizontal))

        if vertical == 'on':
            vpolicy = gtk.POLICY_ALWAYS
        elif vertical == 'off':
            vpolicy = gtk.POLICY_NEVER
        elif vertical == 'auto':
            vpolicy = gtk.POLICY_AUTOMATIC
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (vertical))

        self.set_policy(hpolicy, vpolicy)


class ScrolledView(gtk.Table):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, viewer, parent=None):
        self.viewer = viewer
        super(ScrolledView, self).__init__(rows=2, columns=2)

        self.set_border_width(0)
        self.set_row_spacings(0)
        self.set_col_spacings(0)

        self._adjusting = False
        self._scrolling = False
        self.pad = 20
        self.rng_x = 100.0
        self.rng_y = 100.0

        xoptions = gtk.EXPAND | gtk.FILL
        yoptions = gtk.EXPAND | gtk.FILL

        # reparent the viewer widget
        self.v_w = viewer.get_widget()
        self.attach(self.v_w, 0, 1, 0, 1,
                    xoptions=xoptions, yoptions=yoptions,
                    xpadding=0, ypadding=0)

        self.hsb = gtk.HScrollbar()
        self.hsb.set_round_digits(4)
        self.hsb.connect('value-changed', self._scroll_contents)
        self.attach(self.hsb, 0, 1, 1, 2,
                    xoptions=gtk.FILL, yoptions=0, xpadding=0, ypadding=0)
        self.vsb = gtk.VScrollbar()
        self.vsb.set_round_digits(4)
        self.vsb.connect('value-changed', self._scroll_contents)
        self.attach(self.vsb, 1, 2, 0, 1,
                    xoptions=0, yoptions=gtk.FILL, xpadding=0, ypadding=0)

        self.viewer.add_callback('redraw', self._calc_scrollbars)
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v))

        self._calc_scrollbars(self.viewer)

    def get_widget(self):
        return self

    def _calc_scrollbars(self, viewer):
        """Calculate and set the scrollbar handles from the pan and
        zoom positions.
        """
        if self._scrolling:
            return

        # flag that suppresses a cyclical callback
        self._adjusting = True
        try:
            bd = self.viewer.get_bindings()
            res = bd.calc_pan_pct(self.viewer, pad=self.pad)
            if res is None:
                return

            page_x, page_y = (float(res.thm_pct_x * 100),
                              float(res.thm_pct_y * 100))
            self.rng_x, self.rng_y = 100 - page_x, 100 - page_y
            val_x, val_y = (float(res.pan_pct_x * self.rng_x),
                            float((1.0 - res.pan_pct_y) * self.rng_y))

            upper_x, upper_y = 100.0, 100.0

            adj = self.hsb.get_adjustment()
            adj.configure(val_x, 0.0, upper_x, 1.0, page_x, page_x)
            self.hsb.set_adjustment(adj)
            adj = self.vsb.get_adjustment()
            adj.configure(val_y, 0.0, upper_y, 1.0, page_y, page_y)
            self.vsb.set_adjustment(adj)

        finally:
            self._adjusting = False
        return True

    def _scroll_contents(self, adj):
        """Called when the scroll bars are adjusted by the user.
        """
        if self._adjusting:
            return True

        try:
            pos_x = self.hsb.get_value()
            pos_y = self.vsb.get_value()

            pct_x = pos_x / self.rng_x
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - (pos_y / self.rng_y)

            bd = self.viewer.get_bindings()
            bd.pan_by_pct(self.viewer, pct_x, pct_y, pad=self.pad)

        finally:
            self._scrolling = False

        return True

    def scroll_bars(self, horizontal='on', vertical='on'):
        if horizontal == 'on':
            pass
        elif horizontal == 'off':
            pass
        elif horizontal == 'auto':
            pass
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (horizontal))

        if vertical == 'on':
            pass
        elif vertical == 'off':
            pass
        elif vertical == 'auto':
            pass
        else:
            raise ValueError("Bad scroll bar option: '%s'; should be one of ('on', 'off' or 'auto')" % (vertical))

        self.viewer.logger.warning("scroll_bar(): settings for gtk currently ignored!")

#END
