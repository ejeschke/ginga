#
# Widgets.py -- wrapped HTML widgets and convenience functions
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import threading
import time
import binascii
from functools import reduce

from ginga.misc import Callback, Bunch
import ginga.icons

# path to our icons
icondir = os.path.split(ginga.icons.__file__)[0]

class WidgetError(Exception):
    """For errors thrown in this module."""
    pass

# widget id counter
widget_id = 0
# widget dict
widget_dict = {}
tab_idx = 0
# reference to the created application
_app = None


# BASE
class WidgetBase(Callback.Callbacks):

    def __init__(self):
        global widget_id, widget_dict

        super(WidgetBase, self).__init__()

        self.widget = None
        self.changed = False
        self.enabled = True
        self.tooltip = ''
        widget_id += 1
        self.id = widget_id
        widget_dict[widget_id] = self

    def get_url(self):
        app = self.get_app()
        return "%s?id=%d" % (app.base_url, self.id)

    def get_app(self):
        return _app

    def get_widget(self):
        return self.widget

    def set_tooltip(self, text):
        self.tooltip = text

    def set_enabled(self, tf):
        self.enabled = tf
        app = self.get_app()
        app.do_operation('disable', id=self.id, value=not tf)

    def render(self):
        return '''<!-- NOT YET RENDERED! -->'''

# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text=''):
        super(TextEntry, self).__init__()

        self.widget = None
        self.text = text
        self.length = 20    # seems to be default HTML5 size

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.text = event.value
        self.make_callback('activated')

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='', size=20)
        if not self.enabled:
            d['disabled'] = 'disabled'
        return '''<input id=%(id)s type="text" size=%(size)d name="%(id)s" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(text)s">''' % d

class TextEntrySet(WidgetBase):
    def __init__(self, text=''):
        super(TextEntrySet, self).__init__()

        self.widget = None
        self.text = text
        ## self.entry = None
        ## self.btn = None
        self.length = 20    # seems to be default HTML5 size

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.text = event.value
        self.make_callback('activated')

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='', size=20)
        return '''<span> <input id=%(id)s type="text" size=%(size)d name="%(id)s" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(text)s"/>
 <input type="button" %(disabled)s onclick="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="Set"/> </span>''' % d

class TextArea(WidgetBase):
    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        self.widget = None
        self.editable = editable
        self.wrap = wrap
        self.text = ''

    def _cb_redirect(self, event):
        self.text = event.value
        #self.make_callback('activated')

    def append_text(self, text, autoscroll=True):
        if text.endswith('\n'):
            text = text[:-1]
        self.text.append(text)
        if not autoscroll:
            return

    def get_text(self):
        return self.text

    def clear(self):
        self.text = ""

    def set_text(self, text):
        self.text = text

    def set_limit(self, numlines):
        # for compatibility with the other supported widget sets
        pass

    def set_font(self, font):
        pass

    def set_wrap(self, tf):
        self.wrap = tf

    def render(self):
        # TODO: handle wrapping
        d = dict(id=self.id, text=self.text, disabled='', editable='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if not self.editable:
            d['editable'] = 'readOnly'
        return '''<textarea id=%(id)s name="%(id)s" %(disabled)s %(editable)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)">%(text)s</textarea>''' % d

class Label(WidgetBase):
    def __init__(self, text=''):
        super(Label, self).__init__()

        self.text = text
        self.widget = None

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        app = self.get_app()
        app.do_operation('update_label', id=self.id, value=text)

    def render(self):
        d = dict(id=self.id, text=self.text)
        return '''<span id=%(id)s>%(text)s</span>''' % d


class Button(WidgetBase):
    def __init__(self, text=''):
        super(Button, self).__init__()

        self.text = text
        self.widget = None
        #self.widget.clicked.connect(self._cb_redirect)

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.make_callback('activated')

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        return '''<input id=%(id)s type="button" %(disabled)s onclick="ginga_app.widget_handler('%(id)s', 0)" value="%(text)s">''' % d

class ComboBox(WidgetBase):
    def __init__(self, editable=False, multi_choice=False):
        super(ComboBox, self).__init__()

        self.widget = None
        self.index = 0
        self.multi_choice = multi_choice
        self.choices = []

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.index = int(event.value)
        self.make_callback('activated', self.index)

    def insert_alpha(self, text):
        index = 0
        num_choices = len(self.choices)
        while True:
            if index >= num_choices:
                self.choices.append(text)
                return
            item_text = self.choices[index]
            if item_text > text:
                self.choices.insert(index, text)
                return
            index += 1

    def delete_alpha(self, text):
        self.choices.remove(text)

    def clear(self):
        self.choices = []

    def show_text(self, text):
        index = self.choices.index(text)
        self.set_index(index)

    def append_text(self, text):
        self.choices.append(text)

    def set_index(self, index):
        self.index = index
        app = self.get_app()
        app.do_operation('update_index', id=self.id, value=self.index)

    def get_index(self):
        return self.index

    def render(self):
        d = dict(id=self.id, disabled='')
        if self.multi_choice:
            d['multiple'] = 'multiple'
        else:
            d['multiple'] = ''
        if not self.enabled:
            d['disabled'] = 'disabled'
        res = ['''<select id=%(id)s %(disabled)s name="%(id)s" %(multiple)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)">''' % d]
        for idx, choice in enumerate(self.choices):
            if idx == self.index:
                selected = 'selected'
            else:
                selected = ''
            res.append('''  <option value="%d" %s>%s</option>''' % (
                idx, selected, choice))
        res.append('''</select>''')
        return '\n'.join(res)

class SpinBox(WidgetBase):
    def __init__(self, dtype=int):
        super(SpinBox, self).__init__()

        self.dtype = dtype
        self.widget = None
        self.value = None
        self.decimals = 0
        self.minval = None
        self.maxval = None
        self.incr = None

        self.enable_callback('value-changed')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('value-changed', self.value)

    def get_value(self):
        return self.dtype(self.value)

    def set_value(self, val):
        self.changed = True
        self.value = val

    def set_decimals(self, num):
        self.decimals = num

    def set_limits(self, minval, maxval, incr_value=1):
        self.minval = minval
        self.maxval = maxval
        self.incr = incr_value

    def render(self):
        d = dict(id=self.id, value=self.value, step=self.incr,
                 max=self.maxval, min=self.minval, disabled='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.dtype == float:
            return '''<input id=%(id)s %(disabled)s type="number" onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(value)f" step="%(step)f" max="%(max)f" min="%(min)f">''' % d
        else:
            return '''<input id=%(id)s %(disabled)s type="number" onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(value)d" step="%(step)d" max="%(max)d" min="%(min)d">''' % d


class Slider(WidgetBase):
    def __init__(self, orientation='horizontal', track=False):
        super(Slider, self).__init__()

        self.orientation = orientation
        self.track = track
        self.widget = None
        self.value = None

        self.enable_callback('value-changed')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('value-changed', self.value)

    def get_value(self):
        return self.value

    def set_value(self, val):
        self.changed = True
        self.value = val

    def set_tracking(self, tf):
        pass

    def set_limits(self, minval, maxval, incr_value=1):
        self.minval = minval
        self.maxval = maxval
        self.incr = incr_value

    def render(self):
        d = dict(id=self.id, value=self.value, step=self.incr,
                 max=self.maxval, min=self.minval, disabled='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.dtype == float:
            return '''<input id=%(id)s type="range" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(value)f" step="%(incr)f" max="%(max)f" min="%(min)f" disabled=%(disabled)s>''' % d
        else:
            return '''<input id=%(id)s type="range" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(text)d" step="%(incr)d" max="%(max)d" min="%(min)d"  disabled=%(disabled)s>''' % d

class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        # if orientation == 'horizontal':
        #     self.widget = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        # else:
        #     self.widget = QtGui.QScrollBar(QtCore.Qt.Vertical)
        # self.widget.valueChanged.connect(self._cb_redirect)
        self.widget = None
        self.value = None

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)


class CheckBox(WidgetBase):
    def __init__(self, text=''):
        super(CheckBox, self).__init__()

        self.widget = None
        self.value = False
        self.text = text

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)

    def set_state(self, tf):
        self.value = tf

    def get_state(self):
        val = self.value
        return val

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        return '''<input id=%(id)s type="checkbox" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').checked)" value="%(text)s"><label for="%(id)s">%(text)s</label>''' % d

class ToggleButton(WidgetBase):
    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        ## self.widget = QtGui.QPushButton(text)
        ## self.widget.setCheckable(True)
        ## self.widget.clicked.connect(self._cb_redirect)
        self.widget = None
        self.value = False
        self.text = text

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)

    def set_state(self, tf):
        self.value = tf

    def get_state(self):
        return self.value

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        return '''<input id=%(id)s type="checkbox" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').checked)" value="%(text)s"><label for="%(id)s">%(text)s</label>''' % d


class RadioButton(WidgetBase):

    group_cnt = 0

    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        ## self.widget = QtGui.QRadioButton(text)
        ## self.widget.toggled.connect(self._cb_redirect)
        self.widget = None
        self.text = text
        self.value = False
        self.group_name = None
        if group is None:
            self.group_name = "radio%d" % (RadioButton.group_cnt)
            RadioButton.group_cnt += 1
            self.group = [self]
        else:
            self.group = group.group
            self.group_name = group.group_name

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', event.value)

    def set_state(self, tf):
        if self.value != tf:
            # toggled only fires when the value is toggled
            self.changed = True
            self.value = tf

    def get_state(self):
        return self.value

    def render(self):
        d = dict(id=self.id, disabled='', checked='',
                 group=self.group_name, text=self.text)
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.value:
            d['checked'] = 'checked'
        return '''<input id=%(id)s name="%(group)s" type="radio" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" %(checked)s value="true">%(text)s''' % d

class ProgressBar(WidgetBase):
    def __init__(self):
        super(ProgressBar, self).__init__()

        ## w = QtGui.QProgressBar()
        ## w.setRange(0, 100)
        ## w.setTextVisible(True)
        self.widget = None
        self.value = None

    def set_value(self, pct):
        self.value = pct


class Canvas(WidgetBase):

    canvas_template = '''
    <canvas id="%(id)s" tabindex="%(tab_idx)d"
       width="%(width)s" height="%(height)s">Your browser does not appear to
support HTML5 canvas.</canvas>
    <script type="text/javascript">
        ginga_initialize_canvas(document.getElementById("%(id)s"), "%(id)s",
                                  ginga_app);
    </script>
'''
    def __init__(self, width=600, height=600):
        super(Canvas, self).__init__()

        self.widget = None
        self.width = width
        self.height = height

        self.timers = {}

    def _cb_redirect(self, event):
        pass

    def _draw(self, shape_type, **kwargs):
        shape = dict(kwargs, type=shape_type)
        app = self.get_app()
        app.do_operation("draw_canvas", id=self.id, shape=shape)

    def clear_rect(self, x, y, width, height):
        self._draw("clear", x=x, y=y, width=width, height=height)

    def draw_image(self, img_buf, x, y, width=None, height=None):

        img_string = binascii.b2a_base64(img_buf)
        if isinstance(img_string, bytes):
            img_string = img_string.decode("utf-8")
        img_src = 'data:image/png;base64,' + img_string

        self._draw("image", x=x, y=y, src=img_src, width=width, height=height)

    def add_timer(self, name, cb_fn):
        app = self.get_app()
        timer = app.add_timer(cb_fn)
        self.timers[name] = timer

    def reset_timer(self, name, time_sec):
        app = self.get_app()
        app.reset_timer(self.timers[name], time_sec)

    def render(self):
        global tab_idx
        # canvas needs a tabindex to be able to focus it and register
        # for keyboard events
        tab_idx += 1

        d = dict(id=self.id, width=self.width, height=self.height,
                 tab_idx=tab_idx)
        return Canvas.canvas_template % d


# CONTAINERS

class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        self.children = []

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def remove(self, w, delete=False):
        if not w in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(w)

    def remove_all(self):
        for w in list(self.children):
            self.remove(w)

    def get_children(self):
        return self.children

    def render_children(self, ifx=' '):
        return ifx.join(map(lambda child: child.render(), self.children))

class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.spacing = 0
        self.margins = (0, 0, 0, 0)   # L, R, T, B

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)
        child_w = child.get_widget()

    def set_spacing(self, val):
        self.spacing = val

    def set_margins(self, left, right, top, bottom):
        self.margins = (left, right, top, bottom)

    def set_border_width(self, pix):
        self.margins = (pix, pix, pix, pix)

    def render(self):
        # TODO: handle spacing attribute
        d = dict(id=self.id)
        style_d = dict(left=self.margins[0], right=self.margins[1],
                       top=self.margins[2], bottom=self.margins[3])
        if self.orientation == 'horizontal':
            d['style'] = "display: table-cell; vertical-align: middle; padding: %(left)dpx %(right)dpx %(top)dpx %(bottom)dpx;" % style_d
            d['content'] = self.render_children()
        else:
            d['style'] = "display: table-cell; horizontal-align: middle; padding: %(left)dpx %(right)dpx %(top)dpx %(bottom)dpx;" % style_d
            d['content'] = self.render_children('<br>')

        return '''<div id=%(id)s style="%(style)s">%(content)s</div>''' % d

class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')

class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')

class Frame(ContainerBase):
    def __init__(self, title=None):
        super(Frame, self).__init__()

        self.widget = None
        self.label = title

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)

    def render(self):
        d = dict(id=self.id, content=self.render_children(), legend=self.label)
        res = '''<fieldset id=%(id)s>'''
        if not self.label is None:
            res += '''<legend>%(legend)s</legend>''' % d
        res += "%(content)s" % d
        res += '''</fieldset>'''
        return res


class Expander(Frame):
    pass

class TabWidget(ContainerBase):
    def __init__(self, tabpos='top'):
        super(TabWidget, self).__init__()

        ## nb = QtGui.QTabWidget()
        ## if tabpos == 'top':
        ##     nb.setTabPosition(QtGui.QTabWidget.North)
        ## elif tabpos == 'bottom':
        ##     nb.setTabPosition(QtGui.QTabWidget.South)
        ## elif tabpos == 'left':
        ##     nb.setTabPosition(QtGui.QTabWidget.West)
        ## elif tabpos == 'right':
        ##     nb.setTabPosition(QtGui.QTabWidget.East)
        ## nb.currentChanged.connect(self._cb_redirect)
        self.widget = None
        self.index = None

    def _cb_redirect(self, event):
        index = event.value
        self.make_callback('activated', index)

    def add_widget(self, child, title=''):
        self.add_ref(child)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        self.index = idx

    def index_of(self, child):
        return self.children.index(child)

class StackWidget(ContainerBase):
    def __init__(self):
        super(StackWidget, self).__init__()

        self.widget = None

    def add_widget(self, child, title=''):
        self.add_ref(child)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        self.index = idx

    def index_of(self, child):
        return self.children.index(child)


class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = None

    def set_widget(self, child):
        self.add_ref(child)

    def render(self):
        return self.render_children()

class Splitter(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Splitter, self).__init__()

        self.orientation = orientation
        self.widget = None
        ## w.setStretchFactor(0, 0.5)
        ## w.setStretchFactor(1, 0.5)

    def add_widget(self, child):
        self.add_ref(child)


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        self.widget = None
        self.rows = rows
        self.cols = columns
        self.row_spacing = 0
        self.col_spacing = 0
        self.tbl = {}

    def set_row_spacing(self, val):
        self.row_spacing = val

    def set_column_spacing(self, val):
        self.col_spacing = val

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        self.rows = max(self.rows, row+1)
        self.cols = max(self.cols, col+1)
        self.tbl[(row, col)] = child

    def render(self):
        d = dict(id=self.id)
        res = ['''<table id=%(id)s>''' % d]
        for i in range(self.rows):
            res.append("  <tr>")
            for j in range(self.cols):
                res.append("  <td>")
                key = (row, col)
                if key in self.tbl:
                    res.append(self.tbl[key].render())
                else:
                    res.append("")
                res.append("  </td>")
            res.append("  </tr>")
        return '\n'.join(res)

class ToolbarAction(WidgetBase):
    def __init__(self):
        super(ToolbarAction, self).__init__()

        self.widget = None
        self.value = False
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.widget.isCheckable():
            tf = self.widget.isChecked()
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')

    def set_state(self, tf):
        self.value = tf

    def get_state(self):
        return self.value


class Toolbar(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Toolbar, self).__init__()

        w.orientation = orientation
        self.widget = None

    def add_action(self, text, toggle=False, iconpath=None):
        child = ToolbarAction()
        self.text = text
        if iconpath:
            ## image = QImage(iconpath)
            ## qsize = QtCore.QSize(24, 24)
            ## image = image.scaled(qsize)
            ## pixmap = QPixmap.fromImage(image)
            ## iconw = QIcon(pixmap)
            ## action = self.widget.addAction(iconw, text,
            ##                                child._cb_redirect)
            pass
        else:
            pass
        ##     action = self.widget.addAction(text, child._cb_redirect)
        ## action.setCheckable(toggle)
        child.widget = None
        self.add_ref(child)
        return child

    def add_widget(self, child):
        self.add_ref(child)

    def add_separator(self):
        #self.widget.addSeparator()
        pass


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
        self.add_ref(child)

    def add_name(self, name):
        child = MenuAction(text=name)
        self.add_widget(child)
        return child

    def add_separator(self):
        #self.widget.addSeparator()
        pass


class Menubar(ContainerBase):
    def __init__(self):
        super(Menubar, self).__init__()

        self.widget = None

    def add_widget(self, child):
        self.add_ref(child)

    def add_name(self, name):
        #menu_w = self.widget.addMenu(name)
        child = Menu()
        self.add_ref(child)
        return child


class TopLevel(ContainerBase):
    def __init__(self, title=""):
        super(TopLevel, self).__init__()

        self.title = title
        self.widget = None
        # these are assigned by the Application()
        self.wid = None
        self.url = None
        self.app = None
        #widget.closeEvent = lambda event: self._quit(event)

        self.enable_callback('closed')

    def set_widget(self, child):
        self.add_ref(child)

    def show(self):
        pass

    def hide(self):
        pass

    def close(self):
        self.make_callback('closed')

    def raise_(self):
        pass

    def lower(self):
        pass

    def resize(self, width, height):
        #self.widget.resize(width, height)
        pass

    def focus(self):
        pass

    def move(self, x, y):
        pass

    def maximize(self):
        pass

    def unmaximize(self):
        pass

    def fullscreen(self):
        pass

    def unfullscreen(self):
        pass

    def iconify(self):
        pass

    def uniconify(self):
        pass

    def set_title(self, title):
        self.title = title

    def _cb_redirect(self, event):
        pass

    def render(self):
        base_url = self.app.base_url
        url = base_url + "?wid=%s" % (self.wid)
        ws_url = base_url + "/socket?wid=%s" % (self.wid)
        d = dict(title=self.title, content=self.render_children(),
                 wid=self.wid, url=url, ws_url=ws_url)
        return '''
<!doctype html>
<html>
<head>
    <title>%(title)s</title>
    <style>
      body {
        width: 100%%;
        height: 100%%;
        padding: 0px;
        margin: 0px;
        border: 0;
        overflow: hidden;  /* disable scrollbars */
        display: block; /* no floating content on sides */
      }
    </style>
    <meta name="viewport"
      content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no, target-densitydpi=device-dpi" />
</head>
<body>
    <script type="text/javascript" src="/js/hammer.js"></script>
    <script type="text/javascript" src="/js/application.js"></script>
    <script type="text/javascript">
        var wid = "%(wid)s";
        var url = "%(url)s";
        var ws_url = "ws://" + window.location.host + "/app/socket?wid=%(wid)s";
        var ginga_app = ginga_make_application(ws_url);
    </script>
%(content)s
</body>
</html>''' % d


class Application(object):

    def __init__(self, logger=None, base_url=None):
        global _app, widget_dict

        self.logger = logger
        self.base_url = base_url
        self.window_dict = {}
        self.wincnt = 0
        # list of web socket handlers connected to this application
        self.ws_handlers = []

        _app = self
        widget_dict[0] = self

        self._timer_lock = threading.RLock()
        self._timer_cnt = 0
        self._timer = {}

    def add_window(self, window, wid=None):
        if wid is None:
            wid = 'win%d' % (self.wincnt)
            self.wincnt += 1
        window.wid = wid
        window.url = self.base_url + '?id=%s' % (wid)
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

    def _cb_redirect(self, event):
        #print("application got an event (%s)" % (str(event)))
        pass

    def add_ws_handler(self, handler):
        with self._timer_lock:
            self.ws_handlers.append(handler)

    def do_operation(self, operation, **kwdargs):
        with self._timer_lock:
            handlers = list(self.ws_handlers)

        bad_handlers = []
        for handler in handlers:
            try:
                handler.do_operation(operation, **kwdargs)
            except Exception as e:
                bad_handlers.append(handler)

        # remove problematic clients
        if len(bad_handlers) > 0:
            with self._timer_lock:
                for handler in bad_handlers:
                    self.ws_handlers.remove(handler)

    def on_timer_event(self, event):
        #self.logger.debug("timer update")
        funcs = []
        with self._timer_lock:
            for key, bnch in self._timer.items():
                if (bnch.timer is not None) and \
                   (time.time() > bnch.timer):
                    bnch.timer = None
                    funcs.append(bnch.func)

        for func in funcs:
            try:
                func()
            except Exception as e:
                pass
            #self.logger.debug("update should have been called.")

    def add_timer(self, func):
        with self._timer_lock:
            name = self._timer_cnt
            self._timer_cnt += 1
            timer = Bunch.Bunch(timer=None, func=func, name=name)
            self._timer[name] = timer
            return timer

    def remove_timer(self, timer):
        with self._timer_lock:
            name = timer.name
            del self._timer[name]

    def reset_timer(self, timer, time_sec):
        with self._timer_lock:
            self.logger.debug("setting timer...")
            timer.timer = time.time() + time_sec

    def widget_event(self, event):
        if event.type == "timer":
            self.on_timer_event(event)
            return

        #print("we have an event from '%s' event=%s" % (event.id, str(event)))
        # get the widget associated with this id
        widget = widget_dict[int(event.id)]
        # make the callback for this widget (activation or value-changed)
        widget._cb_redirect(event)

## class SaveDialog(QtGui.QFileDialog):
##     def __init__(self, title=None, selectedfilter=None):
##         super(SaveDialog, self).__init__()

##         self.selectedfilter = selectedfilter
##         self.widget = self.getSaveFileName(self, title, '', selectedfilter)

##     def get_path(self):
##         if self.widget and not self.widget.endswith(self.selectedfilter[1:]):
##             self.widget += self.selectedfilter[1:]
##         return self.widget

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
        #w.widget.setAlignment(QtCore.Qt.AlignRight)
    elif wtype == 'llabel':
        w = Label(title)
        #w.widget.setAlignment(QtCore.Qt.AlignLeft)
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

    ## widget = QtGui.QWidget()
    ## table = QtGui.QGridLayout()
    ## widget.setLayout(table)
    ## table.setVerticalSpacing(2)
    ## table.setHorizontalSpacing(4)
    ## table.setContentsMargins(2, 2, 2, 2)

    table = GridBox(rows=numrows, columns=numcols)

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
                table.add_widget(w, row, col)
                wb[name] = w
            col += 1
        row += 1

    w = hadjust(table, orientation=orientation)

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
