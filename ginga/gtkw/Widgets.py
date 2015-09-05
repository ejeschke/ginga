#
# Widgets.py -- wrapped Gtk widgets and convenience functions
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import GtkHelp, gtksel, GtkMain
import gtk
import gobject

from ginga.misc import Callback, Bunch
from functools import reduce

class WidgetError(Exception):
    """For errors thrown in this module."""
    pass

# BASE

class WidgetBase(Callback.Callbacks):

    def __init__(self):
        super(WidgetBase, self).__init__()

        self.widget = None

    def get_widget(self):
        return self.widget

    def set_tooltip(self, text):
        self.widget.set_tooltip_text(text)

    def set_enabled(self, tf):
        self.widget.set_sensitive(tf)

# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text=''):
        super(TextEntry, self).__init__()

        w = gtk.Entry()
        w.set_text(text)
        w.connect('activate', self._cb_redirect)
        self.widget = w

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.make_callback('activated')

    def get_text(self):
        return self.widget.get_text()

    def set_text(self, text):
        self.widget.set_text(text)

    def set_length(self, numchars):
        # this only sets the visible length of the widget
        self.widget.set_width_chars(numchars)
        pass

class TextEntrySet(WidgetBase):
    def __init__(self, text=''):
        super(TextEntrySet, self).__init__()

        hbox = gtk.HBox()
        hbox.set_spacing(4)
        w = gtk.Entry()
        w.set_text(text)
        hbox.pack_start(w, fill=True)
        w.connect('activate', self._cb_redirect)
        self.entry = w
        w = gtk.Button('Set')
        w.connect('clicked', self._cb_redirect)
        hbox.pack_start(w, fill=False)
        self.btn = w
        self.widget = hbox

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.make_callback('activated')

    def get_text(self):
        return self.entry.get_text()

    def set_text(self, text):
        self.entry.set_text(text)

    def set_length(self, numchars):
        #self.widget.set_width_chars(numchars)
        pass

class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        tw = gtk.TextView()
        if wrap:
            tw.set_wrap_mode(gtk.WRAP_WORD)
        else:
            tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_editable(editable)
        self.widget = tw
        self.histlimit = 0

    def append_text(self, text, autoscroll=True):
        buf = self.widget.get_buffer()
        end = buf.get_end_iter()
        buf.insert(end, text)

        if self.histlimit > 0:
            self._history_housekeeping()
        if not autoscroll:
            return

        end = buf.get_end_iter()
        mark = buf.get_insert()
        #self.widget.scroll_to_iter(end, 0.5)
        # NOTE: this was causing a segfault if the text widget is
        # not mapped yet!  Seems to be fixed in recent versions of
        # gtk
        buf.move_mark(mark, end)
        res = self.widget.scroll_to_mark(mark, 0.2, True)

    def get_text(self):
        buf = self.widget.get_buffer()
        return buf.get_text()

    def _history_housekeeping(self):
        # remove some lines to keep us within our history limit
        buf = self.widget.get_buffer()
        numlines = buf.get_line_count()
        if numlines > self.histlimit:
            rmcount = int(numlines - self.histlimit)
            start = buf.get_iter_at_line(0)
            end   = buf.get_iter_at_line(rmcount)
            buf.delete(start, end)

    def clear(self):
        buf = self.widget.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        buf.delete(start, end)

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_limit(self, numlines):
        self.histlimit = numlines
        self._history_housekeeping()

    def set_font(self, font):
        self.widget.modify_font(font)

    def set_wrap(self, tf):
        if tf:
            self.widget.set_wrap_mode(gtk.WRAP_WORD)
        else:
            self.widget.set_wrap_mode(gtk.WRAP_NONE)

class Label(WidgetBase):
    def __init__(self, text=''):
        super(Label, self).__init__()

        self.widget = gtk.Label(text)

    def get_text(self):
        return self.widget.get_text()

    def set_text(self, text):
        self.widget.set_text(text)


class Button(WidgetBase):
    def __init__(self, text=''):
        super(Button, self).__init__()

        w = gtk.Button(text)
        self.widget = w
        w.connect('clicked', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.make_callback('activated')


class ComboBox(WidgetBase):
    def __init__(self, editable=False):
        super(ComboBox, self).__init__()

        if editable:
            cb = GtkHelp.ComboBoxEntry()
        else:
            cb = GtkHelp.ComboBox()
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        cb.set_model(liststore)
        cell = gtk.CellRendererText()
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)
        self.widget = cb
        self.widget.sconnect('changed', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        idx = widget.get_active()
        self.make_callback('activated', idx)

    def insert_alpha(self, text):
        model = self.widget.get_model()
        tup = (text, )
        j = 0
        for i in range(len(model)):
            j = i
            if model[i][0] > text:
                model.insert(j, tup)
                return
        model.insert(j+1, tup)

    def append_text(self, text):
        model = self.widget.get_model()
        tup = (text, )
        idx = len(model)
        model.insert(idx, tup)

    def insert_text(self, idx, text):
        model = self.widget.get_model()
        tup = (text, )
        model.insert(idx, tup)

    def delete_alpha(self, text):
        model = self.widget.get_model()
        for i in range(len(model)):
            if model[i][0] == text:
                del model[i]
                return

    def clear(self):
        model = self.widget.get_model()
        model.clear()

    def show_text(self, text):
        model = self.widget.get_model()
        for i in range(len(model)):
            if model[i][0] == text:
                self.widget.set_active(i)
                return

    def set_index(self, index):
        self.widget.set_active(index)

    def get_index(self):
        return self.widget.get_active()


class SpinBox(WidgetBase):
    def __init__(self, dtype=int):
        super(SpinBox, self).__init__()

        self.widget = GtkHelp.SpinButton()
        # if not gtksel.have_gtk3:
        #     self.widget.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.widget.sconnect('value-changed', self._cb_redirect)

        self.enable_callback('value-changed')

    def _cb_redirect(self, w):
        val = w.get_value()
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.get_value()

    def set_value(self, val):
        self.widget.set_value(val)

    def set_decimals(self, num):
        self.widget.set_digits(num)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget.get_adjustment()
        adj.configure(minval, minval, maxval, incr_value, incr_value, 0)


class Slider(WidgetBase):
    def __init__(self, orientation='horizontal', track=False):
        super(Slider, self).__init__()

        if orientation == 'horizontal':
            w = GtkHelp.HScale()
            # TEMP: hack because scales don't seem to expand as expected
            w.set_size_request(200, -1)
        else:
            w = GtkHelp.VScale()
            w.set_size_request(-1, 200)
        self.widget = w

        w.set_draw_value(True)
        w.set_value_pos(gtk.POS_BOTTOM)
        self.set_tracking(track)
        w.sconnect('value-changed', self._cb_redirect)

        self.enable_callback('value-changed')

    def _cb_redirect(self, range):
        val = range.get_value()
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.get_value()

    def set_value(self, val):
        self.widget.set_value(val)

    def set_tracking(self, tf):
        if tf:
            self.widget.set_update_policy(gtk.UPDATE_CONTINUOUS)
        else:
            self.widget.set_update_policy(gtk.UPDATE_DISCONTINUOUS)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget.get_adjustment()
        adj.configure(minval, minval, maxval, incr_value, incr_value, 0)


class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        if orientation == 'horizontal':
            self.widget = gtk.HScrollbar()
        else:
            self.widget = gtk.VScrollbar()
        self.widget.connect('value-changed', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, range):
        val = range.get_value()
        self.make_callback('activated', val)


class CheckBox(WidgetBase):
    def __init__(self, text=''):
        super(CheckBox, self).__init__()

        self.widget = GtkHelp.CheckButton(text)
        self.widget.sconnect('toggled', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)

    def set_state(self, tf):
        self.widget.set_active(tf)

    def get_state(self):
        return self.widget.get_active()


class ToggleButton(WidgetBase):
    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        w = GtkHelp.ToggleButton(text)
        w.set_mode(True)
        self.widget = w
        self.widget.sconnect('toggled', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)

    def set_state(self, tf):
        self.widget.set_active(tf)

    def get_state(self):
        return self.widget.get_active()


class RadioButton(WidgetBase):
    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        if group is not None:
            group = group.get_widget()
        self.widget = GtkHelp.RadioButton(group, text)
        self.widget.connect('toggled', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)

    def set_state(self, tf):
        self.widget.set_active(tf)

    def get_state(self):
        return self.widget.get_active()

class ProgressBar(WidgetBase):
    def __init__(self):
        super(ProgressBar, self).__init__()

        w = gtk.ProgressBar()
        # GTK3
        #w.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        #w.set_inverted(False)
        self.widget = w

    def set_value(self, pct):
        pct = float(pct)
        self.widget.set_fraction(pct)
        self.widget.set_text("%.2f %%" % (pct * 100.0))

# CONTAINERS

class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        self.children = []

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def _remove(self, childw):
        self.widget.remove(childw)

    def remove(self, w):
        if not w in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(w)

        self._remove(w.get_widget())

    def remove_all(self):
        for w in list(self.children):
            self.remove(w)

    def get_children(self):
        return self.children


class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        if orientation == 'horizontal':
            self.widget = gtk.HBox()
        else:
            self.widget = gtk.VBox()

    def set_spacing(self, val):
        self.widget.set_spacing(val)

    def set_margins(self, left, right, top, bottom):
        # TODO: can this be made more accurate?
        self.widget.set_border_width(left)

    def set_border_width(self, pix):
        self.widget.set_border_width(pix)

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)
        child_w = child.get_widget()
        # TODO: can this be made more accurate?
        expand = (float(stretch) != 0.0)
        self.widget.pack_start(child_w, expand=expand, fill=True)
        self.widget.show_all()

class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')

class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')


class Frame(ContainerBase):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        fr = gtk.Frame(label=title)
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.10, 0.5)
        self.widget = fr

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.add(child.get_widget())
        self.widget.show_all()


class Expander(ContainerBase):
    def __init__(self, title=None):
        super(Expander, self).__init__()

        w = gtk.Expander(label=title)
        self.widget = w

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.add(child.get_widget())
        self.widget.show_all()


class TabWidget(ContainerBase):
    def __init__(self, tabpos='top'):
        super(TabWidget, self).__init__()

        nb = gtk.Notebook()
        nb.set_show_border(False)
        nb.set_scrollable(True)
        if tabpos == 'top':
            nb.set_tab_pos(gtk.POS_TOP)
        elif tabpos == 'bottom':
            nb.set_tab_pos(gtk.POS_BOTTOM)
        elif tabpos == 'left':
            nb.set_tab_pos(gtk.POS_LEFT)
        elif tabpos == 'right':
            nb.set_tab_pos(gtk.POS_RIGHT)
        nb.connect("switch-page", self._cb_redirect)
        self.widget = nb

        self.enable_callback('activated')

    def _cb_redirect(self, nbw, gptr, index):
        self.make_callback('activated', index)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        label = gtk.Label(title)
        self.widget.append_page(child_w, label)
        self.widget.show_all()

    def get_index(self):
        return self.widget.get_current_page()

    def set_index(self, idx):
        self.widget.set_current_page(idx)

    def index_of(self, child):
        return self.widget.page_num(child.get_widget())


class StackWidget(TabWidget):
    def __init__(self):
        super(StackWidget, self).__init__()

        nb = self.widget
        #nb.set_scrollable(False)
        nb.set_show_tabs(False)
        nb.set_show_border(False)

class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget = sw

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.add_with_viewport(child.get_widget())
        self.widget.show_all()


class Splitter(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Splitter, self).__init__()

        self.orientation = orientation
        if orientation == 'horizontal':
            w = gtk.HPaned()
        else:
            w = gtk.VPaned()
        self.widget = w

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        if len(self.children) == 1:
            #self.widget.pack1(child_w, resize=True, shrink=True)
            self.widget.pack1(child_w)

        else:
            self.widget.pack2(child_w)
        self.widget.show_all()


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        w = gtk.Table(rows=rows, columns=columns)
        self.widget = w

    def set_row_spacing(self, val):
        self.widget.set_row_spacings(val)

    def set_column_spacing(self, val):
        self.widget.set_col_spacings(val)

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        w = child.get_widget()
        if stretch > 0:
            xoptions = gtk.EXPAND|gtk.FILL
        else:
            xoptions = gtk.FILL
        self.widget.attach(w, col, col+1, row, row+1, xoptions=xoptions)
        self.widget.show_all()


class Toolbar(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Toolbar, self).__init__()

        w = gtk.Toolbar()
        w.set_style(gtk.TOOLBAR_ICONS)
        if orientation == 'horizontal':
            w.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        else:
            w.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.widget = w

    def add_action(self, text, toggle=False, iconpath=None):
        if toggle:
            child = ToggleButton(text)
        else:
            child = Button(text)

        if iconpath is not None:
            pixbuf = gtksel.pixbuf_new_from_file_at_size(iconpath, 24, 24)
            if pixbuf is not None:
                image = gtk.image_new_from_pixbuf(pixbuf)
                child.get_widget().set_image(image)

        self.add_widget(child)
        return child

    def add_widget(self, child):
        self.add_ref(child)
        w = child.get_widget()
        self.widget.append_widget(w, None, None)

    def add_separator(self):
        self.widget.append_space()


class MenuAction(WidgetBase):
    def __init__(self, text=None):
        super(MenuAction, self).__init__()

        self.text = text

        self.widget = gtk.MenuItem(label=text)
        self.widget.show()

        self.widget.connect('activate', self._cb_redirect)
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        # TODO: checkable menu items
        self.make_callback('activated')


class Menu(ContainerBase):
    def __init__(self):
        super(Menu, self).__init__()

        self.widget = gtk.Menu()
        self.widget.show()

    def add_widget(self, child):
        menuitem_w = child.get_widget()
        self.widget.append(menuitem_w)
        self.add_ref(child)
        #self.widget.show_all()

    def add_name(self, name):
        child = MenuAction(text=name)
        self.add_widget(child)
        return child

    def add_separator(self):
        sep = gtk.SeparatorMenuItem()
        self.widget.append(sep)
        sep.show()


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = gtk.MenuBar()

    def add_widget(self, child):
        menu_w = child.get_widget()
        self.widget.addMenu(menu_w)
        self.add_ref(child)
        menu_w.show()
        return child

    def add_name(self, name):
        item_w = gtk.MenuItem(label=name)
        child = Menu()
        self.add_ref(child)
        item_w.set_submenu(child.get_widget())
        self.widget.append(item_w)
        item_w.show()
        return child


class TopLevel(ContainerBase):
    def __init__(self, title=None):
        super(TopLevel, self).__init__()

        widget = GtkHelp.TopLevel()
        self.widget = widget
        widget.set_border_width(0)
        widget.connect("destroy", self._quit)
        widget.connect("delete_event", self._closeEvent)

        if not title is None:
            widget.set_title(title)

        self.enable_callback('closed')

    def set_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.add(child_w)

    def show(self):
        self.widget.show_all()

    def hide(self):
        self.widget.hide()

    def _quit(self, *args):
        self.close()

    def _closeEvent(self, widget, event):
        self.close()

    def close(self):
        try:
            self.widget.destroy()
        except Exception as e:
            pass
        #self.widget = None

        self.make_callback('closed')

    def raise_(self):
        window = self.widget.get_window()
        ## if window:
        ##     if hasattr(window, 'present'):
        ##         # gtk3 ?
        ##         window.present()
        ##     else:
        ##         # gtk2
        ##         window.show()
        window.raise_()

    def lower(self):
        window = self.widget.get_window()
        window.lower()

    def resize(self, width, height):
        self.widget.set_size_request(width, height)

    def focus(self):
        window = self.widget.get_window()
        window.focus()

    def move(self, x, y):
        window = self.widget.get_window()
        window.move(x, y)

    def maximize(self):
        window = self.widget.get_window()
        window.maximize()

    def unmaximize(self):
        window = self.widget.get_window()
        window.unmaximize()

    def fullscreen(self):
        window = self.widget.get_window()
        window.fullscreen()

    def unfullscreen(self):
        window = self.widget.get_window()
        window.unfullscreen()

    def iconify(self):
        window = self.widget.get_window()
        window.iconify()

    def uniconify(self):
        window = self.widget.get_window()
        window.deiconify()

    def set_title(self, title):
        self.widget.set_title(title)


class Application(GtkMain.GtkMain):

    def __init__(self, *args, **kwdargs):
        super(Application, self).__init__(*args, **kwdargs)

        self.window_list = []

    def window(self, title=None):
        w = TopLevel(title=title)
        self.window_list.append(w)
        return w


class SaveDialog:
    def __init__(self, title='Save File', selectedfilter=None):
        action = gtk.FILE_CHOOSER_ACTION_SAVE
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        self.widget = gtk.FileChooserDialog(title=title, action=action, buttons=buttons)

        filtr = gtk.FileFilter()
        filtr.add_pattern(selectedfilter)
        if 'png' in selectedfilter:
            filtr.set_name('Image (*.png)')
            self.selectedfilter = '.png'
        elif 'avi' in selectedfilter:
            filtr.set_name('Movie (*.avi)')
            self.selectedfilter = '.avi'
        elif 'npz' in selectedfilter:
            filtr.set_name('Numpy Compressed Archive (*.npz)')
            self.selectedfilter = '.npz'
        self.widget.add_filter(filtr)

    def get_path(self):
        response = self.widget.run()

        if response == gtk.RESPONSE_OK:
            path = self.widget.get_filename()
            if not path.endswith(self.selectedfilter):
                path += self.selectedfilter
            self.widget.destroy()
            return path
        elif response == gtk.RESPONSE_CANCEL:
            self.widget.destroy()
            return None

# MODULE FUNCTIONS

def name_mangle(name, pfx=''):
    newname = []
    for c in name.lower():
        if not (c.isalpha() or c.isdigit() or (c == '_')):
            newname.append('_')
        else:
            newname.append(c)
    return pfx + ''.join(newname)

def make_widget(title, wtype):
    if wtype == 'label':
        w = Label(title)
        w.get_widget().set_alignment(0.95, 0.5)
    elif wtype == 'llabel':
        w = Label(title)
        w.get_widget().set_alignment(0.05, 0.95)
    elif wtype == 'entry':
        w = TextEntry()
        #w.get_widget().set_width_chars(12)
    elif wtype == 'entryset':
        w = TextEntrySet()
    elif wtype == 'combobox':
        w = ComboBox()
    elif wtype == 'spinbutton':
        w = SpinBox(dtype=int)
    elif wtype == 'spinfloat':
        w = SpinBox(dtype=float)
    elif wtype == 'vbox':
        w = VBox()
    elif wtype == 'hbox':
        w = HBox()
    elif wtype == 'hscale':
        w = Slider(orientation='horizontal')
    elif wtype == 'vscale':
        w = Slider(orientation='vertical')
    elif wtype == 'checkbutton':
        w = CheckBox(title)
    elif wtype == 'radiobutton':
        w = RadioButton(title)
    elif wtype == 'togglebutton':
        w = ToggleButton(title)
    elif wtype == 'button':
        w = Button(title)
    elif wtype == 'spacer':
        w = Label('')
    elif wtype == 'textarea':
        w = TextArea(editable=True)
    elif wtype == 'toolbar':
        w = Toolbar()
    elif wtype == 'menubar':
        w = Menubar()
    else:
        raise ValueError("Bad wtype=%s" % wtype)
    return w


def hadjust(w, orientation):
    if orientation != 'horizontal':
        return w
    vbox = VBox()
    vbox.add_widget(w)
    vbox.add_widget(Label(''), stretch=1)
    return vbox


def build_info(captions, orientation='vertical'):
    vbox = gtk.VBox(spacing=2)

    numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)
    if (numcols % 2) != 0:
        raise ValueError("Column spec is not an even number")
    numcols /= 2
    table = gtk.Table(rows=numrows, columns=numcols)
    table.set_row_spacings(2)
    table.set_col_spacings(4)
    vbox.pack_start(table, expand=False)

    wb = Bunch.Bunch()
    row = 0
    for tup in captions:
        col = 0
        while col < numcols:
            idx = col * 2
            if idx < len(tup):
                title, wtype = tup[idx:idx+2]
                if not title.endswith(':'):
                    name = name_mangle(title)
                else:
                    name = name_mangle('lbl_'+title[:-1])
                w = make_widget(title, wtype)
                table.attach(w.get_widget(), col, col+1, row, row+1,
                             xoptions=gtk.FILL, yoptions=gtk.FILL,
                             xpadding=1, ypadding=1)
                wb[name] = w
            col += 1
        row += 1

    vbox.show_all()

    w = wrap(vbox)
    w = hadjust(w, orientation=orientation)

    return w, wb


def wrap(native_widget):
    wrapper = WidgetBase()
    wrapper.widget = native_widget
    return wrapper


def get_orientation(container):
    if not hasattr(container, 'size'):
        return 'vertical'
    (wd, ht) = container.size
    if wd < ht:
        return 'vertical'
    else:
        return 'horizontal'

def get_oriented_box(container, scrolled=True, fill=False):
    orientation = get_orientation(container)

    if orientation == 'vertical':
        box1 = VBox()
        box2 = VBox()
    else:
        box1 = HBox()
        box2 = VBox()

    box2.add_widget(box1)
    if scrolled:
        box2.add_widget(Label(''), stretch=1)
        sw = ScrollArea()
        sw.set_widget(box2)
    else:
        sw = box2

    return box1, sw, orientation

#END
