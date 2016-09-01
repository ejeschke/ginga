#
# GtkHelp.py -- customized Gtk3 widgets
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys, os.path

from ginga.misc import Bunch
import ginga.toolkit

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango
import cairo

ginga.toolkit.use('gtk3')


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

class ComboBox(WidgetMask, Gtk.ComboBox, ComboBoxMixin):
    def __init__(self, *args, **kwdargs):
        WidgetMask.__init__(self)
        Gtk.ComboBox.__init__(self, *args, **kwdargs)


## class ComboBoxEntry(WidgetMask, Gtk.ComboBoxEntry, ComboBoxMixin):
##     def __init__(self, *args, **kwdargs):
##         WidgetMask.__init__(self)
##         Gtk.ComboBoxEntry.__init__(self, *args, **kwdargs)


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
        if (target
           and event.type == Gdk.EventType.BUTTON_PRESS
           and not (event.state & (Gdk.ModifierType.CONTROL_MASK | Gdk.ModifierType.SHIFT_MASK))
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


class MDIWidget(Gtk.Layout):
    """
    Multiple Document Interface type widget for Gtk.

    NOTE: *** This is a work in progress! ***
    """
    def __init__(self):
        super(MDIWidget, self).__init__()

        self.children = []
        self.cur_index = -1
        self.selected_child = None
        self.kbdmouse_mask = 0
        self.cascade_offset = 50

        self.connect("motion_notify_event", self.motion_notify_event)
        self.connect("button_press_event", self.button_press_event)
        self.connect("button_release_event", self.button_release_event)
        mask = self.get_events()
        self.set_events(mask
                        | Gdk.EventMask.ENTER_NOTIFY_MASK
                        | Gdk.EventMask.LEAVE_NOTIFY_MASK
                        | Gdk.EventMask.FOCUS_CHANGE_MASK
                        | Gdk.EventMask.STRUCTURE_MASK
                        | Gdk.EventMask.BUTTON_PRESS_MASK
                        | Gdk.EventMask.BUTTON_RELEASE_MASK
                        | Gdk.EventMask.KEY_PRESS_MASK
                        | Gdk.EventMask.KEY_RELEASE_MASK
                        | Gdk.EventMask.POINTER_MOTION_MASK
                        #| Gdk.EventMask.POINTER_MOTION_HINT_MASK
                        | Gdk.EventMask.SCROLL_MASK)

    def append_page(self, widget, label):
        vbox = Gtk.VBox()
        vbox.set_border_width(4)
        evbox = Gtk.EventBox()
        evbox.add(label)
        #evbox.modify_fg(Gtk.StateType.NORMAL, Gdk.color_parse("yellow"))
        evbox.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("skyblue"))
        vbox.pack_start(evbox, False, False, 0)
        vbox.pack_start(widget, True, True, 4)

        frame = Gtk.EventBox()
        frame.set_size_request(300, 300)
        frame.props.visible_window = True
        frame.set_border_width(0)
        frame.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("palegreen1"))

        frame.add(vbox)
        frame.show_all()

        pos = self.get_widget_position(frame)
        if pos is None:
            x, y = 0, 0
        else:
            x, y = pos
        wd, ht = self.get_widget_size(frame)
        subwin = Bunch.Bunch(widget=widget, label=evbox, frame=frame,
                             x=x, y=y, width=wd, height=ht)
        self.children.append(subwin)

        evbox.connect("button_press_event", self.select_child_cb, subwin)
        frame.connect("button_press_event", self.start_resize_cb, subwin)
        self.put(frame, self.cascade_offset, self.cascade_offset)

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
        frame = subwin.frame
        #frame.show()
        self.raise_widget(subwin)
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

    def get_widget_position(self, widget):
        x, y, width, height = widget.get_allocation()
        return x, y

    def get_widget_size(self, widget):
        x, y, width, height = widget.get_allocation()
        return width, height

    def raise_widget(self, subwin):
        frame = subwin.frame
        # Hack to bring widget to the top--no documentation on any other
        # way to accomplish this
        super(MDIWidget, self).remove(frame)
        frame.unparent()
        self.put(frame, subwin.x, subwin.y)

    def select_child_cb(self, layout, event, subwin):
        ex, ey = event.x_root, event.y_root

        x, y = self.get_widget_position(subwin.frame)
        subwin.x, subwin.y = x, y

        # make this the selected widget
        idx = self.page_num(subwin.widget)
        if idx >= 0:
            self.set_current_page(idx)

        self.selected_child = Bunch.Bunch(subwin=subwin, action='move',
                                          cr = self.setup_cr(self.bin_window),
                                          x_origin=x, y_origin=y, dx=ex, dy=ey)
        return True

    def start_resize_cb(self, widget, event, subwin):
        ex, ey = event.x_root, event.y_root
        x, y = self.get_widget_position(subwin.frame)
        subwin.x, subwin.y = x, y
        self.selected_child = Bunch.Bunch(subwin=subwin, action='resize',
                                          cr = self.setup_cr(self.bin_window),
                                          x_origin=x, y_origin=y, dx=ex, dy=ey)
        return True

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
            subwin = bnch.subwin
            if bnch.action == 'move':
                x = int(subwin.x + (x - bnch.dx))
                y = int(subwin.y + (y - bnch.dy))
                self.move(subwin.frame, x, y)
                subwin.x, subwin.y = self.get_widget_position(subwin.frame)
            elif bnch.action == 'resize':
                wd = int(subwin.width + (x - bnch.dx))
                ht = int(subwin.height + (y - bnch.dy))
                subwin.frame.set_size_request(wd, ht)
                subwin.width, subwin.height = self.get_widget_size(subwin.frame)
            self.selected_child = None
        return True

    def motion_notify_event(self, widget, event):
        button = self.kbdmouse_mask
        if event.is_hint:
            return
        else:
            x, y, state = event.x_root, event.y_root, event.state

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
                x = int(subwin.x + (x - bnch.dx))
                y = int(subwin.y + (y - bnch.dy))
                self.move(subwin.frame, x, y)
            elif bnch.action == 'resize':
                wd = int(subwin.width + (x - bnch.dx))
                ht = int(subwin.height + (y - bnch.dy))
                subwin.frame.set_size_request(wd, ht)
        return True

    def tile_pages(self):
        pass

    def cascade_pages(self):
        x, y = 0, 0
        for subwin in self.children:
            self.move(subwin.frame, x, y)
            x += self.cascade_offset
            y += self.cascade_offset

    def use_tabs(self, tf):
        pass


class FileSelection(object):

    def __init__(self, parent_w, action=Gtk.FileChooserAction.OPEN,
                 title="Select a file"):
        self.parent = parent_w
        # Create a new file selection widget
        self.filew = Gtk.FileChooserDialog(title=title, action=action)
        self.filew.connect("destroy", self.close)
        if action == Gtk.FileChooserAction.SAVE:
            self.filew.add_buttons(Gtk.STOCK_SAVE, 1, Gtk.STOCK_CANCEL, 0)
        else:
            self.filew.add_buttons(Gtk.STOCK_OPEN, 1, Gtk.STOCK_CANCEL, 0)
        self.filew.set_default_response(1)
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

    # Get the selected filename
    def file_ok_sel(self, w, rsp):
        self.close(w)
        if rsp == 0:
            return

        filepath = self.filew.get_filename()
        self.cb(filepath)

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


class Timer(object):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, ival_sec, expire_cb, data=None):
        """Create a timer set to expire after `ival_sec` and which will
        call the callable `expire_cb` when it expires.
        """
        self.ival_sec = ival_sec
        self.cb = expire_cb
        self.data = data
        self._timer = None

    def start(self, ival_sec=None):
        """Start the timer.  If `ival_sec` is not None, it should
        specify the time to expiration in seconds.
        """
        if ival_sec is None:
            ival_sec = self.ival_sec

        self.cancel()

        # Gtk timer set in milliseconds
        time_ms = int(ival_sec * 1000.0)
        self._timer = GObject.timeout_add(time_ms, self._redirect_cb)

    def _redirect_cb(self):
        self._timer = None
        self.cb(self)

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        try:
            if self._timer is not None:
                GObject.source_remove(self._timer)
                self._timer = None
        except:
            pass


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
    direction = None
    if event.direction == Gdk.ScrollDirection.UP:
        direction = 0.0
    elif event.direction == Gdk.ScrollDirection.DOWN:
        direction = 180.0
    elif event.direction == Gdk.ScrollDirection.LEFT:
        direction = 270.0
    elif event.direction == Gdk.ScrollDirection.RIGHT:
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
    pixbuf = pixbuf_new_from_file_at_size(iconpath, wd, ht)
    return pixbuf

def get_font(font_family, point_size):
    font = Pango.FontDescription('%s %d' % (font_family, point_size))
    return font

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
    return GdkPixbuf.Pixbuf.new_from_file_at_size(foldericon,
                                                  width, height)

def make_cursor(widget, iconpath, x, y):
    image = Gtk.Image()
    image.set_from_file(iconpath)
    pixbuf = image.get_pixbuf()
    screen = widget.get_screen()
    display = screen.get_display()
    return Gdk.Cursor(display, pixbuf, x, y)

def set_default_style():
    style_provider = Gtk.CssProvider()

    module_home = os.path.split(sys.modules[__name__].__file__)[0]
    gtk_css = os.path.join(module_home, 'gtk_css')
    with open(gtk_css, 'rb') as css_f:
        css_data = css_f.read()

    style_provider.load_from_data(css_data)

    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(), style_provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

#END
