#
# Widgets.py -- wrapped HTML widgets and convenience functions
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from functools import reduce
import os.path

in_situ_web = False
try:
    from pgwidgets_js.pyodide import Widgets as PGW
    from pgwidgets_js.pyodide.widget import Widget
    # <-- we are being imported from pyodide/pyscript
    in_situ_web = True
except ImportError:
    # <-- we are being imported from python
    from pgwidgets.sync import Widgets as PGW
    from pgwidgets.sync.widget import Widget
    from pgwidgets.sync.application import Application as PGW_Application
    from pgwidgets.extras.file_browser import FileBrowser

from ginga.misc.Callback import Callbacks
from ginga.misc import Bunch, Settings
from ginga.web.pgw import PgHelp
from ginga.util.paths import icondir, app_icon_path
from ginga.fonts import font_asst

__all__ = ['WidgetError', 'Widget', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'TextSource', 'Dial', 'Label', 'Button', 'ComboBox',
           'SpinBox', 'Slider', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'Canvas', 'ProgressBar', 'StatusBar',
           'TreeView', 'TableView', 'Box', 'HBox', 'VBox', 'ButtonBox',
           'FixedLayout', 'Frame', 'Expander', 'TabWidget', 'StackWidget',
           'MDIWidget', 'ScrollArea', 'Splitter', 'GridBox',
           'ToolbarAction', 'Toolbar', 'MenuAction', 'Menu', 'Menubar',
           'Page', 'TopLevel', 'Dialog', 'FileDialog', 'BrowserFileDialog',
           'ColorDialog', 'MessageDialog', 'Timer', 'Application',
           'name_mangle', 'make_widget', 'hadjust', 'build_info', 'wrap']


class WidgetError(Exception):
    """For errors thrown in this module."""
    pass


# reference to the created application
_app = None
# reference to the created session
_session_id = 1
_session = None


# BASE
class CallbackMixin(Callbacks):

    def __init__(self):
        Callbacks.__init__(self)

    def _enable_callback(self, name):
        if name not in self.cb:
            self.clear_callback(name)

    def _make_callback(self, name, *args, **kwargs):
        return Callbacks.make_callback(self, name, *args, **kwargs)

    def enable_callback(self, name):
        self._enable_callback(name)

    def has_callback(self, name):
        if name in self.cb:
            return True
        if not hasattr(self, '_defn') or self._defn is None:
            return False
        return name in self._defn.get("callbacks", [])

    def add_callback(self, name, cb_fn, *args, **kwargs):
        if Callbacks.has_callback(self, name):
            Callbacks.add_callback(self, name, cb_fn, *args, **kwargs)
        else:
            # ``Widget`` is the pgwidgets base class imported at module
            # top (sync or pyodide variant).  ``PGW`` is the *namespace*
            # of concrete widget classes and has no ``Widget`` attribute
            # in the in-situ/pyodide build, so use the imported class.
            Widget.add_callback(self, name, cb_fn, *args, **kwargs)


class WidgetMixin(CallbackMixin):

    def __init__(self):
        CallbackMixin.__init__(self)

        # for storing extra data that the user wants to associate
        # with a widget
        self.extdata = Bunch.Bunch()

    def get_app(self):
        return _app

    def get_widget(self):
        return self

    def get_size(self):
        res = super().get_size()
        if res is None:
            # pgwidgets can return None for the size of a widget
            # if it hasn't been realized
            return 10, 10
        return res

    def focus(self):
        # focus() => set_focus() in pgwidgets
        self.set_focus()

    def delete(self):
        # delete() => destroy() in pgwidgets
        self.destroy()

    def set_font(self, font_info, size=10):
        # The pgwidgets-js ``set_font`` is positional —
        # ``set_font(family, size, weight, style)`` setting the
        # corresponding CSS properties on the element.  Unpack the
        # Ginga-style font here so the JS side gets a CSS
        # family string rather than a dict object that stringifies
        # to "[object Object]" (which the browser then falls back
        # to its default serif font for).
        if isinstance(font_info, str):
            font_info = PgHelp.get_font(font_info, size)
        family = font_info.get('family', 'sans-serif')
        pts = font_info.get('size', size)
        weight = font_info.get('weight', 'normal')
        style = font_info.get('style', 'normal')
        super().set_font(family, pts, weight, style)

    def set_margins(self, l, r, t, b):
        # used interchangably with the idea of border width in Ginga
        # widgets
        self.set_padding([l, r, t, b])

    def set_border_width(self, px):
        self.set_padding(px)

    def cfg_expand(self, horizontal='fixed', vertical='fixed'):
        # this is for compatibility with Qt widgets
        pass


class ContainerWidgetMixin(WidgetMixin):

    def __init__(self):
        WidgetMixin.__init__(self)

        self._enable_callback('widget-removed')

    def remove(self, child, delete=False):
        super().remove(child, destroy=delete)
        self._make_callback('widget-removed', child)

    def remove_all(self, delete=False):
        super().remove_all(destroy=delete)


# for compatibility
class WidgetBase(WidgetMixin):
    pass


class ApplicationBase(Callbacks):
    """Base application class for Ginga-wrapped PG Widgets

    This is subclassed depending on whether we are running completely
    within the browser (Pyodide/PyScript) or externally using the web
    socket interface (pgwidgets-python).
    """
    def __init__(self, logger=None, host='localhost', port=9909, ws_port=None,
                 settings=None):
        global _app
        Callbacks.__init__(self)
        self.logger = logger

        # module-level assignments!
        self._windows = []
        _app = self

        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings

        for name in ['close', 'shutdown']:
            self.enable_callback(name)

    def get_screen_size(self):
        # subclass should override this
        return (1000, 1000)

    def get_url(self):
        # subclass should override this
        return None

    def is_web_backend(self):
        return True

    def make_window(self, title=None):
        win = TopLevel(title=title, moveable=True, resizable=True)
        self.add_window(win)
        return win

    def add_window(self, win):
        if win not in self._windows:
            self._windows.append(win)

    def make_timer(self):
        return Timer()

    def process_events(self, timeout=0.0):
        # In the browser (in-situ) there is nothing to pump: the JS event
        # loop dispatches widget events directly.  Provided so the GUI
        # event pump (GwMain.update_pending) can call it unconditionally.
        # The websocket Application overrides this with a real impl.
        pass

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

        super().close()

    def mainloop(self, timeout=None):
        self.start()
        self.run()


if in_situ_web:
    # <-- Pyodide/Pyscript

    class Application(ApplicationBase):
        """Application class when we are running *in-situ* in the browser."""

        def __init__(self, logger=None, host='localhost', port=9909,
                     ws_port=None, ws_sock=None, settings=None, token=None):
            ApplicationBase.__init__(self, logger=logger, host=host, port=port,
                                     ws_port=ws_port, settings=settings)

    def register_font(self, family, path, weight='normal', style='normal'):
        # no-op for now
        pass

    def set_default_font(self, family, size=None, weight=None, style=None):
        font_asst.add_alias('sans', family.lower())

    FileBrowser = PGW.FileDialog  # noqa

else:
    # <-- Running on a host and using the web socket interface

    class Application(PGW_Application, ApplicationBase):
        """Application class when only the GUI is in the browser."""

        def __init__(self, logger=None, host='localhost', port=9909,
                     http_server=None, ws_port=None, ws_sock=None,
                     max_sessions=1, token=None, settings=None):
            global _session
            ApplicationBase.__init__(self, logger=logger, host=host, port=port,
                                     ws_port=ws_port, settings=settings)
            if ws_port is None:
                ws_port = port + 1
            if http_server is None:
                http_server = self.settings.get('http_server', False)
            # NOTE: set unconditionally so get_url()/mainloop() work even
            # when ``http_server`` is passed explicitly (not via settings)
            self.use_http_server = http_server
            if token is None:
                token = self.settings.get('token', None)

            PGW_Application.__init__(self, ws_port=ws_port, ws_sock=ws_sock,
                                     http_port=port, host=host,
                                     http_server=http_server,
                                     max_sessions=max_sessions,
                                     concurrency_handling='serialized')

            # we create a default session that is used by the widgets
            self.default_session = self.create_session(session_id=_session_id,
                                                       token=token)
            _session = self.default_session

            if self.settings.get('load_bundled_fonts', False):
                # add bundled fonts
                for key in font_asst.get_loadable_fonts():
                    finfo = font_asst.get_font_info(key)
                    self.register_font(finfo.name, finfo.font_path,
                                       style=finfo.style, weight=finfo.weight)

        def get_screen_size(self):
            return self.default_session.get_screen_size()

        def get_url(self):
            if not self.use_http_server:
                return None
            base_url = f"http://{self._host}:{self._http_port}/?session={_session_id}&token={_session.token}"
            return base_url

        def mainloop(self, timeout=None):
            super().start()
            super().run()

        def start(self):
            super().start()

        def process_events(self, timeout=0.1):
            super().process_events(timeout=timeout)


# BASIC WIDGETS

def get_args(args):
    """Return the argument tuple appropriate for how we are running."""
    if args is None:
        return tuple([])
    if in_situ_web:
        return args
    # <--- we are running externally, so we need to prepend the default
    #       session
    if len(args) == 0:
        return (_session,)
    return (_session,) + args


class TextEntry(WidgetMixin, PGW.TextEntry):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.TextEntry.__init__(self, *get_args(args), **kwargs)

        # remapping pgwidgets 'activated' to ours
        self.on('activated', self._cb_redirect)
        self._enable_callback('activated')

    def _cb_redirect(self, value):
        # our 'activated' callback has a slightly different callback
        self._make_callback('activated')


class TextEntrySet(WidgetMixin, PGW.TextEntrySet):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.TextEntrySet.__init__(self, *get_args(args), **kwargs)

        # remapping pgwidgets 'activated' to ours
        self.on('activated', self._cb_redirect)
        self._enable_callback('activated')

    def _cb_redirect(self, value):
        # our 'activated' callback has a slightly different callback
        self._make_callback('activated')


class TextArea(WidgetMixin, PGW.TextArea):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.TextArea.__init__(self, *get_args(args), **kwargs)

    def append_text(self, text, autoscroll=True):
        # if text.endswith('\n'):
        #     text = text[:-1]
        super().append_text(text)
        if autoscroll:
            super().set_scroll_position(0.0, 1.0)


class TextSource(WidgetMixin, PGW.TextSource):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.TextSource.__init__(self, *get_args(args), **kwargs)


class Label(WidgetMixin, PGW.Label):
    def __init__(self, *args, style='normal', **kwargs):
        WidgetMixin.__init__(self)
        PGW.Label.__init__(self, *get_args(args), **kwargs)


class Button(WidgetMixin, PGW.Button):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.Button.__init__(self, *get_args(args), **kwargs)

    def set_icon(self, iconpath, iconsize=None):
        wd, ht = 24, 24
        if iconsize is not None:
            wd, ht = iconsize
        icon_uri = None
        if iconpath is not None:
            icon_uri = PgHelp.get_icon(iconpath, size=(wd, ht))
        super().set_icon(icon_uri, (wd, ht))


class ComboBox(WidgetMixin, PGW.ComboBox):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.ComboBox.__init__(self, *get_args(args), **kwargs)

        # remapping pgwidgets 'activated' to ours
        self.on('activated', self._cb_redirect)
        self._enable_callback('activated')

    def _cb_redirect(self, index, value):
        # our 'activated' callback only returns the index of the chosen thing
        self._make_callback('activated', index)


class SpinBox(WidgetMixin, PGW.SpinBox):
    def __init__(self, *args, dtype=int, **kwargs):
        WidgetMixin.__init__(self)
        _dtype = 'float' if dtype is float else 'int'
        PGW.SpinBox.__init__(self, *get_args(args), dtype=_dtype, **kwargs)

        # remapping 'activated' to 'value-changed'
        self.on('activated', self._cb_redirect)
        self._enable_callback('value-changed')

    def _cb_redirect(self, value):
        self._make_callback('value-changed', value)

    def set_limits(self, minval, maxval, incr_value=1):
        PGW.SpinBox.set_limits(self, minval, maxval, incr_value)


class Slider(WidgetMixin, PGW.Slider):
    def __init__(self, *args, dtype=int, **kwargs):
        WidgetMixin.__init__(self)
        _dtype = 'float' if dtype is float else 'int'
        PGW.Slider.__init__(self, *get_args(args), dtype=_dtype, **kwargs)

        # remapping 'activated' to 'value-changed'
        self.on('activated', self._cb_redirect)
        self._enable_callback('value-changed')

    def _cb_redirect(self, value):
        self._make_callback('value-changed', value)

    def set_limits(self, minval, maxval, incr_value=1):
        PGW.Slider.set_limits(self, minval, maxval, incr_value)


class Dial(WidgetMixin, PGW.Dial):
    def __init__(self, *args, dtype=int, **kwargs):
        WidgetMixin.__init__(self)
        _dtype = 'float' if dtype is float else 'int'
        PGW.Dial.__init__(self, *get_args(args), dtype=_dtype, **kwargs)

        # remapping 'activated' to 'value-changed'
        self.on('activated', self._cb_redirect)
        self._enable_callback('value-changed')

    def _cb_redirect(self, value):
        self._make_callback('value-changed', value)

    def set_limits(self, minval, maxval, incr_value=1):
        PGW.SpinBox.set_limits(self, minval, maxval, incr_value)

    def set_icon(self, iconpath, size=None):
        wd, ht = 24, 24
        if size is not None:
            wd, ht = size
        icon_uri = None
        if iconpath is not None:
            icon_uri = PgHelp.get_icon(iconpath, size=(wd, ht))
        super().set_icon(icon_uri, (wd, ht))


class ScrollBar(WidgetMixin, PGW.ScrollBar):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.ScrollBar.__init__(self, *get_args(args), **kwargs)

    def set_value(self, pct):
        self.set_scroll_percent(pct)

    def get_value(self):
        return self.get_scroll_percent()


class CheckBox(WidgetMixin, PGW.CheckBox):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.CheckBox.__init__(self, *get_args(args), **kwargs)


class ToggleButton(WidgetMixin, PGW.ToggleButton):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.ToggleButton.__init__(self, *get_args(args), **kwargs)


class RadioButton(WidgetMixin, PGW.RadioButton):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.RadioButton.__init__(self, *get_args(args), **kwargs)


class Image(WidgetMixin, PGW.Image):
    def __init__(self, *args, native_image=None, **kwargs):
        WidgetMixin.__init__(self)
        PGW.Image.__init__(self, *get_args(args), **kwargs)

        if native_image is not None:
            self.set_image(native_image)

    def load_file(self, path):
        data_uri = self.to_data_uri(path)
        self.set_image(data_uri)


class ProgressBar(WidgetMixin, PGW.ProgressBar):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.ProgressBar.__init__(self, *get_args(args), **kwargs)


class StatusBar(WidgetMixin, PGW.StatusBar):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.StatusBar.__init__(self, *get_args(args), **kwargs)

    def clear_message(self):
        super().clear()


# Recognised values for the ``widget`` field of a column
# descriptor — kept in sync with the same constant in the qtw /
# gtk3w / gtk4w wrappers.
_CELL_WIDGETS = ('checkbox', 'combobox', 'progress', 'button')


class TreeView(WidgetMixin, PGW.TreeView):
    def __init__(self, *args, auto_expand=False, sortable=False,
                 selection='single', use_alt_row_color=False,
                 dragable=False):
        WidgetMixin.__init__(self)

        PGW.TreeView.__init__(self, *get_args(args),
                              selection_mode=selection, sortable=sortable,
                              alternate_row_colors=use_alt_row_color)
        self.levels = 1
        self.datakeys = []

        # remapping 'collapsed'
        self.on('collapsed', self._cb_redirect_collapsed)
        self._enable_callback('collapsed')
        self.on('expanded', self._cb_redirect_expanded)
        self._enable_callback('expanded')
        self.on('selected', self._cb_redirect_selected)
        self._enable_callback('selected')
        self.on('activated', self._cb_redirect_activated)
        self._enable_callback('activated')

    def _cb_redirect_collapsed(self, node_vals, path):
        self._make_callback('collapsed', path)

    def _cb_redirect_expanded(self, node_vals, path):
        self._make_callback('expanded', path)

    def _cb_redirect_selected(self, sel_lst):
        subtree = super().get_subtree(status='selected')
        self._make_callback('selected', subtree)

    def _cb_redirect_activated(self, node_vals, path, col_key=None):
        # pgwidgets-js sends ``col_key`` as a 3rd arg on newer
        # builds; older builds send only two.  TreeView's
        # public ``activated`` signature stays ``(widget, subtree)``,
        # so col_key is accepted but not surfaced here.
        subtree = super().get_subtree(status=path)
        self._make_callback('activated', subtree)

    def setup_table(self, columns, levels, leaf_key):
        self.levels = levels

        # create the column headers
        col_defs = []
        # columns specifies a mapping
        for col in columns:
            col_def = dict(label=col[0], key=col[1])
            if len(col) > 2:
                col_def['type'] = 'string' if col[2] == 'str' else col[2]
            else:
                col_def['type'] = 'icon' if col[0] == 'icon' else 'string'
            col_defs.append(col_def)
        self.datakeys = [col_def['key'] for col_def in col_defs]
        self.leaf_key = leaf_key

        try:
            super().set_columns(col_defs)
        except Exception as e:
            self.logger.error(f"error setting columns: {e}")

    def set_tree(self, tree_dict):
        super().set_tree(tree_dict)

    def add_tree(self, tree_dict, expand_new=False):
        super().add_tree(tree_dict)

    def update_tree(self, tree_dict, expand_new=False):
        super().update_tree(tree_dict)

    def expand_all(self, tf):
        if tf:
            super().expand_all()
        else:
            super().collapse_all()

    def highlight_path(self, path, onoff, font_color='green'):
        # TODO?
        super().select_path(path, onoff)

    def get_children(self, status='expanded'):
        return super().get_subtree(status=status)

    def get_expanded(self):
        return super().get_subtree(status='expanded')

    def get_collapsed(self):
        return super().get_subtree(status='collapsed')

    def get_selected(self):
        return super().get_subtree(status='selected')

    def get_selected_paths(self):
        return super().get_selected()


class TableView(WidgetMixin, PGW.TableView):
    """Flat tabular view, API-compatible with the qtw TableView.

    Thin wrapper over :class:`pgwidgets.PGW.TableView` (which is in
    turn a flat-display subclass of the underlying TreeView) that
    normalises the constructor signature and callback shapes so a
    single piece of caller code works under either pgw or qtw.

    Constructor signature, callbacks, and method names mirror
    ``ginga.qtw.Widgets.TableView`` — see that class's docstring
    for the full API.  Callback signatures emitted here:

    * ``activated(table, row_dict, path, col_key)``
    * ``selected(table, list_of_row_dicts)``
    * ``sorted(table, col_key, ascending)``
    * ``cell_edited(table, path, col_key, old_value, new_value)``
    * ``scrolled(table, h_pct, v_pct)``

    ``path`` is ``[row_index]`` (a length-1 list) for a flat
    table, matching the qtw side.  ``col_key`` on ``activated``
    reflects the clicked cell's column key on a row dblclick, or
    ``None`` when activation came from the Enter key (no specific
    column) — matching qtw/gtk behaviour.
    """

    def __init__(self, *args, columns=None, show_header=True,
                 selection_mode='single', alternate_row_colors=False,
                 show_grid=False, show_row_numbers=False,
                 sortable=False, allow_text_selection=False,
                 dragable=False):
        WidgetMixin.__init__(self)

        # Build the underlying PGW.TableView with the options it
        # understands.  ``dragable`` has no equivalent on the pgw
        # side today; accepted for signature parity and ignored.
        pgw_kwargs = dict(
            show_header=show_header,
            selection_mode=selection_mode,
            alternate_row_colors=alternate_row_colors,
            show_grid=show_grid,
            show_row_numbers=show_row_numbers,
            sortable=sortable,
            allow_text_selection=allow_text_selection,
        )
        if columns is not None:
            pgw_kwargs['columns'] = self._normalise_columns(columns)
        PGW.TableView.__init__(self, *get_args(args), **pgw_kwargs)

        # Stash for callback redirects (path → row_dict lookup).
        self._user_columns = list(pgw_kwargs.get('columns', []) or [])
        # Shadow copy of row data so get_rows / get_row can answer
        # without a round-trip to the JS side (mirrors what the qtw
        # wrapper does by reading from QTreeWidget items).  Kept in
        # sync by the data-mutating method overrides below.
        self._rows = []
        # Parallel mirror of the JS-side row keys, in visible order.
        # After ``set_rows`` these are ``['row0', 'row1', ...]``;
        # ``insert_row`` / ``delete_row`` keep them in lockstep with
        # JS's auto-keying algorithm so ``_to_pgw_path`` /
        # ``_from_pgw_path`` can translate between integer visible
        # positions and JS row keys after arbitrary mutations.
        self._row_keys = []

        # Wire callback redirects so a single handler signature
        # works regardless of widget set.
        self.on('selected', self._cb_redirect_selected)
        self._enable_callback('selected')
        self.on('activated', self._cb_redirect_activated)
        self._enable_callback('activated')
        self.on('sorted', self._cb_redirect_sorted)
        self._enable_callback('sorted')
        self.on('cell_edited', self._cb_redirect_cell_edited)
        self._enable_callback('cell_edited')
        self.on('scrolled', self._cb_redirect_scrolled)
        self._enable_callback('scrolled')
        # Cell-selection + clipboard callbacks (cell modes).
        self.on('cell_selected', self._cb_redirect_cell_selected)
        self._enable_callback('cell_selected')
        # Action-shaped widget cells (currently: button) fire
        # cell_action(table, row_dict, col_key) on click.
        self.on('cell_action', self._cb_redirect_cell_action)
        self._enable_callback('cell_action')
        for name in ('copy', 'cut', 'paste'):
            self.on(name, self._cb_redirect_clipboard, name)
            self._enable_callback(name)

    # ----- column descriptor normalisation -------------------

    @staticmethod
    def _normalise_columns(columns):
        """Accept dicts, tuples, or strings (same forms as the qtw
        wrapper) and return a list of dicts the underlying
        pgwidgets-js TableView understands.

        Optional dict keys: ``halign``, ``editable``, ``widget``
        (one of ``_CELL_WIDGETS`` or None) and widget-specific
        extras: ``choices``, ``min``, ``max``, ``text``.
        """
        out = []
        for i, col in enumerate(columns):
            if isinstance(col, dict):
                key = col.get('key') or col.get('label') or f'col{i}'
                widget = col.get('widget')
                if widget is not None and widget not in _CELL_WIDGETS:
                    raise ValueError(
                        f"unknown column widget {widget!r} "
                        f"(expected one of {_CELL_WIDGETS})")
                d = {
                    'label': col.get('label', key),
                    'key': key,
                    'type': col.get('type', 'string'),
                }
                if 'halign' in col:
                    d['halign'] = col['halign']
                if 'editable' in col:
                    d['editable'] = bool(col['editable'])
                if 'colwidth' in col:
                    d['colwidth'] = col['colwidth']
                if widget is not None:
                    d['widget'] = widget
                    if 'choices' in col:
                        d['choices'] = list(col['choices'])
                    for opt in ('min', 'max', 'text',
                                'enabled_key', 'visible_key'):
                        if opt in col:
                            d[opt] = col[opt]
            elif isinstance(col, (tuple, list)):
                label = col[0]
                key = col[1] if len(col) > 1 else label
                dtype = col[2] if len(col) > 2 else 'string'
                d = {'label': label, 'key': key, 'type': dtype}
            elif isinstance(col, str):
                d = {'label': col, 'key': col, 'type': 'string'}
            else:
                raise ValueError(
                    f"unrecognised column descriptor: {col!r}")
            out.append(d)
        return out

    # ----- column / row API (delegated, with normalisation) --

    def set_columns(self, columns):
        norm = self._normalise_columns(columns)
        self._user_columns = norm
        super().set_columns(norm)

    def append_column(self, column):
        norm, = self._normalise_columns([column])
        self._user_columns.append(norm)
        super().append_column(norm)

    def insert_column(self, idx, column):
        norm, = self._normalise_columns([column])
        self._user_columns.insert(idx, norm)
        super().insert_column(idx, norm)

    def delete_column(self, idx):
        if 0 <= idx < len(self._user_columns):
            del self._user_columns[idx]
        super().delete_column(idx)

    # ----- row data (mutators shadow _rows for get_rows) -----

    def _col_keys(self):
        return [c['key'] for c in self._user_columns]

    def _normalise_row(self, row):
        if isinstance(row, dict):
            return dict(row)
        if isinstance(row, (list, tuple)):
            return dict(zip(self._col_keys(), row))
        raise ValueError(
            f"row must be a dict or sequence, got {type(row).__name__}")

    def _next_row_key(self):
        """Compute the next free ``rowN`` key, matching JS's
        auto-keying algorithm: start at the current row count and
        walk forward past any collisions.  Must be called *before*
        appending the new row to ``_row_keys``."""
        used = set(self._row_keys)
        i = len(self._row_keys)
        while f'row{i}' in used:
            i += 1
        return f'row{i}'

    def set_rows(self, rows):
        self._rows = [self._normalise_row(r) for r in rows]
        self._row_keys = [f'row{i}' for i in range(len(self._rows))]
        super().set_rows(rows)

    def set_data(self, data):
        self._rows = [self._normalise_row(r) for r in data]
        self._row_keys = [f'row{i}' for i in range(len(self._rows))]
        super().set_data(data)

    def append_row(self, row):
        key = self._next_row_key()
        self._rows.append(self._normalise_row(row))
        self._row_keys.append(key)
        super().append_row(row)

    def insert_row(self, idx, row):
        key = self._next_row_key()
        self._rows.insert(idx, self._normalise_row(row))
        self._row_keys.insert(idx, key)
        super().insert_row(idx, row)

    def delete_row(self, idx):
        if 0 <= idx < len(self._rows):
            del self._rows[idx]
            del self._row_keys[idx]
        super().delete_row(idx)

    def set_cell(self, row, col, value):
        if 0 <= row < len(self._rows):
            if isinstance(col, int):
                if 0 <= col < len(self._user_columns):
                    self._rows[row][self._user_columns[col]['key']] = value
            else:
                self._rows[row][col] = value
        super().set_cell(row, col, value)

    def clear(self):
        self._rows = []
        self._row_keys = []
        super().clear()

    def get_rows(self):
        """Return all rows as a list of dicts.  Mirrors the qtw
        wrapper's method so the same caller code works either way."""
        return [dict(r) for r in self._rows]

    def get_row(self, idx):
        if not (0 <= idx < len(self._rows)):
            raise IndexError(f"row index {idx} out of range")
        return dict(self._rows[idx])

    def set_column_editable(self, col, tf):
        """Mark a column as editable.

        ``col`` may be either an integer user-space column index
        (matching qtw/gtk) or a string column key (matching the
        native pgwidgets-js API).  We accept both so the same
        caller code works under any backend.
        """
        if isinstance(col, int):
            if not (0 <= col < len(self._user_columns)):
                return
            col_key = self._user_columns[col]['key']
        else:
            col_key = col
        # Keep the local _user_columns descriptor in sync so a
        # later set_columns() round-trip preserves the flag.
        for c in self._user_columns:
            if c['key'] == col_key:
                c['editable'] = bool(tf)
                break
        super().set_column_editable(col_key, bool(tf))

    # get_row_count, get_column_count, select_*, sort_by_column,
    # scroll_*, set_show_grid, set_show_row_numbers, set_sortable,
    # set_column_editable, set_column_width,
    # set_optimal_column_widths, set_scroll_position, and
    # get_scroll_position are all inherited from PGW.TableView
    # unchanged.

    # ----- selection conversion ------------------------------

    # ---- path normalisation ---------------------------------
    #
    # pgwidgets-js's TableView.set_data tags each row internally
    # with a string key ``"row0"``, ``"row1"``, ..., and surfaces
    # paths as ``["row0"]`` style lists.  The qtw wrapper, in
    # contrast, uses bare integer row indices (``[0]``, ``[1]``).
    # We convert at the boundary so portable caller code can use
    # integer paths uniformly under either widget set.

    def _to_pgw_path(self, path):
        """Convert a wrapper-style integer-index path (``[2]``) to
        a JS-side key path (``["row5"]``).  Uses our ``_row_keys``
        mirror — naïvely formatting ``'row{N}'`` would be wrong
        after any insert/delete, since JS auto-keys past collisions
        rather than reusing position numbers."""
        out = []
        for i, k in enumerate(path):
            if i == 0 and isinstance(k, int):
                if 0 <= k < len(self._row_keys):
                    out.append(self._row_keys[k])
                else:
                    out.append(f'row{k}')  # best-effort fallback
            elif isinstance(k, int):
                out.append(f'row{k}')
            else:
                out.append(k)
        return out

    def _from_pgw_path(self, path):
        """Inverse of ``_to_pgw_path``: convert ``["row5"]`` to
        ``[2]`` by looking the key up in our mirror.  Falls back
        to ``int(key[3:])`` only when the key isn't tracked — that
        preserves behaviour for paths from a tree we never set
        through ``set_rows`` (rare; mostly defensive)."""
        out = []
        for i, k in enumerate(path or ()):
            if i == 0 and isinstance(k, str):
                if k in self._row_keys:
                    out.append(self._row_keys.index(k))
                    continue
                if k.startswith('row'):
                    try:
                        out.append(int(k[3:]))
                        continue
                    except ValueError:
                        pass
            out.append(k)
        return out

    def get_selected(self):
        """Return selected rows as a list of dicts.

        The underlying ``PGW.TableView.get_selected`` returns a
        list of ``{path, values}`` records; we project to just the
        row dicts for parity with the qtw wrapper.
        """
        raw = super().get_selected()
        out = []
        for entry in raw or []:
            if isinstance(entry, dict) and 'values' in entry:
                out.append(entry['values'])
            else:
                out.append(entry)
        return out

    def get_selected_paths(self):
        """Return rows containing the current selection as a list
        of ``[row_index]`` paths.  Works for both row-mode and
        cell-mode selections — in cell mode the underlying row-
        level selection is empty, so we fall back to deriving row
        indices from the union of selected cells (matching what
        the qtw side returns from ``selectedItems()``)."""
        raw = super().get_selected()
        out = [self._from_pgw_path(entry['path'])
               for entry in (raw or [])
               if isinstance(entry, dict) and 'path' in entry]
        if out:
            return out
        # Cell-mode fallback: derive unique row paths from the
        # cell selection.
        seen = set()
        for c in self.get_selected_cells():
            path = c.get('path')
            if not path:
                continue
            key = tuple(path)
            if key in seen:
                continue
            seen.add(key)
            out.append(list(path))
        out.sort()
        return out

    def select_path(self, path, state=True):
        super().select_path(self._to_pgw_path(path), state)

    def select_paths(self, paths, state=True):
        super().select_paths([self._to_pgw_path(p) for p in paths],
                             state)

    def scroll_to_path(self, path):
        super().scroll_to_path(self._to_pgw_path(path))

    # ----- callback redirects --------------------------------

    def _cb_redirect_selected(self, sel_lst):
        # PGW emits the raw [{path, values}, ...] list; the
        # wrapper's get_selected projects to row dicts.
        self._make_callback('selected', self.get_selected())

    def _cb_redirect_activated(self, values, path, col_key=None):
        # PGW signature: (values_dict, path, col_key).  Re-emit as
        # (row_dict, path, col_key) so it matches qtw/gtk, with path
        # normalised to integer row indices.  ``col_key`` defaults
        # to None for older pgwidgets-js builds that don't yet send
        # the clicked column, and is also None when activation came
        # from the Enter key rather than a cell dblclick.
        self._make_callback('activated', values,
                            self._from_pgw_path(path), col_key)

    def _cb_redirect_sorted(self, col_key, ascending):
        self._make_callback('sorted', col_key, ascending)

    def _cb_redirect_cell_edited(self, path, col_key,
                                 old_value, new_value):
        self._make_callback('cell_edited',
                            self._from_pgw_path(path), col_key,
                            old_value, new_value)

    def _cb_redirect_scrolled(self, h_pct, v_pct):
        self._make_callback('scrolled', h_pct, v_pct)

    def _cb_redirect_cell_action(self, path, col_key):
        """JS fires ``cell_action(path, col_key)`` when the user
        clicks a button-shaped widget cell.  Resolve ``path`` to
        the row dict and re-emit as ``cell_action(table, row_dict,
        col_key)`` to match the qtw signature."""
        idx_path = self._from_pgw_path(path)
        idx = idx_path[0] if idx_path else None
        row = (dict(self._rows[idx])
               if idx is not None and 0 <= idx < len(self._rows)
               else None)
        self._make_callback('cell_action', row, col_key)

    def _cb_redirect_cell_selected(self, cells):
        # JS sends ``[{path, col_key, value}, ...]`` with pgw-style
        # paths.  Normalise paths to integer row indices to match
        # the qtw side.
        out = []
        for c in (cells or []):
            if isinstance(c, dict):
                d = dict(c)
                if 'path' in d:
                    d['path'] = self._from_pgw_path(d['path'])
                out.append(d)
        self._make_callback('cell_selected', out)

    def _cb_redirect_clipboard(self, tsv, name):
        # ``copy``/``cut``/``paste`` carry the TSV (or pasted text)
        # exactly as the JS produced it.  Re-emit unchanged.
        self._make_callback(name, tsv)

    # ----- cell-selection API (matches the qtw wrapper) -------

    def get_selected_cells(self):
        """Return ``[{path, col_key, value}, ...]`` for the current
        cell selection, with paths normalised to integer row
        indices."""
        raw = super().get_selected_cells()
        out = []
        for c in (raw or []):
            if isinstance(c, dict):
                d = dict(c)
                if 'path' in d:
                    d['path'] = self._from_pgw_path(d['path'])
                out.append(d)
        return out

    def select_cell(self, path, col_key, state=True):
        super().select_cell(self._to_pgw_path(path), col_key, bool(state))

    def select_cells(self, cells, state=True):
        converted = []
        for c in (cells or []):
            converted.append({
                'path': self._to_pgw_path(c.get('path', [])),
                'col_key': c.get('col_key'),
            })
        super().select_cells(converted, bool(state))

    def clear_cell_selection(self):
        super().clear_cell_selection()

    # ``copy_selection`` / ``cut_selection`` / ``paste_selection``
    # are exposed by pgwidgets-js as auto-dispatched action methods
    # (see ``pgwidgets_js/defs.py``).  pgwidgets-python's class
    # factory generates the matching Python methods automatically,
    # so the inherited ones forward the call into the browser and
    # fire the ``copy`` / ``cut`` / ``paste`` callbacks once the
    # JS-side clipboard work completes.  No wrapper override
    # needed.

    # ----- per-cell / row / column / table colour overrides --
    #
    # ``set_column_color`` / ``set_table_color`` / ``clear_column_color``
    # / ``clear_all_colors`` don't need path translation and so are
    # auto-generated from defs.py without further help here.  The
    # path-taking methods need our integer-index ↔ pgw-row-key
    # boundary conversion.

    def set_cell_color(self, path, col_key, fg=None, bg=None, bold=None):
        super().set_cell_color(self._to_pgw_path(path), col_key,
                               fg=fg, bg=bg, bold=bold)

    def set_row_color(self, path, fg=None, bg=None, bold=None):
        super().set_row_color(self._to_pgw_path(path),
                              fg=fg, bg=bg, bold=bold)

    def clear_cell_color(self, path, col_key):
        super().clear_cell_color(self._to_pgw_path(path), col_key)

    def clear_row_color(self, path):
        super().clear_row_color(self._to_pgw_path(path))


class Canvas(WidgetMixin, PGW.Canvas):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.Canvas.__init__(self, *get_args(args), **kwargs)


class Box(ContainerWidgetMixin, PGW.Box):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Box.__init__(self, *get_args(args), **kwargs)


class HBox(ContainerWidgetMixin, PGW.HBox):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.HBox.__init__(self, *get_args(args), **kwargs)


class VBox(ContainerWidgetMixin, PGW.VBox):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.VBox.__init__(self, *get_args(args), **kwargs)


class ButtonBox(ContainerWidgetMixin, PGW.ButtonBox):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.ButtonBox.__init__(self, *get_args(args), **kwargs)


class FixedLayout(ContainerWidgetMixin, PGW.FixedLayout):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.FixedLayout.__init__(self, *get_args(args), **kwargs)


class Frame(ContainerWidgetMixin, PGW.Frame):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Frame.__init__(self, *get_args(args), **kwargs)


class Expander(ContainerWidgetMixin, PGW.Expander):
    def __init__(self, *args, notoggle=False, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Expander.__init__(self, *get_args(args),
                              collapsible=not notoggle, **kwargs)

    def expand(self, tf):
        self.set_collapsed(not tf)


class TabWidget(ContainerWidgetMixin, PGW.TabWidget):
    def __init__(self, *args, tabpos='top', reorderable=False,
                 detachable=False, closable=False, group=0):
        ContainerWidgetMixin.__init__(self)
        PGW.TabWidget.__init__(self, *get_args(args), closable=closable,
                               reorderable=reorderable, tab_position=tabpos)

        # remapping 'page_switch'
        self.on('page-switch', self._cb_redirect)
        self._enable_callback('page-switch')

    def add_widget(self, child, title=''):
        # pgwidgets' add_widget takes (child, options); pack the tab
        # title into the options object it expects
        return super().add_widget(child, dict(title=title))

    def _cb_redirect(self, child, index):
        self._make_callback('page-switch', child)


class StackWidget(ContainerWidgetMixin, PGW.StackWidget):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.StackWidget.__init__(self, *get_args(args), **kwargs)

        # remapping 'page_switch'
        self.on('page-switch', self._cb_redirect)
        self._enable_callback('page-switch')

    def add_widget(self, child, title=''):
        # pgwidgets' add_widget takes (child, options); pack the tab
        # title into the options object it expects
        return super().add_widget(child, dict(title=title))

    def _cb_redirect(self, child, index):
        self._make_callback('page-switch', child)


class MDIWidget(ContainerWidgetMixin, PGW.MDIWidget):
    def __init__(self, *args, tabpos='top', mode='mdi', **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.MDIWidget.__init__(self, *get_args(args), **kwargs)

        self.true_mdi = True
        self.icon_data_uri = PgHelp.get_icon(app_icon_path, size=(16, 16))

    def add_widget(self, child, title=''):
        # pgwidgets' add_widget takes (child, options); pack the title
        # and window icon into the options object it expects
        return super().add_widget(child, dict(title=title,
                                              icon_url=self.icon_data_uri))

    def tile_panes(self):
        super().tile_windows()

    def cascade_panes(self):
        super().cascade_windows()


# class MDISubWindow(ContainerWidgetMixin, PGW.MDISubWindow):
#     def __init__(self, *args, **kwargs):
#         ContainerWidgetMixin.__init__(self)
#         PGW.MDISubWindow.__init__(self, *get_args(args), **kwargs)

#     def move(self, x, y):
#         super().set_position(x, y)


class ScrollArea(ContainerWidgetMixin, PGW.ScrollArea):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.ScrollArea.__init__(self, *get_args(args), **kwargs)

    def scroll_to_end(self, vertical=True, horizontal=False):
        h_pct, v_pct = self.get_scroll_position()
        if vertical:
            v_pct = 1.0
        if horizontal:
            h_pct = 1.0
        self.set_scroll_position(h_pct, v_pct)


class AbstractScrollArea(ContainerWidgetMixin, PGW.AbstractScrollArea):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.AbstractScrollArea.__init__(self, *get_args(args), **kwargs)


class Splitter(ContainerWidgetMixin, PGW.Splitter):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Splitter.__init__(self, *get_args(args), **kwargs)


class GridBox(ContainerWidgetMixin, PGW.GridBox):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.GridBox.__init__(self, *get_args(args), **kwargs)

    def resize_grid(self, rows, columns):
        pass

    def add_widget(self, child, row, col, stretch=0):
        super().add_widget(child, row, col)


class ToolbarAction(WidgetMixin, PGW.ToolBarAction):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.ToolBarAction.__init__(self, *get_args(args), **kwargs)


class Toolbar(ContainerWidgetMixin, PGW.ToolBar):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.ToolBar.__init__(self, *get_args(args), **kwargs)

    def add_menu(self, text, menu=None, mtype='tool'):
        if menu is None:
            menu = Menu()
        if mtype == 'mbar':
            child = self.add_action(text, menu=menu)
        else:
            child = Button(text)
            self.add_widget(child)
            child.add_callback('activated', self._popup_menu, menu)

        return menu

    def _popup_menu(self, child, menu):
        x, y = child.get_position()
        menu.popup(x + 20, y + 20)

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None,
                   menu=None):
        icon_uri = None
        if iconpath is not None:
            icon_uri = PgHelp.get_icon(iconpath, size=iconsize)

        # pgwidgets' add_action takes a single ``options`` object
        options = dict(text=text, icon_url=icon_uri, toggle=toggle)
        if menu is not None:
            options['menu'] = menu
        return super().add_action(options)


class MenuAction(WidgetMixin, PGW.MenuAction):
    def __init__(self, *args, **kwargs):
        WidgetMixin.__init__(self)
        PGW.MenuAction.__init__(self, *get_args(args), **kwargs)


class Menu(ContainerWidgetMixin, PGW.Menu):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Menu.__init__(self, *get_args(args), **kwargs)

    def add_name(self, name, checkable=False):
        child = MenuAction(text=name, checkable=checkable)
        self.add_widget(child)
        return child

    def add_menu(self, name, menu=None):
        if menu is None:
            menu = Menu()
        super().add_menu(name, menu)
        return menu

    def get_menu(self, name):
        menu = super().get_menu(name)
        if menu is None:
            raise KeyError(name)
        return menu

    def popup(self, *args):
        if len(args) == 0:
            x, y = 0, 0
        elif len(args) == 1:
            widget = args[0]
            x, y = widget.get_position()
            # offset a bit from popup widget
            x, y = x + 20, y + 20
        elif len(args) == 2:
            x, y = args
        super().popup(x, y)


class Menubar(ContainerWidgetMixin, PGW.MenuBar):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.MenuBar.__init__(self, *get_args(args), **kwargs)

    def add_name(self, name):
        child = Menu()
        self.add_menu(child, name)
        return child

    def get_menu(self, name):
        menu = super().get_menu(name)
        if menu is None:
            raise KeyError(name)
        return menu


class Page(ContainerWidgetMixin, PGW.Page):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Page.__init__(self, *get_args(args), **kwargs)


class TopLevel(ContainerWidgetMixin, PGW.TopLevel):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.TopLevel.__init__(self, *get_args(args), **kwargs)


class Dialog(ContainerWidgetMixin, PGW.Dialog):
    def __init__(self, *args, parent=None, flags=None, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.Dialog.__init__(self, *get_args(args), **kwargs)

    def get_content_area(self):
        # NOTE: this is a bit of a hack--get_content_area is not directly
        # supported via the Python interface. But many of the same methods
        # will work on the Dialog itself
        return self

    def delete(self):
        super().destroy()


class ColorDialog(ContainerWidgetMixin, PGW.ColorDialog):
    def __init__(self, *args, parent=None, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.ColorDialog.__init__(self, *get_args(args), **kwargs)


class FileDialog(ContainerWidgetMixin, FileBrowser):
    """File browser for accessing files locally."""
    def __init__(self, *args, title='', parent=None, **kwargs):
        ContainerWidgetMixin.__init__(self)
        FileBrowser.__init__(self, *get_args(args), title=title)


class BrowserFileDialog(ContainerWidgetMixin, PGW.FileDialog):
    """File browser for uploading files to a remote instance."""
    def __init__(self, *args, parent=None, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.FileDialog.__init__(self, *get_args(args))

    def popup(self, *args):
        self.show()


class MessageDialog(Dialog):

    icon_dct = dict()

    @classmethod
    def set_category_icon(cls, category, iconpath, size=(64, 64)):
        cls.icon_dct[category] = iconpath

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
                iconpath = os.path.join(icondir, iconfile)
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
            img = Image()
            img.load_file(self.icon_dct[category])
            hbox.add_widget(img, stretch=0)
            hbox.add_widget(Label(""), stretch=1)
            vbox.add_widget(hbox, stretch=1)

        tw = Label(text)
        vbox.add_widget(tw, stretch=1)
        vbox.add_widget(tw)


class Timer(CallbackMixin, PGW.Timer):
    def __init__(self, *args, **kwargs):
        CallbackMixin.__init__(self)
        if in_situ_web:
            PGW.Timer.__init__(self, **kwargs)
        else:
            PGW.Timer.__init__(self, *get_args(args), **kwargs)

        # for storing random data in a timer
        self.data = Bunch.Bunch()

        # remapping 'expired'
        for name in ['expired', 'cancelled']:
            self.on(name, self._cb_redirect, name)
            self._enable_callback(name)

    def _cb_redirect(self, value, name):
        self._make_callback(name)

    def set(self, val):
        self.start(val)

    def clear(self):
        self.cancel()


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
        w = Label(title, halign='right')
    elif wtype == 'llabel':
        w = Label(title, halign='left')
    elif wtype in ('textentry', 'entry'):
        w = TextEntry()
        w.set_length(12)
    elif wtype in ('textentryset', 'entryset'):
        w = TextEntrySet()
        w.set_length(12)
    elif wtype == 'combobox':
        w = ComboBox()
        w.set_length(12)
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
    return native_widget


# END
