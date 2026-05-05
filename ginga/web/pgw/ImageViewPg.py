#
# ImageViewPg.py -- a backend for Ginga using javascript and
#      HTML5 canvas and optionally via websockets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import threading

from ginga import ImageView, Mixins, Bindings, events
from ginga.misc.Bunch import Bunch
from ginga.canvas import render
from ginga.cursors import cursor_info
from ginga.web.pgw import PgHelp

in_situ_web = False
try:
    from pgwidgets_js.pyodide import Widgets
    # <-- we are being imported from pyodide/pyscript
    in_situ_web = True
except ImportError:
    # <-- we are being imported from python
    from pgwidgets.sync import Widgets

default_html_fmt = 'jpeg'


class ImageViewPgError(ImageView.ImageViewError):
    pass


class ImageViewPg(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)
        self.needs_scrolledview = True
        self.pgcanvas = None

        # format for rendering image on HTML5 canvas
        # NOTE: 'jpeg' has much better performance than 'png', but can show
        # some artifacts, especially noticeable with small text
        self.t_.set_defaults(html5_canvas_format=default_html_fmt,
                             renderer='cairo')

        self.rgb_order = 'RGBA'
        # this should already be so, but just in case...
        self.defer_redraw = True

        self._timer_resize_lock = threading.RLock()
        self._delayed_size = (0, 0)
        # these will be assigned in set_widget()
        self.timer_resize = None
        self.timer_redraw = None
        self.timer_msg = None

        self.renderer = None
        # Pick a renderer that can work with us
        renderers = ['cairo', 'pil', 'opencv', 'agg']
        preferred = self.t_['renderer']
        if preferred in renderers:
            renderers.remove(preferred)
        self.possible_renderers = [preferred] + renderers
        self.choose_best_renderer()

    def set_widget(self, canvas_w):
        """Call this method with the widget that will be used
        for the display.
        """
        self.logger.debug("set widget canvas_w=%s" % canvas_w)
        self.pgcanvas = canvas_w
        canvas_w.add_callback('map', self.canvas_map_cb)
        canvas_w.add_callback('resize', self.canvas_resize_cb)

        if in_situ_web:
            self.timer_resize = Widgets.Timer()
            self.timer_redraw = Widgets.Timer()
            self.timer_msg = Widgets.Timer()
        else:
            self.timer_resize = Widgets.Timer(canvas_w.session)
            self.timer_redraw = Widgets.Timer(canvas_w.session)
            self.timer_msg = Widgets.Timer(canvas_w.session)

        self.timer_resize.add_callback('expired',
                                       lambda *args: self.delayed_resize_cb())
        self.timer_redraw.add_callback('expired',
                                       lambda *args: self.delayed_redraw())
        self.timer_msg.add_callback('expired',
                                    lambda *args: self.clear_onscreen_message())
        wd, ht = canvas_w.get_size()
        self.configure_window(wd, ht)

    def get_widget(self):
        return self.pgcanvas

    def choose_renderer(self, name):
        klass = render.get_render_class(name)
        self.renderer = klass(self)

        if self.pgcanvas is not None:
            wd, ht = self.pgcanvas_w.get_size()
            self.configure_window(wd, ht)

    def choose_best_renderer(self):
        for name in self.possible_renderers:
            try:
                self.choose_renderer(name)
                self.logger.info("best renderer available is '{}'".format(name))
                return
            except Exception as e:
                # uncomment to troubleshoot
                ## self.logger.error("Error choosing renderer '{}': {}".format(name, e),
                ##                   exc_info=True)
                continue

        raise ImageViewPgError("No valid renderers available: {}".format(str(self.possible_renderers)))

    def update_widget(self):
        self.logger.debug("update_widget pgcanvas=%s" % self.pgcanvas)
        if self.pgcanvas is None:
            return

        try:
            self.logger.debug("getting image as buffer...")
            format = self.t_.get('html5_canvas_format', default_html_fmt)

            buf = self.renderer.get_surface_as_rgb_format_bytes(
                format=format, quality=90)
            self.logger.debug("got '%s' RGB image buffer, len=%d" % (
                format, len(buf)))

            # Now using an image by default
            #self.pgcanvas.set_binary_image(buf, format)
            data_uri = PgHelp.get_image_src_from_buffer(buf, imgtype=format)
            self.pgcanvas.set_image(data_uri)

        except Exception as e:
            self.logger.error("Couldn't update canvas: %s" % (str(e)))

    def reschedule_redraw(self, time_sec):
        if self.pgcanvas is not None:
            self.timer_redraw.stop()
            self.timer_redraw.start(time_sec)
        else:
            self.delayed_redraw()

    def get_plain_image_as_widget(self):
        """Does not include overlaid graphics."""
        image_buf = self.renderer.get_surface_as_rgb_format_buffer()
        return image_buf.getvalue()

    def save_plain_image_as_file(self, filepath, format='png', quality=90):
        """Does not include overlaid graphics."""
        pass

    def set_cursor(self, name):
        if self.pgcanvas is None:
            return
        #self.pgcanvas.config(cursor=cursor)
        self.pgcanvas.set_cursor(name)

    def onscreen_message(self, text, delay=None, redraw=True):
        if self.pgcanvas is None:
            return
        self.timer_msg.stop()
        self.set_onscreen_message(text, redraw=redraw)
        if delay is not None:
            self.timer_msg.start(delay)

    def clear_onscreen_message(self):
        self.logger.debug("clearing message...")
        self.onscreen_message(None)

    def configure_window(self, width, height):
        self.configure(width, height)

    def canvas_map_cb(self, canvas_w, event):
        wd, ht = event['width'], event['height']
        self.logger.debug(f"window mapped to {wd}x{ht}")
        self.configure_window(wd, ht)
        self.redraw(whence=0)

    def canvas_resize_cb(self, canvas_w, event):
        with self._timer_resize_lock:
            self._delayed_size = (event['width'], event['height'])
            self.timer_resize.cond_set(0.25)

    def delayed_resize_cb(self):
        with self._timer_resize_lock:
            wd, ht = self._delayed_size
            self.logger.info("canvas resized to %dx%d" % (wd, ht))
            self.configure_window(wd, ht)
            self.redraw(whence=0)

    def resize(self, width, height):
        """Resize our window to width x height.
        May not work---depending on how the HTML5 canvas is embedded.
        """
        # this shouldn't be needed
        #self.configure_window(width, height)
        self.pgcanvas.resize(width, height)


class PgEventMixin:

    def __init__(self):
        self._button = 0

        # @$%&^(_)*&^ javascript!!
        # table mapping javascript key codes to ginga key names
        # see key_down_event() and key_up_event()
        #
        # this table is used to map special characters to character names
        # see key_down_event()
        self._keytbl = {
            '"': 'doublequote',
            "'": 'singlequote',
        }

        self._keytbl2 = {
            'Backslash': 'backslash',
            "Backquote": 'backquote',
            "Backspace": 'backspace',
            "ShiftLeft": 'shift_l',
            "ShiftRight": 'shift_r',
            "ControlLeft": 'control_l',
            "ControlRight": 'control_r',
            "AltLeft": 'alt_l',
            "AltRight": 'alt_r',
            "CapsLock": 'caps_lock',
            "ArrowUp": 'up',
            "ArrowDown": 'down',
            "ArrowLeft": 'left',
            "ArrowRight": 'right',
            "Tab": 'tab',
            "Space": 'space',
            "Escape": 'escape',
            "Enter": 'enter',
            "Insert": 'insert',
            "Delete": 'delete',
            "PageUp": 'page_up',
            "PageDown": 'page_down',
            "Home": 'home',
            "End": 'end',
            "Pause": 'break',
            "ScrollLock": 'scroll_lock',
            "Numpad0": 'numpad_0',
            "Numpad1": 'numpad_1',
            "Numpad2": 'numpad_2',
            "Numpad3": 'numpad_3',
            "Numpad4": 'numpad_4',
            "Numpad5": 'numpad_5',
            "Numpad6": 'numpad_6',
            "Numpad7": 'numpad_7',
            "Numpad8": 'numpad_8',
            "Numpad9": 'numpad_9',
            "NumpadDecimal": 'numpad_.',
            "NumpadAdd": 'numpad_+',
            "NumpadSubtract": 'numpad_-',
            "NumpadDivide": 'numpad_/',
            "NumpadMultiply": 'numpad_*',
        }

        # define cursor names to web names now--they will be reset
        # in set_widget()
        cursor_names = cursor_info.get_cursor_names()
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            self.define_cursor(curinfo.name, curinfo.web)

        for name in ['motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'rotate', 'pan', 'swipe', 'tap']:
            self.enable_callback(name)

    def set_widget(self, canvas_w):
        super().set_widget(canvas_w)

        # event binding setup
        canvas_w.add_callback('pointer-down',
                              lambda w, e: self.button_press_event(Bunch(e)))
        canvas_w.add_callback('pointer-move',
                              lambda w, e: self.motion_notify_event(Bunch(e)))
        canvas_w.add_callback('pointer-up',
                              lambda w, e: self.button_release_event(Bunch(e)))
        canvas_w.add_callback('scroll',
                              lambda w, e: self.scroll_event(Bunch(e)))
        canvas_w.add_callback('focus-in',
                              lambda w, e: self.focus_event(Bunch(e), True))
        canvas_w.add_callback('focus-out',
                              lambda w, e: self.focus_event(Bunch(e), False))
        canvas_w.add_callback('key-down',
                              lambda w, e: self.key_down_event(Bunch(e)))
        canvas_w.add_callback('key-up',
                              lambda w, e: self.key_up_event(Bunch(e)))
        canvas_w.add_callback('enter',
                              lambda w, e: self.enter_notify_event(Bunch(e)))
        canvas_w.add_callback('leave',
                              lambda w, e: self.leave_notify_event(Bunch(e)))
        canvas_w.add_callback('drop-progress',
                              lambda w, e: self.drop_progress_event(e))
        canvas_w.add_callback('drop-end',
                              lambda w, e: self.drop_event(e))

        # Define cursors
        cursor_names = cursor_info.get_cursor_names()
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            self.build_cursor(canvas_w, curinfo)
            self.define_cursor(curinfo.name, curinfo.name)

        canvas_w.set_cursor('pick')

    def build_cursor(self, canvas_w, curinfo):
        size_px = 16
        wd = int(curinfo.scale_width * size_px)
        ht = int(curinfo.scale_height * size_px)
        hotspot_x = int(curinfo.point_x_pct * wd)
        hotspot_y = int(curinfo.point_y_pct * ht)
        path = curinfo.path
        if in_situ_web:
            with open(path, 'rb') as svg_f:
                buf = svg_f.read()
            path = PgHelp.get_image_src_from_buffer(buf, imgtype='svg')
        canvas_w.add_cursor(curinfo.name, path,
                            hotspot_x, hotspot_y, [wd, ht])

    def set_cursor(self, name):
        if self.pgcanvas is not None:
            self.pgcanvas.set_cursor(name)

    def transkey(self, key_js, keycode):
        self.logger.debug("key in js '%s'" % (key_js))
        if key_js in self._keytbl:
            key = self._keytbl[key_js]
        elif keycode in self._keytbl2:
            key = self._keytbl2[keycode]
        else:
            key = key_js

        self.logger.debug("key name in ginga '%s'" % (key))
        return key

    def get_key_table(self):
        return self._keytbl

    def focus_event(self, event, has_focus):
        self.logger.debug("focus event: focus=%s" % (has_focus))
        return self.make_callback('focus', has_focus)

    def enter_notify_event(self, event):
        self.logger.debug("entering widget...")
        enter_focus = self.t_.get('enter_focus', False)
        if enter_focus:
            self.pgcanvas.set_focus()
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, event):
        # For key_press_events, javascript reports the actual printable
        # key name.  We use a special keymap to just handle the few
        # characters for which we have special names
        keyname = event.key
        self.logger.debug("key press event, keyname=%s" % (keyname))
        if keyname in self._keytbl3:
            keyname = self._keytbl3[keyname]
        self.logger.debug("making key-press cb, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_down_event(self, event):
        # For key down events, javascript only validly reports a key code.
        # We look up the code to determine the key name
        keycode = event.keycode
        self.logger.debug("key down event, key='%s', keycode=%s" % (event.key,
                                                                    keycode))
        keyname = self.transkey(event.key, keycode)
        self.logger.debug("keyname=%s" % (keyname))

        self.logger.debug("making key-press cb, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_up_event(self, event):
        keycode = event.keycode
        self.logger.debug("key release event, keycode=%s" % (keycode))
        keyname = self.transkey(event.key, keycode)

        self.logger.debug("making key-release cb, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, event):
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y
        button = 0
        button |= 0x1 << event.button_trigger - 1
        self._button = button
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()
        return self.make_ui_callback_viewer(self, 'button-press', button,
                                            data_x, data_y)

    def button_release_event(self, event):
        # event.button, event.x, event.y
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y
        button = 0
        button |= 0x1 << event.button_trigger - 1
        self._button = 0
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()
        return self.make_ui_callback_viewer(self, 'button-release', button,
                                            data_x, data_y)

    def motion_notify_event(self, event):
        #button = 0
        button = self._button
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y

        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'motion', button,
                                            data_x, data_y)

    def scroll_event(self, event):
        x, y = event.x, event.y
        delta = event.delta_y
        dx, dy = event.delta_x, event.delta_y
        self.last_win_x, self.last_win_y = x, y

        # if (dx != 0 or dy != 0):
        #     # <= This browser gives us deltas for x and y
        #     # Synthesize this as a pan gesture event
        #     self.make_ui_callback_viewer(self, 'pan', 'start', 0, 0)
        #     self.make_ui_callback_viewer(self, 'pan', 'move', dx, dy)
        #     return self.make_ui_callback_viewer(self, 'pan', 'stop', 0, 0)

        # 15 deg is standard 1-click turn for a wheel mouse
        # delta usually returns +/- 1.0
        #num_degrees = abs(delta) * 15.0
        num_degrees = abs(delta)
        # NOTE: reverse direction for mouse wheel
        delta = - delta

        direction = 0.0
        if delta > 0:
            direction = 0.0
        elif delta < 0:
            direction = 180.0
        self.logger.debug("scroll deg=%f direction=%f" % (
            num_degrees, direction))

        data_x, data_y = self.check_cursor_location()

        return self.make_ui_callback_viewer(self, 'scroll', direction,
                                            num_degrees, data_x, data_y)

    def drop_progress_event(self, event):
        pass

    def drop_event(self, event):
        if event['type'] != 'drop':
            return

        drop = events.DropEvent()
        # common elements for a drop
        data_x, data_y = self.check_cursor_location()
        drop.set(timestamp=event['time_stamp'], types=event['types'],
                 x=event['x'], y=event['y'], data_x=data_x, data_y=data_y)

        if len(event["files"]) > 0:
            drop.set_blobs(event["files"])
            drop.set(types=event['types'], encoding='base64')

        elif len(event["text"]) > 0:
            drop.set_text(event["text"])

        elif len(event["html"]) > 0:
            drop.set_html(event["html"])

        elif event["url"] is not None:
            drop.set_uris([event["url"]])

        return self.make_ui_callback_viewer(self, 'drag-drop', drop)


class ImageViewEvent(Mixins.UIMixin, PgEventMixin, ImageViewPg):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageViewPg.__init__(self, logger=logger, rgbmap=rgbmap,
                             settings=settings, render=render)
        Mixins.UIMixin.__init__(self)
        PgEventMixin.__init__(self)


class ImageViewZoom(ImageViewEvent):

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
                 render='widget',
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings, render=render)

        self.ui_set_active(True, viewer=self)

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

    def center_cursor(self):
        # NOP
        pass

    def position_cursor(self, data_x, data_y):
        # NOP
        pass


class CanvasView(ImageViewZoom):

    def __init__(self, logger=None, settings=None, rgbmap=None,
                 render='widget',
                 bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger, settings=settings,
                               rgbmap=rgbmap, render=render,
                               bindmap=bindmap, bindings=bindings)

        # Needed for UIMixin to propagate events correctly
        self.objects = [self.private_canvas]

    def set_canvas(self, canvas, private_canvas=None):
        super().set_canvas(canvas, private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


class ScrolledViewPg(Widgets.AbstractScrollArea):
    """A class that can take a viewer as a parameter and add scroll bars
    that respond to the pan/zoom levels.
    """

    def __init__(self, *args):
        if in_situ_web:
            session, viewer = None, args[0]
            super().__init__()
        else:
            session, viewer = args
            super().__init__(session)
        self.viewer = viewer

        self._bar_status = dict(horizontal='on', vertical='on')
        # the window jiggles annoyingly as the scrollbar is alternately
        # shown and hidden if we use the default "as needed" policy, so
        # default to always showing them (user can change this after
        # calling the constructor, if desired)
        self.scroll_bars(horizontal='on', vertical='on')

        self._adjusting = False
        self._scrolling = False
        self.pad = 0
        self.viewer_w = None

        # we parent the viewer widget
        w = viewer.get_widget()
        if w is None or not isinstance(w, Widgets.Image):
            # <-- viewer has not had a widget set yet--let's create one
            if in_situ_web:
                self.viewer_w = Widgets.Image(interactive=True,
                                              use_animation_frame=True)
            else:
                self.viewer_w = Widgets.Image(session, interactive=True,
                                              use_animation_frame=True)
            viewer.set_widget(self.viewer_w)
        else:
            # <-- viewer already had a widget
            self.viewer_w = w

        # and embed it in our scroll area
        self.set_widget(self.viewer_w)

        self.timer_scroll_lock = threading.RLock()
        if in_situ_web:
            self.timer_scroll = Widgets.Timer()
        else:
            self.timer_scroll = Widgets.Timer(session)
        self.timer_scroll.add_callback('expired', self.delayed_scrolled_cb)

        # callback when the user scrolls
        self.add_callback('scrolled', self._scrolled_cb)
        # callback when the user resizes our scroll area
        self.add_callback('area-resize', self._resize_cb)

        # callback when the viewer redraws
        self.viewer.add_callback('redraw', self._calc_scrollbars)
        # callback when the viewer limits are set
        self.viewer.add_callback('limits-set',
                                 lambda v, l: self._calc_scrollbars(v, 0))

        self._calc_scrollbars(viewer, 0)

    def _resize_cb(self, mywidget, wd, ht, v_thmb_wd, h_thmb_wd):
        """Resize the viewer widget when the ScrolledView is resized."""
        if self.viewer_w is not None:
            self.viewer_w.resize(wd, ht)

    def _scrolled_cb(self, mywidget, scroll_h_pct, scroll_v_pct):
        """Gets called when our scroll bars are manipulated."""
        if self._adjusting:
            return

        with self.timer_scroll_lock:
            self.timer_scroll.cond_set(0.15)

    def delayed_scrolled_cb(self, timer, *args):
        """Gets called when our scroll bars are manipulated."""
        if self._adjusting:
            return

        self._scrolling = True
        try:
            scroll_h_pct, scroll_v_pct = self.get_scroll_percent()
            pct_x = scroll_h_pct
            # invert Y pct because of orientation of scrollbar
            pct_y = 1.0 - scroll_v_pct

            self.viewer.pan_by_pct(pct_x, pct_y, pad=self.pad)

            # This shouldn't be necessary, but seems to be
            self.viewer.redraw(whence=0)

        finally:
            self._scrolling = False

    def _calc_scrollbars(self, viewer, whence):
        """Calculate and set the scrollbar handles from the pan and
        zoom positions.
        """
        if self._scrolling or whence > 0:
            return

        # flag that suppresses a cyclical callback
        self._adjusting = True
        try:
            res = self.viewer.calc_pan_pct(pad=self.pad)
            if res is None:
                return

            self.set_thumb_percent(res.thm_pct_x, res.thm_pct_y)
            pct_x, pct_y = res.pan_pct_x, 1.0 - res.pan_pct_y
            self.set_scroll_percent(pct_x, pct_y)

        finally:
            self._adjusting = False

    def scroll_bars(self, horizontal='on', vertical='on'):
        self._bar_status.update(dict(horizontal=horizontal,
                                     vertical=vertical))
        self.set_scroll_bar_visibility(horizontal, vertical)

    def get_scroll_bars_status(self):
        return self._bar_status


class ScrolledView(ScrolledViewPg):
    def __init__(self, viewer, parent=None):
        from ginga.web.pgw import Widgets as Ginga_Widgets
        super().__init__(Ginga_Widgets._session, viewer)
