#
# ImageViewPg.py -- a backend for Ginga using javascript and
#      HTML5 canvas and websockets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

from ginga import ImageView, Mixins, Bindings
from ginga.canvas.mixins import DrawingMixin, CanvasMixin, CompoundMixin
from ginga.canvas import render
from ginga.util.toolbox import ModeIndicator


default_html_fmt = 'jpeg'


class ImageViewPgError(ImageView.ImageViewError):
    pass


class ImageViewPg(ImageView.ImageViewBase):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageView.ImageViewBase.__init__(self, logger=logger,
                                         rgbmap=rgbmap, settings=settings)

        self.pgcanvas = None

        # format for rendering image on HTML5 canvas
        # NOTE: 'jpeg' has much better performance than 'png', but can show
        # some artifacts, especially noticeable with small text
        self.t_.set_defaults(html5_canvas_format=default_html_fmt,
                             renderer='cairo')

        self.rgb_order = 'RGBA'
        # this should already be so, but just in case...
        self.defer_redraw = True

        # these will be assigned in set_widget()
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

        app = canvas_w.get_app()
        self.timer_redraw = app.make_timer()
        self.timer_redraw.add_callback('expired',
                                       lambda t: self.delayed_redraw())
        self.timer_msg = app.make_timer()
        self.timer_msg.add_callback('expired',
                                    lambda t: self.clear_onscreen_message())

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

            self.pgcanvas.do_update(buf)

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

    def set_cursor(self, cursor):
        if self.pgcanvas is None:
            return
        #self.pgcanvas.config(cursor=cursor)

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

    def map_event(self, event):
        self.logger.info("window mapped to %dx%d" % (
            event.width, event.height))
        self.configure_window(event.width, event.height)
        self.redraw(whence=0)

    def resize_event(self, event):
        wd, ht = event.width, event.height
        # Not quite ready for prime-time--browser seems to mess with the
        # aspect ratio
        self.logger.info("canvas resized to %dx%d" % (wd, ht))
        self.configure_window(wd, ht)
        self.redraw(whence=0)

    def resize(self, width, height):
        """Resize our window to width x height.
        May not work---depending on how the HTML5 canvas is embedded.
        """
        # this shouldn't be needed
        self.configure_window(width, height)

        self.pgcanvas.resize(width, height)

        # hack to force a browser reload
        app = self.pgcanvas.get_app()
        app.do_operation('reload_page', id=self.pgcanvas.id)


class ImageViewEvent(ImageViewPg):

    def __init__(self, logger=None, rgbmap=None, settings=None, render=None):
        ImageViewPg.__init__(self, logger=logger, rgbmap=rgbmap,
                             settings=settings, render=render)

        self._button = 0

        # @$%&^(_)*&^ javascript!!
        # table mapping javascript key codes to ginga key names
        # see key_down_event() and key_up_event()
        #
        # https://www.cambiaresearch.com/articles/15/javascript-char-codes-key-codes
        self._keytbl = {
            8: 'backspace',
            9: 'tab',
            13: 'return',
            16: 'shift_l',
            #'shift_r': 'shift_r',
            17: 'control_l',
            #'control_r': 'control_r',
            18: 'alt_l',
            #'alt_r': 'alt_r',
            19: 'break',
            20: 'caps_lock',
            27: 'escape',
            32: 'space',
            33: 'page_up',
            34: 'page_down',
            35: 'end',
            36: 'home',
            37: 'left',
            38: 'up',
            39: 'right',
            40: 'down',
            45: 'insert',
            46: 'delete',
            65: 'a',
            66: 'b',
            67: 'c',
            68: 'd',
            69: 'e',
            70: 'f',
            71: 'g',
            72: 'h',
            73: 'i',
            74: 'j',
            75: 'k',
            76: 'l',
            77: 'm',
            78: 'n',
            79: 'o',
            80: 'p',
            81: 'q',
            82: 'r',
            83: 's',
            84: 't',
            85: 'u',
            86: 'v',
            87: 'w',
            88: 'x',
            89: 'y',
            90: 'z',
            91: 'super_l',
            92: 'super_r',
            93: 'menu_r',
            96: 'numpad_0',
            97: 'numpad_1',
            98: 'numpad_2',
            99: 'numpad_3',
            100: 'numpad_4',
            101: 'numpad_5',
            102: 'numpad_6',
            103: 'numpad_7',
            104: 'numpad_8',
            105: 'numpad_9',
            106: 'numpad_*',
            107: 'numpad_+',
            109: 'numpad_-',
            110: 'numpad_.',
            111: 'numpad_/',
            112: 'f1',
            113: 'f2',
            114: 'f3',
            115: 'f4',
            116: 'f5',
            117: 'f6',
            118: 'f7',
            119: 'f8',
            120: 'f9',
            121: 'f10',
            122: 'f11',
            123: 'f12',
            144: 'num_lock',
            145: 'scroll_lock',
            189: '-',
            186: ';',
            187: '=',
            188: ',',
            190: '.',
            191: '/',
            192: 'backquote',
            219: '[',
            220: 'backslash',
            221: ']',
            222: 'singlequote',
        }

        # this is an auxilliary table used to map shifted keys to names
        # see key_down_event() and key_up_event()
        self._keytbl2 = {
            ('shift_l', 'backquote'): '~',
            ('shift_l', '1'): '!',
            ('shift_l', '2'): '@',
            ('shift_l', '3'): '#',
            ('shift_l', '4'): '$',
            ('shift_l', '5'): '%',
            ('shift_l', '6'): '^',
            ('shift_l', '7'): '&',
            ('shift_l', '8'): '*',
            ('shift_l', '9'): '(',
            ('shift_l', '0'): ')',
            ('shift_l', 'a'): 'A',
            ('shift_l', 'b'): 'B',
            ('shift_l', 'c'): 'C',
            ('shift_l', 'd'): 'D',
            ('shift_l', 'e'): 'E',
            ('shift_l', 'f'): 'F',
            ('shift_l', 'g'): 'G',
            ('shift_l', 'h'): 'H',
            ('shift_l', 'i'): 'I',
            ('shift_l', 'j'): 'J',
            ('shift_l', 'k'): 'K',
            ('shift_l', 'l'): 'L',
            ('shift_l', 'm'): 'M',
            ('shift_l', 'n'): 'N',
            ('shift_l', 'o'): 'O',
            ('shift_l', 'p'): 'P',
            ('shift_l', 'q'): 'Q',
            ('shift_l', 'r'): 'R',
            ('shift_l', 's'): 'S',
            ('shift_l', 't'): 'T',
            ('shift_l', 'u'): 'U',
            ('shift_l', 'v'): 'V',
            ('shift_l', 'w'): 'W',
            ('shift_l', 'x'): 'X',
            ('shift_l', 'y'): 'Y',
            ('shift_l', 'z'): 'Z',
            ('shift_l', '-'): '_',
            ('shift_l', '='): '+',
            ('shift_l', '['): '{',
            ('shift_l', ']'): '}',
            ('shift_l', 'backslash'): '|',
            ('shift_l', ';'): ':',
            ('shift_l', 'singlequote'): 'doublequote',
            ('shift_l', ','): '<',
            ('shift_l', '.'): '>',
            ('shift_l', '/'): '?',
        }

        # this table is used to map special characters to character names
        # see key_press_event()
        self._keytbl3 = {
            '\\': 'backslash',
            '"': 'doublequote',
            "'": 'singlequote',
            "`": 'backquote',
            " ": 'space',
        }

        # list of keys for which javascript will give us a keydown event,
        # but not a keypress event.  We use this list to synthesize one.
        self._browser_problem_keys = set(['shift_l', 'control_l', 'alt_l',
                                          'super_l', 'super_r', 'menu_r',
                                          'escape', 'tab',
                                          'left', 'up', 'right', 'down',
                                          'insert', 'delete', 'home', 'end',
                                          'page_up', 'page_down',
                                          ])
        # Define cursors for pick and pan
        #hand = openHandCursor()
        hand = 'fleur'
        self.define_cursor('pan', hand)
        cross = 'cross'
        self.define_cursor('pick', cross)

        self._shifted = False

        for name in ('motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'rotate', 'pan', 'swipe', 'tap'):
            self.enable_callback(name)

    def set_widget(self, canvas):
        super(ImageViewEvent, self).set_widget(canvas)

        # see event binding setup in Viewers.py

        #return self.make_callback('map')

    def transkey(self, keycode):
        self.logger.debug("key code in js '%d'" % (keycode))
        if keycode in self._keytbl:
            key = self._keytbl[keycode]
        else:
            key = chr(keycode)

        if self._shifted:
            try:
                key = self._keytbl2[('shift_l', key)]
            except KeyError:
                pass

        self.logger.debug("key name in ginga '%s'" % (key))
        return key

    def get_key_table(self):
        return self._keytbl

    def focus_event(self, event, has_focus):
        self.logger.debug("focus event: focus=%s" % (has_focus))
        return self.make_callback('focus', has_focus)

    def enter_notify_event(self, event):
        self.logger.debug("entering widget...")
        ## enter_focus = self.t_.get('enter_focus', False)
        ## if enter_focus:
        ##     self.pgcanvas.focus_set()
        return self.make_callback('enter')

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        return self.make_callback('leave')

    def key_press_event(self, event):
        # For key_press_events, javascript reports the actual printable
        # key name.  We use a special keymap to just handle the few
        # characters for which we have special names
        keyname = event.key_name
        self.logger.debug("key press event, keyname=%s" % (keyname))
        if keyname in self._keytbl3:
            keyname = self._keytbl3[keyname]
        self.logger.debug("making key-press cb, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-press', keyname)

    def key_down_event(self, event):
        # For key down events, javascript only validly reports a key code.
        # We look up the code to determine the
        keycode = event.key_code
        self.logger.debug("key down event, keycode=%s" % (keycode))
        keyname = self.transkey(keycode)
        # special hack for modifiers
        if keyname == 'shift_l':
            self._shifted = True

        if keyname in self._browser_problem_keys:
            # JS doesn't report key press callbacks for certain keys
            # so we synthesize one here for those
            self.logger.debug("making key-press cb, key=%s" % (keyname))
            return self.make_ui_callback_viewer(self, 'key-press', keyname)
        return False

    def key_up_event(self, event):
        keycode = event.key_code
        self.logger.debug("key release event, keycode=%s" % (keycode))
        keyname = self.transkey(keycode)
        # special hack for modifiers
        if keyname == 'shift_l':
            self._shifted = False

        self.logger.debug("making key-release cb, key=%s" % (keyname))
        return self.make_ui_callback_viewer(self, 'key-release', keyname)

    def button_press_event(self, event):
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y
        button = 0
        button |= 0x1 << event.button
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
        button |= 0x1 << event.button
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
        delta = event.delta
        dx, dy = event.dx, event.dy
        self.last_win_x, self.last_win_y = x, y

        if (dx != 0 or dy != 0):
            # <= This browser gives us deltas for x and y
            # Synthesize this as a pan gesture event
            self.make_ui_callback_viewer(self, 'pan', 'start', 0, 0)
            self.make_ui_callback_viewer(self, 'pan', 'move', dx, dy)
            return self.make_ui_callback_viewer(self, 'pan', 'stop', 0, 0)

        # 15 deg is standard 1-click turn for a wheel mouse
        # delta usually returns +/- 1.0
        num_degrees = abs(delta) * 15.0

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

    def drop_event(self, event):
        data = event.delta
        self.logger.debug("data=%s" % (str(data)))
        paths = data.split('\n')
        self.logger.debug("dropped text(s): %s" % (str(paths)))
        return self.make_ui_callback_viewer(self, 'drag-drop', paths)

    def pinch_event(self, event):
        self.logger.debug("pinch: event=%s" % (str(event)))
        state = 'move'
        if event.type == 'pinchstart' or event.isfirst:
            state = 'start'
        elif event.type == 'pinchend' or event.isfinal:
            state = 'end'
        rot = event.theta
        scale = event.scale
        self.logger.debug("pinch gesture rot=%f scale=%f state=%s" % (
            rot, scale, state))

        return self.make_ui_callback_viewer(self, 'pinch', state, rot, scale)

    def rotate_event(self, event):
        state = 'move'
        if event.type == 'rotatestart' or event.isfirst:
            state = 'start'
        elif event.type == 'rotateend' or event.isfinal:
            state = 'end'
        rot = event.theta
        self.logger.debug("rotate gesture rot=%f state=%s" % (
            rot, state))

        return self.make_ui_callback_viewer(self, 'rotate', state, rot)

    def pan_event(self, event):
        state = 'move'
        if event.type == 'panstart' or event.isfirst:
            state = 'start'
        elif event.type == 'panend' or event.isfinal:
            state = 'end'
        # TODO: need to know which ones to flip
        dx, dy = -event.dx, event.dy
        self.logger.debug("pan gesture dx=%f dy=%f state=%s" % (
            dx, dy, state))

        return self.make_ui_callback_viewer(self, 'pan', state, dx, dy)

    def swipe_event(self, event):
        if event.isfinal:
            state = 'end'  # noqa
            self.logger.debug("swipe gesture event=%s" % (str(event)))
            ## self.logger.debug("swipe gesture hdir=%s vdir=%s" % (
            ##     hdir, vdir))
            ## return self.make_ui_callback_viewer(self, 'swipe', state,
            ##                                     hdir, vdir)

    def tap_event(self, event):
        if event.isfinal:
            state = 'end'  # noqa
            self.logger.debug("tap gesture event=%s" % (str(event)))


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
                 render='widget',
                 bindmap=None, bindings=None):
        ImageViewEvent.__init__(self, logger=logger, rgbmap=rgbmap,
                                settings=settings, render=render)
        Mixins.UIMixin.__init__(self)

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
        super(CanvasView, self).set_canvas(canvas,
                                           private_canvas=private_canvas)

        self.objects[0] = self.private_canvas


class ImageViewCanvas(ImageViewZoom,
                      DrawingMixin, CanvasMixin, CompoundMixin):

    def __init__(self, logger=None, rgbmap=None, settings=None,
                 render='widget', bindmap=None, bindings=None):
        ImageViewZoom.__init__(self, logger=logger,
                               rgbmap=rgbmap,
                               settings=settings, render=render,
                               bindmap=bindmap,
                               bindings=bindings)
        CompoundMixin.__init__(self)
        CanvasMixin.__init__(self)
        DrawingMixin.__init__(self)

        # we are both a viewer and a canvas
        self.set_canvas(self, private_canvas=self)

        self._mi = ModeIndicator(self)


#END
