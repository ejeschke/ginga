#
# EventMixin.py -- mixin class for handling events in matplotlib.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from matplotlib.backend_tools import Cursors

from ginga import events
from ginga.cursors import cursor_info
from ginga.mplw import MplHelp


class PlotEventMixin:
    """Mixin class for adding Matplotlib non-web toolkit UI events to
    a plot viewer.
    """

    def __init__(self):
        # for matplotlib key handling
        self._keytbl = {
            'shift': 'shift_l',
            'control': 'control_l',
            'alt': 'alt_l',
            'win': 'meta_l',  # windows key
            'cmd': 'meta_l',  # Command key on Macs
            '`': 'backquote',
            '"': 'doublequote',
            "'": 'singlequote',
            '\\': 'backslash',
            ' ': 'space',
            'enter': 'return',
            'pageup': 'page_up',
            'pagedown': 'page_down',
        }

        # For callbacks
        for name in ['motion', 'button-press', 'button-release',
                     'key-press', 'key-release', 'drag-drop',
                     'scroll', 'map', 'focus', 'enter', 'leave',
                     'pinch', 'pan',  # 'swipe', 'tap',
                     'pixel-info']:
            self.enable_callback(name)

        self.add_callback('pixel-info', self.pixel_info_cb)

    def connect_ui(self, mpl_canvas):
        connect = mpl_canvas.mpl_connect
        connect("motion_notify_event", self.motion_notify_event)
        connect("button_press_event", self.button_press_event)
        connect("button_release_event", self.button_release_event)
        connect("scroll_event", self.scroll_event)
        mpl_canvas.capture_scroll = True
        connect("figure_enter_event", self.enter_notify_event)
        connect("figure_leave_event", self.leave_notify_event)
        connect("key_press_event", self.key_down_event)
        connect("key_release_event", self.key_up_event)
        connect("resize_event", self.resize_event)

        self.timer_resize = MplHelp.Timer(mplcanvas=mpl_canvas)
        self.timer_resize.add_callback('expired',
                                       lambda t: self.delayed_resize())

        self.timer_msg = MplHelp.Timer(mplcanvas=mpl_canvas)
        self.timer_msg.add_callback('expired',
                                    lambda t: self.onscreen_message_off())

        # Define cursors
        cursor_names = cursor_info.get_cursor_names()
        # TODO: handle other cursor types
        cross = Cursors.POINTER
        for curname in cursor_names:
            curinfo = cursor_info.get_cursor_info(curname)
            self.define_cursor(curinfo.name, cross)
        self.switch_cursor('pick')

    def _get_modifiers(self, event):
        return event.modifiers

    def _get_button(self, event):
        try:
            btn = 0x1 << (event.button.value - 1)
        except Exception:
            btn = 0
        return btn

    def transkey(self, keyname):
        self.logger.debug("matplotlib keyname='%s'" % (keyname))
        if keyname is None:
            return keyname
        key = keyname
        if 'shift+' in key:
            key = key.replace('shift+', '')
        if 'ctrl+' in key:
            key = key.replace('ctrl+', '')
        if 'alt+' in key:
            key = key.replace('alt+', '')
        if 'meta+' in key:
            key = key.replace('meta+', '')
        key = self._keytbl.get(key, key)
        return key

    def get_key_table(self):
        return self._keytbl

    def _get_key(self, event):
        keyval = self.transkey(event.key)
        self.logger.debug("key event, mpl={}, key={}".format(event.key,
                                                             keyval))
        return keyval

    def scroll_event(self, event):
        button = self._get_button(event)
        if event.button == 'up':
            direction = 0.0
        elif event.button == 'down':
            direction = 180.0
        amount = event.step
        modifiers = self._get_modifiers(event)

        data_x, data_y = event.xdata, event.ydata
        self.set_last_data_xy(data_x, data_y)

        num_degrees = amount  # ???
        g_event = events.ScrollEvent(button=0, state='scroll', mode=None,
                                     modifiers=modifiers,
                                     direction=direction, amount=num_degrees,
                                     data_x=data_x, data_y=data_y,
                                     viewer=self)
        return self.make_ui_callback_viewer(self, 'scroll', g_event)

    def button_press_event(self, event):
        button = self._get_button(event)
        modifiers = self._get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.PointEvent(button=button, state='down', mode=None,
                                    modifiers=modifiers,
                                    data_x=last_data_x, data_y=last_data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'button-press', g_event)

    def button_release_event(self, event):
        button = self._get_button(event)
        modifiers = self._get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.PointEvent(button=button, state='up', mode=None,
                                    modifiers=modifiers,
                                    data_x=last_data_x, data_y=last_data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'button-release', g_event)

    def motion_notify_event(self, event):
        button = self._get_button(event)
        modifiers = self._get_modifiers(event)

        data_x, data_y = event.xdata, event.ydata
        self.set_last_data_xy(data_x, data_y)

        g_event = events.PointEvent(button=button, state='move', mode=None,
                                    modifiers=modifiers,
                                    data_x=data_x, data_y=data_y,
                                    viewer=self)
        return self.make_ui_callback_viewer(self, 'motion', g_event)

    def key_down_event(self, event):
        key = self._get_key(event)
        modifiers = self._get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.KeyEvent(key=key, state='down', mode=None,
                                  modifiers=modifiers,
                                  data_x=last_data_x, data_y=last_data_y,
                                  viewer=self)
        return self.make_ui_callback_viewer(self, 'key-press', g_event)

    def key_up_event(self, event):
        key = self._get_key(event)
        modifiers = self._get_modifiers(event)
        # NOTE: event.xdata, event.ydata seem to be None
        last_data_x, last_data_y = self.get_last_data_xy()

        g_event = events.KeyEvent(key=key, state='up', mode=None,
                                  modifiers=modifiers,
                                  data_x=last_data_x, data_y=last_data_y,
                                  viewer=self)
        return self.make_ui_callback_viewer(self, 'key-release', g_event)

    def resize_event(self, event):
        wd, ht = event.width, event.height
        g_event = events.ResizeEvent(width=wd, height=ht, viewer=self)
        self.make_callback('resize', g_event)

    def enter_notify_event(self, event):
        if self.t_['plot_enter_focus']:
            self.take_focus()
        #last_data_x, last_data_y = self.get_last_data_xy()
        data_x, data_y = event.xdata, event.ydata
        g_event = events.EnterLeaveEvent(state='enter', mode=None,
                                         data_x=data_x, data_y=data_y,
                                         viewer=self)
        return self.make_callback('enter', g_event)

    def leave_notify_event(self, event):
        #last_data_x, last_data_y = self.get_last_data_xy()
        data_x, data_y = event.xdata, event.ydata
        g_event = events.EnterLeaveEvent(state='leave', mode=None,
                                         data_x=data_x, data_y=data_y,
                                         viewer=self)
        return self.make_callback('leave', g_event)

    def focus_event(self, event, has_focus):
        state = 'focus' if has_focus else 'unfocus'
        g_event = events.FocusEvent(state=state, mode=None, focus=has_focus,
                                    viewer=self)
        return self.make_callback('focus', g_event)

    def take_focus(self):
        w = self.get_widget()
        if hasattr(w, 'setFocus'):
            # NOTE: this is a Qt call, not cross-backend
            # TODO: see if matplotlib has a backend independent way
            # to do this
            w.setFocus()
        elif hasattr(w, 'grab_focus'):
            # NOTE: this is a Gtk3 call, not cross-backend
            w.grab_focus()
