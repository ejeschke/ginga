#
# Widgets.py -- wrapped Qt widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import pathlib
from functools import reduce

from ginga.qtw.QtHelp import (QtGui, QtCore, QTextCursor, QIcon, QPixmap,
                              QImage, QCursor, QFont)
from ginga.qtw import QtHelp

from ginga.misc import Callback, Bunch, Settings, LineHistory
import ginga.icons

has_webkit = False
try:
    from ginga.qtw.QtHelp import QWebView  # noqa
    has_webkit = True
except ImportError:
    pass

__all__ = ['WidgetError', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'GrowingTextEdit', 'TextArea', 'Label', 'Button', 'ComboBox',
           'SpinBox', 'Slider', 'Dial', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'ProgressBar', 'StatusBar', 'TreeView',
           'WebView', 'ContainerBase', 'Box', 'HBox', 'VBox', 'Frame',
           'Expander', 'TabWidget', 'StackWidget', 'MDIWidget', 'ScrollArea',
           'Splitter', 'GridBox', 'ToolbarAction', 'Toolbar', 'MenuAction',
           'Menu', 'Menubar', 'TopLevelMixin', 'TopLevel', 'Application',
           'Dialog', 'SaveDialog', 'DragPackage',
           'name_mangle', 'make_widget', 'hadjust', 'build_info', 'wrap',
           'has_webkit']

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]


class WidgetError(Exception):
    """For errors thrown in this module."""
    pass


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
        self.widget.setToolTip(text)

    def get_enabled(self):
        self.widget.isEnabled()

    def set_enabled(self, tf):
        self.widget.setEnabled(tf)

    def get_size(self):
        wd, ht = self.widget.width(), self.widget.height()
        return (wd, ht)

    def get_pos(self):
        x, y = self.widget.x(), self.widget.y()
        return (x, y)

    def get_app(self):
        return _app

    def delete(self):
        self.widget.deleteLater()
        self.widget = None

    def focus(self):
        self.widget.activateWindow()
        self.widget.setFocus()
        # self.widget.raise_()

    def resize(self, width, height):
        self.widget.resize(width, height)

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def is_visible(self):
        return self.widget.isVisible()

    def get_font(self, font_family, point_size):
        font = QtHelp.get_font(font_family, point_size)
        return font

    def cfg_expand(self, horizontal='fixed', vertical='fixed'):
        """WARNING: this call has specific effects dependent on the back
        end. It is not recommended to use it unless you cannot achieve the
        proper layout without it.
        """
        policy_dict = dict(fixed=QtGui.QSizePolicy.Fixed,
                           minimum=QtGui.QSizePolicy.Minimum,
                           maximum=QtGui.QSizePolicy.Maximum,
                           preferred=QtGui.QSizePolicy.Preferred,
                           expanding=QtGui.QSizePolicy.Expanding,
                           minimumexpanding=QtGui.QSizePolicy.MinimumExpanding,
                           ignored=QtGui.QSizePolicy.Ignored)
        h_policy = QtGui.QSizePolicy.Policy(policy_dict[horizontal])
        v_policy = QtGui.QSizePolicy.Policy(policy_dict[vertical])
        self.widget.setSizePolicy(QtGui.QSizePolicy(h_policy, v_policy))


# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntry, self).__init__()

        self.widget = QtGui.QLineEdit()
        self.widget.setText(text)
        self.widget.setReadOnly(not editable)
        self.widget.returnPressed.connect(self._cb_redirect)
        self.widget.keyPressEvent_org = self.widget.keyPressEvent
        self.widget.keyPressEvent = self._key_press_event

        self.history = LineHistory.LineHistory()

        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        self.history.append(self.get_text())
        self.make_callback('activated')

    def _key_press_event(self, event):
        keycode = event.key()
        if keycode in [QtCore.Qt.Key_Up]:
            try:
                self.set_text(self.history.prev())
            except ValueError:
                pass
        elif keycode in [QtCore.Qt.Key_Down]:
            try:
                self.set_text(self.history.next())
            except ValueError:
                pass
        else:
            self.widget.keyPressEvent_org(event)

    def get_text(self):
        return self.widget.text()

    def set_text(self, text):
        self.widget.setText(text)

    def set_editable(self, tf):
        self.widget.setReadOnly(not tf)

    def set_font(self, font, size=10):
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.widget.setFont(font)

    def set_length(self, numchars):
        # this is only supposed to set the visible length (but Qt doesn't
        # really have a good way to do that)
        # self.widget.setMaxLength(numchars)
        pass


class TextEntrySet(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntrySet, self).__init__()

        self.widget = QtHelp.HBox()
        self.entry = QtGui.QLineEdit()
        self.entry.setText(text)
        self.entry.setReadOnly(not editable)
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

    def set_editable(self, tf):
        self.entry.setReadOnly(not tf)

    def set_font(self, font, size=10):
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.widget.setFont(font)

    def set_length(self, numchars):
        # this is only supposed to set the visible length (but Qt doesn't
        # really have a good way to do that)
        # self.widget.setMaxLength(numchars)
        pass

    def set_enabled(self, tf):
        super(TextEntrySet, self).set_enabled(tf)
        self.entry.setEnabled(tf)


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
            self.setMaximumHeight(int(docHeight))


class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        # tw = QtGui.QTextEdit()
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

    def set_editable(self, tf):
        self.widget.setReadOnly(not tf)

    def set_limit(self, numlines):
        # self.widget.setMaximumBlockCount(numlines)
        pass

    def set_font(self, font, size=10):
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.widget.setCurrentFont(font)

    def set_wrap(self, tf):
        if tf:
            self.widget.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        else:
            self.widget.setLineWrapMode(QtGui.QTextEdit.NoWrap)


class Label(WidgetBase):
    def __init__(self, text='', halign='left', style='normal', menu=None):
        super(Label, self).__init__()

        lbl = QtGui.QLabel(text)
        if halign == 'left':
            lbl.setAlignment(QtCore.Qt.AlignLeft)
        elif halign == 'center':
            lbl.setAlignment(QtCore.Qt.AlignHCenter)
        elif halign == 'right':
            lbl.setAlignment(QtCore.Qt.AlignRight)

        self.widget = lbl
        lbl.mousePressEvent = self._cb_redirect
        lbl.mouseReleaseEvent = self._cb_redirect2

        if style == 'clickable':
            lbl.setSizePolicy(QtGui.QSizePolicy.Minimum,
                              QtGui.QSizePolicy.Minimum)
            lbl.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)

        if menu is not None:
            lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            menu_w = menu.get_widget()

            def on_context_menu(point):
                menu_w.exec(lbl.mapToGlobal(point))

            lbl.customContextMenuRequested.connect(on_context_menu)

        # Enable highlighting for copying
        # lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        self.enable_callback('activated')
        self.enable_callback('released')

    def _cb_redirect(self, event):
        buttons = event.buttons()
        if buttons & QtCore.Qt.LeftButton:
            self.make_callback('activated')

    def _cb_redirect2(self, event):
        buttons = event.buttons()
        if buttons & QtCore.Qt.LeftButton:
            self.make_callback('released')

    def get_text(self):
        return self.widget.text()

    def set_text(self, text):
        self.widget.setText(text)

    def set_font(self, font, size=10):
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.widget.setFont(font)

    def set_color(self, fg=None, bg=None):
        self.widget.setStyleSheet(
            "QLabel { background-color: %s; color: %s; }" % (bg, fg))

    def set_halign(self, align):
        # TODO: set horizontal alignment of text
        pass


class Button(WidgetBase):
    def __init__(self, text=''):
        super(Button, self).__init__()

        self.widget = QtGui.QPushButton(text)
        self.widget.clicked.connect(self._cb_redirect)

        self.enable_callback('activated')

    def set_text(self, text):
        self.widget.setText(text)

    def get_text(self):
        return self.widget.text()

    def _cb_redirect(self, *args):
        self.make_callback('activated')


class ComboBox(WidgetBase):
    def __init__(self, editable=False):
        super(ComboBox, self).__init__()

        self.widget = QtHelp.ComboBox()
        self.widget.setSizeAdjustPolicy(QtGui.QComboBox.AdjustToContents)
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

    def get_alpha(self, idx):
        return self.widget.itemText(idx)

    def clear(self):
        self.widget.clear()

    def set_text(self, text):
        self.widget.blockSignals(True)
        index = self.widget.findText(text)
        if index >= 0:
            self.set_index(index)
        else:
            self.widget.setEditText(text)
        self.widget.blockSignals(False)

    # to be deprecated someday
    show_text = set_text

    def get_text(self):
        idx = self.get_index()
        return self.get_alpha(idx)

    def append_text(self, text):
        self.widget.addItem(text)

    def set_index(self, index):
        self.widget.blockSignals(True)
        self.widget.setCurrentIndex(index)
        self.widget.blockSignals(False)

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
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.value()

    def set_value(self, val):
        self.widget.blockSignals(True)
        self.widget.setValue(val)
        self.widget.blockSignals(False)

    def set_decimals(self, num):
        if hasattr(self.widget, 'setDecimals'):
            # only for QDoubleSpinBox
            self.widget.setDecimals(num)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget
        adj.setRange(minval, maxval)
        adj.setSingleStep(incr_value)


class Slider(WidgetBase):
    def __init__(self, orientation='horizontal', dtype=int, track=False):
        super(Slider, self).__init__()

        # NOTE: parameter dtype is ignored for now for Qt

        if orientation == 'horizontal':
            w = QtGui.QSlider(QtCore.Qt.Horizontal)
            w.setTickPosition(QtGui.QSlider.TicksBelow)
        else:
            w = QtGui.QSlider(QtCore.Qt.Vertical)
            w.setTickPosition(QtGui.QSlider.TicksRight)
        # w.setTickPosition(QtGui.QSlider.NoTicks)
        # this controls whether the callbacks are made *as the user
        # moves the slider* or afterwards
        w.setTracking(track)
        self.widget = w
        w.valueChanged.connect(self._cb_redirect)

        self.enable_callback('value-changed')

    def _cb_redirect(self, val):
        self.make_callback('value-changed', val)

    def get_value(self):
        return self.widget.value()

    def set_value(self, val):
        self.widget.blockSignals(True)
        self.widget.setValue(val)
        self.widget.blockSignals(False)

    def set_tracking(self, tf):
        self.widget.setTracking(tf)

    def set_limits(self, minval, maxval, incr_value=1):
        adj = self.widget
        adj.setRange(minval, maxval)
        adj.setSingleStep(incr_value)


class Dial(WidgetBase):
    def __init__(self, dtype=float, wrap=False, track=False):
        super(Dial, self).__init__()

        w = QtGui.QDial()
        w.setWrapping(wrap)
        w.setNotchesVisible(True)

        self._precision = 10000
        w.setRange(0, self._precision)
        w.setSingleStep(int(self._precision / 100))
        self.dtype = dtype
        self.min_val = dtype(0)
        self.max_val = dtype(100)
        self.inc_val = dtype(1)

        # this controls whether the callbacks are made *as the user
        # moves the slider* or afterwards
        w.setTracking(track)
        self.widget = w
        w.valueChanged.connect(self._cb_redirect)

        self.enable_callback('value-changed')

    def _cb_redirect(self, val):
        val = self.get_value()
        self.make_callback('value-changed', val)

    def _cvt_value_out(self, int_val):
        pct = int_val / self._precision
        rng = self.max_val - self.min_val
        val = self.dtype(self.min_val + pct * rng)
        return val

    def _cvt_value_in(self, ext_val):
        rng = self.max_val - self.min_val
        pct = (ext_val - self.min_val) / rng
        val = int(pct * self._precision)
        return val

    def get_value(self):
        int_val = self.widget.value()
        return self._cvt_value_out(int_val)

    def set_value(self, val):
        if val < self.min_val or val > self.max_val:
            raise ValueError("Value '{}' is out of range".format(val))
        self.changed = True
        int_val = self._cvt_value_in(val)
        self.widget.blockSignals(True)
        self.widget.setValue(int_val)
        self.widget.blockSignals(False)

    def set_tracking(self, tf):
        self.widget.setTracking(tf)

    def set_limits(self, minval, maxval, incr_value=1):
        self.min_val = minval
        self.max_val = maxval
        self.inc_val = incr_value

        int_val = self._cvt_value_in(incr_value)
        self.widget.setSingleStep(int_val)


class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        if orientation == 'horizontal':
            self.widget = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        else:
            self.widget = QtGui.QScrollBar(QtCore.Qt.Vertical)
        self.widget.valueChanged.connect(self._cb_redirect)

        self.enable_callback('activated')

    def set_value(self, value):
        int_val = int(round(value * 100.0))
        self.widget.setValue(int_val)

    def get_value(self):
        return self.widget.value() / 100.0

    def _cb_redirect(self):
        val = self.widget.value() / 100.0
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
        self.widget.blockSignals(True)
        self.widget.setChecked(tf)
        self.widget.blockSignals(False)

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
        self.widget.blockSignals(True)
        self.widget.setChecked(tf)
        self.widget.blockSignals(False)

    def get_state(self):
        return self.widget.isChecked()


class RadioButton(WidgetBase):
    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        self.widget = QtGui.QRadioButton(text)
        self.widget.toggled.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

    def set_state(self, tf):
        if self.widget.isChecked() != tf:
            # toggled only fires when the value is toggled
            self.widget.blockSignals(True)
            self.widget.setChecked(tf)
            self.widget.blockSignals(False)

    def get_state(self):
        return self.widget.isChecked()


class Image(WidgetBase):
    def __init__(self, native_image=None, style='normal', menu=None):
        super(Image, self).__init__()

        lbl = QtGui.QLabel()
        self.widget = lbl
        if native_image is not None:
            self._set_image(native_image)

        lbl.mousePressEvent = self._cb_redirect

        if style == 'clickable':
            lbl.setSizePolicy(QtGui.QSizePolicy.Minimum,
                              QtGui.QSizePolicy.Minimum)
            # lbl.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)

        if menu is not None:
            lbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            menu_w = menu.get_widget()

            def on_context_menu(point):
                menu_w.exec(lbl.mapToGlobal(point))

            lbl.customContextMenuRequested.connect(on_context_menu)

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        buttons = event.buttons()
        if buttons & QtCore.Qt.LeftButton:
            self.make_callback('activated')

    def _set_image(self, native_image):
        pixmap = QPixmap.fromImage(native_image)
        self.widget.setPixmap(pixmap)

    def load_file(self, img_path, format=None):
        pixmap = QPixmap()
        pixmap.load(img_path, format=format)
        self.widget.setPixmap(pixmap)


class ProgressBar(WidgetBase):
    def __init__(self):
        super(ProgressBar, self).__init__()

        w = QtGui.QProgressBar()
        w.setRange(0, 100)
        w.setTextVisible(True)
        self.widget = w

    def set_value(self, pct):
        self.widget.setValue(int(pct * 100.0))


class StatusBar(WidgetBase):
    def __init__(self):
        super(StatusBar, self).__init__()

        sbar = QtGui.QStatusBar()
        sbar.setSizeGripEnabled(True)
        self.widget = sbar

    def clear_message(self):
        self.widget.showMessage('', 0)

    def set_message(self, msg_str, duration=10.0):
        # remove message in about `duration` seconds
        self.widget.showMessage(msg_str, int(duration * 1000))


class TreeWidgetItem(QtGui.QTreeWidgetItem):
    """A hack to subclass QTreeWidgetItem to enable sorting by numbers
    in a field.
    """
    def __init__(self, *args, **kwargs):
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            return float(self.text(column)) < float(otherItem.text(column))

        except ValueError:
            return self.text(column) < otherItem.text(column)


class TreeView(WidgetBase):
    def __init__(self, auto_expand=False, sortable=False,
                 selection='single', use_alt_row_color=False,
                 dragable=False):
        super(TreeView, self).__init__()

        self.auto_expand = auto_expand
        self.sortable = sortable
        self.dragable = dragable
        self.selection = selection
        self.levels = 1
        self.leaf_key = None
        self.leaf_idx = 0
        self.columns = []
        self.datakeys = []
        # shadow index
        self.shadow = {}

        tv = QtGui.QTreeWidget()
        self.widget = tv
        tv.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        if selection == 'multiple':
            tv.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        tv.setAlternatingRowColors(use_alt_row_color)
        tv.itemDoubleClicked.connect(self._cb_redirect)
        tv.itemSelectionChanged.connect(self._selection_cb)
        if self.dragable:
            tv.setDragEnabled(True)
            tv.startDrag = self._start_drag

        for cbname in ('selected', 'activated', 'drag-start'):
            self.enable_callback(cbname)

    def setup_table(self, columns, levels, leaf_key):
        self.clear()

        self.columns = columns
        self.levels = levels
        self.leaf_key = leaf_key
        treeview = self.widget
        treeview.setColumnCount(len(columns))
        treeview.setSortingEnabled(self.sortable)

        # speeds things up a bit
        treeview.setUniformRowHeights(True)

        # create the column headers
        if not isinstance(columns[0], str):
            # columns specifies a mapping
            headers = [col[0] for col in columns]
            datakeys = [col[1] for col in columns]
        else:
            headers = datakeys = columns

        self.datakeys = datakeys
        self.leaf_idx = datakeys.index(self.leaf_key)

        if self.sortable:
            # Sort increasing by default
            treeview.sortByColumn(self.leaf_idx, QtCore.Qt.AscendingOrder)

        treeview.setHeaderLabels(headers)

    def set_tree(self, tree_dict):
        self.clear()
        self.add_tree(tree_dict)

    def add_tree(self, tree_dict):

        if self.sortable:
            self.widget.setSortingEnabled(False)

        for key in tree_dict:
            self._add_subtree(1, self.shadow,
                              self.widget, key, tree_dict[key])

        if self.sortable:
            self.widget.setSortingEnabled(True)

        # User wants auto expand?
        if self.auto_expand:
            self.widget.expandAll()

    def _add_subtree(self, level, shadow, parent_item, key, node):

        if level >= self.levels:
            # leaf node
            values = ['' if _key == 'icon' else str(node[_key])
                      for _key in self.datakeys]
            try:
                bnch = shadow[key]
                item = bnch.item
                # TODO: update leaf item

            except KeyError:
                # new item
                item = TreeWidgetItem(parent_item, values)
                if level == 1:
                    parent_item.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)

                shadow[key] = Bunch.Bunch(node=node, item=item, terminal=True)

                # hack for adding an image to a table
                # TODO: add types for columns
                if 'icon' in node:
                    i = self.datakeys.index('icon')
                    item.setIcon(i, node['icon'])

                # mark cell as non-editable
                item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

        else:
            try:
                # node already exists
                bnch = shadow[key]
                item = bnch.item
                d = bnch.node

            except KeyError:
                # new node
                item = TreeWidgetItem(parent_item, [str(key)])
                if level == 1:
                    parent_item.addTopLevelItem(item)
                else:
                    parent_item.addChild(item)
                d = {}
                shadow[key] = Bunch.Bunch(node=d, item=item, terminal=False)

            # recurse for non-leaf interior node
            for key in node:
                self._add_subtree(level + 1, d, item, key, node[key])

    def _selection_cb(self):
        res_dict = self.get_selected()
        self.make_callback('selected', res_dict)

    def _cb_redirect(self, item):
        res_dict = {}
        self._get_item(res_dict, item)
        self.make_callback('activated', res_dict)

    def _get_path(self, item):
        if item is None:
            return []

        if item.childCount() == 0:
            path_rest = self._get_path(item.parent())
            myname = item.text(self.leaf_idx)
            path_rest.append(myname)
            return path_rest

        myname = item.text(0)
        path_rest = self._get_path(item.parent())
        path_rest.append(myname)
        return path_rest

    def _get_item(self, res_dict, item):
        # from the QTreeViewItem `item`, return the item via a path
        # in the dictionary `res_dict`
        path = self._get_path(item)
        d, s = res_dict, self.shadow
        for name in path[:-1]:
            d = d.setdefault(name, {})
            s = s[name].node

        dst_key = path[-1]
        try:
            d[dst_key] = s[dst_key].node
        except KeyError:
            d[dst_key] = None

    def get_selected(self):
        items = list(self.widget.selectedItems())
        res_dict = {}
        for item in items:
            if item.childCount() > 0:
                # only leaf nodes can be selected
                continue
            self._get_item(res_dict, item)
        return res_dict

    def clear(self):
        self.widget.clear()
        self.shadow = {}

    def clear_selection(self):
        self.widget.clearSelection()

    def _path_to_item(self, path):
        s = self.shadow
        for name in path[:-1]:
            s = s[name].node
        item = s[path[-1]].item
        return item

    def select_path(self, path, state=True):
        item = self._path_to_item(path)
        item.setSelected(state)

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)

        # A little painfully inefficient, can we do better than this?
        font = QtHelp.QFont()
        if not onoff:
            color = QtHelp.QColor('black')
        else:
            font.setBold(True)
            color = QtHelp.QColor(font_color)
        brush = QtHelp.QBrush(color)

        for i in range(item.columnCount()):
            item.setForeground(i, brush)
            item.setFont(i, font)

    def scroll_to_path(self, path):
        item = self._path_to_item(path)
        midx = self.widget.indexFromItem(item, 0)
        self.widget.scrollTo(midx, QtGui.QAbstractItemView.PositionAtCenter)

    def scroll_to_end(self):
        model = self.widget.model()
        midx = model.index(model.rowCount() - 1, 0)
        self.widget.scrollTo(midx, QtGui.QAbstractItemView.PositionAtBottom)

    def sort_on_column(self, i):
        self.widget.sortByColumn(i, QtCore.Qt.AscendingOrder)

    def set_column_width(self, i, width):
        self.widget.setColumnWidth(i, width)

    def set_column_widths(self, lwidths):
        for i, width in enumerate(lwidths):
            if width is not None:
                self.set_column_width(i, width)

    def set_optimal_column_widths(self):
        for i in range(len(self.columns)):
            self.widget.resizeColumnToContents(i)

    def get_column_widths(self):
        return [self.widget.columnWidth(i) for i in range(len(self.columns))]

    def _start_drag(self, event):
        res_dict = self.get_selected()
        drag_pkg = DragPackage(self.widget)
        self.make_callback('drag-start', drag_pkg, res_dict)
        drag_pkg.start_drag()


class WebView(WidgetBase):
    def __init__(self):
        if not has_webkit:
            raise NotImplementedError("Missing webkit")

        super(WebView, self).__init__()
        self.widget = QWebView()

    def load_url(self, url):
        self.widget.load(QtCore.QUrl(url))

    def load_html_string(self, html_string):
        self.widget.setHtml(html_string)

    def go_back(self):
        self.widget.back()

    def go_forward(self):
        self.widget.forward()

    def reload_page(self):
        self.widget.reload()

    def stop_loading(self):
        self.widget.stop()


# CONTAINERS

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
        layout = self.widget.layout()
        if layout is not None:
            layout.removeWidget(childw)

        childw.setParent(None)
        if delete:
            childw.deleteLater()

    def remove(self, child, delete=False):
        if child not in self.children:
            raise ValueError("Widget is not a child of this container")
        self.children.remove(child)

        self._remove(child.get_widget(), delete=delete)
        self.make_callback('widget-removed', child)

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
        try:
            return l.index(nchild)
        except (IndexError, ValueError) as e:
            return -1

    def _native_to_child(self, nchild):
        idx = self._get_native_index(nchild)
        if idx < 0:
            return None
        return self.children[idx]

    def set_margins(self, left, right, top, bottom):
        layout = self.widget.layout()
        layout.setContentsMargins(left, right, top, bottom)

    def set_border_width(self, pix):
        layout = self.widget.layout()
        layout.setContentsMargins(pix, pix, pix, pix)


class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.widget = QtGui.QWidget()
        self.orientation = orientation
        if orientation == 'horizontal':
            self.layout = QtGui.QHBoxLayout()
        else:
            self.layout = QtGui.QVBoxLayout()

        # because of ridiculous defaults
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(self.layout)

    def insert_widget(self, idx, child, stretch=0):
        self.add_ref(child)
        child_w = child.get_widget()
        self.layout.insertWidget(idx, child_w, stretch=stretch)
        self.make_callback('widget-added', child)

    def add_widget(self, child, stretch=0):
        self.add_ref(child)
        child_w = child.get_widget()
        self.layout.addWidget(child_w, stretch=stretch)
        self.make_callback('widget-added', child)

    def set_spacing(self, val):
        self.layout.setSpacing(val)


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
        self.layout = vbox
        # because of ridiculous defaults
        vbox.setContentsMargins(2, 2, 2, 2)
        self.widget.setLayout(vbox)
        if title:
            lbl = QtGui.QLabel(title)
            lbl.setAlignment(QtCore.Qt.AlignHCenter)
            # lbl.setAlignment(QtCore.Qt.AlignLeft)
            vbox.addWidget(lbl, stretch=0)
            self.label = lbl
        else:
            self.label = None

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        self.widget.layout().addWidget(child.get_widget(), stretch=stretch)

    def set_text(self, text):
        if self.label is not None:
            self.label.setText(text)


# Qt custom expander widget
# See http://stackoverflow.com/questions/10364589/equivalent-of-gtks-expander-in-pyqt4  # noqa
#
class Expander(ContainerBase):
    r_arrow = None
    d_arrow = None

    # Note: add 'text-align: left;' if you want left adjusted labels
    widget_style = """
    QPushButton { margin: 1px,1px,1px,1px; padding: 0px;
                  border-width: 0px; border-style: solid; }
    """

    def __init__(self, title='', notoggle=False):
        super(Expander, self).__init__()

        # Qt doesn't seem to like it (segfault) if we actually construct
        # these icons in the class variable declarations
        if Expander.r_arrow is None:
            Expander.r_arrow = QtHelp.get_icon(
                os.path.join(icondir, 'triangle-right-48.png'), size=(12, 12))
        if Expander.d_arrow is None:
            Expander.d_arrow = QtHelp.get_icon(
                os.path.join(icondir, 'triangle-down-48.png'), size=(12, 12))

        self.widget = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)
        self.layout = vbox

        self.toggle = None
        if not notoggle:
            toggle = ToggleButton(title)
            self.toggle = toggle
            toggle_w = toggle.get_widget()
            toggle_w.setIcon(Expander.r_arrow)
            toggle_w.setStyleSheet(Expander.widget_style)
            toggle.add_callback('activated', self._toggle_widget)
            vbox.addWidget(toggle.get_widget(), stretch=0)

        self.widget.setLayout(vbox)

        for name in ('opened', 'closed'):
            self.enable_callback(name)

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w, stretch=stretch)
        child_w.setVisible(False)

    def expand(self, tf):
        child = self.get_children()[0]
        child_w = child.get_widget()
        if tf:
            if child_w.isVisible():
                # child already open
                return
            if self.toggle is not None:
                self.toggle.get_widget().setIcon(Expander.d_arrow)
            child_w.setVisible(True)
            self.make_callback('opened')
        else:
            if not child_w.isVisible():
                # child already closed
                return
            if self.toggle is not None:
                self.toggle.get_widget().setIcon(Expander.r_arrow)
            child_w.setVisible(False)
            self.make_callback('closed')

    def _toggle_widget(self, w, tf):
        self.expand(tf)


class TabWidget(ContainerBase):
    def __init__(self, tabpos='top', reorderable=False, detachable=False,
                 group=0):
        super(TabWidget, self).__init__()

        self.reorderable = reorderable
        self.detachable = detachable

        w = QtGui.QTabWidget()
        w.currentChanged.connect(self._cb_redirect)
        w.tabCloseRequested.connect(self._tab_close)
        w.setUsesScrollButtons(True)
        # w.setTabsClosable(True)
        if self.reorderable:
            w.setMovable(True)
        # w.tabInserted = self._tab_insert_cb
        # w.tabRemoved = self._tab_remove_cb
        self.widget = w
        self.set_tab_position(tabpos)

        for name in ('page-switch', 'page-close', 'page-move', 'page-detach'):
            self.enable_callback(name)

    def set_tab_position(self, tabpos):
        w = self.widget
        if tabpos == 'top':
            w.setTabPosition(QtGui.QTabWidget.North)
        elif tabpos == 'bottom':
            w.setTabPosition(QtGui.QTabWidget.South)
        elif tabpos == 'left':
            w.setTabPosition(QtGui.QTabWidget.West)
        elif tabpos == 'right':
            w.setTabPosition(QtGui.QTabWidget.East)

    def _cb_redirect(self, index):
        # get new index, because passed index can be out of date
        index = self.get_index()
        child = self.index_to_widget(index)
        if child is not None:
            self.make_callback('page-switch', child)

    def _tab_close(self, index):
        child = self.index_to_widget(index)
        self.make_callback('page-close', child)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addTab(child_w, title)
        # attach title to child
        child.extdata.tab_title = title
        self.make_callback('widget-added', child)

    def _remove(self, nchild, delete=False):
        idx = self.widget.indexOf(nchild)
        self.widget.removeTab(idx)

        nchild.setParent(None)
        if delete:
            nchild.deleteLater()

    def get_index(self):
        return self.widget.currentIndex()

    def set_index(self, idx):
        self.widget.setCurrentIndex(idx)
        # child = self.index_to_widget(idx)
        # child.focus()

    def index_of(self, child):
        return self.widget.indexOf(child.get_widget())

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        nchild = self.widget.widget(idx)
        if nchild is None:
            return nchild
        return self._native_to_child(nchild)

    def highlight_tab(self, idx, tf):
        tabbar = self.widget.tabBar()
        if not tf:
            color = QtHelp.QColor('black')
        else:
            color = QtHelp.QColor('green')
        tabbar.setTabTextColor(idx, color)


class StackWidget(ContainerBase):
    def __init__(self):
        super(StackWidget, self).__init__()

        self.widget = QtGui.QStackedWidget()

        for name in ['page-switch']:
            self.enable_callback(name)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addWidget(child_w)
        # attach title to child
        child.extdata.tab_title = title
        self.make_callback('widget-added', child)

    def get_index(self):
        return self.widget.currentIndex()

    def set_index(self, idx):
        _idx = self.widget.currentIndex()
        self.widget.setCurrentIndex(idx)

        child = self.index_to_widget(idx)
        if _idx != idx:
            self.make_callback('page-switch', child)
        # child.focus()

    def index_of(self, child):
        return self.widget.indexOf(child.get_widget())

    def index_to_widget(self, idx):
        nchild = self.widget.widget(idx)
        return self._native_to_child(nchild)


class MDIWidget(ContainerBase):
    def __init__(self, tabpos='top', mode='mdi'):
        super(MDIWidget, self).__init__()

        w = QtGui.QMdiArea()
        w.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        w.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        # See note below in add_widget()
        #w.subWindowActivated.connect(self._cb_redirect)

        # w.setSizePolicy(QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding,
        #                                   QtGui.QSizePolicy.Expanding))
        w.setTabsClosable(True)
        w.setTabsMovable(False)
        self.widget = w
        self.true_mdi = True
        self.cur_index = -1

        for name in ('page-switch', 'page-close'):
            self.enable_callback(name)

        self.set_tab_position(tabpos)
        self.set_mode(mode)

    def set_tab_position(self, tabpos):
        w = self.widget
        if tabpos == 'top':
            w.setTabPosition(QtGui.QTabWidget.North)
        elif tabpos == 'bottom':
            w.setTabPosition(QtGui.QTabWidget.South)
        elif tabpos == 'left':
            w.setTabPosition(QtGui.QTabWidget.West)
        elif tabpos == 'right':
            w.setTabPosition(QtGui.QTabWidget.East)

    def get_mode(self):
        if self.widget.viewMode() == QtGui.QMdiArea.TabbedView:
            return 'tabs'
        return 'mdi'

    def set_mode(self, mode):
        mode = mode.lower()
        if mode == 'tabs':
            self.widget.setViewMode(QtGui.QMdiArea.TabbedView)
        elif mode == 'mdi':
            self.widget.setViewMode(QtGui.QMdiArea.SubWindowView)
        else:
            raise ValueError("Don't understand mode='%s'" % (mode))

    def _cb_redirect(self, subwin):
        if subwin is not None:
            nchild = subwin.widget()
            child = self._native_to_child(nchild)
            try:
                self.cur_index = self.children.index(child)
            except Exception:
                self.cur_index = -1
            self.make_callback('page-switch', child)

    def _child_close(self, subwin, child):
        self.make_callback('page-close', child)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        subwin = MDIWindow(self, child, title=title)
        subwin.add_callback('close', self._child_close, child)

        self.make_callback('widget-added', child)
        return subwin

    def _remove(self, nchild, delete=False):
        subwins = list(self.widget.subWindowList())
        l = [sw.widget() for sw in subwins]
        try:
            idx = l.index(nchild)
            subwin = subwins[idx]
        except (IndexError, ValueError) as e:
            subwin = None

        if subwin is not None:
            self.widget.removeSubWindow(subwin)
            subwin.deleteLater()

        nchild.setParent(None)
        if delete:
            nchild.deleteLater()

    def get_index(self):
        subwin = self.widget.activeSubWindow()
        if subwin is not None:
            return self._get_native_index(subwin.widget())
        return self.cur_index

    def _get_subwin(self, widget):
        for subwin in list(self.widget.subWindowList()):
            if subwin.widget() == widget:
                return subwin
        return None

    def set_index(self, idx):
        if 0 <= idx < len(self.children):
            child = self.children[idx]
            subwin = self._get_subwin(child.widget)
            if subwin is not None:
                self.widget.setActiveSubWindow(subwin)

    def index_of(self, child):
        nchild = child.get_widget()
        return self._get_native_index(nchild)

    def index_to_widget(self, idx):
        if 0 <= idx < len(self.children):
            return self.children[idx]
        return None

    def tile_panes(self):
        self.widget.tileSubWindows()

    def cascade_panes(self):
        self.widget.cascadeSubWindows()

    def use_tabs(self, tf):
        if tf:
            self.widget.setViewMode(QtGui.QMdiArea.TabbedView)
        else:
            self.widget.setViewMode(QtGui.QMdiArea.SubWindowView)


class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = QtGui.QScrollArea()
        self.widget.setWidgetResizable(True)
        self.widget._resizeEvent = self.widget.resizeEvent
        self.widget.resizeEvent = self._resize_cb

        self.enable_callback('configure')

    def _resize_cb(self, event):
        self.widget._resizeEvent(event)

        rect = self.widget.geometry()
        x1, y1, x2, y2 = rect.getCoords()
        width = x2 - x1
        height = y2 - y1
        self.make_callback('configure', width, height)

    def set_widget(self, child):
        self.add_ref(child)
        self.widget.setWidget(child.get_widget())

    def scroll_to_end(self, vertical=True, horizontal=False):
        area = self.widget
        if vertical:
            area.verticalScrollBar().setValue(
                area.verticalScrollBar().maximum())
        if horizontal:
            area.horizontalScrollBar().setValue(
                area.horizontalScrollBar().maximum())


class Splitter(ContainerBase):
    def __init__(self, orientation='horizontal', thumb_px=8):
        super(Splitter, self).__init__()

        self.thumb_px = thumb_px

        w = QtGui.QSplitter()
        self.orientation = orientation
        # NOTE: need to style splitter due to lack of any visual
        # indicator on Linux and Windows
        if self.orientation == 'horizontal':
            w.setOrientation(QtCore.Qt.Horizontal)
            if thumb_px is not None:
                iconfile = pathlib.Path(icondir) / 'vdots.png'
                w.setStyleSheet(
                    """
                    QSplitter::handle { width: %spx; height: %spx;
                                        image: url(%s); }
                    """ % (self.thumb_px, self.thumb_px, iconfile))
        else:
            w.setOrientation(QtCore.Qt.Vertical)
            if thumb_px is not None:
                iconfile = pathlib.Path(icondir) / 'hdots.png'
                w.setStyleSheet(
                    """
                    QSplitter::handle { height: %spx; image: url(%s); }
                    """ % (self.thumb_px, iconfile))
        self.widget = w
        w.setChildrenCollapsible(True)

    def add_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.addWidget(child_w)
        self.make_callback('widget-added', child)

    def get_sizes(self):
        return list(self.widget.sizes())

    def set_sizes(self, sizes):
        return self.widget.setSizes(sizes)


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        w = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        w.setLayout(layout)
        self.widget = w

    def resize_grid(self, rows, columns):
        pass

    def set_row_spacing(self, val):
        self.widget.layout().setVerticalSpacing(val)

    def set_column_spacing(self, val):
        self.widget.layout().setHorizontalSpacing(val)

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        w = child.get_widget()
        self.widget.layout().addWidget(w, row, col)
        self.make_callback('widget-added', child)

    def insert_cell(self, row, col):
        raise NotImplementedError("insert_cell needs to be implemented!")

    def insert_row(self, index):
        raise NotImplementedError("insert_row needs to be implemented!")

    def append_row(self):
        raise NotImplementedError("append_row needs to be implemented!")

    def delete_row(self, index):
        raise NotImplementedError("delete_row needs to be implemented!")


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
        self._menu = None
        self.widget.setStyleSheet(
            """
            QToolBar { padding: 0; spacing: 0; }\n
            QToolBar QToolButton { padding: 0; margin: 0; }\n
            """)

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        child = ToolbarAction()
        if iconpath:
            image = QImage(iconpath)
            wd, ht = 24, 24
            if iconsize is not None:
                wd, ht = iconsize
            qsize = QtCore.QSize(wd, ht)
            image = image.scaled(qsize)
            pixmap = QPixmap.fromImage(image)
            iconw = QIcon(pixmap)
            action = self.widget.addAction(iconw, text,
                                           child._cb_redirect)
            if text is not None and len(text) > 0:
                self.widget.setToolButtonStyle(QtCore.Qt.ToolButtonTextUnderIcon)
        else:
            action = self.widget.addAction(text, child._cb_redirect)
        action.setCheckable(toggle)
        child.widget = action
        self.add_ref(child)
        return child

    def add_widget(self, child):
        self.add_ref(child)
        w = child.get_widget()
        # in toolbars, generally don't want widgets to take up any more
        # space than necessary
        w.setSizePolicy(QtGui.QSizePolicy.Fixed,
                        QtGui.QSizePolicy.Fixed)
        self.widget.addWidget(w)
        self.make_callback('widget-added', child)

    def add_menu(self, text, menu=None, mtype='tool'):
        if menu is None:
            menu = Menu()
        if mtype == 'tool':
            child = self.add_action(text)
        else:
            child = Label(text, style='clickable', menu=menu)
            self.add_widget(child)
            child.add_callback('released', lambda w: menu.hide())

        child.add_callback('activated', lambda w: menu.popup())
        return menu

    def add_separator(self):
        self.widget.addSeparator()


class MenuAction(WidgetBase):
    def __init__(self, text=None, checkable=False):
        super(MenuAction, self).__init__()

        self.widget = None
        self.text = text
        self.checkable = checkable
        self.enable_callback('activated')

    def set_state(self, tf):
        if not self.checkable:
            raise ValueError("Not a checkable menu item")
        self.widget.setChecked(tf)

    def get_state(self):
        return self.widget.isChecked()

    def _cb_redirect(self, *args):
        if self.widget.isCheckable():
            tf = self.widget.isChecked()
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')


class Menu(ContainerBase):
    def __init__(self):
        super(Menu, self).__init__()

        # NOTE: this get's overwritten if created from Menubar
        self.widget = QtGui.QMenu()
        self.menus = Bunch.Bunch(caseless=True)

    def add_widget(self, child):
        w = self.widget.addAction(child.text, lambda: child._cb_redirect())
        if child.checkable:
            w.setCheckable(True)
        child.widget = w
        self.add_ref(child)
        self.make_callback('widget-added', child)

    def add_name(self, name, checkable=False):
        child = MenuAction(text=name, checkable=checkable)
        self.add_widget(child)
        return child

    def add_menu(self, name):
        menu_w = self.widget.addMenu(name)
        child = Menu()
        child.widget = menu_w
        self.add_ref(child)
        self.menus[name] = child
        return child

    def add_separator(self):
        self.widget.addSeparator()

    def popup(self, widget=None):
        if widget is not None:
            w = widget.get_widget()
            if w.isEnabled():
                # self.widget.popup(w.mapToGlobal(QtCore.QPoint(0, 0)))
                self.widget.exec(w.mapToGlobal(QtCore.QPoint(0, 0)))
        else:
            if self.widget.isEnabled():
                self.widget.exec(QCursor.pos())

    def get_menu(self, name):
        return self.menus[name]


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = QtGui.QMenuBar()
        if hasattr(self.widget, 'setNativeMenuBar'):
            self.widget.setNativeMenuBar(False)
        self.menus = Bunch.Bunch(caseless=True)

    def add_widget(self, child, name):
        if not isinstance(child, Menu):
            raise ValueError("child widget needs to be a Menu object")
        menu_w = self.widget.addMenu(name)
        child.widget = menu_w
        self.add_ref(child)
        self.menus[name] = child
        self.make_callback('widget-added', child)
        return child

    def add_name(self, name):
        menu_w = self.widget.addMenu(name)
        child = Menu()
        child.widget = menu_w
        self.add_ref(child)
        self.menus[name] = child
        return child

    def get_menu(self, name):
        return self.menus[name]


class TopLevelMixin(object):

    def __init__(self, title=None):

        self.widget.closeEvent = lambda event: self._quit(event)
        self.widget.destroyed = self._destroyed_cb

        if title is not None:
            self.widget.setWindowTitle(title)

        self.enable_callback('close')

    def _quit(self, event):
        # event.accept()
        # let application decide how to handle this
        event.ignore()
        self.close()

    def _closeEvent(self, *args):
        self.close()

    def close(self):
        # self.widget.deleteLater()
        # self.widget = None
        self.make_callback('close')

    def _destroyed_cb(self, event, *args):
        event.accept()

    def raise_(self):
        self.widget.raise_()
        self.widget.activateWindow()

    def lower(self):
        self.widget.lower()

    def focus(self):
        self.widget.raise_()
        self.widget.activateWindow()

    def move(self, x, y):
        self.widget.move(x, y)

    def maximize(self):
        self.widget.showMaximized()

    def unmaximize(self):
        self.widget.showNormal()

    def is_maximized(self):
        return self.widget.isMaximized()

    def fullscreen(self):
        self.widget.showFullScreen()

    def unfullscreen(self):
        self.widget.showNormal()

    def is_fullscreen(self):
        return self.widget.isFullScreen()

    def iconify(self):
        self.hide()

    def uniconify(self):
        self.widget.showNormal()

    def set_title(self, title):
        self.widget.setWindowTitle(title)


class MDIWindow(TopLevelMixin, WidgetBase):
    def __init__(self, parent, child, title=''):
        """NOTE: this widget is not meant to be instantiated except *inside*
        of MDIWidget implementation.
        """
        WidgetBase.__init__(self)
        self.parent = parent
        w = QtGui.QMdiSubWindow(parent.get_widget())
        # remove Qt logo from subwindow
        w.setWindowIcon(QIcon(QPixmap(1, 1)))
        self.widget = w

        child_w = child.get_widget()
        w.setWidget(child_w)

        # NOTE: we fire the page-switch callback by intercepting the
        # focus event on the subwindow, rather than off of the
        # subWindowActivated signal because the latter fires if
        # the widget accepts focus when the mouse enters the window,
        # whereas this approach one actually has to click in the window
        # or title bar.

        def _focus_cb(event):
            if event.gotFocus():
                self.parent._cb_redirect(self.widget)

        parent_w = parent.get_widget()
        parent_w.addSubWindow(w)

        w.focusInEvent = _focus_cb
        # Monkey-patching the widget to take control of resize and move
        # events
        w._resizeEvent = w.resizeEvent
        w.resizeEvent = lambda event: self._window_resized(event, w, child)
        w._moveEvent = w.moveEvent
        w.moveEvent = lambda event: self._window_moved(event, w, child)
        w._closeEvent = w.closeEvent
        w.closeEvent = lambda event: self._window_closed(event, w, child)
        # attach title to child
        child.extdata.tab_title = title

        TopLevelMixin.__init__(self, title=title)

        # does child have a previously saved size
        size = child.extdata.get('mdi_size', None)
        if size is not None:
            wd, ht = size
            w.resize(wd, ht)

        # does child have a previously saved position
        pos = child.extdata.get('mdi_pos', None)
        if pos is not None:
            x, y = pos
            w.move(x, y)

        child.show()
        w.show()

    def _window_resized(self, event, subwin, child):
        qsize = event.size()
        wd, ht = qsize.width(), qsize.height()
        # save size into child widget metadata
        child.extdata.mdi_size = (wd, ht)
        subwin._resizeEvent(event)

    def _window_moved(self, event, subwin, child):
        qpos = event.pos()
        x, y = qpos.x(), qpos.y()
        # save position into child widget metadata
        child.extdata.mdi_pos = (x, y)
        subwin._moveEvent(event)

    def _window_closed(self, event, subwin, widget):
        # let the application deal with this if desired in page-close
        # callback
        event.ignore()
        # self.widget.removeSubWindow(subwin)

        self.make_callback('close')


class TopLevel(TopLevelMixin, ContainerBase):

    def __init__(self, title=None):
        ContainerBase.__init__(self)

        widget = QtHelp.TopLevel()
        self.widget = widget
        box = QtGui.QVBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)
        widget.setLayout(box)

        TopLevelMixin.__init__(self, title=title)

    def set_widget(self, child):
        self.add_ref(child)
        child_w = child.get_widget()
        self.widget.layout().addWidget(child_w)


class Application(Callback.Callbacks):

    def __init__(self, logger=None, settings=None):
        global _app
        super(Application, self).__init__()

        self.logger = logger
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.settings.add_defaults(use_opengl=False)

        self.window_list = []
        self.window_dict = {}
        self.wincnt = 0
        if self.settings.get('use_opengl', False):
            # ensure we are using correct version of opengl
            # NOTE: On MacOSX w/Qt it is necessary to set the default OpenGL
            # profile BEFORE creating the QApplication object, because it
            # shares the OpenGL context
            QtHelp.set_default_opengl_context()

        # NOTE: the default value of "PassThrough" allows odd scaling
        # factors that can make text and icon rendering look terrible
        # on some platforms
        if QtHelp.have_pyqt6 or QtHelp.have_pyside6:
            QtGui.QApplication.setHighDpiScaleFactorRoundingPolicy(
                QtCore.Qt.HighDpiScaleFactorRoundingPolicy.Floor)

        app = QtGui.QApplication([])
        # app.lastWindowClosed.connect(lambda *args: self._quit())
        self._qtapp = app
        _app = self

        # Get screen size
        screen = app.primaryScreen()
        rect = screen.availableGeometry()
        size = rect.size()
        self.screen_wd = size.width()
        self.screen_ht = size.height()

        # Get screen resolution
        xdpi = screen.physicalDotsPerInchX()
        ydpi = screen.physicalDotsPerInchY()
        self.screen_res = max(xdpi, ydpi)

        for name in ('shutdown', ):
            self.enable_callback(name)

    def get_screen_size(self):
        return (self.screen_wd, self.screen_ht)

    def process_events(self):
        self._qtapp.processEvents()

    def process_end(self):
        self._qtapp.quit()

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

    def make_timer(self):
        return QtHelp.Timer()

    def mainloop(self):
        self._qtapp.exec()

    def quit(self):
        self._qtapp.quit()


class Dialog(TopLevelMixin, WidgetBase):

    def __init__(self, title='', flags=None, buttons=[],
                 parent=None, modal=False):
        WidgetBase.__init__(self)

        if parent is not None:
            parent = parent.get_widget()
        self.widget = QtGui.QDialog(parent)
        self.widget.setModal(modal)

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(vbox)

        TopLevelMixin.__init__(self, title=title)

        self.content = VBox()
        vbox.addWidget(self.content.get_widget(), stretch=1)

        if len(buttons) > 0:
            hbox_w = QtGui.QWidget()
            hbox = QtGui.QHBoxLayout()
            hbox_w.setLayout(hbox)

            for name, val in buttons:
                btn = QtGui.QPushButton(name)

                def cb(val):
                    return lambda: self._cb_redirect(val)

                btn.clicked.connect(cb(val))
                hbox.addWidget(btn, stretch=0)

            vbox.addWidget(hbox_w, stretch=0)
            # self.widget.closeEvent = lambda event: self.delete()

        self.enable_callback('activated')

    def _cb_redirect(self, val):
        self.make_callback('activated', val)

    def get_content_area(self):
        return self.content


class SaveDialog(QtGui.QFileDialog):

    def __init__(self, title=None, selectedfilter=None):
        super(SaveDialog, self).__init__()

        self.title = title
        self.selectedfilter = selectedfilter
        self.widget = self

    def get_path(self):
        res = self.getSaveFileName(self, self.title, '', self.selectedfilter)

        if isinstance(res, tuple):
            res = res[0]

        if (res and self.selectedfilter is not None and
                not res.endswith(self.selectedfilter[1:])):
            res += self.selectedfilter[1:]
        if res == '':
            # user cancelled dialog
            res = None

        return res


class DragPackage(object):
    def __init__(self, src_widget):
        self.src_widget = src_widget
        self._drag = QtHelp.QDrag(self.src_widget)
        self._data = QtCore.QMimeData()
        self._drag.setMimeData(self._data)

    def set_urls(self, urls):
        _urls = [QtCore.QUrl(url) for url in urls]
        self._data.setUrls(_urls)

    def set_text(self, text):
        self._data.setText(text)

    def start_drag(self):
        self._drag.exec(QtCore.Qt.MoveAction)


# MODULE FUNCTIONS

def name_mangle(name, pfx=''):
    newname = []
    for c in name.lower():
        if not (c.isalpha() or c.isdigit() or (c == '_')):
            newname.append('_')
        else:
            newname.append(c)
    return pfx + ''.join(newname)


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


def make_widget(title, wtype):
    if wtype == 'label':
        w = Label(title)
        w.widget.setAlignment(QtCore.Qt.AlignRight)
    elif wtype == 'llabel':
        w = Label(title)
        w.widget.setAlignment(QtCore.Qt.AlignLeft)
    elif wtype == 'entry':
        w = TextEntry()
        # w.widget.setMaxLength(12)
    elif wtype == 'entryset':
        w = TextEntrySet()
        # w.widget.setMaxLength(12)
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


def build_info(captions, orientation='vertical'):
    # numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)
    if (numcols % 2) != 0:
        raise ValueError("Column spec is not an even number")
    numcols = int(numcols // 2)

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
                title, wtype = tup[idx:idx + 2]
                if not title.endswith(':'):
                    name = name_mangle(title)
                else:
                    name = name_mangle('lbl_' + title[:-1])
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

# END
