#
# Widgets.py -- wrapped Qt widgets and convenience functions
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
from functools import reduce

from ginga.qtw.QtHelp import QtGui, QtCore, QTextCursor, \
     QIcon, QPixmap, QImage
from ginga.qtw import QtHelp, QtMain

from ginga.misc import Callback, Bunch
import ginga.icons

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]

class WidgetError(Exception):
    """For errors thrown in this module."""
    pass

# BASE

class WidgetBase(Callback.Callbacks):

    def __init__(self):
        super(WidgetBase, self).__init__()

        self.widget = None
        self.changed = False

    def get_widget(self):
        return self.widget

    def set_tooltip(self, text):
        self.widget.setToolTip(text)

    def set_enabled(self, tf):
        self.widget.setEnabled(tf)


# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text=''):
        super(TextEntry, self).__init__()

        self.widget = QtGui.QLineEdit()
        self.widget.setText(text)
        self.widget.returnPressed.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.make_callback('activated')

    def get_text(self):
        return self.widget.text()

    def set_text(self, text):
        self.widget.setText(text)

    def set_length(self, numchars):
        # this is only supposed to set the visible length (but Qt doesn't
        # really have a good way to do that)
        #self.widget.setMaxLength(numchars)
        pass

class TextEntrySet(WidgetBase):
    def __init__(self, text=''):
        super(TextEntrySet, self).__init__()

        self.widget = QtHelp.HBox()
        self.entry = QtGui.QLineEdit()
        self.entry.setText(text)
        layout = self.widget.layout()
        layout.addWidget(self.entry, stretch=1)
        self.btn = QtGui.QPushButton('Set')
        self.entry.returnPressed.connect(self._cb_redirect)
        self.btn.clicked.connect(self._cb_redirect)
        layout.addWidget(self.btn, stretch=0)

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.make_callback('activated')

    def get_text(self):
        return self.entry.text()

    def set_text(self, text):
        self.entry.setText(text)

    def set_length(self, numchars):
        # this is only supposed to set the visible length (but Qt doesn't
        # really have a good way to do that)
        #self.widget.setMaxLength(numchars)
        pass

class GrowingTextEdit(QtGui.QTextEdit):

    def __init__(self, *args, **kwargs):
        super(GrowingTextEdit, self).__init__(*args, **kwargs)
        self.document().documentLayout().documentSizeChanged.connect(
            self.sizeChange)
        self.heightMin = 0
        self.heightMax = 65000

    def sizeChange(self):
        docHeight = self.document().size().height()
        # add some margin to prevent auto scrollbars
        docHeight += 20
        if self.heightMin <= docHeight <= self.heightMax:
            self.setMaximumHeight(docHeight)


class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        #tw = QtGui.QTextEdit()
        tw = GrowingTextEdit()
        tw.setReadOnly(not editable)
        if wrap:
            tw.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        else:
            tw.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.widget = tw

    def append_text(self, text, autoscroll=True):
        if text.endswith('\n'):
            text = text[:-1]
        self.widget.append(text)
        if not autoscroll:
            return

        self.widget.moveCursor(QTextCursor.End)
        self.widget.moveCursor(QTextCursor.StartOfLine)
        self.widget.ensureCursorVisible()

    def get_text(self):
        return self.widget.document().toPlainText()

    def clear(self):
        self.widget.clear()

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_limit(self, numlines):
        #self.widget.setMaximumBlockCount(numlines)
        pass

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
        self.make_callback('activated')


class ComboBox(WidgetBase):
    def __init__(self, editable=False):
        super(ComboBox, self).__init__()

        self.widget = QtHelp.ComboBox()
        self.widget.setEditable(editable)
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

    def clear(self):
        self.widget.clear()

    def show_text(self, text):
        index = self.widget.findText(text)
        self.set_index(index)

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
            w = QtGui.QDoubleSpinBox()
        else:
            w = QtGui.QSpinBox()
        w.valueChanged.connect(self._cb_redirect)
        # should values wrap around
        w.setWrapping(False)
        self.widget = w

        self.enable_callback('value-changed')

    def _cb_redirect(self, val):
        if self.changed:
            self.changed = False
            return
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.value()

    def set_value(self, val):
        self.changed = True
        self.widget.setValue(val)

    def set_decimals(self, num):
        self.widget.setDecimals(num)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget
        adj.setRange(minval, maxval)
        adj.setSingleStep(incr_value)


class Slider(WidgetBase):
    def __init__(self, orientation='horizontal', track=False):
        super(Slider, self).__init__()

        if orientation == 'horizontal':
            w = QtGui.QSlider(QtCore.Qt.Horizontal)
        else:
            w = QtGui.QSlider(QtCore.Qt.Vertical)
        # this controls whether the callbacks are made *as the user
        # moves the slider* or afterwards
        w.setTracking(track)
        w.setTickPosition(QtGui.QSlider.TicksBelow)
        self.widget = w
        w.valueChanged.connect(self._cb_redirect)

        self.enable_callback('value-changed')

    def _cb_redirect(self, val):
        if self.changed:
            self.changed = False
            return
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.value()

    def set_value(self, val):
        self.changed = True
        self.widget.setValue(val)

    def set_tracking(self, tf):
        self.widget.setTracking(tf)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget
        adj.setRange(minval, maxval)
        adj.setSingleStep(incr_value)


class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        if orientation == 'horizontal':
            self.widget = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        else:
            self.widget = QtGui.QScrollBar(QtCore.Qt.Vertical)
        self.widget.valueChanged.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self):
        val = self.widget.value()
        self.make_callback('activated', val)


class CheckBox(WidgetBase):
    def __init__(self, text=''):
        super(CheckBox, self).__init__()

        self.widget = QtGui.QCheckBox(text)
        self.widget.stateChanged.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        val = self.get_state()
        self.make_callback('activated', val)

    def set_state(self, tf):
        self.widget.setChecked(tf)

    def get_state(self):
        val = self.widget.checkState()
        # returns 0 (unchecked) or 2 (checked)
        return (val != 0)

class ToggleButton(WidgetBase):
    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        self.widget = QtGui.QPushButton(text)
        self.widget.setCheckable(True)
        self.widget.clicked.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

    def set_state(self, tf):
        self.widget.setChecked(tf)

    def get_state(self):
        return self.widget.isChecked()


class RadioButton(WidgetBase):
    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        self.widget = QtGui.QRadioButton(text)
        self.widget.toggled.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, val):
        if self.changed:
            self.changed = False
            return
        self.make_callback('activated', val)

    def set_state(self, tf):
        if self.widget.isChecked() != tf:
            # toggled only fires when the value is toggled
            self.changed = True
            self.widget.setChecked(tf)

    def get_state(self):
        return self.widget.isChecked()


class ProgressBar(WidgetBase):
    def __init__(self):
        super(ProgressBar, self).__init__()

        w = QtGui.QProgressBar()
        w.setRange(0, 100)
        w.setTextVisible(True)
        self.widget = w

    def set_value(self, pct):
        self.widget.setValue(int(pct * 100.0))

# CONTAINERS

class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        self.children = []

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def _remove(self, childw, delete=False):
        self.widget.layout().removeWidget(childw)
        childw.setParent(None)
        if delete:
            childw.deleteLater()

    def remove(self, w, delete=False):
        if not w in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(w)

        self._remove(w.get_widget(), delete=delete)

    def remove_all(self):
        for w in list(self.children):
            self.remove(w)

    def get_children(self):
        return self.children

class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.orientation = orientation
        if orientation == 'horizontal':
            self.widget = QtHelp.HBox()
        else:
            self.widget = QtHelp.VBox()

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w, stretch=stretch)

    def set_spacing(self, val):
        self.widget.layout().setSpacing(val)

    def set_margins(self, left, right, top, bottom):
        self.widget.layout().setContentsMargins(left, right, top, bottom)

    def set_border_width(self, pix):
        self.widget.layout().setContentsMargins(pix, pix, pix, pix)


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')

class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')

class Frame(ContainerBase):
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
            #lbl.setAlignment(QtCore.Qt.AlignLeft)
            vbox.addWidget(lbl, stretch=0)
            self.label = lbl
        else:
            self.label = None

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        self.widget.layout().addWidget(child.get_widget(), stretch=stretch)


# Qt custom expander widget
# See http://stackoverflow.com/questions/10364589/equivalent-of-gtks-expander-in-pyqt4
#
class Expander(ContainerBase):
    r_arrow = None
    d_arrow = None

    # Note: add 'text-align: left;' if you want left adjusted labels
    widget_style = """
    QPushButton { margin: 1px,1px,1px,1px; padding: 0px;
                  border-width: 0px; border-style: solid; }
    """

    def __init__(self, title=''):
        super(Expander, self).__init__()

        # Qt doesn't seem to like it (segfault) if we actually construct
        # these icons in the class variable declarations
        if Expander.r_arrow is None:
            Expander.r_arrow = QtHelp.get_icon(os.path.join(icondir,
                                                            'triangle-right-48.png'),
                                               size=(12, 12))
        if Expander.d_arrow is None:
            Expander.d_arrow = QtHelp.get_icon(os.path.join(icondir,
                                                            'triangle-down-48.png'),
                                               size=(12, 12))

        self.widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self.toggle = QtGui.QPushButton(Expander.r_arrow, title)
        self.toggle.setStyleSheet(Expander.widget_style)
        #self.toggle.setCheckable(True)
        self.toggle.clicked.connect(self._toggle_widget)

        vbox.addWidget(self.toggle, stretch=0)
        self.widget.setLayout(vbox)

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w, stretch=stretch)
        child_w.setVisible(False)

    def _toggle_widget(self):
        child = self.get_children()[0]
        child_w = child.get_widget()
        #if self.toggle.isChecked():
        if child_w.isVisible():
            self.toggle.setIcon(Expander.r_arrow)
            child_w.setVisible(False)
        else:
            self.toggle.setIcon(Expander.d_arrow)
            child_w.setVisible(True)


class TabWidget(ContainerBase):
    def __init__(self, tabpos='top'):
        super(TabWidget, self).__init__()

        nb = QtGui.QTabWidget()
        if tabpos == 'top':
            nb.setTabPosition(QtGui.QTabWidget.North)
        elif tabpos == 'bottom':
            nb.setTabPosition(QtGui.QTabWidget.South)
        elif tabpos == 'left':
            nb.setTabPosition(QtGui.QTabWidget.West)
        elif tabpos == 'right':
            nb.setTabPosition(QtGui.QTabWidget.East)
        nb.currentChanged.connect(self._cb_redirect)
        self.widget = nb

    def _cb_redirect(self, index):
        self.make_callback('activated', index)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addTab(child_w, title)

    def get_index(self):
        return self.widget.getCurrentIndex()

    def set_index(self, idx):
        self.widget.setCurrentIndex(idx)

    def index_of(self, child):
        return self.widget.indexOf(child.get_widget())

class StackWidget(ContainerBase):
    def __init__(self):
        super(StackWidget, self).__init__()

        self.widget = QtHelp.StackedWidget()

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addTab(child_w, title)

    def get_index(self):
        return self.widget.getCurrentIndex()

    def set_index(self, idx):
        self.widget.setCurrentIndex(idx)

    def index_of(self, child):
        return self.widget.indexOf(child.get_widget())


class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = QtGui.QScrollArea()
        self.widget.setWidgetResizable(True)

    def set_widget(self, child):
        self.add_ref(child)
        self.widget.setWidget(child.get_widget())

class Splitter(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Splitter, self).__init__()

        w = QtGui.QSplitter()
        self.orientation = orientation
        if orientation == 'horizontal':
            w.setOrientation(QtCore.Qt.Horizontal)
        else:
            w.setOrientation(QtCore.Qt.Vertical)
        self.widget = w
        w.setStretchFactor(0, 0.5)
        w.setStretchFactor(1, 0.5)

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addWidget(child_w)


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        w = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        w.setLayout(layout)
        self.widget = w

    def set_row_spacing(self, val):
        self.widget.layout().setVerticalSpacing(val)

    def set_column_spacing(self, val):
        self.widget.layout().setHorizontalSpacing(val)

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        w = child.get_widget()
        self.widget.layout().addWidget(w, row, col)


class ToolbarAction(WidgetBase):
    def __init__(self):
        super(ToolbarAction, self).__init__()

        self.widget = None
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.widget.isCheckable():
            tf = self.widget.isChecked()
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')

    def set_state(self, tf):
        self.widget.setChecked(tf)

    def get_state(self):
        return self.widget.isChecked()


class Toolbar(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Toolbar, self).__init__()

        w = QtGui.QToolBar()
        if orientation == 'horizontal':
            w.setOrientation(QtCore.Qt.Horizontal)
        else:
            w.setOrientation(QtCore.Qt.Vertical)
        self.widget = w

    def add_action(self, text, toggle=False, iconpath=None):
        child = ToolbarAction()
        if iconpath:
            image = QImage(iconpath)
            qsize = QtCore.QSize(24, 24)
            image = image.scaled(qsize)
            pixmap = QPixmap.fromImage(image)
            iconw = QIcon(pixmap)
            action = self.widget.addAction(iconw, text,
                                           child._cb_redirect)
        else:
            action = self.widget.addAction(text, child._cb_redirect)
        action.setCheckable(toggle)
        child.widget = action
        self.add_ref(child)
        return child

    def add_widget(self, child):
        self.add_ref(child)
        w = child.get_widget()
        self.widget.addWidget(w)

    def add_separator(self):
        self.widget.addSeparator()


class MenuAction(WidgetBase):
    def __init__(self, text=None):
        super(MenuAction, self).__init__()

        self.widget = None
        self.text = text
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.widget.isCheckable():
            tf = self.widget.isChecked()
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')


class Menu(ContainerBase):
    def __init__(self):
        super(Menu, self).__init__()

        # this ends up being a reference to the Qt menubar or toolbar
        self.widget = None

    def add_widget(self, child):
        child.widget = self.widget.addAction(child.text,
                                             lambda: child._cb_redirect())
        self.add_ref(child)

    def add_name(self, name):
        child = MenuAction(text=name)
        self.add_widget(child)
        return child

    def add_separator(self):
        self.widget.addSeparator()


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = QtGui.QMenuBar()

    def add_widget(self, child):
        menu_w = child.get_widget()
        self.widget.addMenu(menu_w)
        self.add_ref(child)

    def add_name(self, name):
        menu_w = self.widget.addMenu(name)
        child = Menu()
        child.widget = menu_w
        self.add_ref(child)
        return child


class TopLevel(ContainerBase):
    def __init__(self, title=None):
        super(TopLevel, self).__init__()

        widget = QtHelp.TopLevel()
        self.widget = widget
        box = QtGui.QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        widget.setLayout(box)
        widget.closeEvent = lambda event: self._quit(event)

        if not title is None:
            widget.setWindowTitle(title)

        self.enable_callback('closed')

    def set_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w)

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def _quit(self, event):
        event.accept()
        self.close()

    def _closeEvent(*args):
        self.close()

    def close(self):
        self.widget.deleteLater()
        #self.widget = None

        self.make_callback('closed')

    def raise_(self):
        self.widget.raise_()
        self.widget.activateWindow()

    def lower(self):
        self.widget.lower()

    def resize(self, width, height):
        self.widget.resize(width, height)

    def focus(self):
        self.widget.raise_()
        self.widget.activateWindow()

    def move(self, x, y):
        self.widget.moveTo(x, y)

    def maximize(self):
        self.widget.showMaximized()

    def unmaximize(self):
        self.widget.showNormal()

    def fullscreen(self):
        self.widget.showFullScreen()

    def unfullscreen(self):
        self.widget.showNormal()

    def iconify(self):
        self.hide()

    def uniconify(self):
        self.widget.showNormal()

    def set_title(self, title):
        self.widget.setWindowTitle(title)


class Application(QtMain.QtMain):

    def __init__(self, *args, **kwdargs):
        super(Application, self).__init__(*args, **kwdargs)

        self.window_list = []

    def window(self, title=None):
        w = TopLevel(title=title)
        self.window_list.append(w)
        return w


class SaveDialog(QtGui.QFileDialog):
    def __init__(self, title=None, selectedfilter=None):
        super(SaveDialog, self).__init__()

        self.selectedfilter = selectedfilter
        self.widget = self.getSaveFileName(self, title, '', selectedfilter)

    def get_path(self):
        if self.widget and not self.widget.endswith(self.selectedfilter[1:]):
            self.widget += self.selectedfilter[1:]
        return self.widget

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
        w.widget.setAlignment(QtCore.Qt.AlignRight)
    elif wtype == 'llabel':
        w = Label(title)
        w.widget.setAlignment(QtCore.Qt.AlignLeft)
    elif wtype == 'entry':
        w = TextEntry()
        #w.widget.setMaxLength(12)
    elif wtype == 'entryset':
        w = TextEntrySet()
        #w.widget.setMaxLength(12)
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
                    name = name_mangle(title)
                else:
                    name = name_mangle('lbl_'+title[:-1])
                w = make_widget(title, wtype)
                table.addWidget(w.widget, row, col)
                wb[name] = w
            col += 1
        row += 1

    w = wrap(widget)
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
