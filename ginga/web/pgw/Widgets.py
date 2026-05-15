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
from ginga.util.paths import icondir

__all__ = ['WidgetError', 'Widget', 'WidgetBase', 'TextEntry', 'TextEntrySet',
           'TextArea', 'TextSource', 'Dial', 'Label', 'Button', 'ComboBox',
           'SpinBox', 'Slider', 'ScrollBar', 'CheckBox', 'ToggleButton',
           'RadioButton', 'Image', 'Canvas', 'ProgressBar', 'StatusBar',
           'TreeView', 'TableView', 'Box', 'HBox', 'VBox', 'ButtonBox',
           'FixedLayout', 'Frame', 'Expander', 'TabWidget', 'StackWidget',
           'MDIWidget', 'ScrollArea', 'Splitter', 'GridBox',
           'ToolbarAction', 'Toolbar', 'MenuAction', 'Menu', 'Menubar',
           'Page', 'TopLevel', 'Dialog',
           'FileDialog', 'ColorDialog', 'MessageDialog', 'Timer',
           'Application', 'name_mangle', 'make_widget', 'hadjust',
           'build_info', 'wrap']


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
            PGW.Widget.add_callback(self, name, cb_fn, *args, **kwargs)


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
        # set_font api in pgwidgets
        if isinstance(font_info, str):
            font_info = PgHelp.get_font(font_info, size)
        super().set_font(dict(font=font_info.family, size=font_info.point_size,
                              weight=font_info.weight, style=font_info.style))

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

    def make_window(self, title=None):
        win = TopLevel(title=title, moveable=True, resizable=True)
        self.add_window(win)
        return win

    def add_window(self, win):
        if win not in self._windows:
            self._windows.append(win)

    def make_timer(self):
        return Timer()

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
                     ws_port=None, settings=None, token='none'):
            ApplicationBase.__init__(self, logger=logger, host=host, port=port,
                                     ws_port=ws_port, settings=settings)

    FileBrowser = PGW.FileDialog  # noqa

else:
    # <-- Running on a host and using the web socket interface

    class Application(PGW_Application, ApplicationBase):
        """Application class when only the GUI is in the browser."""

        def __init__(self, logger=None, host='localhost', port=9909,
                     ws_port=None, settings=None, max_sessions=1,
                     token='none'):
            global _session
            ApplicationBase.__init__(self, logger=logger, host=host, port=port,
                                     ws_port=ws_port, settings=settings)
            if ws_port is None:
                ws_port = port + 1
            PGW_Application.__init__(self, ws_port=ws_port,
                                     http_port=port, host=host,
                                     http_server=True,
                                     max_sessions=max_sessions,
                                     concurrency_handling='serialized')

            # we create a default session that is used by the widgets
            self.default_session = self.create_session(session_id=_session_id,
                                                       token=token)
            _session = self.default_session

        def get_screen_size(self):
            return self.default_session.get_screen_size()

        def get_url(self):
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

    def _cb_redirect_activated(self, node_vals, path):
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
    def __init__(self, *args, auto_expand=False, sortable=False,
                 selection='single', use_alt_row_color=False):
        WidgetMixin.__init__(self)

        PGW.TreeView.__init__(self, *get_args(args),
                              selection_mode=selection, sortable=sortable,
                              alternate_row_colors=use_alt_row_color)


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

    def _cb_redirect(self, child, index):
        self._make_callback('page-switch', child)


class StackWidget(ContainerWidgetMixin, PGW.StackWidget):
    def __init__(self, *args, **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.StackWidget.__init__(self, *get_args(args), **kwargs)

        # remapping 'page_switch'
        self.on('page-switch', self._cb_redirect)
        self._enable_callback('page-switch')

    def _cb_redirect(self, child, index):
        self._make_callback('page-switch', child)


class MDIWidget(ContainerWidgetMixin, PGW.MDIWidget):
    def __init__(self, *args, tabpos='top', mode='mdi', **kwargs):
        ContainerWidgetMixin.__init__(self)
        PGW.MDIWidget.__init__(self, *get_args(args), **kwargs)

        self.true_mdi = True

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

    def get_scroll_position(self):
        # TODO: this is a bug in pgwidgets, sometimes returns None
        res = super().get_scroll_position()
        if res is None:
            return (1.0, 1.0)
        return res

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

    def add_action(self, text, toggle=False, iconpath=None, iconsize=None):
        icon_uri = None
        if iconpath is not None:
            icon_uri = PgHelp.get_icon(iconpath, size=iconsize)

        return super().add_action(text=text, icon_url=icon_uri, toggle=toggle)


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


# class FileDialog(ContainerWidgetMixin, PGW.FileDialog):
#     def __init__(self, *args, title='', parent=None, **kwargs):
#         ContainerWidgetMixin.__init__(self)
#         PGW.FileDialog.__init__(self, *get_args(args), **kwargs)

class FileDialog(ContainerWidgetMixin, FileBrowser):
    def __init__(self, *args, title='', parent=None, **kwargs):
        ContainerWidgetMixin.__init__(self)
        FileBrowser.__init__(self, *get_args(args), title=title)


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
