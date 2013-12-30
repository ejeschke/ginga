#
# Widgets.py -- wrapped Gtk widgets and convenience functions
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.gtkw import GtkHelp
import gtk
import gobject

from ginga.misc import Callback, Bunch

class WidgetBase(Callback.Callbacks):

    def __init__(self):
        super(WidgetBase, self).__init__()

        self.widget = None

    def get_widget(self):
        return self.widget

# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text=''):
        super(TextEntry, self).__init__()

        w = gtk.Entry()
        w.set_text(text)
        w.connect('activate', self._cb_redirect)
        self.widget = w
        
        self.enable_callback('activated')

    def _cb_redirect(self):
        value = self.widget.text()
        self.make_callback('activated', value)

    def get_text(self):
        return self.widget.get_text()
    
    def set_text(self, text):
        self.widget.set_text(text)

    def set_length(self, numchars):
        self.widget.set_width_chars(numchars)
    
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

    def append_text(self, text, autoscroll=True):
        buf = self.widget.get_buffer()
        end = buf.get_end_iter()
        buf.insert(end, text)
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
    
    def clear(self):
        buf = self.widget.get_buffer()
        start = buf.get_start_iter()
        end = buf.get_end_iter()
        buf.delete(start, end)

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_limit(self, numlines):
        # TODO
        pass
    
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
        w.connect('clicked', self._cb_redirect)
        self.widget = w
        
        self.enable_callback('activated')

    def _cb_redirect(self, w):
        self.make_callback('activated')

    
class ComboBox(WidgetBase):
    def __init__(self):
        super(ComboBox, self).__init__()

        cb = gtk.ComboBox()
        liststore = gtk.ListStore(gobject.TYPE_STRING)
        cb.set_model(liststore)
        cell = gtk.CellRendererText()
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)
        self.widget = cb
        self.widget.connect('changed', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        idx = widget.get_active()
        self.make_callback('activated', idx)

    def insert_alpha(self, text):
        model = self.widget.get_model()
        tup = (text, )
        j = 0
        for i in xrange(len(model)):
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
        for i in xrange(len(model)):
            if model[i][0] == text:
                del model[i]
                return

    def clear(self):
        model = self.widget.get_model()
        model.clear()

    def show_text(self, text):
        model = self.widget.get_model()
        for i in xrange(len(model)):
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

        self.widget = gtk.SpinButton()
        self.widget.connect('value-changed', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

    
class Slider(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(Slider, self).__init__()

        if orientation == 'horizontal':
            self.widget = gtk.HScale()
        else:
            self.widget = gtk.VScale()
        self.widget.connect('value-changed', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, range):
        val = range.get_value()
        self.make_callback('activated', val)
    

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

        self.widget = gtk.CheckButton(text)
        self.widget.connect('toggled', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)
    

class ToggleButton(WidgetBase):
    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        w = gtk.ToggleButton(text)
        w.set_mode(True)
        self.widget = w
        self.widget.connect('toggled', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)
    

class RadioButton(WidgetBase):
    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        self.widget = gtk.RadioButton(group, text)
        self.widget.connect('toggled', self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, widget):
        val = widget.get_active()
        self.make_callback('activated', val)

# CONTAINERS

class BoxMixin(object):
    def set_spacing(self, val):
        self.widget.set_spacing(val)

    def set_margins(self, left, right, top, bottom):
        # TODO: can this be made more accurate?
        self.widget.set_border_width(left)
        
    def add_widget(self, child, stretch=0.0):
        child_w = child.get_widget()
        # TODO: can this be made more accurate?
        expand = (float(stretch) != 0.0)
        self.widget.pack_start(child_w, expand=expand, fill=True)


class HBox(WidgetBase, BoxMixin):
    def __init__(self):
        super(HBox, self).__init__()

        self.widget = gtk.HBox()

class VBox(WidgetBase, BoxMixin):
    def __init__(self):
        super(VBox, self).__init__()

        self.widget = gtk.VBox()

class Frame(WidgetBase):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        fr = gtk.Frame(label=title)
        fr.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        fr.set_label_align(0.10, 0.5)
        self.widget = fr

    def set_widget(self, child):
        self.widget.add(child.get_widget())
    
class TabWidget(WidgetBase):
    def __init__(self):
        super(TabWidget, self).__init__()

        self.widget = gtk.Notebook()

    def add_tab(self, tab_title, child):
        child_w = child.get_widget()
        label = gtk.Label(tab_title)
        tab_w.append_page(widget, label)
        self.widget.addTab(child_w, label)

    def get_index(self):
        return self.widget.get_active()

    def set_index(self, idx):
        self.widget.set_active(idx)

class ScrollArea(WidgetBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        sw = gtk.ScrolledWindow()
        sw.set_border_width(2)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.widget = sw

    def set_widget(self, child):
        self.widget.add_with_viewport(child.get_widget())


# MODULE FUNCTIONS

def _name_mangle(name, pfx=''):
    newname = []
    for c in name.lower():
        if not (c.isalpha() or c.isdigit() or (c == '_')):
            newname.append('_')
        else:
            newname.append(c)
    return pfx + ''.join(newname)

def _get_widget(title, wtype):
    if wtype == 'label':
        w = Label(title)
        w.get_widget().set_alignment(0.95, 0.5)
    elif wtype == 'llabel':
        w = Label(title)
        w.get_widget().set_alignment(0.05, 0.95)
    elif wtype == 'entry':
        w = Entry()
        w.get_widget().set_width_chars(12)
    elif wtype == 'combobox':
        w = ComboBox()
    elif wtype == 'spinbutton':
        w = SpinBox(dtype=int)
    elif wtype == 'spinfloat':
        w = SpinBox(dtype=float)
    elif wtype == 'vbox':
        w = QtHelp.VBox()
    elif wtype == 'hbox':
        w = QtHelp.HBox()
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
        w = gtk.Label('')
    else:
        raise ValueError("Bad wtype=%s" % wtype)
    return w

def build_info(captions):
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
                    name = _name_mangle(title)
                else:
                    name = _name_mangle('lbl_'+title[:-1])
                w = _get_widget(title, wtype)
                table.attach(w.get_widget(), col, col+1, row, row+1,
                             xoptions=gtk.FILL, yoptions=gtk.FILL,
                             xpadding=1, ypadding=1)
                wb[name] = w
            col += 1
        row += 1

    vbox.show_all()

    wrapper = WidgetBase()
    wrapper.widget = vbox
    return wrapper, wb


#END
