#
# GtkHelp.py -- customized Gtk3 widgets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import os.path
import math
import random
import time

import numpy as np

from ginga.misc import Bunch, Callback
from ginga.fonts import font_asst
import ginga.icons
import ginga.toolkit

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk  # noqa
from gi.repository import Gdk  # noqa
from gi.repository import GdkPixbuf  # noqa
from gi.repository import GObject  # noqa
from gi.repository import Pango  # noqa
import cairo

ginga.toolkit.use('gtk3')

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]

DND_TARGET_TYPE_TEXT = 0
DND_TARGET_TYPE_URIS = 1


class WidgetMask(object):
    def __init__(self, *args):
        self.cb_fn = None
        self.cb_args = []
        self.cb_kwdargs = {}

        self.connected = False
        self.changed = False

    def sconnect(self, signal, cb_fn, *args, **kwdargs):
        self.cb_fn = cb_fn
        self.cb_args = args
        self.cb_kwdargs = kwdargs

        self.connect(signal, self.cb)
        self.connected = True

    def change(self):
        if self.connected:
            self.changed = True

    def cb(self, *args):
        if self.changed:
            self.changed = False
            return

        newargs = list(args)
        newargs.extend(self.cb_args)
        kwdargs = self.cb_kwdargs.copy()
        return self.cb_fn(*newargs, **kwdargs)


class TopLevel(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self)


class CheckButton(WidgetMask, Gtk.CheckButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.CheckButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(CheckButton, self).set_active(newval)


class ToggleButton(WidgetMask, Gtk.ToggleButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.ToggleButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(ToggleButton, self).set_active(newval)

    def toggle(self):
        oldval = self.get_active()
        newval = not oldval
        super(ToggleButton, self).set_active(newval)


class RadioButton(WidgetMask, Gtk.RadioButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.RadioButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(RadioButton, self).set_active(newval)

    def toggle(self):
        oldval = self.get_active()
        newval = not oldval
        super(RadioButton, self).set_active(newval)


class CheckMenuItem(WidgetMask, Gtk.CheckMenuItem):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.CheckMenuItem.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(CheckMenuItem, self).set_active(newval)


class SpinButton(WidgetMask, Gtk.SpinButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.SpinButton.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(SpinButton, self).set_value(newval)


class HScale(WidgetMask, Gtk.HScale):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.HScale.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(HScale, self).set_value(newval)


class VScale(WidgetMask, Gtk.VScale):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.VScale.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(VScale, self).set_value(newval)


class ComboBox(WidgetMask, Gtk.ComboBox):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.ComboBox.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(ComboBox, self).set_active(newval)

    def insert_alpha(self, text):
        model = self.get_model()
        tup = (text, )
        j = 0
        for i in range(len(model)):
            j = i
            if model[i][0] > text:
                model.insert(j, tup)
                return
        model.insert(j + 1, tup)

    def insert_text(self, idx, text):
        model = self.get_model()
        tup = (text, )
        model.insert(idx, tup)

    def delete_alpha(self, text):
        model = self.get_model()
        for i in range(len(model)):
            if model[i][0] == text:
                del model[i]
                return

    def clear(self):
        model = self.get_model()
        model.clear()

    def show_text(self, text):
        model = self.get_model()
        for i in range(len(model)):
            if model[i][0] == text:
                self.set_active(i)
                return


class Notebook(WidgetMask, Gtk.Notebook):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.Notebook.__init__(self, *args, **kwdargs)

    def set_group_id(self, id):
        super(Notebook, self).set_group_name(str(id))

    def set_current_page(self, new_idx):
        old_idx = self.get_current_page()
        if old_idx != new_idx:
            self.change()

        super(Notebook, self).set_current_page(new_idx)


class MultiDragDropTreeView(Gtk.TreeView):
    '''TreeView that captures mouse events to make drag and drop work
    properly
    See: https://gist.github.com/kevinmehall/278480#file-multiple-selection-dnd-class-py
    '''

    def __init__(self):
        super(MultiDragDropTreeView, self).__init__()

        self.connect('button_press_event', self.on_button_press)
        self.connect('button_release_event', self.on_button_release)
        self.defer_select = False

    def on_button_press(self, widget, event):
        # Here we intercept mouse clicks on selected items so that we can
        # drag multiple items without the click selecting only one
        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (target and
                event.type == Gdk.EventType.BUTTON_PRESS and
                not (event.state &
                     (Gdk.ModifierType.CONTROL_MASK |
                      Gdk.ModifierType.SHIFT_MASK)) and
                self.get_selection().path_is_selected(target[0])):
            # disable selection
            self.get_selection().set_select_function(lambda *ignore: False)
            self.defer_select = target[0]

    def on_button_release(self, widget, event):
        # re-enable selection
        self.get_selection().set_select_function(lambda *ignore: True)

        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (self.defer_select and target and
                self.defer_select == target[0] and
                not (event.x == 0 and event.y == 0)):  # certain drag and drop
            self.set_cursor(target[0], target[1], False)

        self.defer_select = False


class MDISubWindow(Callback.Callbacks):

    def __init__(self, widget, label):
        super(MDISubWindow, self).__init__()

        self.widget = widget

        vbox = Gtk.VBox()
        vbox.set_border_width(4)
        hbox = Gtk.HBox()
        close = Gtk.Button("x")
        maxim = Gtk.Button("^")
        minim = Gtk.Button("v")
        hbox.pack_start(close, False, False, 0)
        hbox.pack_start(minim, False, False, 0)
        hbox.pack_start(maxim, False, False, 0)

        evbox = Gtk.EventBox()
        evbox.add(label)
        modify_bg(evbox, "gray90")
        self.label = label
        self.evbox = evbox
        hbox.pack_start(evbox, True, True, 2)

        vbox.pack_start(hbox, False, False, 0)
        vbox.pack_start(widget, True, True, 4)

        # what size does the widget want to be?
        rect = widget.get_allocation()
        self.x, self.y, wd, ht = rect.x, rect.y, rect.width, rect.height
        ## wd = widget.get_preferred_width()
        ## ht = widget.get_preferred_height()
        ## wd, ht = widget.get_size_request()
        self.width, self.height = max(wd, 300), max(ht, 300)

        frame = Gtk.EventBox()
        frame.set_size_request(self.width, self.height)
        frame.props.visible_window = True
        frame.set_border_width(0)
        modify_bg(frame, "gray70")
        self.frame = frame

        frame.add(vbox)
        frame.show_all()

        for name in ('close', 'maximize', 'minimize'):
            self.enable_callback(name)

        maxim.connect('clicked', lambda *args: self.make_callback('maximize'))
        minim.connect('clicked', lambda *args: self.make_callback('minimize'))
        close.connect('clicked', lambda *args: self.make_callback('close'))

    def raise_(self):
        window = self.frame.get_window()
        if window is not None:
            window.raise_()

    def lower(self):
        window = self.frame.get_window()
        if window is not None:
            window.lower()

    def focus(self):
        self.frame.grab_focus()


class MDIWidget(Gtk.Layout):
    """
    Multiple Document Interface type widget for Gtk.
    """
    def __init__(self):
        Gtk.Layout.__init__(self)

        self.children = []
        self.cur_index = -1
        self.selected_child = None
        self.kbdmouse_mask = 0
        self.cascade_offset = 50
        self.minimized_width = 150
        self.delta_px = 50

        mask = self.get_events()
        self.set_events(mask |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK |
                        Gdk.EventMask.FOCUS_CHANGE_MASK |
                        Gdk.EventMask.STRUCTURE_MASK |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.KEY_PRESS_MASK |
                        Gdk.EventMask.KEY_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK)

        self.connect("motion_notify_event", self.motion_notify_event)
        self.connect("button_press_event", self.button_press_event)
        self.connect("button_release_event", self.button_release_event)

        modify_bg(self, "gray50")

    def add_subwin(self, subwin):

        self.children.append(subwin)

        subwin.evbox.connect("button_press_event", self.select_child_cb, subwin)
        subwin.frame.connect("button_press_event", self.start_resize_cb, subwin)
        subwin.add_callback('maximize', lambda *args: self.maximize_page(subwin))
        subwin.add_callback('minimize', lambda *args: self.minimize_page(subwin))

        self.put(subwin.frame, subwin.x, subwin.y)

        # note: seem to need a slight delay to let the widget be mapped
        # in order to accurately determine its position and size
        #self.update_subwin_position(subwin)
        #self.update_subwin_size(subwin)
        GObject.timeout_add(1000, self.update_subwin_position, subwin)
        GObject.timeout_add(1500, self.update_subwin_size, subwin)

        self._update_area_size()

    def append_page(self, widget, label):

        subwin = MDISubWindow(widget, label)

        # pick a random spot to place the window initially
        rect = self.get_allocation()
        wd, ht = rect.width, rect.height
        x = random.randint(self.cascade_offset,  # nosec
                           max(self.cascade_offset + 10, wd // 2))
        y = random.randint(self.cascade_offset,  # nosec
                           max(self.cascade_offset + 10, ht // 2))
        subwin.x, subwin.y = x, y

        self.add_subwin(subwin)
        return subwin

    def set_tab_reorderable(self, w, tf):
        pass

    def set_tab_detachable(self, w, tf):
        pass

    def get_tab_label(self, w):
        return None

    def page_num(self, widget):
        index, subwin = self._widget_to_index(widget)
        return index

    def get_nth_page(self, idx):
        if 0 <= idx < len(self.children):
            subwin = self.children[idx]
            return subwin.widget
        return None

    def set_current_page(self, idx):
        subwin = self.children[idx]
        subwin.raise_()
        self.cur_index = idx

    def get_current_page(self):
        return self.cur_index

    def _widget_to_index(self, widget):
        index = 0
        for subwin in self.children:
            if subwin.widget == widget:
                return index, subwin
            index += 1
        return -1, None

    def remove_page(self, idx):
        subwin = self.children[idx]
        self.remove(subwin.widget)

    def remove(self, widget):
        idx, subwin = self._widget_to_index(widget)
        if subwin is not None:
            self.children.remove(subwin)
            self.cur_index = -1
            frame = subwin.frame
            super(MDIWidget, self).remove(frame)
            widget.unparent()
        self._update_area_size()

    def get_widget_position(self, widget):
        rect = widget.get_allocation()
        x, y = rect.x, rect.y
        return x, y

    def get_widget_size(self, widget):
        rect = widget.get_allocation()
        width, height = rect.width, rect.height
        return width, height

    def update_subwin_position(self, subwin):
        rect = subwin.frame.get_allocation()
        x, y, = rect.x, rect.y
        subwin.x, subwin.y = x, y

    def update_subwin_size(self, subwin):
        rect = subwin.frame.get_allocation()
        wd, ht = rect.width, rect.height
        subwin.width, subwin.height = wd, ht

    def raise_widget(self, subwin):
        subwin.raise_()

    def select_child_cb(self, layout, event, subwin):
        x_root, y_root = event.x_root, event.y_root

        x, y = self.get_widget_position(subwin.frame)
        subwin.x, subwin.y = x, y

        # make this the selected widget
        idx = self.page_num(subwin.widget)
        if idx >= 0:
            self.set_current_page(idx)

        self.selected_child = Bunch.Bunch(subwin=subwin, action='move',
                                          x_origin=x, y_origin=y,
                                          x_root=x_root, y_root=y_root)
        return True

    def start_resize_cb(self, widget, event, subwin):
        self.update_subwin_size(subwin)

        x_root, y_root = event.x_root, event.y_root
        x, y = widget.translate_coordinates(self, event.x, event.y)

        rect = subwin.frame.get_allocation()
        x1, y1, wd, ht = rect.x, rect.y, rect.width, rect.height
        x2, y2 = x1 + wd, y1 + ht
        subwin.x, subwin.y = x1, y1
        subwin.width, subwin.height = wd, ht

        updates = set([])
        if abs(x - x2) < self.delta_px:
            # right side
            if abs(y - y2) < self.delta_px:
                # lower right corner
                origin = 'lr'
                updates = set(['w', 'h'])
            elif abs(y - y1) < self.delta_px:
                origin = 'ur'
                updates = set(['w', 'h', 'y'])
            else:
                origin = 'r'
                updates = set(['w'])
        elif abs(x - x1) < self.delta_px:
            # left side
            if abs(y - y2) < self.delta_px:
                # lower left corner
                origin = 'll'
                updates = set(['w', 'h', 'x'])
            elif abs(y - y1) < self.delta_px:
                origin = 'ul'
                updates = set(['w', 'h', 'x', 'y'])
            else:
                origin = 'l'
                updates = set(['w', 'x'])
        elif abs(y - y2) < self.delta_px:
            # bottom
            origin = 'b'
            updates = set(['h'])
        else:
            origin = 't'
            updates = set(['h', 'y'])

        self.selected_child = Bunch.Bunch(subwin=subwin, action='resize',
                                          x_origin=x1, y_origin=y1,
                                          wd=wd, ht=ht,
                                          x_root=x_root, y_root=y_root,
                                          origin=origin, updates=updates)
        return True

    def button_press_event(self, widget, event):
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        return True

    def _update_area_size(self):
        rect = self.get_allocation()
        mx_wd, mx_ht = rect.width, rect.height

        for subwin in self.children:
            rect = subwin.frame.get_allocation()
            x, y, wd, ht = rect.x, rect.y, rect.width, rect.height

            mx_wd, mx_ht = max(mx_wd, x + wd), max(mx_ht, y + ht)

        self.set_size(mx_wd, mx_ht)

    def _resize(self, bnch, x_root, y_root):
        subwin = bnch.subwin
        updates = bnch.updates

        dx, dy = x_root - bnch.x_root, y_root - bnch.y_root

        wd = bnch.wd
        if 'w' in updates:
            wd = int(wd + dx)
        ht = bnch.ht
        if 'h' in updates:
            ht = int(ht + dy)

        if 'x' in updates or 'y' in updates:
            x = bnch.x_origin
            if 'x' in updates:
                x = int(x + dx)
                if x < bnch.x_origin:
                    wd = bnch.wd + abs(dx)
                else:
                    wd = bnch.wd + -abs(dx)

            y = bnch.y_origin
            if 'y' in updates:
                y = int(y + dy)
                if y < bnch.y_origin:
                    ht = bnch.ht + abs(dy)
                else:
                    ht = bnch.ht + -abs(dy)

            # this works better if it is not self.move_page()
            self.move(subwin.frame, x, y)

        if 'w' in updates or 'h' in updates:
            # this works better if it is not self.resize_page()
            subwin.frame.set_size_request(wd, ht)

        self._update_area_size()

    def button_release_event(self, widget, event):
        x_root, y_root = event.x_root, event.y_root
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)

        if self.selected_child is not None:
            bnch = self.selected_child
            subwin = bnch.subwin
            if bnch.action == 'move':
                x = int(subwin.x + (x_root - bnch.x_root))
                y = int(subwin.y + (y_root - bnch.y_root))
                self.move_page(subwin, x, y)

            elif bnch.action == 'resize':
                self._resize(bnch, x_root, y_root)

                self.update_subwin_position(subwin)
                # NOTE: necessary for wrapped widget to remember position
                self.move_page(subwin, subwin.x, subwin.y)

                self.update_subwin_size(subwin)
                # NOTE: necessary for wrapped widget to remember size
                self.resize_page(subwin, subwin.width, subwin.height)

            self.selected_child = None

        self._update_area_size()
        return True

    def motion_notify_event(self, widget, event):
        button = self.kbdmouse_mask
        x_root, y_root, state = event.x_root, event.y_root, event.state

        if state & Gdk.ModifierType.BUTTON1_MASK:
            button |= 0x1
        elif state & Gdk.ModifierType.BUTTON2_MASK:
            button |= 0x2
        elif state & Gdk.ModifierType.BUTTON3_MASK:
            button |= 0x4

        if (button & 0x1) and (self.selected_child is not None):
            bnch = self.selected_child
            subwin = bnch.subwin
            if bnch.action == 'move':
                x = int(subwin.x + (x_root - bnch.x_root))
                y = int(subwin.y + (y_root - bnch.y_root))
                # this works better if it is not self.move_page()
                self.move(subwin.frame, x, y)

            elif bnch.action == 'resize':
                self._resize(bnch, x_root, y_root)

        self._update_area_size()
        return True

    def tile_pages(self):
        # calculate number of rows and cols, try to maintain a square
        # TODO: take into account the window geometry
        num_widgets = len(self.children)
        rows = int(round(math.sqrt(num_widgets)))
        cols = rows
        if rows**2 < num_widgets:
            cols += 1

        # find out how big each window should be
        rect = self.get_allocation()
        width, height = rect.width, rect.height
        wd, ht = width // cols, height // rows

        # and move and resize them into place
        for i in range(0, rows):
            for j in range(0, cols):
                index = i * cols + j
                if index < num_widgets:
                    subwin = self.children[index]

                    self.resize_page(subwin, wd, ht)

                    x, y = j * wd, i * ht
                    self.move_page(subwin, x, y)

                    subwin.raise_()

        self._update_area_size()

    def cascade_pages(self):
        x, y = 0, 0
        for subwin in self.children:
            self.move_page(subwin, x, y)
            subwin.raise_()
            x += self.cascade_offset
            y += self.cascade_offset

        self._update_area_size()

    def use_tabs(self, tf):
        pass

    def move_page(self, subwin, x, y):
        self.move(subwin.frame, x, y)
        subwin.x, subwin.y = x, y

    def resize_page(self, subwin, wd, ht):
        subwin.frame.set_size_request(wd, ht)
        subwin.width, subwin.height = wd, ht

    def maximize_page(self, subwin):
        rect = self.get_allocation()
        wd, ht = rect.width, rect.height

        subwin.raise_()
        self.resize_page(subwin, wd, ht)
        self.move_page(subwin, 0, 0)

        self._update_area_size()

    def minimize_page(self, subwin):
        rect = self.get_allocation()
        height = rect.height

        rect = subwin.frame.get_allocation()
        x = rect.x

        rect = subwin.label.get_allocation()
        ht = rect.height

        self.resize_page(subwin, self.minimized_width, ht)
        self.move_page(subwin, x, height - ht)
        subwin.lower()

        self._update_area_size()

    def close_page(self, subwin):
        self._update_area_size()


class Splitter(Gtk.Layout):
    """
    Splitter type widget for Gtk.
    """
    def __init__(self, orientation='horizontal', thumb_px=8):
        Gtk.Layout.__init__(self)

        self.orientation = orientation
        self._sizes = []
        self._dims = (0, 0)
        self.children = []
        self.thumbs = []
        self.thumb_px = thumb_px
        self.thumb_aspect = 3.25
        self.kbdmouse_mask = 0

        mask = self.get_events()
        self.set_events(mask |
                        Gdk.EventMask.ENTER_NOTIFY_MASK |
                        Gdk.EventMask.LEAVE_NOTIFY_MASK
                        )

        self.connect("size-allocate", self._size_allocate_cb)
        modify_bg(self, "gray50")

    def add_widget(self, widget):
        rect = self.get_allocation()
        wd, ht = rect.width, rect.height

        self.children.append(widget)

        if len(self.children) == 1:
            widget.set_size_request(wd, ht)
            self.put(widget, 0, 0)
            sizes = self._sizes
            if len(sizes) == 0:
                pos = wd if self.orientation == 'horizontal' else ht
                sizes = [pos]
            self.set_sizes(sizes)

        else:
            if self.orientation == 'horizontal':
                thumbfile, _w, _h = ('vdots.png', self.thumb_px,
                                     int(self.thumb_px * self.thumb_aspect))
            else:
                thumbfile, _w, _h = ('hdots.png',
                                     int(self.thumb_px * self.thumb_aspect),
                                     self.thumb_px)
            iconfile = os.path.join(icondir, thumbfile)
            pixbuf = pixbuf_new_from_file_at_size(iconfile, _w, _h)
            image = Gtk.Image.new_from_pixbuf(pixbuf)
            thumb = Gtk.EventBox()
            thumb.set_visible_window(True)
            thumb.add(image)
            modify_bg(thumb, "gray90")

            i = len(self.thumbs)
            self.thumbs.append(thumb)
            thumb.connect("button_press_event", self._start_resize_cb, i)
            thumb.connect("button_release_event", self._stop_resize_cb, i)
            thumb.connect("motion_notify_event", self._do_resize_cb, i)
            thumb.connect("enter_notify_event", self._thumb_enter_cb)
            thumb.connect("leave_notify_event", self._thumb_leave_cb)

            self.put(thumb, 0, 0)
            self.put(widget, 0, 0)

            sizes = self._sizes
            if len(sizes) < len(self.children):
                pos = wd if self.orientation == 'horizontal' else ht
                sizes.append(pos)
            self.set_sizes(sizes)

        self.show_all()

    def _thumb_enter_cb(self, widget, event):
        # change the cursor to a resize one when we enter the thumb area
        display = self.get_display()
        cur_name = ('ew-resize' if self.orientation == 'horizontal'
                    else 'ns-resize')
        cursor = Gdk.Cursor.new_from_name(display, cur_name)
        win = self.get_window()
        if win is not None:
            win.set_cursor(cursor)

    def _thumb_leave_cb(self, widget, event):
        # change the cursor to the normal one when we leave the thumb area
        display = self.get_display()
        cursor = Gdk.Cursor.new_from_name(display, 'default')
        win = self.get_window()
        if win is not None:
            win.set_cursor(cursor)

    def get_sizes(self):
        return list(self._sizes)

    def set_sizes(self, sizes):
        sizes = list(sizes)
        ## if sizes == self._sizes:
        ##     return
        if self.get_realized():
            rect = self.get_allocation()
            wd, ht = rect.width, rect.height
        else:
            min_req, nat_req = self.get_preferred_size()
            wd, ht = nat_req.width, nat_req.height

        x, y = 0, 0
        # calc space needed by all necessary thumbs
        remaining_thumb_space = max(0, len(self.children) - 1) * self.thumb_px
        new_sizes = []
        thumbs, widgets = [], []
        for num, child in enumerate(self.children):
            off = sizes[num]

            if self.orientation == 'horizontal':
                if num == 0:
                    widgets.append((child, 0, 0, off, ht))
                    new_sizes.append(off)
                    x += off

                else:
                    thumb = self.thumbs[num - 1]
                    thumbs.append((thumb, x, y, self.thumb_px, ht))
                    x += self.thumb_px
                    remaining_thumb_space -= self.thumb_px

                    rest = max(0, wd - (x + remaining_thumb_space))
                    if num < len(self.children) - 1:
                        rest = min(off, rest)
                    widgets.append((child, x, y, rest, ht))
                    new_sizes.append(rest)
                    x += rest

            else:
                if num == 0:
                    widgets.append((child, 0, 0, wd, off))
                    new_sizes.append(off)
                    y += off

                else:
                    thumb = self.thumbs[num - 1]
                    thumbs.append((thumb, x, y, wd, self.thumb_px))
                    y += self.thumb_px
                    remaining_thumb_space -= self.thumb_px

                    rest = max(0, ht - (y + remaining_thumb_space))
                    if num < len(self.children) - 1:
                        rest = min(off, rest)
                    widgets.append((child, x, y, wd, rest))
                    new_sizes.append(rest)
                    y += rest

        self._sizes = new_sizes
        assert len(self._sizes) == len(self.children)

        for child, x, y, wd, ht in widgets:
            self._move_resize_child(child, x, y, wd, ht)
        for thumb, x, y, wd, ht in thumbs:
            self._move_resize_child(thumb, x, y, wd, ht)

    def remove(self, child):
        if child not in self.children:
            raise ValueError("widget is not one of our children")
        idx = self.children.index(child)
        if len(self.children) > 1:
            if idx > 0:
                # not first child
                thumb = self.thumbs.pop(idx - 1)
            else:
                thumb = self.thumbs.pop(0)

            super(Splitter, self).remove(thumb)

        self._sizes.pop(idx)
        self.children.remove(child)
        super(Splitter, self).remove(child)

        self.set_sizes(self._sizes)

    def _move_resize_child(self, child, x, y, wd, ht):
        rect = child.get_allocation()
        modified = False

        if (rect.x, rect.y) != (x, y):
            modified = True
            self.move(child, x, y)

        if (rect.width, rect.height) != (wd, ht):
            modified = True
            child.set_size_request(wd, ht)

            alloc = Gdk.Rectangle()
            alloc.x, alloc.y, alloc.width, alloc.height = x, y, wd, ht
            child.size_allocate(alloc)

            #child.set_clip(alloc)

            win = child.get_window()
            if win is not None:
                win.invalidate_rect(None, True)
                win.resize(wd, ht)

        if modified:
            # don't think this should be necessary, but just in case
            child.queue_draw()
            #child.queue_resize()
            child.queue_allocate()

    def _calc_size(self, i, pos):
        sizes = list(self._sizes)
        n = sum([sizes[j] for j in range(0, i)])
        n += max(0, i - 1) * self.thumb_px
        return max(0, pos - n)

    def _start_resize_cb(self, widget, event, i):
        x_root, y_root = event.x_root, event.y_root
        x, y = widget.translate_coordinates(self, event.x, event.y)

        pos = x if self.orientation == 'horizontal' else y
        sizes = list(self._sizes)
        sizes[i] = self._calc_size(i, pos)
        self.set_sizes(sizes)
        return True

    def _stop_resize_cb(self, widget, event, i):
        x_root, y_root = event.x_root, event.y_root
        x, y = widget.translate_coordinates(self, event.x, event.y)

        pos = x if self.orientation == 'horizontal' else y
        sizes = list(self._sizes)
        sizes[i] = self._calc_size(i, pos)
        self.set_sizes(sizes)
        return True

    def _do_resize_cb(self, widget, event, i):
        button = self.kbdmouse_mask
        x_root, y_root, state = event.x_root, event.y_root, event.state
        x, y = widget.translate_coordinates(self, event.x, event.y)

        if state & Gdk.ModifierType.BUTTON1_MASK:
            button |= 0x1
        elif state & Gdk.ModifierType.BUTTON2_MASK:
            button |= 0x2
        elif state & Gdk.ModifierType.BUTTON3_MASK:
            button |= 0x4

        if button == 0x1:
            pos = x if self.orientation == 'horizontal' else y
            sizes = list(self._sizes)
            sizes[i] = self._calc_size(i, pos)
            self.set_sizes(sizes)
        return True

    def _size_allocate_cb(self, widget, rect):
        x, y, wd, ht = rect.x, rect.y, rect.width, rect.height

        dims = (wd, ht)
        if dims == self._dims:
            return
        super(Splitter, self).set_size(wd, ht)

        self._dims = dims

        self.set_sizes(self._sizes)
        return True


class Dial(Gtk.DrawingArea):

    __gtype_name__ = "Dial"

    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE,
                          (GObject.TYPE_FLOAT,)),
    }

    def __init__(self):
        Gtk.DrawingArea.__init__(self)
        self.set_can_focus(True)
        self.dims = np.array((0, 0))
        self.center = np.array((0.0, 0.0))
        self.bg = (0.94, 0.94, 0.94)
        self.fg = (0.4, 0.4, 0.4)
        self.knob_fg = (1.0, 1.0, 1.0)
        self.knob_fill = (0.2, 0.2, 0.2)
        self.focus_fg = (0.2, 0.6, 0.9)
        self.fontname = 'Sans Serif'
        self.fontsize = 10.0
        self._has_focus = False
        self.surface = None

        # draw labels
        self.draw_scale = True
        # how to rotate the labels
        self.label_style = 1
        self.values = []
        self.draw_value_pos = 0

        self.value = 0.0
        self.value_text = str(self.value)

        # internal state
        self._dragging = False
        self.tracking = False
        self.wrap = False
        self.angle = 0.0
        self.ang_offset = 0.0
        self.ang_invert = False
        self.turn_delta = 6.0
        self.min_ang_deg = 0.0
        self.max_ang_deg = 360.0

        self.connect("draw", self.draw_event)
        self.connect("configure-event", self.configure_event)
        self.set_app_paintable(True)
        # prevents extra redraws, because we manually redraw on a size
        # change
        self.set_redraw_on_allocate(False)

        self.connect('button-press-event', self.button_press_event)
        self.connect('button-release-event', self.button_release_event)
        self.connect('motion-notify-event', self.motion_notify_event)
        self.connect('scroll-event', self.scroll_event)
        self.connect('focus_in_event', self.focus_event, True)
        self.connect('focus_out_event', self.focus_event, False)
        mask = self.get_events()
        self.set_events(mask |
                        Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.FOCUS_CHANGE_MASK |
                        Gdk.EventMask.EXPOSURE_MASK)

    def button_press_event(self, widget, event):
        if event.button == 1:
            self._dragging = True
            self._calc_action(event.x, event.y)
            return True

    def button_release_event(self, widget, event):
        self._dragging = False
        self._calc_action(event.x, event.y)
        return True

    def motion_notify_event(self, widget, event):
        # Are we holding down the left mouse button?
        if not self._dragging:
            return False

        self._calc_action(event.x, event.y)
        return True

    def scroll_event(self, widget, event):
        degrees, direction = get_scroll_info(event)
        if direction < 180.0:
            self.turn_ccw()
        else:
            self.turn_cw()

        self.draw()
        return True

    def focus_event(self, widget, event, tf):
        self._has_focus = tf
        self.draw()
        return True

    def _calc_action(self, x, y):
        ang_deg = np.degrees(np.arctan2(x - self.center[0],
                                        y - self.center[1]) + np.pi * 1.5)
        ang_deg = self.normalize_angle(ang_deg + self.ang_offset)
        if self.ang_invert:
            ang_deg = 360.0 - ang_deg

        self.angle_action(x, y, ang_deg)

    def draw(self):
        if self.surface is None:
            return
        cr = cairo.Context(self.surface)

        cr.select_font_face(self.fontname)
        cr.set_font_size(self.fontsize)

        # fill background
        wd, ht = self.dims
        cr.rectangle(0, 0, wd, ht)
        r, g, b = self.bg
        cr.set_source_rgba(r, g, b)
        cr.fill()

        r, g, b = self.fg
        cr.set_source_rgba(r, g, b)
        cr.set_line_width(2.0)

        cr.save()
        cx, cy = self.center
        cr.translate(cx, cy)
        cr.move_to(0, 0)

        # draw circle
        cradius = min(cx, cy)
        cradius *= 0.66
        cr.arc(0, 0, cradius, 0, 2 * np.pi)
        cr.fill()

        if self._has_focus:
            r, g, b = self.focus_fg
        else:
            r, g, b = (0.0, 0.0, 0.0)
        cr.set_source_rgba(r, g, b)
        cr.new_path()
        cr.set_line_width(2)
        cr.arc(0, 0, cradius, 0, 2 * np.pi)
        cr.stroke()
        cr.new_path()
        cr.set_line_width(1)

        if self.draw_scale:
            cr.new_path()
            cr.set_source_rgba(0.0, 0.0, 0.0)
            for tup in self.values:
                if len(tup) == 3:
                    label, value, theta = tup
                else:
                    value, theta = tup
                    label = str(value)
                if self.ang_invert:
                    theta = 360.0 - theta
                theta_pos = self.normalize_angle(theta + 90.0 - self.ang_offset)
                theta_rad = np.radians(theta_pos)
                a, b, wd, ht, i, j = cr.text_extents(label)
                crad2 = cradius + ht / 2.0
                if self.label_style == 0:
                    crad2 += wd

                # draw small filled dot as position marker
                cx, cy = (np.sin(theta_rad) * cradius,
                          np.cos(theta_rad) * cradius)
                cr.move_to(cx, cy)
                r, g, b = self.knob_fill
                cr.set_source_rgba(r, g, b)
                cr.arc(cx, cy, 2, 0, 2 * np.pi)
                cr.stroke_preserve()
                cr.fill()

                # draw label
                cx, cy = np.sin(theta_rad) * crad2, np.cos(theta_rad) * crad2
                cr.move_to(cx, cy)

                text_rad = np.arctan2(cx, cy)
                if self.label_style == 0:
                    text_rad = 0.0
                elif self.label_style == 1:
                    text_rad += np.pi
                elif self.label_style == 2:
                    text_rad += - np.pi / 2
                cr.save()
                cr.translate(cx, cy)
                cr.rotate(-text_rad)
                if self.label_style == 1:
                    cr.move_to(-wd / 2, 0)
                cr.show_text(label)
                #cr.rotate(text_rad)
                cr.restore()

            cr.new_path()

        cr.move_to(0, 0)
        theta = self.angle
        if self.ang_invert:
            theta = 360.0 - theta
        theta = self.normalize_angle(theta - self.ang_offset)

        cr.rotate(-np.radians(theta))

        # draw knob (pointer)
        r, g, b = self.knob_fg
        cr.set_source_rgba(r, g, b)
        crad2 = cradius
        cr.new_path()
        x1, y1, x2, y2 = -crad2, 0, crad2, 0
        cx1, cy1, cx2, cy2 = self.calc_vertexes(x1, y1, x2, y2,
                                                arrow_length=crad2)
        cr.move_to(x2, y2)
        cr.line_to(cx1, cy1)
        #cr.line_to(0, 0)
        cr.line_to(cx2, cy2)
        cr.close_path()
        r, g, b = self.knob_fg
        cr.set_source_rgba(r, g, b)
        cr.stroke_preserve()
        r, g, b = self.knob_fill
        cr.set_source_rgba(r, g, b)
        cr.fill()
        cr.move_to(0, 0)
        cr.arc(0, 0, abs(cx1 + cx2) * 2.1, 0, 2 * np.pi)
        cr.stroke_preserve()
        cr.fill()

        text = self.value_text
        if self.draw_value_pos == 1:
            r, g, b = self.bg
            cr.set_source_rgba(r, g, b)
            cr.move_to(0, 0)
            cr.show_text(text)

        cr.restore()

        if self.draw_value_pos == 2:
            a, b, wd, ht, i, j = cr.text_extents(text)
            r, g, b = self.fg
            cr.set_source_rgba(r, g, b)
            x, y = self.center
            cr.move_to(x - wd / 2, (y - cradius) * 0.5 + ht)
            cr.show_text(text)

        cr.move_to(0, 0)

        self.update_widget()

    def normalize_angle(self, ang_deg):
        ang_deg = np.fmod(ang_deg + 360.0, 360.0)
        return ang_deg

    def finalize_angle(self, ang_deg):
        self.angle = ang_deg
        self.draw()

    def get_angle(self):
        return self.angle

    def set_labels(self, val_ang_pairs):
        self.values = val_ang_pairs

        self.draw()

    def set_tracking(self, tf):
        self.tracking = tf

    def configure_event(self, widget, event):
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height

        self.dims = np.array((width, height))
        self.center = np.array((width / 2, height / 2))

        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)

        self.draw()
        return True

    def update_widget(self):
        if self.surface is None:
            # window is not mapped/configured yet
            return

        win = self.get_window()
        if win is not None and self.surface is not None:
            wd, ht = self.dims

            self.queue_draw_area(0, 0, wd, ht)

    def draw_event(self, widget, cr):
        # redraw the screen from backing surface
        cr.set_source_surface(self.surface, 0, 0)

        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def calc_vertexes(self, start_cx, start_cy, end_cx, end_cy,
                      arrow_length=10, arrow_degrees=0.35):

        angle = np.arctan2(end_cy - start_cy, end_cx - start_cx) + np.pi

        cx1 = end_cx + arrow_length * np.cos(angle - arrow_degrees)
        cy1 = end_cy + arrow_length * np.sin(angle - arrow_degrees)
        cx2 = end_cx + arrow_length * np.cos(angle + arrow_degrees)
        cy2 = end_cy + arrow_length * np.sin(angle + arrow_degrees)

        return (cx1, cy1, cx2, cy2)

    def angle_action(self, x, y, ang_deg):
        """Subclass overrides to provide custom behavior"""
        self._set_value(ang_deg)

    def turn_ccw(self):
        """Subclass overrides to provide custom behavior"""
        self._set_value(self.angle + self.turn_delta)

    def turn_cw(self):
        """Subclass overrides to provide custom behavior"""
        self._set_value(self.angle - self.turn_delta)

    def _set_value(self, ang_deg):
        """Subclass overrides to provide custom behavior"""
        ang_deg = self.normalize_angle(ang_deg)
        ang_deg = np.clip(ang_deg, self.min_ang_deg, self.max_ang_deg)
        self.value = ang_deg
        self.finalize_angle(ang_deg)

        if not self._dragging or self.tracking:
            self.emit("value-changed", self.value)

    def set_value(self, ang_deg):
        """Subclass overrides to provide custom behavior"""
        self._set_value(ang_deg)

    def get_value(self):
        """Subclass overrides to provide custom behavior"""
        return self.value


class ValueDial(Dial):

    __gtype_name__ = "ValueDial"

    def __init__(self):
        Dial.__init__(self)

        # for drawing value
        self.label_style = 1
        self.draw_value_pos = 2

        # setup axis orientation to match value
        self.ang_offset = 140.0
        self.ang_invert = True
        self.min_ang_deg = 0.0
        self.max_ang_deg = 260.0
        self.set_labels([("min", 0.0), ("max", 260.0)])

        self.min_val = 0.0
        self.max_val = 0.0
        self.inc_val = 0.0

    def angle_action(self, x, y, ang_deg):
        value = self._angle_to_value(ang_deg)
        self._set_value(value)

    def turn_ccw(self):
        ang_deg = np.clip(self.angle + self.turn_delta,
                          0.0, self.max_ang_deg)
        value = self._angle_to_value(ang_deg)
        self._set_value(value)

    def turn_cw(self):
        ang_deg = np.clip(self.angle - self.turn_delta,
                          0.0, self.max_ang_deg)
        value = self._angle_to_value(ang_deg)
        self._set_value(value)

    def _set_value(self, value):
        if value < self.min_val or value > self.max_val:
            raise ValueError("value '{}' is out of range".format(value))

        self.value = value
        self.value_text = "%.2f" % self.value

        ang_deg = self._value_to_angle(value)
        self.finalize_angle(ang_deg)

        if not self._dragging or self.tracking:
            self.emit("value-changed", self.value)

    def get_value(self):
        return self.value

    def _value_to_angle(self, value):
        # make angle match value
        rng = self.max_val - self.min_val
        pct = (value - self.min_val) / rng
        ang_deg = pct * self.max_ang_deg
        ang_deg = np.clip(ang_deg, 0.0, self.max_ang_deg)
        return ang_deg

    def _angle_to_value(self, ang_deg):
        # make value match angle
        pct = ang_deg / self.max_ang_deg
        rng = self.max_val - self.min_val
        value = self.min_val + pct * rng
        value = np.clip(value, self.min_val, self.max_val)
        return value

    def set_limits(self, min_val, max_val, inc_val):
        self.min_val = min_val
        self.max_val = max_val
        self.inc_val = inc_val

        pct = inc_val / (max_val - min_val)
        self.turn_delta = pct * self.max_ang_deg


class IndexDial(Dial):

    __gtype_name__ = "IndexDial"

    def __init__(self):
        Dial.__init__(self)

        self.idx = 0
        self.label_style = 1

    def angle_action(self, x, y, ang_deg):
        idx = self.best_index(ang_deg)
        self.set_index(idx)

    def turn_ccw(self):
        idx = self.idx - 1
        if idx < 0:
            if self.wrap:
                self.set_index(len(self.values) - 1)
        else:
            self.set_index(idx)

    def turn_cw(self):
        idx = self.idx + 1
        if idx >= len(self.values):
            if self.wrap:
                self.set_index(0)
        else:
            self.set_index(idx)

    def set_index(self, idx):
        idx = int(idx)
        if idx < 0 or idx >= len(self.values):
            raise ValueError("index '{}' is outside range 0-{}".format(idx,
                                                                       len(self.values)))
        self.idx = idx
        tup = self.values[idx]
        self.value = tup[0] if len(tup) == 2 else tup[1]
        self.value_text = str(self.value)

        self.angle = tup[-1]
        self.draw()

        if not self._dragging or self.tracking:
            self.emit("value-changed", idx)

    def get_index(self):
        return self.idx

    def get_value(self):
        return self.value

    def best_index(self, ang_deg):
        # find the index that is closest to the angle ang_deg
        angles = np.array([tup[-1] for tup in self.values])
        ang_deg = self.normalize_angle(ang_deg)
        angles = np.abs(angles - ang_deg)
        idx = np.argmin(angles)
        return idx


class FileSelection(object):

    def __init__(self, parent_w, action=Gtk.FileChooserAction.OPEN,
                 title="Select a file", all_at_once=False):
        # TODO: deprecate the functionality when all_at_once == False
        # and make the default to be True
        self.parent = parent_w
        self.all_at_once = all_at_once
        # Create a new file selection widget
        self.filew = Gtk.FileChooserDialog(title=title, action=action)
        self.filew.connect("destroy", self.close)
        if action == Gtk.FileChooserAction.SAVE:
            self.filew.add_buttons(Gtk.STOCK_SAVE, 1, Gtk.STOCK_CANCEL, 0)
        else:
            self.filew.add_buttons(Gtk.STOCK_OPEN, 1, Gtk.STOCK_CANCEL, 0)
        self.filew.set_default_response(1)
        self.filew.set_select_multiple(True)
        self.filew.connect("response", self.file_ok_sel)

        # Connect the cancel_button to destroy the widget
        #self.filew.cancel_button.connect("clicked", self.close)

    def popup(self, title, callfn, initialdir=None, filename=None):
        """Let user select and load file."""
        self.cb = callfn
        self.filew.set_title(title)
        if initialdir:
            self.filew.set_current_folder(initialdir)

        if filename:
            #self.filew.set_filename(filename)
            self.filew.set_current_name(filename)

        self.filew.show()
        # default size can be enormous
        self.filew.resize(800, 600)

    # Get the selected filename
    def file_ok_sel(self, w, rsp):
        self.close(w)
        if rsp == 0:
            return

        paths = self.filew.get_filenames()
        if self.all_at_once:
            self.cb(paths)
        else:
            for path in paths:
                self.cb(path)

    def close(self, widget):
        self.filew.hide()


class DirectorySelection(FileSelection):
    """Handle directory selection dialog."""
    def __init__(self, parent_w):
        super(DirectorySelection, self).__init__(
            parent_w, action=Gtk.FileChooserAction.SELECT_FOLDER,
            title="Select a directory")

    def popup(self, title, callfn, initialdir=None):
        """Let user select a directory."""
        super(DirectorySelection, self).popup(title, callfn, initialdir)


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self._timer = None
        self.start_time = 0.0
        self.deadline = 0.0

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def start(self, duration=None):
        """Start the timer.  If `duration` is not None, it should
        specify the time to expiration in seconds.
        """
        if duration is None:
            duration = self.duration

        self.set(duration)

    def set(self, duration):

        self.stop()

        self.start_time = time.time()
        self.deadline = self.start_time + duration
        # Gtk timer set in milliseconds
        time_ms = int(duration * 1000.0)
        self._timer = GObject.timeout_add(time_ms, self._redirect_cb)

    def _redirect_cb(self):
        self._timer = None
        self.make_callback('expired')

    def is_set(self):
        return self._timer is not None

    def cond_set(self, time_sec):
        if not self.is_set():
            # TODO: probably a race condition here
            self.set(time_sec)

    def elapsed_time(self):
        return time.time() - self.start_time

    def time_left(self):
        return max(0.0, self.deadline - time.time())

    def get_deadline(self):
        return self.deadline

    def stop(self):
        try:
            if self._timer is not None:
                GObject.source_remove(self._timer)
        except Exception:
            pass
        self._timer = None

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel


def combo_box_new_text():
    liststore = Gtk.ListStore(GObject.TYPE_STRING)
    combobox = ComboBox()
    combobox.set_model(liststore)
    cell = Gtk.CellRendererText()
    combobox.pack_start(cell, True)
    combobox.add_attribute(cell, 'text', 0)
    return combobox


def get_scroll_info(event):
    """
    Returns the (degrees, direction) of a scroll motion Gtk event.
    """
    valid, dx, dy = event.get_scroll_deltas()
    if valid:
        # we have a trackpad or some device that reports pixel deltas
        delta = math.sqrt(dx ** 2 + dy ** 2)
        if dy < 0:
            delta = -delta

        ang_rad = math.atan2(dy, dx)
        direction = math.degrees(ang_rad) - 90.0
        direction = math.fmod(direction + 360.0, 360.0)

        # TODO: is this accurate?--NOT TESTED
        num_degrees = delta / 8.0

    else:
        valid, direction = event.get_scroll_direction()
        if valid:
            if event.direction == Gdk.ScrollDirection.UP:
                direction = 0.0
            elif event.direction == Gdk.ScrollDirection.DOWN:
                direction = 180.0
            elif event.direction == Gdk.ScrollDirection.LEFT:
                direction = 270.0
            elif event.direction == Gdk.ScrollDirection.RIGHT:
                direction = 90.0

        else:
            direction = None

        # TODO: does Gtk encode the amount of scroll?
        # 15 deg is standard 1-click turn for a wheel mouse
        num_degrees = 15.0

    return (num_degrees, direction)


def get_icon(iconpath, size=None):
    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24
    pixbuf = pixbuf_new_from_file_at_size(iconpath, wd, ht)
    return pixbuf


def get_font(font_family, point_size):
    font_family = font_asst.resolve_alias(font_family, font_family)
    font = Pango.FontDescription('%s %d' % (font_family, point_size))
    return font


def load_font(font_name, font_file):
    # TODO!
    ## raise ValueError("Loading fonts dynamically is an unimplemented"
    ##                  " feature for gtk3 back end")
    return font_name


def pixbuf_new_from_xpm_data(xpm_data):
    xpm_data = bytes('\n'.join(xpm_data))
    return GdkPixbuf.Pixbuf.new_from_xpm_data(xpm_data)


def pixbuf_new_from_array(data, rgbtype, bpp):
    # NOTE: there is a bug in gtk3 with pixbuf_new_from_array()
    # See: http://stackoverflow.com/questions/24062779/how-to-correctly-covert-3d-array-into-continguous-rgb-bytes/24070152#24070152
    #return GdkPixbuf.Pixbuf.new_from_array(data, rgbtype, bpp)

    height, width, depth = data.shape
    pixl = GdkPixbuf.PixbufLoader.new_with_type('pnm')
    # P6 is the magic number of PNM format,
    # and 255 is the max color allowed
    pixl.write((b"P6 %d %d 255 " % (width, height)) + data.tobytes(order='C'))
    pix = pixl.get_pixbuf()
    pixl.close()
    return pix


def pixbuf_new_from_data(rgb_buf, rgbtype, hasAlpha, bpp, dawd, daht, stride):
    return GdkPixbuf.Pixbuf.new_from_data(rgb_buf, rgbtype, hasAlpha, bpp,
                                          dawd, daht, stride, None, None)


def pixbuf_new_from_file_at_size(foldericon, width, height):
    return GdkPixbuf.Pixbuf.new_from_file_at_size(foldericon, width, height)


def pixbuf_new_from_file(file_path):
    return GdkPixbuf.Pixbuf.new_from_file(file_path)


def make_cursor(widget, iconpath, x, y):
    image = Gtk.Image()
    image.set_from_file(iconpath)
    pixbuf = image.get_pixbuf()
    screen = widget.get_screen()
    display = screen.get_display()
    return Gdk.Cursor(display, pixbuf, x, y)


def modify_bg(widget, color):
    context = widget.get_style_context()
    if color is not None:
        context.add_class("custom_bg")
        css_data = "*.custom_bg { background-image: none; background-color: %s; }" % (color)
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(css_data.encode())
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    else:
        context.remove_class("custom_bg")


def set_default_style():
    style_provider = Gtk.CssProvider()

    module_home = os.path.split(sys.modules[__name__].__file__)[0]
    gtk_css = os.path.join(module_home, 'gtk_css')
    with open(gtk_css, 'rb') as css_f:
        css_data = css_f.read()

    try:
        style_provider.load_from_data(css_data)

        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    except Exception:
        pass

# END
