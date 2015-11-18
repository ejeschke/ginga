#
# GtkHelp.py -- customized Gtk widgets
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function

from ginga.gtkw import gtksel
from ginga.misc import Bunch

import gtk
import gobject
import pango


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


class TopLevel(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)

class CheckButton(WidgetMask, gtk.CheckButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.CheckButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(CheckButton, self).set_active(newval)

class ToggleButton(WidgetMask, gtk.ToggleButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.ToggleButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(ToggleButton, self).set_active(newval)

    def toggle(self):
        oldval = self.get_active()
        newval = not oldval
        super(ToggleButton, self).set_active(newval)


class RadioButton(WidgetMask, gtk.RadioButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.RadioButton.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(RadioButton, self).set_active(newval)

    def toggle(self):
        oldval = self.get_active()
        newval = not oldval
        super(RadioButton, self).set_active(newval)


class CheckMenuItem(WidgetMask, gtk.CheckMenuItem):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.CheckMenuItem.__init__(self, *args, **kwdargs)

    def set_active(self, newval):
        oldval = self.get_active()
        if oldval != newval:
            self.change()

        super(CheckMenuItem, self).set_active(newval)


class SpinButton(WidgetMask, gtk.SpinButton):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.SpinButton.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(SpinButton, self).set_value(newval)


class HScale(WidgetMask, gtk.HScale):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.HScale.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(HScale, self).set_value(newval)

class VScale(WidgetMask, gtk.VScale):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.VScale.__init__(self, *args, **kwdargs)

    def set_value(self, newval):
        oldval = self.get_value()
        if oldval != newval:
            self.change()

        super(VScale, self).set_value(newval)


class ComboBoxMixin(object):

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
        model.insert(j+1, tup)

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

class ComboBox(WidgetMask, gtk.ComboBox, ComboBoxMixin):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.ComboBox.__init__(self, *args, **kwdargs)


class ComboBoxEntry(WidgetMask, gtk.ComboBoxEntry, ComboBoxMixin):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        gtk.ComboBoxEntry.__init__(self, *args, **kwdargs)


class Notebook(gtk.Notebook):
    def set_group_id(self, id):
        if not gtksel.have_gtk3:
            super(Notebook, self).set_group_id(id)
        else:
            super(Notebook, self).set_group_name(str(id))


class MultiDragDropTreeView(gtk.TreeView):
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
        if (target
           and event.type == gtk.gdk.BUTTON_PRESS
           and not (event.state & (gtk.gdk.CONTROL_MASK|gtk.gdk.SHIFT_MASK))
           and self.get_selection().path_is_selected(target[0])):
            # disable selection
            self.get_selection().set_select_function(lambda *ignore: False)
            self.defer_select = target[0]

    def on_button_release(self, widget, event):
        # re-enable selection
        self.get_selection().set_select_function(lambda *ignore: True)

        target = self.get_path_at_pos(int(event.x), int(event.y))
        if (self.defer_select and target
           and self.defer_select == target[0]
           and not (event.x==0 and event.y==0)): # certain drag and drop
            self.set_cursor(target[0], target[1], False)

        self.defer_select=False


class MDIWorkspace(gtk.Layout):
    """
    This is a work in progress!
    """
    def __init__(self):
        super(MDIWorkspace, self).__init__()

        self.children = []
        self.selected_child = None
        self.kbdmouse_mask = 0

        self.bg_rgb = (0.5, 0.5, 0.5)
        self._last_win_x = None
        self._last_win_y = None

        self.connect("configure-event", self.configure_event)
        if not gtksel.have_gtk3:
            self.connect("expose_event", self.expose_event)
        ## else:
        ##     self.connect("draw", self.draw_event)
        self.connect("motion_notify_event", self.motion_notify_event)
        self.connect("button_press_event", self.button_press_event)
        self.connect("button_release_event", self.button_release_event)
        mask = self.get_events()
        self.set_events(mask
                        | gtk.gdk.ENTER_NOTIFY_MASK
                        | gtk.gdk.LEAVE_NOTIFY_MASK
                        | gtk.gdk.FOCUS_CHANGE_MASK
                        | gtk.gdk.STRUCTURE_MASK
                        | gtk.gdk.BUTTON_PRESS_MASK
                        | gtk.gdk.BUTTON_RELEASE_MASK
                        | gtk.gdk.KEY_PRESS_MASK
                        | gtk.gdk.KEY_RELEASE_MASK
                        | gtk.gdk.POINTER_MOTION_MASK
                        #| gtk.gdk.POINTER_MOTION_HINT_MASK
                        | gtk.gdk.SCROLL_MASK)

    def expose_event(self, widget, event):
        x , y, width, height = event.area
        win = widget.get_window()
        cr = win.cairo_create()

        # set clip area for exposed region
        cr.rectangle(x, y, width, height)
        cr.clip()

        cr.set_source_rgb(*self.bg_rgb)
        cr.paint()
        return True

    def configure_event(self, widget, event):
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height

        # This is a workaround for a strange bug in Gtk 3
        # where we get multiple configure callbacks even though
        # the size hasn't changed.  We avoid creating a new surface
        # if there is an old surface with the exact same size.
        # This prevents some flickering of the display on focus events.
        wwd, wht = self.get_window_size()
        if (wwd == width) and (wht == height):
            return True

        win = widget.get_window()
        cr = win.cairo_create()

        # set clip area for exposed region
        cr.rectangle(0, 0, width, height)
        #cr.clip()

        cr.set_source_rgb(*self.bg_rgb)
        cr.paint()
        #self.configure(width, height)
        return True

    def append_page(self, widget, label):
        vbox = gtk.VBox()
        evbox = gtk.EventBox()
        evbox.add(label)
        evbox.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("yellow"))
        evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("skyblue"))
        vbox.pack_start(evbox, fill=False, expand=False)
        vbox.pack_start(widget, fill=True, expand=True)

        fr = gtk.Frame()
        fr.set_border_width(10)
        fr.set_shadow_type(gtk.SHADOW_ETCHED_OUT)
        fr.add(vbox)
        #fr.set_resize_mode(gtk.RESIZE_IMMEDIATE)
        fr.show_all()

        evbox.connect("button_press_event", self.select_child_cb, fr)

        bnch = Bunch.Bunch(widget=widget, window=fr)
        self.children.append(bnch)

        self.put(fr, 10, 10)

    def set_tab_reorderable(self, w, tf):
        pass
    def set_tab_detachable(self, w, tf):
        pass

    def get_tab_label(self, w):
        return None

    def page_num(self, widget):
        idx = 0
        for bnch in self.children:
            if bnch.widget == widget:
                return idx
            idx += 1
        return -1

    def set_current_page(self, idx):
        bnch = self.children[idx]
        window = bnch.window
        window.show()

    def remove_page(self, idx):
        bnch = self.children[idx]
        window = bnch.window
        #self.remove(window)

    def select_child_cb(self, layout, event, widget):
        ex = event.x_root; ey = event.y_root
        x, y, width, height = widget.get_allocation()
        win = widget.get_window()
        if win is None:
            return False
        x, y = win.get_position()
        #dx, dy = int(ex - x), int(ey - y)
        dx, dy = ex, ey
        self.selected_child = Bunch.Bunch(widget=widget,
                                          cr = self.setup_cr(self.bin_window),
                                          x_origin=x, y_origin=y,
                                          dx=dx, dy=dy, wd=width, ht=height)
        return False

    def button_press_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x; y = event.y
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        return True

    def setup_cr(self, drawable):
        cr = drawable.cairo_create()
        cr.set_line_width(2)
        cr.set_dash([ 3.0, 4.0, 6.0, 4.0], 5.0)
        return cr

    def button_release_event(self, widget, event):
        # event.button, event.x, event.y
        x = event.x_root; y = event.y_root
        button = self.kbdmouse_mask
        if event.button != 0:
            button |= 0x1 << (event.button - 1)
        if self.selected_child is not None:
            bnch = self.selected_child
            x = int(bnch.x_origin + (x - bnch.dx))
            y = int(bnch.x_origin + (y - bnch.dy))
            self.move(self.selected_child.widget, x, y)
            self.selected_child = None
        return True

    def motion_notify_event(self, widget, event):
        button = self.kbdmouse_mask
        if event.is_hint:
            return
        else:
            x, y, state = event.x_root, event.y_root, event.state

        if state & gtk.gdk.BUTTON1_MASK:
            button |= 0x1
        elif state & gtk.gdk.BUTTON2_MASK:
            button |= 0x2
        elif state & gtk.gdk.BUTTON3_MASK:
            button |= 0x4

        if (button & 0x1) and (self.selected_child is not None):
            bnch = self.selected_child
            x = int(bnch.x_origin + (x - bnch.dx))
            y = int(bnch.x_origin + (y - bnch.dy))
            self.move(self.selected_child.widget, x, y)

        return True

    def to_next(self):
        pass
    def to_previous(self):
        pass

    def tile_panes(self):
        pass
    def cascade_panes(self):
        pass
    def use_tabs(self, tf):
        pass


class FileSelection(object):

    def __init__(self, parent_w, action=gtk.FILE_CHOOSER_ACTION_OPEN):
        self.parent = parent_w
        # Create a new file selection widget
        self.filew = gtk.FileChooserDialog(title="Select a file",
                                           action=action)
        self.filew.connect("destroy", self.close)
        if action == gtk.FILE_CHOOSER_ACTION_SAVE:
            self.filew.add_buttons(gtk.STOCK_SAVE, 1, gtk.STOCK_CANCEL, 0)
        else:
            self.filew.add_buttons(gtk.STOCK_OPEN, 1, gtk.STOCK_CANCEL, 0)
        self.filew.set_default_response(1)
        self.filew.connect("response", self.file_ok_sel)

        # Connect the cancel_button to destroy the widget
        #self.filew.cancel_button.connect("clicked", self.close)

    def popup(self, title, callfn, initialdir=None,
              filename=None):
        self.cb = callfn
        self.filew.set_title(title)
        if initialdir:
            self.filew.set_current_folder(initialdir)

        if filename:
            #self.filew.set_filename(filename)
            self.filew.set_current_name(filename)

        self.filew.show()

    # Get the selected filename
    def file_ok_sel(self, w, rsp):
        self.close(w)
        if rsp == 0:
            return

        filepath = self.filew.get_filename()
        self.cb(filepath)

    def close(self, widget):
        self.filew.hide()


def get_scroll_info(event):
    """
    Returns the (degrees, direction) of a scroll motion Gtk event.
    """
    direction = None
    if event.direction == gtk.gdk.SCROLL_UP:
        direction = 0.0
    elif event.direction == gtk.gdk.SCROLL_DOWN:
        direction = 180.0
    elif event.direction == gtk.gdk.SCROLL_LEFT:
        direction = 270.0
    elif event.direction == gtk.gdk.SCROLL_RIGHT:
        direction = 90.0

    # TODO: does Gtk encode the amount of scroll?
    # 15 deg is standard 1-click turn for a wheel mouse
    degrees = 15.0

    return (degrees, direction)

def get_icon(iconpath, size=None):
    if size is not None:
        wd, ht = size
    else:
        wd, ht = 24, 24
    pixbuf = gtksel.pixbuf_new_from_file_at_size(iconpath, wd, ht)
    return pixbuf

def get_font(font_family, point_size):
    font = pango.FontDescription('%s %d' % (font_family, point_size))
    return font

#END
