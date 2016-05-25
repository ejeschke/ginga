#
# Widgets.py -- wrapped HTML widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import threading
import time, re
from functools import reduce

from ginga.misc import Callback, Bunch, LineHistory
from ginga.web.pgw import PgHelp
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


default_font = "Arial 8"

def _font_info(font_str):
    """Extract font information from a font string, such as supplied to the
    'font' argument to a widget.
    """
    vals = font_str.split(';')
    point_size, style, weight = 8, 'normal', 'normal'
    family = vals[0]
    if len(vals) > 1:
        style = vals[1]
    if len(vals) > 2:
        weight = vals[2]

    match = re.match(r'^(.+)\s+(\d+)$', family)
    if match:
        family, point_size = match.groups()
        point_size = int(point_size)

    return Bunch.Bunch(family=family, point_size=point_size,
                       style=style, weight=weight)

# BASE
class WidgetBase(Callback.Callbacks):

    def __init__(self):
        global widget_id, widget_dict

        super(WidgetBase, self).__init__()

        self.widget = None
        self.changed = False
        # external data can be attached here
        self.extdata = Bunch.Bunch()
        # generic attributes of widgets
        self.enabled = True
        self.width = 400
        self.height = 800
        self.bgcolor = 'gray'
        self.fgcolor = 'black'
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

    def get_size(self):
        return self.width, self.height

    def delete(self):
        # for now...
        pass

    def resize(self, width, height):
        self.width, self.height = width, height

    def focus(self):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def get_font(self, font_family, point_size):
        font = '%s %s' % (font_family, point_size)
        return font

    def cfg_expand(self, horizontal=0, vertical=0):
        # this is for compatibility with Qt widgets
        pass

    def render(self):
        text = "'%s' NOT YET IMPLEMENTED" % (str(self.__class__))
        d = dict(id=self.id, text=text)
        return '''<span id=%(id)s>%(text)s</span>''' % d

# BASIC WIDGETS

class TextEntry(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntry, self).__init__()

        self.widget = None
        self.text = text
        self.editable = editable
        self.font = default_font
        self.length = 20    # seems to be default HTML5 size

        self.history = LineHistory.LineHistory()

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.text = event.value
        self.history.append(self.get_text())
        self.make_callback('activated')

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        app = self.get_app()
        app.do_operation('update_value', id=self.id, value=text)

    def set_editable(self, tf):
        self.editable = tf

    def set_font(self, font):
        self.font = font

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        # TODO: render font
        d = dict(id=self.id, text=self.text, disabled='', size=20)
        if not self.enabled:
            d['disabled'] = 'disabled'
        return '''<input id=%(id)s type="text" size=%(size)d name="%(id)s" %(disabled)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(text)s">''' % d

class TextEntrySet(WidgetBase):
    def __init__(self, text='', editable=True):
        super(TextEntrySet, self).__init__()

        self.widget = None
        self.text = text
        self.font = default_font
        self.editable = editable
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
        app = self.get_app()
        app.do_operation('update_value', id=self.id, value=text)

    def set_font(self, font):
        self.font = font

    def set_editable(self, tf):
        self.editable = tf

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        # TODO: render font, editable
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
        self.font = default_font

    def _cb_redirect(self, event):
        self.text = event.value
        #self.make_callback('activated')

    def append_text(self, text, autoscroll=True):
        ## if text.endswith('\n'):
        ##     text = text[:-1]
        self.text = self.text + text

        app = self.get_app()
        app.do_operation('update_value', id=self.id, value=self.text)

        if not autoscroll:
            return

    def get_text(self):
        return self.text

    def clear(self):
        self.text = ""

    def set_text(self, text):
        self.text = text

        app = self.get_app()
        app.do_operation('update_value', id=self.id, value=self.text)

    def set_limit(self, numlines):
        # for compatibility with the other supported widget sets
        pass

    def set_editable(self, tf):
        self.editable = tf

    def set_font(self, font):
        self.font = font

    def set_wrap(self, tf):
        self.wrap = tf

    def render(self):
        # TODO: handle wrapping, render font
        d = dict(id=self.id, text=self.text, disabled='', editable='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if not self.editable:
            d['editable'] = 'readOnly'
        return '''<textarea id=%(id)s name="%(id)s" style="width: 100%%;" %(disabled)s %(editable)s onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)">%(text)s</textarea>''' % d

class Label(WidgetBase):
    def __init__(self, text='', halign='left', style='normal', menu=None):
        super(Label, self).__init__()

        self.text = text
        self.font = default_font
        self.halign = halign
        self.style = style
        self.fgcolor = None
        self.bgcolor = None
        self.menu = menu
        self.widget = None

        self.enable_callback('activated')

    def get_text(self):
        return self.text

    def set_text(self, text):
        self.text = text
        app = self.get_app()
        app.do_operation('update_label', id=self.id, value=text)

    def set_font(self, font):
        self.font = font

    def set_color(self, fg=None, bg=None):
        if fg is not None:
            self.fgcolor = fg
        if bg is not None:
            self.bgcolor = bg
        style = self._compose_style()
        app = self.get_app()
        app.do_operation('update_style', id=self.id, value=style)

    def _compose_style(self):
        style = ""
        #style += ("text-align: %s; " % self.halign)
        if self.fgcolor is not None:
            style += ("color: %s; " % self.fgcolor)
        if self.bgcolor is not None:
            style += ("background-color: %s; " % self.bgcolor)
        f_info = _font_info(self.font)
        style += ("font-family: %s; " % f_info.family)
        style += ("font-size: %s; "   % f_info.point_size)
        style += ("font-style: %s; "  % f_info.style)
        style += ("font-weight: %s; " % f_info.weight)
        return style

    def render(self):
        # TODO: render font, alignment, style, menu, clickable
        style = self._compose_style()
        d = dict(id=self.id, text=self.text, style=style)
        return '''<span id=%(id)s style="%(style)s">%(text)s</span>''' % d


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

    def get_alpha(self, idx):
        return self.choices[idx]

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
        self.value = dtype(0)
        self.decimals = 0
        self.minval = dtype(0)
        self.maxval = dtype(0)
        self.incr = dtype(0)

        self.enable_callback('value-changed')

    def _cb_redirect(self, event):
        self.value = self.dtype(event.value)
        self.make_callback('value-changed', self.value)

    def get_value(self):
        return self.dtype(self.value)

    def set_value(self, val):
        self.changed = True
        self.value = self.dtype(val)

    def set_decimals(self, num):
        self.decimals = num

    def set_limits(self, minval, maxval, incr_value=1):
        self.minval = self.dtype(minval)
        self.maxval = self.dtype(maxval)
        self.incr = self.dtype(incr_value)

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
    def __init__(self, orientation='horizontal', track=False, dtype=int):
        super(Slider, self).__init__()

        self.orientation = orientation
        self.track = track
        self.widget = None
        self.dtype = dtype
        self.value = dtype(0)
        self.minval = dtype(0)
        self.maxval = dtype(0)
        self.incr = dtype(0)

        self.enable_callback('value-changed')

    def _cb_redirect(self, event):
        self.value = self.dtype(event.value)
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
        d = dict(id=self.id, value=self.value, incr=self.incr,
                 max=self.maxval, min=self.minval, disabled='',
                 orient='', style='')
        if self.orientation == 'vertical':
            # firefox
            d['orient'] = 'orient=vertical'
            d['style'] = "-webkit-appearance: slider-vertical;"
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.dtype == float:
            return '''<input id=%(id)s type="range" %(disabled)s style="%(style)s" onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(value)f" step="%(incr)f" max="%(max)f" min="%(min)f orient="%(orient)s">''' % d
        else:
            return '''<input id=%(id)s type="range" %(disabled)s style="%(style)s" onchange="ginga_app.widget_handler('%(id)s', document.getElementById('%(id)s').value)" value="%(value)d" step="%(incr)d" max="%(max)d" min="%(min)d orient="%(orient)s">''' % d

class ScrollBar(WidgetBase):
    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        # if orientation == 'horizontal':
        #     self.widget = QtGui.QScrollBar(QtCore.Qt.Horizontal)
        # else:
        #     self.widget = QtGui.QScrollBar(QtCore.Qt.Vertical)
        # self.widget.valueChanged.connect(self._cb_redirect)
        self.widget = None
        self.value = 0.0

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


class Image(WidgetBase):
    def __init__(self, native_image=None, style='normal', menu=None):
        super(Image, self).__init__()

        self.image = None
        self.img_src = ''
        self.menu = menu
        self.widget = None

        self.enable_callback('activated')

        if native_image is not None:
            self._set_image(native_image)

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', event.value)

    def _set_image(self, native_image):
        self.image = native_image
        self.img_src = PgHelp.get_image_src_from_buffer(self.image)

        app = self.get_app()
        app.do_operation('update_imgsrc', id=self.id, value=self.img_src)

    def render(self):
        # TODO: callback for click
        d = dict(id=self.id, src=self.img_src, tooltip=self.tooltip,
                 height=self.height, width=self.width)
        ## return '''<div><img id=%(id)s src="%(src)s" alt="%(tooltip)s"
        ##                 width="%(width)d" height="%(height)d"></div>''' % d
        ## return '''<img id=%(id)s width="%(width)d" height="%(height)d"
        ##              src="%(src)s" alt="%(tooltip)s">''' % d
        return '''<img id=%(id)s src="%(src)s" alt="%(tooltip)s">''' % d

class ProgressBar(Label):
    def __init__(self):
        self.value = 0.0
        self.start_time = time.time()
        super(ProgressBar, self).__init__(self._format())

    def _format(self):
        pct = self.value * 100.0
        elapsed = time.time() - self.start_time
        text = "%.2f %%  %.2f sec" % (pct, elapsed)
        return text

    def set_value(self, pct):
        self.value = pct
        if pct == 0.0:
            # reset start time
            self.start_time = time.time()

        self.set_text(self._format())


class StatusBar(Label):
    def __init__(self):
        super(StatusBar, self).__init__()

    def set_message(self, msg_str):
        # TODO: remove message in about 10 seconds
        self.set_text(msg_str)


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
        self.widget = None

        for cbname in ('selected', 'activated', 'drag-start'):
            self.enable_callback(cbname)

    def setup_table(self, columns, levels, leaf_key):
        self.clear()
        # TODO

    def set_tree(self, tree_dict):
        self.clear()
        self.add_tree(tree_dict)

    def add_tree(self, tree_dict):
        # TODO
        pass

    def _selection_cb(self):
        res_dict = self.get_selected()
        self.make_callback('selected', res_dict)

    def _cb_redirect(self, item):
        res_dict = {}
        self._get_item(res_dict, item)
        self.make_callback('activated', res_dict)

    def get_selected(self):
        res_dict = {}
        return res_dict

    def clear(self):
        self.shadow = {}

    def clear_selection(self):
        pass

    def _path_to_item(self, path):
        s = self.shadow
        for name in path[:-1]:
            s = s[name].node
        item = s[path[-1]].item
        return item

    def select_path(self, path):
        item = self._path_to_item(path)
        # TODO

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)
        # TODO

    def scroll_to_path(self, path):
        item = self._path_to_item(path)
        # TODO

    def sort_on_column(self, i):
        pass

    def set_column_width(self, i, width):
        pass

    def set_column_widths(self, lwidths):
        for i, width in enumerate(lwidths):
            if width is not None:
                self.set_column_width(i, width)

    def set_optimal_column_widths(self):
        for i in range(len(self.columns)):
            pass


class Canvas(WidgetBase):

    canvas_template = '''
    <canvas id="%(id)s" tabindex="%(tab_idx)d"
       style="position: relative; left: 0px; right: 0px; top: 0px; bottom: 0px;"
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
        self.name = ''

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

        img_src = PgHelp.get_image_src_from_buffer(img_buf)

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
        # TODO: probably need to maintain children as list of widget ids
        self.children = []
        self.margins = (0, 0, 0, 0)   # L, R, T, B

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def remove(self, w, delete=False):
        if not w in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(w)

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())

    def remove_all(self):
        self.children[:] = []

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())

    def get_children(self):
        return self.children

    def render(self):
        return self.render_children()

    def set_margins(self, left, right, top, bottom):
        self.margins = (left, right, top, bottom)

    def set_border_width(self, pix):
        self.margins = (pix, pix, pix, pix)

    def render_children(self, ifx=' ', spacing=0, spacing_side='right'):
        def _render_child(child):
            ## return '''<span style="margin-%s: %dpx;">%s</span>''' % (
            ##     spacing_side, spacing, child.render())
            return child.render()
        return ifx.join(map(_render_child, self.children))

class Box(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.spacing = 0

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())

    def set_spacing(self, val):
        self.spacing = val

    def render(self):
        # TODO: handle spacing attribute
        d = dict(id=self.id)
        style_d = dict(left=self.margins[0], right=self.margins[1],
                       top=self.margins[2], bottom=self.margins[3])
        if self.orientation == 'horizontal':
            d['style'] = "display: flex; flex-direction: row; flex-wrap: nowrap; justify-content: flex-start; margin: %(left)dpx %(right)dpx %(top)dpx %(bottom)dpx;" % style_d
            d['content'] = self.render_children(spacing=self.spacing,
                                                spacing_side='right')
        else:
            d['style'] = "display: flex; flex-direction: column; flex-wrap: nowrap; justify-content: flex-start; margin: %(left)dpx %(right)dpx %(top)dpx %(bottom)dpx;" % style_d
            d['content'] = self.render_children(spacing=self.spacing,
                                                spacing_side='bottom')

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

    tab_script_template = '''
    <script>
    ginga_initialize_tab_widget(document.getElementById("%(id)s"), "%(id)s", ginga_app)
    </script>
    '''

    def __init__(self, tabpos='top', reorderable=False, detachable=True,
                 group=0):
        super(TabWidget, self).__init__()

        self.reorderable = reorderable
        self.detachable = detachable
        self.group = group

        self.widget = None
        self.index = 0
        self.set_tab_position(tabpos)
        self.titles = []
        self._tabs_visible = True

        for name in ('page-switch', 'page-close', 'page-move', 'page-detach'):
            self.enable_callback(name)

    def set_tab_position(self, tabpos):
        self.tabpos = tabpos
        # TODO: set tab position
        nb = self.widget
        if tabpos == 'top':
            pass
        elif tabpos == 'bottom':
            pass
        elif tabpos == 'left':
            pass
        elif tabpos == 'right':
            pass

    def _cb_redirect(self, event):
        self.index = event.value
        self.make_callback('page-switch', self.index)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        self.titles.append(title)
        # attach title to child
        child.extdata.tab_title = title

        app = self.get_app()
        #app.do_operation('update_html', id=self.id, value=self.render())
        # this is a hack--we really don't want to reload the page, but just
        # re-rendering the HTML does not seem to process the CSS right
        app.do_operation('reload_page', id=self.id)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        self.index = idx

        app = self.get_app()
        app.do_operation('set_tab', id=self.id, value=self.index)

    def index_of(self, child):
        try:
            return self.children.index(child)
        except ValueError:
            return -1

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        return self.children[idx]

    def render(self):
        d = dict(id=self.id)
        style_d = dict(left=self.margins[0], right=self.margins[1],
                       top=self.margins[2], bottom=self.margins[3])
        d['style'] = "padding: 0; margin: %(left)dpx %(right)dpx %(top)dpx %(bottom)dpx;" % style_d
        res = ['''\n<div id="%(id)s" style="%(style)s">\n''' % d]

        if self._tabs_visible:
            # draw tabs
            res.append('''  <ul>\n''')
            d['cnt'] = 1
            for child in self.get_children():
                d['title'] = self.titles[d['cnt']-1]
                res.append('''<li><a href="#%(id)s-%(cnt)d">%(title)s</a></li>\n''' % d)
                d['cnt'] += 1
            res.append('''  </ul>\n''')

        d['cnt'] = 1
        for child in self.get_children():
            d['content'] = child.render()
            res.append('''<div id="%(id)s-%(cnt)d" style="%(style)s"> %(content)s </div>\n''' % d)
            d['cnt'] += 1

        res.append('''</div>\n''')
        res.append(TabWidget.tab_script_template % d)

        return ''.join(res)

class StackWidget(TabWidget):
    def __init__(self):
        super(StackWidget, self).__init__(tabpos='top', reorderable=False,
                                          detachable=False, group=-1)
        self._tabs_visible = False


class MDIWidget(TabWidget):

    def __init__(self, tabpos='top', mode='tabs'):
        super(MDIWidget, self).__init__(tabpos=tabpos)

        self.mode = 'tabs'
        self.true_mdi = False

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        pass

    def tile_panes(self):
        pass

    def cascade_panes(self):
        pass

    def use_tabs(self, tf):
        pass

class ScrollArea(ContainerBase):
    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = None

        self.enable_callback('configure')

    def set_widget(self, child):
        self.add_ref(child)

    def scroll_to_end(self, vertical=True, horizontal=False):
        pass

    def render(self):
        # TODO: handle spacing attribute
        d = dict(id=self.id)
        child = self.get_children()[0]
        d['content'] = child.render()
        return '''<div id=%(id)s>%(content)s</div>''' % d

class Splitter(Box):

    def get_sizes(self):
        wd, ht = self.get_size()
        if self.orientation == 'horizontal':
            length = wd
        else:
            length = ht
        return length // self.num_children()

    def set_sizes(self, sizes):
        pass

    def _cb_redirect(self, event):
        pass


class GridBox(ContainerBase):
    def __init__(self, rows=1, columns=1):
        super(GridBox, self).__init__()

        self.widget = None
        self.num_rows = rows
        self.num_cols = columns
        self.row_spacing = 0
        self.col_spacing = 0
        self.tbl = {}

    def resize_grid(self, rows, columns):
        self.num_rows = rows
        self.num_cols = columns

    def set_row_spacing(self, val):
        self.row_spacing = val

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def set_column_spacing(self, val):
        self.col_spacing = val

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        self.num_rows = max(self.num_rows, row+1)
        self.num_cols = max(self.num_cols, col+1)
        self.tbl[(row, col)] = child

        app = self.get_app()
        app.do_operation('update_html', id=self.id,
                         value=self.render_body())

    def render_body(self):
        res = []
        for i in range(self.num_rows):
            res.append("  <tr>")
            for j in range(self.num_cols):
                res.append("  <td>")
                key = (i, j)
                if key in self.tbl:
                    res.append(self.tbl[key].render())
                else:
                    res.append("")
                res.append("  </td>")
            res.append("  </tr>")
        return '\n'.join(res)

    def render(self):
        d = dict(id=self.id)
        res = ['''<table id=%(id)s>''' % d]
        res.append(self.render_body())
        res.append("</table>")
        return '\n'.join(res)

class ToolbarAction(WidgetBase):
    def __init__(self):
        super(ToolbarAction, self).__init__()

        self.widget = None
        self.value = False
        self.checkable = False
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.checkable:
            tf = self.get_state()
            self.make_callback('activated', tf)
        else:
            self.make_callback('activated')

    def set_state(self, tf):
        self.value = tf

    def get_state(self):
        return self.value

    def render(self):
        return self.widget.render()


class Toolbar(ContainerBase):
    def __init__(self, orientation='horizontal'):
        super(Toolbar, self).__init__()

        self.orientation = orientation
        self.widget = Box(orientation=orientation)

    def add_action(self, text, toggle=False, iconpath=None):
        child = ToolbarAction()
        self.text = text
        if iconpath:
            native_image = PgHelp.get_icon(iconpath, size=(24, 24),
                                           format='png')
            widget = Image(native_image=native_image)
            widget.resize(24, 24)
        else:
            widget = Button(text)
        child.checkable = toggle
        child.widget = widget
        self.widget.add_widget(child, stretch=0)
        return child

    def add_widget(self, child):
        self.add_ref(child)

    def add_menu(self, text, menu=None):
        if menu is None:
            menu = Menu()
        child = self.add_action(text)
        child.add_callback('activated', lambda w: menu.popup())
        return menu

    def add_separator(self):
        #self.widget.addSeparator()
        pass

    def render(self):
        return self.widget.render()

class MenuAction(WidgetBase):
    def __init__(self, text=None):
        super(MenuAction, self).__init__()

        self.widget = None
        self.text = text
        self.is_checkable = False
        self.value = False
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.is_checkable:
            self.make_callback('activated', self.value)
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

    def popup(self, widget=None):
        # TODO
        if widget is not None:
            w = widget.get_widget()

class Menubar(HBox):

    def __init__(self):
        super(Menubar, self).__init__()

        self.menus = Bunch.Bunch(caseless=True)

        self.set_border_width(2)
        self.set_spacing(8)

    def add_name(self, name):
        child = Menu()
        self.menus[name] = child
        menu_w = Label(text=name, halign='left', style='clickable',
                       menu=child)
        self.add_widget(menu_w)
        return child

    def get_menu(self, name):
        return self.menus[name]


class TopLevel(ContainerBase):
    def __init__(self, title=""):
        super(TopLevel, self).__init__()

        self.title = title
        self.widget = None
        # these are assigned by the Application()
        self.wid = None
        self.url = None
        self.app = None
        self.debug = False
        #widget.closeEvent = lambda event: self._quit(event)

        self.enable_callback('close')

    def set_widget(self, child):
        self.add_ref(child)

    def add_dialog(self, child):
        self.add_ref(child)

        app = self.get_app()
        app.do_operation('update_html', id=self.id,
                         value=self.render_children())

    def show(self):
        pass

    def hide(self):
        pass

    def close(self):
        self.make_callback('close')

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
        if self.debug:
            debug = 'true'
        else:
            debug = 'false'
        d = dict(title=self.title, content=self.render_children(),
                 wid=self.wid, id=self.id, url=url, ws_url=ws_url,
                 debug=debug)
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
        overflow: hidden; /* disable scrollbars */
        display: block; /* no floating content on sides */
      }
    </style>
    <meta name="viewport"
      content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no, target-densitydpi=device-dpi" />
</head>
<body>
    <script type="text/javascript" src="/js/hammer.js"></script>

    <!-- The next three lines are for the jQuery widgets (e.g., Dialog) -->
    <link rel="stylesheet" href="//code.jquery.com/ui/1.11.4/themes/smoothness/jquery-ui.css">
    <script src="//code.jquery.com/jquery-1.10.2.js"></script>
    <script src="//code.jquery.com/ui/1.11.4/jquery-ui.js"></script>
    <script type="text/javascript" src="/js/application.js"></script>
    <script type="text/javascript">
        var wid = "%(wid)s";
        var url = "%(url)s";
        var ws_url = "ws://" + window.location.host + "/app/socket?wid=%(wid)s";
        var ginga_app = ginga_make_application(ws_url, %(debug)s);
    </script>
<div id=%(id)s>%(content)s</div>
</body>
</html>''' % d


class Application(Callback.Callbacks):

    def __init__(self, logger=None, base_url=None,
                 host='localhost', port=9909):
        global _app, widget_dict
        super(Application, self).__init__()

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

        self.host = host
        self.port = port
        self.base_url = "http://%s:%d/app" % (self.host, self.port)

        # Get screen size
        # TODO: need to pass this from Web browser
        self.screen_wd = 1600
        self.screen_ht = 1200

        for name in ('shutdown', ):
            self.enable_callback(name)

    def get_screen_size(self):
        return (self.screen_wd, self.screen_ht)

    def process_events(self):
        pass

    def process_end(self):
        pass

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

    def make_window(self, title=None, wid=None):
        w = TopLevel(title=title)
        self.add_window(w, wid=wid)
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
                self.logger.error("Error doing operation '%s': %s" % (
                    operation, str(e)))
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
            #self.logger.debug("setting timer...")
            timer.timer = time.time() + time_sec

    def widget_event(self, event):
        if event.type == "timer":
            self.on_timer_event(event)
            return

        # get the widget associated with this id
        w_id = int(event.id)
        try:
            widget = widget_dict[w_id]
            # make the callback for this widget (activation or value-changed)
            widget._cb_redirect(event)

        except KeyError:
            self.logger.error("Event '%s' from unknown widget (id=%d)" % (
                str(event), w_id))

    def start(self, no_ioloop=False):

        import tornado.web
        import tornado.ioloop
        from ginga.web.pgw import PgHelp, js

        js_path = os.path.dirname(js.__file__)

        # create and run the app
        self.server = tornado.web.Application([
            #(r"/js/(.*\.js)", tornado.web.StaticFileHandler,
            (r"/js/(.*)", tornado.web.StaticFileHandler,
             {"path":  js_path}),
            (r"/js/jquery/(.*)", tornado.web.StaticFileHandler,
             {"path":  os.path.join(js_path, 'jquery')}),
            (r"/app", PgHelp.WindowHandler,
              dict(name='Application', url='/app', app=self)),
            (r"/app/socket", PgHelp.ApplicationHandler,
              dict(name='ApplicationSocketInterface', app=self)),
            ],
               app=self, logger=self.logger)

        self.server.listen(self.port, self.host)

        self.logger.info("ginga web now running at " + self.base_url)

        if no_ioloop:
            self.t_ioloop = None
        else:
            self.t_ioloop = tornado.ioloop.IOLoop.instance()
            self.t_ioloop.start()

    def stop(self):
        # how to stop tornado server?
        if not self.t_ioloop is None:
            self.t_ioloop.stop()

        self.ev_quit.set()

    def mainloop(self, no_ioloop=False):
        self.start(no_ioloop=no_ioloop)

class Dialog(WidgetBase):

    dialog_template = '''
    <div id="%(id)s">
    <script>
    ginga_initialize_dialog(document.getElementById("%(id)s"), "%(id)s", "%(title)s", %(buttons)s, %(modal)s, ginga_app)
    </script>
    %(content)s
    </div>
    '''

    def __init__(self, title='', flags=None, buttons=[],
                 parent=None, callback=None, modal=False):

        super(Dialog, self).__init__()

        if parent is None:
            raise ValueError("Top level 'parent' parameter required")

        self.title = title
        self.buttons = buttons
        self.value = None
        self.modal = modal
        self.content = VBox()
        self.enable_callback('close')
        if callback:
            self.enable_callback('activated')
            self.add_callback('activated', callback)

        self.parent = parent
        parent.add_dialog(self)

    def buttons_to_js_obj(self):
        d = dict(id=self.id)
        s = '{'
        for item in self.buttons:
            d['label'], d['val'] = item
            s += '''
            "%(label)s": function() {
            ginga_app.widget_handler("%(id)s", "%(val)s");
            },
            ''' % d
        s += '}'
        return s

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)

    def get_content_area(self):
        return self.content

    def show(self):
        app = self.get_app()
        app.do_operation('dialog_action', id=self.id, action="open")

    def raise_(self):
        # TODO
        pass

    def close(self):
        app = self.get_app()
        app.do_operation('dialog_action', id=self.id, action="close")

        self.make_callback('close')

    def render(self):
        d = dict(id=self.id, title=self.title, buttons=self.buttons_to_js_obj(), modal=str(self.modal).lower())
        d['content'] = self.content.render()
        return self.dialog_template % d

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
    numrows = len(captions)
    numcols = reduce(lambda acc, tup: max(acc, len(tup)), captions, 0)
    if (numcols % 2) != 0:
        raise ValueError("Column spec is not an even number")
    numcols = int(numcols // 2)

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
    if not fill:
        box2.add_widget(Label(''), stretch=1)
    if scrolled:
        sw = ScrollArea()
        sw.set_widget(box2)
    else:
        sw = box2

    return box1, sw, orientation

#END
