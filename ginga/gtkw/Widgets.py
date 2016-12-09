#
# Widgets.py -- wrapped Gtk widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import GtkHelp
import ginga.util.six as six
import gtk
import gobject

from ginga.misc import Callback, Bunch, LineHistory
from functools import reduce

class WidgetError(Exception):
    """For errors thrown in this module."""
    pass


# (see TabWidget)
_widget_move_event = None
_app = None

# BASE

class WidgetBase(Callback.Callbacks):

    def __init__(self):
        super(WidgetBase, self).__init__()

        self.widget = None
        # external data can be attached here
        self.extdata = Bunch.Bunch()

    def get_widget(self):
        return self.widget

    def set_tooltip(self, text):
        self.widget.set_tooltip_text(text)

    def set_enabled(self, tf):
        self.widget.set_sensitive(tf)

    def get_size(self):
        window = self.widget.get_window()
        if window is not None:
            # NOTE: we don't seem to get accurate information unless
            # the window is actually mapped, thus the test
            rect = self.widget.get_allocation()
            x, y, wd, ht = rect.x, rect.y, rect.width, rect.height

        else:
            # window maybe isn't realized yet--try other ways
            # NOTE: get_size_request() does not seem to work the same
            # as size_request() for gtk2!
            wd, ht = self.widget.size_request()

        return wd, ht

    def get_pos(self):
        rect = self.widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height
        return x, y

    def get_app(self):
        return _app

    def delete(self):
        self.widget.destroy()

    def show(self):
        #self.widget.show()
        self.widget.show_all()

    def hide(self):
        self.widget.hide()

    def focus(self):
        self.widget.grab_focus()

    def resize(self, width, height):
        self.widget.set_size_request(width, height)
        # hackish way to allow the widget to be resized down again later
        # NOTE: for gtk2 we can't do this because it affects get_size()
        #gobject.idle_add(self.widget.set_size_request, -1, -1)

    def get_font(self, font_family, point_size):
        font = GtkHelp.get_font(font_family, point_size)
        return font

    def cfg_expand(self, horizontal=0, vertical=0):
        # this is for compatibility with Qt widgets
        pass

# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntry, self).__init__()

        w = gtk.Entry()
        w.set_text(text)
        w.set_editable(editable)
        w.connect('key-press-event', self._key_press_event)
        w.connect('activate', self._cb_redirect)
        self.widget = w

        self.history = LineHistory.LineHistory()

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.history.append(self.get_text())
        self.make_callback('activated')

    def _key_press_event(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == 'Up':
            try:
                text = self.history.prev()
                self.set_text(text)
                self.widget.set_position(len(text))
            except ValueError:
                pass
            return True
        elif keyname == 'Down':
            try:
                text = self.history.next()
                self.set_text(text)
                self.widget.set_position(len(text))
            except ValueError:
                pass
            return True
        return False

    def get_text(self):
        return self.widget.get_text()

    def set_text(self, text):
        self.widget.set_text(text)

    def set_editable(self, tf):
        self.widget.set_editable(tf)

    def set_font(self, font):
        self.widget.modify_font(font)

    def set_length(self, numchars):
        # this only sets the visible length of the widget
        self.widget.set_width_chars(numchars)
        pass

class TextEntrySet(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntrySet, self).__init__()

        hbox = gtk.HBox()
        hbox.set_spacing(4)
        w = gtk.Entry()
        w.set_text(text)
        w.set_editable(editable)
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

    def set_editable(self, tf):
        self.entry.set_editable(tf)

    def set_font(self, font):
        self.widget.modify_font(font)

    def set_length(self, numchars):
        #self.widget.set_width_chars(numchars)
        pass

    def set_enabled(self, tf):
        super(TextEntrySet, self).set_enabled(tf)
        self.entry.set_sensitive(tf)

class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        tw = gtk.TextView()
        if wrap:
            tw.set_wrap_mode(gtk.WRAP_WORD)
        else:
            tw.set_wrap_mode(gtk.WRAP_NONE)
        tw.set_editable(editable)
        self.tw = tw

        # this widget has a built in ScrollArea to match Qt functionality
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.tw)
        self.widget = sw

        self.histlimit = 0

    def append_text(self, text, autoscroll=True):
        buf = self.tw.get_buffer()
        end = buf.get_end_iter()
        buf.insert(end, text)

        if self.histlimit > 0:
            self._history_housekeeping()
        if not autoscroll:
            return

        end = buf.get_end_iter()
        mark = buf.get_insert()
        #self.tw.scroll_to_iter(end, 0.5)
        # NOTE: this was causing a segfault if the text widget is
        # not mapped yet!  Seems to be fixed in recent versions of
        # gtk
        buf.move_mark(mark, end)
        res = self.tw.scroll_to_mark(mark, 0.2, True)

    def get_text(self):
        buf = self.tw.get_buffer()
        return buf.get_text()

    def _history_housekeeping(self):
        # remove some lines to keep us within our history limit
        buf = self.tw.get_buffer()
        numlines = buf.get_line_count()
        if numlines > self.histlimit:
            rmcount = int(numlines - self.histlimit)
            start = buf.get_iter_at_line(0)
            end   = buf.get_iter_at_line(rmcount)
            buf.delete(start, end)

    def clear(self):
        buf = self.tw.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        buf.delete(start, end)

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_limit(self, numlines):
        self.histlimit = numlines
        self._history_housekeeping()

    def set_editable(self, tf):
        self.tw.set_editable(tf)

    def set_font(self, font):
        self.tw.modify_font(font)

    def set_wrap(self, tf):
        if tf:
            self.tw.set_wrap_mode(gtk.WRAP_WORD)
        else:
            self.tw.set_wrap_mode(gtk.WRAP_NONE)

class Label(WidgetBase):
    def __init__(self, text='', halign='left', style='normal', menu=None):
        super(Label, self).__init__()

        label = gtk.Label(text)
        evbox = gtk.EventBox()
        evbox.set_border_width(0)
        evbox.props.visible_window = False
        evbox.add(label)
        evbox.connect("button_press_event", self._cb_redirect)

        if halign == 'left':
            label.set_justify(gtk.JUSTIFY_LEFT)
        elif halign == 'center':
            label.set_justify(gtk.JUSTIFY_CENTER)
        elif halign == 'right':
            label.set_justify(gtk.JUSTIFY_RIGHT)

        evbox.connect("button_press_event", self._cb_redirect)
        self.enable_callback('activated')

        self.label = label
        self.menu = menu
        self.evbox = evbox
        self.widget = evbox
        if style == 'clickable':
            fr = gtk.Frame()
            fr.set_shadow_type(gtk.SHADOW_OUT)
            evbox.props.visible_window = True
            fr.add(evbox)
            self.frame = fr
            self.widget = fr

    def _cb_redirect(self, widget, event):
        # event.button, event.x, event.y
        if event.button == 1:
            self.make_callback('activated')
            return True

        elif event.button == 3 and self.menu is not None:
            menu_w = self.menu.get_widget()
            return menu_w.popup(None, None, None,
                                event.button, event.time)
        return False

    def get_text(self):
        return self.label.get_text()

    def set_text(self, text):
        self.label.set_text(text)

    def set_font(self, font):
        self.label.modify_font(font)

    def set_color(self, fg=None, bg=None):
        if bg is not None:
            self.evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bg))
        if fg is not None:
            self.label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(fg))

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

    def get_alpha(self, idx):
        model = self.widget.get_model()
        text = model[idx][0]
        return text

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
        #self.widget.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.widget.sconnect('value-changed', self._cb_redirect)

        self.enable_callback('value-changed')

        self.dtype = dtype

    def _cb_redirect(self, w):
        val = self.dtype(w.get_value())
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.dtype(self.widget.get_value())

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


class Image(WidgetBase):
    def __init__(self, native_image=None, style='normal', menu=None):
        super(Image, self).__init__()

        if native_image is None:
            native_image = gtk.Image()
        self.image = native_image
        self.image.set_property("has-tooltip", True)
        evbox = gtk.EventBox()
        evbox.add(self.image)
        evbox.connect("button-press-event", self._cb_redirect1)
        evbox.connect("button-release-event", self._cb_redirect2)
        self._action = None
        self.menu = menu
        self.widget = evbox

        self.enable_callback('activated')

    def _cb_redirect1(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 1:
                self._action = 'click'

            elif event.button == 3 and self.menu is not None:
                menu_w = self.menu.get_widget()
                return menu_w.popup(None, None, None,
                                    event.button, event.time)

    def _cb_redirect2(self, widget, event):
        if event.type == gtk.gdk.BUTTON_RELEASE:
            if (event.button == 1) and (self._action == 'click'):
                self._action = None
                self.make_callback('activated')

    def _set_image(self, native_image):
        self.image.set_from_pixbuf(native_image.get_pixbuf())

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

class StatusBar(WidgetBase):
    def __init__(self):
        super(StatusBar, self).__init__()

        sbar = gtk.Statusbar()
        sbar.set_has_resize_grip(True)
        self.ctx_id = None
        self.widget = sbar
        self.statustask = None

    def _clear_message(self):
        self.statustask = None
        self.widget.remove_all(self.ctx_id)

    def set_message(self, msg_str, duration=10.0):
        try:
            self.widget.remove_all(self.ctx_id)
        except:
            pass
        self.ctx_id = self.widget.get_context_id('status')
        self.widget.push(self.ctx_id, msg_str)

        # remove message in about 10 seconds
        if self.statustask:
            gobject.source_remove(self.statustask)
        self.statustask = gobject.timeout_add(int(1000 * duration),
                                              self._clear_message)


class TreeView(WidgetBase):
    def __init__(self, auto_expand=False, sortable=False, selection='single',
                 use_alt_row_color=False, dragable=False):
        super(TreeView, self).__init__()

        self.auto_expand = auto_expand
        self.sortable = sortable
        self.selection = selection
        self.dragable = dragable
        self.levels = 1
        self.leaf_key = None
        self.leaf_idx = 0
        self.columns = []
        self.datakeys = []
        # shadow index
        self.shadow = {}

        # this widget has a built in ScrollArea to match Qt functionality
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget = sw

        if self.dragable:
            tv = GtkHelp.MultiDragDropTreeView()
            # enable drag from this widget
            toImage = [ ( "text/plain", 0, 0 ) ]
            tv.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                        toImage, gtk.gdk.ACTION_COPY)
            tv.connect("drag-data-get", self._start_drag)
        else:
            tv = gtk.TreeView()

        self.tv = tv
        sw.add(self.tv)
        tv.connect('cursor-changed', self._selection_cb)
        tv.connect('row-activated', self._cb_redirect)
        # needed to get alternating row colors
        if use_alt_row_color:
            tv.set_rules_hint(True)
        if self.selection == 'multiple':
            # enable multiple selection
            treeselection = tv.get_selection()
            treeselection.set_mode(gtk.SELECTION_MULTIPLE)

        for cbname in ('selected', 'activated', 'drag-start'):
            self.enable_callback(cbname)

    def setup_table(self, columns, levels, leaf_key):
        self.clear()

        self.columns = columns
        self.levels = levels
        self.leaf_key = leaf_key

        # create the column headers
        if not isinstance(columns[0], str):
            # columns specifies a mapping
            headers = [ col[0] for col in columns ]
            datakeys = [ col[1] for col in columns ]
        else:
            headers = datakeys = columns

        self.datakeys = datakeys
        self.leaf_idx = datakeys.index(self.leaf_key)
        # make sort functions
        self.cell_sort_funcs = []
        for kwd in self.datakeys:
            self.cell_sort_funcs.append(self._mksrtfnN(kwd))

        # Remove old columns, if any
        for col in list(self.tv.get_columns()):
            self.tv.remove_column(col)

        # Set up headers
        for n in range(0, len(self.columns)):
            kwd = self.datakeys[n]
            if kwd == 'icon':
                cell = gtk.CellRendererPixbuf()
            else:
                cell = gtk.CellRendererText()
            cell.set_padding(2, 0)
            header = headers[n]
            tvc = gtk.TreeViewColumn(header, cell)
            tvc.set_resizable(True)
            if self.sortable:
                tvc.connect('clicked', self.sort_cb, n)
                tvc.set_clickable(True)
            if n == 0:
                fn_data = self._mkcolfn0(kwd)
                ## cell.set_property('xalign', 1.0)
            else:
                fn_data = self._mkcolfnN(kwd)
            tvc.set_cell_data_func(cell, fn_data)
            self.tv.append_column(tvc)

        treemodel = gtk.TreeStore(object)
        self.tv.set_fixed_height_mode(False)
        self.tv.set_model(treemodel)
        # This speeds up rendering of TreeViews
        self.tv.set_fixed_height_mode(True)

    def set_tree(self, tree_dict):
        self.clear()

        model = gtk.TreeStore(object)
        self._add_tree(model, tree_dict)

    def add_tree(self, tree_dict):
        model = self.tv.get_model()
        self._add_tree(model, tree_dict)

    def _add_tree(self, model, tree_dict):

        # Hack to get around slow TreeView scrolling with large lists
        self.tv.set_fixed_height_mode(False)

        for key in tree_dict:
            self._add_subtree(1, self.shadow,
                              model, None, key, tree_dict[key])

        self.tv.set_model(model)

        self.tv.set_fixed_height_mode(True)

        # User wants auto expand?
        if self.auto_expand:
            self.tv.expand_all()

    def _add_subtree(self, level, shadow, model, parent_item, key, node):

        if level >= self.levels:
            # leaf node
            try:
                bnch = shadow[key]
                item_iter = bnch.item
                # TODO: update leaf item

            except KeyError:
                # new item
                item_iter = model.append(parent_item, [node])
                shadow[key] = Bunch.Bunch(node=node, item=item_iter,
                                          terminal=True)

        else:
            try:
                # node already exists
                bnch = shadow[key]
                item = bnch.item
                d = bnch.node

            except KeyError:
                # new node
                item = model.append(None, [str(key)])
                d = {}
                shadow[key] = Bunch.Bunch(node=d, item=item, terminal=False)

            # recurse for non-leaf interior node
            for key in node:
                self._add_subtree(level+1, d, model, item, key, node[key])

    def _selection_cb(self, treeview):
        path, column = treeview.get_cursor()
        model = treeview.get_model()
        item = model.get_iter(path)
        res_dict = {}
        self._get_item(res_dict, item)
        self.make_callback('selected', res_dict)

    def _cb_redirect(self, treeview, path, column):
        model = treeview.get_model()
        item = model.get_iter(path)
        res_dict = {}
        self._get_item(res_dict, item)
        self.make_callback('activated', res_dict)

    def _get_path(self, item):
        if item is None:
            return []

        model = self.tv.get_model()
        if not model.iter_has_child(item):
            # child node, so append my name to parent's path
            path_rest = self._get_path(model.iter_parent(item))
            d = model.get_value(item, 0)
            if isinstance(d, str):
                myname = d
            else:
                myname = d[self.leaf_key]
            path_rest.append(myname)
            return path_rest

        # non-leaf node case
        myname = model.get_value(item, 0)
        path_rest = self._get_path(model.iter_parent(item))
        path_rest.append(myname)
        return path_rest

    def _get_item(self, res_dict, item):
        # from the model iter `item`, return the item via a path
        # in the dictionary `res_dict`
        path = self._get_path(item)
        d, s = res_dict, self.shadow
        for name in path[:-1]:
            d = d.setdefault(name, {})
            s = s[name].node

        dst_key = path[-1]
        d[dst_key] = s[dst_key].node

    def get_selected(self):
        treeselection = self.tv.get_selection()
        model, pathlist = treeselection.get_selected_rows()
        res_dict = {}
        for path in pathlist:
            item = model.get_iter(path)
            self._get_item(res_dict, item)
        return res_dict

    def clear(self):
        model = gtk.TreeStore(object)
        self.tv.set_model(model)
        self.shadow = {}

    def clear_selection(self):
        treeselection = self.tv.get_selection()
        treeselection.unselect_all()

    def select_path(self, path):
        treeselection = self.tv.get_selection()
        item = self._path_to_item(path)
        treeselection.select_iter(item)

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)
        # TODO

    def _path_to_item(self, path):
        s = self.shadow
        for name in path[:-1]:
            s = s[name].node
        item = s[path[-1]].item
        return item

    def scroll_to_path(self, path):
        item = self._path_to_item(path)
        model = self.tv.get_model()
        treepath = model.get_path(item)
        self.tv.scroll_to_cell(treepath, use_align=True, row_align=0.5)

    def sort_on_column(self, i):
        model = self.tv.get_model()
        model.set_sort_column_id(i, gtk.SORT_ASCENDING)

    def set_column_width(self, i, width):
        col = self.tv.get_column(i)
        col.set_max_width(width)

    def set_column_widths(self, lwidths):
        for i, width in enumerate(lwidths):
            if width is not None:
                self.set_column_width(i, width)

    def set_optimal_column_widths(self):
        self.tv.columns_autosize()

    def sort_cb(self, column, idx):
        treeview = column.get_tree_view()
        model = treeview.get_model()
        model.set_sort_column_id(idx, gtk.SORT_ASCENDING)
        fn = self.cell_sort_funcs[idx]
        model.set_sort_func(idx, fn)
        return True

    def _mksrtfnN(self, idx):
        def fn(*args):
            model, iter1, iter2 = args[:3]
            bnch1 = model.get_value(iter1, 0)
            bnch2 = model.get_value(iter2, 0)
            if isinstance(bnch1, str):
                if isinstance(bnch2, str):
                    return cmp(bnch1.lower(), bnch2.lower())
                return 0
            val1, val2 = bnch1[idx], bnch2[idx]
            if isinstance(val1, str):
                val1 = val1.lower()
                val2 = val2.lower()
            res = cmp(val1, val2)
            return res
        return fn

    def _mkcolfn0(self, idx):
        def fn(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            if isinstance(bnch, str):
                cell.set_property('text', bnch)
            elif isinstance(bnch, gtk.gdk.Pixbuf):
                cell.set_property('pixbuf', bnch)
            elif isinstance(bnch[idx], gtk.gdk.Pixbuf):
                cell.set_property('pixbuf', bnch[idx])
            else:
                cell.set_property('text', bnch[idx])
        return fn

    def _mkcolfnN(self, idx):
        def fn(*args):
            column, cell, model, iter = args[:4]
            bnch = model.get_value(iter, 0)
            if isinstance(bnch, str):
                cell.set_property('text', '')
            elif isinstance(bnch, gtk.gdk.Pixbuf):
                cell.set_property('text', '')
            elif isinstance(bnch[idx], gtk.gdk.Pixbuf):
                cell.set_property('pixbuf', bnch[idx])
            else:
                cell.set_property('text', bnch[idx])
        return fn

    def _start_drag(self, treeview, context, selection,
                         info, timestamp):
        res_dict = self.get_selected()
        drag_pkg = DragPackage(self.tv, selection)
        self.make_callback('drag-start', drag_pkg, res_dict)
        drag_pkg.start_drag()

# CONTAINERS

class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        self.children = []

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def _remove(self, childw, delete=False):
        self.widget.remove(childw)
        if delete:
            childw.destroy()

    def remove(self, w, delete=False):
        if not w in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(w)

        self._remove(w.get_widget(), delete=delete)

    def remove_all(self, delete=False):
        for w in list(self.children):
            self.remove(w, delete=delete)

    def get_children(self):
        return self.children

    def num_children(self):
        return len(self.children)

    def _get_native_children(self):
        return [child.get_widget() for child in self.children]

    def _get_native_index(self, nchild):
        l = self._get_native_children()
        return l.index(nchild)

    def _native_to_child(self, nchild):
        idx = self._get_native_index(nchild)
        return self.children[idx]

    def set_margins(self, left, right, top, bottom):
        # TODO: can this be made more accurate?
        self.widget.set_border_width(left)

    def set_border_width(self, pix):
        self.widget.set_border_width(pix)


class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        if orientation == 'horizontal':
            self.widget = gtk.HBox()
        else:
            self.widget = gtk.VBox()

    def set_spacing(self, val):
        self.widget.set_spacing(val)

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
    def __init__(self, tabpos='top', reorderable=False, detachable=True,
                 group=0):
        super(TabWidget, self).__init__()

        self.reorderable = reorderable
        self.detachable = detachable

        nb = GtkHelp.Notebook()
        #nb = gtk.Notebook()
        nb.set_show_border(False)
        nb.set_scrollable(True)
        # Allows drag-and-drop between notebooks
        nb.set_group_id(group)
        if self.detachable:
            nb.connect("create-window", self._tab_detach_cb)
        nb.connect("page-added", self._tab_insert_cb)
        nb.connect("page-removed", self._tab_remove_cb)
        nb.sconnect("switch-page", self._cb_redirect)
        #nb.connect("switch-page", self._cb_redirect)
        self.widget = nb
        self.set_tab_position(tabpos)

        for name in ('page-switch', 'page-close', 'page-move', 'page-detach'):
            self.enable_callback(name)

    def set_tab_position(self, tabpos):
        nb = self.widget
        if tabpos == 'top':
            nb.set_tab_pos(gtk.POS_TOP)
        elif tabpos == 'bottom':
            nb.set_tab_pos(gtk.POS_BOTTOM)
        elif tabpos == 'left':
            nb.set_tab_pos(gtk.POS_LEFT)
        elif tabpos == 'right':
            nb.set_tab_pos(gtk.POS_RIGHT)

    def _tab_detach_cb(self, source, nchild_w, x, y):
        child = self._native_to_child(nchild_w)
        # remove child
        # (native widget already has been removed by gtk)
        self.children.remove(child)

        #nchild_w.unparent()
        self.make_callback('page-detach', child)

    def _tab_insert_cb(self, nbw, nchild_w, page_num):
        global _widget_move_event
        if _widget_move_event is not None:
            event, _widget_move_event = _widget_move_event, None
            already_here = nchild_w in self._get_native_children()
            if not already_here and event.child.get_widget() == nchild_w:
                child = event.child
                # remove child from src tab
                # (native widget already has been removed by gtk)
                event.src_widget.children.remove(child)
                # add child to us
                # (native widget already has been added by gtk)
                self.add_ref(child)
                self.make_callback('page-move', event.src_widget, child)

    def _tab_remove_cb(self, nbw, nchild_w, page_num):
        global _widget_move_event
        child = self._native_to_child(nchild_w)
        _widget_move_event = WidgetMoveEvent(self, child)

    def _cb_redirect(self, nbw, gptr, index):
        child = self.index_to_widget(index)
        self.make_callback('page-switch', child)

    def _cb_select(self, widget, event, child):
        self.make_callback('page-switch', child)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        label = gtk.Label(title)
        evbox = gtk.EventBox()
        evbox.props.visible_window = True
        evbox.add(label)
        evbox.show_all()
        evbox.connect("button-press-event", self._cb_select, child)
        self.widget.append_page(child_w, evbox)
        if self.reorderable:
            self.widget.set_tab_reorderable(child_w, True)
        if self.detachable:
            self.widget.set_tab_detachable(child_w, True)
        self.widget.show_all()
        # attach title to child
        child.extdata.tab_title = title

    def get_index(self):
        return self.widget.get_current_page()

    def set_index(self, idx):
        self.widget.set_current_page(idx)

    def index_of(self, child):
        return self.widget.page_num(child.get_widget())

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        nchild = self.widget.get_nth_page(idx)
        return self._native_to_child(nchild)

    def highlight_tab(self, idx, tf):
        nchild = self.widget.get_nth_page(idx)
        evbox = self.widget.get_tab_label(nchild)
        if tf:
            evbox.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse('palegreen'))
        else:
            evbox.modify_bg(gtk.STATE_NORMAL, None)

class StackWidget(TabWidget):
    def __init__(self):
        super(StackWidget, self).__init__()

        nb = self.widget
        #nb.set_scrollable(False)
        nb.set_show_tabs(False)
        nb.set_show_border(False)

class MDIWidget(ContainerBase):

    def __init__(self, tabpos='top', mode='tabs'):
        super(MDIWidget, self).__init__()

        self.mode = 'mdi'
        self.true_mdi = True

        # TODO: currently scrollbars are not working
        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget = sw
        w = GtkHelp.MDIWidget()
        self.mdi_w = w
        w._move_page = w.move_page
        w.move_page = self._window_moved
        w._resize_page = w.resize_page
        w.resize_page = self._window_resized

        sw.set_hadjustment(self.mdi_w.get_hadjustment())
        sw.set_vadjustment(self.mdi_w.get_vadjustment())
        sw.add(self.mdi_w)

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        pass

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        label = gtk.Label(title)
        subwin = self.mdi_w.append_page(child_w, label)
        #self.mdi_w.show_all()
        # attach title to child
        child.extdata.tab_title = title

        # does child have a previously saved size
        size = child.extdata.get('mdi_size', None)
        if size is not None:
            wd, ht = size
            self.mdi_w.resize_page(subwin, wd, ht)

        # does child have a previously saved position
        pos = child.extdata.get('mdi_pos', None)
        if pos is not None:
            x, y = pos
            self.mdi_w.move_page(subwin, x, y)

    def _remove(self, childw, delete=False):
        self.mdi_w.remove(childw)
        if delete:
            childw.destroy()

    def _cb_redirect(self, nbw, gptr, index):
        child = self.index_to_widget(index)
        self.make_callback('page-switch', child)

    def _window_resized(self, subwin, wd, ht):
        self.mdi_w._resize_page(subwin, wd, ht)

        # save size
        nchild = subwin.widget
        child = self._native_to_child(nchild)
        child.extdata.mdi_size = (wd, ht)
        return True

    def _window_moved(self, subwin, x, y):
        self.mdi_w._move_page(subwin, x, y)

        # save position
        nchild = subwin.widget
        child = self._native_to_child(nchild)
        child.extdata.mdi_pos = (x, y)
        return True

    def get_index(self):
        return self.mdi_w.get_current_page()

    def set_index(self, idx):
        self.mdi_w.set_current_page(idx)

    def index_of(self, child):
        return self.mdi_w.page_num(child.get_widget())

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        nchild = self.mdi_w.get_nth_page(idx)
        return self._native_to_child(nchild)

    def tile_panes(self):
        self.mdi_w.tile_pages()

    def cascade_panes(self):
        self.mdi_w.cascade_pages()

    def use_tabs(self, tf):
        pass

class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget = sw

        self.enable_callback('configure')
        sw.connect("size_allocate", self._resize_cb)

    def _resize_cb(self, widget, allocation):
        rect = widget.get_allocation()
        x, y, width, height = rect.x, rect.y, rect.width, rect.height
        self.make_callback('configure', width, height)
        return True

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.add_with_viewport(child.get_widget())
        self.widget.show_all()

    def scroll_to_end(self, vertical=True, horizontal=False):
        if vertical:
            adj_w = self.widget.get_vadjustment()
            maxv = adj_w.get_upper()
            adj_w.set_value(maxv)
        if horizontal:
            adj_w = self.widget.get_hadjustment()
            maxv = adj_w.get_upper()
            adj_w.set_value(maxv)


class Splitter(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Splitter, self).__init__()

        self.orientation = orientation
        self.widget = self._get_pane()
        self.panes = [self.widget]

    def _get_pane(self):
        if self.orientation == 'horizontal':
            w = gtk.HPaned()
        else:
            w = gtk.VPaned()
        return w

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        if len(self.children) == 1:
            self.widget.pack1(child_w)

        else:
            last = self.widget
            if len(self.panes) > 0:
                last = self.panes[-1]

            w = self._get_pane()
            self.panes.append(w)

            w.pack1(child_w)
            last.pack2(w)

        self.widget.show_all()

    def _get_sizes(self, pane):
        rect = pane.get_allocation()
        if self.orientation == 'horizontal':
            total = rect.width
        else:
            total = rect.height
        pos = pane.get_position()
        return (pos, total)

    def get_sizes(self):
        res = []
        if len(self.panes) > 0:
            for pane in self.panes[:-1]:
                pos, total = self._get_sizes(pane)
                res.append(pos)
            pane = self.panes[-1]
            pos, total = self._get_sizes(pane)
            res.append(total)
        return res

    def set_sizes(self, sizes):
        for i, pos in enumerate(sizes):
            pane = self.panes[i]
            pane.set_position(pos)


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        w = gtk.Table(rows=rows, columns=columns)
        self.widget = w
        self.num_rows = rows
        self.num_cols = columns

    def resize_grid(self, rows, columns):
        self.num_rows = rows
        self.num_cols = columns
        self.widget.resize(rows, columns)

    def set_row_spacing(self, val):
        self.widget.set_row_spacings(val)

    def set_column_spacing(self, val):
        self.widget.set_col_spacings(val)

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def add_widget(self, child, row, col, stretch=0):
        resize = False
        if row > self.num_rows:
            resize = True
            self.num_rows = row
        if col > self.num_cols:
            resize = True
            self.num_cols = col
        if resize:
            self.resize_grid(self.num_rows, self.num_cols)

        self.add_ref(child)
        w = child.get_widget()
        if stretch > 0:
            xoptions = gtk.EXPAND|gtk.FILL
            yoptions = gtk.EXPAND|gtk.FILL
        else:
            xoptions = gtk.FILL
            yoptions = gtk.FILL
        self.widget.attach(w, col, col+1, row, row+1,
                           xoptions=xoptions, yoptions=yoptions,
                           xpadding=0, ypadding=0)
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

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        if toggle:
            child = ToggleButton(text)
        else:
            child = Button(text)

        if iconpath is not None:
            wd, ht = 24, 24
            if iconsize is not None:
                wd, ht = iconsize
            pixbuf = GtkHelp.pixbuf_new_from_file_at_size(iconpath, wd, ht)
            if pixbuf is not None:
                image = gtk.image_new_from_pixbuf(pixbuf)
                child.get_widget().set_image(image)

        self.add_widget(child)
        return child

    def add_widget(self, child):
        self.add_ref(child)
        w = child.get_widget()
        self.widget.append_widget(w, None, None)

    def add_menu(self, text, menu=None):
        if menu is None:
            menu = Menu()
        child = self.add_action(text)
        child.add_callback('activated', lambda w: menu.popup())
        return menu

    def add_separator(self):
        self.widget.append_space()


class MenuAction(WidgetBase):
    def __init__(self, text=None, checkable=False):
        super(MenuAction, self).__init__()

        self.text = text
        self.checkable = checkable

        if checkable:
            self.widget = gtk.CheckMenuItem(label=text)
            self.widget.connect('toggled', self._cb_redirect)
        else:
            self.widget = gtk.MenuItem(label=text)
            self.widget.connect('activate', self._cb_redirect)
        self.widget.show()

        self.enable_callback('activated')

    def set_state(self, tf):
        if not self.checkable:
            raise ValueError("Not a checkable menu item")
        self.widget.set_active(tf)

    def get_state(self):
        return self.widget.get_active()

    def _cb_redirect(self, *args):
        if self.checkable:
            tf = self.widget.get_active()
            self.make_callback('activated', tf)
        else:
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

    def add_name(self, name, checkable=False):
        child = MenuAction(text=name, checkable=checkable)
        self.add_widget(child)
        return child

    def add_separator(self):
        sep = gtk.SeparatorMenuItem()
        self.widget.append(sep)
        sep.show()

    def popup(self, widget=None):
        menu = self.widget
        menu.show_all()
        if six.PY2:
            now = long(0)
        else:
            now = int(0)
        menu.popup(None, None, None, 0, now)


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = gtk.MenuBar()
        self.menus = Bunch.Bunch(caseless=True)

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
        self.menus[name] = child
        item_w.set_submenu(child.get_widget())
        self.widget.append(item_w)
        item_w.show()
        return child

    def get_menu(self, name):
        return self.menus[name]


class TopLevelMixin(object):

    def __init__(self, title=None):
        self._fullscreen = False

        self.widget.connect("destroy", self._quit)
        self.widget.connect("delete_event", self._close_event)
        self.widget.connect("window_state_event", self._window_event)
        self.widget.connect("configure-event", self._configure_event)

        if not title is None:
            self.widget.set_title(title)

        self.enable_callback('close')

    def show(self):
        self.widget.show_all()

    def hide(self):
        self.widget.hide()

    def _quit(self, *args):
        self.close()

    def _close_event(self, widget, event):
        try:
            self.close()

        finally:
            # don't automatically destroy window
            return True

    def _window_event(self, widget, event):
        if ((event.changed_mask & gtk.gdk.WINDOW_STATE_FULLSCREEN) or
            (event.changed_mask & gtk.gdk.WINDOW_STATE_MAXIMIZED)):
            self._fullscreen = True
        else:
            self._fullscreen = False

    def _configure_event(self, widget, event):
        x, y, width, height = event.x, event.y, event.width, event.height
        x, y = self.widget.translate_coordinates(self.widget, x, y)
        self.extdata.setvals(x=x, y=y, width=width, height=height)
        return False

    def close(self):
        ## try:
        ##     self.widget.destroy()
        ## except Exception as e:
        ##     pass
        #self.widget = None

        self.make_callback('close')

    def get_size(self):
        window = self.widget.get_window()
        if window is not None:
            rect = self.widget.get_allocation()
            x, y, wd, ht = rect.x, rect.y, rect.width, rect.height

        else:
            # window maybe isn't realized yet--try other ways
            wd, ht = self.widget.size_request()
            ed = self.extdata
            wd, ht = ed.get('width', wd), ed.get('height', ht)

        return wd, ht

    def get_pos(self):
        window = self.widget.get_window()
        if window is not None:
            x, y = window.get_origin()
        else:
            ed = self.extdata
            x, y = ed.get('x', None), ed.get('y', None)

        return x, y

    def raise_(self):
        window = self.widget.get_window()
        window.raise_()

    def lower(self):
        window = self.widget.get_window()
        window.lower()

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

    def is_fullscreen(self):
        return self._fullscreen

    def iconify(self):
        window = self.widget.get_window()
        window.iconify()

    def uniconify(self):
        window = self.widget.get_window()
        window.deiconify()

    def set_title(self, title):
        self.widget.set_title(title)


class TopLevel(TopLevelMixin, ContainerBase):

    def __init__(self, title=None):
        ContainerBase.__init__(self)

        self._fullscreen = False

        widget = GtkHelp.TopLevel()
        self.widget = widget
        widget.set_border_width(0)

        TopLevelMixin.__init__(self, title=title)

    def set_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.add(child_w)


class Application(Callback.Callbacks):

    def __init__(self, logger=None):
        global _app
        super(Application, self).__init__()

        self.logger = logger
        self.window_list = []

        self.window_dict = {}
        self.wincnt = 0

        try:
            screen = gtk.gdk.screen_get_default()
            self.screen_ht = screen.get_height()
            self.screen_wd = screen.get_width()
        except:
            self.screen_wd = 1600
            self.screen_ht = 1200
        ## self.logger.debug("screen dimensions %dx%d" % (
        ##     self.screen_wd, self.screen_ht))

        _app = self

        for name in ('shutdown', ):
            self.enable_callback(name)

        # Set up Gtk style
        GtkHelp.set_default_style()

    def get_screen_size(self):
        return (self.screen_wd, self.screen_ht)

    def process_events(self):
        while gtk.events_pending():
            #gtk.main_iteration(False)
            gtk.main_iteration()

    def process_end(self):
        pass

    def add_window(self, window, wid=None):
        if wid is None:
            wid = 'win%d' % (self.wincnt)
            self.wincnt += 1
        window.wid = wid
        window.url = ''
        window.app = self

        self.window_dict[wid] = window

    def get_window(self, wid):
        return self.window_dict[wid]

    def has_window(self, wid):
        return wid in self.window_dict

    def get_wids(self):
        return list(self.window_dict.keys())

    def make_window(self, title=None):
        w = TopLevel(title=title)
        self.add_window(w)
        return w

    def mainloop(self):
        gtk.main()


class Dialog(TopLevelMixin, WidgetBase):

    def __init__(self, title='', flags=0, buttons=[],
                 parent=None, modal=False):
        WidgetBase.__init__(self)

        if parent is not None:
            self.parent = parent.get_widget()
        else:
            self.parent = None

        button_list = []
        for name, val in buttons:
            button_list.extend([name, val])

        self.widget = gtk.Dialog(title=title, flags=flags,
                                 buttons=tuple(button_list))
        self.widget.set_modal(modal)

        TopLevelMixin.__init__(self, title=title)

        self.content = VBox()
        self.content.set_border_width(0)
        content = self.widget.get_content_area()
        content.pack_start(self.content.get_widget(), fill=True, expand=True)

        self.widget.connect("response", self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, w, val):
        self.make_callback('activated', val)

    def get_content_area(self):
        return self.content


class SaveDialog(object):
    def __init__(self, title='Save File', selectedfilter=None):
        action = gtk.FILE_CHOOSER_ACTION_SAVE
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                   gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        self.widget = gtk.FileChooserDialog(title=title, action=action,
                                            buttons=buttons)
        self.selectedfilter = selectedfilter

        if selectedfilter is not None:
            self._add_filter(selectedfilter)

    def _add_filter(self, selectedfilter):
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
            if self.selectedfilter is not None and not path.endswith(self.selectedfilter):
                path += self.selectedfilter
            self.widget.destroy()
            return path
        elif response == gtk.RESPONSE_CANCEL:
            self.widget.destroy()
            return None

class DragPackage(object):
    def __init__(self, src_widget, selection):
        self.src_widget = src_widget
        self._selection = selection

    def set_urls(self, urls):
        self._selection.set_uris(urls)
        self._selection.set("text/plain", 0, '\n'.join(urls))

    def start_drag(self):
        pass

class WidgetMoveEvent(object):
    def __init__(self, src_widget, child):
        self.src_widget = src_widget
        self.child = child
        self._result = False

    def accept(self):
        self._result = True

    def reject(self):
        self._result = False

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
        w.label.set_alignment(0.95, 0.5)
    elif wtype == 'llabel':
        w = Label(title)
        w.label.set_alignment(0.05, 0.95)
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
    elif wtype == 'progress':
        w = ProgressBar()
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
    numcols = int(numcols // 2)
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
    ## wd, ht = container.get_size()
    #print('container size is %dx%d' % (wd, ht))
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

    box2.add_widget(box1, stretch=1)
    if not fill:
        box2.add_widget(Label(''), stretch=1)
    if scrolled:
        sw = ScrollArea()
        sw.set_widget(box2)
    else:
        sw = box2

    return box1, sw, orientation

#END
