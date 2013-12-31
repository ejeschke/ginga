#
# Widgets.py -- wrapped Qt widgets and convenience functions
# 
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from ginga.qtw.QtHelp import QtGui, QtCore
from ginga.qtw import QtHelp

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

        self.widget = QtGui.QLineEdit()
        self.widget.setText(text)
        self.widget.returnPressed.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self):
        value = self.widget.text()
        self.make_callback('activated', value)

    def get_text(self):
        return self.widget.text()
    
    def set_text(self, text):
        self.widget.setText(text)

    def set_length(self, numchars):
        self.widget.setMaxLength(numchars)
    
    
class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        tw = QtGui.QTextEdit()
        tw.setReadOnly(not editable)
        if wrap:
            tw.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        else:
            tw.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.widget = tw

    def append_text(self, text, autoscroll=True):
        self.widget.append(text)
        if not autoscroll:
            return

        self.widget.moveCursor(QtGui.QTextCursor.End)
        self.widget.moveCursor(QtGui.QTextCursor.StartOfLine)
        self.widget.ensureCursorVisible()
            
    def get_text(self):
        return self.widget.text()
    
    def clear(self):
        self.widget.clear()

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_limit(self, numlines):
        self.widget.setMaximumBlockCount(numlines)
    
    def set_font(self, font):
        self.widget.setCurrentFont(font)
        
    def set_wrap(self, tf):
        if tf:
            self.widget.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        else:
            self.widget.setLineWrapMode(QtGui.QTextEdit.NoWrap)
    
class Label(WidgetBase):
    def __init__(self, text=''):
        super(Label, self).__init__()

        self.widget = QtGui.QLabel(text)

    def get_text(self):
        return self.widget.text()
    
    def set_text(self, text):
        self.widget.setText(text)

    
class Button(WidgetBase):
    def __init__(self, text=''):
        super(Button, self).__init__()

        self.widget = QtGui.QPushButton(text)
        self.widget.clicked.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        print "_CB", args
        self.make_callback('activated')

    
class ComboBox(WidgetBase):
    def __init__(self):
        super(ComboBox, self).__init__()

        self.widget = QtHelp.ComboBox()
        self.widget.activated.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self):
        idx = self.widget.currentIndex()
        self.make_callback('activated', idx)

    def insert_alpha(self, text):
        index = 0
        while True:
            itemText = self.widget.itemText(index)
            if len(itemText) == 0:
                break
            if itemText > text:
                self.widget.insertItem(index, text)
                return
            index += 1
        self.widget.addItem(text)
        
    def delete_alpha(self, text):
        index = self.widget.findText(text)
        self.widget.removeItem(index)

    def show_text(self, text):
        index = self.widget.findText(text)
        self.widget.setCurrentIndex(index)

    def append_text(self, text):
        self.widget.addItem(text)

    def set_index(self, index):
        self.widget.setCurrentIndex(index)

    def get_index(self):
        return self.widget.currentIndex()

    
class SpinBox(WidgetBase):
    def __init__(self, dtype=int):
        super(SpinBox, self).__init__()

        if dtype == float:
            self.widget = QtGui.QDoubleSpinBox()
        else:
            self.widget = QtGui.QSpinBox()
        self.widget.valueChanged.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

    
class Slider(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(Slider, self).__init__()

        if orientation == 'horizontal':
            self.widget = QtGui.QSlider(QtCore.Qt.Horizontal)
        else:
            self.widget = QtGui.QSlider(QtCore.Qt.Vertical)
        self.widget.activated.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)
    

class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        if orientation == 'horizontal':
            self.widget = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        else:
            self.widget = QtGui.QScrollBar(QtCore.Qt.Vertical)
        self.widget.activated.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)
    

class CheckBox(WidgetBase):
    def __init__(self, text=''):
        super(CheckBox, self).__init__()

        self.widget = QtGui.QCheckBox(text)
        self.widget.stateChanged.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)
    

class ToggleButton(WidgetBase):
    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        self.widget = QtGui.QPushButton(text)
        self.widget.setCheckable(True)
        self.widget.stateChanged.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)
    

class RadioButton(WidgetBase):
    def __init__(self, text=''):
        super(RadioButton, self).__init__()

        self.widget = QtGui.QRadioButton(text)
        self.widget.stateChanged.connect(self._cb_redirect)
        
        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

# CONTAINERS

class BoxMixin(object):
    def set_spacing(self, val):
        self.widget.layout().setSpacing(val)

    def set_margins(self, left, right, top, bottom):
        self.widget.layout().setContentsMargins(left, right, top, bottom)
        

class HBox(WidgetBase, BoxMixin):
    def __init__(self):
        super(HBox, self).__init__()

        self.widget = QtHelp.HBox()

    def add_widget(self, child, stretch=0.0):
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w, stretch=stretch,
                                       alignment=QtCore.Qt.AlignLeft)

class VBox(WidgetBase, BoxMixin):
    def __init__(self):
        super(VBox, self).__init__()

        self.widget = QtHelp.VBox()

    def add_widget(self, child, stretch=0.0):
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w, stretch=stretch,
                                       alignment=QtCore.Qt.AlignTop)

class Frame(WidgetBase):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        self.widget = QtGui.QFrame()
        self.widget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        vbox = QtGui.QVBoxLayout()
        # because of ridiculous defaults
        vbox.setContentsMargins(2, 2, 2, 2)
        self.widget.setLayout(vbox)
        if title:
            lbl = QtGui.QLabel(title)
            lbl.setAlignment(QtCore.Qt.AlignHCenter)
            vbox.addWidget(lbl, stretch=0)
            self.label = lbl
        else:
            self.label = None

    def set_widget(self, child):
        self.widget.layout().addWidget(child.get_widget())
    
class TabWidget(WidgetBase):
    def __init__(self):
        super(TabWidget, self).__init__()

        self.widget = QtGui.QTabWidget()

    def add_tab(self, tab_title, child):
        child_w = child.get_widget()
        self.widget.addTab(child_w, tab_title)

    def get_index(self):
        return self.widget.getCurrentIndex()

    def set_index(self, idx):
        self.widget.setCurrentIndex(idx)

class ScrollArea(WidgetBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = QtGui.QScrollArea()
        self.widget.setWidgetResizable(True)

    def set_widget(self, child):
        self.widget.setWidget(child.get_widget())


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
        w.widget.setAlignment(QtCore.Qt.AlignRight)
    elif wtype == 'llabel':
        w = Label(title)
        w.widget.setAlignment(QtCore.Qt.AlignLeft)
    elif wtype == 'entry':
        w = Entry()
        w.widget.setMaxLength(12)
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
        w = QtGui.QLabel('')
    else:
        raise ValueError("Bad wtype=%s" % wtype)
    return w

def build_info(captions):
    numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)
    if (numcols % 2) != 0:
        raise ValueError("Column spec is not an even number")
    numcols /= 2

    widget = QtGui.QWidget()
    table = QtGui.QGridLayout()
    widget.setLayout(table)
    table.setVerticalSpacing(2)
    table.setHorizontalSpacing(4)
    table.setContentsMargins(2, 2, 2, 2)

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
                table.addWidget(w.widget, row, col)
                wb[name] = w
            col += 1
        row += 1

    wrapper = WidgetBase()
    wrapper.widget = widget
    return wrapper, wb

#END
