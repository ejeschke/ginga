#
# Widgets.py -- wrapped HTML widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os.path
import threading
import time
import json
from functools import reduce

from ginga.misc import Callback, Bunch, LineHistory
from ginga.web.pgw import PgHelp
from ginga.util import six
from ginga.util.six.moves import filter

# For future support of WebView widget
has_webkit = False

__all__ = ['WidgetError', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'Label', 'Button', 'ComboBox',
           'SpinBox', 'Slider', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'ProgressBar', 'StatusBar', 'TreeView',
           'Canvas', 'ContainerBase', 'Box', 'HBox', 'VBox', 'Frame',
           'Expander', 'TabWidget', 'StackWidget', 'MDIWidget', 'ScrollArea',
           'Splitter', 'GridBox', 'ToolbarAction', 'Toolbar', 'MenuAction',
           'Menu', 'Menubar', 'TopLevel', 'Application', 'Dialog',
           'name_mangle', 'make_widget', 'hadjust', 'build_info', 'wrap',
           'has_webkit']


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

default_font = PgHelp.font_info("Arial 8")


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
        self.margins = (0, 0, 0, 0)   # T, R, B, L,

    def get_url(self):
        app = self.get_app()
        return "%s?id=%d" % (app.base_url, self.id)

    def get_app(self):
        return _app

    def get_widget(self):
        return self.widget

    def set_tooltip(self, text):
        self.tooltip = text

    def get_enabled(self):
        return self.enabled

    def set_enabled(self, tf):
        self.enabled = tf
        app = self.get_app()
        app.do_operation('disable', id=self.id, value=not tf)

    def get_size(self):
        return self.width, self.height

    def get_pos(self):
        # TODO
        return 0, 0

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

    def get_font(self, font, size):
        if PgHelp.font_regex.match(font) is None:
            font = PgHelp.font_info('%s %d' % (font, size))
        else:
            font = PgHelp.font_info(font)
        return font

    def cfg_expand(self, horizontal=0, vertical=0):
        # this is for compatibility with Qt widgets
        pass

    def set_padding(self, top, right, bottom, left):
        padding = "%dpx %dpx %dpx %dpx" % (top, right, bottom, left)
        self.add_css_styles([('padding', padding)])

    def set_margins(self, top, right, bottom, left):
        self.margins = (top, right, bottom, left)
        margin = "%dpx %dpx %dpx %dpx" % self.margins
        self.add_css_styles([('margin', margin)])

    def set_border_width(self, pix):
        self.add_css_styles([('border-width', '%dpx' % pix)])

    def get_css_classes(self, fmt=None):
        classes = self.extdata.setdefault('css_classes', [])
        if fmt == 'str':
            classes = " ".join(classes)
        return classes

    def add_css_classes(self, new_classes):
        # add any new classes
        classes = self.get_css_classes()
        classes = classes + \
            list(filter(lambda t: t not in classes, new_classes))
        self.extdata.css_classes = classes

    def get_css_styles(self, fmt=None):
        styles = self.extdata.setdefault('inline_styles', [])
        if fmt == 'str':
            styles = ["%s: %s" % (x, y) for x, y in styles]
            styles = "; ".join(styles)
        return styles

    def add_css_styles(self, new_styles):
        # replace any styles that are overridden and add new styles
        styles = self.get_css_styles()
        od = dict(styles)
        nd = dict(new_styles)
        styles = [(a, b) if a not in nd else (a, nd[a])
                  for a, b in styles] + \
            list(filter(lambda t: t[0] not in od, new_styles))
        self.extdata.inline_styles = styles

    def call_custom_method(self, future, method_name, **kwargs):
        app = self.get_app()
        c_id = app.get_caller_id()
        app.callers[c_id] = future
        app.do_operation(method_name, id=self.id, caller_id=c_id, **kwargs)

    def render(self):
        text = "'%s' NOT YET IMPLEMENTED" % (str(self.__class__))
        d = dict(id=self.id, text=text)
        return '''<div id=%(id)s>%(text)s</div>''' % d


# BASIC WIDGETS

class TextEntry(WidgetBase):

    html_template = '''
    <input id=%(id)s type="text" size=%(size)d name="%(id)s"
       class="%(classes)s" style="%(styles)s" %(disabled)s
       onchange="ginga_app.widget_handler('activate', '%(id)s',
         document.getElementById('%(id)s').value)" value="%(text)s">
       '''

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

    def set_font(self, font, size=10):
        if isinstance(font, six.string_types):
            font = self.get_font(font, size)
        self.font = font

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        # TODO: render font
        d = dict(id=self.id, text=self.text, disabled='', size=self.length,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        return self.html_template % d  # noqa


class TextEntrySet(WidgetBase):

    html_template = '''
        <span class="%(classes)s" style="%(styles)s">
        <input id=%(id)s type="text" size=%(size)d name="%(id)s"
           class="%(classes)s" style="%(styles)s"
           %(disabled)s onchange="ginga_app.widget_handler('activate', '%(id)s',
              document.getElementById('%(id)s').value)" value="%(text)s"/>
        <input type="button" %(disabled)s
            class="%(classes)s" style="%(styles)s"
            onclick="ginga_app.widget_handler('activate', '%(id)s',
              document.getElementById('%(id)s').value)" value="Set"/>
        </span>
        '''

    def __init__(self, text='', editable=True):
        super(TextEntrySet, self).__init__()

        self.widget = None
        self.text = text
        self.font = default_font
        self.editable = editable
        # self.entry = None
        # self.btn = None
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

    def set_font(self, font, size=10):
        if isinstance(font, six.string_types):
            font = self.get_font(font, size)
        self.font = font

    def set_editable(self, tf):
        self.editable = tf

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        # TODO: render font, editable
        d = dict(id=self.id, text=self.text, disabled='', size=self.length,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        return self.html_template % d  # noqa


class TextArea(WidgetBase):

    html_template = '''
        <textarea id=%(id)s name="%(id)s"
           class="%(classes)s" style="%(styles)s" %(disabled)s
           %(editable)s onchange="ginga_app.widget_handler('activate', '%(id)s',
           document.getElementById('%(id)s').value)">%(text)s</textarea>
           '''

    def __init__(self, wrap=False, editable=False):
        super(TextArea, self).__init__()

        self.widget = None
        self.editable = editable
        self.wrap = wrap
        self.text = ''
        self.font = default_font

        # is this properly a css style?
        self.add_css_styles([('width', '100%')])

    def _cb_redirect(self, event):
        self.text = event.value
        # self.make_callback('activated')

    def append_text(self, text, autoscroll=True):
        # if text.endswith('\n'):
        #     text = text[:-1]
        self.text = self.text + text

        app = self.get_app()
        app.do_operation('update_value', id=self.id, value=self.text)

        if not autoscroll:
            return
        app.do_operation('scroll_bottom', id=self.id)

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

    def set_font(self, font, size=10):
        if isinstance(font, six.string_types):
            font = self.get_font(font, size)
        self.font = font

    def set_wrap(self, tf):
        self.wrap = tf

    def render(self):
        # TODO: handle wrapping, render font
        d = dict(id=self.id, text=self.text, disabled='', editable='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        if not self.editable:
            d['editable'] = 'readOnly'
        return self.html_template % d  # noqa


class Label(WidgetBase):

    html_template = '''
    <div id=%(id)s class="%(classes)s" style="%(styles)s">%(text)s</div>
    '''

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

    def set_font(self, font, size=10):
        if isinstance(font, six.string_types):
            font = self.get_font(font, size)
        self.font = font
        self.add_css_styles([('font-family', font.family),
                             ('font-size', font.point_size),
                             ('font-style', font.style),
                             ('font-weight', font.weight)])

    def set_color(self, fg=None, bg=None):
        if fg is not None:
            self.fgcolor = fg
            self.add_css_styles([('color', fg)])
        if bg is not None:
            self.bgcolor = bg
            self.add_css_styles([('background-color', bg)])

        style = self.get_css_styles(fmt='str')
        app = self.get_app()
        app.do_operation('update_style', id=self.id, value=style)

    def render(self):
        # TODO: render alignment, style, menu, clickable
        d = dict(id=self.id, text=self.text,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class Button(WidgetBase):

    html_template = '''
        <input id=%(id)s type="button"
            class="%(classes)s" style="%(styles)s" %(disabled)s
            onclick="ginga_app.widget_handler('activate', '%(id)s', 'clicked')"
            value="%(text)s">
            '''

    def __init__(self, text=''):
        super(Button, self).__init__()

        self.text = text
        self.widget = None

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.make_callback('activated')

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        return self.html_template % d  # noqa


class ComboBox(WidgetBase):

    html_template = '''
    <select id=%(id)s %(disabled)s name="%(id)s" %(multiple)s
            class="%(classes)s" style="%(styles)s"
            onchange="ginga_app.widget_handler('activate', '%(id)s',
                   document.getElementById('%(id)s').value)">
    %(options)s
    </select>
    '''

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
        d = dict(id=self.id, disabled='', multiple='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.multi_choice:
            d['multiple'] = 'multiple'
        if not self.enabled:
            d['disabled'] = 'disabled'
        res = []  # noqa
        for idx, choice in enumerate(self.choices):
            if idx == self.index:
                selected = 'selected'
            else:
                selected = ''
            res.append('''  <option value="%d" %s>%s</option>''' % (
                idx, selected, choice))
        d['options'] = '\n'.join(res)

        return self.html_template % d


class SpinBox(WidgetBase):

    html_template = '''
    <input id=%(id)s %(disabled)s type="number"
       class="%(classes)s" style="%(styles)s"
       onchange="ginga_app.widget_handler('activate', '%(id)s',
                     document.getElementById('%(id)s').value)"
       value="%(value)s" step="%(step)s" max="%(max)s" min="%(min)s">
       '''

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
        d = dict(id=self.id, value=str(self.dtype(self.value)),
                 step=str(self.dtype(self.incr)),
                 max=str(self.dtype(self.maxval)),
                 min=str(self.dtype(self.minval)), disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'

        return self.html_template % d  # noqa


class Slider(WidgetBase):

    html_template = '''
    <input id=%(id)s type="range" %(disabled)s
       class="%(classes)s" style="%(styles)s"
       onchange="ginga_app.widget_handler('activate', '%(id)s',
                       document.getElementById('%(id)s').value)"
       value="%(value)s" step="%(incr)s" max="%(max)s" min="%(min)s
       orient="%(orient)s">
    '''

    def __init__(self, orientation='horizontal', dtype=int, track=False):
        super(Slider, self).__init__()

        self.orientation = orientation
        self.track = track
        self.widget = None
        self.dtype = dtype
        self.value = dtype(0)
        self.minval = dtype(0)
        self.maxval = dtype(0)
        self.incr = dtype(0)

        if orientation == 'vertical':
            self.add_css_styles([('-webkit-appearance', 'slider-vertical')])

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
        d = dict(id=self.id, value=str(self.dtype(self.value)),
                 incr=str(self.dtype(self.incr)),
                 max=str(self.dtype(self.maxval)),
                 min=str(self.dtype(self.minval)),
                 disabled='', orient='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'vertical':
            # firefox
            d['orient'] = 'orient=vertical'
        if not self.enabled:
            d['disabled'] = 'disabled'

        return self.html_template % d  # noqa


class ScrollBar(WidgetBase):

    html_template = '''
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').jqxScrollBar({ value: %(value)d,
                                        min: 0, max: 100, step: 1,
                                        width: %(width)s, height: %(height)s,
                                        vertical: %(vert)s });
            $('#%(id)s').on('valueChanged', function (event) {
                ginga_app.widget_handler('activate', '%(id)s',
                                         parseInt(event.currentValue));
            });
        });
    </script>
    '''

    def __init__(self, orientation='horizontal'):
        super(ScrollBar, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.value = 0
        self.thickness = 15

        self.enable_callback('activated')

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)

    def render(self):
        d = dict(id=self.id, value=self.value, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'vertical':
            d['vert'] = 'false'
            d['width'], d['height'] = self.thickness, "'100%'"
        else:
            d['vert'] = 'true'
            d['width'], d['height'] = "'100%'", self.thickness

        return self.html_template % d


class CheckBox(WidgetBase):

    html_template = '''
    <span class="%(classes)s" style="%(styles)s">
    <input id=%(id)s type="checkbox" %(disabled)s
        class="%(classes)s"
        onchange="ginga_app.widget_handler('activate', '%(id)s',
                    document.getElementById('%(id)s').checked)"
        value="%(text)s"><label for="%(id)s">%(text)s</label>
    </span>
    '''

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
        d = dict(id=self.id, text=self.text, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'

        return self.html_template % d  # noqa


class ToggleButton(WidgetBase):

    html_template = '''
    <span class="%(classes)s" style="%(styles)s">
    <input id=%(id)s type="checkbox" %(disabled)s
         class="%(classes)s"
         onchange="ginga_app.widget_handler('activate', '%(id)s',
                        document.getElementById('%(id)s').checked)"
         value="%(text)s"><label for="%(id)s">%(text)s</label>
    </span>
    '''

    def __init__(self, text=''):
        super(ToggleButton, self).__init__()

        # self.widget = QtGui.QPushButton(text)
        # self.widget.setCheckable(True)
        # self.widget.clicked.connect(self._cb_redirect)
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
        d = dict(id=self.id, text=self.text, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'

        return self.html_template % d  # noqa


class RadioButton(WidgetBase):

    html_template = '''
    <span class="%(classes)s" style="%(styles)s">
    <input id=%(id)s name="%(group)s" type="radio"
         class="%(classes)s"
         %(disabled)s onchange="ginga_app.widget_handler('activate', '%(id)s',
                document.getElementById('%(id)s').value)" %(checked)s
         value="true">%(text)s
    </span>
    '''
    group_cnt = 0

    def __init__(self, text='', group=None):
        super(RadioButton, self).__init__()

        # self.widget = QtGui.QRadioButton(text)
        # self.widget.toggled.connect(self._cb_redirect)
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
                 group=self.group_name, text=self.text,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.value:
            d['checked'] = 'checked'

        return self.html_template % d  # noqa


class Image(WidgetBase):

    html_template = '''
    <img id=%(id)s src="%(src)s"  alt="%(tooltip)s"
         class="%(classes)s" style="%(styles)s">
    '''

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

    def load_file(self, img_path, format=None):
        img = PgHelp.get_native_image(img_path, format=format)
        self._set_image(img)

    def render(self):
        # TODO: callback for click
        d = dict(id=self.id, src=self.img_src, tooltip=self.tooltip,
                 height=self.height, width=self.width,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class ProgressBar(WidgetBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').jqxProgressBar({ value: %(value)d, disabled: %(disabled)s,
                                          width: %(width)s, height: %(height)s,
                                          orientation: '%(orient)s' });
            // see python method set_index() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'set_progress',
                function (elt, msg) {
                    $(elt).jqxProgressBar('val', msg.value);
            });
        });
    </script>
    """

    def __init__(self, orientation='horizontal'):
        super(ProgressBar, self).__init__()
        self.value = 0.0
        self.orientation = orientation
        self.widget = None
        self.thickness = 15

    def set_value(self, pct):
        self.value = pct
        # jqxProgressBar needs integer values in the range 0-100
        pct = int(self.value * 100.0)

        app = self.get_app()
        app.do_operation('set_progress', id=self.id, value=pct)

    def render(self):
        pct = int(self.value * 100.0)
        d = dict(id=self.id, value=pct, disabled='false',
                 orient=self.orientation,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'vertical':
            d['width'], d['height'] = self.thickness, "'100%'"
        else:
            d['width'], d['height'] = "'100%'", self.thickness

        return self.html_template % d


class StatusBar(Label):
    def __init__(self):
        super(StatusBar, self).__init__()

    def set_message(self, msg_str, duration=10.0):
        # TODO: remove message in about `duration` seconds
        self.set_text(msg_str)


class TreeView(WidgetBase):

    html_template = """
    <div id="%(id)s">
    </div>
    <script type="text/javascript">
        var source = %(source)s;
        var columns = %(columns)s;
        var dataAdapter = new $.jqx.dataAdapter(source);
        $(document).ready(function () {
            $("#%(id)s").jqxTreeGrid({
                                       altRows: %(use_alt_row_color)s,
                                       sortable: %(sortable)s,
                                       source: dataAdapter,
                                       width: %(width)s,
                                       columns: columns,
                                       columnsResize: true,
                                       selectionMode: "%(selectionMode)s"
                                       });
            // The rowSelect event tells us that a row has been selected.
            $("#%(id)s").on("rowSelect", function (event) {
                // Call the getSelection method to get the list of selected
                // rows so we can send the list back to the Python code.
                var rowsSelected = $("#%(id)s").jqxTreeGrid("getSelection");
                var payload = [];
                // Send only the list of rowid values back to the Python code
                for (var i = 0; i < rowsSelected.length; i++) {
                        payload[i] = rowsSelected[i]["rowid"];
                }
                ginga_app.widget_handler("row-select", "%(id)s", payload);
            });
            // The rowDoubleClick event tells us that a cell has been double-clicked on.
            $("#%(id)s").on("rowDoubleClick", function (event) {
                var payload = {rowid: event.args.row["rowid"], dataField: event.args.dataField}
                ginga_app.widget_handler("double-click", "%(id)s", payload);
            });
            // see python method clear() in this widget
            ginga_app.add_widget_custom_method("%(id)s","clear",
                function (elt, msg) {
                    $(elt).jqxTreeGrid("clear");
            });
            // see python method clear_selection() in this widget
            ginga_app.add_widget_custom_method("%(id)s","clear_selection",
                function (elt, msg) {
                    $(elt).jqxTreeGrid("clearSelection");
            });
            // see python method scroll_to_path() in this widget
            ginga_app.add_widget_custom_method("%(id)s","scroll_to_path",
                function (elt, msg) {
                    $(elt).jqxTreeGrid("ensureRowVisible", msg.index);
            });
            // see python method select_path() in this widget
            ginga_app.add_widget_custom_method("%(id)s","select_row",
                function (elt, msg) {
                    var method;
                    if (msg.state) {
                        method = "selectRow";
                    } else {
                        method = "unselectRow";
                    }
                    $(elt).jqxTreeGrid(method, msg.index);
            });
            // see python method sort_on_column() in this widget
            ginga_app.add_widget_custom_method("%(id)s","sort_on_column",
                function (elt, msg) {
                    $(elt).jqxTreeGrid("sortBy", msg.dataField, msg.sortOrder);
            });
            // see python method set_column_width() in this widget
            ginga_app.add_widget_custom_method("%(id)s","set_column_property",
                function (elt, msg) {
                    $(elt).jqxTreeGrid("setColumnProperty", msg.dataField, msg.property, msg.width);
            });
        });
    </script>
    """

    def __init__(self, auto_expand=False, sortable=False, selection='single',
                 use_alt_row_color=False, dragable=False):
        super(TreeView, self).__init__()

        self.auto_expand = auto_expand
        self.sortable = sortable

        self.jQWidgetsSelectionModes = dict(single='singleRow', multiple='multipleRows')
        self.selection = self.jQWidgetsSelectionModes[selection]

        self.use_alt_row_color = use_alt_row_color
        # TODO: "dragable" actions not yet implemented
        self.dragable = dragable
        self.levels = 1
        self.leaf_key = None
        self.leaf_idx = 0
        self.columns = []
        self.columnWidths = []
        self.datakeys = []
        # shadow index
        self.shadow = {}
        self.widget = None
        # self.localData will be populated in the manner required by
        # jqxTreeGrid.
        self.localData = []
        self.rowid = -1
        self.rows = []
        # We need to keep track of the row(s) that the user has
        # selected.
        self.selectedRows = []

        for cbname in ('selected', 'activated', 'drag-start'):
            self.enable_callback(cbname)

    def setup_table(self, columns, levels, leaf_key):
        self.clear()
        self.columns = columns
        self.levels = levels
        self.leaf_key = leaf_key
        for i in range(len(columns)):
            self.columnWidths.append(None)

    def set_tree(self, tree_dict):
        self.rowid = -1
        self.clear()
        self.localData = []
        self.add_tree(tree_dict)

    def add_tree(self, tree_dict):
        if self.sortable:
            keys = sorted(tree_dict)
        else:
            keys = tree_dict.keys()
        for key in keys:
            self._add_subtree(1, self.shadow, None, key, tree_dict[key])

    def _add_subtree(self, level, shadow, parent_item, key, node):
        def _addTopLevelItem(item):
            self.localData.append(item)

        def _addChild(parent_item, item):
            parent_item['children'].append(item)

        if level >= self.levels:
            # leaf node
            try:
                bnch = shadow[key]
                item = bnch.item
                # TODO: update leaf item
            except KeyError:
                # new item
                item = node
                self.rowid += 1
                item['rowid'] = self.rowid
                if level == 1:
                    item['parentRowNum'] = None
                    _addTopLevelItem(item)
                else:
                    item['parentRowNum'] = parent_item['rowid']
                    _addChild(parent_item, item)

                shadow[key] = Bunch.Bunch(node=node, item=item, terminal=True)
                self.rows.append(item)

        else:
            try:
                # node already exists
                bnch = shadow[key]
                item = bnch.item
                d = bnch.node

            except KeyError:
                # new node
                self.rowid += 1
                item = {self.leaf_key: str(key), 'expanded': self.auto_expand,
                        'rowid': self.rowid, 'children': []}
                if level == 1:
                    item['parentRowNum'] = None
                    _addTopLevelItem(item)
                else:
                    item['parentRowNum'] = parent_item['rowid']
                    _addChild(parent_item, item)

                d = {}
                shadow[key] = Bunch.Bunch(node=d, item=item, terminal=False)
                self.rows.append(item)

            # recurse for non-leaf interior node
            if self.sortable:
                keys = sorted(node)
            else:
                keys = node.keys()
            for key in keys:
                self._add_subtree(level + 1, d, item, key, node[key])

    def _selection_cb(self):
        res_dict = self.get_selected()
        self.make_callback('selected', res_dict)

    def _cb_redirect(self, event):
        res_dict = {}
        # We handle the following two event types:
        #   1. row-select
        #   2. double-click
        if event.type == 'row-select':
            self.selectedRows = event.value
            res_dict = self.get_selected()
            self.make_callback('selected', res_dict)
        elif event.type == 'double-click':
            self._get_item(res_dict, event.value['rowid'])
            self.make_callback('activated', res_dict)

    def _get_path(self, rowNum):
        if rowNum is None:
            return []

        row = self.rows[rowNum]
        try:
            childCount = len(row['children'])
        except KeyError:
            childCount = 0
        if childCount == 0:
            path_rest = self._get_path(row['parentRowNum'])
            myname = row[self.leaf_key]
            path_rest.append(myname)
            return path_rest

        colTitle0, fieldName0 = self.columns[0]
        myname = row[fieldName0]
        parentRowNum = row['parentRowNum']
        path_rest = self._get_path(parentRowNum)
        path_rest.append(myname)
        return path_rest

    def _get_item(self, res_dict, rowNum):
        path = self._get_path(rowNum)
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
        res_dict = {}
        for rowNum in self.selectedRows:
            try:
                children = self.rows[rowNum]['children']
                if len(children) > 0:
                    continue
            except KeyError:
                pass
            self._get_item(res_dict, rowNum)
        return res_dict

    def clear(self):
        app = self.get_app()
        app.do_operation('clear', id=self.id)
        self.rowid = -1
        self.rows = []
        self.localData = []
        self.shadow = {}
        self.selectedRows = []

    def clear_selection(self):
        self.selectedRows = []
        app = self.get_app()
        app.do_operation('clear_selection', id=self.id)

    def _path_to_item(self, path):
        s = self.shadow
        for name in path[:-1]:
            s = s[name].node
        item = s[path[-1]].item
        return item

    def select_path(self, path, state=True):
        item = self._path_to_item(path)
        if self.selectedRows.count(item) < 1:
            self.selectedRows.append(item)
        app = self.get_app()
        app.do_operation('select_row', id=self.id, index=item['rowid'], state=state)

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)  # noqa
        # TODO - Is there be a way to do this with CSS?

    def scroll_to_path(self, path):
        item = self._path_to_item(path)
        app = self.get_app()
        app.do_operation('scroll_to_path', id=self.id, index=item['rowid'])

    def sort_on_column(self, i):
        colTitle, fieldName = self.columns[i]
        app = self.get_app()
        app.do_operation('sort_on_column', id=self.id, dataField=fieldName, sortOrder='asc')

    def set_column_width(self, i, width):
        self.columnWidths[i] = width
        colTitle, fieldName = self.columns[i]
        app = self.get_app()
        app.do_operation('set_column_property', id=self.id, dataField=fieldName, property='width', width=width)

    def set_column_widths(self, lwidths):
        for i, width in enumerate(lwidths):
            if width is not None:
                self.set_column_width(i, width)

    def set_optimal_column_widths(self):
        # TODO - looks like jqxTreeGrid API doesn't have a way to
        # automatically re-size the column width to fit the contents
        for i in range(len(self.columns)):
            pass

    def columns_to_js(self):
        col_arr = []
        for i, colTuple in enumerate(self.columns):
            colTitle, fieldName = colTuple
            col_arr.append(dict(text=colTitle, dataField=fieldName))
            if self.columnWidths[i] is not None:
                col_arr[i]['width'] = self.columnWidths[i]
        columns_js = json.dumps(col_arr)
        return columns_js

    def source_obj_js(self):
        s = dict(dataType='json',
                 dataFields=[{'name': 'rowid', 'type': 'number'},
                             {'name': 'children', 'type': 'array'},
                             {'name': 'expanded', 'type': 'bool'}],
                 localData=self.localData,
                 hierarchy={'root': 'children'},
                 id='rowid',
                 sortColumn='rowid')
        for colTitle, fieldName in self.columns:
            s['dataFields'].append(dict(name=fieldName, type='string'))
        source_js = json.dumps(s)
        return source_js

    def render(self):
        self.columns_to_js()
        d = dict(id=self.id,
                 columns=self.columns_to_js(),
                 source=self.source_obj_js(),
                 use_alt_row_color=json.dumps(self.use_alt_row_color),
                 sortable=json.dumps(self.sortable),
                 width=self.width,
                 selectionMode=self.selection)
        return self.html_template % d


class Canvas(WidgetBase):

    canvas_template = '''
    <canvas id="%(id)s" tabindex="%(tab_idx)d"
       class="%(classes)s" style="%(styles)s"
       width="%(width)s" height="%(height)s"
       minWidth=1 minHeight=1>
       Your browser does not appear to support HTML5 canvas.</canvas>
    <script type="text/javascript">
        ginga_initialize_canvas(document.getElementById("%(id)s"), "%(id)s",
                                  ginga_app);
    </script>
'''  # noqa

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
                 tab_idx=tab_idx,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        return Canvas.canvas_template % d


# CONTAINERS

class ContainerBase(WidgetBase):
    def __init__(self):
        super(ContainerBase, self).__init__()
        # TODO: probably need to maintain children as list of widget ids
        self.children = []

        for name in ['widget-added', 'widget-removed']:
            self.enable_callback(name)

    def add_ref(self, ref):
        # TODO: should this be a weakref?
        self.children.append(ref)

    def remove(self, child, delete=False):
        if child not in self.children:
            raise KeyError("Widget is not a child of this container")
        self.children.remove(child)

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())
        self.make_callback('widget-removed', child)

    def remove_all(self):
        self.children[:] = []

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())

    def get_children(self):
        return self.children

    def num_children(self):
        return len(self.children)

    def render(self):
        return self.render_children()

    def render_children(self, ifx=' ', spacing=0, spacing_side='right'):
        # TODO: find a way to avoid overriding any padding specifically
        # set in the child
        if spacing_side == 'right':
            margins = (0, spacing, 0, 0)
        else:
            margins = (0, 0, spacing, 0)

        res = []
        children = self.get_children()
        for child in children:
            if child != children[-1]:
                child.set_margins(*margins)
            res.append(child.render())

        return ifx.join(res)


class Box(ContainerBase):

    html_template = '''
    <div id=%(id)s class="%(classes)s" style="%(styles)s">
      %(content)s
    </div>
    '''

    def __init__(self, orientation='horizontal'):
        super(Box, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.spacing = 0

        if self.orientation == 'horizontal':
            self.add_css_classes(['hbox'])
        else:
            self.add_css_classes(['vbox'])

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)
        flex = int(round(stretch))
        # Consider whether we need to add the following:
        #   -webkit-flex-grow, -ms-flex-grow, -moz-flex-grow
        # and their "shrink" conterparts
        child.add_css_styles([('flex-grow', flex), ('flex-shrink', 1)])

        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())
        self.make_callback('widget-added', child)

    def set_spacing(self, val):
        self.spacing = val

    def render(self):
        # TODO: handle spacing attribute
        d = dict(id=self.id,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'horizontal':
            d['content'] = self.render_children(spacing=self.spacing,
                                                spacing_side='right')
        else:
            d['content'] = self.render_children(spacing=self.spacing,
                                                spacing_side='bottom')

        return self.html_template % d


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')


class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')


class Frame(ContainerBase):

    html_template = '''
    <fieldset id=%(id)s class="%(classes)s" style="%(styles)s">
      %(legend)s
      %(content)s
    </fieldset>
    '''

    def __init__(self, title=None):
        super(Frame, self).__init__()

        self.widget = None
        self.label = title

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)

    def render(self):
        d = dict(id=self.id, content=self.render_children(),
                 legend='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.label is not None:
            d['legend'] = "<legend>%s</legend>" % self.label

        self.html_template % d


class Expander(ContainerBase):

    html_template = """
    <div id='%(id)s'  class="%(classes)s" style="%(styles)s">
      <div> %(title)s </div>
      <div>
        %(content)s
      </div>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
             $("#%(id)s").jqxExpander({ width: '%(width)s',
                                        expanded: false });
        });
    </script>
    """

    def __init__(self, title=''):
        super(Expander, self).__init__()

        self.widget = None
        self.label = title

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)

    def render(self):
        children = self.get_children()
        if len(children) == 0:
            content = ''
        else:
            content = children[0].render()
        d = dict(id=self.id, content=content, title=self.label,
                 width=500,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class TabWidget(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      %(tabs)s
      %(content)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').tabs({ active: '%(pos)s', heightStyle: 'fill' });
            $('#%(id)s').on('tabsactivate', function (event, ui) {
                ginga_app.widget_handler('activate', '%(id)s',
                                           event['owner']['selectedItem']);
            });

            // see python method set_index() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'select_tab',
                function (elt, msg) {
                    $(elt).tabs('option', 'active', msg.index);
            });
        });
    </script>
    """

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
        self.add_css_classes(['ui-tabs'])
        self._tabs_visible = True

        for name in ('page-switch', 'page-close', 'page-move', 'page-detach'):
            self.enable_callback(name)

    def _update(self):
        app = self.get_app()
        app.do_operation('update_html', id=self.id, value=self.render())

    def set_tab_position(self, tabpos):
        tabpos = tabpos.lower()
        if tabpos not in ('top', 'bottom'):
            raise ValueError("pg widgets doesn't support tabs position '%s'" % (
                tabpos))
        self.tabpos = tabpos

    def _cb_redirect(self, event):
        self.index = event.value
        child = self.index_to_widget(self.index)
        self.make_callback('page-switch', child)

    def add_widget(self, child, title=''):
        self.add_ref(child)
        self.titles.append(title)
        # attach title to child
        child.extdata.tab_title = title

        app = self.get_app()  # noqa
        # app.do_operation('update_html', id=self.id, value=self.render())
        # this is a hack--we really don't want to reload the page, but just
        # re-rendering the HTML does not seem to process the CSS right
        #app.do_operation('reload_page', id=self.id)
        self.make_callback('widget-added', child)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        self.index = idx

        app = self.get_app()
        app.do_operation('select_tab', id=self.id, index=self.index)

    def index_of(self, child):
        try:
            return self.children.index(child)
        except ValueError:
            return -1

    def index_to_widget(self, idx):
        """Returns child corresponding to `idx`"""
        return self.children[idx]

    def render(self):
        d = dict(id=self.id, pos=self.tabpos, tabs='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        if self._tabs_visible:
            # draw tabs
            res = ['''<ul class="ui-tabs-nav">\n''']
            for child in self.get_children():
                res.append('''<li> <a href="#%s-%s"> %s </a></li>\n''' % (
                    self.id, child.id, child.extdata.tab_title))
            res.append("</ul>\n")
            d['tabs'] = '\n'.join(res)

        res = ['''<div id="%s-%s"> %s </div>\n''' % (self.id, child.id,
                                                     child.render())
               for child in self.get_children()]
        d['content'] = '\n'.join(res)

        return self.html_template % d


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

    html_template = """
    <div id='%(id)s'  class="%(classes)s" style="%(styles)s">
      %(content)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
             $("#%(id)s").jqxPanel({ width: '%(width)s', height: '%(height)s' });
        });
    </script>
    """

    def __init__(self):
        super(ScrollArea, self).__init__()

        self.widget = None

        self.enable_callback('configure')

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)

    def scroll_to_end(self, vertical=True, horizontal=False):
        pass

    def render(self):
        children = self.get_children()
        if len(children) == 0:
            content = ''
        else:
            content = children[0].render()
        d = dict(id=self.id, content=content,
                 width='100%', height='100%',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class Splitter(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      %(panels)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').jqxSplitter({ width: '100%%', height: '100%%',
                                       orientation: '%(orient)s',
                                       disabled: %(disabled)s,
                                       panels: %(sizes)s
                                        });
            $('#%(id)s').on('resize', function (event) {
                 var sizes = [];
                 for (i = 0; i < event.args.panels.length; i++) {
                     var panel = event.args.panels[i];
                     sizes.push(panel.size);
                 }
                 ginga_app.widget_handler('activate', '%(id)s', sizes);
            });
        });
    </script>
    """

    def __init__(self, orientation='horizontal'):
        super(Splitter, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.sizes = []

        self.enable_callback('activated')

    def add_widget(self, child):
        self.add_ref(child)
        self.make_callback('widget-added', child)

    def get_sizes(self):
        return self.sizes

    def set_sizes(self, sizes):
        self.sizes = sizes

        # TODO:
        #self.call_custom_method('set_sizes', sizes=self.sizes)

    def _cb_redirect(self, event):
        self.set_sizes(event.value)

        self.make_callback('activated', self.sizes)

    def render(self):
        panels = ['''<div> %s </div>''' % (child.render())
                  for child in self.get_children()]
        sizes = ['''{ size: %d }''' % size
                 for size in self.sizes]
        disabled = str(not self.enabled).lower()
        if self.orientation == 'vertical':
            orient = 'horizontal'
        else:
            orient = 'vertical'
        d = dict(id=self.id, panels='\n'.join(panels), disabled=disabled,
                 sizes='[ %s ]' % ','.join(sizes), orient=orient,
                 width=500, height=500,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class GridBox(ContainerBase):

    html_template = '''
    <table id=%(id)s class="%(classes)s" style="%(styles)s">
    %(content)s
    </table>
    '''

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
        self.num_rows = max(self.num_rows, row + 1)
        self.num_cols = max(self.num_cols, col + 1)
        self.tbl[(row, col)] = child

        app = self.get_app()
        app.do_operation('update_html', id=self.id,
                         value=self.render_body())
        self.make_callback('widget-added', child)

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
        d = dict(id=self.id,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'),
                 content=self.render_body())

        return self.html_template % d


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

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        child = ToolbarAction()
        self.text = text
        if iconpath:
            wd, ht = 24, 24
            if iconsize is not None:
                wd, ht = iconsize
            native_image = PgHelp.get_icon(iconpath, size=(wd, ht),
                                           format='png')
            widget = Image(native_image=native_image)
            widget.resize(wd, ht)
        else:
            widget = Button(text)
        child.checkable = toggle
        child.widget = widget
        self.widget.add_widget(child, stretch=0)
        return child

    def add_widget(self, child):
        self.add_ref(child)
        self.make_callback('widget-added', child)

    def add_menu(self, text, menu=None, mtype='tool'):
        if menu is None:
            menu = Menu()
        child = self.add_action(text)
        child.widget.add_callback('activated', lambda w: menu.popup())
        return menu

    def add_separator(self):
        # self.widget.addSeparator()
        pass

    def render(self):
        return self.widget.render()


class MenuAction(WidgetBase):

    html_template = """%(item)s %(content)s"""

    def __init__(self, text=None, checkable=False):
        super(MenuAction, self).__init__()

        self.widget = None
        self.text = text
        self.checkable = checkable
        self.value = False
        self.enable_callback('activated')

    def _cb_redirect(self, *args):
        if self.checkable:
            self.make_callback('activated', self.value)
        else:
            self.make_callback('activated')

    def render(self):
        disabled = str(not self.enabled).lower()
        content = ''
        if self.widget is not None:
            content = self.widget.render()
        d = dict(id=self.id, item=self.text, disabled=disabled,
                 content=content,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class Menu(ContainerBase):

    # case 1: not a top-level menu
    html_template1 = """
    <ul id='%(id)s' class="%(classes)s" style="%(styles)s">
    %(content)s
    </ul>
    """

    # case 2: a top-level menu
    html_template2 = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      <ul>
      %(content)s
      </ul>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $("#%(id)s").jqxMenu({
                                   mode: 'popup', disabled: %(disabled)s });
            $('#%(id)s').on('itemclick', function (event) {
                // get the clicked LI element.
                var elt = event.args;
                var w_id = elt.getAttribute('data-menuitem-id');
                ginga_app.widget_handler('activate', w_id, 'clicked');
            });

            // see python method popup() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'popup_menu',
                function (elt, msg) {
                    var top = $(window).scrollTop();
                    var left = $(window).scrollLeft();
                    $(elt).jqxMenu('open', left + msg.x, top + msg.y);
            });
        });
    </script>
    """

    def __init__(self):
        super(Menu, self).__init__()

        # this ends up being a reference to the Pg menubar or toolbar
        self.widget = None
        self.menus = Bunch.Bunch(caseless=True)

    def add_widget(self, child):
        self.add_ref(child)
        self.make_callback('widget-added', child)

    def add_name(self, name, checkable=False):
        child = MenuAction(text=name, checkable=checkable)
        self.add_widget(child)
        return child

    def add_menu(self, name):
        child = Menu()
        self.menus[name] = child
        act_w = self.add_name(name)
        act_w.widget = child
        return child

    def get_menu(self, name):
        return self.menus[name]

    def add_separator(self):
        # TODO
        pass

    def _cb_redirect(self, event):
        # NOTE: this is called when they click only on the menu header
        pass

    def popup(self, widget=None):
        # TODO: handle offset from widget
        x, y = 0, 0
        app = self.get_app()
        app.do_operation('popup_menu', id=self.id, x=x, y=y)

    def render(self):
        content = ['''<li data-menuitem-id="%s"> %s </li>''' % (
                   child.id, child.render())
                   for child in self.get_children()]
        disabled = str(not self.enabled).lower()
        d = dict(id=self.id, content='\n'.join(content), disabled=disabled,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        if self.widget is not None:
            return self.html_template1 % d
        return self.html_template2 % d


class Menubar(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      <ul>
      %(content)s
      </ul>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $("#%(id)s").jqxMenu({ width: '%(width)s', height: '%(height)s',
                                   disabled: %(disabled)s });
            $('#%(id)s').on('itemclick', function (event) {
              // get the clicked LI element.
              var elt = event.args;
              var w_id = elt.getAttribute('data-menuitem-id');
              ginga_app.widget_handler('activate', w_id, 'clicked');
            });
        });
    </script>
    """

    def __init__(self):
        super(Menubar, self).__init__()

        self.menus = Bunch.Bunch(caseless=True)
        self.thickness = 28

    def add_widget(self, child, name):
        if not isinstance(child, Menu):
            raise ValueError("child widget needs to be a Menu object")
        child.extdata.text = name
        child.widget = self
        self.menus[name] = child
        self.add_ref(child)
        self.make_callback('widget-added', child)
        return child

    def add_name(self, name):
        child = Menu()
        return self.add_widget(child, name)

    def get_menu(self, name):
        return self.menus[name]

    def render(self):
        # each child should be a Menu
        content = ['''<li data-menuitem-id="%s"> %s %s </li>''' % (
            child.id, child.extdata.get('text', ''), child.render())
            for child in self.get_children()]
        disabled = str(not self.enabled).lower()
        d = dict(id=self.id, content='\n'.join(content), disabled=disabled,
                 width='100%', height=self.thickness,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d


class TopLevel(ContainerBase):

    html_template = '''
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
        overflow-x: hidden; /* disable horizontal scrollbar */
        display: block; /* no floating content on sides */
      }
    </style>
    <meta name="viewport"
      content="width=device-width, initial-scale=1.0, minimum-scale=1.0, maximum-scale=1.0, user-scalable=no, target-densitydpi=device-dpi" />
</head>
<body>
    %(script_imports)s

    <!-- For Ginga -->
    <link rel="stylesheet" href="/js/ginga_pg.css" type="text/css" />
    <script type="text/javascript" src="/js/ginga_pg.js"></script>
    <script type="text/javascript">
        var wid = "%(wid)s";
        var url = "%(url)s";
        var ws_url = "ws://" + window.location.host + "/app/socket?wid=%(wid)s";
        var ginga_app = ginga_make_application(ws_url, %(debug)s);
    </script>

<div id=%(id)s>%(content)s</div>
</body>
</html>
'''

    def __init__(self, title=""):
        super(TopLevel, self).__init__()

        self.title = title
        self.widget = None
        # these are assigned by the Application()
        self.wid = None
        self.url = None
        self.app = None
        self.debug = False
        self.script_imports = None
        # widget.closeEvent = lambda event: self._quit(event)

        self.enable_callback('close')

    def set_widget(self, child):
        self.add_ref(child)

    def add_dialog(self, child):
        self.add_ref(child)

        app = self.get_app()
        app.do_operation('update_html', id=self.id,
                         value=self.render_children())
        self.make_callback('widget-added', child)

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
        # self.widget.resize(width, height)
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

        # prepare javascript imports
        if self.script_imports is None:
            self.script_imports = self.app.script_imports
        script_imports = [self.app.script_decls[key]
                          for key in self.script_imports]

        d = dict(title=self.title, content=self.render_children(),
                 wid=self.wid, id=self.id, url=url, ws_url=ws_url,
                 debug=debug, script_imports='\n'.join(script_imports),
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d  # noqa


class Application(Callback.Callbacks):

    script_decls = {
        'hammer': '''
    <script type="text/javascript" src="/js/hammer.js"></script>
    ''',

        'jquery': '''
    <!-- jQuery foundation -->
    <link rel="stylesheet" href="//code.jquery.com/ui/1.12.1/themes/smoothness/jquery-ui.css">
    <script src="//code.jquery.com/jquery-1.12.4.js"></script>
    <script src="//code.jquery.com/ui/1.12.1/jquery-ui.js"></script>
    ''',

        'jqx': '''
    <!-- For jQWidgets -->
    <link rel="stylesheet" href="/js/jqwidgets/styles/jqx.base.css" type="text/css" />
    <script type="text/javascript" src="/js/jqwidgets/jqxcore.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxdata.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxbuttons.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxscrollbar.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxsplitter.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxtabs.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxpanel.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxexpander.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxprogressbar.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxmenu.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxtoolbar.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxdatatable.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxtreegrid.js"></script>
    ''',
    }

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
        # default sections from script imports to insert in web pages
        # see TopLevel widget, above
        self.script_imports = ['hammer', 'jquery']

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

        # for tracking remote ecmascript calls
        self.caller_id = 0
        self.callers = {}

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

    def get_caller_id(self):
        c_id, self.caller_id = self.caller_id, self.caller_id + 1
        return c_id

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
                    if handler in self.ws_handlers:
                        self.ws_handlers.remove(handler)

    def on_timer_event(self, event):
        # self.logger.debug("timer update")
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
            # self.logger.debug("update should have been called.")

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
            # self.logger.debug("setting timer...")
            timer.timer = time.time() + time_sec

    def widget_event(self, event):
        if event.type == 'timer':
            self.on_timer_event(event)
            return

        # get the widget associated with this id
        w_id = event.id

        if event.type == 'ecma_call_result':
            caller_id = event.value['caller_id']
            f = self.callers.get(caller_id, None)
            if f is not None:
                del self.callers[caller_id]
                f.resolve(event.value['caller_result'])
            return

        try:
            w_id = int(event.id)
            widget = widget_dict[w_id]
            # make the callback for this widget (activation or value-changed)
            widget._cb_redirect(event)

        except KeyError:
            self.logger.error("Event '%s' from unknown widget (id=%s)" % (
                str(event), w_id))

    def start(self, no_ioloop=False):

        import tornado.web
        import tornado.ioloop
        from ginga.web.pgw import PgHelp, js

        js_path = os.path.dirname(js.__file__)

        # create and run the app
        self.server = tornado.web.Application([
            # (r"/js/(.*\.js)", tornado.web.StaticFileHandler,
            (r"/js/(.*)", tornado.web.StaticFileHandler,
             {"path": js_path}),
            (r"/js/jquery/(.*)", tornado.web.StaticFileHandler,
             {"path": os.path.join(js_path, 'jquery')}),
            (r"/app", PgHelp.WindowHandler,
             dict(name='Application', url='/app', app=self)),
            (r"/app/socket", PgHelp.ApplicationHandler,
             dict(name='ApplicationSocketInterface', app=self)),
        ], app=self, logger=self.logger)

        self.server.listen(self.port, self.host)

        self.logger.info("ginga web now running at " + self.base_url)

        if no_ioloop:
            self.t_ioloop = None
        else:
            self.t_ioloop = tornado.ioloop.IOLoop.instance()
            self.t_ioloop.start()

    def stop(self):
        # how to stop tornado server?
        if self.t_ioloop is not None:
            self.t_ioloop.stop()

        self.ev_quit.set()

    def mainloop(self, no_ioloop=False):
        self.start(no_ioloop=no_ioloop)

    def quit(self):
        self.stop()


class Dialog(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
        %(content)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').dialog({
                autoOpen: false, modal: %(modal)s,
                autoResize: true,
                title: "%(title)s",
                closeOnEscape: false,
                position: { x: 50, y: 50},
                draggable: true, resizeable: true,
                minWidth: 'auto', minHeight: 'auto',
                width: 'auto', height: 'auto',
                maxWidth: '100%%', maxHeight: '100%%',
            });
            // otherwise we get scrollbars in the dialog
            $('#%(id)s').css('overflow', 'visible');

            $('#%(id)s').on('beforeClose', function (event) {
                ginga_app.widget_handler('dialog-close', '%(id)s', true);
            });

            var resize_timer;
            $('#%(id)s').on("dialogresize", function (event, ui) {
                event.preventDefault()
                clearTimeout(resize_timer);
                resize_timer = setTimeout(function () {
                var payload = { width: ui.size.width,
                                height: ui.size.height,
                                x: ui.position.left,
                                y: ui.position.top }
                ginga_app.resize_window();
                ginga_app.widget_handler('dialog-resize', '%(id)s', payload);
                }, 250);
            });

            // $('#%(id)s').on("dialogfocus", function (event, ui) {
            //     ginga_app.widget_handler('dialog-focus', '%(id)s', true);
            // });

            $('#%(id)s').on("dialogopen", function (event, ui) {
                ginga_app.resize_window();
                ginga_app.widget_handler('dialog-open', '%(id)s', true);
            });

            // see python method show() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'show_dialog',
                function (elt, msg) {
                    $(elt).dialog('open');
            });

            // see python method hide() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'hide_dialog',
                function (elt, msg) {
                    $(elt).dialog('close');
            });

        });
    </script>
    """

    def __init__(self, title='', flags=None, buttons=[],
                 parent=None, callback=None, modal=False):

        super(Dialog, self).__init__()

        if parent is None:
            raise ValueError("Top level 'parent' parameter required")

        self.title = title
        self.parent = parent
        self.buttons = buttons
        self.value = None
        self.modal = modal
        self.body = VBox()
        for name in ('activated', 'open', 'close', 'resize'):
            self.enable_callback(name)
        if callback:
            self.add_callback('activated', callback)

        if len(buttons) == 0:
            self.content = self.body
        else:
            self.content = VBox()
            self.body.add_widget(self.content, stretch=1)
            hbox = HBox()
            hbox.set_spacing(4)
            for name, val in buttons:
                btn = Button(name)
                btn.add_callback('activated', self._btn_choice, name, val)
                hbox.add_widget(btn)
            self.body.add_widget(hbox, stretch=0)

        self.set_margins(0, 0, 0, 0)
        #self.add_css_classes([])

        parent.add_dialog(self)

    def _cb_redirect(self, event):
        if event.type == 'dialog-resize':
            wd, ht = int(event.value['width']), int(event.value['height'])
            self.make_callback('resize', (wd, ht))

        elif event.type == 'dialog-open':
            # TODO: don't allow dialog to be closed
            self.make_callback('open')

        elif event.type == 'dialog-close':
            # TODO: don't allow dialog to be closed
            self.make_callback('close')

    def _btn_choice(self, btn_w, name, val):
        # user clicked one of the supplied buttons
        self.make_callback('activated', val)

    def get_content_area(self):
        return self.content

    def show(self):
        app = self.get_app()
        app.do_operation('show_dialog', id=self.id)

    def hide(self):
        app = self.get_app()
        app.do_operation('hide_dialog', id=self.id)

    def raise_(self):
        self.show()

    def close(self):
        self.make_callback('close')

    def render(self):
        wd, ht = self.get_size()
        d = dict(id=self.id, body_id=self.body.id, title=self.title,
                 width=wd, height=ht,
                 modal=str(self.modal).lower(),
                 content=self.body.render(),
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        return self.html_template % d

# class SaveDialog(QtGui.QFileDialog):
#     def __init__(self, title=None, selectedfilter=None):
#         super(SaveDialog, self).__init__()
#
#         self.selectedfilter = selectedfilter
#         self.widget = self.getSaveFileName(self, title, '', selectedfilter)
#
#     def get_path(self):
#         if self.widget and not self.widget.endswith(self.selectedfilter[1:]):
#             self.widget += self.selectedfilter[1:]
#         return self.widget


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
        # w.widget.setAlignment(QtCore.Qt.AlignRight)
    elif wtype == 'llabel':
        w = Label(title)
        # w.widget.setAlignment(QtCore.Qt.AlignLeft)
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
                title, wtype = tup[idx:idx + 2]
                if not title.endswith(':'):
                    name = name_mangle(title)
                else:
                    name = name_mangle('lbl_' + title[:-1])
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


# END
