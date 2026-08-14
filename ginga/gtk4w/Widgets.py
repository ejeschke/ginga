#
# Widgets.py -- wrapped Gtk widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#

import contextlib
import uuid
import pathlib
import os
from functools import reduce

from ginga.gtk4w import GtkHelp
from ginga.gtk4w import _columnview
from ginga.util import treehelper
from ginga.gtk4w.GtkHelp import Timer  # noqa
from ginga import colors
from ginga.util.paths import icondir as ginga_icon_dir
from ginga.misc import Callback, Bunch, Settings, LineHistory
from ginga.util.paths import icondir, app_icon_path
from ginga.fonts import font_asst
from ginga.gw.widget_helpers import DIALOG_FLAGS_ONTOP
from ginga.util.syncops import Shelf
from ginga.locale.localize import translate_caption, _tr

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import GObject

__all__ = ['WidgetError', 'Widget', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'Label', 'HSeparator', 'VSeparator',
           'Button', 'ComboBox', 'Timer',
           'SpinBox', 'Slider', 'Dial', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'ProgressBar', 'StatusBar', 'TreeView',
           'TableView', 'ContainerBase', 'Box', 'HBox', 'VBox', 'Frame',
           'Expander', 'TabWidget', 'StackWidget', 'MDIWidget', 'ScrollArea',
           'Splitter', 'GridBox', 'Toolbar', 'MenuAction',
           'Menu', 'Menubar', 'TopLevelMixin', 'TopLevel', 'Application',
           'Dialog', 'SaveDialog', 'ColorDialog', 'FileDialog', 'MessageDialog',
           'DragPackage', 'WidgetMoveEvent', 'name_mangle', 'make_widget',
           'hadjust', 'build_info', 'wrap']


_TABLE_VIEW_ROW_NUM_KEY = '_row_num_'

# Recognised values for the ``widget`` field of a column descriptor
# — kept in sync with the same constant in the qtw / pgw / gtk3w
# wrappers.  The gtk4 backend records the field on the normalised
# column dict but doesn't act on it yet (phase 4 will wire it).
_CELL_WIDGETS = ('checkbox', 'combobox', 'progress', 'button')


def _coerce_bool(s):
    if isinstance(s, bool):
        return s
    if isinstance(s, (int, float)):
        return bool(s)
    if isinstance(s, str):
        return s.strip().lower() in ('1', 'true', 't', 'yes', 'y', 'on', '✓')
    return bool(s)


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
        self._widget_name = f"W{id(self)}"
        # external data can be attached here
        self.extdata = Bunch.Bunch()

    def get_widget(self):
        return self.widget

    def batch(self):
        """Group a burst of updates so the backend can apply them as one.

        Backends that ship updates to a remote view (currently ``pg``,
        which drives a browser over a websocket) send everything done
        inside the block as a single message and redraw once, instead of
        one message and one redraw per call.  That makes a bulk update --
        rewriting a few hundred cells of a tree, say -- cost about what
        one update costs.

        On the desktop backends there is nothing to coalesce, so this is
        a no-op context manager.  It is defined on every backend so
        application code can use it unconditionally::

            with tree.batch():
                for path, col_key, value in changes:
                    tree.set_cell(path, col_key, value)
        """
        return contextlib.nullcontext()

    def set_tooltip(self, text):
        self.widget.set_tooltip_text(text)

    def set_bg(self, color):
        """Set the widget's background colour.  ``color`` is a CSS
        string (``'#rrggbb'``, ``'red'``, ``'rgba(...)'``, …) or
        ``None`` to clear the override.

        Implemented via ``GtkHelp.modify_bg``, which attaches a
        per-widget ``CssProvider`` to the widget's style context
        with a class-scoped rule — so it works on transparent
        containers (``Gtk.Box``, ``Gtk.Grid``) too.

        Themed widgets paint multi-state backgrounds; a generic
        ``set_bg`` may be partially overridden by hover / active
        states on those."""
        GtkHelp.modify_bg(self.widget, color)

    def get_enabled(self):
        return self.widget.get_sensitive()

    def set_enabled(self, tf):
        self.widget.set_sensitive(tf)

    def set_margins(self, left, right, top, bottom):
        self.widget.set_margin_start(left)
        self.widget.set_margin_end(right)
        self.widget.set_margin_top(top)
        self.widget.set_margin_bottom(bottom)

    def set_padding(self, px):
        if isinstance(px, int):
            self.set_margins(px, px, px, px)
        else:
            self.set_margins(*px)

    def is_container(self):
        return False

    def get_size(self):
        try:
            wd = self.widget.get_width()
            ht = self.widget.get_height()
            if wd == 0 or ht == 0:
                wd, ht = self.widget.get_size_request()
                if int(wd + ht) <= 0:
                    raise Exception("No size yet")

        except Exception:
            # window maybe isn't realized yet--try other ways
            min_req, nat_req = self.widget.get_preferred_size()
            wd, ht = nat_req.width, nat_req.height

            # wd, ht = max(1, wd), max(1, ht)
        return wd, ht

    def get_pos(self):
        rect = GtkHelp.widget_allocation(self.widget)
        x, y = rect.x, rect.y
        return x, y

    def get_app(self):
        return _app

    def delete(self):
        #self.widget.destroy()
        #self.hide()
        self.widget.unrealize()
        self.widget = None

    def show(self):
        self.widget.set_visible(True)

    def hide(self):
        self.widget.set_visible(False)

    def is_visible(self):
        return self.widget.get_visible()

    def focus(self):
        self.widget.grab_focus()

    def resize(self, width, height):
        self.widget.set_size_request(width, height)

        # hackish way to allow the widget to be resized down again later
        # NOTE: this may cause some problems for sizing certain widgets
        if width > 0 and height > 0:
            #GLib.idle_add(self.widget.set_size_request, -1, -1)
            pass

    def set_min_size(self, wd, ht):
        if wd is None:
            # sentinal for unrestricted
            wd = -1
        if ht is None:
            # sentinal for unrestricted
            ht = -1
        self.widget.set_size_request(wd, ht)

    def set_max_size(self, wd, ht):
        # NOTE: no direct equivalent in Gtk
        pass

    def get_font(self, font_family, point_size):
        font = GtkHelp.get_font(font_family, point_size)
        return font

    def _set_name(self, obj):
        name = f"W{id(obj)}"
        self._widget_name = name
        obj.set_name(name)
        return name

    def _get_name(self):
        return self._widget_name

    def cfg_expand(self, horizontal='fixed', vertical='fixed'):
        # this is for compatibility with Qt widgets
        pass

    def set_expanding(self, horizontal=False, vertical=False):
        # NOTE: no direct equivalent in Gtk
        pass

    def set_border_width(self, pix):
        GtkHelp.set_border_width(self.widget, pix)

    def get_rgb_array(self):
        return GtkHelp.get_rgb_array(self.widget)


Widget = WidgetBase

# BASIC WIDGETS


class TextEntry(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntry, self).__init__()

        w = Gtk.Entry()
        w.set_hexpand(True)
        w.set_halign(Gtk.Align.FILL)
        w.set_text(text)
        w.set_editable(editable)
        # TODO
        #w.connect('key-press-event', self._key_press_event)
        w.connect('activate', self._cb_redirect)
        self.widget = w

        self.history = LineHistory.LineHistory()

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.history.append(self.get_text())
        self.make_callback('activated')

    def _key_press_event(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
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

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO
        #self.widget.modify_font(font)

    def set_length(self, numchars):
        # this only sets the visible length of the widget
        self.widget.set_width_chars(numchars)
        pass


class TextEntrySet(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntrySet, self).__init__()

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.set_spacing(4)
        w = Gtk.Entry()
        w.set_hexpand(True)
        w.set_halign(Gtk.Align.FILL)
        w.set_text(text)
        w.set_editable(editable)
        hbox.append(w)
        w.connect('activate', self._cb_redirect)
        self.entry = w
        w = Gtk.Button(label=_tr('Set'))
        w.connect('clicked', self._cb_redirect)
        hbox.append(w)
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

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO
        #self.widget.modify_font(font)

    def set_length(self, numchars):
        # self.widget.set_width_chars(numchars)
        pass

    def set_enabled(self, tf):
        super(TextEntrySet, self).set_enabled(tf)
        self.entry.set_sensitive(tf)


class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        tw = Gtk.TextView()
        if wrap:
            tw.set_wrap_mode(Gtk.WrapMode.WORD)
        else:
            tw.set_wrap_mode(Gtk.WrapMode.NONE)
        tw.set_editable(editable)
        self.tw = tw

        # this widget has a built in ScrollArea to match Qt functionality
        sw = Gtk.ScrolledWindow()
        GtkHelp.set_border_width(sw, 2)
        sw.set_has_frame(True)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(self.tw)
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
        # self.tw.scroll_to_iter(end, 0.5)
        # NOTE: this was causing a segfault if the text widget is
        # not mapped yet!  Seems to be fixed in recent versions of
        # gtk
        buf.move_mark(mark, end)
        res = self.tw.scroll_to_mark(mark, 0.2, False, 0.0, 0.0)  # noqa

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
            end = buf.get_iter_at_line(rmcount)
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

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO
        #self.tw.modify_font(font)

    def set_wrap(self, kind):
        d = {'none': Gtk.WrapMode.NONE,
             'char': Gtk.WrapMode.CHAR,
             'word': Gtk.WrapMode.WORD,
             'full': Gtk.WrapMode.WORD_CHAR,
             }
        if isinstance(kind, bool):
            # <-- old API interface
            self.tw.set_wrap_mode(d['word' if kind else 'none'])
        else:
            self.tw.set_wrap_mode(d[kind])

    def set_scroll_pos(self, pos):
        vadj = self.widget.get_vadjustment()
        if pos == -1:
            vadj.set_value(vadj.get_upper())
        else:
            vadj.set_value(pos)


class Label(WidgetBase):
    def __init__(self, text='', halign='left', style='normal', menu=None):
        super(Label, self).__init__()

        label = Gtk.Label(label=text)
        pad = 2
        GtkHelp.set_border_width(label, pad)

        if halign == 'left':
            label.set_justify(Gtk.Justification.LEFT)
        elif halign == 'center':
            label.set_justify(Gtk.Justification.CENTER)
        elif halign == 'right':
            label.set_justify(Gtk.Justification.RIGHT)

        self.label = label
        self.menu = menu

        if style == 'clickable':
            gesture = Gtk.GestureClick.new()
            gesture.connect("pressed", self._cb_redirect)
            # all buttons
            gesture.set_button(0)
            label.add_controller(gesture)
            self.enable_callback('activated')

            fr = Gtk.Frame()
            fr.set_child(label)
            self.frame = fr
            self.widget = fr
        else:
            self.widget = label

        if style == 'clickable' or menu is not None:
            gesture = Gtk.GestureClick.new()
            gesture.connect("released", self._cb_redirect)
            # all buttons
            gesture.set_button(3)
            label.add_controller(gesture)
            self.enable_callback('released')

    def _cb_redirect(self, event, n_clicks, x, y):
        event_button = event.get_current_button()
        if event_button == 1:
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self.make_callback('activated')
            return True

        elif event_button == 3 and self.menu is not None:
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self.menu.popup(self)
            return True

        event.set_state(Gtk.EventSequenceState.DENIED)
        return False

    def _cb_redirect2(self, event, n_clicks, x, y):
        event_button = event.get_current_button()
        if event_button == 1:
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self.make_callback('released')
            return True

        event.set_state(Gtk.EventSequenceState.DENIED)
        return False

    def get_text(self):
        return self.label.get_text()

    def set_text(self, text):
        self.label.set_text(text)

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO
        #self.label.modify_font(font)

    def set_color(self, fg=None, bg=None):
        if bg is not None:
            GtkHelp.modify_bg(self.widget, bg)
        if fg is not None:
            # set the label text colour via CSS; GTK4 removed both
            # modify_fg() and Gtk.StateType
            GtkHelp.modify_fg(self.label, fg)

    def set_halign(self, align):
        align = align.lower()
        if align == 'left':
            self.label.set_justify(Gtk.Justification.LEFT)
        elif align == 'center':
            self.label.set_justify(Gtk.Justification.CENTER)
        elif align == 'right':
            self.label.set_justify(Gtk.Justification.RIGHT)
        else:
            raise ValueError(f"Don't understand alignment '{align}'")

    def set_valign(self, align):
        align = align.lower()
        # GtkWidget's valign property positions the label within
        # whatever vertical space the parent allocates — only
        # visible when the parent gives the label more height
        # than the text needs (e.g. inside a stretched Box cell).
        if align == 'top':
            gtk_align = Gtk.Align.START
        elif align == 'center':
            gtk_align = Gtk.Align.CENTER
        elif align == 'bottom':
            gtk_align = Gtk.Align.END
        else:
            raise ValueError(f"Don't understand alignment '{align}'")
        self.label.set_valign(gtk_align)


class HSeparator(WidgetBase):
    """A thin horizontal rule.

    TODO: implement with Gtk.Separator(orientation=HORIZONTAL); for now this
    is a no-op placeholder (an empty label) so the gtk4 backend stays usable.
    """
    def __init__(self):
        super().__init__()
        self.widget = Gtk.Label()


class VSeparator(WidgetBase):
    """A thin vertical rule.

    TODO: implement with Gtk.Separator(orientation=VERTICAL); no-op
    placeholder for now.
    """
    def __init__(self):
        super().__init__()
        self.widget = Gtk.Label()


class Button(WidgetBase):

    # Class-level default hover colors; a button snapshots these at
    # construction, so bracketing UI creation with set_hover_color(bg, fg)
    # ... set_hover_color(None, None) gives just those buttons a hover
    # highlight.  See set_hover_color().
    _hover_bg = None
    _hover_fg = None

    def __init__(self, text=None, iconpath=None, iconsize=None):
        super(Button, self).__init__()

        w = Gtk.Button()
        self.widget = w
        if iconpath is not None:
            self.set_icon(iconpath, iconsize=iconsize)

        if text is not None:
            self.widget.set_label(text)

        self._set_name(w)
        w.connect('clicked', self._cb_redirect)

        self._bg = None
        self._fg = None
        self._hover_bg = Button._hover_bg
        self._hover_fg = Button._hover_fg
        self._css_provider = None

        self.enable_callback('activated')

        self._apply_style()

    @classmethod
    def set_hover_color(cls, bg=None, fg=None):
        """Set the default hover background/foreground for buttons created
        *after* this call; pass ``(None, None)`` to clear it.  Bracket the
        creation of a group of buttons to give just those buttons a hover
        highlight."""
        cls._hover_bg = bg
        cls._hover_fg = fg

    def set_text(self, text):
        self.widget.set_label(text)

    def get_text(self):
        return self.widget.get_label()

    def set_icon(self, iconpath, iconsize=None):
        wd, ht = 24, 24
        if iconsize is not None:
            wd, ht = iconsize
        iconw = GtkHelp.get_icon(iconpath, size=(wd, ht))
        self.widget.set_image(iconw)

    def set_color(self, bg=None, fg=None):
        """Set this button's base background/foreground."""
        self._bg = bg
        self._fg = fg
        self._apply_style()

    def set_hover(self, bg=None, fg=None):
        """Override this button's hover background/foreground (independent of
        the class-level default); pass ``(None, None)`` to clear it."""
        self._hover_bg = bg
        self._hover_fg = fg
        self._apply_style()

    def _shaded_bg(self, color):
        # A subtle top-lighter / bottom-darker vertical gradient, so the fill
        # reads as shaded rather than flat.
        r, g, b = colors.resolve_color(color)[:3]
        top = colors.get_hex((min(1.0, r + 0.10), min(1.0, g + 0.10),
                              min(1.0, b + 0.10)))
        bot = colors.get_hex((max(0.0, r - 0.10), max(0.0, g - 0.10),
                              max(0.0, b - 0.10)))
        return "linear-gradient(to bottom, {} 0%, {} 100%)".format(top, bot)

    def _style_props(self, bg, fg):
        parts = []
        if bg is not None:
            parts.append("background-image: {};".format(self._shaded_bg(bg)))
        if fg is not None:
            parts.append("color: {};".format(
                colors.get_hex(colors.resolve_color(fg))))
        return " ".join(parts)

    def _apply_style(self):
        myname = self._get_name()
        rules = []
        base = self._style_props(self._bg, self._fg)
        if len(base) > 0:
            rules.append("*.%s { %s }" % (myname, base))
        hover = self._style_props(self._hover_bg, self._hover_fg)
        if len(hover) > 0:
            rules.append("*.%s:hover { %s }" % (myname, hover))
        if len(rules) == 0 and self._css_provider is None:
            return
        self.widget.add_css_class(myname)
        css_data = "\n".join(rules) if len(rules) > 0 else "*.%s {}" % myname
        # NB: installed on the display, not on the widget -- GTK4
        # deprecated the per-widget provider.  The rules are scoped by
        # ``myname``, which this widget alone carries, so they reach
        # exactly as far as they did before.
        GtkHelp.set_widget_css(self.widget, 'style', css_data)
        self._css_provider = True

    def _cb_redirect(self, *args):
        self.make_callback('activated')


class ComboBox(WidgetBase):
    def __init__(self, editable=False):
        super(ComboBox, self).__init__()

        cb = GtkHelp.ComboBox(has_entry=editable)
        liststore = Gtk.ListStore(GObject.TYPE_STRING)
        cb.set_model(liststore)
        cell = Gtk.CellRendererText()
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)
        if editable:
            cb.set_entry_text_column(0)
            # ENTER in the entry commits the typed value (see
            # _entry_activate_cb); typing alone must not fire 'activated'
            cb.get_child().connect('activate', self._entry_activate_cb)
        self.widget = cb
        self.widget.sconnect('changed', self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        idx = widget.get_active()
        # Only fire on a real selection.  For an editable combo box, typing
        # in the entry also emits 'changed' but leaves the active index at
        # -1; ENTER there is handled by _entry_activate_cb.
        if idx >= 0:
            self.make_callback('activated', idx)

    def _entry_activate_cb(self, entry):
        # ENTER in the editable entry commits the typed value: resolve it to
        # a model index, appending it (like the Qt backend) if it is a new
        # value, so the index reported to 'activated' is valid and
        # consistent with get_text()/get_index().  set_active() masks its
        # own 'changed' (GtkHelp.ComboBox), so this does not re-enter
        # _cb_redirect.
        idx = self.get_index()
        if idx < 0:
            self.append_text(entry.get_text())
            idx = len(self.widget.get_model()) - 1
        self.widget.set_active(idx)
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
        model.insert(j + 1, tup)

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
        if self.widget.get_has_entry():
            entry = self.widget.get_entry()
            entry.set_text('')

    def set_text(self, text):
        model = self.widget.get_model()
        for i in range(len(model)):
            if model[i][0] == text:
                self.widget.set_active(i)
                return

        if self.widget.get_has_entry():
            entry = self.widget.get_child()
            entry.set_text(text)

    # to be deprecated someday
    show_text = set_text

    def set_index(self, index):
        self.widget.set_active(index)

    def get_index(self):
        if self.widget.get_has_entry():
            # Return the index of the item matching the current (possibly
            # typed) text, or -1 if it is not one of the offerings -- e.g. a
            # new value typed but not committed with ENTER.
            text = self.get_text()
            model = self.widget.get_model()
            for i in range(len(model)):
                if model[i][0] == text:
                    return i
            return -1

        return self.widget.get_active()

    def get_text(self):
        if self.widget.get_has_entry():
            entry = self.widget.get_child()
            return entry.get_text()

        idx = self.get_index()
        return self.get_alpha(idx)


class SpinBox(WidgetBase):
    def __init__(self, dtype=int):
        super(SpinBox, self).__init__()

        self.dtype = dtype
        self.widget = GtkHelp.SpinButton()
        self.widget.sconnect('value-changed', self._cb_redirect)

        self.enable_callback('value-changed')

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
    def __init__(self, orientation='horizontal', dtype=int, track=False):
        super(Slider, self).__init__()

        # NOTE: parameter dtype is ignored for now for gtk4

        if orientation == 'horizontal':
            w = GtkHelp.Scale(orientation=Gtk.Orientation.HORIZONTAL)
            # TEMP: hack because scales don't seem to expand as expected
            w.set_size_request(200, -1)
        else:
            w = GtkHelp.Scale(orientation=Gtk.Orientation.VERTICAL)
            w.set_size_request(-1, 200)
        self.widget = w

        w.set_draw_value(True)
        w.set_value_pos(Gtk.PositionType.BOTTOM)
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
            # self.widget.set_update_policy(Gtk.UPDATE_CONTINUOUS)
            pass
        else:
            # self.widget.set_update_policy(Gtk.UPDATE_DISCONTINUOUS)
            pass

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget.get_adjustment()
        adj.configure(minval, minval, maxval, incr_value, incr_value, 0)


class Dial(WidgetBase):
    def __init__(self, dtype=float, wrap=False, track=False):
        super(Dial, self).__init__()

        w = GtkHelp.ValueDial()
        self.widget = w

        w.draw_value = False
        w.wrap = wrap
        w.set_tracking(track)
        w.connect('value-changed', self._cb_redirect)
        self.dtype = dtype

        self.enable_callback('value-changed')

    def _cb_redirect(self, dial, val):
        ext_val = self.dtype(val)
        self.make_callback('value-changed', ext_val)

    def get_value(self):
        int_val = self.widget.get_value()
        return self.dtype(int_val)

    def set_value(self, val):
        self.widget.set_value(val)

    def set_tracking(self, tf):
        self.widget.set_tracking(tf)

    def set_limits(self, minval, maxval, incr_value=1):
        self.widget.set_limits(minval, maxval, incr_value)


class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        if orientation == 'horizontal':
            self.widget = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL)
        else:
            self.widget = Gtk.Scrollbar(orientation=Gtk.Orientation.VERTICAL)
        self.widget.set_range(0.0, 100.0)
        self.widget.connect('value-changed', self._cb_redirect)

        self.enable_callback('activated')

    def set_value(self, value):
        flt_val = value * 100.0
        self.widget.set_value(flt_val)

    def get_value(self):
        return self.widget.get_value() / 100.0

    def _cb_redirect(self, range):
        val = range.get_value() / 100.0
        self.make_callback('activated', val)


class CheckBox(WidgetBase):
    def __init__(self, text=''):
        super(CheckBox, self).__init__()

        self.widget = GtkHelp.CheckButton(label=text)
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

        w = GtkHelp.ToggleButton(label=text)
        #w.set_mode(True)
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

        self.widget = GtkHelp.RadioButton(label=text)
        if group is not None:
            group_w = group.get_widget()
            self.widget.set_group(group_w)

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

    @classmethod
    def get_native_image_from_file(cls, iconpath, size=None, adjust_width=True):
        return GtkHelp.get_image(iconpath, size=size,
                                 adjust_width=adjust_width)

    def __init__(self, native_image=None, style='normal', menu=None):
        super(Image, self).__init__()

        self.image = Gtk.Picture()
        if native_image is not None:
            GtkHelp.picture_set_pixbuf(self.image, native_image)
        self.image.set_property("has-tooltip", True)
        gesture = Gtk.GestureClick.new()
        gesture.connect("pressed", self._cb_redirect1)
        # all buttons
        gesture.set_button(0)
        self.image.add_controller(gesture)
        gesture = Gtk.GestureClick.new()
        gesture.connect("released", self._cb_redirect2)
        # all buttons
        gesture.set_button(0)
        self.image.add_controller(gesture)
        self._action = None
        self.menu = menu
        self.widget = self.image

        # State for animating multi-frame images (e.g. animated GIFs).
        # GTK4's Gtk.Picture has no set_from_animation, so we drive a
        # GdkPixbuf.PixbufAnimationIter ourselves on a GLib timeout.
        self._anim = None
        self._anim_iter = None
        self._anim_timer = None
        # pause/resume the animation with the widget's on-screen lifetime so
        # the timeout doesn't keep firing (and keep the widget alive) after
        # it is gone
        self.image.connect("realize", self._resume_animation)
        self.image.connect("unrealize", self._pause_animation)

        self.enable_callback('activated')

    def _cb_redirect1(self, event, n_clicks, x, y):
        event_button = event.get_current_button()
        if event_button == 1:
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self._action = 'click'

        elif event_button == 3 and self.menu is not None:
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self.menu.popup(self)
            return

        event.set_state(Gtk.EventSequenceState.DENIED)
        return False

    def _cb_redirect2(self, event, n_clicks, x, y):
        event_button = event.get_current_button()
        if (event_button == 1) and (self._action == 'click'):
            event.set_state(Gtk.EventSequenceState.CLAIMED)
            self._action = None
            self.make_callback('activated')
            return True

        event.set_state(Gtk.EventSequenceState.DENIED)
        return False

    def _set_image(self, native_image):
        # native_image may be a PixbufAnimation (animated) or something with
        # a get_pixbuf() (static)
        if isinstance(native_image, GdkPixbuf.PixbufAnimation):
            if native_image.is_static_image():
                self._stop_animation()
                GtkHelp.picture_set_pixbuf(self.image, native_image.get_static_image())
            else:
                self._start_animation(native_image)
        else:
            self._stop_animation()
            GtkHelp.picture_set_pixbuf(self.image, native_image.get_pixbuf())

    def load_file(self, img_path, format=None):
        # format ignored at present.  GTK4's Gtk.Picture has no
        # set_from_animation, so for a multi-frame (animated) image we drive
        # the frames ourselves; otherwise fall back to a static pixbuf.
        anim = GdkPixbuf.PixbufAnimation.new_from_file(img_path)
        if anim.is_static_image():
            self._stop_animation()
            pixbuf = GtkHelp.pixbuf_new_from_file(img_path)
            GtkHelp.picture_set_pixbuf(self.image, pixbuf)
        else:
            self._start_animation(anim)

    def _start_animation(self, anim):
        self._stop_animation()
        self._anim = anim
        # None => start from the current time
        self._anim_iter = anim.get_iter(None)
        self._schedule_frame()

    def _schedule_frame(self):
        it = self._anim_iter
        if it is None:
            return
        texture = GtkHelp.texture_from_pixbuf(it.get_pixbuf())
        self.image.set_paintable(texture)
        delay = it.get_delay_time()   # ms until next frame, -1 if none
        if delay < 0:
            return
        # avoid a busy loop on frames that report a zero/tiny delay
        delay = max(delay, 20)
        self._anim_timer = GLib.timeout_add(delay, self._advance_anim)

    def _advance_anim(self):
        self._anim_timer = None
        if self._anim_iter is None:
            return False
        self._anim_iter.advance(None)
        # shows the next frame and reschedules itself with its delay
        self._schedule_frame()
        return False

    def _pause_animation(self, *args):
        # stop the timeout but keep the animation state so it can resume
        if self._anim_timer is not None:
            GLib.source_remove(self._anim_timer)
            self._anim_timer = None

    def _resume_animation(self, *args):
        if self._anim_iter is not None and self._anim_timer is None:
            self._schedule_frame()

    def _stop_animation(self):
        self._pause_animation()
        self._anim = None
        self._anim_iter = None


class ProgressBar(WidgetBase):
    def __init__(self):
        super(ProgressBar, self).__init__()

        w = Gtk.ProgressBar()
        # GTK3
        # w.set_orientation(Gtk.Orientation.HORIZONTAL)
        # w.set_inverted(False)
        self.widget = w

    def set_value(self, pct):
        pct = float(pct)
        self.widget.set_fraction(pct)
        self.widget.set_text("%.2f %%" % (pct * 100.0))


class StatusBar(WidgetBase):
    def __init__(self):
        super(StatusBar, self).__init__()

        sbar = Gtk.Statusbar()
        self.ctx_id = None
        self.widget = sbar
        self.statustask = None

    def clear_message(self):
        self.statustask = None
        if self.ctx_id is not None:
            try:
                self.widget.remove_all(self.ctx_id)
            except Exception:
                pass
            self.ctx_id = None

    def set_message(self, msg_str, duration=10.0):
        try:
            if self.ctx_id is not None:
                self.widget.remove_all(self.ctx_id)
        except Exception:
            pass
        self.ctx_id = self.widget.get_context_id('status')
        self.widget.push(self.ctx_id, msg_str)

        # remove message in about `duration` seconds
        if self.statustask is not None:
            GObject.source_remove(self.statustask)
            self.statustask = None
        if duration > 0.0:
            self.statustask = GLib.timeout_add(int(1000 * duration),
                                               self.clear_message)


class TreeView(_columnview.ColumnViewTreeMixin, WidgetBase):
    """A tree/table view built on Gtk.ColumnView.

    Same API as the other backends -- see the qt and pg wrappers -- but
    without GtkTreeView, which is deprecated in GTK4 and cannot host a
    real widget per cell.  Here each cell is a genuine widget, so an
    editable cell, a check button or a drop-down is usable directly
    rather than appearing only once the cell is activated.
    """

    def __init__(self, auto_expand=False, sortable=False,
                 selection='single', use_alt_row_color=False,
                 dragable=False):
        WidgetBase.__init__(self)

        self.dragable = dragable
        self.cell_pad_px = 0
        self.row_pad_px = 0
        self.col_pad_px = 0
        self.editable = False
        self._css = None
        self._css_name = 'ginga-tree-%d' % (id(self),)
        self._css_decls = {}
        self._css_display = None
        self._css_realize_id = None
        self._alt_row_colors = use_alt_row_color

        for cbname in ('selected', 'activated', 'drag-start', 'collapsed',
                       'expanded', 'changed', 'sorted', 'cell_edited',
                       'cell_action', 'cell_selected', 'scrolled',
                       'copy', 'cut', 'paste'):
            self.enable_callback(cbname)

        self._cv_init(selection=selection, auto_expand=auto_expand,
                      sortable=sortable,
                      use_alt_row_color=use_alt_row_color)
        self.cv.add_css_class(self._css_name)
        # start compact, like the other backends; set_cell_padding()
        # and friends adjust from here
        self._apply_css()

    # ----- the remainder of the portable API ------------------------

    def delete_tree(self, tree_dict, prune_empty=True):
        """Delete the nodes named by `tree_dict`.

        A key mapping to an empty dict removes that node and its
        subtree; a non-empty one is descended into.  With `prune_empty`
        a branch left childless goes as well.
        """
        removed = self._delete_spec(self.store, tree_dict or {},
                                    prune_empty)
        if removed > 0:
            self._refresh_bound_cells()
            self.make_callback('changed')
        return removed

    def _delete_spec(self, store, spec, prune_empty):
        removed = 0
        for key, sub in (spec or {}).items():
            row = None
            for candidate in store:
                if candidate.key == key:
                    row = candidate
                    break
            if row is None:
                continue
            descend = (isinstance(sub, dict) and len(sub) > 0
                       and row.children is not None
                       and row.children.get_n_items() > 0)
            if not descend:
                store.remove(_columnview._position_of(store, row))
                removed += 1
                continue
            removed += self._delete_spec(row.children, sub, prune_empty)
            if prune_empty and row.children.get_n_items() == 0:
                store.remove(_columnview._position_of(store, row))
                removed += 1
        return removed

    # ----- appearance -----------------------------------------------
    #
    # ColumnView is styled with CSS rather than by setting properties
    # on cell renderers, so these translate to a stylesheet on the
    # widget.

    def _apply_css(self, **decls):
        """Restyle this view.

        The rules are scoped to a class carried by this widget alone, so
        one tree's font or padding doesn't leak into every other
        ColumnView in the application.

        Row height needs saying explicitly: GTK4's theme gives cells a
        min-height, and the widgets living in them (a check button, an
        editable label) bring their own, so rows come out much taller
        than the qt and pg backends unless both are relaxed.
        """
        self._css_decls = getattr(self, '_css_decls', {})
        self._css_decls.update(decls)
        font = ' '.join(f'{k}: {v};' for k, v in self._css_decls.items()
                        if v is not None and k.startswith('font'))
        name = self._css_name
        row_pad = self.row_pad_px
        col_pad = self.col_pad_px
        # Colours are style classes generated on demand.  They are
        # scoped to rows that aren't selected, so the selection
        # highlight wins -- otherwise a cell's own foreground stays put
        # over the selection background and the text goes invisible.
        color_rules = '\n'.join(
            'columnview.%s > listview > row:not(:selected) .%s { %s }'
            % (name, cls, body)
            for cls, body in getattr(self, '_color_rules', {}).items())
        # Background: a view should sit on the theme's *base* colour,
        # not the window's.  Both spellings are emitted -- GTK themes
        # define @theme_base_color, libadwaita @view_bg_color -- and an
        # undefined one is simply dropped, so whichever exists wins.
        # set_bg() overrides both.
        explicit = getattr(self, '_bg_color', None)
        if explicit is not None:
            bg = 'background-color: %s;' % (explicit,)
        else:
            # NOTE: only one name can be used.  CSS keeps the *last*
            # declaration that parses, not the last that resolves, so
            # emitting both would silently discard the first --
            # @view_bg_color is libadwaita-only, and where it isn't
            # defined the background ends up unset and the window's
            # colour shows through.  @theme_base_color is the name GTK
            # themes define; set_bg() overrides it.
            bg = 'background-color: @theme_base_color;'

        alt_rows = ''
        if getattr(self, '_alt_row_colors', False):
            # NB: on the *cells*, not the row.  The cells are painted
            # over the row, so a shade on the row never shows.
            alt_rows = ('columnview.%s > listview > row:not(:selected)'
                        ':nth-child(even) > cell '
                        '{ background-color: shade(@theme_base_color, 0.93); }'
                        % (name,))
        style = f"""
        columnview.{name} {{
            {font}
            {bg}
        }}
        columnview.{name} > listview {{
            {bg}
        }}
        columnview.{name} > listview > row:not(:selected) > cell {{
            {bg}
        }}
        columnview.{name} > listview > row > cell {{
            padding: {row_pad}px {col_pad}px;
            min-height: 0;
        }}
        columnview.{name} > listview > row {{ min-height: 0; }}
        columnview.{name} .ginga-cell-selected {{
            background-color: alpha(currentColor, 0.18);
        }}
        /* ...and in the theme's selection colour where there is one, so
           a selected column reads as selected rather than as a faint
           wash.  Separate block on purpose: an undefined colour name
           drops its declaration, leaving the rule above standing. */
        columnview.{name} .ginga-cell-selected {{
            background-color: alpha(@theme_selected_bg_color, 0.35);
        }}
        {alt_rows}
        {color_rules}
        /* An editable cell holds a GtkEditableLabel, which is an
           entry: at rest it paints the theme's *entry* background over
           the cell, which reads as a tinted block on themes whose entry
           colour differs from the view's, and hides the selection
           highlight while the text still turns the selected colour --
           making it invisible.  Strip it back to the cell until the
           cell is actually being edited.  Every node under the stack
           is named, not just the entry: the display side is a label
           that some themes paint too, and a rule that stops at the
           entry leaves the cell tinted (and hides the selection). */
        columnview.{name} editablelabel:not(.editing):not(.ginga-cell-selected),
        columnview.{name} editablelabel:not(.editing) > stack,
        columnview.{name} editablelabel:not(.editing) > stack > *,
        columnview.{name} editablelabel:not(.editing) > stack > * > * {{
            background: none;
            background-color: transparent;
            box-shadow: none;
            border: none;
            outline: none;
        }}
        columnview.{name} label,
        columnview.{name} editablelabel,
        columnview.{name} checkbutton,
        columnview.{name} checkbutton check,
        columnview.{name} dropdown,
        columnview.{name} dropdown button,
        columnview.{name} progressbar,
        columnview.{name} button {{
            min-height: 0;
            padding-top: 0;
            padding-bottom: 0;
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_string(style)
        self._css_pending = provider

        # The stylesheet goes on a display, and a plugin often builds
        # its widgets before there is one -- in which case nothing was
        # installed and the view fell back to whatever the window was
        # painted with.  Install now if we can, and otherwise as soon
        # as the widget is realised.
        display = self.cv.get_display() or Gdk.Display.get_default()
        if display is None:
            if not getattr(self, '_css_realize_id', None):
                self._css_realize_id = self.cv.connect(
                    'realize', self._on_realize_apply_css)
            return

        if self._css is not None:
            Gtk.StyleContext.remove_provider_for_display(display, self._css)
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._css = provider
        self._css_display = display

    def _on_realize_apply_css(self, widget):
        """Install the stylesheet once a display exists."""
        if self._css_realize_id:
            self.cv.disconnect(self._css_realize_id)
            self._css_realize_id = None
        self._apply_css()

    def set_font(self, font, size=10):
        font_info = font
        if isinstance(font_info, str):
            font_info = font_asst.parse_font(font_info)
        # expand the family to the CSS fallback list of registered
        # substitutes, as the rest of this backend does -- Pango can't
        # resolve an alias like 'fixed' from a bare font-family
        family = font_asst.get_css_family_list(
            getattr(font_info, 'family', 'sans'))
        self.font = font_info
        self.fontsize = size
        self._apply_css(**{
            'font-family': family,
            'font-size': f'{size}pt',
            'font-style': getattr(font_info, 'style', 'normal'),
            'font-weight': getattr(font_info, 'weight', 'normal')})

    def set_header_font(self, font, size=10):
        # headers take the same stylesheet; ColumnView has no separate
        # header font property
        self.set_font(font, size=size)

    def set_cell_padding(self, px):
        self.cell_pad_px = px
        self.set_row_spacing(px)
        self.set_column_spacing(px)

    def set_row_spacing(self, px):
        self.row_pad_px = px
        self._apply_css()

    def set_column_spacing(self, px):
        self.col_pad_px = px
        self._apply_css()

    def set_bg(self, color):
        """Force the view's background, overriding the theme."""
        self._bg_color = color
        self._apply_css()

    def _header_buttons(self):
        """The clickable header widgets, in column order."""
        header = self.cv.get_first_child()
        if header is None:
            return []
        out = []
        child = header.get_first_child()
        while child is not None:
            out.append(child)
            child = child.get_next_sibling()
        return out

    def _connect_header_clicks(self):
        """Clicking a header selects that column's cells.

        ColumnView headers only sort; with sorting off they do nothing
        at all, so the click is picked up here to give the column
        selection the qt table offers.

        The titles are built lazily, so right after the columns change
        the header still holds the previous set -- hence the idle pass
        as well as the immediate one.  Which column a title stands for
        is worked out when it is clicked rather than now, for the same
        reason: numbering it here binds it to a header that may not
        have the row-number column in it yet, and every click then
        lands one column to the left.
        """
        self._install_header_gestures()
        GLib.idle_add(self._install_header_gestures)

    def _install_header_gestures(self):
        for button in self._header_buttons():
            if getattr(button, '_ginga_header_gesture', False):
                continue
            gesture = Gtk.GestureClick.new()
            gesture.set_button(1)
            # CAPTURE: the title has its own gesture underneath, and it
            # claims the press before a bubble-phase one is reached
            gesture.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            gesture.connect('pressed', self._on_header_pressed)
            button.add_controller(gesture)
            button._ginga_header_gesture = True
        return False            # one-shot, for idle_add

    def _on_header_pressed(self, gesture, n_press, x, y):
        button = gesture.get_widget()
        col_idx = self._column_at(button, x)
        if col_idx is None:
            return
        self._on_header_clicked(gesture, n_press, x, y, col_idx)

    def _column_at(self, button, x):
        """Which data column a header title belongs to.

        By position on screen, not by sibling order: GTK keeps the
        header's children in creation order, so the row-number column
        -- inserted at position 0 after the others -- comes *last* in
        the child list while sitting leftmost on screen.  Counting
        children therefore picks the column one to the left.
        """
        titles = self._titles_in_view_order()
        if button not in titles:
            return None
        col_idx = titles.index(button) - self._col_offset()
        return col_idx if 0 <= col_idx < len(self.datakeys) else None

    def _titles_in_view_order(self):
        """Header titles left to right."""
        def left_edge(widget):
            ok, rect = widget.compute_bounds(self.cv)
            return rect.origin.x if ok else 0.0

        return sorted(self._header_buttons(), key=left_edge)

    def _on_header_clicked(self, gesture, n_press, x, y, col_idx):
        """Header click -> sort and/or column-select.

        Follows the qt table exactly: only cell selection modes select
        at all; on a sortable table a plain click sorts and a modifier
        click selects; on a non-sortable one every click selects.
        Ctrl adds a column, Shift extends from the last one clicked.
        """
        if not self._cell_mode():
            return
        if col_idx < 0 or col_idx >= len(self.datakeys):
            return
        state = gesture.get_current_event_state()
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)

        # plain click on a sortable header sorts; ColumnView does that
        # itself, so stay out of the way
        if self.sortable and not (ctrl or shift):
            return

        anchor = getattr(self, '_col_anchor', None)
        if shift and anchor is not None:
            lo, hi = sorted((anchor, col_idx))
            col_idxs = list(range(lo, hi + 1))
        else:
            col_idxs = [col_idx]
            self._col_anchor = col_idx

        if not ctrl and not shift:
            self._cell_selection = set()
            # a column selection replaces what was selected before,
            # including any selected rows
            self.clear_selection()
        col_keys = [self.datakeys[i] for i in col_idxs]
        cells = [dict(path=self._path_for_row(row), col_key=col_key)
                 for row in _columnview.walk_rows(self.store)
                 for col_key in col_keys]
        self.select_cells(cells, state=True)
        self.make_callback('cell_selected', self.get_selected_cells())

    def debug_style(self):
        """Report how this view is styled, for diagnosing appearance
        problems in a running application."""
        display = self.cv.get_display() or Gdk.Display.get_default()
        return dict(css_class=self._css_name,
                    provider_installed=self._css is not None,
                    display=None if display is None else display.get_name(),
                    realized=self.cv.get_realized(),
                    background=getattr(self, '_bg_color', None),
                    rules=len(getattr(self, '_color_rules', {})))

    def get_rgb_array(self):
        return GtkHelp.get_rgb_array(self.cv)


class TableView(TreeView):
    """A flat table, built on the same ColumnView as TreeView.

    A table is a one-level tree, so the rows, columns, colours,
    editing and widget cells all come from TreeView; what differs is
    the vocabulary.  Rows are addressed by index rather than by key --
    ``get_row(3)``, ``select_path([3])`` -- and ``get_selected()``
    returns a list of row dicts rather than a nested tree, matching the
    qt and pg tables.
    """

    def __init__(self, columns=None, show_header=True,
                 selection_mode='single', alternate_row_colors=False,
                 show_grid=False, show_row_numbers=False,
                 sortable=False, allow_text_selection=False,
                 dragable=False):
        # NOTE: the table takes selection_mode / alternate_row_colors,
        # while the tree takes selection / use_alt_row_color.  That is
        # the generic API on every backend, so keep to it here.
        super().__init__(auto_expand=False, sortable=sortable,
                         selection=selection_mode,
                         use_alt_row_color=alternate_row_colors,
                         dragable=dragable)
        self._show_grid = show_grid
        self._show_row_numbers = show_row_numbers
        self._show_header = show_header
        self.cv.set_show_row_separators(show_grid)
        self.cv.set_show_column_separators(show_grid)
        self.set_show_header(show_header)
        if columns is not None:
            self.set_columns(columns)

    def set_show_header(self, tf):
        """ColumnView has no header property, so the header widget --
        its first child -- is hidden directly."""
        self._show_header = tf
        header = self.cv.get_first_child()
        if header is not None:
            header.set_visible(bool(tf))

    # ----- rows are named by index --------------------------------

    def _path_for_row(self, row):
        idx = self._index_of(row)
        return [] if idx is None else [idx]

    def _index_of(self, row):
        for i, candidate in enumerate(self.store):
            if candidate is row:
                return i
        return None

    def _row_at(self, path):
        """Accept an index, or a one-element path holding one."""
        if isinstance(path, int):
            index = path
        elif isinstance(path, (list, tuple)) and len(path) == 1:
            index = path[0]
        else:
            return super()._row_at(path)
        if isinstance(index, str):
            return super()._row_at([index])
        if 0 <= index < self.store.get_n_items():
            return self.store.get_item(index)
        return None

    # ----- columns ------------------------------------------------

    def set_columns(self, columns):
        specs = [treehelper.normalize_column(col, i)
                 for i, col in enumerate(columns)]
        leaf_key = specs[0]['key'] if specs else None
        self.setup_table(columns, 1, leaf_key)
        if self._show_row_numbers:
            column = Gtk.ColumnViewColumn.new('', self._rownum_factory())
            column.set_resizable(False)
            column.set_expand(False)
            self.cv.insert_column(0, column)
        self._connect_header_clicks()

    def append_column(self, column):
        self.set_columns(list(self.columns) + [column])

    def insert_column(self, index, column):
        cols = list(self.columns)
        cols.insert(index, column)
        self.set_columns(cols)

    def delete_column(self, index):
        cols = list(self.columns)
        if isinstance(index, str):
            index = self.datakeys.index(index)
        if 0 <= index < len(cols):
            del cols[index]
            self.set_columns(cols)

    def get_column_count(self):
        return len(self.datakeys)

    def set_column_width(self, i, width):
        super().set_column_width(i + self._col_offset(), width)

    # ----- row contents -------------------------------------------

    def _normalise_row(self, values):
        if isinstance(values, dict):
            return dict(values)
        if isinstance(values, (list, tuple)):
            return dict(zip(self.datakeys, values))
        raise WidgetError("row must be a dict or a sequence, got "
                          f"{type(values).__name__}")

    def set_rows(self, rows):
        self.clear()
        for values in rows:
            self.store.append(_columnview.Row(self._next_key(),
                                              self._normalise_row(values),
                                              is_leaf=True))
        self._refresh_bound_cells()

    set_data = set_rows

    def set_table(self, table):
        from ginga.util import tablehelper
        self.set_columns(tablehelper.columns_from_table(table))
        self.set_rows(tablehelper.rows_from_table(table))

    def _next_key(self):
        used = {row.key for row in self.store}
        i = self.store.get_n_items()
        while f'row{i}' in used:
            i += 1
        return f'row{i}'

    def append_row(self, values):
        self.store.append(_columnview.Row(self._next_key(),
                                          self._normalise_row(values),
                                          is_leaf=True))
        self._refresh_bound_cells()

    def insert_row(self, index, values):
        row = _columnview.Row(self._next_key(),
                              self._normalise_row(values), is_leaf=True)
        n = self.store.get_n_items()
        self.store.insert(max(0, min(index, n)), row)
        self._refresh_bound_cells()

    def delete_row(self, index):
        if 0 <= index < self.store.get_n_items():
            self.store.remove(index)
            self._refresh_bound_cells()

    def get_row_count(self):
        return self.store.get_n_items()

    def get_row(self, index):
        row = self._row_at(index)
        if row is None:
            raise IndexError(f"row index {index} out of range")
        return dict(row.values)

    def get_rows(self):
        return [dict(row.values) for row in self.store]

    def set_cell(self, row, col, value):
        target = self._row_at(row)
        if target is None:
            return
        col_key = (self.datakeys[col] if isinstance(col, int)
                   else col)
        target.values[col_key] = value
        target.supplied.add(col_key)
        self._refresh_bound_cells()

    # ----- selection ----------------------------------------------

    def get_selected(self):
        """A list of row dicts, as the qt and pg tables return."""
        return [dict(row.values) for row in self._selected_rows()]

    def set_selected(self, items):
        self.clear_selection()
        for item in (items or []):
            self.select_path(item)

    # ----- presentation -------------------------------------------

    def set_show_grid(self, tf):
        self._show_grid = tf
        self.cv.set_show_row_separators(tf)
        self.cv.set_show_column_separators(tf)

    def set_sortable(self, tf):
        self.sortable = tf
        offset = self._col_offset()
        for i, column in enumerate(self.cv.get_columns()):
            if i < offset:
                continue        # the row-number column never sorts
            column.set_sorter(
                self._make_column_sorter(i - offset) if tf else None)

    def _col_offset(self):
        return 1 if self._show_row_numbers else 0

    def sort_by_column(self, col, ascending=True):
        idx = col if isinstance(col, int) else self.datakeys.index(col)
        idx += self._col_offset()
        columns = self.cv.get_columns()
        if 0 <= idx < len(columns):
            self.cv.sort_by_column(
                columns[idx],
                Gtk.SortType.ASCENDING if ascending
                else Gtk.SortType.DESCENDING)

    def set_scroll_position(self, h_pct, v_pct):
        sw = self.widget
        for adj, pct in ((sw.get_hadjustment(), h_pct),
                         (sw.get_vadjustment(), v_pct)):
            if adj is None or pct is None:
                continue
            span = adj.get_upper() - adj.get_page_size()
            adj.set_value(adj.get_lower() + span * pct)

    def get_scroll_position(self):
        sw = self.widget
        out = []
        for adj in (sw.get_hadjustment(), sw.get_vadjustment()):
            if adj is None:
                out.append(0.0)
                continue
            span = adj.get_upper() - adj.get_page_size()
            out.append(0.0 if span <= 0 else
                       (adj.get_value() - adj.get_lower()) / span)
        return tuple(out)

    def set_show_row_numbers(self, tf):
        """Show a leading column of row numbers.

        It is a real ColumnView column, but not one of the caller's:
        it is prepended on rebuild and skipped everywhere the API talks
        in column indices, so ``datakeys`` and ``set_cell(row, 2, ...)``
        keep referring to the caller's own columns.
        """
        if bool(tf) == bool(self._show_row_numbers):
            return
        self._show_row_numbers = bool(tf)
        if self.columns:
            self.set_columns(self.columns)

    def _rownum_factory(self):
        factory = Gtk.SignalListItemFactory()

        def setup(_f, list_item):
            label = Gtk.Label()
            label.set_xalign(1.0)
            label.add_css_class('dim-label')
            list_item.set_child(label)

        def bind(_f, list_item):
            row = list_item.get_item().get_item()
            idx = self._index_of(row)
            list_item.get_child().set_text(
                '' if idx is None else str(idx + 1))

        factory.connect('setup', setup)
        factory.connect('bind', bind)
        return factory


class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        self.children = []

        for name in ['widget-added', 'widget-removed']:
            self.enable_callback(name)

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def _remove(self, childw, delete=False):
        self.widget.remove(childw)
        childw.unparent()
        if delete:
            #childw.destroy()
            pass

    def remove(self, child, delete=False):
        if child not in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(child)

        self._remove(child.get_widget(), delete=delete)
        self.make_callback('widget-removed', child)

    def remove_all(self, delete=False):
        for child in list(self.children):
            self.remove(child, delete=delete)

    def is_container(self):
        return True

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


class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.orientation = orientation
        if orientation == 'horizontal':
            self.widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        else:
            self.widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # Cross-axis alignment to apply to each child as it joins
        # the box (and to existing children when ``set_align`` is
        # called).  ``None`` means use Gtk's default (FILL).
        self._cross_align = None

    def set_spacing(self, val):
        self.widget.set_spacing(val)

    def insert_widget(self, idx, child, stretch=0):
        child_w = child.get_widget()
        # TODO: can this be made more accurate?
        expand = (float(stretch) > 0)
        if self.orientation == 'horizontal':
            child_w.set_hexpand(expand)
        else:
            child_w.set_vexpand(expand)
        self.widget.append(child_w)
        self.widget.reorder_child(child_w, idx)
        self.children.insert(idx, child)
        self._apply_cross_align(child_w)
        self.make_callback('widget-added', child)

    def add_widget(self, child, stretch=0):
        self.add_ref(child)
        child_w = child.get_widget()
        # TODO: can this be made more accurate?
        # old style was pack_start(child, expand_bool, fill_bool, padding_px_int)
        expand = (float(stretch) > 0)
        if self.orientation == 'horizontal':
            child_w.set_hexpand(expand)
        else:
            child_w.set_vexpand(expand)
        self.widget.append(child_w)
        self._apply_cross_align(child_w)
        self.make_callback('widget-added', child)

    def set_align(self, align):
        """Cross-axis alignment for children of this Box.  Accepts
        ``'top'`` / ``'center'`` / ``'bottom'`` on a horizontal
        box, ``'left'`` / ``'center'`` / ``'right'`` on a vertical
        box.  Mismatch raises ``ValueError``."""
        self._cross_align = self._resolve_align(align)
        for child in self.get_children():
            self._apply_cross_align(child.get_widget())

    def _resolve_align(self, align):
        align = align.lower()
        if self.orientation == 'horizontal':
            mapping = {'top': Gtk.Align.START,
                       'center': Gtk.Align.CENTER,
                       'bottom': Gtk.Align.END}
            expected = "'top' | 'center' | 'bottom'"
        else:
            mapping = {'left': Gtk.Align.START,
                       'center': Gtk.Align.CENTER,
                       'right': Gtk.Align.END}
            expected = "'left' | 'center' | 'right'"
        if align not in mapping:
            raise ValueError(
                f"{self.orientation} Box.set_align expects {expected}, "
                f"got {align!r}")
        return mapping[align]

    def _apply_cross_align(self, child_w):
        if self._cross_align is None:
            return
        if self.orientation == 'horizontal':
            child_w.set_valign(self._cross_align)
        else:
            child_w.set_halign(self._cross_align)


class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')


class ButtonBox(HBox):
    """A horizontal row of buttons all sized to match the widest button, so
    they line up as a tidy uniform group.

    Parameters
    ----------
    min_button_width : int or None
        If given, buttons are never sized narrower than this, even when the
        widest button's natural size is smaller.
    halign : str
        Horizontal alignment of the button group within the box: 'left',
        'center' (default), or 'right'.
    """
    def __init__(self, min_button_width=None, halign='center'):
        super(ButtonBox, self).__init__()

        self.min_button_width = min_button_width
        self._halign = halign
        self._spacers = []
        self.set_border_width(4)
        # a SizeGroup makes all its widgets share the widest natural width
        self._sizegroup = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

    def add_widget(self, child):
        w = child.get_widget()
        self._sizegroup.add_widget(w)
        if self.min_button_width is not None:
            w.set_size_request(self.min_button_width, -1)
        super(ButtonBox, self).add_widget(child, stretch=0)
        self._apply_align()

    def set_halign(self, halign):
        """Align the button group: 'left', 'center', or 'right'."""
        self._halign = halign
        self._apply_align()

    def _apply_align(self):
        """Position the button group with expanding spacers per halign."""
        box = self.get_widget()
        for sp in self._spacers:
            box.remove(sp)
        self._spacers = []
        if self._halign in ('right', 'center'):
            sp = Gtk.Label()
            sp.set_hexpand(True)
            box.prepend(sp)
            self._spacers.append(sp)
        if self._halign in ('left', 'center'):
            sp = Gtk.Label()
            sp.set_hexpand(True)
            box.append(sp)
            self._spacers.append(sp)


class Frame(ContainerBase):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        fr = Gtk.Frame(label=title)
        #fr.set_label_align(0.10, 0.5)
        fr.set_label_align(0.10)
        self.widget = fr

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.set_child(child.get_widget())

    def set_text(self, text):
        w = self.get_widget()
        lbl = w.get_label_widget()
        if lbl is None:
            # frame built without a title -- create the label from the string
            w.set_label(text)
        else:
            lbl.set_text(text)

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO: GTK4 removed modify_font(); title font styling needs CSS
        # (see Label.set_font)


class Expander(ContainerBase):
    def __init__(self, title=None, notoggle=False):
        super().__init__()

        self.widget = Gtk.Expander()
        self.widget.set_label(title)
        self.widget.connect("activate", self._cb_redirect)
        # NOTE: currently no support for notoggle
        self.content = None

        for name in ('opened', 'closed'):
            self.enable_callback(name)

    def _cb_redirect(self, w):
        if w.get_expanded():
            self.make_callback('opened')
        else:
            self.make_callback('closed')

    def set_widget(self, child, stretch=1):
        if self.content is not None:
            self.remove(self.content)
        self.add_ref(child)
        self.content = child
        self.widget.set_child(child.get_widget())

    def expand(self, tf):
        self.widget.set_expanded(tf)

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        # TODO: GTK4 removed modify_font(); title font styling needs CSS
        # (see Label.set_font)


class TabWidget(ContainerBase):
    def __init__(self, tabpos='top', reorderable=False, detachable=True,
                 group=0):
        super(TabWidget, self).__init__()

        self.reorderable = reorderable
        self.detachable = detachable

        nb = GtkHelp.Notebook()
        # nb = Gtk.Notebook()
        nb.set_show_border(False)
        nb.set_scrollable(True)
        # Allows drag-and-drop between notebooks
        # nb.set_group_id(group)  # in gtk3?
        if self.detachable:
            nb.connect("create-window", self._tab_detach_cb)
        nb.connect("page-added", self._tab_insert_cb)
        nb.connect("page-removed", self._tab_remove_cb)
        # contrary to some other widgets, we want the "tab changed" event
        # when the index is switched programmatically as well as by user
        ## nb.sconnect("switch-page", self._cb_redirect)
        nb.connect("switch-page", self._cb_redirect)
        self.widget = nb
        self.set_tab_position(tabpos)

        for name in ('page-switch', 'page-close', 'page-move', 'page-detach'):
            self.enable_callback(name)

    def set_tab_position(self, tabpos):
        nb = self.widget
        if tabpos == 'top':
            nb.set_tab_pos(Gtk.PositionType.TOP)
        elif tabpos == 'bottom':
            nb.set_tab_pos(Gtk.PositionType.BOTTOM)
        elif tabpos == 'left':
            nb.set_tab_pos(Gtk.PositionType.LEFT)
        elif tabpos == 'right':
            nb.set_tab_pos(Gtk.PositionType.RIGHT)

    def _tab_detach_cb(self, source, nchild_w, x, y):
        child = self._native_to_child(nchild_w)
        # remove child
        # (native widget already has been removed by gtk)
        self.children.remove(child)

        # nchild_w.unparent()
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
        try:
            child = self._native_to_child(nchild_w)
            _widget_move_event = WidgetMoveEvent(self, child)
        except ValueError:
            # we were triggered by a removal that is not a move
            pass

    def _cb_redirect(self, nbw, gptr, index):
        child = self.index_to_widget(index)
        self.make_callback('page-switch', child)

    def _cb_select(self, widget, event, child):
        self.make_callback('page-switch', child)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        label = Gtk.Label(label=title)
        #label.connect("button-press-event", self._cb_select, child)
        self.widget.append_page(child_w, label)
        if self.reorderable:
            self.widget.set_tab_reorderable(child_w, True)
        if self.detachable:
            self.widget.set_tab_detachable(child_w, True)
        # attach title to child
        child.extdata.tab_title = title
        self.make_callback('widget-added', child)

    def get_index(self):
        return self.widget.get_current_page()

    def set_index(self, idx):
        self.widget.set_current_page(idx)

    def index_of(self, child):
        widget = child.get_widget()
        if widget is None:
            return -1
        return self.widget.page_num(widget)

    def remove(self, child, delete=False):
        idx = self.index_of(child)
        self.children.remove(child)
        self.widget.remove_page(idx)
        child_w = child.get_widget()
        child_w.unparent()
        if delete:
            # child_w.destroy()
            pass
        self.make_callback('widget-removed', child)

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        nchild = self.widget.get_nth_page(idx)
        return self._native_to_child(nchild)

    def highlight_tab(self, idx, tf):
        nchild = self.widget.get_nth_page(idx)
        evbox = self.widget.get_tab_label(nchild)
        if tf:
            GtkHelp.modify_bg(evbox, 'palegreen')
        else:
            GtkHelp.modify_bg(evbox, None)


class StackWidget(TabWidget):
    def __init__(self):
        super(StackWidget, self).__init__()

        nb = self.widget
        # nb.set_scrollable(False)
        nb.set_show_tabs(False)
        nb.set_show_border(False)


class MDIWidget(ContainerBase):

    def __init__(self, tabpos='top', mode='tabs'):
        super(MDIWidget, self).__init__()

        self.mode = 'mdi'
        self.true_mdi = True

        self.mdi_w = GtkHelp.MDIWidget()
        self.widget = self.mdi_w.sw
        w = self.mdi_w
        # Monkey patching the internal callbacks so that we can make
        # the correct callbacks
        w._move_page = w.move_page
        w.move_page = self._window_moved
        w._resize_page = w.resize_page
        w.resize_page = self._window_resized
        w._set_current_page = w.set_current_page
        w.set_current_page = self._set_current_page

        for name in ('page-switch', 'page-close'):
            self.enable_callback(name)

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        pass

    def add_widget(self, child, title=''):
        self.add_ref(child)
        subwin = MDIWindow(self, child, title=title)
        subwin.add_callback('close', self._window_close, child)

        self.make_callback('widget-added', child)
        return subwin

    def _remove(self, childw, delete=False):
        self.mdi_w.remove(childw)
        if delete:
            #childw.destroy()
            pass

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

    def _window_close(self, subwin, child):
        return self.make_callback('page-close', child)

    def _set_current_page(self, idx):
        _idx = self.mdi_w.get_current_page()
        self.mdi_w._set_current_page(idx)
        if _idx != idx:
            child = self.index_to_widget(idx)
            self.make_callback('page-switch', child)

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

    def get_child_size(self, child):
        return self.mdi_w.get_widget_size(child.get_widget())

    def get_child_position(self, child):
        return self.mdi_w.get_widget_position(child.get_widget())

    def tile_panes(self):
        self.mdi_w.tile_pages()

    def cascade_panes(self):
        self.mdi_w.cascade_pages()

    def use_tabs(self, tf):
        pass


class MDIWindow(WidgetBase):
    def __init__(self, parent, child, title='', iconpath=None):
        """NOTE: this widget is not meant to be instantiated except *inside*
        of MDIWidget implementation.
        """
        WidgetBase.__init__(self)
        self.parent = parent
        mdi_w = parent.mdi_w

        # does child have a previously saved size?
        size = child.extdata.get('mdi_size', None)
        if size is not None:
            wd, ht = size
            child.resize(wd, ht)

        child_w = child.get_widget()
        label = Gtk.Label(label=title)
        if iconpath is None:
            iconpath = app_icon_path

        subwin = GtkHelp.MDISubWindow(child_w, label, iconpath=iconpath)
        self.widget = subwin
        # attach title to child
        child.extdata.tab_title = title

        self.enable_callback('close')
        subwin.add_callback('close', self._window_close)

        # does child have a previously saved position?
        pos = child.extdata.get('mdi_pos', None)
        if pos is not None:
            subwin.x, subwin.y = pos

        mdi_w.add_subwin(subwin)

    def get_pos(self):
        return self.widget.x, self.widget.y

    def raise_(self):
        self.widget.raise_()

    def lower(self):
        self.widget.lower()

    def focus(self):
        self.widget.focus()

    def move(self, x, y):
        self.parent.mdi_w.move_page(self.widget, x, y)

    def resize(self, wd, ht):
        self.parent.mdi_w.resize_page(self.widget, wd, ht)

    def maximize(self):
        self.parent.mdi_w.maximize_page(self.widget)

    def unmaximize(self):
        raise WidgetError("this call not available for MDIWindow")

    def fullscreen(self):
        raise WidgetError("this call not available for MDIWindow")

    def unfullscreen(self):
        raise WidgetError("this call not available for MDIWindow")

    def is_fullscreen(self):
        raise WidgetError("this call not available for MDIWindow")

    def iconify(self):
        self.parent.mdi_w.minimize_page(self.widget)

    def uniconify(self):
        raise WidgetError("this call not available for MDIWindow")

    def set_title(self, title):
        self.widget.label.set_text(title)

    def _window_close(self, subwin):
        return self.make_callback('close')


class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        sw = Gtk.ScrolledWindow()
        sw.set_has_frame(True)
        GtkHelp.set_border_width(sw, 2)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.widget = sw

        self.enable_callback('configure')
        # TODO
        #sw.connect("resize", self._resize_cb)

    def _resize_cb(self, widget, width, height):
        self.make_callback('configure', width, height)
        return True

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)
        self.widget.set_child(child.get_widget())

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
    def __init__(self, orientation='horizontal', thumb_px=8):
        super(Splitter, self).__init__()

        # thumb_px ignored in this version
        self.orientation = orientation
        self.widget = self._get_pane()
        self.panes = [self.widget]

    def _get_pane(self):
        # ``background-color: transparent`` on the separator keeps
        # the custom dots image visible while letting the window's
        # chrome-grey background show through behind it — without
        # it the theme's default ``separator.wide`` colour wins,
        # which is usually a slightly lighter shade than the rest
        # of the window.
        if self.orientation == 'horizontal':
            w = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
            iconfile = pathlib.Path(icondir) / 'vdots.png'
            content = ("background-image: url('file://%s'); "
                       "background-color: transparent; "
                       "background-repeat: no-repeat; "
                       "background-position: center center; "
                       "background-size: 10px 30px;" % (iconfile))
        else:
            w = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
            iconfile = pathlib.Path(icondir) / 'hdots.png'
            content = ("background-image: url('file://%s'); "
                       "background-color: transparent; "
                       "background-repeat: no-repeat; "
                       "background-position: center center; "
                       "background-size: 30px 10px;" % (iconfile))
        w.set_wide_handle(True)
        # scoped to this paned: the provider goes on the display now
        GtkHelp.set_widget_css(w, 'handle',
                               "paned.{name} > separator.wide { %s }"
                               % (content,))

        return w

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()

        # without a Frame it can be difficult to see the divider
        frame_w = Gtk.Frame()
        frame_w.set_child(child_w)

        if len(self.children) == 1:
            self.widget.set_start_child(frame_w)

        else:
            last = self.widget
            if len(self.panes) > 0:
                last = self.panes[-1]

            w = self._get_pane()
            self.panes.append(w)

            w.set_start_child(frame_w)
            last.set_end_child(w)

        self.make_callback('widget-added', child)

    def _get_sizes(self, pane):
        rect = GtkHelp.widget_allocation(pane)
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


class Splitter2(ContainerBase):
    def __init__(self, orientation='horizontal', thumb_px=8):
        super(Splitter, self).__init__()

        self.orientation = orientation
        self.widget = GtkHelp.Splitter(orientation=self.orientation,
                                       thumb_px=thumb_px)

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()

        # without a Frame it can be difficult to see the divider
        frame_w = Gtk.Frame()
        #frame_w.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        #frame_w.set_shadow_type(Gtk.ShadowType.NONE)
        frame_w.set_child(child_w)

        self.widget.add_widget(frame_w)
        self.make_callback('widget-added', child)

    def get_sizes(self):
        return self.widget.get_sizes()

    def set_sizes(self, sizes):
        self.widget.set_sizes(sizes)


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        w = Gtk.Grid()
        self.widget = w
        self.tbl = {}
        self.num_rows = rows
        self.num_cols = columns

    def resize_grid(self, rows, columns):
        self.num_rows = rows
        self.num_cols = columns
        # No resize() for Gtk4 Grid widget
        #self.widget.resize(rows, columns)

    def set_row_spacing(self, val):
        self.widget.set_row_spacing(val)

    def set_column_spacing(self, val):
        self.widget.set_column_spacing(val)

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def get_row_column_count(self):
        return self.num_rows, self.num_cols

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

        key = (row, col)
        if key in self.tbl:
            # take care of case where we are overwriting a child
            old_child = self.tbl[key]
            old_child.hide()
            self.remove(old_child)
        self.tbl[key] = child
        self.add_ref(child)
        w = child.get_widget()
        # NOTE: attach() specifies column, THEN row
        self.widget.attach(w, col, row, 1, 1)
        self.make_callback('widget-added', child)

    def remove(self, child, delete=False):
        super().remove(child, delete=delete)

        # need to delete the child from self.tbl
        children = list(self.tbl.values())
        if child in children:
            keys = list(self.tbl.keys())
            idx = children.index(child)
            key = keys[idx]
            del self.tbl[key]

    def get_widget_at_cell(self, row, col):
        return self.tbl[(row, col)]

    def insert_row(self, index, widgets=None):
        if widgets is not None:
            if len(widgets) != self.num_cols:
                raise ValueError("Number of widgets ({}) != number of columns ({})".format(len(widgets), self.num_cols))

        self.resize_grid(self.num_rows + 1, self.num_cols)

        if index > self.num_rows:
            index = self.num_rows
        self.widget.insert_row(index)

        if widgets is not None:
            for col, child in enumerate(widgets):
                self.add_widget(child, index, col)

    def append_row(self, widgets):
        num_rows, num_cols = self.get_row_column_count()
        return self.insert_row(num_rows, widgets)

    def delete_row(self, index):
        if index < 0 or index >= self.num_rows:
            raise ValueError("Index ({}) out of bounds ({})".format(index, self.num_rows))

        # remove widgets in row from table
        for j in range(self.num_cols):
            key = (index, j)
            if key in self.tbl:
                child = self.tbl.pop(key)
                self.remove(child)

        self.widget.remove_row(index)
        self.num_rows -= 1


class Toolbar(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Toolbar, self).__init__()

        self.box = Box(orientation=orientation)
        #w.set_style(Gtk.ToolbarStyle.ICONS)
        self.widget = self.box.get_widget()
        # if orientation == 'horizontal':
        #     w.set_orientation(Gtk.Orientation.HORIZONTAL)
        # else:
        #     w.set_orientation(Gtk.Orientation.VERTICAL)

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        if toggle:
            child = ToggleButton(text)
        else:
            child = Button(text)
        child.get_widget().set_has_frame(False)

        if iconpath is not None:
            if iconsize is not None:
                wd, ht = iconsize
            else:
                scale_f = _app.screen_res / 96.0
                px = int(scale_f * 24)
                wd, ht = px, px
            pixbuf = GtkHelp.pixbuf_new_from_file_at_size(iconpath, wd, ht)
            if pixbuf is not None:
                image_w = GtkHelp.picture_from_pixbuf(pixbuf)
                btn_w = child.get_widget()
                btn_w.set_child(image_w)

        self.add_widget(child)
        return child

    def add_widget(self, child):
        self.box.add_widget(child, stretch=0)
        self.make_callback('widget-added', child)
        return child

    def add_menu(self, text, menu=None, mtype='tool'):
        if menu is None:
            menu = Menu()
        if mtype == 'tool':
            child = self.add_action(text)
        else:
            child = Label(text, style='clickable', menu=menu)
            self.add_widget(child)
            child.add_callback('released', lambda w: menu.hide())

        child.add_callback('activated', lambda w: menu.popup(child))
        return menu

    def add_separator(self):
        #sep_w = Gtk.SeparatorToolItem()
        #sep = wrap(sep_w)
        #self.widget.insert(sep_w, -1)
        #self.add_ref(sep)
        self.box.add_widget(Label(" | "), stretch=0)

    def add_spacer(self):
        self.box.add_widget(Label(""), stretch=1)


def _menu_icon(iconpath):
    """A GIcon for a menu item.

    A GTK4 menu is a ``Gio.Menu`` model, so its icons are ``GIcon``s
    rather than widgets: a file icon for ginga's own artwork, a themed
    name otherwise.  ``Gtk.PopoverMenu`` renders these; the menu *bar*
    does not, which is why an icon-only entry there keeps its text.
    """
    if iconpath is None:
        return None
    if os.path.exists(iconpath):
        return Gio.FileIcon.new(Gio.File.new_for_path(iconpath))
    return Gio.ThemedIcon.new(iconpath)


class MenuAction(WidgetBase):
    def __init__(self, text=None, checkable=False, iconpath=None,
                 iconsize=None, icon_only=False):
        super(MenuAction, self).__init__()

        self.text = text
        self.checkable = checkable
        self.iconpath = iconpath
        self.iconsize = iconsize
        self.icon_only = icon_only
        self.state = None

        action_id = "menu-" + str(uuid.uuid4())
        if checkable:
            self.state = GLib.Variant("b", False)
            self.action = Gio.SimpleAction(name=action_id,
                                           parameter_type=None,
                                           state=self.state,
                                           enabled=True)
            self.action.connect('change-state', self._cb_redirect)
        else:
            self.action = Gio.SimpleAction(name=action_id,
                                           parameter_type=None,
                                           state=None,
                                           enabled=True)
            #self.action = Gio.SimpleAction.new(action_id, None)
            self.action.connect('activate', self._cb_redirect)

        _app._gtkapp.add_action(self.action)
        #self.action.set_enabled(True)

        self.widget = Gio.MenuItem.new(self._label(), "app." + action_id)
        if iconpath is not None:
            self.widget.set_icon(_menu_icon(iconpath))
        self.enable_callback('activated')

    def set_tooltip(self, text):
        # TODO
        pass

    def _label(self):
        # an icon-only item still needs its text where no icon was
        # given, which is how the reference viewer's Language menu
        # stays usable
        if self.icon_only and self.iconpath is not None:
            return ''
        return self.text

    def set_icon(self, iconpath, iconsize=None):
        self.iconpath = iconpath
        if iconsize is not None:
            self.iconsize = iconsize
        self.widget.set_icon(_menu_icon(iconpath))
        self.widget.set_label(self._label())

    def set_state(self, tf):
        if not self.checkable:
            raise ValueError("Not a checkable menu item")
        #self.action.set_state(tf)
        self.action.set_state(GLib.Variant("b", tf))

    def get_state(self):
        return self.action.get_state()

    def set_enabled(self, tf):
        # The widget is a Gio.MenuItem (a model item, not a Gtk widget), so
        # WidgetBase.set_enabled's set_sensitive() doesn't apply.  A menu
        # item's enabled state is driven by its backing GAction.
        self.action.set_enabled(bool(tf))

    def get_enabled(self):
        return self.action.get_enabled()

    def _cb_redirect(self, *args):
        if self.checkable:
            # 'change-state' fires as (action, requested_value); a stateful
            # action doesn't update its own state, so commit it here (the
            # Gio.MenuItem widget has no get_active()).
            value = args[1] if len(args) > 1 else None
            if value is not None:
                self.action.set_state(value)
                tf = value.get_boolean()
            else:
                cur = self.action.get_state()
                tf = cur.get_boolean() if cur is not None else False
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')


class Menu(ContainerBase):
    def __init__(self):
        super(Menu, self).__init__()

        self.model = Gio.Menu()
        # NOTE: this is only used if the menu is employed as a context menu
        self.widget = Gtk.PopoverMenu.new_from_model_full(self.model,
                                                          Gtk.PopoverMenuFlags.NESTED)
        self.widget.set_halign(Gtk.Align.START)
        self.widget.set_has_arrow(False)
        self.widget.set_autohide(True)
        self.widget.set_cascade_popdown(True)
        self.menus = Bunch.Bunch(caseless=True)
        self.add_separator()

    def add_widget(self, child):
        self.make_callback('widget-added', child)

    def add_name(self, name, checkable=False, iconpath=None, iconsize=None,
                 icon_only=False):
        child = MenuAction(text=name, checkable=checkable, iconpath=iconpath,
                           iconsize=iconsize, icon_only=icon_only)
        self.menus[name] = child
        self.section.append_item(child.get_widget())
        #self.widget.set_menu_model(self.model)
        return child

    def add_menu(self, name, iconpath=None, iconsize=None, icon_only=False):
        child = Menu()
        self.menus[name] = child
        label = '' if (icon_only and iconpath is not None) else name
        item = Gio.MenuItem.new_submenu(label, child.model)
        if iconpath is not None:
            item.set_icon(_menu_icon(iconpath))
        self.section.append_item(item)
        return child

    def get_menu(self, name):
        return self.menus[name]

    def add_separator(self):
        self.section = Gio.Menu()
        item = Gio.MenuItem.new_section(label=None,
                                        section=self.section)
        self.model.append_item(item)

    def popup(self, widget=None):
        if widget is not None:
            self.widget.set_parent(widget.get_widget())
        if self.widget.get_sensitive():
            self.widget.popup()


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.model = Gio.Menu()
        self.widget = Gtk.PopoverMenuBar.new_from_model(self.model)
        self.menus = Bunch.Bunch(caseless=True)

    def add_widget(self, child, name):
        if not isinstance(child, Menu):
            raise ValueError("child widget needs to be a Menu object")
        self.model.append_submenu(name, child.model)
        self.menus[name] = child
        #item.add_callback('activated', self._show_menu, name)
        self.make_callback('widget-added', child)
        return child

    def add_name(self, name, iconpath=None, iconsize=None, icon_only=False):
        # NB: a menubar entry shows its label only.  GtkPopoverMenuBar
        # renders each entry as a bare label and ignores the item's
        # icon; the alternative -- a row of GtkMenuButtons -- can show
        # one, but loses press-drag-release selection across the bar,
        # which is why the model-driven bar is kept.  Icons inside the
        # menus themselves do render (see Menu.add_name).
        child = Menu()
        return self.add_widget(child, name)

    # def _show_menu(self, menubar, name):
    #     self.menus[name].popup(self)

    def get_menu(self, name):
        return self.menus[name]


class TopLevelMixin:

    def __init__(self, title=None):
        self._fullscreen = False

        self._destroy_id = self.widget.connect("destroy", self._quit)
        # TODO
        self.widget.connect("close-request", self._close_event)
        #self.widget.connect("window_state_event", self._window_event)
        #self.widget.connect("configure-event", self._configure_event)

        if title is not None:
            self.widget.set_title(title)

        self.enable_callback('close')

    def show(self):
        self.widget.present()

    def hide(self):
        self.widget.set_visible(False)

    def _quit(self, *args):
        self.close()

    def _close_event(self, widget):
        try:
            self.close()

        finally:
            # don't automatically destroy window
            return True

    def _window_event(self, widget, event):
        if ((event.changed_mask & Gdk.WindowState.FULLSCREEN) or
                (event.changed_mask & Gdk.WindowState.MAXIMIZED)):
            self._fullscreen = True
        else:
            self._fullscreen = False

    def _configure_event(self, widget, event):
        x, y, width, height = event.x, event.y, event.width, event.height
        self.extdata.setvals(x=x, y=y, width=width, height=height)
        return False

    def close(self):
        # try:
        #     self.widget.destroy()
        # except Exception as e:
        #     pass
        # self.widget = None

        self.make_callback('close')

    def delete(self):
        widget = self.widget
        super().delete()
        window = widget.get_root()
        if window is not None:
            # We are tearing the window down deliberately, so disconnect our
            # "destroy" handler first: otherwise window.destroy() re-enters
            # _quit -> close() -> the 'close' callback, which pops the quit
            # confirmation dialog a second time and then records sizes on the
            # already-deleted widgets.
            if getattr(self, '_destroy_id', None) is not None:
                widget.handler_disconnect(self._destroy_id)
                self._destroy_id = None
            window.destroy()

    def get_size(self):
        if self.widget is None:
            # window already torn down -- fall back to the last recorded size
            ed = self.extdata
            return ed.get('width', 0), ed.get('height', 0)
        try:
            wd = self.widget.get_width()
            ht = self.widget.get_height()

        except Exception:
            # window maybe isn't realized yet--try other ways
            # req = self.widget.get_size_request()
            # wd, ht = req
            min_req, nat_req = self.widget.get_preferred_size()
            wd, ht = nat_req.width, nat_req.height
            ed = self.extdata
            wd, ht = ed.get('width', wd), ed.get('height', ht)

        return wd, ht

    def get_pos(self):
        res = None
        window = self.widget.get_root()
        if window is not None:
            # TODO: Gtk4 doesn't want you to know a window's position
            #res = window.get_origin()
            #if isinstance(res, tuple) and len(res) == 2:
            #    return res
            pass

        ed = self.extdata
        x, y = ed.get('x', 0), ed.get('y', 0)
        return x, y

    def raise_(self):
        # window = self.widget.get_root()
        # if window is not None:
        #     window.raise_()
        self.widget.present()

    def lower(self):
        window = self.widget.get_root()
        if window is not None:
            window.lower()

    def focus(self):
        # window = self.widget.get_root()
        # if window is not None:
        #     window.focus()
        self.widget.focus()

    def move(self, x, y):
        window = self.widget.get_root()
        if window is not None:
            # Gtk4 doesn't want to allow you to move windows
            #window.move(x, y)
            pass

    def maximize(self):
        window = self.widget.get_root()
        if window is not None:
            window.maximize()

    def unmaximize(self):
        window = self.widget.get_root()
        if window is not None:
            window.unmaximize()

    def is_maximized(self):
        window = self.widget.get_root()
        mask = Gdk.WindowState.MAXIMIZED
        return window.get_state() & mask != 0

    def fullscreen(self):
        window = self.widget.get_root()
        if window is not None:
            window.fullscreen()

    def unfullscreen(self):
        window = self.widget.get_root()
        if window is not None:
            window.unfullscreen()

    def is_fullscreen(self):
        return self._fullscreen

    def iconify(self):
        window = self.widget.get_root()
        if window is not None:
            window.minimize()

    def uniconify(self):
        window = self.widget.get_root()
        if window is not None:
            window.unminimize()

    def set_title(self, title):
        self.widget.set_title(title)


class TopLevel(TopLevelMixin, ContainerBase):

    def __init__(self, title=None, iconpath=None):
        ContainerBase.__init__(self)

        self._fullscreen = False
        self.dialogs = []

        widget = GtkHelp.TopLevel()
        if iconpath is None:
            iconpath = app_icon_path
        # TODO: no set_icon in Gtk4
        #widget.set_icon(GtkHelp.get_icon(iconpath))
        self.widget = widget
        GtkHelp.set_border_width(widget, 0)

        TopLevelMixin.__init__(self, title=title)
        if _app is None:
            raise Exception("Application object needs to be created before any widgets")
        _app.add_window(self)

        self.overlay = Gtk.Overlay()
        self.widget.set_child(self.overlay)

    def set_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.overlay.set_child(child_w)

    def set_icon(self, iconpath):
        # NOTE: not guaranteed to work after the window is created because
        # this can be rendered by the window manager. Better to use the
        # constructor 'iconpath' parameter
        # TODO: no set_icon in Gtk4
        #self.widget.set_icon(GtkHelp.get_icon(iconpath))
        pass

    def add_dialog(self, child):
        if child not in self.dialogs:
            self.dialogs.append(child)
            child_w = child.get_widget()
            child_w.set_halign(Gtk.Align.CENTER)
            child_w.set_valign(Gtk.Align.CENTER)
            self.overlay.add_overlay(child_w)

    def remove_dialog(self, child):
        self.dialogs.remove(child)
        child_w = child.get_widget()
        self.overlay.remove_overlay(child_w)


class Application(Callback.Callbacks):

    def __init__(self, logger=None, settings=None, ws_sock=None):
        global _app
        super(Application, self).__init__()

        self.logger = logger
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.settings.add_defaults(font_scaling_factor=None)

        self.window_list = []
        self.window_dict = {}
        self.wincnt = 0

        try:
            display = Gdk.Display.get_default()
            screen = display.get_default_screen()
            window = screen.get_active_window()
            monitor = screen.get_monitor_at_window(window)

            g = screen.get_monitor_geometry(monitor)
            self.screen_ht = g.height
            self.screen_wd = g.width

            self.screen_res = screen.get_resolution()

            scale = self.settings.get('font_scaling_factor', None)
            if scale is None:
                # hack for Gtk--scale fonts on HiDPI displays
                scale = self.screen_res / 72.0
            self.logger.debug("setting default font_scaling_factor={}".format(scale))
            from ginga.fonts import font_asst
            font_asst.default_scaling_factor = scale
        except Exception:
            self.screen_wd = 1600
            self.screen_ht = 1200
            self.screen_res = 96
        # self.logger.debug("screen dimensions %dx%d" % (
        #     self.screen_wd, self.screen_ht))

        app = Gtk.Application(application_id="ginga")
        app.connect('activate', self.on_activate_cb)
        self._gtkapp = app
        self._gtkapp.connect('window-added', self._show_window)
        self._gtkapp.connect('action-added', self._show_action)
        self._activated = False
        self._pending = []
        self._periodic = []
        _app = self

        # NOTE: GObject.threads_init() used to be called here for
        # PyGObject < 3.10.2.  It has been a no-op ever since, and on
        # current versions it raises a deprecation warning -- which
        # turns into an error under this project's pytest settings.
        # self._time_save = time.time()

        for name in ('close', 'shutdown'):
            self.enable_callback(name)

        # Set up Gtk style
        GtkHelp.set_default_style()

    def _show_action(self, *args):
        pass

    def _show_window(self, *args):
        pass

    def get_screen_size(self):
        return (self.screen_wd, self.screen_ht)

    def on_activate_cb(self, app, *args):
        self._activated = True
        while len(self._pending) > 0:
            widget = self._pending.pop()
            self.add_window(widget)

    def add_periodic_callback(self, after_sec, method):
        after_msec = int(after_sec * 1000)
        self._periodic.append(Bunch.Bunch(after_sec=after_sec,
                                          after_msec=after_msec,
                                          method=method))

    def process_events(self):
        pass

    def process_end(self):
        # stop the Gtk main loop (_gtkapp.run) so the application can exit
        self._gtkapp.quit()

    def _process_custom_events(self, bnch):
        try:
            bnch.method()
        finally:
            #GLib.timeout_add(bnch.after_msec,
            #                 self._process_custom_events, bnch)
            GLib.idle_add(self._process_custom_events, bnch)

    def _boot_periodic(self):
        for bnch in self._periodic:
            #GLib.timeout_add(bnch.after_msec,
            #                 self._process_custom_events, bnch)
            GLib.idle_add(self._process_custom_events, bnch)

    def add_window(self, window, wid=None):
        if not self._activated:
            self._pending.append(window)
            return
        self._gtkapp.add_window(window.get_widget())
        if wid is None:
            wid = 'win%d' % (self.wincnt)
            self.wincnt += 1
        window.wid = wid
        window.url = ''
        window.app = self

        self.window_dict[wid] = window

    def remove_window(self, window):
        wid = window.wid
        del self.window_dict[wid]

    def get_window(self, wid):
        return self.window_dict[wid]

    def has_window(self, wid):
        return wid in self.window_dict

    def get_wids(self):
        return list(self.window_dict.keys())

    def make_window(self, title=None):
        w = TopLevel(title=title)
        return w

    def make_timer(self):
        return GtkHelp.Timer()

    def get_url(self):
        return None

    def is_web_backend(self):
        return False

    def open_url(self, url):
        """Open *url* in the user's web browser (desktop backend)."""
        import webbrowser
        webbrowser.open(url, new=2)

    def register_font(self, family, path, weight='normal', style='normal'):
        # This is almost a no-op for Gtk3--no easy way to load a font
        # we'll just register it in case there is a way to do that in
        # the future
        f_key = font_asst.add_loadable_font(path, family, style=style,
                                            weight=weight)  # noqa

    def set_default_font(self, family, size=None, weight=None, style=None):
        font_asst.add_alias('sans', family.lower())

    def _mainloop(self):
        GLib.idle_add(self._boot_periodic)

        self._gtkapp.run(None)

    def mainloop(self):
        self._gtkapp.run(None)

    def close(self):
        """Called when someone is asking the application to close.
        Can register for this callback if you want an application-wide
        event to confirm closure.
        """
        self.make_callback('close')

    def quit(self):
        """Called when someone is forcibly quitting the application.
        Can register for this callback if you want an application-wide
        event to clean up before shutdown.
        """
        self.make_callback('shutdown')

        self._gtkapp.quit()


class Dialog(WidgetBase):

    def __init__(self, title='', flags=DIALOG_FLAGS_ONTOP, buttons=[],
                 parent=None, modal=False, autoclose=False):
        super().__init__()
        self.flags = flags if flags is not None else 0
        self.buttons = []
        self.parent = parent
        self.modal = modal
        self.label = None

        vbox = VBox()
        vbox.set_border_width(4)
        if parent is None:
            self.dialog = TopLevel()
            self.widget = self.dialog.get_widget()
            self.dialog.set_widget(vbox)
        else:
            self.dialog = StackWidget()
            self.widget = self.dialog.get_widget()
            self.label = Label(title)
            self.label.set_border_width(4)
            GtkHelp.modify_bg(self.label.get_widget(), "gray95")
            vbox.add_widget(self.label, stretch=0)
            self.dialog.add_widget(vbox)
            GtkHelp.modify_bg(self.dialog.get_widget(), "gray85")

        # a ButtonBox gives a tidy, uniform-width button row
        btn_box = ButtonBox()
        btn_box.set_border_width(5)
        btn_box.set_spacing(4)
        self.buttonbox = btn_box

        for name, val in buttons:
            btn = Button(name)
            self.add_button(btn, name)

        # ??
        #self.widget.set_modal(modal)

        self.content = VBox()
        self.content.set_border_width(4)
        vbox.add_widget(self.content, stretch=1)
        vbox.add_widget(btn_box, stretch=0)

        for name in ['activated', 'close']:
            self.enable_callback(name)

        if autoclose:
            self.add_callback('close', lambda w: w.hide())

    def _cb_redirect(self, widget, val):
        self.make_callback('activated', val)

    def _cb_close(self, widget):
        self.make_callback('close')

    def get_content_area(self):
        return self.content

    def add_button(self, btn, val):
        self.buttons.append(btn)
        btn.add_callback('activated', self._cb_redirect, val)
        self.buttonbox.add_widget(btn)

    def show(self):
        self.popup()

    def popup(self, parent=None):
        # An explicit parent passed here forces the attach/transient-for
        # behavior; otherwise it is applied only when the on-top flag is
        # set (the default).
        force = parent is not None
        if parent is None:
            parent = self.parent
        if parent is not None:
            if isinstance(parent, TopLevel):
                parent.add_dialog(self)
            elif force or (self.flags & DIALOG_FLAGS_ONTOP):
                parent_w = parent.get_widget()
                if isinstance(parent_w, Gtk.Window):
                    self.widget.set_transient_for(parent_w)

        # a dialog with a parent is a page in a notebook, not a window
        GtkHelp.present(self.widget)


class MessageDialog(Dialog):

    icon_dct = dict()

    @classmethod
    def set_category_icon(cls, category, iconpath, size=(64, 64)):
        native_img = Image.get_native_image_from_file(iconpath, size=size)
        cls.icon_dct[category] = native_img

    def __init__(self, title='', flags=None, buttons=[("Dismiss", 0)],
                 parent=None, modal=False, autoclose=False):
        Dialog.__init__(self, title=title, flags=flags, buttons=buttons,
                        parent=parent, modal=modal, autoclose=autoclose)

        # initialize default icons for certain categories
        if 'warning' not in MessageDialog.icon_dct:
            for category, iconfile in [('warning', "warning.svg"),
                                       #('critical', "critical.svg"),
                                       #('denied', "denied.svg"),
                                       ('error', "error.svg"),
                                       ('info', "information.svg"),
                                       ('question', "question.svg")]:
                iconpath = os.path.join(ginga_icon_dir, iconfile)
                MessageDialog.set_category_icon(category, iconpath)

        vbox = self.get_content_area()
        vbox.set_margins(4, 4, 4, 4)

    def set_message(self, category, text, title=None):
        if title is not None:
            if self.label is not None:
                self.label.set_text(title)
            else:
                self.widget.set_title(title)
        vbox = self.get_content_area()
        vbox.remove_all()
        if category in self.icon_dct:
            hbox = HBox()
            hbox.set_border_width(4)
            hbox.add_widget(Label(""), stretch=1)
            img = Image(native_image=MessageDialog.icon_dct[category])
            hbox.add_widget(img, stretch=0)
            hbox.add_widget(Label(""), stretch=1)
            vbox.add_widget(hbox, stretch=1)

        tw = Label(text)
        vbox.add_widget(tw, stretch=1)
        vbox.add_widget(tw)


class ColorDialog(Dialog):
    """A color selection dialog."""
    def __init__(self, title='', initial_color='blue',
                 parent=None, modal=False, auto_close=True):
        buttons = [("Cancel", 0), ("OK", 1)]
        Dialog.__init__(self, title=title, buttons=buttons,
                        parent=parent, modal=modal)

        self.chooser = Gtk.ColorChooserWidget()
        self.chooser.set_use_alpha(False)
        vbox = self.get_content_area()
        vbox.add_widget(wrap(self.chooser), stretch=1)

        self.set_color(initial_color)
        self.chooser.connect('color_activated', self._cb_changed)

        self._chosen_color = self.get_color(format='tuple')
        self.auto_close = auto_close

        # TODO: pick callback does not currently work
        for name in ['activated', 'pick']:
            self.enable_callback(name)

    def _cb_redirect(self, val):
        if self.auto_close:
            self.widget.set_visible(False)
        if val == 0:
            # Cancel
            return
        gc = self.chooser.get_rgba()
        self._chosen_color = (gc.red, gc.green, gc.blue, gc.alpha)
        self.make_callback('activated', self._chosen_color)

    def _cb_changed(self, *args):
        gc = self.chooser.get_rgba()
        self.make_callback('pick', (gc.red, gc.green, gc.blue, gc.alpha))

    def get_color(self, format='tuple'):
        if format == 'tuple':
            return self._chosen_color
        if format == 'hex':
            return colors.get_hex(self._chosen_color[:3])
        raise ValueError(f"bad format type: '{format}'; should be 'tuple' or 'hex'")

    def set_color(self, color):
        (r, g, b) = colors.resolve_color(color)
        self._chosen_color = (r, g, b)
        g_color = Gdk.RGBA(r, g, b, 1.0)
        self.chooser.set_rgba(g_color)


class FileDialog(Dialog):
    """A file/directory selection dialog."""
    def __init__(self, title='', parent=None, modal=False, auto_close=True):
        buttons = [("Cancel", 0), ("OK", 1)]
        Dialog.__init__(self, title=title, buttons=buttons,
                        parent=parent, modal=modal)

        self.widget.set_size_request(600, 600)
        self.chooser = Gtk.FileChooserWidget()
        # TODO: FileChooserWidget is deprecated in Gtk 4.10
        # TODO: file-activated signal is no longer supported in Gtk4
        # self.chooser.connect('file-activated', self._cb_redirect2)

        vbox = self.get_content_area()
        vbox.add_widget(wrap(self.chooser), stretch=1)

        self.filter_dict = dict()
        self.auto_close = auto_close

    def set_mode(self, mode):
        if mode == 'save':
            self.chooser.set_action(Gtk.FileChooserAction.SAVE)
            self.chooser.set_select_multiple(False)
        elif mode == 'file':
            self.chooser.set_action(Gtk.FileChooserAction.OPEN)
            self.chooser.set_select_multiple(False)
        elif mode == 'files':
            self.chooser.set_action(Gtk.FileChooserAction.OPEN)
            self.chooser.set_select_multiple(True)
        elif mode == 'directory':
            self.chooser.set_action(Gtk.FileChooserAction.CREATE_FOLDER)
            self.chooser.set_select_multiple(False)

    def set_directory(self, path):
        if not os.path.isdir(path):
            raise ValueError(f"{path} does not seem to be an existing directory")
        g_dir = Gio.File.new_for_path(path)
        self.chooser.set_current_folder(g_dir)

    def set_filename(self, path):
        if os.path.isdir(path):
            return self.set_directory(path)

        _dir, filename = os.path.split(path)
        if len(_dir) > 0:
            if not os.path.isdir(_dir):
                raise ValueError(f"{_dir} does not seem to be an existing directory")
            g_dir = Gio.File.new_for_path(_dir)
            self.chooser.set_current_folder(g_dir)
        # TODO: set_file() does not work as expected, even if file exists
        self.chooser.set_current_name(filename)

    def clear_filters(self):
        self.filter_dict = dict()
        filt = Gtk.FileFilter()
        filt.set_name("All files (*.*)")
        filt.add_pattern("*")
        self.chooser.set_filter(filt)

    def add_ext_filter(self, category, file_ext):
        exts = self.filter_dict.setdefault(category, [])
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        exts.append(f"*{file_ext}")

        filt = Gtk.FileFilter()
        res = []
        for category, exts in self.filter_dict.items():
            res.append(f"{category} ({','.join(list(exts))})")
            for ext in exts:
                filt.add_pattern(ext)
        filt.set_name(", ".join(res))
        self.chooser.set_filter(filt)

    def _cb_redirect(self, w, val):
        if self.auto_close:
            self.widget.set_visible(False)
        if val == 0:
            # Cancel
            return
        paths = [g_file.get_path() for g_file in self.chooser.get_files()]
        if len(paths) > 0:
            self.make_callback('activated', paths)

    # def _cb_redirect2(self, widget, user_data):
    #     # double-click on a file, or pressed ENTER
    #     paths = [g_file.get_path() for g_file in self.chooser.get_files()]
    #     if self.auto_close:
    #         self.widget.hide()
    #     if len(paths) > 0:
    #         self.make_callback('activated', paths)


class SaveDialog:
    # TODO: deprecate and use only FileDialog
    def __init__(self, title='Save File', selectedfilter=None):
        action = Gtk.FileChooserAction.SAVE
        buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                   Gtk.STOCK_SAVE, Gtk.ResponseType.OK)

        self.widget = Gtk.FileChooserDialog(title=title, action=action,
                                            buttons=buttons)
        self.selectedfilter = selectedfilter

        if selectedfilter is not None:
            self._add_filter(selectedfilter)

    def _add_filter(self, selectedfilter):
        filtr = Gtk.FileFilter()
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

        if response == Gtk.ResponseType.OK:
            path = self.widget.get_filename()
            if (self.selectedfilter is not None and
                    not path.endswith(self.selectedfilter)):
                path += self.selectedfilter
            #self.widget.destroy()
            self.widget = None
            return path
        elif response == Gtk.ResponseType.CANCEL:
            #self.widget.destroy()
            self.widget = None
            return None


class DragPackage:
    """What a widget hands to its ``drag-start`` callback to be filled in.

    GTK4 drags carry a ``Gdk.ContentProvider`` built up front rather
    than a selection filled in when the drop happens, so the callback's
    ``set_uris`` / ``set_text`` are collected here and turned into one
    when the drag begins.
    """

    def __init__(self, src_widget=None, selection=None):
        self.src_widget = src_widget
        self._selection = selection
        self._uris = []
        self._text = None

    def set_uris(self, urls):
        self._uris = list(urls)

    def set_text(self, text):
        self._text = text

    def start_drag(self):
        pass

    def content_provider(self):
        """The collected data as a ``Gdk.ContentProvider``, or None."""
        providers = []

        def typed(gtype, content):
            # new_typed() is a C varargs convenience and isn't
            # introspectable; a GValue is the way through Python
            value = GObject.Value(gtype)
            value.set_boxed(content) if gtype != GObject.TYPE_STRING \
                else value.set_string(content)
            return Gdk.ContentProvider.new_for_value(value)

        if len(self._uris) > 0:
            files = [Gio.File.new_for_uri(uri) if '://' in uri
                     else Gio.File.new_for_path(uri) for uri in self._uris]
            # Gdk.FileList is what ginga's viewers accept
            providers.append(typed(Gdk.FileList,
                                   Gdk.FileList.new_from_list(files)))
            providers.append(typed(GObject.TYPE_STRING,
                                   '\n'.join(self._uris)))
        if self._text is not None:
            providers.append(typed(GObject.TYPE_STRING, self._text))
        if len(providers) == 0:
            return None
        if len(providers) == 1:
            return providers[0]
        return Gdk.ContentProvider.new_union(providers)


class WidgetMoveEvent:
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
        # GTK4 removed Gtk.Misc.set_alignment(); use set_xalign() to
        # right-adjust the caption text within its grid cell
        w.label.set_xalign(0.95)
    elif wtype == 'llabel':
        w = Label(title)
        # left-adjust the value text
        w.label.set_xalign(0.05)
    elif wtype in ('textentry', 'entry'):
        w = TextEntry()
        # w.get_widget().set_width_chars(12)
    elif wtype in ('textentryset', 'entryset'):
        w = TextEntrySet()
    elif wtype == 'combobox':
        w = ComboBox()
    elif wtype == 'comboboxedit':
        w = ComboBox(editable=True)
    elif wtype in ('spinbox', 'spinbutton'):
        w = SpinBox(dtype=int)
    elif wtype == 'spinfloat':
        w = SpinBox(dtype=float)
    elif wtype == 'vbox':
        w = VBox()
    elif wtype == 'hbox':
        w = HBox()
    elif wtype in ('hslider', 'hscale'):
        w = Slider(orientation='horizontal')
    elif wtype in ('vslider', 'vscale'):
        w = Slider(orientation='vertical')
    elif wtype in ('checkbox', 'checkbutton'):
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
    elif wtype == 'dial':
        w = Dial()
    else:
        raise ValueError("Bad wtype=%s" % wtype)
    return w


def hadjust(w, orientation):
    """Ostensibly, a function to reduce the vertical footprint of a widget
    that is normally used in a vertical stack (usually a Splitter), when it
    is instead used in a horizontal orientation.
    """
    if orientation != 'horizontal':
        return w
    # This currently does not seem to be needed for most plugins that are
    # coded to flow either vertically or horizontally and, in fact, reduces
    # the visual asthetic somewhat.
    ## spl = Splitter(orientation='vertical')
    ## spl.add_widget(w)
    ## spl.add_widget(Label(''))
    ## return spl
    return w


def build_info(captions, orientation='vertical'):
    box = Box(orientation=orientation)
    box.set_spacing(2)

    numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)
    if (numcols % 2) != 0:
        raise ValueError("Column spec is not an even number")
    numcols = int(numcols // 2)
    table = GridBox(rows=numrows, columns=numcols)
    table.set_row_spacing(2)
    table.set_column_spacing(4)
    #box.pack_start(table, False, False, 0)
    box.add_widget(table, stretch=0)

    wb = Bunch.Bunch()
    row = 0
    for tup in captions:
        col = 0
        while col < numcols:
            idx = col * 2
            if idx < len(tup):
                title, wtype = tup[idx:idx + 2]
                title, disp = translate_caption(title, wtype)
                if not title.endswith(':'):
                    name = name_mangle(title)
                else:
                    name = name_mangle('lbl_' + title[:-1])
                w = make_widget(disp, wtype)
                table.add_widget(w, row, col)
                wb[name] = w
            col += 1
        row += 1

    w = hadjust(box, orientation=orientation)

    return w, wb


def wrap(native_widget):
    wrapper = WidgetBase()
    wrapper.widget = native_widget
    return wrapper


# END
