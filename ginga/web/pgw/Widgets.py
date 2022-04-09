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
import asyncio
from functools import reduce

from ginga.misc import Callback, Bunch, Settings, LineHistory
from ginga.web.pgw import PgHelp

# For future support of WebView widget
has_webkit = False

__all__ = ['WidgetError', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'Dial', 'Label', 'Button', 'ComboBox',
           'SpinBox', 'Slider', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'ProgressBar', 'StatusBar', 'TreeView',
           'Canvas', 'ContainerBase', 'Box', 'HBox', 'VBox', 'Frame',
           'Expander', 'TabWidget', 'StackWidget', 'MDIWidget', 'ScrollArea',
           'Splitter', 'GridBox', 'ToolbarAction', 'Toolbar', 'MenuAction',
           'Menu', 'Menubar', 'Page', 'TopLevel', 'Application', 'Dialog',
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
        self.margins = (0, 0, 0, 0)   # T, R, B, L
        self._rendered = False

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
        if self._rendered:
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

    def is_visible(self):
        return getattr(self, '_rendered', True)

    def get_font(self, font, size):
        if PgHelp.font_regex.match(font) is None:
            font = PgHelp.font_info('%s %d' % (font, size))
        else:
            font = PgHelp.font_info(font)
        return font

    def cfg_expand(self, horizontal='fixed', vertical='fixed'):
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
        if self._rendered:
            app = self.get_app()
            c_id = app.get_caller_id()
            app.callers[c_id] = future
            app.do_operation(method_name, id=self.id, caller_id=c_id, **kwargs)

    def render(self):
        text = "'%s' NOT YET IMPLEMENTED" % (str(self.__class__))
        d = dict(id=self.id, text=text)
        self._rendered = True
        return '''<div id=%(id)s>%(text)s</div>''' % d


# BASIC WIDGETS

class TextEntry(WidgetBase):

    html_template = '''
    <input id=%(id)s type="text" maxlength=%(size)d size=%(size)d name="%(id)s"
       class="%(classes)s" style="%(styles)s" %(disabled)s %(readonly)s
       onkeyup="ginga_app.widget_handler('activate', '%(id)s', document.getElementById('%(id)s').value)"
       value="%(text)s">
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_value', id=self.id, value=text)

    def set_editable(self, tf):
        self.editable = tf

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        self.font = font
        self.add_css_styles([('font-family', font.family),
                             ('font-size', font.point_size),
                             ('font-style', font.style),
                             ('font-weight', font.weight)])
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_ohtml', id=self.id, value=self.render())

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_ohtml', id=self.id, value=self.render())

    def render(self):
        # TODO: render font
        d = dict(id=self.id, text=self.text, disabled='', size=self.length,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'),
                 readonly='')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if not self.editable:
            d['readonly'] = 'readonly'
        self._rendered = True
        return self.html_template % d  # noqa


class TextEntrySet(WidgetBase):

    html_template = '''
        <span class="%(classes)s" style="%(styles)s">
        <input id=%(id)s type="text" size=%(size)d name="%(id)s" value="%(text)s"
           class="%(classes)s" style="%(styles)s" %(readonly)s maxlength=%(size)d %(disabled)s
           onkeydown="if(event.key == 'Enter') document.getElementById('%(id)s-button').click()"/>
        <input type="button" %(disabled)s id="%(id)s-button"
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_value', id=self.id, value=text)

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        self.font = font
        self.add_css_styles([('font-family', font.family),
                             ('font-size', font.point_size),
                             ('font-style', font.style),
                             ('font-weight', font.weight)])
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_ohtml', id=self.id, name=self.render())

    def set_editable(self, tf):
        self.editable = tf

    def set_length(self, numchars):
        # this is only supposed to set the visible length
        self.length = numchars

    def render(self):
        # TODO: render font, editable
        d = dict(id=self.id, text=self.text, disabled='', size=self.length,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'),
                 readonly='')
        if not self.editable:
            d['readonly'] = 'readonly'
        self._rendered = True
        return self.html_template % d  # noqa


class TextArea(WidgetBase):

    html_template = '''
        <textarea id=%(id)s name="%(id)s" %(readonly)s wrap="%(wrap)s"
           class="%(classes)s" style="%(styles)s" %(disabled)s
           %(editable)s onkeyup="ginga_app.widget_handler('activate', '%(id)s',
           document.getElementById('%(id)s').value)">%(text)s</textarea>
        <script type="text/javascript">
            $(document).ready(function(){
                // see python method set_wrap in this widget
                ginga_app.add_widget_custom_method('%(id)s', 'update_wrap',
                    function (elt, msg) {
                        (msg.value) ? document.getElementById('%(id)s').setAttribute('wrap', 'hard') :
                            document.getElementById('%(id)s').setAttribute('wrap', 'off');
                });
            });
        </script>
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

        if self._rendered:
            app = self.get_app()
            app.do_operation('update_value', id=self.id, value=self.text)

        if not autoscroll:
            return
        if self._rendered:
            app.do_operation('scroll_bottom', id=self.id)

    def get_text(self):
        return self.text

    def clear(self):
        self.text = ""
        if self._rendered:
            app = self.get_app()
            self.set_text("")
            app.do_operation('update_html', id=self.id, value=self.text)

    def set_text(self, text):
        self.text = text

        if self._rendered:
            app = self.get_app()
            app.do_operation('update_value', id=self.id, value=self.text)

    def set_limit(self, numlines):
        # for compatibility with the other supported widget sets
        pass

    def set_editable(self, tf):
        self.editable = tf

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        self.font = font
        self.add_css_styles([('font-family', font.family),
                             ('font-size', font.point_size),
                             ('font-style', font.style),
                             ('font-weight', font.weight)])
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_ohtml', id=self.id, value=self.render())

    def set_wrap(self, tf):
        self.wrap = tf
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_wrap', id=self.id, value=self.wrap)

    def render(self):
        # TODO: handle wrapping, render font
        d = dict(id=self.id, text=self.text, disabled='', editable='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'),
                 readonly='', wrap='off')
        if not self.enabled:
            d['disabled'] = 'disabled'
        if not self.editable:
            d['readonly'] = 'readonly'
        if self.wrap:
            d['wrap'] = 'hard'
        self._rendered = True
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_label', id=self.id, value=text)

    def set_font(self, font, size=10):
        if isinstance(font, str):
            font = self.get_font(font, size)
        self.font = font
        self.add_css_styles([('font-family', font.family),
                             ('font-size', font.point_size),
                             ('font-style', font.style),
                             ('font-weight', font.weight)])
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_ohtml', id=self.id, value=self.render())

    def set_color(self, fg=None, bg=None):
        if fg is not None:
            self.fgcolor = fg
            self.add_css_styles([('color', fg)])
        if bg is not None:
            self.bgcolor = bg
            self.add_css_styles([('background-color', bg)])

        if self._rendered:
            style = self.get_css_styles(fmt='str')
            app = self.get_app()
            app.do_operation('update_style', id=self.id, value=style)

    # ...FOR HALIGN...
    def set_halign(self, align=None):
        if align is not None:
            self.halign = align
            self.add_css_styles([('text-align', align)])
        if self._rendered:
            app = self.get_app()
            # Styles re-render after selecting a choice
            app.do_operation('update_ohtml', id=self.id, value=self.render())

    def render(self):
        # TODO: render alignment, style, menu, clickable
        d = dict(id=self.id, text=self.text,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        self._rendered = True
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

    def set_text(self, text):
        self.text = text
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_value', id=self.id, value=self.text)

    def get_text(self):
        return self.text

    def _cb_redirect(self, event):
        self.make_callback('activated')

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        self._rendered = True
        return self.html_template % d  # noqa


class ComboBox(WidgetBase):

    html_template = '''
    <select id=%(id)s %(disabled)s name="%(id)s" %(multiple)s
            class="%(classes)s" style="%(styles)s"
            onchange="ginga_app.widget_handler('activate', '%(id)s',
                   document.getElementById('%(id)s').value)">
    %(options)s
    </select>
    <script type="text/javascript">
        $(document).ready(function(){
            document.getElementById('%(id)s').addEventListener('wheel', function(e) {
                if (e.deltaY < 0) {
                    this.selectedIndex = Math.max(this.selectedIndex - 1, 0);
                }
                if (e.deltaY > 0) {
                    this.selectedIndex = Math.min(this.selectedIndex + 1, this.length - 1);
                }
                ginga_app.widget_handler('activate', '%(id)s',
                   document.getElementById('%(id)s').value);
            });
        });
    </script>
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
        if len(text) <= 0:
            return
        while index <= num_choices:
            if index >= num_choices:
                self.choices.append(text)
                if self._rendered:
                    app = self.get_app()
                    app.do_operation('update_html', id=self.id, value=self.render())
                return
            item_text = self.choices[index]
            if item_text > text:
                self.choices.insert(index, text)
                if self._rendered:
                    app = self.get_app()
                    app.do_operation('update_html', id=self.id, value=self.render())
                return
            index += 1

    def delete_alpha(self, text):
        if self.choices.count(text) != 0:
            self.choices.remove(text)
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_html', id=self.id, value=self.render())

    def get_alpha(self, idx):
        return self.choices[idx]

    def clear(self):
        self.choices = []
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_html', id=self.id, value=self.render())

    def set_text(self, text):
        index = self.choices.index(text)
        self.set_index(index)

    # to be deprecated someday
    show_text = set_text

    def get_text(self):
        idx = self.get_index()
        return self.choices[idx]

    def append_text(self, text):
        self.choices.append(text)

    def set_index(self, index):
        self.index = index
        if self._rendered:
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

        self._rendered = True
        return self.html_template % d


class SpinBox(WidgetBase):

    html_template = '''
    <input id=%(id)s value="%(value)s">
    <script type="text/javascript">
        $(document).ready(function(){
            $('#%(id)s').spinner({ step: %(step)s, disabled: %(disabled)s,
                                     max: %(max)s, min: %(min)s,
                                     numberFormat: "%(format)s", culture: "fr"
            });
            // Set value of spinner box
            ginga_app.add_widget_custom_method('%(id)s', 'set_spinval',
                function (elt, msg) {
                    $(elt).spinner( "value", msg.value );
            });
            // Set limits of spinner box
            ginga_app.add_widget_custom_method('%(id)s', 'set_limits',
                function (elt, msg) {
                    var current_val = $(elt).spinner( "value" );
                    // set max limit
                    if (current_val > msg.value[1]) {
                        $(elt).spinner( "value", msg.value[1] );
                    }
                    $(elt).spinner({ max: msg.value[1] });

                    // set min limit
                    if (current_val < msg.value[0]) {
                        $(elt).spinner( "value", msg.value[0] );
                    }
                    $(elt).spinner({ min: msg.value[0] });

                    // set increment value
                    $(elt).spinner( "option", "step", msg.value[2] );
            });
            // Sends value when spinner value changes to client side
            $('#%(id)s').on( "spin", function( event, ui ) {
                ginga_app.widget_handler('activate', '%(id)s', ui.value);
            });
            $('#%(id)s').on( "spinchange", function( event, ui ) {
                ginga_app.widget_handler('activate', '%(id)s', document.getElementById('%(id)s').value);
            });
        });
    </script>
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('set_spinval', id=self.id, value=self.value)

    def set_decimals(self, num):
        self.decimals = num

    def set_limits(self, minval, maxval, incr_value=1):
        self.minval = self.dtype(minval)
        self.maxval = self.dtype(maxval)
        self.incr = self.dtype(incr_value)
        limits = [self.minval, self.maxval, self.incr]
        if self._rendered:
            app = self.get_app()
            app.do_operation('set_limits', id=self.id, value=limits)

    def render(self):
        d = dict(id=self.id, value=str(self.dtype(self.value)),
                 step=str(self.dtype(self.incr)),
                 max=str(self.dtype(self.maxval)),
                 format='',
                 min=str(self.dtype(self.minval)), disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = "true"
        else:
            d['disabled'] = "false"
        if self.dtype == int:
            d['format'] = ''
        elif self.dtype == float:
            d['format'] = 'n3'
        self._rendered = True
        return self.html_template % d  # noqa


class Slider(WidgetBase):

    html_template = '''
    <div id="%(id)s" tracking="%(tracking)s" class="%(classes)s" style="%(styles)s"></div>
    <script type="text/javascript">
        $(document).ready(function(){
            $('#%(id)s').slider({ max: %(max)s, min: %(min)s, step: %(incr)s,
                                 orientation: "%(orient)s", disabled: %(disabled)s,
                                 value: %(value)s,
                                 change: function (event, ui) {
                                    ginga_app.widget_handler('activate', '%(id)s', ui.value);
                                 }
            });
            // see python method set_value in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'set_slideval',
                function (elt, msg) {
                    $(elt).slider( "option", "value", msg.value );
            });
            // see python method set_limits in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'set_limits',
                function (elt, msg) {
                    $(elt).slider( "option", "min", msg.value[0] );
                    $(elt).slider( "option", "max", msg.value[1] );
                    $(elt).slider( "option", "step", msg.value[2] );
            });
            ginga_app.add_widget_custom_method('%(id)s', 'set_slidemax',
                function (elt, msg) {
                    $(elt).slider( "option", "max", msg.value );
            });
            // Set tracking (NOT WORKING YET)
            ginga_app.add_widget_custom_method('%(id)s', 'toggle_track',
                function (elt, msg) {
                    document.getElementById('%(id)s').setAttribute('tracking', msg.value);
            });
            // Deal with tracking
            if (document.getElementById('%(id)s').getAttribute('tracking') == 'true') {
                $('#%(id)s').on( "slide", function( event, ui ) {
                    ginga_app.widget_handler('activate', '%(id)s', ui.value);
                });
            }
            else {
                $('#%(id)s').on( "slide", function( event, ui ) {
                    console.log("Do nothing");
                });
            }
        });
    </script>
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('set_slideval', id=self.id, value=self.value)

    def set_tracking(self, tf):
        self.track = tf
        # TODO: Toggle tracking on/off dynamically
        if self._rendered:
            app = self.get_app()
            app.do_operation('toggle_track', id=self.id, value=self.track)

    def set_limits(self, minval, maxval, incr_value=1):
        self.minval = self.dtype(minval)
        self.maxval = self.dtype(maxval)
        self.incr = incr_value
        limits = [self.minval, self.maxval, self.incr]
        if self._rendered:
            app = self.get_app()
            app.do_operation('set_limits', id=self.id, value=limits)

    def render(self):
        d = dict(id=self.id, value=str(self.dtype(self.value)),
                 incr=str(self.dtype(self.incr)),
                 max=str(self.dtype(self.maxval)),
                 min=str(self.dtype(self.minval)),
                 disabled='', orient='', tracking='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'vertical':
            # firefox
            d['orient'] = 'vertical'
        if not self.enabled:
            d['disabled'] = "true"
        else:
            d['disabled'] = "false"
        if self.track:
            d['tracking'] = "true"
        else:
            d['tracking'] = "false"
        self._rendered = True
        return self.html_template % d  # noqa


class Dial(WidgetBase):

    html_template = '''
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').jqxKnob({ value: %(value)d,
                                   min: %(min_val)d, max: %(max_val)d,
                                   step: %(inc_val)d,
                                   width: %(width)d, height: %(height)d,
                                   snapToStep: true,
                rotation: 'clockwise',
                style: { stroke: '#dfe3e9', strokeWidth: 3, fill: { color: '#fefefe', gradientType: "linear", gradientStops: [[0, 1], [50, 0.9], [100, 1]] } }
            });
            $('#%(id)s').on('valueChanged', function (event) {
                ginga_app.widget_handler('activate', '%(id)s',
                                         parseInt(event.currentValue));
            });
        });
    </script>
    '''

    def __init__(self, dtype=float, wrap=False, track=False):
        super(Dial, self).__init__()

        self.widget = None
        self.value = 0
        # this controls whether the callbacks are made *as the user
        # moves the dial* or afterwards
        self.tracking = track
        # this controls whether we can wrap around or not
        self.wrap = wrap

        self.dtype = dtype
        self.min_val = dtype(0)
        self.max_val = dtype(100)
        self.inc_val = dtype(1)

        self.enable_callback('value-changed')

    def _cb_redirect(self, val):
        self.value = val
        self.make_callback('value-changed', self.value)

    def get_value(self):
        return self.value

    def set_value(self, val):
        if val < self.min_val or val > self.max_val:
            raise ValueError("Value '{}' is out of range".format(val))
        self.value = val

    def set_tracking(self, tf):
        self.track = tf

    def set_limits(self, minval, maxval, incr_value=1):
        self.min_val = minval
        self.max_val = maxval
        self.inc_val = incr_value

    def render(self):
        d = dict(id=self.id, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'),
                 min_val=self.min_val, max_val=self.max_val,
                 inc_val=self.inc_val, value=self.value,
                 width=100, height=100)
        if not self.enabled:
            d['disabled'] = 'disabled'

        self._rendered = True
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
            // see python method set_value() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'set_scrollval',
                function (elt, msg) {
                    $(elt).jqxScrollBar({ value: msg.value });
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

    def set_value(self, value):
        self.value = int(round(value * 100.0))
        if self._rendered:
            app = self.get_app()
            app.do_operation('set_scrollval', id=self.id, value=self.value)

    def get_value(self):
        return self.widget.value() / 100.0

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value / 100.0)

    def render(self):
        d = dict(id=self.id, value=self.value, disabled='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if self.orientation == 'vertical':
            d['vert'] = 'true'
            d['width'], d['height'] = self.thickness, "'100%'"
        else:
            d['vert'] = 'false'
            d['width'], d['height'] = "'100%'", self.thickness

        self._rendered = True
        return self.html_template % d


class CheckBox(WidgetBase):

    html_template = '''
    <span class="%(classes)s" style="%(styles)s">
    <input id=%(id)s type="checkbox" %(disabled)s %(checked)s
        class="%(classes)s"
        onchange="ginga_app.widget_handler('activate', '%(id)s',
                    document.getElementById('%(id)s').checked)"
        value="%(text)s"><label for="%(id)s">%(text)s</label>
    </span>
    <script type="text/javascript">
        $(document).ready(function () {
            // see python method set_state in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'update_state',
                function (elt, msg) {
                    msg.value ? document.getElementById('%(id)s').checked = true :
                                document.getElementById('%(id)s').checked = false;
            });
        });
    </script>
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_state', id=self.id, value=self.value)

    def get_state(self):
        val = self.value
        return val

    def render(self):
        d = dict(id=self.id, text=self.text, disabled='', checked='',
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.value:
            d['checked'] = 'checked'
        self._rendered = True
        return self.html_template % d  # noqa


class ToggleButton(WidgetBase):

    html_template = '''
    <div>
        <label class="%(class1)s" style="%(styles)s">
            <input id=%(id)s type="checkbox" %(disabled)s value="%(text)s" %(checked)s
                 onchange="ginga_app.widget_handler('activate', '%(id)s',
                 document.getElementById('%(id)s').checked)">
            <span class="%(class2)s"></span>
        </label>
        <label for="%(id)s" style="%(styles)s">%(text)s</label>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            // see python method set_state in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'update_state',
                function (elt, msg) {
                    msg.value ? document.getElementById('%(id)s').checked = true :
                                document.getElementById('%(id)s').checked = false;
            });
        });
    </script>
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
        self.add_css_classes(['switch', 'slider round'])
        self.add_css_styles([('float', 'left')])

    def _cb_redirect(self, event):
        self.value = event.value
        self.make_callback('activated', self.value)

    def set_state(self, tf):
        self.value = tf
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_state', id=self.id, value=self.value)

    def get_state(self):
        return self.value

    def render(self):
        css_classes = self.get_css_classes(fmt='str').split(' ', 1)
        d = dict(id=self.id, text=self.text, disabled='', checked='',
                 class1=[k for k in css_classes if 'switch' in k][0],
                 class2=[k for k in css_classes if 'slider round' in k][0],
                 styles=self.get_css_styles(fmt='str'))
        if not self.enabled:
            d['disabled'] = 'disabled'
        if self.value:
            d['checked'] = 'checked'

        self._rendered = True
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

        self._rendered = True
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

        if self._rendered:
            app = self.get_app()
            app.do_operation('update_imgsrc', id=self.id, value=self.img_src)

    def load_file(self, img_path, format=None):
        if format is None:
            format = 'png'
        img = PgHelp.get_native_image(img_path, format=format)
        self._set_image(img)

    def render(self):
        # TODO: callback for click
        d = dict(id=self.id, src=self.img_src, tooltip=self.tooltip,
                 height=self.height, width=self.width,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        self._rendered = True
        return self.html_template % d


class ProgressBar(WidgetBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').jqxProgressBar({ value: %(value)d, disabled: %(disabled)s,
                                          showText: true,
                                          width: %(width)s, height: %(height)s,
                                          orientation: '%(orient)s' });
            // see python method set_index() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'set_progress',
                function (elt, msg) {
                    $(elt).jqxProgressBar('value', msg.value);
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

        if self._rendered:
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

        self._rendered = True
        return self.html_template % d


class StatusBar(Label):
    def __init__(self):
        super(StatusBar, self).__init__()

    def clear_message(self):
        self.set_text('')

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
        self.rowid = -1
        self.rows = []
        self.localData = []
        self.shadow = {}
        self.selectedRows = []

        if self._rendered:
            app = self.get_app()
            app.do_operation('clear', id=self.id)

    def clear_selection(self):
        self.selectedRows = []
        if self._rendered:
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
        if self._rendered:
            app = self.get_app()
            app.do_operation('select_row', id=self.id, index=item['rowid'], state=state)

    def highlight_path(self, path, onoff, font_color='green'):
        item = self._path_to_item(path)  # noqa
        # TODO - Is there be a way to do this with CSS?

    def scroll_to_path(self, path):
        item = self._path_to_item(path)
        if self._rendered:
            app = self.get_app()
            app.do_operation('scroll_to_path', id=self.id, index=item['rowid'])

    def scroll_to_end(self):
        # TODO
        pass

    def sort_on_column(self, i):
        colTitle, fieldName = self.columns[i]
        if self._rendered:
            app = self.get_app()
            app.do_operation('sort_on_column', id=self.id, dataField=fieldName, sortOrder='asc')

    def set_column_width(self, i, width):
        self.columnWidths[i] = width
        colTitle, fieldName = self.columns[i]
        if self._rendered:
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

    def get_column_widths(self):
        return list(self.columnWidths)

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
        self._rendered = True
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

    def _cb_redirect(self, event):
        pass

    def _draw(self, shape_type, **kwargs):
        shape = dict(kwargs, type=shape_type)
        # TODO: save shapes to be sent if canvas is not rendered?
        if self._rendered:
            app = self.get_app()
            app.do_operation("draw_canvas", id=self.id, shape=shape)

    def clear_rect(self, x, y, width, height):
        self._draw("clear", x=x, y=y, width=width, height=height)

    def draw_image(self, img_buf, x, y, width=None, height=None):

        img_src = PgHelp.get_image_src_from_buffer(img_buf)

        self._draw("image", x=x, y=y, src=img_src, width=width, height=height)

    def render(self):
        global tab_idx
        # canvas needs a tabindex to be able to focus it and register
        # for keyboard events
        tab_idx += 1

        d = dict(id=self.id, width=self.width, height=self.height,
                 tab_idx=tab_idx,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        self._rendered = True
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

        if self._rendered:
            app = self.get_app()
            app.do_operation('remove_child', id=child.id)

        self.make_callback('widget-removed', child)

    def remove_all(self):
        children = list(self.children)
        for child in children:
            self.remove(child)

    def get_children(self):
        return self.children

    def num_children(self):
        return len(self.children)

    def render(self):
        self._rendered = True
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
    <script> type="text/javascript">
        $(document).ready(function () {
            // see python method insert_widget() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'insert_child',
                function (elt, msg) {
                    let child = elt.children[msg.index];
                    let numChildren = elt.children.length;
                    // if widget needs to be inserted at the end
                    if (msg.index == numChildren) {
                        child = elt.children[msg.index-1];
                        child.insertAdjacentHTML('afterend', msg.value);
                    }
                    else {
                        child.insertAdjacentHTML('beforebegin', msg.value);
                    }
            });
        });
    </script>
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

    def insert_widget(self, idx, child, stretch=0.0):
        self.add_ref(child)
        flex = int(round(stretch))
        child.add_css_styles([('flex-grow', flex), ('flex-shrink', 1)])

        if self._rendered:
            app = self.get_app()
            app.do_operation('insert_child', id=self.id, value=child.render(), index=idx)
        self.make_callback('widget-added', child)

    def add_widget(self, child, stretch=0.0):
        self.add_ref(child)
        flex = int(round(stretch))
        # Consider whether we need to add the following:
        #   -webkit-flex-grow, -ms-flex-grow, -moz-flex-grow
        # and their "shrink" conterparts
        child.add_css_styles([('flex-grow', flex), ('flex-shrink', 1)])

        if self._rendered:
            app = self.get_app()
            app.do_operation('append_child', id=self.id, value=child.render())
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

        self._rendered = True
        return self.html_template % d


class HBox(Box):
    def __init__(self):
        super(HBox, self).__init__(orientation='horizontal')


class VBox(Box):
    def __init__(self):
        super(VBox, self).__init__(orientation='vertical')


class Frame(ContainerBase):

    html_template = '''
    <div id='%(id)s' class="%(parent)s" style="%(styles)s">
        <h6 class="%(child1)s">%(title)s</h6>
        <div class="%(child2)s">%(content)s</div>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            // see python method set_widget() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'update_widget',
                function (elt, msg) {
                    $(".%(child2)s").empty();
                    $(".%(child2)s").append(msg.value);
            });
            // see python method set_text() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'update_frametext',
                function (elt, msg) {
                    elt.querySelector(".%(child1)s").innerHTML = msg.value;
            });
        });
    </script>
    '''

    def __init__(self, title=None):
        super(Frame, self).__init__()

        self.widget = None
        self.label = title
        self.add_css_classes(['frame', 'frame-widget', 'frame-text'])

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_widget', id=self.id, value=child.render())

    def render(self):
        children = self.get_children()
        css_classes = self.get_css_classes(fmt='str').split()
        if len(children) == 0:
            content = ''
        else:
            content = children[0].render()
        d = dict(id=self.id, content=content, title=self.label,
                 parent=[k for k in css_classes if 'frame' in k][0],
                 child1=[k for k in css_classes if 'frame-text' in k][0],
                 child2=[k for k in css_classes if 'frame-widget' in k][0],
                 styles=self.get_css_styles(fmt='str'))

        self._rendered = True
        return self.html_template % d

    def set_text(self, text):
        self.label = text
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_frametext', id=self.id, value=self.label)


class Expander(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      <div> %(title)s </div>
      <div>
        %(content)s
      </div>
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
             $("#%(id)s").jqxExpander({ width: '%(width)s',
                                        expanded: false });
             // see python method set_widget() in this widget
             ginga_app.add_widget_custom_method('%(id)s', 'update_expander',
                function (elt, msg) {
                    $(elt).jqxExpander('setContent', msg.value);
             });
        });
    </script>
    """

    def __init__(self, title='', notoggle=False):
        super(Expander, self).__init__()
        if notoggle:
            raise NotImplementedError("notoggle=True not implemented "
                                      "for this backend")
        self.widget = None
        self.label = title

    def set_widget(self, child, stretch=1):
        self.remove_all()
        self.add_ref(child)
        if self._rendered:
            app = self.get_app()
            app.do_operation('update_expander', id=self.id, value=child.render())

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

        self._rendered = True
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
        if self._rendered:
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

        if self._rendered:
            app = self.get_app()  # noqa
            app.do_operation('append_child', id=self.id, value=child.render())
            # this is a hack--we really don't want to reload the page, but just
            # re-rendering the HTML does not seem to process the CSS right
            #app.do_operation('reload_page', id=self.id)
        self.make_callback('widget-added', child)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        self.index = idx

        if self._rendered:
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

        self._rendered = True
        return self.html_template % d


class StackWidget(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
        %(content)s
    </div>
    """

    def __init__(self):
        super(StackWidget, self).__init__()
        self.add_css_classes(['stackbox'])
        self.index = 0

    def add_widget(self, child, title=""):
        children = self.get_children()
        child.add_css_styles([('grid-column-start', '1'), ('grid-row-start', '1')])
        # if there are no children, set first added widget to be visible
        if len(children) == 0:
            self.index = 0
            self.add_ref(child)
            child.add_css_styles([('visibility', 'visible')])
        # hide all other children
        else:
            self.add_ref(child)
            child.add_css_styles([('visibility', 'hidden')])

        if self._rendered:
            app = self.get_app()
            app.do_operation("append_child", id=self.id, value=child.render())
        self.make_callback('widget-added', child)

    def get_index(self):
        return self.index

    def set_index(self, idx):
        child = self.get_children()
        child[idx].add_css_styles([('visibility', 'hidden')])

        if self._rendered:
            new_visible = child[idx]
            old_visible = child[self.index]
            old_visible.add_css_styles([('visibility', 'hidden')])
            new_visible.add_css_styles([('visibility', 'visible')])
            style1 = new_visible.get_css_styles(fmt='str')
            style2 = old_visible.get_css_styles(fmt='str')

            app = self.get_app()
            app.do_operation("update_style", id=new_visible.id, value=style1)
            app.do_operation("update_style", id=old_visible.id, value=style2)

        self.index = idx

    def index_of(self, child):
        try:
            return self.children.index(child)
        except ValueError:
            return -1

    def index_to_widget(self, idx):
        return self.children[idx]

    def render(self):
        children = self.get_children()
        d = dict(id=self.id,
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))
        d['content'] = self.render_children(spacing_side='bottom')
        self._rendered = True
        return self.html_template % d


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
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
      %(content)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $("#%(id)s").jqxPanel({ width: '%(width)s', height: '%(height)s' });
            // see python methods scroll_to_end and scroll_to_pct in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'scroll_vert',
                function (elt, msg) {
                    var end_height = $("#%(id)s").jqxPanel('getScrollHeight');
                    var current_hscroll = $("#%(id)s").jqxPanel('getHScrollPosition');
                    if (msg.value >= 0 && msg.value <= 100) {
                        $(elt).jqxPanel('scrollTo', current_hscroll, pct_to_position(end_height, msg.value));
                    }
                    else {
                        $(elt).jqxPanel('scrollTo', current_hscroll, end_height);
                    }
            });
            ginga_app.add_widget_custom_method('%(id)s', 'scroll_hori',
                function (elt, msg) {
                    var end_width = $("#%(id)s").jqxPanel('getScrollWidth');
                    var current_vscroll = $("#%(id)s").jqxPanel('getVScrollPosition');
                    if (msg.value >= 0 && msg.value <= 100) {
                        $(elt).jqxPanel('scrollTo', pct_to_position(end_width, msg.value), current_vscroll);
                    }
                    else {
                        $(elt).jqxPanel('scrollTo', end_width, current_vscroll);
                    }
            });
            // convert percentage to a position value
            function pct_to_position(position_total, pct) {
                return pct / 100 * position_total;
            }
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
        if self._rendered:
            app = self.get_app()
            if vertical:
                app.do_operation('scroll_vert', id=self.id)
            if horizontal:
                app.do_operation('scroll_hori', id=self.id)

    def scroll_to_pct(self, percent, vertical=True, horizontal=False):
        if self._rendered:
            app = self.get_app()
            if vertical:
                app.do_operation('scroll_vert', id=self.id, value=percent)
            if horizontal:
                app.do_operation('scroll_hori', id=self.id, value=percent)

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

        self._rendered = True
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
            ginga_app.add_widget_custom_method('%(id)s', 'add_splitter',
                function (elt) {
                    $('#%(id)s').jqxSplitter({ width: '100%%', height: '100%%',
                                       orientation: '%(orient)s',
                                       disabled: %(disabled)s,
                                       panels: %(sizes)s
                                        });
            });
        });
    </script>
    """

    def __init__(self, orientation='horizontal', thumb_px=8):
        super(Splitter, self).__init__()

        self.orientation = orientation
        self.widget = None
        self.thumb_px = thumb_px
        self.sizes = []

        self.enable_callback('activated')

    def add_widget(self, child):
        self.add_ref(child)
        self.make_callback('widget-added', child)

        if len(self.sizes) > 2:
            app = self.get_app()
            app.do_operation('add_splitter', id=self.id)

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

        self._rendered = True
        return self.html_template % d


class GridBox(ContainerBase):

    html_template = '''
    <table id=%(id)s class="%(classes)s" style="%(styles)s">
        %(content)s
    </table>
    <script type="text/javascript">
        // see python method insert_cell in this widget
        ginga_app.add_widget_custom_method('%(id)s', 'insert_cell',
                function (elt, msg) {
                    let table = document.getElementById("%(id)s");
                    let row = msg.value[0];
                    table.rows.item(row).insertCell(msg.value[1]);
        });
        // see python method insert_row in this widget
        ginga_app.add_widget_custom_method('%(id)s', 'insert_row',
                function (elt, msg) {
                    let index = msg.value[0];
                    let numColumns = msg.value[1];
                    let newRow = document.getElementById("%(id)s").insertRow(index);
                    for (let i = 0; i < numColumns; i++) {
                        newRow.insertCell(i);
                    }
        });
        // see python method append_row in this widget
        ginga_app.add_widget_custom_method('%(id)s', 'append_row',
                function (elt, msg) {
                    let numRows = msg.value[0];
                    let numColumns = msg.value[1];
                    let newRow = document.getElementById("%(id)s").insertRow(numRows);
                    for (let i = 0; i < numColumns; i++) {
                        newRow.insertCell(i);
                    }
        });
        // see python method delete_row in this widget
        ginga_app.add_widget_custom_method('%(id)s', 'delete_row',
                function (elt, msg) {
                    document.getElementById("%(id)s").deleteRow(msg.value);
        });
    </script>
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
        self.add_css_styles([('border-collapse', 'separate')])
        self.add_css_styles([('border-spacing', ' %dpx %dpx' % (self.col_spacing, self.row_spacing))])
        style = self.get_css_styles(fmt='str')
        if self._rendered:
            app = self.get_app()
            app.do_operation("update_style", id=self.id, value=style)

    def set_spacing(self, val):
        self.set_row_spacing(val)
        self.set_column_spacing(val)

    def set_column_spacing(self, val):
        self.col_spacing = val
        self.add_css_styles([('border-collapse', 'separate')])
        self.add_css_styles([('border-spacing', ' %dpx %dpx' % (self.col_spacing, self.row_spacing))])
        style = self.get_css_styles(fmt='str')
        if self._rendered:
            app = self.get_app()
            app.do_operation("update_style", id=self.id, value=style)

    def add_widget(self, child, row, col, stretch=0):
        self.add_ref(child)
        self.num_rows = max(self.num_rows, row + 1)
        self.num_cols = max(self.num_cols, col + 1)
        self.tbl[(row, col)] = child

        if self._rendered:
            app = self.get_app()
            app.do_operation('update_html', id=self.id,
                             value=self.render_body())
        self.make_callback('widget-added', child)

    def insert_cell(self, row, col):
        indices = [row, col]
        if self._rendered:
            app = self.get_app()
            app.do_operation("insert_cell", id=self.id, value=indices)

    def insert_row(self, index):
        indices = [index, self.num_cols]
        self.num_rows += 1

        # handle case where user inserts row at the end of the gridbox
        if index == self.num_rows - 1:
            for j in range(self.num_cols):
                self.tbl[(index, j)] = Box()
        else:
            # shift key/value pairs down to make the row empty at index
            for i in range(self.num_rows - 2, index - 1, -1):
                for j in range(self.num_cols):
                    self.tbl[(i + 1, j)] = self.tbl[(i, j)]
            # populate inserted row with empty Boxes for render_body()
            for j in range(self.num_cols):
                self.tbl[(index, j)] = Box()

        if self._rendered:
            app = self.get_app()
            app.do_operation("insert_row", id=self.id, value=indices)

    def append_row(self):
        indices = [self.num_rows, self.num_cols]
        if self._rendered:
            app = self.get_app()
            app.do_operation("append_row", id=self.id, value=indices)
        self.num_rows += 1
        # populate appended row with empty Boxes for render_body()
        for j in range(self.num_cols):
            self.tbl[(self.num_rows - 1, j)] = Box()

    def delete_row(self, index):

        if index < 0 or index >= self.num_rows:
            print("Index out of bounds")
            return

        if index == self.num_rows - 1:
            for j in range(self.num_cols):
                self.tbl.pop((self.num_rows - 1, j))
        else:
            # shift dict key, value pairs up
            for i in range(index + 1, self.num_rows):
                for j in range(self.num_cols):
                    self.tbl[(i - 1, j)] = self.tbl[(i, j)]
            # delete items in last row to maintain self.tbl
            for j in range(self.num_cols):
                self.tbl.pop((self.num_rows - 1, j))

        self.num_rows -= 1
        if self._rendered:
            app = self.get_app()
            app.do_operation("delete_row", id=self.id, value=index)

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

        self._rendered = True
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
        self._rendered = True
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
        self._rendered = True
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

        self._rendered = True
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
        if self._rendered:
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

        self._rendered = True
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

        self._rendered = True
        return self.html_template % d


class Page(ContainerBase):

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
        super(Page, self).__init__()

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

        if self._rendered:
            app = self.get_app()
            app.do_operation('append_child', id=self.id,
                             value=child.render())
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

        self._rendered = True
        return self.html_template % d  # noqa


class TopLevel(ContainerBase):

    html_template = """
    <div id='%(id)s' class="%(classes)s" style="%(styles)s">
        %(content)s
    </div>
    <script type="text/javascript">
        $(document).ready(function () {
            $('#%(id)s').dialog({
                autoOpen: true, modal: false,
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

            // see python method raise_() in this widget
            ginga_app.add_widget_custom_method('%(id)s', 'raise_dialog',
                function (elt, msg) {
                    $(elt).dialog('moveToTop');
            });

        });
    </script>
    """

    def __init__(self, title="", parent=None):

        super(TopLevel, self).__init__()

        ## if parent is None:
        ##     raise ValueError("Top level 'parent' parameter required")

        self.title = title
        self.parent = parent

        for name in ('open', 'close', 'resize'):
            self.enable_callback(name)

        self.set_margins(0, 0, 0, 0)
        #self.add_css_classes([])

        # NOTE: either use this or explicitly call add_dialog() on
        # TopLevel widget!
        ## if parent is not None:
        ##     parent.add_dialog(self)

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

    def set_widget(self, child):
        self.remove_all()
        self.add_ref(child)

    def show(self):
        if self._rendered:
            app = self.get_app()
            app.do_operation('show_dialog', id=self.id)

    def hide(self):
        if self._rendered:
            app = self.get_app()
            app.do_operation('hide_dialog', id=self.id)

    def raise_(self):
        if self._rendered:
            app = self.get_app()
            app.do_operation('raise_dialog', id=self.id)

    def lower(self):
        pass

    def focus(self):
        pass

    def move(self, x, y):
        pass

    def maximize(self):
        pass

    def unmaximize(self):
        pass

    def is_maximized(self):
        return False

    def fullscreen(self):
        pass

    def unfullscreen(self):
        pass

    def is_fullscreen(self):
        return False

    def iconify(self):
        pass

    def uniconify(self):
        pass

    def set_title(self, title):
        self.title = title

    def close(self):
        self.make_callback('close')

    def render_body(self):
        if len(self.children) == 0:
            return ""

        return self.children[0].render()

    def render(self):
        wd, ht = self.get_size()
        d = dict(id=self.id, title=self.title,
                 width=wd, height=ht,
                 content=self.render_body(),
                 classes=self.get_css_classes(fmt='str'),
                 styles=self.get_css_styles(fmt='str'))

        self._rendered = True
        return self.html_template % d


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
    <script type="text/javascript" src="/js/jqwidgets/jqxknob.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxprogressbar.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxmenu.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxtoolbar.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxdatatable.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxtreegrid.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxdraw.js"></script>
    <script type="text/javascript" src="/js/jqwidgets/jqxnumberinput.js"></script>
    ''',
    }

    def __init__(self, logger=None, base_url=None,
                 host='localhost', port=9909, settings=None):
        # NOTE: base_url parameter not used, but here for backward compatibility
        global _app, widget_dict
        super(Application, self).__init__()

        self.logger = logger
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings
        self.settings.add_defaults(host=host, port=port)

        self.base_url = self.settings.get('base_url', None)
        self.window_dict = {}
        self.wincnt = 0
        # list of web socket handlers connected to this application
        self.ws_handlers = []
        # default sections from script imports to insert in web pages
        # see Page widget, above
        self.script_imports = ['hammer', 'jquery']

        _app = self
        widget_dict[0] = self

        self._timer_lock = threading.RLock()
        self._timers = []
        self.t_ioloop = None

        self.host = self.settings.get('host', 'localhost')
        self.port = self.settings.get('port', 9909)
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
        if self.t_ioloop is None:
            raise Exception("No event loop was started for this thread")

        tasks = asyncio.all_tasks(self.t_ioloop)
        self.t_ioloop.run_until_complete(asyncio.gather(*tasks))

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
        w = Page(title=title)
        self.add_window(w, wid=wid)
        return w

    def get_caller_id(self):
        c_id, self.caller_id = self.caller_id, self.caller_id + 1
        return c_id

    def _cb_redirect(self, event):
        #self.logger.debug("application got an event (%s)" % (str(event)))
        pass

    def add_ws_handler(self, handler):
        with self._timer_lock:
            self.ws_handlers.append(handler)

    def do_operation(self, operation, **kwdargs):
        self.logger.debug('---- (%d) operation: %s' % (
            kwdargs.get('id', 0), operation))

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
        """internal event handler for timer events"""
        # self.logger.debug("timer update")
        with self._timer_lock:
            expired = [timer for timer in self._timers
                       if (timer.deadline is not None and
                           time.time() > timer.deadline)]

        for timer in expired:
            timer.expire()
            # self.logger.debug("update should have been called.")

    def add_timer(self, timer):
        """internal method for timer management; see Timer class in PgHelp"""
        with self._timer_lock:
            if timer not in self._timers:
                self._timers.append(timer)

    def remove_timer(self, timer):
        """internal method for timer management; see Timer class in PgHelp"""
        with self._timer_lock:
            if timer in self._timers:
                self._timers.remove(timer)

    def make_timer(self):
        return PgHelp.Timer(app=self)

    def widget_event(self, event):
        """internal method for event management"""
        if event.type == 'timer':
            self.on_timer_event(event)
            return

        # get the widget associated with this id
        w_id = event.id
        self.logger.debug('----(%s) event: %s' % (w_id, event))

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

        self.t_ioloop = None
        try:
            # NOTE: tornado now uses the asyncio event loop
            self.t_ioloop = asyncio.get_running_loop()

        except RuntimeError as ex:
            if no_ioloop:
                raise ex

            # TODO: really just want to check for this exception:
            #  "There is no current event loop in thread ..."
            self.t_ioloop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.t_ioloop)

        self.server.listen(self.port, self.host)

        self.logger.info("ginga web now running at " + self.base_url)

    def stop(self):
        # how to stop tornado server?
        if self.t_ioloop is not None:
            self.t_ioloop.stop()

        self.ev_quit.set()

    def mainloop(self, no_ioloop=False):
        self.start(no_ioloop=no_ioloop)

        if self.t_ioloop is None:
            raise Exception("No event loop was started for this thread")

        while not self.t_ioloop.is_closed():
            self.t_ioloop.run_forever()

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

        ## if parent is None:
        ##     raise ValueError("Top level 'parent' parameter required")

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

        # NOTE: either use this or explicitly call add_dialog() on
        # Page widget!
        ## if parent is not None:
        ##     parent.add_dialog(self)

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
        if self._rendered:
            app = self.get_app()
            app.do_operation('show_dialog', id=self.id)

    def hide(self):
        if self._rendered:
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

        self._rendered = True
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
