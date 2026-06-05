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
                              QTextOption, QCursor, QFont, SaveDialog)
from ginga.qtw import QtHelp
from ginga.qtw.QtHelp import Timer  # noqa

from ginga import colors
from ginga.util.paths import icondir as ginga_icon_dir
from ginga.misc import Callback, Bunch, Settings, LineHistory
from ginga.util.paths import icondir, app_icon_path

__all__ = ['WidgetError', 'Widget', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'Label', 'Button', 'ComboBox', 'Timer',
           'SpinBox', 'Slider', 'Dial', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'ProgressBar', 'StatusBar', 'TreeView',
           'TableView', 'ContainerBase', 'Box', 'HBox', 'VBox', 'Frame',
           'Expander', 'FixedLayout', 'TabWidget', 'StackWidget', 'MDIWidget',
           'ScrollArea', 'Splitter', 'GridBox', 'ToolbarAction', 'Toolbar',
           'MenuAction', 'Menu', 'Menubar', 'TopLevelMixin', 'TopLevel',
           'Application', 'Dialog', 'SaveDialog', 'ColorDialog', 'FileDialog',
           'MessageDialog', 'DragPackage',
           'name_mangle', 'make_widget', 'hadjust', 'build_info', 'wrap']


class WidgetError(Exception):
    """For errors thrown in this module."""
    pass


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

    def set_tooltip(self, text):
        self.widget.setToolTip(text)

    def set_bg(self, color):
        """Set the widget's background colour.  ``color`` is a CSS
        string (``'#rrggbb'``, ``'red'``, ``'rgba(...)'``, …) or
        ``None`` to clear the override.

        Uses ``setAutoFillBackground(True)`` + palette ``Window``
        role — the reliable mechanism that paints plain
        ``QWidget`` (Box / HBox / VBox containers) as well as
        every other widget class.  Stylesheets on plain QWidget
        are ignored without ``WA_StyledBackground`` *and* a
        ``paintEvent`` override, so palette is the simpler path.

        Themed widgets (Button, ComboBox, …) paint their own
        multi-state backgrounds via the platform style; on those,
        a generic ``set_bg`` may be partially overridden by hover /
        active states.  For uniform styling on themed widgets,
        use their widget-specific style API instead."""
        if color is None:
            self.widget.setAutoFillBackground(False)
            # Reset to the application default palette so any
            # previously applied Window colour goes away.
            self.widget.setPalette(QtGui.QApplication.palette(self.widget))
        else:
            self.widget.setAutoFillBackground(True)
            pal = self.widget.palette()
            pal.setColor(QtHelp.QPalette.Window, QtHelp.QColor(color))
            self.widget.setPalette(pal)

    def get_enabled(self):
        self.widget.isEnabled()

    def set_enabled(self, tf):
        self.widget.setEnabled(tf)

    def is_container(self):
        return False

    def get_size(self):
        wd, ht = self.widget.width(), self.widget.height()
        return (wd, ht)

    def get_pos(self):
        x, y = self.widget.x(), self.widget.y()
        return (x, y)

    def get_app(self):
        return _app

    def delete(self):
        w, self.widget = self.widget, None
        QtHelp.delete_widget(w)
        #w.deleteLater()

    def focus(self):
        self.widget.activateWindow()
        self.widget.setFocus()
        # self.widget.raise_()

    def resize(self, width, height):
        _wd, _ht = self.get_size()
        if width < 0:
            width = _wd
        if height < 0:
            height = _ht
        self.widget.resize(int(width), int(height))

    def set_min_size(self, wd, ht):
        if wd is None:
            # sentinal for unrestricted
            wd = QtHelp.QWIDGETSIZE_MAX
        if ht is None:
            # sentinal for unrestricted
            ht = QtHelp.QWIDGETSIZE_MAX
        self.widget.setMinimumSize(wd, ht)

    def set_max_size(self, wd, ht):
        if wd is None:
            # sentinal for unrestricted
            wd = QtHelp.QWIDGETSIZE_MAX
        if ht is None:
            # sentinal for unrestricted
            ht = QtHelp.QWIDGETSIZE_MAX
        self.widget.setMaximumSize(wd, ht)

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def is_visible(self):
        return self.widget.isVisible()

    def get_font(self, font_family, point_size):
        font = QtHelp.get_font(font_family, point_size)
        return font

    def _set_name(self, obj):
        name = obj.objectName()
        if name is None or len(name) == 0:
            name = f"W{id(obj)}"
        obj.setObjectName(name)
        self._widget_name = name
        return name

    def _get_name(self):
        return self._widget_name

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

    def set_expanding(self, horizontal=False, vertical=False):
        # a simple version of cfg_expand that is more cross platform
        policy = self.widget.sizePolicy()
        hpolicy = policy.horizontalPolicy()
        vpolicy = policy.verticalPolicy()
        if horizontal:
            hpolicy = QtGui.QSizePolicy.Expanding
        if vertical:
            vpolicy = QtGui.QSizePolicy.Expanding
        self.widget.setSizePolicy(QtGui.QSizePolicy(hpolicy, vpolicy))

    def get_rgb_array(self):
        return QtHelp.get_rgb_array(self.widget)


Widget = WidgetBase

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


class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        #tw = QtGui.QTextEdit()
        tw = QtHelp.QGrowingTextEdit()
        tw.setReadOnly(not editable)
        if wrap:
            tw.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        else:
            tw.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        self.tw = tw
        self.widget = tw

    def append_text(self, text, autoscroll=True):
        if text.endswith('\n'):
            text = text[:-1]
        self.tw.append(text)
        if not autoscroll:
            return

        self.tw.moveCursor(QTextCursor.End)
        self.tw.moveCursor(QTextCursor.StartOfLine)
        self.tw.ensureCursorVisible()

    def get_text(self):
        return self.tw.document().toPlainText()

    def clear(self):
        self.tw.clear()

    def set_text(self, text):
        self.clear()
        self.append_text(text)

    def set_editable(self, tf):
        self.tw.setReadOnly(not tf)

    def set_limit(self, numlines):
        # self.tw.setMaximumBlockCount(numlines)
        pass

    def set_font(self, font, size=10):
        if not isinstance(font, QFont):
            font = self.get_font(font, size)
        self.tw.setCurrentFont(font)

    def set_wrap(self, kind):
        if isinstance(kind, bool):
            # <-- old API
            kind = 'full' if kind else 'none'

        if kind == 'none':
            self.tw.setLineWrapMode(QtGui.QTextEdit.NoWrap)
        else:
            self.tw.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
            if kind in ('char', 'full'):
                self.tw.setWordWrapMode(QTextOption.WrapAnywhere)
            elif kind == 'word':
                self.tw.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)

    def set_scroll_pos(self, pos):
        vsb = self.tw.verticalScrollBar()
        if pos == -1:
            vsb.setValue(vsb.maximum())
        else:
            vsb.setValue(pos)


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
        self._set_name(self.widget)
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
                if hasattr(menu_w, 'exec_'):
                    # PySide2
                    menu_w.exec_(lbl.mapToGlobal(point))
                else:
                    menu_w.exec(lbl.mapToGlobal(point))

            lbl.customContextMenuRequested.connect(on_context_menu)

        # Enable highlighting for copying
        # lbl.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        for name in ['activated', 'released']:
            self.enable_callback(name)

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

    def set_color(self, bg=None, fg=None):
        content = ""
        if bg is not None:
            bg_tup = colors.resolve_color(bg)
            bg_hex = colors.get_hex(bg_tup)
            content = f"background-color: {bg_hex};"
        if fg is not None:
            fg_tup = colors.resolve_color(fg)
            fg_hex = colors.get_hex(fg_tup)
            content = f"{content} color: {fg_hex};"
        if len(content) > 0:
            myname = self._get_name()
            self.widget.setStyleSheet(
                "#%s { %s }" % (myname, content))

    def set_halign(self, align):
        align = align.lower()
        # Mask the horizontal-alignment bits out of the current
        # value and OR in the new flag, so the existing vertical
        # bits (set via ``set_valign``) survive.
        cur = self.widget.alignment() & ~QtCore.Qt.AlignHorizontal_Mask
        if align == 'left':
            cur |= QtCore.Qt.AlignLeft
        elif align == 'center':
            cur |= QtCore.Qt.AlignHCenter
        elif align == 'right':
            cur |= QtCore.Qt.AlignRight
        else:
            raise ValueError(f"Don't understand alignment '{align}'")
        self.widget.setAlignment(cur)

    def set_valign(self, align):
        align = align.lower()
        cur = self.widget.alignment() & ~QtCore.Qt.AlignVertical_Mask
        if align == 'top':
            cur |= QtCore.Qt.AlignTop
        elif align == 'center':
            cur |= QtCore.Qt.AlignVCenter
        elif align == 'bottom':
            cur |= QtCore.Qt.AlignBottom
        else:
            raise ValueError(f"Don't understand alignment '{align}'")
        self.widget.setAlignment(cur)


class Button(WidgetBase):
    def __init__(self, text=None, iconpath=None, iconsize=None):
        super(Button, self).__init__()

        self.widget = QtGui.QPushButton()

        if iconpath is not None:
            self.set_icon(iconpath, iconsize=iconsize)

        if text is not None:
            self.widget.setText(text)

        self.widget.clicked.connect(self._cb_redirect)
        self._set_name(self.widget)

        self.enable_callback('activated')

    def set_text(self, text):
        self.widget.setText(text)

    def get_text(self):
        return self.widget.text()

    def set_icon(self, iconpath, iconsize=None):
        wd, ht = 24, 24
        if iconsize is not None:
            wd, ht = iconsize
        iconw = QtHelp.get_icon(iconpath, size=(wd, ht))
        self.widget.setIcon(iconw)

    def set_color(self, bg=None, fg=None):
        content = ""
        if bg is not None:
            bg_tup = colors.resolve_color(bg)
            bg_hex = colors.get_hex(bg_tup)
            content = f"background-color: {bg_hex};"
        if fg is not None:
            fg_tup = colors.resolve_color(fg)
            fg_hex = colors.get_hex(fg_tup)
            content = f"{content} color: {fg_hex};"
        if len(content) > 0:
            myname = self._get_name()
            self.widget.setStyleSheet(
                "#%s { %s }" % (myname, content))

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

    def _cb_redirect(self, *args):
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
        return (val == QtCore.Qt.CheckState.Checked)


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
        if self.widget.isChecked() == tf:
            return
        # toggled only fires when the value is toggled
        self.widget.blockSignals(True)
        if not tf and self.widget.autoExclusive():
            # Qt won't let us uncheck the currently-checked radio in
            # an autoExclusive group; flip the flag, uncheck, then
            # restore.  Matches what gtk's set_active(False) does
            # natively and what cross-backend callers expect.
            self.widget.setAutoExclusive(False)
            self.widget.setChecked(False)
            self.widget.setAutoExclusive(True)
        else:
            self.widget.setChecked(tf)
        self.widget.blockSignals(False)

    def get_state(self):
        return self.widget.isChecked()


class Image(WidgetBase):

    @classmethod
    def get_native_image_from_file(cls, iconpath, size=None, adjust_width=True):
        return QtHelp.get_image(iconpath, size=size,
                                adjust_width=adjust_width)

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
                if hasattr(menu_w, 'exec_'):
                    # PySide2
                    menu_w.exec_(lbl.mapToGlobal(point))
                else:
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


def _coerce_bool(s):
    """Best-effort string → bool conversion for sort keys."""
    if isinstance(s, bool):
        return s
    if isinstance(s, (int, float)):
        return bool(s)
    if isinstance(s, str):
        return s.strip().lower() in ('1', 'true', 't', 'yes', 'y',
                                     'on', '✓')
    return bool(s)


class TreeWidgetItem(QtGui.QTreeWidgetItem):
    """``QTreeWidgetItem`` subclass with type-aware sort comparison.

    Looks up the column's declared type on the parent ``QTreeWidget``
    (set by :meth:`TreeView.setup_table` as ``_datatypes``) and
    compares accordingly.  Mirrors the pgw TreeView's type-aware
    sort behaviour so a column of integers sorts numerically,
    a column of booleans by truth value, and so on.  Falls back to
    case-insensitive string comparison for unknown types.
    """
    def __init__(self, *args, **kwargs):
        QtGui.QTreeWidgetItem.__init__(self, *args, **kwargs)

    def __lt__(self, other):
        tv = self.treeWidget()
        col = tv.sortColumn()
        dtype = getattr(tv, '_datatypes', None)
        kind = dtype[col] if dtype and 0 <= col < len(dtype) else 'str'

        a, b = self.text(col), other.text(col)

        # Empty strings always sort last (consistent both ways) so
        # missing values don't muddle the order.
        if a == '' and b != '':
            return False
        if b == '' and a != '':
            return True

        if kind in ('int', 'integer'):
            try:
                return int(a) < int(b)
            except (ValueError, TypeError):
                pass  # fall through to string compare
        elif kind in ('float', 'number'):
            try:
                return float(a) < float(b)
            except (ValueError, TypeError):
                pass
        elif kind in ('bool', 'boolean'):
            return _coerce_bool(a) < _coerce_bool(b)
        elif kind == 'check':
            return self.checkState(col) < other.checkState(col)
        # 'str', 'icon', 'widget', or unknown — try numeric first
        # (preserves the old TreeView heuristic where un-typed
        # numeric strings sort numerically), then fall back to
        # case-insensitive string compare.
        try:
            return float(a) < float(b)
        except (ValueError, TypeError):
            return a.lower() < b.lower()


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
        self.datatypes = []
        # shadow index
        self.shadow = {}
        self.font = 'Sans Serif'
        self.fontsize = 10.0
        self.cell_pad_px = 0
        self.editable = False

        tv = QtGui.QTreeWidget()
        self.widget = tv
        tv.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        if selection == 'multiple':
            tv.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        tv.setAlternatingRowColors(use_alt_row_color)
        tv.itemDoubleClicked.connect(self._cb_redirect)
        tv.itemSelectionChanged.connect(self._selection_cb)
        tv.itemExpanded.connect(self._item_expanded_cb)
        tv.itemCollapsed.connect(self._item_collapsed_cb)
        tv.itemChanged.connect(self._item_changed_cb)
        # Fires when the user clicks a header section to (re)sort.
        # Lets TreeViewItem.__lt__ do type-aware comparison while
        # the higher level gets a clean "the user sorted by col N"
        # event.
        tv.header().sortIndicatorChanged.connect(self._sort_indicator_cb)
        if self.dragable:
            tv.setDragEnabled(True)
            tv.startDrag = self._start_drag

        for cbname in ('selected', 'activated', 'drag-start', 'expanded',
                       'collapsed', 'changed', 'sorted'):
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
            if len(columns[0]) > 2:
                datatypes = [col[2] for col in columns]
            else:
                datatypes = ['icon' if _key == 'icon' else 'str'
                             for _key in datakeys]
        else:
            headers = datakeys = columns
            datatypes = ['icon' if _key == 'icon' else 'str'
                         for _key in datakeys]

        self.datakeys = datakeys
        self.datatypes = datatypes
        # Mirror datatypes onto the QTreeWidget itself so the
        # TreeWidgetItem.__lt__ comparator can see them without
        # needing a back-reference to the Ginga wrapper.
        treeview._datatypes = datatypes
        self.leaf_idx = datakeys.index(self.leaf_key)

        if self.sortable:
            # Sort increasing by default
            treeview.sortByColumn(self.leaf_idx, QtCore.Qt.AscendingOrder)

        treeview.setHeaderLabels(headers)

    def set_tree(self, tree_dict):
        self.clear()
        self.add_tree(tree_dict)

    def add_tree(self, tree_dict, expand_new=False):
        """Add a tree to the TreeView"""
        if self.sortable:
            # NOTE: turning off sorting while adding makes the operation
            # faster
            self.widget.setSortingEnabled(False)

        self._add_subtree(1, self.shadow, self.widget, tree_dict,
                          expand_new=expand_new)

        if self.sortable:
            # re-enable sorting if needed
            self.widget.setSortingEnabled(True)

        # User wants auto expand?
        if self.auto_expand:
            self.widget.expandAll()

    def update_tree(self, tree_dict, expand_new=False):
        """Update the TreeView according to the changes in `tree_dict`"""
        if self.sortable:
            self.widget.setSortingEnabled(False)

        self._del_subtree(1, self.shadow, self.widget, tree_dict)
        self._add_subtree(1, self.shadow, self.widget, tree_dict,
                          expand_new=expand_new)

        if self.sortable:
            self.widget.setSortingEnabled(True)

        # User wants auto expand?
        if self.auto_expand:
            self.widget.expandAll()

    def _del_subtree(self, level, shadow, parent_item, tree):
        """Prune elements from widget that are not in the new tree"""

        for key in list(shadow.keys()):
            bnch = shadow[key]
            if key not in tree:
                item = bnch.item
                del shadow[key]
                if level == 1:
                    parent_item.takeTopLevelItem(parent_item.indexOfTopLevelItem(item))
                else:
                    parent_item.removeChild(item)
            else:
                if level < self.levels:
                    self._del_subtree(level + 1, bnch.node, bnch.item,
                                      tree[key])

    def _add_subtree(self, level, shadow, parent_item, tree, expand_new=False):
        """add/update elements from widget that are in the new tree"""

        for key in tree:
            node = tree[key]
            if level >= self.levels:
                # leaf node
                try:
                    bnch = shadow[key]
                    item = bnch.item
                    bnch.node.update(node)

                except KeyError:
                    # new item
                    item = TreeWidgetItem(parent_item)
                    if level == 1:
                        parent_item.addTopLevelItem(item)
                    else:
                        parent_item.addChild(item)

                    bnch = Bunch.Bunch(node=node, item=item, terminal=True)
                    shadow[key] = bnch

                # update leaf item
                for i, _key in enumerate(self.datakeys):
                    datatype = self.datatypes[i]
                    if datatype == 'icon':
                        item.setIcon(i, node[_key])
                    elif datatype == 'check':
                        state = QtCore.Qt.Checked if node[_key] else \
                            QtCore.Qt.Unchecked
                        item.setCheckState(i, state)
                        # if self.editable:
                        #     item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
                        # else:
                        #     item.setFlags(item.flags() & ~QtCore.Qt.ItemIsUserCheckable)
                    elif datatype == 'widget':
                        qt_w = node[_key].get_widget()
                        self.widget.setItemWidget(item, i, qt_w)
                    else:
                        item.setText(i, str(node[_key]))
                        if self.editable:
                            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                        else:
                            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)

            else:
                try:
                    # shadow node already exists
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

                    if expand_new:
                        self.widget.expandItem(item)

                # ensure that items that were collapsed stay collapsed
                expanded = item.isExpanded()
                if not expanded:
                    self.widget.collapseItem(item)

                # recurse for non-leaf interior node
                self._add_subtree(level + 1, d, item, node)

    def _selection_cb(self):
        res_dict = self.get_selected()
        self.make_callback('selected', res_dict)

    def _sort_indicator_cb(self, col, order):
        """Fire when the user clicks a header section to (re)sort.

        The callback carries the column *key* (a stable string),
        not the column index — matching the pgw TableView's
        ``sorted`` signature so a single handler works under both
        widget sets.
        """
        ascending = (order == QtCore.Qt.AscendingOrder)
        col_key = (self.datakeys[col]
                   if 0 <= col < len(self.datakeys) else None)
        self.make_callback('sorted', col_key, ascending)

    def _item_expanded_cb(self, item):
        path = self._get_path(item)
        self.make_callback('expanded', path)

    def _item_collapsed_cb(self, item):
        path = self._get_path(item)
        self.make_callback('collapsed', path)

    def _item_changed_cb(self, item, col):
        path = self._get_path(item)
        key = self.datakeys[col]
        datatype = self.datatypes[col]
        if datatype == 'check':
            val = (item.checkState(col) == QtCore.Qt.Checked)
        elif datatype == 'widget':
            # should return the wrapped widget here
            val = None
        else:
            val = item.text(col)
        # TODO: change shadow bunch?
        self.make_callback('changed', path, key, val)

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
        """Get a dict of selected items."""
        items = list(self.widget.selectedItems())
        res_dict = {}
        for item in items:
            if item.childCount() > 0:
                # only leaf nodes can be reported with this method
                continue
            else:
                self._get_item(res_dict, item)
        return res_dict

    def get_selected_paths(self):
        """Get a list of selected paths.
        NOTE: this returns both leaves and branches (leaf paths are
        longer)
        """
        items = list(self.widget.selectedItems())
        return [self._get_path(item) for item in items]

    def _get_children(self, item_list, parent_item, status='all'):
        # helper function for get_children()
        for row in range(parent_item.childCount()):
            item = parent_item.child(row)
            if item.childCount() > 0:
                if (status == 'all' or
                    (status == 'expanded' and item.isExpanded()) or
                    (status == 'collapsed' and not item.isExpanded())):
                    self._get_children(item_list, item, status=status)
            else:
                item_list.append(item)
        return item_list

    def get_children(self, status='all'):
        item_list = []
        for key, bnch in self.shadow.items():
            item = bnch.item
            if (status == 'all' or
                (status == 'expanded' and item.isExpanded()) or
                (status == 'collapsed' and not item.isExpanded())):
                self._get_children(item_list, item, status=status)

        res_dict = {}
        for item in item_list:
            self._get_item(res_dict, item)
        return res_dict

    def get_expanded(self):
        """Returns a list of paths of all the expanded nodes."""
        res_list = []
        iterator = QtGui.QTreeWidgetItemIterator(self.widget,
                                                 QtGui.QTreeWidgetItemIterator.HasChildren)
        while iterator.value():
            item = iterator.value()
            if item.isExpanded():
                res_list.append(self._get_path(item))
            iterator += 1

        return res_list

    def get_collapsed(self):
        """Returns a list of paths of all the collapsed nodes."""
        res_list = []
        iterator = QtGui.QTreeWidgetItemIterator(self.widget,
                                                 QtGui.QTreeWidgetItemIterator.HasChildren)
        while iterator.value():
            item = iterator.value()
            if not item.isExpanded():
                res_list.append(self._get_path(item))
            iterator += 1

        return res_list

    def expand_all(self, tf):
        self.widget.blockSignals(True)
        try:
            if tf:
                self.widget.expandAll()
            else:
                self.widget.collapseAll()
        finally:
            self.widget.blockSignals(False)

    def clear(self):
        self.widget.clear()
        self.shadow = {}

    def clear_selection(self):
        self.widget.blockSignals(True)
        try:
            self.widget.clearSelection()
        finally:
            self.widget.blockSignals(False)

    def _path_to_item(self, path):
        s = self.shadow
        for name in path[:-1]:
            s = s[name].node
        item = s[path[-1]].item
        return item

    def select_path(self, path, state=True):
        item = self._path_to_item(path)
        self.widget.blockSignals(True)
        try:
            item.setSelected(state)
        finally:
            self.widget.blockSignals(False)

    def select_paths(self, paths, state=True):
        self.widget.blockSignals(True)
        try:
            for path in paths:
                item = self._path_to_item(path)
                item.setSelected(state)
        finally:
            self.widget.blockSignals(False)

    def select_all(self, state=True):
        self.widget.blockSignals(True)
        try:
            iterator = QtGui.QTreeWidgetItemIterator(self.widget)
            while iterator.value():
                item = iterator.value()
                item.setSelected(state)
                iterator += 1
        finally:
            self.widget.blockSignals(False)

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)

        # A little painfully inefficient, can we do better than this?
        font = QtHelp.QFont()
        if not onoff:
            color = QtHelp.QColor('black')
        else:
            font.setBold(True)
            color = QtHelp.get_color(font_color, 1.0)
        brush = QtHelp.QBrush(color)

        for i in range(item.columnCount()):
            item.setForeground(i, brush)
            item.setFont(i, font)

    def set_path_background(self, path, bgcolor, alpha=1.0):
        item = self._path_to_item(path)
        hex_clr = colors.resolve_color(bgcolor, format='hex')
        qclr = QtHelp.get_color(bgcolor, alpha)
        brush = QtHelp.QBrush(qclr)
        for i in range(item.columnCount()):
            item.setBackground(i, brush)

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

    def set_font(self, fontname, size):
        self.font = fontname
        self.fontsize = size
        self.__set_style()

    def set_cell_padding(self, px):
        self.cell_pad_px = int(px)
        self.__set_style()

    def __set_style(self):
        style = f"""
        QTreeWidget {{
            font: {self.font};
            font-size: {self.fontsize}pt;
        }}
        QHeaderView::section {{
            font: {self.font};
            font-size: {self.fontsize}pt;
            font-weight: bold;
        }}
        QTreeWidget::item {{
            padding: {self.cell_pad_px};
        }}
        """
        self.widget.setStyleSheet(style)

    def _start_drag(self, event):
        res_dict = self.get_selected()
        drag_pkg = DragPackage(self.widget)
        self.make_callback('drag-start', drag_pkg, res_dict)
        drag_pkg.start_drag()


# Synthetic key used for the row-number column when show_row_numbers
# is enabled.  Underscore-prefixed so it can't collide with a real
# user column key.
_ROW_NUM_KEY = '_row_num_'

# Recognised values for the ``widget`` field of a column descriptor.
# A column without ``widget`` set renders as plain text (the long-
# standing behaviour); a column with ``widget`` set hosts a real
# Qt widget per cell.  Keep this in sync with the same constant in
# the pgw / gtk3w / gtk4w wrappers.
_CELL_WIDGETS = ('checkbox', 'combobox', 'progress', 'button')


class _CellWrapper(QtGui.QWidget):
    """Container for widget-typed TableView cells.

    Paints its own background in ``paintEvent`` (fillRect with the
    current cell colour).  Qt's ``setItemWidget`` covers the cell
    rect with this widget — the QTreeWidgetItem's background brush
    is not composited under it, and stylesheet / palette tweaks
    don't reliably re-render after the initial paint.  Painting
    directly in paintEvent is the only technique that works
    consistently across platform styles.

    The colour is stored on the instance; ``set_cell_color`` is
    called from ``_paint_widget_cell`` and from the install path."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bg_color = None
        self._fg_color = None

    def set_cell_color(self, fg, bg):
        self._bg_color = bg
        self._fg_color = fg
        if fg is not None:
            qfg = QtHelp.QColor(fg)
            pal = self.palette()
            pal.setColor(QtHelp.QPalette.WindowText, qfg)
            pal.setColor(QtHelp.QPalette.ButtonText, qfg)
            self.setPalette(pal)
            layout = self.layout()
            if layout is not None:
                for i in range(layout.count()):
                    child = layout.itemAt(i).widget()
                    if child is not None:
                        child.setPalette(pal)
        self.update()

    def paintEvent(self, event):
        if self._bg_color is not None:
            p = QtHelp.QPainter(self)
            p.fillRect(self.rect(), QtHelp.QColor(self._bg_color))
            p.end()
        super().paintEvent(event)


class TableView(TreeView):
    """Flat tabular view, API-compatible with the pgw TableView.

    Backed by a ``QTreeWidget`` configured for single-level display
    (no expand/collapse hierarchy, no indentation), so it visually
    presents as a table while reusing all of :class:`TreeView`'s
    selection / drag / font / padding / type-aware sort plumbing.
    The row-oriented public API matches :class:`PGW.TableView`
    (and the underlying pgwidgets-python ``TableView``):

    Constructor options
    -------------------
    columns : list
        Column descriptors.  Each entry may be:

        * a ``dict``: ``{label, key, type, halign}`` (the canonical
          form, matching pgw);
        * a tuple/list: ``(label, key[, type])`` (the legacy form);
        * a bare string: treated as both label and key, type
          ``'string'``.

        ``type`` is one of ``'string'``/``'str'``, ``'integer'``/
        ``'int'``, ``'float'``/``'number'``, ``'boolean'``/``'bool'``,
        or ``'icon'``.  Drives the sort comparator.
    show_header : bool
        Show the column header row.  Default ``True``.
    selection_mode : str
        ``'single'``, ``'multiple'``, ``'none'``, or the per-cell
        variants ``'single-cell'`` / ``'multiple-cell'``.  Cell
        modes light up the cell-clicked rectangle (Shift) /
        disjoint cells (Ctrl), plus row-select via row-number
        click and column-select via header click (with modifiers
        if ``sortable`` is on).
    alternate_row_colors : bool
        Stripe alternate rows.
    show_grid : bool
        Draw grid lines.  ``QTreeWidget`` doesn't expose native
        grid lines, so this is emulated via a stylesheet —
        cosmetic only.
    show_row_numbers : bool
        Show a 1-based row-number column on the left, styled like
        a vertical header (gray background, bold, narrow,
        non-editable, non-sortable).
    sortable : bool
        Allow click-to-sort on column headers.
    allow_text_selection : bool
        Currently a no-op on qtw; accepted for API compatibility.
    dragable : bool
        Allow rows to be dragged out (inherited from TreeView).

    Row data
    --------
    ``set_rows`` / ``set_data`` / ``append_row`` / ``insert_row``
    accept either a ``dict`` keyed by column key, or a positional
    ``list`` / ``tuple`` matching the column order.  Internally
    rows are addressed by integer index, exposed as a length-1
    "path" (``[row_index]``) to mirror :class:`TreeView`.

    Callbacks
    ---------
    * ``activated(table, row_dict, [row_index], col_key)`` — fires
      on double-click.  ``col_key`` is the user-space column key
      that was clicked, or ``None`` if the click landed on the
      synthetic row-number column.
    * ``selected(table, list_of_row_dicts)`` — row-mode selection
      changed.
    * ``cell_selected(table, [{path, col_key, value}, ...])`` —
      cell-mode selection changed (``single-cell`` /
      ``multiple-cell``).
    * ``sorted(table, col_key, ascending)`` — user clicked a
      header to sort.
    * ``cell_edited(table, [row_index], col_key, old_value, new_value)``
      — an editable cell was edited (only fires for columns marked
      editable via :meth:`set_column_editable`).
    * ``scrolled(table, h_pct, v_pct)`` — scroll position changed.
    * ``copy(table, tsv)`` / ``cut(table, tsv)`` /
      ``paste(table, text)`` — Ctrl+C / X / V on the widget.  The
      widget itself updates the visible cells on paste / cut; the
      callbacks let plugins react (e.g. propagate to a backing
      model).
    """

    def __init__(self, columns=None, show_header=True,
                 selection_mode='single', alternate_row_colors=False,
                 show_grid=False, show_row_numbers=False,
                 sortable=False, allow_text_selection=False,
                 dragable=False):
        # Cell modes map to a row-level "multiple" Qt mode at the
        # TreeView layer; per-cell behavior is enabled below by
        # switching the SelectionBehavior to SelectItems.
        self._selection_mode_arg = selection_mode
        is_cell_mode = selection_mode in ('single-cell', 'multiple-cell')
        parent_mode = 'multiple' if is_cell_mode else selection_mode
        super().__init__(auto_expand=False, sortable=sortable,
                         selection=parent_mode,
                         use_alt_row_color=alternate_row_colors,
                         dragable=dragable)

        # Flat-table display tweaks.  Hides the expand/collapse
        # indicator and zeroes out indentation so the first column
        # starts flush left like a real table.
        tv = self.widget
        tv.setRootIsDecorated(False)
        tv.setItemsExpandable(False)
        tv.setIndentation(0)
        if not show_header:
            tv.header().hide()

        # Per-column editable flags.  Populated by
        # set_column_editable; consulted when rows are added.
        self._editable_cols = set()
        # User-supplied (normalised) column descriptors.  Excludes
        # the synthetic row-number column even when show_row_numbers
        # is on, so the public API indexes into the user's columns.
        self._user_columns = []
        self._show_row_numbers = bool(show_row_numbers)
        self._show_grid = False
        self._allow_text_selection = bool(allow_text_selection)  # noqa

        # Colour-override state, four layers with cell > row >
        # column > table precedence (mirrors the pgw side).  See
        # _resolve_cell_color / _apply_color_to_cell below.
        #
        # Cell / row entries are keyed by ``id(QTreeWidgetItem)``
        # so they survive header-click sort but are wiped when
        # ``set_rows`` / ``set_columns`` rebuild the items (item
        # objects go away).  Column / table entries persist
        # across rebuilds and are re-applied to every new row.
        self._cell_color_map = {}     # (id(item), user_col) -> {fg,bg}
        self._row_color_map = {}      # id(item)             -> {fg,bg}
        self._col_color_map = {}      # col_key              -> {fg,bg}
        self._table_color = None      # {fg,bg} | None

        # Per-cell embedded widgets (for ``widget``-typed columns).
        # Keyed by ``(id(item), col_key)`` so they survive sort and
        # are wiped on row delete / clear / set_rows alongside the
        # item itself.  Qt owns the lifetime of the widget once
        # ``setItemWidget`` is called — we just drop the reference.
        self._cell_widgets = {}

        # Replace TreeView's 'activated' / 'changed' wiring with
        # the table-oriented signatures.  Connect to additional
        # signals for 'scrolled'.
        tv.verticalScrollBar().valueChanged.connect(self._scroll_cb)
        tv.horizontalScrollBar().valueChanged.connect(self._scroll_cb)

        # New callbacks (in addition to those TreeView enables).
        # ``cell_action`` fires when the user clicks a ``widget``
        # cell that's action-shaped (currently: ``button``).
        for cbname in ('cell_edited', 'scrolled',
                       'cell_selected', 'cell_action',
                       'copy', 'cut', 'paste'):
            self.enable_callback(cbname)

        # Explicit anchor for cell-mode Shift-extends.  Qt has its
        # own "current index" notion, but it's mutated by clicks
        # before our handlers see them, so we track our own anchor
        # — updated on plain/Ctrl clicks on cells, row-numbers, or
        # headers — and read it for Shift+row-num / Shift+header
        # extensions across whole rows / columns.
        self._cell_anchor = None  # (row, user_col) or None

        # ----- cell-mode wiring -----------------------------------
        # When the caller asked for a cell-level selection mode,
        # switch QTreeWidget to per-cell selection and route the
        # 'cell_selected' callback through itemSelectionChanged.
        if is_cell_mode:
            tv.setSelectionBehavior(QtGui.QAbstractItemView.SelectItems)
            if selection_mode == 'multiple-cell':
                tv.setSelectionMode(
                    QtGui.QAbstractItemView.ExtendedSelection)
            else:  # single-cell
                tv.setSelectionMode(
                    QtGui.QAbstractItemView.SingleSelection)
            # Take over sort triggering so plain header click sorts
            # (when sortable) without *also* firing the column-
            # select handler, and modifier-click selects without
            # *also* triggering Qt's auto-sort.  We still keep the
            # parent's sortIndicatorChanged wiring for the public
            # ``sorted`` callback, just route the trigger ourselves.
            # ORDER MATTERS: setSortingEnabled(False) has a side-
            # effect of calling header().setSectionsClickable(False),
            # so make sections clickable *after* disabling sorting.
            tv.setSortingEnabled(False)
            tv.header().setSectionsClickable(True)

        # Header section click → handles both sort (if sortable)
        # and column-select (with modifiers, or always in
        # non-sortable cell mode).
        tv.header().sectionClicked.connect(self._header_section_clicked)
        # Track item clicks so plain-click on the synthetic row-
        # number column selects the whole row in cell mode, and so
        # ordinary cell clicks update the anchor.
        tv.itemClicked.connect(self._item_clicked_cb)

        # Keyboard shortcuts for Ctrl+C / Ctrl+X / Ctrl+V.  The
        # parent shortcut ties these to *this* QTreeWidget so they
        # only fire when it has focus.
        for keyseq, slot in (
                ('Ctrl+C', self.copy_selection),
                ('Ctrl+X', self.cut_selection),
                ('Ctrl+V', self.paste_selection)):
            # QShortcut + QKeySequence live in different qtpy
            # submodules across PyQt5/6 + PySide2/6 — QtHelp
            # papers over that.
            sc = QtHelp.QShortcut(QtHelp.QKeySequence(keyseq), tv)
            sc.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(slot)

        # Apply default high-contrast selection styling.  Qt's
        # default highlight palette is often a pale tint that
        # leaves cell text barely readable; force a saturated blue
        # background with white text (and keep that scheme when
        # the widget loses focus too, so the selected row stays
        # visible while a context menu / cell editor is open).
        self._apply_stylesheet()

        if show_grid:
            self.set_show_grid(True)

        if columns is not None:
            self.set_columns(columns)

    # ----- internal helpers ------------------------------------

    @staticmethod
    def _normalise_columns(columns):
        """Accept dicts, tuples, or strings; return list of dicts.

        Recognised dict keys: ``label``, ``key``, ``type`` (data
        type — ``'string'`` / ``'number'`` / ``'bool'`` / ``'icon'``
        etc.), ``halign``, ``editable``, ``widget`` (presentation —
        one of ``_CELL_WIDGETS`` or None), and widget-specific
        extras: ``choices`` (combobox), ``min`` / ``max`` (progress),
        ``text`` (button default label).
        """
        out = []
        for i, col in enumerate(columns):
            if isinstance(col, dict):
                key = col.get('key') or col.get('label') or f'col{i}'
                widget = col.get('widget')
                if widget is not None and widget not in _CELL_WIDGETS:
                    raise WidgetError(
                        f"unknown column widget {widget!r} "
                        f"(expected one of {_CELL_WIDGETS})")
                d = {
                    'label': col.get('label', key),
                    'key': key,
                    'type': col.get('type', 'string'),
                    'halign': col.get('halign'),
                    'editable': bool(col.get('editable', False)),
                    'widget': widget,
                    'choices': (list(col['choices'])
                                if 'choices' in col else None),
                    'min': col.get('min'),
                    'max': col.get('max'),
                    'text': col.get('text'),
                    # Per-row gates for widget cells: name of a
                    # row-dict field whose truthiness controls
                    # whether the embedded widget is enabled /
                    # visible.  ``None`` means "always on".
                    'enabled_key': col.get('enabled_key'),
                    'visible_key': col.get('visible_key'),
                    # Initial column width in pixels.  Applied
                    # once at column-setup time; users can resize
                    # afterwards.  ``None`` lets the view pick.
                    'colwidth': col.get('colwidth'),
                }
            elif isinstance(col, (tuple, list)):
                label = col[0]
                key = col[1] if len(col) > 1 else label
                dtype = col[2] if len(col) > 2 else 'string'
                d = {'label': label, 'key': key, 'type': dtype,
                     'halign': None, 'editable': False,
                     'widget': None, 'choices': None,
                     'min': None, 'max': None, 'text': None,
                     'enabled_key': None, 'visible_key': None,
                     'colwidth': None}
            elif isinstance(col, str):
                d = {'label': col, 'key': col, 'type': 'string',
                     'halign': None, 'editable': False,
                     'widget': None, 'choices': None,
                     'min': None, 'max': None, 'text': None,
                     'enabled_key': None, 'visible_key': None,
                     'colwidth': None}
            else:
                raise WidgetError(
                    f"unrecognised column descriptor: {col!r}")
            out.append(d)
        return out

    def _col_offset(self):
        """How many columns to skip before the user's first column.

        1 when ``show_row_numbers`` is on (the row-number column
        sits at index 0); 0 otherwise.
        """
        return 1 if self._show_row_numbers else 0

    def _user_col_keys(self):
        return [c['key'] for c in self._user_columns]

    def _item_to_row_dict(self, item):
        """Reconstruct a row dict from a QTreeWidgetItem.  For
        widget-typed cells, read the live value off the embedded
        widget instead of the (placeholder) text."""
        offset = self._col_offset()
        row = {}
        for j, col in enumerate(self._user_columns):
            col_key = col['key']
            w = self._cell_widgets.get((id(item), col_key))
            if w is not None:
                row[col_key] = self._read_widget_value(col, w)
            else:
                row[col_key] = item.text(j + offset)
        return row

    def _apply_editable_flags(self, item):
        """Apply per-column editable flags to a fresh row item."""
        offset = self._col_offset()
        # First, clear editable on every column (including the
        # row-number column, which is always non-editable).
        flags = item.flags() & ~QtCore.Qt.ItemIsEditable
        item.setFlags(flags)
        # Then we'd need per-column editability — but QTreeWidgetItem
        # flags are per-item, not per-column.  Practical workaround:
        # if ANY column is marked editable, mark the whole item
        # editable.  Callers who want per-column editability typically
        # rely on the QTreeWidget's edit-on-double-click defaulting
        # to whichever column was clicked.
        if self._editable_cols:
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
        # Row-number cell is never editable; QTreeWidgetItem flags
        # don't differentiate per column, so we rely on user clicks
        # not landing on column 0 (it's narrow and visually clearly
        # a row header).
        if offset > 0:
            # Make the row-number cell visually a header.
            self._style_row_number_cell(item)

    def _style_row_number_cell(self, item):
        # Background / foreground from the application palette so
        # the styling tracks the user's theme.
        palette = self.widget.palette()
        bg = palette.button()
        fg = palette.buttonText()
        item.setBackground(0, bg)
        item.setForeground(0, fg)
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        item.setTextAlignment(0,
                              QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

    def _renumber_row_column(self):
        """Refresh the synthetic row-number column after rows
        are inserted/deleted/reordered."""
        if not self._show_row_numbers:
            return
        tv = self.widget
        for i in range(tv.topLevelItemCount()):
            item = tv.topLevelItem(i)
            item.setText(0, str(i + 1))
            self._style_row_number_cell(item)

    def _build_col_specs(self):
        """Translate ``self._user_columns`` to setup_table's tuple
        form, prepending the row-number column if enabled."""
        specs = [(c['label'], c['key'], c['type'])
                 for c in self._user_columns]
        if self._show_row_numbers:
            specs = [('', _ROW_NUM_KEY, 'str')] + specs
        return specs

    def _rebuild_table(self, rows=None):
        """Re-run setup_table from the current state and (optionally)
        re-populate rows.  Called when the column shape changes."""
        col_specs = self._build_col_specs()
        if not col_specs:
            return
        # leaf_key: the first user column's key is a reasonable
        # primary; the row-number column is never the leaf.
        leaf_key = self._user_columns[0]['key']
        # Per-cell / per-row colour overrides reference item
        # identities that won't survive setup_table's rebuild.
        # Drop them now; column / table layers persist and will
        # be re-applied via _apply_row_colors as each new row
        # comes back through _append_one.
        self._cell_color_map.clear()
        self._row_color_map.clear()
        super().setup_table(col_specs, levels=1, leaf_key=leaf_key)
        # Parent's setup_table calls ``setSortingEnabled(self.sortable)``
        # which has a side-effect of resetting the header's
        # ``setSectionsClickable`` state — so in cell mode we have
        # to re-apply our overrides after every column rebuild,
        # otherwise header clicks stop firing ``sectionClicked``.
        # ORDER MATTERS: setSortingEnabled(False) itself calls
        # setSectionsClickable(False), so toggle sections clickable
        # *after* disabling sorting.
        if self._is_cell_mode():
            tv = self.widget
            tv.setSortingEnabled(False)
            tv.header().setSectionsClickable(True)
        if self._show_row_numbers:
            self._configure_row_number_column()
        self._apply_initial_colwidths()
        if rows is not None:
            self.set_rows(rows)

    def _apply_initial_colwidths(self):
        """Apply any per-column ``colwidth`` declared on the
        column descriptors.  Strings are accepted but only the
        numeric form is meaningful here — qt column widths are
        pixel integers (matching ``set_column_width``)."""
        for i, col in enumerate(self._user_columns):
            w = col.get('colwidth')
            if w is None:
                continue
            try:
                px = int(w)
            except (TypeError, ValueError):
                continue
            self.set_column_width(i, px)

    def _configure_row_number_column(self):
        tv = self.widget
        header = tv.header()
        # Narrow, fixed-ish width.  ResizeToContents grows to fit
        # the largest "999..." label as rows are added.
        header.setSectionResizeMode(0, QtGui.QHeaderView.ResizeToContents)
        # Make the row-number header itself look like a row-header
        # corner cell: blank, no sort indicator.
        tv.headerItem().setText(0, '')

    # ----- column management -----------------------------------

    def set_columns(self, columns):
        """Replace the column layout.  Clears existing rows."""
        self._user_columns = self._normalise_columns(columns)
        # Pick up any ``editable: True`` flags baked into the
        # column dicts (matches the pgw side, where the JS reads
        # ``colDef.editable`` directly).  ``set_column_editable``
        # may still be called later to flip individual columns.
        self._editable_cols = {i for i, c in enumerate(self._user_columns)
                               if c.get('editable')}
        self._rebuild_table()

    def insert_column(self, idx, column):
        """Insert a new column at index ``idx`` (user-space)."""
        col, = self._normalise_columns([column])
        self._user_columns.insert(idx, col)
        # Snapshot existing rows so we can repopulate, since
        # changing columnCount on QTreeWidget invalidates items.
        rows = self.get_rows()
        for r in rows:
            r.setdefault(col['key'], '')
        self._rebuild_table(rows=rows)

    def append_column(self, column):
        self.insert_column(len(self._user_columns), column)

    def delete_column(self, idx):
        if not (0 <= idx < len(self._user_columns)):
            raise WidgetError(f"column index {idx} out of range")
        removed = self._user_columns.pop(idx)
        rows = self.get_rows()
        for r in rows:
            r.pop(removed['key'], None)
        self._rebuild_table(rows=rows)

    def set_column_editable(self, col_idx, tf):
        if tf:
            self._editable_cols.add(col_idx)
        else:
            self._editable_cols.discard(col_idx)
        # Re-apply flags on existing items
        tv = self.widget
        for i in range(tv.topLevelItemCount()):
            self._apply_editable_flags(tv.topLevelItem(i))

    def get_column_count(self):
        return len(self._user_columns)

    def set_column_width(self, idx, width):
        """Set width (px) of user column ``idx``."""
        self.widget.setColumnWidth(idx + self._col_offset(), width)

    # ----- row management --------------------------------------

    def set_rows(self, rows):
        """Replace all rows.  ``rows`` is a sequence of dicts
        (keyed by column key) or a sequence of positional values."""
        self.widget.clear()
        # Per-cell / per-row colour overrides reference the
        # old item objects we're about to discard; drop those.
        # Column / table colours persist and are re-applied to
        # each new row via _apply_row_colors.
        self._cell_color_map.clear()
        self._row_color_map.clear()
        # Same for embedded cell widgets — their host items just
        # went away, so the widgets are destroyed by Qt.
        self._cell_widgets.clear()
        for i, row in enumerate(rows):
            self._append_one(row)

    # Alias matching pgw's ``set_data`` name.
    set_data = set_rows

    def append_row(self, values):
        self._append_one(values)

    def insert_row(self, idx, values):
        tv = self.widget
        item, row_dict = self._make_row_item(values)
        tv.insertTopLevelItem(idx, item)
        self._apply_editable_flags(item)
        self._install_widget_cells(item, row_dict)
        self._apply_row_colors(item)
        self._renumber_row_column()

    def delete_row(self, idx):
        tv = self.widget
        if not (0 <= idx < tv.topLevelItemCount()):
            raise WidgetError(f"row index {idx} out of range")
        item = tv.takeTopLevelItem(idx)
        # Drop dangling colour + widget entries that referenced
        # this item.
        if item is not None:
            iid = id(item)
            self._row_color_map.pop(iid, None)
            for key in [k for k in self._cell_color_map
                        if k[0] == iid]:
                del self._cell_color_map[key]
            self._drop_widget_cells_for(item)
        self._renumber_row_column()

    def get_row_count(self):
        return self.widget.topLevelItemCount()

    def get_row(self, idx):
        item = self.widget.topLevelItem(idx)
        if item is None:
            raise WidgetError(f"row index {idx} out of range")
        return self._item_to_row_dict(item)

    def get_rows(self):
        tv = self.widget
        return [self._item_to_row_dict(tv.topLevelItem(i))
                for i in range(tv.topLevelItemCount())]

    def set_cell(self, row, col, value):
        item = self.widget.topLevelItem(row)
        if item is None:
            raise WidgetError(f"row index {row} out of range")
        if not (0 <= col < len(self._user_columns)):
            raise WidgetError(f"column index {col} out of range")
        col_spec = self._user_columns[col]
        col_idx = col + self._col_offset()
        # Widget cells: push the value through to the embedded
        # widget so the display reflects the change.  Signals are
        # blocked so this programmatic update doesn't fire
        # cell_edited (which is for user-initiated changes).
        w = self._cell_widgets.get((id(item), col_spec['key']))
        if w is not None:
            w.blockSignals(True)
            try:
                self._write_widget_value(col_spec, w, value)
            finally:
                w.blockSignals(False)
            item.setData(col_idx, QtCore.Qt.UserRole, value)
            return
        text = '' if value is None else str(value)
        item.setText(col_idx, text)
        # Mirror to UserRole so the next cell_edited callback can
        # report old_value correctly.
        item.setData(col_idx, QtCore.Qt.UserRole, text)

    def _write_widget_value(self, col, w, value):
        wtype = col['widget']
        if wtype == 'checkbox':
            w.setChecked(bool(value))
        elif wtype == 'combobox':
            if value is not None:
                w.setCurrentText(str(value))
        elif wtype == 'progress':
            try:
                w.setValue(int(value) if value is not None
                           else w.minimum())
            except (TypeError, ValueError):
                pass
        elif wtype == 'button':
            if value is not None:
                w.setText(str(value))

    def _append_one(self, values):
        tv = self.widget
        item, row_dict = self._make_row_item(values)
        tv.addTopLevelItem(item)
        self._apply_editable_flags(item)
        # Widget cells need the item to be in the tree before
        # ``setItemWidget`` will accept it.  Install widgets
        # *before* applying colours so ``_apply_color_to_cell``
        # can also paint the wrapper containers in one pass.
        self._install_widget_cells(item, row_dict)
        self._apply_row_colors(item)
        self._renumber_row_column()

    def _make_row_item(self, values):
        """Build a TreeWidgetItem from a row dict-or-sequence.
        Returns ``(item, row_dict)`` — the row_dict is needed by
        callers who install widget cells after the item is added
        to the tree."""
        if isinstance(values, dict):
            row_dict = values
        elif isinstance(values, (list, tuple)):
            row_dict = dict(zip(self._user_col_keys(), values))
        else:
            raise WidgetError(
                f"row must be a dict or sequence, got {type(values).__name__}")

        item = TreeWidgetItem()
        offset = self._col_offset()
        for j, col in enumerate(self._user_columns):
            val = row_dict.get(col['key'], '')
            # Widget-typed columns don't show text — the embedded
            # widget is installed over the cell in
            # ``_install_widget_cells`` and any cell text would
            # bleed out around it.  Leave the cell text empty;
            # ``_install_widget_cells`` populates UserRole with the
            # typed value for cell_edited's old_value tracking.
            if col.get('widget'):
                item.setText(j + offset, '')
                continue
            text = '' if val is None else str(val)
            item.setText(j + offset, text)
            # Stash the value in Qt.UserRole so cell_edited can
            # report old_value without us hooking the editor.
            item.setData(j + offset, QtCore.Qt.UserRole, text)
        # The row-number text is filled in by _renumber_row_column
        # after the item is in the tree.
        return item, row_dict

    # ----- embedded widget cells ------------------------------
    #
    # Columns whose descriptor carries ``widget='checkbox' |
    # 'combobox' | 'progress' | 'button'`` host a real Qt widget
    # per cell (installed via QTreeWidget.setItemWidget).  The
    # widget is the source-of-truth for the cell's value; we sync
    # it back into the QTreeWidgetItem's UserRole storage on every
    # change so the rest of the wrapper (cell_edited, get_row,
    # copy/paste) keeps working uniformly.

    def _install_widget_cells(self, item, row_dict):
        """Walk widget-typed columns and create+install a Qt
        widget per cell on ``item``.  Caller must have already
        added ``item`` to the tree.

        Honours the per-column ``visible_key`` and ``enabled_key``
        gates: if ``visible_key`` is set and the named row field
        is falsy, no widget is installed (the cell stays empty);
        if ``enabled_key`` is set, the embedded widget's enabled
        state mirrors that field."""
        offset = self._col_offset()
        for j, col in enumerate(self._user_columns):
            if not col.get('widget'):
                continue
            col_idx = j + offset
            col_key = col['key']
            visible_key = col.get('visible_key')
            if visible_key is not None \
                    and not row_dict.get(visible_key, True):
                continue
            value = row_dict.get(col_key)
            inner = self._make_cell_widget(col, value, item, col_key)
            enabled_key = col.get('enabled_key')
            if enabled_key is not None:
                inner.setEnabled(bool(row_dict.get(enabled_key, True)))
            # Wrap inner in a _CellWrapper that paints its own bg
            # in paintEvent.  Resolve the cell colour *before*
            # setItemWidget so the very first paint already has
            # the correct background — Qt caches the first paint
            # of a widget hosted in setItemWidget, so painting
            # in the wrapper's __init__ is far more reliable than
            # repainting it later.
            container = self._wrap_cell_widget(inner, col)
            self._cell_widgets[(id(item), col_key)] = inner
            fg0, bg0, _bold0 = self._resolve_cell_color(item, j)
            container.set_cell_color(fg0, bg0)
            self.widget.setItemWidget(item, col_idx, container)
            # Stash the typed value in UserRole so cell_edited
            # ``old_value`` reads correctly on the first change.
            item.setData(col_idx, QtCore.Qt.UserRole, value)

    def _paint_widget_cell(self, container, fg, bg):
        """Push the resolved cell colour onto a ``_CellWrapper``
        and force a repaint.  The wrapper's ``paintEvent`` then
        fills the cell with ``bg``.  A bare ``update()`` is not
        always enough — Qt sometimes caches the first paint of a
        widget hosted via ``setItemWidget`` — so we also poke the
        tree's viewport to invalidate that cache."""
        if isinstance(container, _CellWrapper):
            container.set_cell_color(fg, bg)
        viewport = self.widget.viewport()
        if viewport is not None:
            viewport.update()

    @staticmethod
    def _wrap_cell_widget(inner, col):
        """Place ``inner`` in a ``_CellWrapper`` container that
        paints its own bg in ``paintEvent``.  Layout policy
        depends on widget type: small widgets (checkbox) are
        centered; wide widgets (combobox, progress, button) fill
        the cell."""
        container = _CellWrapper()
        layout = QtGui.QHBoxLayout(container)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)
        wtype = col.get('widget')
        if wtype == 'checkbox':
            # Center small toggles within the cell.
            layout.addStretch()
            layout.addWidget(inner)
            layout.addStretch()
        else:
            # Combobox / progress / button stretch to fill so they
            # don't look orphaned in a wide cell.
            layout.addWidget(inner)
        return container

    def _make_cell_widget(self, col, value, item, col_key):
        wtype = col['widget']
        if wtype == 'checkbox':
            w = QtGui.QCheckBox()
            w.setChecked(bool(value))
            w.setStyleSheet('background: transparent;')
            w.stateChanged.connect(
                lambda _state, it=item, ck=col_key:
                    self._on_cell_widget_changed(it, ck))
            return w
        if wtype == 'combobox':
            w = QtGui.QComboBox()
            choices = col.get('choices') or []
            for ch in choices:
                w.addItem(str(ch))
            if value is not None and str(value) in [str(c) for c in choices]:
                w.setCurrentText(str(value))
            w.currentIndexChanged.connect(
                lambda _i, it=item, ck=col_key:
                    self._on_cell_widget_changed(it, ck))
            return w
        if wtype == 'progress':
            w = QtGui.QProgressBar()
            lo = col.get('min', 0) or 0
            hi = col.get('max', 100) if col.get('max') is not None else 100
            w.setRange(int(lo), int(hi))
            try:
                w.setValue(int(value) if value is not None else int(lo))
            except (TypeError, ValueError):
                w.setValue(int(lo))
            return w
        if wtype == 'button':
            label = (str(value) if value is not None
                     else (col.get('text') or ''))
            w = QtGui.QPushButton(label)
            w.clicked.connect(
                lambda _checked=False, it=item, ck=col_key:
                    self._on_cell_widget_clicked(it, ck))
            return w
        raise WidgetError(f"unknown cell widget type: {wtype!r}")

    def _read_widget_value(self, col, w):
        wtype = col['widget']
        if wtype == 'checkbox':
            return bool(w.isChecked())
        if wtype == 'combobox':
            return w.currentText()
        if wtype == 'progress':
            return int(w.value())
        if wtype == 'button':
            # No persistent value — return the current label so
            # round-trips through get_row() preserve it.
            return w.text()
        return None

    def _on_cell_widget_changed(self, item, col_key):
        """Fire cell_edited(table, [row], col_key, old, new) when
        an editable widget cell mutates."""
        w = self._cell_widgets.get((id(item), col_key))
        if w is None:
            return
        try:
            j = self._user_col_keys().index(col_key)
        except ValueError:
            return
        col = self._user_columns[j]
        col_idx = j + self._col_offset()
        new_value = self._read_widget_value(col, w)
        old_value = item.data(col_idx, QtCore.Qt.UserRole)
        if old_value == new_value:
            return
        item.setData(col_idx, QtCore.Qt.UserRole, new_value)
        row_idx = self.widget.indexOfTopLevelItem(item)
        if row_idx < 0:
            return
        self.make_callback('cell_edited', [row_idx], col_key,
                           old_value, new_value)

    def _on_cell_widget_clicked(self, item, col_key):
        """Fire cell_action(table, row_dict, col_key) on button
        cells."""
        row_idx = self.widget.indexOfTopLevelItem(item)
        if row_idx < 0:
            return
        row = self._item_to_row_dict(item)
        self.make_callback('cell_action', row, col_key)

    def _drop_widget_cells_for(self, item):
        """Drop widget-cell entries for an item that's about to
        be removed."""
        iid = id(item)
        for key in [k for k in self._cell_widgets if k[0] == iid]:
            del self._cell_widgets[key]

    def clear(self):
        # Qt destroys the embedded cell widgets when the items
        # holding them are cleared; drop our refs so we don't
        # keep dangling handles to deleted C++ objects.
        self._cell_widgets.clear()
        super().clear()

    # ----- selection -------------------------------------------

    def get_selected(self):
        """Return selected rows as a list of dicts."""
        tv = self.widget
        return [self._item_to_row_dict(it) for it in tv.selectedItems()]

    def get_selected_paths(self):
        """Return selected rows as a list of ``[row_index]`` paths."""
        tv = self.widget
        # Deduplicate row indices — selectedItems() with a per-cell
        # selection mode returns one entry per selected cell, but
        # callers want one entry per selected row.
        seen, out = set(), []
        for it in tv.selectedItems():
            idx = tv.indexOfTopLevelItem(it)
            if idx >= 0 and idx not in seen:
                seen.add(idx)
                out.append([idx])
        out.sort()
        return out

    # ----- cell-selection public API ---------------------------

    def get_selected_cells(self):
        """Return ``[{path, col_key, value}, ...]`` for the cells
        currently selected — sorted by (row, column).  Available in
        any selection mode, but only meaningful in
        ``single-cell`` / ``multiple-cell``."""
        tv = self.widget
        # selectionModel().selectedIndexes() returns one QModelIndex
        # per selected cell, including the synthetic row-number
        # column.  Filter that out.
        offset = self._col_offset()
        out = []
        for qmi in tv.selectionModel().selectedIndexes():
            col = qmi.column()
            user_col = col - offset
            if user_col < 0 or user_col >= len(self._user_columns):
                continue
            row = qmi.row()
            col_key = self._user_columns[user_col]['key']
            it = tv.topLevelItem(row)
            value = it.text(col) if it is not None else ''
            out.append({'path': [row],
                        'col_key': col_key,
                        'value': value})
        out.sort(key=lambda d: (d['path'][0],
                                self._user_col_keys()
                                    .index(d['col_key'])))
        return out

    def select_cell(self, path, col_key, state=True):
        """Select (or deselect) a single cell by ``(path, col_key)``."""
        if not path:
            return
        idx = self._resolve_to_row_index(path)
        if idx is None or not (0 <= idx < self.get_row_count()):
            return
        try:
            user_col = self._user_col_keys().index(col_key)
        except ValueError:
            return
        col = user_col + self._col_offset()
        it = self.widget.topLevelItem(idx)
        if it is None:
            return
        model = self.widget.model()
        qmi = model.index(idx, col)
        sm = self.widget.selectionModel()
        flag = (QtCore.QItemSelectionModel.Select if state
                else QtCore.QItemSelectionModel.Deselect)
        sm.select(qmi, flag)

    def select_cells(self, cells, state=True):
        for c in (cells or []):
            self.select_cell(c.get('path'), c.get('col_key'), state)

    def clear_cell_selection(self):
        self.widget.clearSelection()

    # ----- per-cell / row / column / table colour overrides ----

    def _resolve_cell_color(self, item, user_col):
        """Walk cell → row → column → table to produce the
        merged ``(fg, bg, bold)`` style triple for one item /
        user-col.  Each component may be ``None`` (meaning "no
        override at this layer" — the underlying widget palette /
        default font wins)."""
        iid = id(item)
        col_key = (self._user_columns[user_col]['key']
                   if 0 <= user_col < len(self._user_columns)
                   else None)
        fg = bg = bold = None

        def _absorb(d):
            nonlocal fg, bg, bold
            if not d:
                return
            if fg is None: fg = d.get('fg')
            if bg is None: bg = d.get('bg')
            if bold is None: bold = d.get('bold')

        _absorb(self._cell_color_map.get((iid, user_col)))
        _absorb(self._row_color_map.get(iid))
        _absorb(self._col_color_map.get(col_key))
        _absorb(self._table_color)
        return fg, bg, bold

    def _apply_color_to_cell(self, item, user_col):
        """Write the resolved colour + weight to the
        QTreeWidgetItem.  Always overwrites — a ``None`` resolved
        value installs a default (invalid) brush or unbolds the
        cell font, clearing the item's override and letting the
        widget palette / default font show through again."""
        fg, bg, bold = self._resolve_cell_color(item, user_col)
        col = user_col + self._col_offset()
        # ``QtGui`` in this module is actually qtpy.QtWidgets;
        # QBrush / QColor live in qtpy.QtGui and are re-exported
        # from QtHelp.
        item.setForeground(col,
                           QtHelp.QBrush(QtHelp.QColor(fg)) if fg
                           else QtHelp.QBrush())
        item.setBackground(col,
                           QtHelp.QBrush(QtHelp.QColor(bg)) if bg
                           else QtHelp.QBrush())
        # Per-cell font weight.  ``item.font(col)`` returns the
        # widget's current font (typeface, size); we toggle the
        # bold bit without disturbing anything else.
        font = item.font(col)
        font.setBold(bool(bold))
        item.setFont(col, font)
        # For widget cells, the embedded widget paints over the
        # item brush — Qt doesn't composite the delegate background
        # through ``setItemWidget`` content.  Mirror the resolved
        # bg onto the wrapper container so the cell colour shows
        # behind the widget, and propagate fg into the inner
        # widget's palette so labels (button text / checkbox box)
        # contrast against the new bg.
        container = self.widget.itemWidget(item, col)
        if container is not None:
            self._paint_widget_cell(container, fg, bg)

    def _apply_row_colors(self, item):
        """Paint every user-column cell of a single item according
        to the current cell/row/column/table state.  Called from
        ``_append_one`` / ``insert_row`` so newly-inserted rows
        pick up column- and table-level overrides automatically."""
        for user_col in range(len(self._user_columns)):
            self._apply_color_to_cell(item, user_col)

    def _apply_all_colors(self):
        """Reapply colours to every visible cell — used when a
        change at column or table level affects many cells at
        once."""
        tv = self.widget
        for row in range(tv.topLevelItemCount()):
            item = tv.topLevelItem(row)
            if item is None:
                continue
            self._apply_row_colors(item)

    def set_cell_color(self, path, col_key, fg=None, bg=None, bold=None):
        idx = self._resolve_to_row_index(path)
        if idx is None:
            return
        if col_key not in self._user_col_keys():
            return
        user_col = self._user_col_keys().index(col_key)
        item = self.widget.topLevelItem(idx)
        if item is None:
            return
        key = (id(item), user_col)
        if fg is None and bg is None and bold is None:
            self._cell_color_map.pop(key, None)
        else:
            self._cell_color_map[key] = {'fg': fg, 'bg': bg, 'bold': bold}
        self._apply_color_to_cell(item, user_col)

    def set_row_color(self, path, fg=None, bg=None, bold=None):
        idx = self._resolve_to_row_index(path)
        if idx is None:
            return
        item = self.widget.topLevelItem(idx)
        if item is None:
            return
        iid = id(item)
        if fg is None and bg is None and bold is None:
            self._row_color_map.pop(iid, None)
        else:
            self._row_color_map[iid] = {'fg': fg, 'bg': bg, 'bold': bold}
        self._apply_row_colors(item)

    def set_column_color(self, col_key, fg=None, bg=None, bold=None):
        if col_key not in self._user_col_keys():
            return
        if fg is None and bg is None and bold is None:
            self._col_color_map.pop(col_key, None)
        else:
            self._col_color_map[col_key] = {'fg': fg, 'bg': bg,
                                            'bold': bold}
        user_col = self._user_col_keys().index(col_key)
        tv = self.widget
        for row in range(tv.topLevelItemCount()):
            item = tv.topLevelItem(row)
            if item is not None:
                self._apply_color_to_cell(item, user_col)

    def set_table_color(self, fg=None, bg=None, bold=None):
        if fg is None and bg is None and bold is None:
            self._table_color = None
        else:
            self._table_color = {'fg': fg, 'bg': bg, 'bold': bold}
        self._apply_all_colors()

    def clear_cell_color(self, path, col_key):
        self.set_cell_color(path, col_key, fg=None, bg=None)

    def clear_row_color(self, path):
        self.set_row_color(path, fg=None, bg=None)

    def clear_column_color(self, col_key):
        self.set_column_color(col_key, fg=None, bg=None)

    def clear_all_colors(self):
        self._cell_color_map.clear()
        self._row_color_map.clear()
        self._col_color_map.clear()
        self._table_color = None
        self._apply_all_colors()

    def set_selected(self, items):
        """Select rows by integer index, by ``[row]`` path, or by
        row dict (matched by leaf-key value)."""
        tv = self.widget
        # Reset
        tv.clearSelection()
        for it in items:
            idx = self._resolve_to_row_index(it)
            if idx is None or not (0 <= idx < tv.topLevelItemCount()):
                continue
            tv.topLevelItem(idx).setSelected(True)

    def select_path(self, path, state=True):
        """``path`` is ``[row_index]`` (length 1)."""
        if not path:
            return
        idx = self._resolve_to_row_index(path)
        if idx is None or not (0 <= idx < self.get_row_count()):
            return
        self.widget.topLevelItem(idx).setSelected(state)

    def select_paths(self, paths, state=True):
        for p in paths:
            self.select_path(p, state)

    def select_all(self, state=True):
        if state:
            self.widget.selectAll()
        else:
            self.widget.clearSelection()

    def _resolve_to_row_index(self, item):
        if isinstance(item, int):
            return item
        if isinstance(item, (list, tuple)) and item:
            # path: [row_index] or [leaf_value]
            head = item[0]
            if isinstance(head, int):
                return head
            try:
                return int(head)
            except (TypeError, ValueError):
                return None
        if isinstance(item, dict):
            # Match by leaf-key value
            leaf = self.leaf_key
            if leaf is None:
                return None
            want = item.get(leaf)
            for i in range(self.get_row_count()):
                if self.get_row(i).get(leaf) == want:
                    return i
        return None

    # ----- sort / scroll ---------------------------------------

    def set_sortable(self, tf):
        self.sortable = bool(tf)
        self.widget.setSortingEnabled(self.sortable)

    def sort_by_column(self, col, ascending=True):
        order = (QtCore.Qt.AscendingOrder if ascending
                 else QtCore.Qt.DescendingOrder)
        self.widget.sortByColumn(col + self._col_offset(), order)

    def scroll_to_path(self, path):
        idx = self._resolve_to_row_index(path)
        if idx is None or not (0 <= idx < self.get_row_count()):
            return
        item = self.widget.topLevelItem(idx)
        self.widget.scrollToItem(item)

    def scroll_to_end(self):
        n = self.get_row_count()
        if n:
            self.widget.scrollToItem(self.widget.topLevelItem(n - 1))

    def set_scroll_position(self, h_pct, v_pct):
        for bar, pct in ((self.widget.horizontalScrollBar(), h_pct),
                         (self.widget.verticalScrollBar(), v_pct)):
            mx = bar.maximum()
            bar.setValue(int(pct * mx))

    def get_scroll_position(self):
        out = []
        for bar in (self.widget.horizontalScrollBar(),
                    self.widget.verticalScrollBar()):
            mx = bar.maximum()
            out.append(bar.value() / mx if mx else 0.0)
        return tuple(out)

    # ----- display config --------------------------------------

    def set_show_grid(self, tf):
        """Toggle grid lines.  QTreeWidget has no native grid; we
        emulate via a stylesheet, so the result is approximate."""
        self._show_grid = bool(tf)
        self._apply_stylesheet()

    def _apply_stylesheet(self):
        """Apply the TableView's visual overrides.

        Selection highlight is set via the widget's *palette*, not
        a stylesheet.  This matters: any ``QTreeView::item`` rule
        in a stylesheet (even one scoped to ``:selected``) makes
        Qt switch to ``QStyleSheetStyle`` for item rendering,
        which clobbers per-item ``setBackground`` brushes.  Using
        the palette keeps the high-contrast selection scheme AND
        lets per-cell / per-row colour overrides paint normally.

        The grid-line stylesheet rule (when ``show_grid`` is on)
        is the same hazard, so it stays as an *opt-in* trade-off:
        with the grid on, per-item colours may not appear under
        every Qt version.  For full grid + per-item-colour
        compatibility, a custom QStyledItemDelegate would be
        needed — out of scope here.
        """
        # High-contrast selection scheme via palette.  Both the
        # Active and Inactive colour groups get the same blue so
        # selected rows stay readable when focus moves off the
        # tree (context menu open, cell editor up, etc.).
        palette = self.widget.palette()
        sel_bg = QtHelp.QColor('#2a64c8')
        sel_fg = QtHelp.QColor('white')
        # ``QPalette.Highlight`` / ``HighlightedText`` are the role
        # enums; qtpy normalises Qt5/Qt6 access so this form works
        # under all bindings.
        palette.setColor(QtHelp.QPalette.Highlight, sel_bg)
        palette.setColor(QtHelp.QPalette.HighlightedText, sel_fg)
        palette.setColor(QtHelp.QPalette.Inactive,
                         QtHelp.QPalette.Highlight, sel_bg)
        palette.setColor(QtHelp.QPalette.Inactive,
                         QtHelp.QPalette.HighlightedText, sel_fg)
        self.widget.setPalette(palette)

        # Grid lines via stylesheet (QTreeView has no native
        # grid).  Opt-in only, since the ``::item`` rule below
        # interferes with per-item colour painting (known Qt
        # quirk).  Callers who need both grid AND per-item
        # colouring should leave grid off; see the docstring.
        if self._show_grid:
            self.widget.setStyleSheet(
                "QTreeView::item { "
                "border-right: 1px solid #d0d0d0; "
                "border-bottom: 1px solid #d0d0d0; }")
        else:
            self.widget.setStyleSheet("")

    def set_show_row_numbers(self, tf):
        new = bool(tf)
        if new == self._show_row_numbers:
            return
        self._show_row_numbers = new
        if self._user_columns:
            rows = self.get_rows()
            # set_columns wipes the table; preserve the user's data.
            self.set_columns(self._user_columns)
            self.set_rows(rows)

    # ----- overridden callback redirects -----------------------

    def _cb_redirect(self, item, col=-1):
        # TreeView's version emits a path-keyed dict; for a flat
        # table, emit (row_dict, path, col_key) where path is
        # [row_index] and col_key is the user-space column key (or
        # ``None`` if the click landed on the synthetic row-number
        # column or couldn't be resolved).  Matches the qtw / gtk
        # TableView 'activated' signature.
        row_dict = self._item_to_row_dict(item)
        idx = self.widget.indexOfTopLevelItem(item)
        user_col = col - self._col_offset()
        col_key = (self._user_columns[user_col]['key']
                   if 0 <= user_col < len(self._user_columns) else None)
        self.make_callback('activated', row_dict, [idx], col_key)

    def _selection_cb(self):
        # In cell modes, fire 'cell_selected' with per-cell records
        # instead of (or alongside) the row-level 'selected'.
        if self._is_cell_mode():
            self.make_callback('cell_selected', self.get_selected_cells())
        else:
            self.make_callback('selected', self.get_selected())

    def _is_cell_mode(self):
        return self._selection_mode_arg in ('single-cell', 'multiple-cell')

    def _item_changed_cb(self, item, col):
        # Skip the synthetic row-number column.
        if self._show_row_numbers and col == 0:
            return
        user_col = col - self._col_offset()
        # Only fire cell_edited for columns the caller marked
        # editable, so spurious itemChanged signals from
        # programmatic updates don't trigger callbacks.
        if user_col in self._editable_cols:
            col_key = (self._user_columns[user_col]['key']
                       if 0 <= user_col < len(self._user_columns)
                       else None)
            new_value = item.text(col)
            old_value = item.data(col, QtCore.Qt.UserRole)
            idx = self.widget.indexOfTopLevelItem(item)
            self.make_callback('cell_edited', [idx], col_key,
                               old_value, new_value)
            # Update the stashed value so the next edit reports
            # the right old_value.
            item.setData(col, QtCore.Qt.UserRole, new_value)
        # Keep the legacy 'changed' callback firing too for
        # TreeView-compatible callers.
        super()._item_changed_cb(item, col)

    def _scroll_cb(self, value):
        h, v = self.get_scroll_position()
        self.make_callback('scrolled', h, v)

    # ----- cell-mode click routing -----------------------------

    def _item_clicked_cb(self, item, column):
        """Handle clicks on a cell.  Routes row-number column
        clicks to whole-row selection and updates the Shift-extend
        anchor for ordinary cell clicks."""
        if not self._is_cell_mode():
            return
        tv = self.widget
        row = tv.indexOfTopLevelItem(item)
        if row < 0:
            return
        offset = self._col_offset()
        user_col = column - offset
        mods = QtGui.QApplication.keyboardModifiers()
        ctrl = bool(mods & QtCore.Qt.ControlModifier) or \
            bool(mods & QtCore.Qt.MetaModifier)
        shift = bool(mods & QtCore.Qt.ShiftModifier)

        # Row-number column gets whole-row select handling.
        if self._show_row_numbers and column == 0:
            self._do_row_select(row, ctrl, shift)
            return

        # Ordinary cell click: Qt's built-in selection logic has
        # already done the right thing (select / toggle / extend).
        # We just refresh our anchor so a subsequent Shift+row-num
        # or Shift+header click extends from this cell.
        if not shift and user_col >= 0:
            self._cell_anchor = (row, user_col)

    def _do_row_select(self, row, ctrl, shift):
        """Select an entire row (all user columns) via the row-
        number gutter, honouring Ctrl-toggle and Shift-extend
        modifiers."""
        tv = self.widget
        sm = tv.selectionModel()
        model = tv.model()
        offset = self._col_offset()
        ncols = len(self._user_columns)
        if ncols == 0:
            return

        if shift and self._cell_anchor is not None:
            a_row, _ = self._cell_anchor
            rmin, rmax = (a_row, row) if a_row <= row else (row, a_row)
            sel = QtCore.QItemSelection(
                model.index(rmin, offset),
                model.index(rmax, offset + ncols - 1))
            sm.clear()
            sm.select(sel, QtCore.QItemSelectionModel.Select)
            # Anchor unchanged on Shift-extend (Excel-style).
            return

        sel = QtCore.QItemSelection(
            model.index(row, offset),
            model.index(row, offset + ncols - 1))
        if ctrl:
            sm.select(sel, QtCore.QItemSelectionModel.Toggle)
        else:
            sm.clear()
            sm.select(sel, QtCore.QItemSelectionModel.Select)
        self._cell_anchor = (row, 0)

    def _header_section_clicked(self, logical_index):
        """Header click → sort and/or column-select.

        When ``sortable`` is on, plain click sorts (we drive it
        ourselves since ``setSortingEnabled`` is off in cell mode);
        modifier clicks select.  When ``sortable`` is off, every
        click selects.  Always: only fires in cell mode (the
        signal is connected unconditionally but the handler bails
        out for row modes)."""
        if not self._is_cell_mode():
            return
        user_col = logical_index - self._col_offset()
        if user_col < 0 or user_col >= len(self._user_columns):
            return
        mods = QtGui.QApplication.keyboardModifiers()
        ctrl = bool(mods & QtCore.Qt.ControlModifier) or \
            bool(mods & QtCore.Qt.MetaModifier)
        shift = bool(mods & QtCore.Qt.ShiftModifier)

        # Plain click on a sortable header → sort, not select.
        if self.sortable and not (ctrl or shift):
            asc = True
            cur_col, cur_asc = (self.widget.header().sortIndicatorSection(),
                                self.widget.header().sortIndicatorOrder()
                                == QtCore.Qt.AscendingOrder)  # noqa318

            if cur_col == logical_index:
                asc = not cur_asc
            self.sort_by_column(user_col, ascending=asc)
            return

        self._do_column_select(user_col, ctrl, shift)

    def _do_column_select(self, user_col, ctrl, shift):
        """Select an entire column (all rows) via header click,
        honouring Ctrl-toggle and Shift-extend modifiers."""
        tv = self.widget
        sm = tv.selectionModel()
        model = tv.model()
        nrows = tv.topLevelItemCount()
        if nrows == 0:
            return
        offset = self._col_offset()
        col = user_col + offset

        if shift and self._cell_anchor is not None:
            _, a_col = self._cell_anchor
            cmin, cmax = (a_col, user_col) if a_col <= user_col \
                else (user_col, a_col)
            sel = QtCore.QItemSelection(
                model.index(0, cmin + offset),
                model.index(nrows - 1, cmax + offset))
            sm.clear()
            sm.select(sel, QtCore.QItemSelectionModel.Select)
            return

        sel = QtCore.QItemSelection(
            model.index(0, col),
            model.index(nrows - 1, col))
        if ctrl:
            sm.select(sel, QtCore.QItemSelectionModel.Toggle)
        else:
            sm.clear()
            sm.select(sel, QtCore.QItemSelectionModel.Select)
        self._cell_anchor = (0, user_col)

    # ----- clipboard -------------------------------------------

    def _build_selection_tsv(self):
        """Build a TSV string from the bounding rectangle of the
        current selection.  Gaps emit empty cells."""
        if self._is_cell_mode():
            cells = self.get_selected_cells()
            keyed = {(c['path'][0], c['col_key']):
                     ('' if c['value'] is None else str(c['value']))
                     for c in cells}
            if not keyed:
                return ''
            rows = sorted({r for (r, _) in keyed})
            user_keys = self._user_col_keys()
            cols_used = sorted({user_keys.index(k)
                                for (_, k) in keyed
                                if k in user_keys})
            if not cols_used:
                return ''
            cMin, cMax = cols_used[0], cols_used[-1]
            lines = []
            for r in rows:
                cells_row = []
                for c in range(cMin, cMax + 1):
                    cells_row.append(keyed.get((r, user_keys[c]), ''))
                lines.append('\t'.join(cells_row))
            return '\n'.join(lines)
        # Row mode: every selected row gets serialised in full.
        paths = self.get_selected_paths()
        if not paths:
            return ''
        rows = sorted(p[0] for p in paths)
        lines = []
        for r in rows:
            row_dict = self.get_row(r)
            lines.append('\t'.join(
                ('' if row_dict.get(k) is None else str(row_dict[k]))
                for k in self._user_col_keys()))
        return '\n'.join(lines)

    def _selection_top_left(self):
        """Return ``(row, col_index)`` of the top-left cell in the
        current selection, or None if empty."""
        if self._is_cell_mode():
            cells = self.get_selected_cells()
            if not cells:
                return None
            user_keys = self._user_col_keys()
            r_min = min(c['path'][0] for c in cells)
            c_min = min(user_keys.index(c['col_key'])
                        for c in cells if c['col_key'] in user_keys)
            return (r_min, c_min)
        paths = self.get_selected_paths()
        if not paths:
            return None
        return (min(p[0] for p in paths), 0)

    def copy_selection(self):
        tsv = self._build_selection_tsv()
        if not tsv:
            return
        QtGui.QApplication.clipboard().setText(tsv)
        self.make_callback('copy', tsv)

    def cut_selection(self):
        tsv = self._build_selection_tsv()
        if not tsv:
            return
        QtGui.QApplication.clipboard().setText(tsv)
        # Clear editable cells in the selection.
        offset = self._col_offset()
        user_keys = self._user_col_keys()
        if self._is_cell_mode():
            for c in self.get_selected_cells():
                if c['col_key'] not in user_keys:
                    continue
                user_col = user_keys.index(c['col_key'])
                if user_col not in self._editable_cols:
                    continue
                row = c['path'][0]
                old = c['value']
                self.set_cell(row, user_col, '')
                self.make_callback('cell_edited', [row], c['col_key'],
                                   old, '')
        else:
            for path in self.get_selected_paths():
                row = path[0]
                for user_col in range(len(self._user_columns)):
                    if user_col not in self._editable_cols:
                        continue
                    col_key = self._user_columns[user_col]['key']
                    it = self.widget.topLevelItem(row)
                    old = it.text(user_col + offset) if it else ''
                    self.set_cell(row, user_col, '')
                    self.make_callback('cell_edited', [row], col_key,
                                       old, '')
        self.make_callback('cut', tsv)

    def paste_selection(self):
        text = QtGui.QApplication.clipboard().text()
        if text is None or text == '':
            return
        anchor = self._selection_top_left()
        if anchor is None:
            return
        anchor_row, anchor_col = anchor
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        rows = text.split('\n')
        # Drop trailing empty row left over by most clipboards.
        while rows and rows[-1] == '':
            rows.pop()
        n_user_cols = len(self._user_columns)
        n_rows = self.get_row_count()
        offset = self._col_offset()
        for i, line in enumerate(rows):
            r = anchor_row + i
            if r >= n_rows:
                break
            cells = line.split('\t')
            for j, val in enumerate(cells):
                c = anchor_col + j
                if c >= n_user_cols:
                    break
                if c not in self._editable_cols:
                    continue
                col_key = self._user_columns[c]['key']
                it = self.widget.topLevelItem(r)
                old = it.text(c + offset) if it else ''
                self.set_cell(r, c, val)
                self.make_callback('cell_edited', [r], col_key, old, val)
        self.make_callback('paste', text)


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
        try:
            return l.index(nchild)
        except (IndexError, ValueError) as e:
            return -1

    def _native_to_child(self, nchild):
        idx = self._get_native_index(nchild)
        if idx < 0:
            return None
        return self.children[idx]

    def set_padding(self, px):
        layout = self.widget.layout()
        if layout is None:
            return
        if isinstance(px, int):
            layout.setContentsMargins(px, px, px, px)
        else:
            layout.setContentsMargins(*px)

    def set_margins(self, left, right, top, bottom):
        layout = self.widget.layout()
        if layout is None:
            return
        layout.setContentsMargins(left, right, top, bottom)

    def set_border_width(self, pix):
        layout = self.widget.layout()
        if layout is None:
            return
        layout.setContentsMargins(pix, pix, pix, pix)

    def set_border_color(self, color):
        pass


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

    def set_align(self, align):
        """Cross-axis alignment for the children laid out in this
        Box.  Accepted values depend on the Box's ``orientation``:

        * horizontal box → ``'top'`` / ``'center'`` / ``'bottom'``
        * vertical box   → ``'left'`` / ``'center'`` / ``'right'``

        Only visible when the Box's parent gives it more cross-axis
        space than the children need."""
        flag = self._resolve_align(align)
        self.layout.setAlignment(flag)

    def _resolve_align(self, align):
        align = align.lower()
        if self.orientation == 'horizontal':
            mapping = {'top':    QtCore.Qt.AlignTop,
                       'center': QtCore.Qt.AlignVCenter,
                       'bottom': QtCore.Qt.AlignBottom}
            expected = "'top' | 'center' | 'bottom'"
        else:
            mapping = {'left':   QtCore.Qt.AlignLeft,
                       'center': QtCore.Qt.AlignHCenter,
                       'right':  QtCore.Qt.AlignRight}
            expected = "'left' | 'center' | 'right'"
        if align not in mapping:
            raise ValueError(
                f"{self.orientation} Box.set_align expects {expected}, "
                f"got {align!r}")
        return mapping[align]


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
                os.path.join(icondir, 'triangle-right.svg'), size=(12, 12))
        if Expander.d_arrow is None:
            Expander.d_arrow = QtHelp.get_icon(
                os.path.join(icondir, 'triangle-down.svg'), size=(12, 12))

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


class FixedLayout(ContainerBase):
    """A container widget in which children can be placed at fixed
    positions.
    """
    def __init__(self):
        super().__init__()

        self.widget = QtGui.QWidget()

    def add_widget(self, child, x_px, y_px):
        child_w = child.get_widget()
        child_w.setParent(self.widget)

        child_w.move(x_px, y_px)
        self.add_ref(child)

    def remove(self, child, delete=False):
        if child not in self.children:
            raise ValueError("Widget is not a child of this container")
        self.children.remove(child)

        child_w = child.get_widget()
        child_w.unParent()
        if delete:
            child_w.deleteLater()

        self.make_callback('widget-removed', child)


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
        w.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        w.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        # See note below in add_widget()
        #w.subWindowActivated.connect(self._cb_redirect)
        # disable wheel event scrolling the space
        w.wheelEvent = self.wheelEvent

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

    def get_child_size(self, child):
        subwin = self._get_subwin(child.get_widget())
        return subwin.width(), subwin.height()

    def get_child_position(self, child):
        subwin = self._get_subwin(child.get_widget())
        return subwin.x(), subwin.y()

    def tile_panes(self):
        self.widget.tileSubWindows()

    def cascade_panes(self):
        self.widget.cascadeSubWindows()

    def use_tabs(self, tf):
        if tf:
            self.widget.setViewMode(QtGui.QMdiArea.TabbedView)
        else:
            self.widget.setViewMode(QtGui.QMdiArea.SubWindowView)

    def wheelEvent(self, event):
        event.accept()


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
        self.widget = w
        self._set_name(self.widget)
        self.orientation = orientation
        # NOTE: need to style splitter due to lack of any visual
        # indicator on Linux and Windows
        if self.orientation == 'horizontal':
            w.setOrientation(QtCore.Qt.Horizontal)
            if thumb_px is not None:
                iconfile = pathlib.Path(icondir) / 'vdots.png'
                w.setStyleSheet(
                    """
                    #%s::handle { width: %spx; height: %spx;
                                  image: url(%s); }
                    """ % (self._get_name(), self.thumb_px, self.thumb_px,
                           iconfile))
        else:
            w.setOrientation(QtCore.Qt.Vertical)
            if thumb_px is not None:
                iconfile = pathlib.Path(icondir) / 'hdots.png'
                w.setStyleSheet(
                    """
                    #%s::handle { height: %spx; image: url(%s); }
                    """ % (self._get_name(), self.thumb_px, iconfile))
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
        self.tbl = {}

    def resize_grid(self, rows, columns):
        pass

    def set_row_spacing(self, val):
        self.widget.layout().setVerticalSpacing(val)

    def set_column_spacing(self, val):
        self.widget.layout().setHorizontalSpacing(val)

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def get_row_column_count(self):
        num_rows = self.widget.layout().rowCount()
        num_cols = self.widget.layout().columnCount()
        return num_rows, num_cols

    def add_widget(self, child, row, col, stretch=0):
        key = (row, col)
        if key in self.tbl:
            # take care of case where we are overwriting a child
            old_child = self.tbl[key]
            old_child.hide()
            self.remove(old_child)
        self.tbl[key] = child
        self.add_ref(child)

        w = child.get_widget()
        self.widget.layout().addWidget(w, row, col)
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
        num_rows, num_cols = self.get_row_column_count()

        if widgets is not None:
            if len(widgets) != num_cols:
                raise ValueError("Number of widgets ({}) != number of columns ({})".format(len(widgets), num_cols))

        # handle case where user inserts row before the end of the gridbox
        if index < num_rows:
            # shift key/value pairs down to make the row empty at index
            for i in range(num_rows - 1, index - 1, -1):
                for j in range(num_cols):
                    key = (i, j)
                    if key in self.tbl:
                        child = self.tbl.pop(key)
                        self.tbl[(i + 1, j)] = child
                        # move actual widget down in QGridLayout
                        w = child.get_widget()
                        self._remove(w)
                        self.widget.layout().addWidget(w, i + 1, j)

        if widgets is not None:
            for j in range(num_cols):
                child = widgets[j]
                self.add_widget(child, index, j)

    def append_row(self, widgets):
        num_rows, num_cols = self.get_row_column_count()
        return self.insert_row(num_rows, widgets)

    def delete_row(self, index):
        num_rows, num_cols = self.get_row_column_count()
        if index < 0 or index >= num_rows:
            raise ValueError("Index ({}) out of bounds ({})".format(index, num_rows))

        # remove widgets in row to be deleted from table
        for j in range(num_cols):
            key = (index, j)
            if key in self.tbl:
                child = self.tbl.pop(key)
                child.hide()
                self.remove(child)

        if index < num_rows - 1:
            # if not removing very last row, shift key/value pairs up
            for i in range(index + 1, num_rows):
                for j in range(num_cols):
                    key = (i, j)
                    if key in self.tbl:
                        child = self.tbl.pop(key)
                        self.tbl[(i - 1, j)] = child
                        # move actual widget up in QGridLayout
                        w = child.get_widget()
                        self._remove(w)
                        self.widget.layout().addWidget(w, i - 1, j)


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
        self._set_name(self.widget)
        self._menu = None
        myname = self._get_name()
        self.widget.setStyleSheet(
            """
            #%s { padding: 0; spacing: 1; }\n
            #%s QToolButton { padding: 2; margin: 0; }\n
            """ % (myname, myname))

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        child = ToolbarAction()
        if iconpath is not None:
            wd, ht = 24, 24
            if iconsize is not None:
                wd, ht = iconsize
            iconw = QtHelp.get_icon(iconpath, size=(wd, ht))
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

    def add_spacer(self):
        spacer = QtGui.QWidget()
        spacer.setSizePolicy(QtGui.QSizePolicy.Expanding,
                             QtGui.QSizePolicy.Expanding)
        self.widget.addWidget(spacer)


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
        if hasattr(self.widget, 'setToolTipsVisible'):
            # only for QT >= 5.1
            self.widget.setToolTipsVisible(True)
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
                if hasattr(self.widget, 'exec_'):
                    # PySide2
                    self.widget.exec_(w.mapToGlobal(QtCore.QPoint(0, 0)))
                else:
                    self.widget.exec(w.mapToGlobal(QtCore.QPoint(0, 0)))
        else:
            if self.widget.isEnabled():
                if hasattr(self.widget, 'exec_'):
                    # PySide2
                    self.widget.exec_(QCursor.pos())
                else:
                    self.widget.exec(QCursor.pos())

    def get_menu(self, name):
        return self.menus[name]


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = QtGui.QMenuBar()
        if hasattr(self.widget, 'setNativeMenuBar'):
            self.widget.setNativeMenuBar(True)
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
    def __init__(self, parent, child, title='', iconpath=None):
        """NOTE: this widget is not meant to be instantiated except *inside*
        of MDIWidget implementation.
        """
        WidgetBase.__init__(self)
        self.parent = parent
        w = QtGui.QMdiSubWindow(parent.get_widget())
        # replace Qt logo from subwindow
        if iconpath is None:
            iconpath = app_icon_path
        w.setWindowIcon(QIcon(iconpath))
        #w.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.widget = w

        child_w = child.get_widget()
        # what size does the widget want to be?
        wd, ht = child_w.width(), child_w.height()
        w.setWidget(child_w)
        w.resize(wd, ht)

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

    def set_icon(self, iconpath):
        self.widget.setWindowIcon(QIcon(iconpath))

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

    def __init__(self, title=None, iconpath=None):
        ContainerBase.__init__(self)

        widget = QtHelp.TopLevel()

        if iconpath is None:
            iconpath = app_icon_path
        widget.setWindowIcon(QIcon(iconpath))
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

    def set_icon(self, iconpath):
        # NOTE: not guaranteed to work after the window is created because
        # this can be rendered by the window manager. Better to use the
        # constructor 'iconpath' parameter
        self.widget.setWindowIcon(QIcon(iconpath))


class Application(Callback.Callbacks):

    def __init__(self, logger=None, settings=None, ws_sock=None):
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
        #QtGui.QApplication.setAttribute(QtCore.Qt.AA_DisableHighDpiScaling, True)

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

        for name in ('close', 'shutdown'):
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
        self.add_window(w)
        return w

    def make_timer(self):
        return QtHelp.Timer()

    def get_url(self):
        return None

    def is_web_backend(self):
        return False

    def mainloop(self):
        self._qtapp.exec()

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

        self._qtapp.quit()


class Dialog(TopLevelMixin, WidgetBase):

    def __init__(self, title='', flags=None, buttons=[],
                 parent=None, modal=False, autoclose=False):
        WidgetBase.__init__(self)

        if parent is not None:
            parent = parent.get_widget()
        self.widget = QtGui.QDialog(parent)
        self.widget.setModal(modal)
        self.buttons = []

        vbox = QtGui.QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 0)
        self.widget.setLayout(vbox)

        TopLevelMixin.__init__(self, title=title)

        self.content = VBox()
        vbox.addWidget(self.content.get_widget(), stretch=1)

        # buttons
        hbox = HBox()
        hbox.set_padding(5)
        hbox.set_spacing(4)
        self.buttonbox = hbox
        vbox.addWidget(hbox.get_widget(), stretch=0)

        if len(buttons) > 0:
            for name, val in buttons:
                btn = Button(name)
                self.add_button(btn, val)

            # self.widget.closeEvent = lambda event: self.delete()

        self.enable_callback('activated')

        if autoclose:
            self.add_callback('close', lambda w: w.hide())

    def _cb_redirect(self, w, val):
        self.make_callback('activated', val)

    def get_content_area(self):
        return self.content

    def add_button(self, btn, val):
        self.buttons.append(btn)

        btn.add_callback('activated', self._cb_redirect, val)
        self.buttonbox.add_widget(btn, stretch=1)

    def popup(self, parent=None):
        if parent is not None:
            self.widget.setParent(parent.get_widget())
        self.widget.show()


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
            self.set_title(title)
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


class ColorDialog(TopLevelMixin, WidgetBase):
    """A color selection dialog."""
    def __init__(self, title='', initial_color='blue',
                 parent=None, modal=False):
        WidgetBase.__init__(self)

        if parent is not None:
            parent = parent.get_widget()
        self.widget = QtGui.QColorDialog(parent)
        self.widget.setModal(modal)
        self.set_color(initial_color)
        self.widget.colorSelected.connect(self._cb_redirect)
        self.widget.currentColorChanged.connect(self._cb_changed)
        self._chosen_color = self.get_color(format='tuple')

        TopLevelMixin.__init__(self, title=title)

        for name in ['activated', 'pick']:
            self.enable_callback(name)

    def _cb_redirect(self, q_color):
        r, g, b, a = q_color.getRgbF()
        self._chosen_color = (r, g, b, a)
        self.make_callback('activated', self._chosen_color)

    def _cb_changed(self, q_color):
        r, g, b, a = q_color.getRgbF()
        self.make_callback('pick', (r, g, b, a))

    def get_color(self, format='tuple'):
        if format == 'tuple':
            return self._chosen_color
        if format == 'hex':
            return colors.get_hex(self._chosen_color[:3])
        raise ValueError(f"bad format type: '{format}'; should be 'tuple' or 'hex'")

    def set_color(self, color):
        (r, g, b) = colors.resolve_color(color)
        self._chosen_color = (r, g, b)
        q_color = QtHelp.get_color((r, g, b), 1.0)
        self.widget.setCurrentColor(q_color)

    def popup(self, parent=None):
        if parent is not None:
            self.widget.setParent(parent.get_widget())
        self.widget.open()


class FileDialog(TopLevelMixin, WidgetBase):
    """A file/directory selection dialog."""
    def __init__(self, title='', parent=None, modal=False):
        WidgetBase.__init__(self)

        if parent is not None:
            parent = parent.get_widget()
        self.widget = QtGui.QFileDialog(parent)
        self.widget.setFileMode(QtGui.QFileDialog.AnyFile)  # default, unless changed
        self.widget.setModal(modal)
        self.widget.filesSelected.connect(self._cb_redirect)
        self.filter_dict = dict()

        TopLevelMixin.__init__(self, title=title)

        for name in ['activated']:
            self.enable_callback(name)

    def set_mode(self, mode):
        self.widget.setOption(QtGui.QFileDialog.ShowDirsOnly, False)
        if mode == 'save':
            self.widget.setFileMode(QtGui.QFileDialog.AnyFile)
            self.widget.setAcceptMode(QtGui.QFileDialog.AcceptSave)
        elif mode == 'file':
            self.widget.setFileMode(QtGui.QFileDialog.ExistingFile)
        elif mode == 'files':
            self.widget.setFileMode(QtGui.QFileDialog.ExistingFiles)
        elif mode == 'directory':
            self.widget.setFileMode(QtGui.QFileDialog.Directory)
            self.widget.setOption(QtGui.QFileDialog.ShowDirsOnly, True)

    def set_directory(self, path):
        if not os.path.isdir(path):
            raise ValueError(f"{path} does not seem to be an existing directory")
        self.widget.setDirectory(path)

    def set_filename(self, path):
        if os.path.isdir(path):
            return self.set_directory(path)

        _dir, filename = os.path.split(path)
        if len(_dir) > 0:
            if not os.path.isdir(_dir):
                raise ValueError(f"{_dir} does not seem to be an existing directory")
            self.widget.setDirectory(_dir)
        self.widget.selectFile(filename)

    def clear_filters(self):
        self.filter_dict = dict()
        self.widget.setNameFilter("")

    def add_ext_filter(self, category, file_ext):
        exts = self.filter_dict.setdefault(category, [])
        if not file_ext.startswith('.'):
            file_ext = '.' + file_ext
        exts.append(f"*{file_ext}")

        l = []
        for category, exts in self.filter_dict.items():
            l.append("{} ({})".format(category, ' '.join(exts)))
        s = ';;'.join(l)
        self.widget.setNameFilter(s)

    def _cb_redirect(self, paths):
        if len(paths) > 0:
            self.make_callback('activated', paths)

    def popup(self, parent=None):
        if parent is not None:
            self.widget.setParent(parent.get_widget())
        self.widget.open()


class DragPackage:
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
    elif wtype in ('textentry', 'entry'):
        w = TextEntry()
        # w.widget.setMaxLength(12)
    elif wtype in ('textentryset', 'entryset'):
        w = TextEntrySet()
        # w.widget.setMaxLength(12)
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
