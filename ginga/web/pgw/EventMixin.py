#
# EventMixin.py -- mixin class for handling events in pg widgets.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.cursors import cursor_info
from ginga import events


class PlotEventMixin:

    def __init__(self):
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
        # Define cursors
        cursor_names = cursor_info.get_cursor_names()
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            self.define_cursor(curinfo.name, curinfo.web)

        self._shifted = False
        # this is set in set_widget()
        self.pgcanvas = None

    def set_widget(self, canvas_w):
        self.logger.debug("set widget canvas_w=%s" % canvas_w)
        self.pgcanvas = canvas_w

        app = canvas_w.get_app()
        self.timer_resize = app.make_timer()
        self.timer_resize.add_callback('expired',
                                       lambda t: self.delayed_resize())
        self.timer_msg = app.make_timer()
        self.timer_msg.add_callback('expired',
                                    lambda t: self.onscreen_message_off())

        wd, ht = canvas_w.get_size()
        self.set_window_size(wd, ht)

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

    def _get_modifiers(self, event):
        modifiers = set([])
        if event.ctrl_key:
            modifiers.add('ctrl')
        if event.meta_key:
            modifiers.add('meta')
        if event.shift_key:
            modifiers.add('shift')
        return modifiers

    def map_event(self, event):
        wd, ht = event.width, event.height
        g_event = events.MapEvent(state='mapped', width=wd, height=ht,
                                  viewer=self)
        self.make_callback('map', g_event)

    def resize_event(self, event):
        wd, ht = event.width, event.height
        g_event = events.ResizeEvent(width=wd, height=ht, viewer=self)
        self.make_callback('resize', g_event)

    def focus_event(self, event, has_focus):
        self.logger.debug("focus event: focus=%s" % (has_focus))
        data_x, data_y = self.check_cursor_location()
        state = 'focus' if has_focus else 'unfocus'
        g_event = events.FocusEvent(state=state, mode=None, focus=has_focus,
                                    viewer=self)
        return self.make_callback('focus', g_event)

    def enter_notify_event(self, event):
        self.logger.debug("entering widget...")
        ## enter_focus = self.t_.get('enter_focus', False)
        ## if enter_focus:
        ##     self.pgcanvas.focus_set()
        data_x, data_y = self.check_cursor_location()
        g_event = events.EnterLeaveEvent(state='enter', mode=None,
                                         data_x=data_x, data_y=data_y,
                                         viewer=self)
        return self.make_callback('enter', g_event)

    def leave_notify_event(self, event):
        self.logger.debug("leaving widget...")
        last_data_x, last_data_y = self.get_last_data_xy()
        g_event = events.EnterLeaveEvent(state='leave', mode=None,
                                         data_x=last_data_x, data_y=last_data_y,
                                         viewer=self)
        return self.make_callback('leave', g_event)

    def key_press_event(self, event):
        # For key_press_events, javascript reports the actual printable
        # key name.  We use a special keymap to just handle the few
        # characters for which we have special names
        keyname = event.key_name
        self.logger.debug("key press event, keyname=%s" % (keyname))
        if keyname in self._keytbl3:
            keyname = self._keytbl3[keyname]
        modifiers = self._get_modifiers(event)
        self.logger.debug("making key-press cb, key=%s" % (keyname))
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.KeyEvent(key=keyname, state='down', mode=None,
                                  modifiers=modifiers,
                                  data_x=last_data_x, data_y=last_data_y,
                                  viewer=self)
        return self.make_ui_callback_viewer(self, 'key-press', g_event)

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
            modifiers = self._get_modifiers(event)
            self.logger.debug("making key-press cb, key=%s" % (keyname))
            last_data_x, last_data_y = self.get_last_data_xy()

            g_event = events.KeyEvent(key=keyname, state='down', mode=None,
                                      modifiers=modifiers,
                                      data_x=last_data_x, data_y=last_data_y,
                                      viewer=self)
            return self.make_ui_callback_viewer(self, 'key-press', g_event)

        return False

    def key_up_event(self, event):
        keycode = event.key_code
        self.logger.debug("key release event, keycode=%s" % (keycode))
        keyname = self.transkey(keycode)
        # special hack for modifiers
        if keyname == 'shift_l':
            self._shifted = False

        modifiers = self._get_modifiers(event)
        self.logger.debug("making key-release cb, key=%s" % (keyname))
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.KeyEvent(key=keyname, state='up', mode=None,
                                  modifiers=modifiers,
                                  data_x=last_data_x, data_y=last_data_y,
                                  viewer=self)
        return self.make_ui_callback_viewer(self, 'key-release', g_event)

    def button_press_event(self, event):
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y
        button = 0
        button |= 0x1 << event.button
        self._button = button
        modifiers = self._get_modifiers(event)
        self.logger.debug("button event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()
        g_event = events.PointEvent(button=button, state='down', mode=None,
                                    modifiers=modifiers,
                                    data_x=data_x, data_y=data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'button-press', g_event)

    def button_release_event(self, event):
        # event.button, event.x, event.y
        x = event.x
        y = event.y
        self.last_win_x, self.last_win_y = x, y
        button = 0
        button |= 0x1 << event.button
        self._button = 0
        modifiers = self._get_modifiers(event)
        self.logger.debug("button release at %dx%d button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()
        g_event = events.PointEvent(button=button, state='up', mode=None,
                                    modifiers=modifiers,
                                    data_x=data_x, data_y=data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'button-release', g_event)

    def motion_notify_event(self, event):
        #button = 0
        button = self._button
        x, y = event.x, event.y
        self.last_win_x, self.last_win_y = x, y
        modifiers = self._get_modifiers(event)

        self.logger.debug("motion event at %dx%d, button=%x" % (x, y, button))

        data_x, data_y = self.check_cursor_location()

        g_event = events.PointEvent(button=button, state='move', mode=None,
                                    modifiers=modifiers,
                                    data_x=data_x, data_y=data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'motion', g_event)

    def scroll_event(self, event):
        x, y = event.x, event.y
        delta = event.delta
        dx, dy = event.dx, event.dy
        self.last_win_x, self.last_win_y = x, y
        modifiers = self._get_modifiers(event)

        # if (dx != 0 or dy != 0):
        #     # <= This browser gives us deltas for x and y
        #     # Synthesize this as a pan gesture event
        #     self.make_ui_callback_viewer(self, 'pan', 'start', 0, 0)
        #     self.make_ui_callback_viewer(self, 'pan', 'move', dx, dy)
        #     return self.make_ui_callback_viewer(self, 'pan', 'stop', 0, 0)

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

        g_event = events.ScrollEvent(button=0, state='scroll', mode=None,
                                     modifiers=modifiers,
                                     direction=direction, amount=num_degrees,
                                     data_x=data_x, data_y=data_y,
                                     viewer=self)
        return self.make_ui_callback_viewer(self, 'scroll', g_event)

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
