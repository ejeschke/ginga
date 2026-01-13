#
# GenericControl.py -- Generic controller base class.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys
import os
import traceback
import tempfile
import threading
import webbrowser

# Local application imports
from ginga.misc import Bunch
from ginga.util import toolbox
from ginga.doc import download_doc

# GUI imports
from ginga.gw import GwHelp, GwMain, PluginManager
from ginga.gw import Widgets, Desktop
from ginga.util.paths import icondir as icon_dir

pluginconfpfx = None


class GenericShell(GwMain.GwMain, Widgets.Application):
    """
    Main generic shell for housing global plugins and building a UI from
    a layout.
    """
    def __init__(self, logger, thread_pool, module_manager, preferences,
                 ev_quit=None):
        GwMain.GwMain.__init__(self, logger=logger, ev_quit=ev_quit,
                               app=self, thread_pool=thread_pool)

        # Create general preferences
        self.prefs = preferences
        settings = self.prefs.create_category('general')
        settings.add_defaults(appname='ginga',
                              title="Ginga",
                              confirm_shutdown=True,
                              save_layout=False)
        settings.load(onError='silent')
        # this will set self.logger and self.settings
        Widgets.Application.__init__(self, logger=logger, settings=settings)

        self.mm = module_manager
        # event for controlling termination of threads executing in this
        # object
        if not ev_quit:
            self.ev_quit = threading.Event()
        else:
            self.ev_quit = ev_quit

        self.tmpdir = tempfile.gettempdir()

        # For callbacks
        for name in ('delete-workspace'):
            self.enable_callback(name)

        self.lock = threading.RLock()
        self.wscount = 0
        self.appname = settings.get('appname', 'ginga')

        self.plugins = []
        self._plugin_sort_method = self.get_plugin_menuname

        # This plugin manager handles "global" (aka standard) plug ins
        self.gpmon = self.get_plugin_manager(self.logger, self,
                                             None, self.mm)

        # GUI initialization
        self.w = Bunch.Bunch()
        self.main_wsname = None
        self._lastwsname = None
        self.ds = None
        self.layout = None
        self.layout_file = None
        self._help = Bunch.Bunch(remember_choice=False, choice=0)

        self.gui_dialog_lock = threading.RLock()
        self.gui_dialog_list = []
        self.w.root = None

    def get_preferences(self):
        return self.prefs

    def stop(self):
        self.logger.info(f"shutting down {self.appname}...")
        self.ev_quit.set()
        self.logger.debug("should be exiting now")

    # PLUGIN MANAGEMENT

    def get_plugin_manager(self, logger, image_viewer, ds, mm):
        return PluginManager.PluginManager(logger, image_viewer, ds, mm)

    def start_global_plugin(self, plugin_name, raise_tab=False):
        self.gpmon.start_plugin_future(None, plugin_name, None)
        if raise_tab:
            p_info = self.gpmon.get_plugin_info(plugin_name)
            self.ds.raise_tab(p_info.tabname)

    def stop_global_plugin(self, plugin_name):
        self.gpmon.deactivate(plugin_name)

    def call_global_plugin_method(self, plugin_name, method_name,
                                  args, kwargs):
        """
        Parameters
        ----------
        plugin_name : str
            The name of the global plugin containing the method to call.

        method_name : str
            The name of the method to call.

        args : list or tuple
            The positional arguments to the method

        kwargs : dict
            The keyword arguments to the method

        Returns
        -------
        result : return value from calling the method
        """
        p_obj = self.gpmon.get_plugin(plugin_name)
        method = getattr(p_obj, method_name)
        return self.gui_call(method, *args, **kwargs)

    def start_plugin(self, plugin_name, spec):
        self.start_global_plugin(plugin_name, raise_tab=True)

    def add_global_plugin(self, spec):
        try:
            spec.setdefault('ptype', 'global')
            name = spec.setdefault('name', spec.get('klass', spec.module))

            pfx = spec.get('pfx', pluginconfpfx)
            path = spec.get('path', None)
            self.plugins.append(spec)
            if spec.get('enabled', True):
                self.mm.load_module(spec.module, pfx=pfx, path=path)

            self.gpmon.load_plugin(name, spec)

        except Exception as e:
            self.logger.error("Unable to load global plugin '%s': %s" % (
                name, str(e)))

    def add_plugin(self, spec):
        self.add_global_plugin(spec)

    def set_plugins(self, plugins):
        self.plugins = []
        for spec in plugins:
            self.add_plugin(spec)

    def get_plugins(self):
        return self.plugins

    def get_plugin_spec(self, name):
        """Get the specification attributes for plugin with name `name`."""
        l_name = name.lower()
        for spec in self.plugins:
            name = spec.get('name', spec.get('klass', spec.module))
            if name.lower() == l_name:
                return spec
        raise KeyError(name)

    def get_plugin_menuname(self, spec):
        category = spec.get('category', None)
        name = spec.setdefault('name', spec.get('klass', spec.module))
        menu = spec.get('menu', spec.get('tab', name))
        if category is None:
            return menu
        return category + '.' + menu

    def set_plugin_sortmethod(self, fn):
        self._plugin_sort_method = fn

    def boot_plugins(self):
        # Sort plugins according to desired order
        self.plugins.sort(key=self._plugin_sort_method)

        for spec in self.plugins:
            name = spec.setdefault('name', spec.get('klass', spec.module))
            start = spec.get('start', True)
            # for now only start global plugins that have start==True
            if start and spec.get('ptype', 'local') == 'global':
                self.error_wrap(self.start_plugin, name, spec)

    def show_error(self, errmsg, raisetab=True):
        if self.gpmon.has_plugin('Errors'):
            obj = self.gpmon.get_plugin('Errors')
            obj.add_error(errmsg)
            if raisetab:
                self.ds.raise_tab('Errors')

    def error_wrap(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)

        except Exception as e:
            errmsg = "\n".join([e.__class__.__name__, str(e)])
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."
            errmsg += tb_str
            self.logger.error(errmsg)
            self.gui_do(self.show_error, errmsg, raisetab=True)

    def help_text(self, name, text, text_kind='plain', trim_pfx=0):
        """
        Provide help text for the user.

        This method will trim the text as necessary and display it in
        the text widget.

        Parameters
        ----------
        name : str
            Category of help to show.

        text : str
            The text to show.

        text_kind : str (optional)
            One of 'plain' or 'rst'.  Default is 'plain'.

        trim_pfx : int (optional)
            Number of spaces to trim off the beginning of each line of text.

        """
        if trim_pfx > 0:
            # caller wants to trim some space off the front
            # of each line
            text = toolbox.trim_prefix(text, trim_pfx)

        if text_kind in ['rst', 'plain']:
            self.show_help_text(name, text)

        else:
            raise ValueError(
                "I don't know how to display text of kind '%s'" % (text_kind))

    def help(self, text=None, text_kind='url'):
        if text_kind == 'url':
            if text is None:
                # get top URL of external RTD docs
                text = download_doc.get_online_docs_url(plugin=None)
            self.show_help_url(text)
        else:
            if isinstance(text, str):
                self.show_help_text('HELP', text)

    def show_help_url(self, url):
        """
        Open a URL in an external browser using Python's webbrowser module.
        """
        self.logger.info(f"opening '{url}' in external browser...")
        webbrowser.open(url)

    def help_plugin(self, plugin_obj, text_kind='rst', url=None):
        """
        Called from a plugin's default help() method. Offers to show the
        user plugin docstring in a text widget or view the RTD doc in an
        external web browser.
        """

        def _do_help(val, url=None):
            if val == 1:
                # show plain text in a text widget
                if plugin_obj is not None:
                    name, doc = plugin_obj._get_docstring()
                    self.show_help_text(name, doc)
            elif val == 2:
                # show web page in external browser
                if url is None:
                    url = download_doc.get_online_docs_url(plugin=plugin_obj)
                self.show_help_url(url)

        if self._help.choice > 0:
            # User made a decision to keep getting plugin help the same way
            return _do_help(self._help.choice, url=url)

        # Create troubleshooting dialog if downloading cannot be done
        dialog = Widgets.Dialog(title="Show documentation",
                                parent=self.w.root,
                                modal=False,
                                buttons=[("Cancel", 0),
                                         ("Show RST text", 1),
                                         ("Use external browser", 2),
                                         ])
        dialog.buttons[0].set_tooltip("Skip help")
        dialog.buttons[1].set_tooltip("Show local docstring for plugin help")
        dialog.buttons[2].set_tooltip("Show online web documentation in external browser")
        vbox = dialog.get_content_area()
        dialog_text = Widgets.TextArea(wrap=True, editable=False)
        dialog_text.set_text("How would you like to see help?")
        vbox.add_widget(dialog_text, stretch=1)
        cb = Widgets.CheckBox("Remember my choice for session")
        cb.set_state(False)
        vbox.add_widget(cb, stretch=0)

        def _remember_choice_cb(w, tf):
            self._help.remember_choice = tf

        def _do_help_cb(dialog, val, url=None):
            if self._help.remember_choice:
                self._help.choice = val
            self.ds.remove_dialog(dialog)
            _do_help(val, url=url)

        cb.add_callback('activated', _remember_choice_cb)
        dialog.add_callback('activated', _do_help_cb, url=url)
        self.ds.show_dialog(dialog)

    def show_help_text(self, name, help_txt, wsname='channels'):
        """
        Show help text in a closeable tab window.  The title of the
        window is set from ``name`` prefixed with 'HELP:'
        """
        tabname = 'HELP: {}'.format(name)
        group = 1
        tabnames = self.ds.get_tabnames(group)
        if tabname in tabnames:
            # tab is already up somewhere
            return

        vbox = Widgets.VBox()
        vbox.set_margins(4, 4, 4, 4)
        vbox.set_spacing(2)

        msg_font = self.get_font('fixed', 12)
        tw = Widgets.TextArea(wrap=False, editable=False)
        tw.set_font(msg_font)
        tw.set_text(help_txt)
        vbox.add_widget(tw, stretch=1)

        btns = Widgets.HBox()
        btns.set_border_width(4)
        btns.set_spacing(3)

        def _close_cb(w):
            self.ds.remove_tab(tabname)

        btn = Widgets.Button("Close")
        btn.add_callback('activated', _close_cb)
        btns.add_widget(btn, stretch=0)
        btns.add_widget(Widgets.Label(''), stretch=1)

        vbox.add_widget(btns, stretch=0)

        self.ds.add_tab(wsname, vbox, group, tabname)
        self.ds.raise_tab(tabname)

    def configure_workspace(self, wstype):
        ws = self.get_current_workspace()
        ws.configure_wstype(wstype)

    def cycle_workspace_type(self):
        ws = self.get_current_workspace()
        ws.cycle_wstype()

    def add_workspace(self, wsname, wstype, inSpace=None, use_toolbar=True):
        if inSpace is None:
            inSpace = self.main_wsname

        if wsname in self.ds.get_tabnames(None):
            raise ValueError("Tab name already in use: '%s'" % (wsname))

        ws = self.ds.make_ws(name=wsname, group=1, wstype=wstype,
                             use_toolbar=use_toolbar)
        if inSpace != 'top level':
            self.ds.add_tab(inSpace, ws.widget, 1, ws.name)
        else:
            #width, height = 700, 800
            #self.ds.create_toplevel_ws(width, height, group=1)
            top_w = self.ds.add_toplevel(ws, ws.name)
            ws.extdata.top_w = top_w

        return ws

    def delete_workspace(self, ws):
        # close the workspace
        top_w = ws.extdata.get('top_w', None)
        if top_w is None:
            self.ds.remove_tab(ws.name)
        else:
            # this is a top-level window
            self.ds.remove_toplevel(top_w)

        # inform desktop we are no longer tracking this
        self.ds.delete_ws(ws.name)

        self.make_gui_callback('delete-workspace', ws)

    def show_status(self, text):
        """Write a message to the status bar.

        Parameters
        ----------
        text : str
            The message.

        """
        self.status_msg("%s", text)

    def error(self, text):
        self.logger.error(text)
        self.status_msg("%s", text)
        # TODO: turn bar red

    def logit(self, text):
        try:
            obj = self.gpmon.get_plugin('Log')
            self.gui_do(obj.log, text)
        except Exception:
            pass

    def set_loglevel(self, level):
        handlers = self.logger.handlers
        for hdlr in handlers:
            hdlr.setLevel(level)

    def set_layout(self, layout, layout_file=None, save_layout=False,
                   main_wsname=None):
        self.layout = layout
        self.layout_file = layout_file
        self.save_layout = save_layout
        if main_wsname is not None:
            self.main_wsname = main_wsname

    def get_screen_dimensions(self):
        return (self.screen_wd, self.screen_ht)

    def build_toplevel(self, ignore_saved_layout=False):
        lo_file = self.layout_file
        if ignore_saved_layout:
            lo_file = None

        self.w.tooltips = None

        self.ds = Desktop.Desktop(self)
        self.ds.build_desktop(self.layout, lo_file=lo_file,
                              widget_dict=self.w)
        if self.main_wsname is None:
            ws = self.ds.get_default_ws()
            if ws is not None:
                self.main_wsname = ws.name
            else:
                # legacy value for layouts that don't define a default
                # workspace
                self.main_wsname = 'channels'
        self._lastwsname = self.main_wsname
        # TEMP: FIX ME!
        self.gpmon.ds = self.ds

        self.add_callback('close', self.close_cb)
        self.add_callback('shutdown', self.shutdown_cb)
        for win in self.ds.toplevels:
            # add delete/destroy callbacks
            win.add_callback('close', self.window_close)
            win.set_title(self.settings.get('title', "Ginga"))
            root = win
        self.ds.add_callback('all-closed', self.quit)

        self.w.root = root

        # initialize workspaces
        for wsname in self.ds.get_wsnames():
            ws = self.ds.get_ws(wsname)
            self.init_workspace(ws)

        if 'status' in self.w:
            statusholder = self.w['status']
            self.add_statusbar(statusholder)

        self.w.root.show()

    def add_statusbar(self, holder):
        self.w.status = Widgets.StatusBar()
        holder.add_widget(self.w.status, stretch=1)

    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def set_titlebar(self, text):
        self.w.root.set_title("{}: {}".format(self.appname.capitalize(), text))

    def status_msg(self, format, *args):
        if not format:
            s = ''
        else:
            s = format % args

        if 'status' in self.w:
            self.w.status.set_message(s)

    def set_pos(self, x, y):
        self.w.root.move(x, y)

    def set_size(self, wd, ht):
        self.w.root.resize(wd, ht)

    def set_geometry(self, geometry):
        # translation of X window geometry specification WxH+X+Y
        coords = geometry.replace('+', ' +')
        coords = coords.replace('-', ' -')
        coords = coords.split()
        if 'x' in coords[0]:
            # spec includes dimensions
            dim = coords[0]
            coords = coords[1:]
        else:
            # spec is position only
            dim = None

        if dim is not None:
            # user specified dimensions
            dim = list(map(int, dim.split('x')))
            self.set_size(*dim)

        if len(coords) > 0:
            # user specified position
            coords = list(map(int, coords))
            self.set_pos(*coords)

    def get_font(self, font_family, point_size):
        return GwHelp.get_font(font_family, point_size)

    def get_icon(self, icondir, filename):
        iconpath = os.path.join(icondir, filename)
        icon = GwHelp.get_icon(iconpath)
        return icon

    ####################################################
    # CALLBACKS
    ####################################################

    def window_close(self, w):
        """Quit the application.
        """
        # forces processing of close_cb
        self.close()

    def close_cb(self, app):
        if not self.settings.get('confirm_shutdown', True):
            self.quit()

        # confirm close with a dialog here
        q_quit = Widgets.Dialog(title="Confirm Quit", modal=False,
                                parent=self.w.root,
                                buttons=[("Cancel", False), ("Confirm", True)])
        # necessary so it doesn't get garbage collected right away
        self.w.quit_dialog = q_quit
        vbox = q_quit.get_content_area()
        vbox.set_margins(4, 4, 4, 4)
        hbox = Widgets.HBox()
        hbox.set_border_width(4)
        hbox.add_widget(Widgets.Label(""), stretch=1)
        img = Widgets.Image()
        iconfile = os.path.join(icon_dir, "warning.svg")
        img.load_file(iconfile)
        hbox.add_widget(img, stretch=0)
        hbox.add_widget(Widgets.Label(""), stretch=1)
        vbox.add_widget(hbox, stretch=1)
        vbox.add_widget(Widgets.Label("Do you really want to quit?"))
        q_quit.add_callback('activated', self._confirm_quit_cb)
        q_quit.add_callback('close', lambda w: self._confirm_quit_cb(w, False))
        q_quit.show()

    def _confirm_quit_cb(self, w, tf):
        dialog = self.w.quit_dialog
        self.w.quit_dialog = None
        if dialog is not None:
            dialog.delete()
        if not tf:
            return

        self.quit()

    def shutdown_cb(self, app):
        """Quit the application.
        """
        self.logger.info("Attempting to shut down the application...")

        # write out our current layout
        if self.layout_file is not None and self.save_layout:
            self.error_wrap(self.ds.write_layout_conf, self.layout_file)

        self.stop()

        # stop all global plugins
        self.gpmon.stop_all_plugins()

        self.w.root = None
        while len(self.ds.toplevels) > 0:
            w = self.ds.toplevels.pop()
            w.delete()

    def next_dialog(self):
        with self.gui_dialog_lock:
            # this should be the just completed call for a dialog
            # that gets popped off
            self.gui_dialog_list.pop(0)

            if len(self.gui_dialog_list) > 0:
                # if there are any other dialogs waiting, start
                # the next one
                future = self.gui_dialog_list[0]
                self.nongui_do_future(future)

    def init_workspace(self, ws):
        # subclass should override as necessary
        pass
