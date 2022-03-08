#
# Control.py -- Controller for the Ginga reference viewer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# stdlib imports
import sys
import os
import traceback
import time
import tempfile
import threading
import logging
import platform
import atexit
import shutil
import inspect
from collections import deque, OrderedDict

# Local application imports
from ginga import cmap, imap
from ginga.misc import Bunch, Timer, Future
from ginga.util import catalog, iohelper, loader, toolbox
from ginga.util import viewer as gviewer
from ginga.canvas.CanvasObject import drawCatalog
from ginga.canvas.types.layer import DrawingCanvas

# GUI imports
from ginga.gw import GwHelp, GwMain, PluginManager
from ginga.gw import Widgets, Viewers, Desktop
from ginga import toolkit
from ginga.fonts import font_asst

# Version
from ginga import __version__

# Reference viewer
from ginga.rv.Channel import Channel

have_docutils = False
try:
    from docutils.core import publish_string
    have_docutils = True
except ImportError:
    pass


#pluginconfpfx = 'plugins'
pluginconfpfx = None

package_home = os.path.split(sys.modules['ginga.version'].__file__)[0]

# pick up plugins specific to our chosen toolkit
tkname = toolkit.get_family()
if tkname is not None:
    # TODO: this relies on a naming convention for widget directories!
    # TODO: I think this can be removed, since the widget specific
    # plugin directories have been deleted
    child_dir = os.path.join(package_home, tkname + 'w', 'plugins')
    sys.path.insert(0, child_dir)

icon_path = os.path.abspath(os.path.join(package_home, 'icons'))


class ControlError(Exception):
    pass


class GingaViewError(Exception):
    pass


class GingaShell(GwMain.GwMain, Widgets.Application):
    """
    Main Ginga shell for housing plugins and running the reference
    viewer.

    """
    def __init__(self, logger, thread_pool, module_manager, preferences,
                 ev_quit=None):
        GwMain.GwMain.__init__(self, logger=logger, ev_quit=ev_quit,
                               app=self, thread_pool=thread_pool)

        # Create general preferences
        self.prefs = preferences
        settings = self.prefs.create_category('general')
        settings.add_defaults(fixedFont=None,
                              serifFont=None,
                              sansFont=None,
                              channel_follows_focus=False,
                              scrollbars='off',
                              numImages=10,
                              # Offset to add to numpy-based coords
                              pixel_coords_offset=1.0,
                              # save primary header when loading files
                              save_primary_header=True,
                              inherit_primary_header=False,
                              cursor_interval=0.050,
                              download_folder=None,
                              save_layout=False,
                              channel_prefix="Image")
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

        self.tmpdir = tempfile.mkdtemp()
        # remove temporary directory on exit
        atexit.register(_rmtmpdir, self.tmpdir)

        # For callbacks
        for name in ('add-image', 'channel-change', 'remove-image',
                     'add-channel', 'delete-channel', 'field-info',
                     'add-image-info', 'remove-image-info'):
            self.enable_callback(name)

        # Initialize the timer factory
        self.timer_factory = Timer.TimerFactory(ev_quit=self.ev_quit,
                                                logger=self.logger)
        self.timer_factory.wind()

        self.lock = threading.RLock()
        self.channel = Bunch.caselessDict()
        self.channel_names = []
        self.cur_channel = None
        self.wscount = 0
        self.statustask = None
        self.preload_lock = threading.RLock()
        self.preload_list = deque([], 4)

        # Load bindings preferences
        bindprefs = self.prefs.create_category('bindings')
        bindprefs.load(onError='silent')

        self.plugins = []
        self._plugin_sort_method = self.get_plugin_menuname

        # some default colormap info
        self.cm = cmap.get_cmap("gray")
        self.im = imap.get_imap("ramp")

        # This plugin manager handles "global" (aka standard) plug ins
        # (unique instances, not per channel)
        self.gpmon = self.get_plugin_manager(self.logger, self,
                                             None, self.mm)

        # Initialize catalog and image server bank
        self.imgsrv = catalog.ServerBank(self.logger)

        # state for implementing field-info callback
        self._cursor_task = self.get_backend_timer()
        self._cursor_task.set_callback('expired', self._cursor_timer_cb)
        self._cursor_last_update = time.time()
        self.cursor_interval = self.settings.get('cursor_interval', 0.050)

        # add user preferred fonts for aliases, if present
        fixed_font = self.settings.get('fixedFont', None)
        if fixed_font is not None:
            font_asst.add_alias('fixed', fixed_font)

        serif_font = self.settings.get('serifFont', None)
        if serif_font is not None:
            font_asst.add_alias('serif', serif_font)

        sans_font = self.settings.get('sansFont', None)
        if sans_font is not None:
            font_asst.add_alias('sans', sans_font)

        # GUI initialization
        self.w = Bunch.Bunch()
        self.iconpath = icon_path
        self.main_wsname = None
        self._lastwsname = None
        self.ds = None
        self.layout = None
        self.layout_file = None
        self._lsize = None
        self._rsize = None

        self.filesel = None
        self.menubar = None
        self.gui_dialog_lock = threading.RLock()
        self.gui_dialog_list = []
        self.w.root = None
        # fullscreen viewer and top-level widget
        self.fs_viewer = None
        self.w.fscreen = None

        gviewer.register_viewer(Viewers.CanvasView)
        gviewer.register_viewer(Viewers.TableViewGw)
        gviewer.register_viewer(Viewers.PlotViewGw)

    def get_server_bank(self):
        return self.imgsrv

    def get_preferences(self):
        return self.prefs

    def get_timer(self):
        return self.timer_factory.timer()

    def get_backend_timer(self):
        return self.make_timer()

    def stop(self):
        self.logger.info("shutting down Ginga...")
        self.timer_factory.quit()
        self.ev_quit.set()
        self.logger.debug("should be exiting now")

    def reset_viewer(self):
        channel = self.get_current_channel()
        opmon = channel.opmon
        opmon.deactivate_focused()
        self.normalsize()

    def get_draw_class(self, drawtype):
        drawtype = drawtype.lower()
        return drawCatalog[drawtype]

    def get_draw_classes(self):
        return drawCatalog

    def make_async_gui_callback(self, name, *args, **kwargs):
        # NOTE: asynchronous!
        self.gui_do(self.make_callback, name, *args, **kwargs)

    def make_gui_callback(self, name, *args, **kwargs):
        if self.is_gui_thread():
            return self.make_callback(name, *args, **kwargs)
        else:
            # note: this cannot be "gui_call"--locks viewer.
            # so call becomes async when a non-gui thread invokes it
            self.gui_do(self.make_callback, name, *args, **kwargs)

    # PLUGIN MANAGEMENT

    def start_operation(self, opname):
        return self.start_local_plugin(None, opname, None)

    def start_local_plugin(self, chname, opname, future):
        channel = self.get_channel(chname)
        opmon = channel.opmon
        opmon.start_plugin_future(channel.name, opname, future)
        if hasattr(channel.viewer, 'onscreen_message'):
            channel.viewer.onscreen_message(opname, delay=1.0)

    def stop_local_plugin(self, chname, opname):
        channel = self.get_channel(chname)
        opmon = channel.opmon
        opmon.deactivate(opname)

    def call_local_plugin_method(self, chname, plugin_name, method_name,
                                 args, kwargs):
        """
        Parameters
        ----------
        chname : str
            The name of the channel containing the plugin.

        plugin_name : str
            The name of the local plugin containing the method to call.

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
        channel = self.get_channel(chname)
        opmon = channel.opmon
        p_obj = opmon.get_plugin(plugin_name)
        method = getattr(p_obj, method_name)
        return self.gui_call(method, *args, **kwargs)

    def start_global_plugin(self, plugin_name, raise_tab=False):
        self.gpmon.start_plugin_future(None, plugin_name, None)
        if raise_tab:
            pInfo = self.gpmon.get_plugin_info(plugin_name)
            self.ds.raise_tab(pInfo.tabname)

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
        ptype = spec.get('ptype', 'local')
        if ptype == 'local':
            self.start_operation(plugin_name)
        else:
            self.start_global_plugin(plugin_name, raise_tab=True)

    def add_local_plugin(self, spec):
        try:
            spec.setdefault('ptype', 'local')
            name = spec.setdefault('name', spec.get('klass', spec.module))

            pfx = spec.get('pfx', pluginconfpfx)
            path = spec.get('path', None)
            self.mm.load_module(spec.module, pfx=pfx, path=path)
            self.plugins.append(spec)

        except Exception as e:
            self.logger.error("Unable to load local plugin '%s': %s" % (
                name, str(e)))

    def add_global_plugin(self, spec):
        try:
            spec.setdefault('ptype', 'global')
            name = spec.setdefault('name', spec.get('klass', spec.module))

            pfx = spec.get('pfx', pluginconfpfx)
            path = spec.get('path', None)
            self.mm.load_module(spec.module, pfx=pfx, path=path)
            self.plugins.append(spec)

            self.gpmon.load_plugin(name, spec)

        except Exception as e:
            self.logger.error("Unable to load global plugin '%s': %s" % (
                name, str(e)))

    def add_plugin(self, spec):
        if not spec.get('enabled', True):
            return
        ptype = spec.get('ptype', 'local')
        if ptype == 'global':
            self.add_global_plugin(spec)
        else:
            self.add_local_plugin(spec)

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
            hidden = spec.get('hidden', False)
            if not hidden:
                self.add_plugin_menu(name, spec)

            start = spec.get('start', True)
            # for now only start global plugins that have start==True
            # channels are not yet created by this time
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

        This method will convert the text as necessary with docutils and
        display it in the WBrowser plugin, if available.  If the plugin is
        not available and the text is type 'rst' then the text will be
        displayed in a plain text widget.

        Parameters
        ----------
        name : str
            Category of help to show.

        text : str
            The text to show.  Should be plain, HTML or RST text

        text_kind : str (optional)
            One of 'plain', 'html', 'rst'.  Default is 'plain'.

        trim_pfx : int (optional)
            Number of spaces to trim off the beginning of each line of text.

        """

        if trim_pfx > 0:
            # caller wants to trim some space off the front
            # of each line
            text = toolbox.trim_prefix(text, trim_pfx)

        if text_kind == 'rst':
            # try to convert RST to HTML using docutils
            try:
                overrides = {'input_encoding': 'ascii',
                             'output_encoding': 'utf-8'}
                text_html = publish_string(text, writer_name='html',
                                           settings_overrides=overrides)
                # docutils produces 'bytes' output, but webkit needs
                # a utf-8 string
                text = text_html.decode('utf-8')
                text_kind = 'html'

            except Exception as e:
                self.logger.error("Error converting help text to HTML: %s" % (
                    str(e)))
                # revert to showing RST as plain text

        else:
            raise ValueError(
                "I don't know how to display text of kind '%s'" % (text_kind))

        if text_kind == 'html':
            self.help(text=text, text_kind='html')

        else:
            self.show_help_text(name, text)

    def help(self, text=None, text_kind='url'):

        if not self.gpmon.has_plugin('WBrowser'):
            return self.show_error("help() requires 'WBrowser' plugin")

        self.start_global_plugin('WBrowser')

        # need to let GUI finish processing, it seems
        self.update_pending()

        obj = self.gpmon.get_plugin('WBrowser')

        if text is not None:
            if text_kind == 'url':
                obj.browse(text)
            else:
                obj.browse(text, url_is_content=True)
        else:
            obj.show_help()

    def show_help_text(self, name, help_txt, wsname='right'):
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

    # BASIC IMAGE OPERATIONS

    def load_image(self, filespec, idx=None, show_error=True):
        """
        A wrapper around ginga.util.loader.load_data()

        Parameters
        ----------
        filespec : str
            The path of the file to load (must reference a single file).

        idx : str, int or tuple; optional, defaults to None
            The index of the image to open within the file.

        show_error : bool, optional, defaults to True
            If `True`, then display an error in the GUI if the file
            loading process fails.

        Returns
        -------
        data_obj : data object named by filespec
        """
        save_prihdr = self.settings.get('save_primary_header', False)
        inherit_prihdr = self.settings.get('inherit_primary_header', False)
        try:
            data_obj = loader.load_data(filespec, logger=self.logger,
                                        idx=idx,
                                        save_primary_header=save_prihdr,
                                        inherit_primary_header=inherit_prihdr)
        except Exception as e:
            errmsg = "Failed to load file '%s': %s" % (
                filespec, str(e))
            self.logger.error(errmsg)
            try:
                (type, value, tb) = sys.exc_info()
                tb_str = "\n".join(traceback.format_tb(tb))
            except Exception as e:
                tb_str = "Traceback information unavailable."
            if show_error:
                self.gui_do(self.show_error, errmsg + '\n' + tb_str)
            raise ControlError(errmsg)

        self.logger.debug("Successfully loaded file into object.")
        return data_obj

    def load_file(self, filepath, chname=None, wait=True,
                  create_channel=True, display_image=True,
                  image_loader=None):
        """Load a file and display it.

        Parameters
        ----------
        filepath : str
            The path of the file to load (must reference a local file).

        chname : str, optional
            The name of the channel in which to display the image.

        wait : bool, optional
            If `True`, then wait for the file to be displayed before returning
            (synchronous behavior).

        create_channel : bool, optional
            Create channel.

        display_image : bool, optional
            If not `False`, then will load the image.

        image_loader : func, optional
            A special image loader, if provided.

        Returns
        -------
        image
            The image object that was loaded.

        """
        if not chname:
            channel = self.get_current_channel()
        else:
            if not self.has_channel(chname) and create_channel:
                self.gui_call(self.add_channel, chname)
            channel = self.get_channel(chname)
        chname = channel.name

        if image_loader is None:
            image_loader = self.load_image

        cache_dir = self.settings.get('download_folder', self.tmpdir)

        info = iohelper.get_fileinfo(filepath, cache_dir=cache_dir)

        # check that file is locally accessible
        if not info.ondisk:
            errmsg = "File must be locally loadable: %s" % (filepath)
            self.gui_do(self.show_error, errmsg)
            return

        filepath = info.filepath

        kwargs = {}
        idx = None
        if info.numhdu is not None:
            kwargs['idx'] = info.numhdu

        try:
            image = image_loader(filepath, **kwargs)

        except Exception as e:
            errmsg = "Failed to load '%s': %s" % (filepath, str(e))
            self.gui_do(self.show_error, errmsg)
            return

        future = Future.Future()
        future.freeze(image_loader, filepath, **kwargs)

        # Save a future for this image to reload it later if we
        # have to remove it from memory
        image.set(loader=image_loader, image_future=future)

        if image.get('path', None) is None:
            image.set(path=filepath)

        # Assign a name to the image if the loader did not.
        name = image.get('name', None)
        if name is None:
            name = iohelper.name_image_from_path(filepath, idx=idx)
            image.set(name=name)

        if display_image:
            # Display image.  If the wait parameter is False then don't wait
            # for the image to load into the viewer
            if wait:
                self.gui_call(self.add_image, name, image, chname=chname)
            else:
                self.gui_do(self.add_image, name, image, chname=chname)
        else:
            self.gui_do(self.bulk_add_image, name, image, chname)

        # Return the image
        return image

    def add_download(self, info, future):
        """
        Hand off a download to the Downloads plugin, if it is present.

        Parameters
        ----------
        info : `~ginga.misc.Bunch.Bunch`
            A bunch of information about the URI as returned by
            `ginga.util.iohelper.get_fileinfo()`

        future : `~ginga.misc.Future.Future`
            A future that represents the future computation to be performed
            after downloading the file.  Resolving the future will trigger
            the computation.
        """
        if self.gpmon.has_plugin('Downloads'):
            obj = self.gpmon.get_plugin('Downloads')
            self.gui_do(obj.add_download, info, future)
        else:
            self.show_error("Please activate the 'Downloads' plugin to"
                            " enable download functionality")

    def open_uri_cont(self, filespec, loader_cont_fn):
        """Download a URI (if necessary) and do some action on it.

        If the file is already present (e.g. a file:// URI) then this
        merely confirms that and invokes the continuation.

        Parameters
        ----------
        filespec : str
            The path of the file to load (can be a non-local URI)

        loader_cont_fn : func (str) -> None
            A continuation consisting of a function of one argument
            that does something with the file once it is downloaded
            The parameter is the local filepath after download, plus
            any "index" understood by the loader.

        """
        info = iohelper.get_fileinfo(filespec)

        # download file if necessary
        if ((not info.ondisk) and (info.url is not None) and
                (not info.url.startswith('file:'))):
            # create up a future to do the download and set up a
            # callback to handle it when finished
            def _download_cb(future):
                filepath = future.get_value(block=False)
                self.logger.debug("downloaded: %s" % (filepath))
                self.gui_do(loader_cont_fn, filepath + info.idx)

            future = Future.Future()
            future.add_callback('resolved', _download_cb)
            self.add_download(info, future)
            return

        # invoke the continuation
        loader_cont_fn(info.filepath + info.idx)

    def open_file_cont(self, pathspec, loader_cont_fn):
        """Open a file and do some action on it.

        Parameters
        ----------
        pathspec : str
            The path of the file to load (can be a URI, but must reference
            a local file).

        loader_cont_fn : func (data_obj) -> None
            A continuation consisting of a function of one argument
            that does something with the data_obj created by the loader

        """
        self.assert_nongui_thread()

        info = iohelper.get_fileinfo(pathspec)

        filepath = info.filepath

        if not os.path.exists(filepath):
            errmsg = "File does not appear to exist: '%s'" % (filepath)
            self.gui_do(self.show_error, errmsg)
            return

        warnmsg = ""
        try:
            typ, subtyp = iohelper.guess_filetype(filepath)

        except Exception as e:
            warnmsg = "Couldn't determine file type of '{0:}': " \
                      "{1:}".format(filepath, str(e))
            self.logger.warning(warnmsg)
            typ = None

        def _open_file(opener_class):
            # kwd args to pass to opener
            kwargs = dict()
            save_prihdr = self.settings.get('save_primary_header', False)
            kwargs['save_primary_header'] = save_prihdr
            inherit_prihdr = self.settings.get('inherit_primary_header', False)
            kwargs['inherit_primary_header'] = inherit_prihdr

            # open the file and load the items named by the index
            opener = opener_class(self.logger)
            try:
                with opener.open_file(filepath) as io_f:
                    io_f.load_idx_cont(info.idx, loader_cont_fn, **kwargs)

            except Exception as e:
                errmsg = "Error opening '%s': %s" % (filepath, str(e))
                try:
                    (_type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))
                except Exception as e:
                    tb_str = "Traceback information unavailable."
                self.gui_do(self.show_error, errmsg + '\n' + tb_str)

        def _check_open(errmsg):
            if typ is None:
                errmsg = ("Error determining file type: {0:}\n"
                          "\nPlease choose an opener or cancel, for file:\n"
                          "{1:}".format(errmsg, filepath))
                openers = loader.get_all_openers()
                self.gui_do(self.gui_choose_file_opener, errmsg, openers,
                            _open_file, None, filepath)

            else:
                mimetype = "{}/{}".format(typ, subtyp)
                openers = loader.get_openers(mimetype)

                num_openers = len(openers)
                if num_openers == 1:
                    opener_class = openers[0].opener
                    self.nongui_do(_open_file, opener_class)
                    self.__next_dialog()

                elif num_openers == 0:
                    errmsg = ("No registered opener for: '{0:}'\n"
                              "\nPlease choose an opener or cancel, for file:\n"
                              "{1:}".format(mimetype, filepath))
                    openers = loader.get_all_openers()
                    self.gui_do(self.gui_choose_file_opener, errmsg, openers,
                                _open_file, mimetype, filepath)

                else:
                    errmsg = ("Multiple registered openers for: '{0:}'\n"
                              "\nPlease choose an opener or cancel, for file:\n"
                              "{1:}".format(mimetype, filepath))
                    self.gui_do(self.gui_choose_file_opener, errmsg, openers,
                                _open_file, '*', filepath)

        future = Future.Future()
        future.freeze(_check_open, warnmsg)

        with self.gui_dialog_lock:
            self.gui_dialog_list.append(future)
            if len(self.gui_dialog_list) == 1:
                self.nongui_do_future(future)

    def open_uris(self, uris, chname=None, bulk_add=False):
        """Open a set of URIs.

        Parameters
        ----------
        uris : list of str
            The URIs of the files to load

        chname: str, optional (defaults to channel with focus)
            The name of the channel in which to load the items

        bulk_add : bool, optional (defaults to False)
            If True, then all the data items are loaded into the
            channel without disturbing the current item there.
            If False, then the first item loaded will be displayed
            and the rest of the items will be loaded as bulk.

        """
        if len(uris) == 0:
            return

        if chname is None:
            channel = self.get_channel_info()
            if channel is None:
                # No active channel to load these into
                return
            chname = channel.name
        channel = self.get_channel_on_demand(chname)

        def show_dataobj_bulk(data_obj):
            self.gui_do(channel.add_image, data_obj, bulk_add=True)

        def load_file_bulk(filepath):
            self.nongui_do(self.open_file_cont, filepath, show_dataobj_bulk)

        def show_dataobj(data_obj):
            self.gui_do(channel.add_image, data_obj, bulk_add=False)

        def load_file(filepath):
            self.nongui_do(self.open_file_cont, filepath, show_dataobj)

        # determine whether first file is loaded as a bulk load
        if bulk_add:
            self.open_uri_cont(uris[0], load_file_bulk)
        else:
            self.open_uri_cont(uris[0], load_file)
        self.update_pending()

        for uri in uris[1:]:
            # rest of files are all loaded using bulk load
            self.open_uri_cont(uri, load_file_bulk)
            self.update_pending()

    def add_preload(self, chname, image_info):
        bnch = Bunch.Bunch(chname=chname, info=image_info)
        with self.preload_lock:
            self.preload_list.append(bnch)
        self.nongui_do(self.preload_scan)

    def preload_scan(self):
        # preload any pending files
        # TODO: do we need any throttling of loading here?
        with self.preload_lock:
            while len(self.preload_list) > 0:
                bnch = self.preload_list.pop()
                self.nongui_do(self.preload_file, bnch.chname,
                               bnch.info.name, bnch.info.path,
                               image_future=bnch.info.image_future)

    def preload_file(self, chname, imname, path, image_future=None):
        # sanity check to see if the file is already in memory
        self.logger.debug("preload: checking %s in %s" % (imname, chname))
        channel = self.get_channel(chname)

        if imname not in channel.datasrc:
            # not there--load image in a non-gui thread, then have the
            # gui add it to the channel silently
            self.logger.info("preloading image %s" % (path))
            if image_future is None:
                # TODO: need index info?
                image = self.load_image(path)
            else:
                image = image_future.thaw()

            self.gui_do(self.add_image, imname, image,
                        chname=chname, silent=True)
        self.logger.debug("end preload")

    def zoom_in(self):
        """Zoom the view in one zoom step.
        """
        viewer = self.getfocus_viewer()
        if hasattr(viewer, 'zoom_in'):
            viewer.zoom_in()
        return True

    def zoom_out(self):
        """Zoom the view out one zoom step.
        """
        viewer = self.getfocus_viewer()
        if hasattr(viewer, 'zoom_out'):
            viewer.zoom_out()
        return True

    def zoom_1_to_1(self):
        """Zoom the view to a 1 to 1 pixel ratio (100 %%).
        """
        viewer = self.getfocus_viewer()
        if hasattr(viewer, 'scale_to'):
            viewer.scale_to(1.0, 1.0)
        return True

    def zoom_fit(self):
        """Zoom the view to fit the image entirely in the window.
        """
        viewer = self.getfocus_viewer()
        if hasattr(viewer, 'zoom_fit'):
            viewer.zoom_fit()
        return True

    def auto_levels(self):
        """Perform an auto cut levels on the image.
        """
        viewer = self.getfocus_viewer()
        if hasattr(viewer, 'auto_levels'):
            viewer.auto_levels()

    def prev_img_ws(self, ws, loop=True):
        """Go to the previous image in the focused channel in the workspace.
        """
        channel = self.get_active_channel_ws(ws)
        if channel is None:
            return
        channel.prev_image()
        return True

    def next_img_ws(self, ws, loop=True):
        """Go to the next image in the focused channel in the workspace.
        """
        channel = self.get_active_channel_ws(ws)
        if channel is None:
            return
        channel.next_image()
        return True

    def prev_img(self, loop=True):
        """Go to the previous image in the channel.
        """
        channel = self.get_current_channel()
        if channel is None:
            self.show_error("Please create a channel.", raisetab=True)
            return
        channel.prev_image()
        return True

    def next_img(self, loop=True):
        """Go to the next image in the channel.
        """
        channel = self.get_current_channel()
        if channel is None:
            self.show_error("Please create a channel.", raisetab=True)
            return
        channel.next_image()
        return True

    def get_current_workspace(self):
        channel = self.get_channel_info()
        if channel is None:
            return None
        ws = self.ds.get_ws(channel.workspace)
        return ws

    def get_active_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            return None
        # Not exactly the most robust or straightforward way to find the
        # active channel in this workspace...
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title
        if self.has_channel(chname):
            return self.get_channel(chname)
        return None

    def prev_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace.",
                            raisetab=True)
            return

        ws.to_previous()

        channel = self.get_active_channel_ws(ws)
        if (channel is not None) and self.has_channel(channel.name):
            self.change_channel(channel.name, raisew=True)

    def next_channel_ws(self, ws):
        children = list(ws.nb.get_children())
        if len(children) == 0:
            self.show_error("No channels in this workspace.",
                            raisetab=True)
            return

        ws.to_next()

        channel = self.get_active_channel_ws(ws)
        if (channel is not None) and self.has_channel(channel.name):
            self.change_channel(channel.name, raisew=True)

    def prev_channel(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return
        self.prev_channel_ws(ws)

    def next_channel(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return
        self.next_channel_ws(ws)

    def add_channel_auto_ws(self, ws):
        if ws.toolbar is not None:
            chname = ws.extdata.w_chname.get_text().strip()
        else:
            chname = ''
        if len(chname) == 0:
            # make up a channel name
            chpfx = self.settings.get('channel_prefix', "Image")
            chpfx = ws.extdata.get('chpfx', chpfx)
            chname = chpfx

        if self.has_channel(chname):
            chname = self.make_channel_name(chname)

        try:
            self.get_channel(chname)
            # <-- channel name already in use
            self.show_error(
                "Channel name '%s' cannot be used, sorry." % (chname),
                raisetab=True)
            return

        except KeyError:
            pass

        return self.add_channel(chname, workspace=ws.name)

    def add_channel_auto(self):
        ws = self.get_current_workspace()
        if ws is None:
            self.show_error("Please select or create a workspace",
                            raisetab=True)
            return

        return self.add_channel_auto_ws(ws)

    def remove_channel_auto(self):
        channel = self.get_channel_info()
        if channel is None:
            return
        self.delete_channel(channel.name)

    def configure_workspace(self, wstype):
        ws = self.get_current_workspace()
        ws.configure_wstype(wstype)

    def cycle_workspace_type(self):
        ws = self.get_current_workspace()
        ws.cycle_wstype()

    def add_workspace(self, wsname, wstype, inSpace=None):
        if inSpace is None:
            inSpace = self.main_wsname

        if wsname in self.ds.get_tabnames(None):
            raise ValueError("Tab name already in use: '%s'" % (wsname))

        ws = self.ds.make_ws(name=wsname, group=1, wstype=wstype,
                             use_toolbar=True)
        if inSpace != 'top level':
            self.ds.add_tab(inSpace, ws.widget, 1, ws.name)
        else:
            #width, height = 700, 800
            #self.ds.create_toplevel_ws(width, height, group=1)
            top_w = self.ds.add_toplevel(ws, ws.name)
            ws.extdata.top_w = top_w

        return ws

    # CHANNEL MANAGEMENT

    def add_image(self, imname, image, chname=None, silent=False):
        if chname is None:
            channel = self.get_current_channel()
            if channel is None:
                raise ValueError("Need to provide a channel name to add "
                                 "the image")
            chname = channel.name

        # add image to named channel
        channel = self.get_channel_on_demand(chname)
        channel.add_image(image, silent=silent)

    def advertise_image(self, chname, image):
        channel = self.get_channel(chname)
        info = channel.get_image_info(image.get('name'))

        self.make_gui_callback('add-image', chname, image, info)

    def update_image_info(self, image, info):
        for chname in self.get_channel_names():
            channel = self.get_channel(chname)
            channel.update_image_info(image, info)

    def bulk_add_image(self, imname, image, chname):
        channel = self.get_channel_on_demand(chname)
        channel.add_image(image, bulk_add=True)

    def get_image(self, chname, imname):
        channel = self.get_channel(chname)
        if channel is None:
            return None
        return channel.get_loaded_image(imname)

    def getfocus_viewer(self):
        channel = self.get_current_channel()
        if channel is None:
            return None
        return channel.viewer

    def get_viewer(self, chname):
        channel = self.get_channel(chname)
        if channel is None:
            return None
        return channel.viewer

    def switch_name(self, chname, imname, path=None,
                    image_future=None):
        try:
            # create channel if it doesn't exist already
            channel = self.get_channel_on_demand(chname)
            channel.switch_name(imname)

            self.change_channel(channel.name)
        except Exception as e:
            self.show_error("Couldn't switch to image '%s': %s" % (
                str(imname), str(e)), raisetab=True)

    def redo_plugins(self, image, channel):
        if image is not None:
            imname = image.get('name', None)
            if (imname is not None) and (imname not in channel):
                # image may have been removed--
                # skip updates to this channel's plugins
                return

        # New data in channel
        # update active global plugins
        opmon = self.gpmon
        for key in opmon.get_active():
            obj = opmon.get_plugin(key)
            try:
                if image is None:
                    self.gui_do(obj.blank, channel)
                else:
                    self.gui_do(obj.redo, channel, image)

            except Exception as e:
                self.logger.error(
                    "Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

        # update active local plugins
        opmon = channel.opmon
        for key in opmon.get_active():
            obj = opmon.get_plugin(key)
            try:
                if image is None:
                    self.gui_do(obj.blank)
                else:
                    self.gui_do(obj.redo)

            except Exception as e:
                self.logger.error(
                    "Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

    def close_plugins(self, channel):
        """Close all plugins associated with the channel."""
        opmon = channel.opmon
        for key in opmon.get_active():
            obj = opmon.get_plugin(key)
            try:
                self.gui_call(obj.close)

            except Exception as e:
                self.logger.error(
                    "Failed to continue operation: %s" % (str(e)))
                # TODO: log traceback?

    def channel_image_updated(self, channel, image):

        with self.lock:
            self.logger.debug("Update image start")
            start_time = time.time()

            # add cb so that if image is modified internally
            #  our plugins get updated
            if image is not None:
                image.add_callback('modified', self.redo_plugins, channel)

            self.logger.debug("executing redo() in plugins...")
            self.redo_plugins(image, channel)

            split_time1 = time.time()
            self.logger.info("Channel image update: %.4f sec" % (
                split_time1 - start_time))

    def change_channel(self, chname, image=None, raisew=True):
        self.logger.debug("change channel: %s" % (chname))
        name = chname.lower()
        if self.cur_channel is None:
            oldchname = None
        else:
            oldchname = self.cur_channel.name.lower()

        channel = self.get_channel(name)

        if name != oldchname:
            with self.lock:
                self.cur_channel = channel

        if name != oldchname:
            # raise tab
            if raisew:
                #self.ds.raise_tab(channel.workspace)
                self.ds.raise_tab(name)

            if oldchname is not None:
                try:
                    self.ds.highlight_tab(oldchname, False)
                except Exception:
                    # old channel may not exist!
                    pass
            self.ds.highlight_tab(name, True)

            ## # Update title bar
            title = channel.name
            ## if image is not None:
            ##     name = image.get('name', 'Noname')
            ##     title += ": %s" % (name)
            self.set_titlebar(title)

        if image is not None:
            try:
                channel.switch_image(image)

            except Exception as e:
                self.show_error("Error viewing data object: {}".format(e),
                                raisetab=True)

        self.make_gui_callback('channel-change', channel)

        self.update_pending()
        return True

    def has_channel(self, chname):
        with self.lock:
            return chname in self.channel

    def get_channel(self, chname):
        with self.lock:
            if chname is None:
                return self.cur_channel
            return self.channel[chname]

    def get_channel_info(self, chname=None):
        # TO BE DEPRECATED--please use get_channel() or get_current_channel()
        return self.get_channel(chname)

    def get_current_channel(self):
        with self.lock:
            return self.cur_channel

    def get_channel_on_demand(self, chname):
        if self.has_channel(chname):
            return self.get_channel(chname)

        return self.gui_call(self.add_channel, chname)

    def get_channel_name(self, viewer):
        with self.lock:
            items = self.channel.items()
        for name, channel in items:
            if viewer in channel.viewers:
                return channel.name
        return None

    def make_channel_name(self, pfx):
        i = 0
        while i < 10000:
            chname = pfx + str(i)
            if not self.has_channel(chname):
                return chname
            i += 1
        return pfx + str(time.time())

    def add_channel(self, chname, workspace=None,
                    num_images=None, settings=None,
                    settings_template=None,
                    settings_share=None, share_keylist=None):
        """Create a new Ginga channel.

        Parameters
        ----------
        chname : str
            The name of the channel to create.

        workspace : str or None
            The name of the workspace in which to create the channel

        num_images : int or None
            The cache size for the number of images to keep in memory

        settings : `~ginga.misc.Settings.SettingGroup` or `None`
            Viewer preferences. If not given, one will be created.

        settings_template : `~ginga.misc.Settings.SettingGroup` or `None`
            Viewer preferences template

        settings_share : `~ginga.misc.Settings.SettingGroup` or `None`
            Viewer preferences instance to share with newly created settings

        share_keylist : list of str
            List of names of settings that should be shared

        Returns
        -------
        channel : `~ginga.misc.Bunch.Bunch`
            The channel info bunch.

        """
        with self.lock:
            if self.has_channel(chname):
                return self.get_channel(chname)

            if chname in self.ds.get_tabnames(None):
                raise ValueError("Tab name already in use: '%s'" % (chname))

            name = chname
            if settings is None:
                settings = self.prefs.create_category('channel_' + name)
                try:
                    settings.load(onError='raise')

                except Exception as e:
                    self.logger.info("no saved preferences found for channel "
                                     "'%s', using default: %s" % (name, str(e)))

                    # copy template settings to new channel
                    if settings_template is not None:
                        osettings = settings_template
                        osettings.copy_settings(settings)
                    else:
                        try:
                            # use channel_Image as a template if one was not
                            # provided
                            osettings = self.prefs.get_settings('channel_Image')
                            self.logger.debug("Copying settings from 'Image' to "
                                              "'%s'" % (name))
                            osettings.copy_settings(settings)
                        except KeyError:
                            pass

            if (share_keylist is not None) and (settings_share is not None):
                # caller wants us to share settings with another viewer
                settings_share.share_settings(settings, keylist=share_keylist)

            # Make sure these preferences are at least defined
            if num_images is None:
                num_images = settings.get('numImages',
                                          self.settings.get('numImages', 1))
            settings.set_defaults(switchnew=True, numImages=num_images,
                                  raisenew=True, genthumb=True,
                                  focus_indicator=False,
                                  preload_images=False, sort_order='loadtime')

            self.logger.debug("Adding channel '%s'" % (chname))
            channel = Channel(chname, self, datasrc=None,
                              settings=settings)

            bnch = self.add_viewer(chname, settings,
                                   workspace=workspace)
            # for debugging
            bnch.image_viewer.set_name('channel:%s' % (chname))

            opmon = self.get_plugin_manager(self.logger, self,
                                            self.ds, self.mm)

            channel.widget = bnch.widget
            channel.container = bnch.container
            channel.workspace = bnch.workspace
            channel.connect_viewer(bnch.image_viewer)
            channel.viewer = bnch.image_viewer
            # older name, should eventually be deprecated
            channel.fitsimage = bnch.image_viewer
            channel.opmon = opmon

            name = chname.lower()
            self.channel[name] = channel

            # Update the channels control
            self.channel_names.append(chname)
            self.channel_names.sort()

            if len(self.channel_names) == 1:
                self.cur_channel = channel

            # Prepare local plugins for this channel
            for spec in self.get_plugins():
                opname = spec.get('klass', spec.get('module'))
                if spec.get('ptype', 'global') == 'local':
                    opmon.load_plugin(opname, spec, chinfo=channel)

            self.make_gui_callback('add-channel', channel)
            return channel

    def delete_channel(self, chname):
        """Delete a given channel from viewer."""
        name = chname.lower()

        if len(self.channel_names) < 1:
            self.logger.error('Delete channel={0} failed. '
                              'No channels left.'.format(chname))
            return

        with self.lock:
            channel = self.channel[name]

            # Close local plugins open on this channel
            self.close_plugins(channel)

            try:
                idx = self.channel_names.index(chname)
            except ValueError:
                idx = 0

            # Update the channels control
            self.channel_names.remove(channel.name)
            self.channel_names.sort()

            self.ds.remove_tab(chname)
            del self.channel[name]
            self.prefs.remove_settings('channel_' + chname)

            # pick new channel
            num_channels = len(self.channel_names)
            if num_channels > 0:
                if idx >= num_channels:
                    idx = num_channels - 1
                self.change_channel(self.channel_names[idx])
            else:
                self.cur_channel = None

        self.make_gui_callback('delete-channel', channel)

    def get_channel_names(self):
        with self.lock:
            return self.channel_names

    def scale2text(self, scalefactor):
        if scalefactor >= 1.0:
            text = '%.2fx' % (scalefactor)
        else:
            text = '1/%.2fx' % (1.0 / scalefactor)
        return text

    def banner(self, raiseTab=False):
        banner_file = os.path.join(self.iconpath, 'ginga-splash.ppm')
        chname = 'Ginga'
        channel = self.get_channel_on_demand(chname)
        viewer = channel.viewer
        viewer.enable_autocuts('off')
        viewer.enable_autozoom('off')
        viewer.enable_autocenter('on')
        viewer.cut_levels(0, 255)
        viewer.scale_to(1, 1)

        image = self.load_file(banner_file, chname=chname, wait=True)

        # Insert Ginga version info
        header = image.get_header()
        header['VERSION'] = __version__

        if raiseTab:
            self.change_channel(chname)

    def remove_image_by_name(self, chname, imname, impath=None):
        channel = self.get_channel(chname)
        viewer = channel.viewer
        self.logger.info("removing image %s" % (imname))
        # If this is the current image in the viewer, clear the viewer
        image = viewer.get_image()
        if image is not None:
            curname = image.get('name', 'NONAME')
            if curname == imname:
                viewer.clear()

        channel.remove_image(imname)

    def move_image_by_name(self, from_chname, imname, to_chname, impath=None):

        channel_from = self.get_channel(from_chname)
        channel_to = self.get_channel(to_chname)
        channel_from.move_image_to(imname, channel_to)

    def remove_current_image(self):
        channel = self.get_current_channel()
        viewer = channel.viewer
        image = viewer.get_image()
        if image is None:
            return
        imname = image.get('name', 'NONAME')
        impath = image.get('path', None)
        self.remove_image_by_name(channel.name, imname, impath=impath)

    def follow_focus(self, tf):
        self.settings['channel_follows_focus'] = tf

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

    def play_soundfile(self, filepath, format=None, priority=20):
        self.logger.debug("Subclass could override this to play sound file "
                          "'%s'" % (filepath))

    def get_color_maps(self):
        """Get the list of named color maps.

        Returns
        -------
        names : list
            A list of all named colormaps installed.

        """
        return cmap.get_names()

    def get_intensity_maps(self):
        """Get the list of named intensity maps.

        Returns
        -------
        names : list
            A list of all named intensity maps installed.

        """
        return imap.get_names()

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

        self.font = self.get_font('fixed', 12)
        self.font11 = self.get_font('fixed', 11)
        self.font14 = self.get_font('fixed', 14)
        self.font18 = self.get_font('fixed', 18)

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

        for win in self.ds.toplevels:
            # add delete/destroy callbacks
            win.add_callback('close', self.quit)
            win.set_title("Ginga")
            root = win
        self.ds.add_callback('all-closed', self.quit)

        self.w.root = root
        self.w.fscreen = None

        # get informed about window closures in existing workspaces
        for wsname in self.ds.get_wsnames():
            ws = self.ds.get_ws(wsname)
            self.init_workspace(ws)

        if 'menu' in self.w:
            menuholder = self.w['menu']
            self.w.menubar = self.add_menus(menuholder)

        self.add_dialogs()

        if 'status' in self.w:
            statusholder = self.w['status']
            self.add_statusbar(statusholder)

        self.w.root.show()

    def get_plugin_manager(self, logger, fitsview, ds, mm):
        return PluginManager.PluginManager(logger, fitsview, ds, mm)

    def _name_mangle(self, name, pfx=''):
        newname = []
        for c in name.lower():
            if not (c.isalpha() or c.isdigit() or (c == '_')):
                newname.append('_')
            else:
                newname.append(c)
        return pfx + ''.join(newname)

    def add_menus(self, holder):

        menubar = Widgets.Menubar()
        self.menubar = menubar

        # NOTE: Special hack for Mac OS X. From the Qt documentation:
        # "If you want all windows in a Mac application to share one
        #  menu bar, you must create a menu bar that does not have a
        #  parent."
        macos_ver = platform.mac_ver()[0]
        if len(macos_ver) > 0:
            pass
        else:
            holder.add_widget(menubar, stretch=1)

        # create a File pulldown menu, and add it to the menu bar
        filemenu = menubar.add_name("File")

        item = filemenu.add_name("Load Image")
        item.add_callback('activated', lambda *args: self.gui_load_file())

        item = filemenu.add_name("Remove Image")
        item.add_callback("activated",
                          lambda *args: self.remove_current_image())

        filemenu.add_separator()

        item = filemenu.add_name("Quit")
        item.add_callback('activated', lambda *args: self.window_close())

        # create a Channel pulldown menu, and add it to the menu bar
        chmenu = menubar.add_name("Channel")

        item = chmenu.add_name("Add Channel")
        item.add_callback('activated', lambda *args: self.gui_add_channel())

        item = chmenu.add_name("Add Channels")
        item.add_callback('activated', lambda *args: self.gui_add_channels())

        item = chmenu.add_name("Delete Channel")
        item.add_callback('activated', lambda *args: self.gui_delete_channel())

        # create a Window pulldown menu, and add it to the menu bar
        wsmenu = menubar.add_name("Workspace")

        item = wsmenu.add_name("Add Workspace")
        item.add_callback('activated', lambda *args: self.gui_add_ws())

        # # create a Option pulldown menu, and add it to the menu bar
        # optionmenu = menubar.add_name("Option")

        # create a Plugins pulldown menu, and add it to the menu bar
        plugmenu = menubar.add_name("Plugins")
        self.w.menu_plug = plugmenu

        # create a Help pulldown menu, and add it to the menu bar
        helpmenu = menubar.add_name("Help")

        item = helpmenu.add_name("About")
        item.add_callback('activated',
                          lambda *args: self.banner(raiseTab=True))

        item = helpmenu.add_name("Documentation")
        item.add_callback('activated', lambda *args: self.help())

        return menubar

    def add_menu(self, name):
        """Add a menu with name `name` to the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.add_name(name)

    def get_menu(self, name):
        """Get the menu with name `name` from the global menu bar.
        Returns a menu widget.
        """
        if self.menubar is None:
            raise ValueError("No menu bar configured")
        return self.menubar.get_menu(name)

    def add_dialogs(self):
        if hasattr(GwHelp, 'FileSelection'):
            self.filesel = GwHelp.FileSelection(self.w.root.get_widget(),
                                                all_at_once=True)

    def add_plugin_menu(self, name, spec):
        # NOTE: self.w.menu_plug is a ginga.Widgets wrapper
        if 'menu_plug' not in self.w:
            return
        category = spec.get('category', None)
        categories = None
        if category is not None:
            categories = category.split('.')
        menuname = spec.get('menu', spec.get('tab', name))

        menu = self.w.menu_plug
        if categories is not None:
            for catname in categories:
                try:
                    menu = menu.get_menu(catname)
                except KeyError:
                    menu = menu.add_menu(catname)

        item = menu.add_name(menuname)
        item.add_callback('activated',
                          lambda *args: self.start_plugin(name, spec))

    def add_statusbar(self, holder):
        self.w.status = Widgets.StatusBar()
        holder.add_widget(self.w.status, stretch=1)

    def fullscreen(self):
        self._fullscreen_off()
        self.w.root.fullscreen()

    def normalsize(self):
        self._fullscreen_off()
        self.w.root.unfullscreen()

    def maximize(self):
        self._fullscreen_off()

        if self.w.root.is_maximized():
            self.w.root.unmaximize()
        else:
            self.w.root.maximize()

    def toggle_fullscreen(self):
        self._fullscreen_off()

        if not self.w.root.is_fullscreen():
            self.w.root.fullscreen()
        else:
            self.w.root.unfullscreen()

    def build_fullscreen(self):
        if self.w.fscreen is None:
            self.build_fullscreen_viewer()
        else:
            # viewer has been built already. If visible, toggle it
            if self.w.fscreen.is_visible():
                self._fullscreen_off()
                return

        self.w.fscreen.show()
        self.w.fscreen.fullscreen()
        self.w.fscreen.raise_()

        # Get image from current focused channel
        channel = self.get_current_channel()
        viewer = channel.fitsimage

        # Get canvas from current focused channel
        canvas = viewer.get_canvas()
        if canvas is None:
            return
        fi = self.fs_viewer

        with fi.suppress_redraw:
            if canvas is not fi.get_canvas():
                fi.set_canvas(canvas)
            # Copy attributes of the channel viewer to the full screen one
            copy_attrs = ['autocuts',
                          'limits', 'transforms',
                          'rotation', 'cutlevels', 'rgbmap', 'icc',
                          'interpolation', 'pan', 'zoom'
                          ]
            viewer.copy_attributes(fi, copy_attrs)

    def _fullscreen_off(self):
        if self.w.fscreen is not None:
            self.w.fscreen.hide()
            # TODO: needed for Qt--can't recover the OpenGL context after
            # re-show; workaround is to rebuild the viewer every time
            self.fs_viewer.imgwin = None
            self.w.fscreen.delete()
            self.w.fscreen = None
            self.fs_viewer = None

    def build_fullscreen_viewer(self):
        """Builds a full screen single channel borderless viewer.
        """
        root = Widgets.TopLevel()
        vbox = Widgets.VBox()
        vbox.set_border_width(0)
        vbox.set_spacing(0)
        root.set_widget(vbox)

        settings = self.prefs.create_category('fullscreen')
        settings.set(autocuts='off', autozoom='off', autocenter='off',
                     sanity_check_scale=False)
        fi = self.build_viewpane(settings)
        self.fs_viewer = fi

        iw = Viewers.GingaViewerWidget(viewer=fi)
        vbox.add_widget(iw, stretch=1)

        self.w.fscreen = root
        root.hide()

    def make_viewer(self, vinfo, channel):
        """Make a viewer whose salient info is in `vinfo` and add it to
        `channel`.
        """
        stk_w = channel.widget

        viewer = vinfo.vclass(logger=self.logger,
                              settings=channel.settings)
        stk_w.add_widget(viewer.get_widget(), title=vinfo.name)

        # let the GUI respond to this widget addition
        self.update_pending()

        # let the channel object do any necessary initialization
        channel.connect_viewer(viewer)

        # finally, let the viewer do any viewer-side initialization
        viewer.initialize_channel(self, channel)

    ####################################################
    # THESE METHODS ARE CALLED FROM OTHER MODULES & OBJECTS
    ####################################################

    def set_titlebar(self, text):
        self.w.root.set_title("Ginga: %s" % text)

    def build_viewpane(self, settings, rgbmap=None, size=(1, 1)):
        # instantiate bindings loaded with users preferences
        bclass = Viewers.ImageViewCanvas.bindingsClass
        bindprefs = self.prefs.create_category('bindings')
        bd = bclass(self.logger, settings=bindprefs)

        wtype = 'widget'
        if self.settings.get('use_opengl', False):
            wtype = 'opengl'

        fi = Viewers.ImageViewCanvas(logger=self.logger,
                                     rgbmap=rgbmap,
                                     settings=settings,
                                     render=wtype,
                                     bindings=bd)
        fi.set_desired_size(size[0], size[1])

        canvas = DrawingCanvas()
        canvas.enable_draw(False)
        fi.set_canvas(canvas)

        # check general settings for default value of enter_focus
        enter_focus = settings.get('enter_focus', None)
        if enter_focus is None:
            enter_focus = self.settings.get('enter_focus', True)
        fi.set_enter_focus(enter_focus)
        # check general settings for default value of focus indicator
        focus_ind = settings.get('show_focus_indicator', None)
        if focus_ind is None:
            focus_ind = self.settings.get('show_focus_indicator', False)
        fi.show_focus_indicator(focus_ind)
        fi.use_image_profile = True

        fi.add_callback('cursor-changed', self.motion_cb)
        fi.add_callback('cursor-down', self.force_focus_cb)
        fi.add_callback('key-down-none', self.keypress)
        fi.add_callback('drag-drop', self.dragdrop)
        fi.ui_set_active(True, viewer=fi)

        bd = fi.get_bindings()
        bd.enable_all(True)

        fi.set_bg(0.2, 0.2, 0.2)
        return fi

    def add_viewer(self, name, settings, workspace=None):

        vbox = Widgets.VBox()
        vbox.set_border_width(1)
        vbox.set_spacing(0)

        if not workspace:
            workspace = self.main_wsname
        w = self.ds.get_nb(workspace)

        size = (700, 700)
        if isinstance(w, Widgets.MDIWidget) and w.true_mdi:
            size = (300, 300)

        # build image viewer & widget
        fi = self.build_viewpane(settings, size=size)

        # add scrollbar support
        scr_val = settings.setdefault('scrollbars', None)
        scr_set = settings.get_setting('scrollbars')
        if scr_val is None:
            # general settings as backup value if not overridden in channel
            scr_val = self.settings.get('scrollbars', 'off')
        si = Viewers.ScrolledView(fi)
        si.scroll_bars(horizontal=scr_val, vertical=scr_val)
        scr_set.add_callback('set', self._toggle_scrollbars, si)
        iw = Widgets.wrap(si)

        stk_w = Widgets.StackWidget()
        stk_w.add_widget(iw, title='image')

        fi.add_callback('focus', self.focus_cb, name)
        vbox.add_widget(stk_w, stretch=1)
        fi.set_name(name)

        # Add the viewer to the specified workspace
        self.ds.add_tab(workspace, vbox, 1, name)

        self.update_pending()

        bnch = Bunch.Bunch(image_viewer=fi,
                           widget=stk_w, container=vbox,
                           workspace=workspace)
        return bnch

    def _toggle_scrollbars(self, setting, value, widget):
        widget.scroll_bars(horizontal=value, vertical=value)

    def gui_add_channel(self, chname=None):
        chpfx = self.settings.get('channel_prefix', "Image")
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        if not chname:
            chname = self.make_channel_name(chpfx)

        captions = (('New channel name:', 'label', 'channel_name', 'entry'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions, orientation='vertical')

        # populate values
        b.channel_name.set_text(chname)
        names = self.ds.get_wsnames()
        try:
            idx = names.index(self._lastwsname)
        except Exception:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)

        # build dialog
        dialog = Widgets.Dialog(title="Add Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channel_cb(w, rsp, b, names))  # noqa
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_add_channels(self):
        chpfx = self.settings.get('channel_prefix', "Image")
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Prefix:', 'label', 'Prefix', 'entry'),
                    ('Number:', 'label', 'Number', 'spinbutton'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    )

        w, b = Widgets.build_info(captions)
        b.prefix.set_text(chpfx)
        b.number.set_limits(1, 12, incr_value=1)
        b.number.set_value(1)

        names = self.ds.get_wsnames()
        try:
            idx = names.index(self.main_wsname)
        except Exception:
            idx = 0
        for name in names:
            b.workspace.append_text(name)
        b.workspace.set_index(idx)
        dialog = Widgets.Dialog(title="Add Channels",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_channels_cb(w, rsp, b, names))  # noqa
        box = dialog.get_content_area()
        box.add_widget(w, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel(self, chname=None):
        if chname is None:
            channel = self.get_channel(chname)
            if (len(self.get_channel_names()) == 0) or (channel is None):
                self.show_error("There are no more channels to delete.",
                                raisetab=True)
                return

            chname = channel.name

        lbl = Widgets.Label("Really delete channel '%s' ?" % (chname))
        dialog = Widgets.Dialog(title="Delete Channel",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_channel_cb(w, rsp, chname))  # noqa

        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_window(self, tabname):
        lbl = Widgets.Label("Really delete window '%s' ?" % (tabname))
        dialog = Widgets.Dialog(title="Delete Window",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_tab_cb(w, rsp, tabname))

        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def gui_delete_channel_ws(self, ws):
        num_children = ws.num_pages()
        if num_children == 0:
            self.show_error("No channels in this workspace to delete.",
                            raisetab=True)
            return
        idx = ws.nb.get_index()
        child = ws.nb.index_to_widget(idx)
        chname = child.extdata.tab_title

        if self.has_channel(chname):
            self.gui_delete_channel(chname)
        else:
            self.gui_delete_window(chname)

    def gui_add_ws(self):
        chpfx = self.settings.get('channel_prefix', "Image")
        ws = self.get_current_workspace()
        if ws is not None:
            chpfx = ws.extdata.get('chpfx', chpfx)

        captions = (('Workspace name:', 'label', 'Workspace name', 'entry'),
                    ('Workspace type:', 'label', 'Workspace type', 'combobox'),
                    ('In workspace:', 'label', 'workspace', 'combobox'),
                    ('Channel prefix:', 'label', 'Channel prefix', 'entry'),
                    ('Number of channels:', 'label', 'num_channels',
                     'spinbutton'),
                    ('Share settings:', 'label', 'Share settings', 'entry'),
                    )
        w, b = Widgets.build_info(captions)

        self.wscount += 1
        wsname = "ws%d" % (self.wscount)
        b.workspace_name.set_text(wsname)
        #b.share_settings.set_length(60)

        cbox = b.workspace_type
        cbox.append_text("Tabs")
        cbox.append_text("Grid")
        cbox.append_text("MDI")
        cbox.append_text("Stack")
        cbox.set_index(0)

        cbox = b.workspace
        names = self.ds.get_wsnames()
        names.insert(0, 'top level')
        try:
            idx = names.index(self.main_wsname)
        except Exception:
            idx = 0
        for name in names:
            cbox.append_text(name)
        cbox.set_index(idx)

        b.channel_prefix.set_text(chpfx)
        spnbtn = b.num_channels
        spnbtn.set_limits(0, 36, incr_value=1)
        spnbtn.set_value(0)

        dialog = Widgets.Dialog(title="Add Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.add_ws_cb(w, rsp, b, names))
        box = dialog.get_content_area()
        box.add_widget(w, stretch=1)
        self.ds.show_dialog(dialog)

    def gui_load_file(self, initialdir=None):
        #self.start_operation('FBrowser')
        self.filesel.popup("Load File", self.load_file_cb,
                           initialdir=initialdir)

    def gui_choose_file_opener(self, msg, openers, open_cb, mimetype,
                               filepath):

        wgts = Bunch.Bunch()
        wgts.table = Widgets.TreeView(auto_expand=True,
                                      use_alt_row_color=True)
        columns = [('Name', 'name'),
                   ('Note', 'note'),
                   ]
        wgts.table.setup_table(columns, 1, 'name')

        tree_dict = OrderedDict()
        openers = list(openers)
        for bnch in openers:
            tree_dict[bnch.name] = bnch

        wgts.table.set_tree(tree_dict)
        # highlight first choice
        path = [openers[0].name]
        wgts.table.select_path(path)

        dialog = Widgets.Dialog(title="Choose File Opener",
                                flags=0,
                                modal=False,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.choose_opener_cb(w, rsp, wgts,
                                                                 openers,
                                                                 open_cb,
                                                                 mimetype))

        box = dialog.get_content_area()
        box.set_border_width(4)
        box.add_widget(Widgets.Label(msg), stretch=0)
        box.add_widget(wgts.table, stretch=1)

        if mimetype is not None:
            hbox = Widgets.HBox()
            wgts.choice = Widgets.CheckBox("Remember choice for session")
            hbox.add_widget(wgts.choice)
            box.add_widget(hbox, stretch=0)
        else:
            wgts.choice = None

        self.ds.show_dialog(dialog)

    def gui_choose_viewer(self, msg, viewers, open_cb, dataobj):

        wgts = Bunch.Bunch()
        wgts.table = Widgets.TreeView(auto_expand=True,
                                      use_alt_row_color=True)
        columns = [('Name', 'name'),
                   #('Note', 'note'),
                   ]
        wgts.table.setup_table(columns, 1, 'name')

        tree_dict = OrderedDict()
        openers = list(viewers)
        for bnch in viewers:
            tree_dict[bnch.name] = bnch

        # set up widget to show viewer description when they click on it
        wgts.descr = Widgets.TextArea(wrap=True, editable=False)

        def _select_viewer_cb(w, dct):
            vclass = list(dct.values())[0].vclass
            text = inspect.getdoc(vclass)
            if text is None:
                text = "(No description available)"
            wgts.descr.set_text(text)

        wgts.table.add_callback('selected', _select_viewer_cb)
        wgts.table.set_tree(tree_dict)
        # highlight first choice
        path = [openers[0].name]
        wgts.table.select_path(path)

        dialog = Widgets.Dialog(title="Choose viewer",
                                flags=0,
                                modal=False,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.choose_viewer_cb(w, rsp, wgts,
                                                                 viewers,
                                                                 open_cb,
                                                                 dataobj))

        box = dialog.get_content_area()
        box.set_border_width(4)
        box.add_widget(Widgets.Label(msg), stretch=0)
        box.add_widget(wgts.table, stretch=0)
        box.add_widget(wgts.descr, stretch=1)

        ## if mimetype is not None:
        ##     hbox = Widgets.HBox()
        ##     wgts.choice = Widgets.CheckBox("Remember choice for session")
        ##     hbox.add_widget(wgts.choice)
        ##     box.add_widget(hbox, stretch=0)
        ## else:
        ##     wgts.choice = None

        self.ds.show_dialog(dialog)
        dialog.resize(600, 600)

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

    def collapse_pane(self, side):
        """
        Toggle collapsing the left or right panes.
        """
        # TODO: this is too tied to one configuration, need to figure
        # out how to generalize this
        hsplit = self.w['hpnl']
        sizes = hsplit.get_sizes()
        lsize, msize, rsize = sizes
        if self._lsize is None:
            self._lsize, self._rsize = lsize, rsize
        self.logger.debug("left=%d mid=%d right=%d" % (
            lsize, msize, rsize))
        if side == 'right':
            if rsize < 10:
                # restore pane
                rsize = self._rsize
                msize -= rsize
            else:
                # minimize pane
                self._rsize = rsize
                msize += rsize
                rsize = 0
        elif side == 'left':
            if lsize < 10:
                # restore pane
                lsize = self._lsize
                msize -= lsize
            else:
                # minimize pane
                self._lsize = lsize
                msize += lsize
                lsize = 0
        hsplit.set_sizes([lsize, msize, rsize])

    def get_font(self, font_family, point_size):
        return GwHelp.get_font(font_family, point_size)

    def get_icon(self, icondir, filename):
        iconpath = os.path.join(icondir, filename)
        icon = GwHelp.get_icon(iconpath)
        return icon

    ####################################################
    # CALLBACKS
    ####################################################

    def window_close(self, *args):
        """Quit the application.
        """
        self.quit()

    def quit(self, *args):
        """Quit the application.
        """
        self.logger.info("Attempting to shut down the application...")

        self.stop()

        # stop plugins in every channel
        for chname in self.get_channel_names():
            channel = self.get_channel(chname)
            opmon = channel.opmon
            opmon.stop_all_plugins()

        # stop all global plugins
        self.gpmon.stop_all_plugins()

        # write out our current layout
        if self.layout_file is not None and self.save_layout:
            self.error_wrap(self.ds.write_layout_conf, self.layout_file)

        self.w.root = None
        while len(self.ds.toplevels) > 0:
            w = self.ds.toplevels.pop()
            w.delete()

    def add_channel_cb(self, w, rsp, b, names):
        chname = str(b.channel_name.get_text())
        idx = b.workspace.get_index()
        if idx < 0:
            idx = 0
        wsname = names[idx]
        self.ds.remove_dialog(w)
        # save name for next add
        self._lastwsname = wsname
        if rsp != 1:
            return

        if self.has_channel(chname):
            self.show_error("Channel name already in use: '%s'" % (chname))
            return True

        self.error_wrap(self.add_channel, chname, workspace=wsname)
        return True

    def add_channels_cb(self, w, rsp, b, names):
        chpfx = b.prefix.get_text()
        idx = b.workspace.get_index()
        wsname = names[idx]
        num = int(b.number.get_value())
        self.ds.remove_dialog(w)
        if (rsp != 1) or (num <= 0):
            return

        for i in range(num):
            chname = self.make_channel_name(chpfx)
            self.error_wrap(self.add_channel, chname, workspace=wsname)
        return True

    def delete_channel_cb(self, w, rsp, chname):
        self.ds.remove_dialog(w)
        if rsp != 1:
            return
        self.delete_channel(chname)
        return True

    def delete_tab_cb(self, w, rsp, tabname):
        self.ds.remove_dialog(w)
        if rsp != 1:
            return
        self.ds.remove_tab(tabname)
        return True

    def __next_dialog(self):
        with self.gui_dialog_lock:
            # this should be the just completed call for a dialog
            # that gets popped off
            self.gui_dialog_list.pop(0)

            if len(self.gui_dialog_list) > 0:
                # if there are any other dialogs waiting, start
                # the next one
                future = self.gui_dialog_list[0]
                self.nongui_do_future(future)

    def choose_opener_cb(self, w, rsp, wgts, openers, open_cb, mimetype):
        sel_dct = wgts.table.get_selected()
        if rsp != 1:
            # cancel
            self.ds.remove_dialog(w)
            self.__next_dialog()
            return

        bnchs = list(sel_dct.values())
        if len(bnchs) != 1:
            # user didn't select an opener
            self.show_error("Need to select one opener!", raisetab=True)
            return

        bnch = bnchs[0]
        self.ds.remove_dialog(w)

        if wgts.choice is not None and wgts.choice.get_state():
            # user wants us to remember their choice
            if mimetype != '*':
                # loader is not registered for this mimetype, so go ahead
                # and do it
                loader.add_opener(mimetype, bnch.opener,
                                  priority=bnch.priority, note=bnch.note)
            else:
                # multiple loaders for the same mimetype--
                # remember setting by prioritizing choice
                bnch.priority = -1

        self.nongui_do(open_cb, bnch.opener)
        self.__next_dialog()
        return True

    def choose_viewer_cb(self, w, rsp, wgts, viewers, open_cb, dataobj):
        sel_dct = wgts.table.get_selected()
        if rsp != 1:
            # cancel
            self.ds.remove_dialog(w)
            return

        bnchs = list(sel_dct.values())
        if len(bnchs) != 1:
            # user didn't select an opener
            self.show_error("Need to select one viewer!", raisetab=True)
            return

        bnch = bnchs[0]
        self.ds.remove_dialog(w)

        open_cb(bnch, dataobj)
        return True

    def init_workspace(self, ws):

        # add close handlers
        ws.add_callback('ws-close', self.workspace_closed_cb)
        if ws.has_callback('page-close'):
            ws.add_callback('page-close', self.page_close_cb)
        if ws.has_callback('page-switch'):
            ws.add_callback('page-switch', self.page_switch_cb)
        if ws.has_callback('page-added'):
            ws.add_callback('page-added', self.page_added_cb)
        if ws.has_callback('page-removed'):
            ws.add_callback('page-removed', self.page_removed_cb)

        if ws.toolbar is not None:
            tb = ws.toolbar
            tb.add_separator()

            # add toolbar buttons for navigating between tabs
            iconpath = os.path.join(self.iconpath, "prev_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(24, 24))
            btn.set_tooltip("Focus previous tab in this workspace")
            btn.add_callback('activated', lambda w: self.prev_channel_ws(ws))
            ws.extdata.w_prev_tab = btn
            btn.set_enabled(False)
            iconpath = os.path.join(self.iconpath, "next_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(24, 24))
            btn.set_tooltip("Focus next tab in this workspace")
            btn.add_callback('activated', lambda w: self.next_channel_ws(ws))
            ws.extdata.w_next_tab = btn
            btn.set_enabled(False)

            tb.add_separator()

            entry = Widgets.TextEntry()
            entry.set_length(8)
            chpfx = self.settings.get('channel_prefix', "Image")
            entry.set_text(chpfx)
            entry.set_tooltip("Name or prefix for a new channel")
            ws.extdata.w_chname = entry
            btn = tb.add_widget(entry)

            # add toolbar buttons adding and deleting channels
            iconpath = os.path.join(self.iconpath, "inbox_plus_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(24, 23))
            btn.set_tooltip("Add a channel to this workspace")
            btn.add_callback('activated',
                             lambda w: self.add_channel_auto_ws(ws))
            ws.extdata.w_new_channel = btn
            iconpath = os.path.join(self.iconpath, "inbox_minus_48.png")
            btn = tb.add_action(None, iconpath=iconpath, iconsize=(24, 23))
            btn.set_tooltip("Delete current channel from this workspace")
            btn.add_callback('activated',
                             lambda w: self.gui_delete_channel_ws(ws))
            btn.set_enabled(False)
            ws.extdata.w_del_channel = btn

    def add_ws_cb(self, w, rsp, b, names):
        try:
            wsname = str(b.workspace_name.get_text())
            wstype = b.workspace_type.get_text().lower()
            if rsp != 1:
                self.ds.remove_dialog(w)
                return

            try:
                nb = self.ds.get_nb(wsname)  # noqa
                self.show_error(
                    "Workspace name '%s' cannot be used, sorry." % (wsname),
                    raisetab=True)
                self.ds.remove_dialog(w)
                return

            except KeyError:
                pass

            in_space = b.workspace.get_text()

            chpfx = b.channel_prefix.get_text().strip()
            num = int(b.num_channels.get_value())
            share_list = b.share_settings.get_text().split()

            self.ds.remove_dialog(w)

            ws = self.error_wrap(self.add_workspace, wsname, wstype,
                                 inSpace=in_space)
            ws.extdata.chpfx = chpfx

            self.init_workspace(ws)

            if num <= 0:
                return

            # Create a settings template to copy settings from
            name = "channel_template_%f" % (time.time())
            settings = self.prefs.create_category(name)
            try:
                settings_template = self.prefs.get_settings('channel_Image')
                settings_template.copy_settings(settings)
            except KeyError:
                settings_template = None

            for i in range(num):
                chname = self.make_channel_name(chpfx)
                self.add_channel(chname, workspace=wsname,
                                 settings_template=settings_template,
                                 settings_share=settings,
                                 share_keylist=share_list)
        except Exception as e:
            self.logger.error("Exception building workspace: %s" % (str(e)))

        return True

    def load_file_cb(self, paths):
        # NOTE: this dialog callback is handled a little differently
        # from some of the other pop-ups.  It only gets called if a
        # file was selected and "Open" clicked.  This is due to the
        # use of FileSelection rather than Dialog widget
        self.open_uris(paths)

    def _get_channel_by_container(self, child):
        for chname in self.get_channel_names():
            channel = self.get_channel(chname)
            if channel.container == child:
                return channel
        return None

    def page_switch_cb(self, ws, child):
        self.logger.debug("page switched to %s" % (str(child)))

        # Find the channel that contains this widget
        channel = self._get_channel_by_container(child)
        self.logger.debug("channel: %s" % (str(channel)))
        if channel is not None:
            viewer = channel.viewer
            if viewer != self.getfocus_viewer():
                chname = channel.name

                self.logger.debug("Active channel switch to '%s'" % (
                    chname))
                self.change_channel(chname, raisew=False)

        return True

    def workspace_closed_cb(self, ws):
        self.logger.debug("workspace requests close")
        num_children = ws.num_pages()
        if num_children > 0:
            self.show_error(
                "Please close all windows in this workspace first!",
                raisetab=True)
            return

        # TODO: this will prompt the user if we should close the workspace
        lbl = Widgets.Label("Really delete workspace '%s' ?" % (ws.name))
        dialog = Widgets.Dialog(title="Delete Workspace",
                                flags=0,
                                buttons=[['Cancel', 0], ['Ok', 1]],
                                parent=self.w.root)
        dialog.add_callback('activated',
                            lambda w, rsp: self.delete_workspace_cb(w, rsp,
                                                                    ws))
        box = dialog.get_content_area()
        box.add_widget(lbl, stretch=0)

        self.ds.show_dialog(dialog)

    def delete_workspace_cb(self, w, rsp, ws):
        self.ds.remove_dialog(w)
        if rsp == 0:
            return

        top_w = ws.extdata.get('top_w', None)
        if top_w is None:
            self.ds.remove_tab(ws.name)
        else:
            # this is a top-level window
            self.ds.remove_toplevel(top_w)

        # inform desktop we are no longer tracking this
        self.ds.delete_ws(ws.name)

        return True

    def page_added_cb(self, ws, child):
        self.logger.debug("page added in %s: '%s'" % (ws.name, str(child)))

        num_pages = ws.num_pages()
        if ws.toolbar is not None:
            if num_pages > 1:
                ws.extdata.w_prev_tab.set_enabled(True)
                ws.extdata.w_next_tab.set_enabled(True)
            ws.extdata.w_del_channel.set_enabled(True)

    def page_removed_cb(self, ws, child):
        self.logger.debug("page removed in %s: '%s'" % (ws.name, str(child)))
        num_pages = ws.num_pages()
        if num_pages <= 1:
            if ws.toolbar is not None:
                ws.extdata.w_prev_tab.set_enabled(False)
                ws.extdata.w_next_tab.set_enabled(False)
                if num_pages <= 0:
                    ws.extdata.w_del_channel.set_enabled(False)

    def page_close_cb(self, ws, child):
        # user is attempting to close the page
        self.logger.debug("page closed in %s: '%s'" % (ws.name, str(child)))

        channel = self._get_channel_by_container(child)
        if channel is not None:
            self.gui_delete_channel(channel.name)

    def showxy(self, viewer, data_x, data_y):
        """Called by the mouse-tracking callback to handle reporting of
        cursor position to various plugins that subscribe to the
        'field-info' callback.
        """
        # This is an optimization to get around slow coordinate
        # transformation by astropy and possibly other WCS packages,
        # which causes delay for other mouse tracking events, e.g.
        # the zoom plugin.
        # We only update the under cursor information every period
        # defined by (self.cursor_interval) sec.
        #
        # If the refresh interval has expired then update the info;
        # otherwise (re)set the timer until the end of the interval.
        cur_time = time.time()
        elapsed = cur_time - self._cursor_last_update
        if elapsed > self.cursor_interval:
            # cancel timer
            self._cursor_task.clear()
            self.gui_do_oneshot('field-info', self._showxy,
                                viewer, data_x, data_y)
        else:
            # store needed data into the timer data area
            self._cursor_task.data.setvals(viewer=viewer,
                                           data_x=data_x, data_y=data_y)
            # calculate delta until end of refresh interval
            period = self.cursor_interval - elapsed
            # set timer conditionally (only if it hasn't yet been set)
            self._cursor_task.cond_set(period)
        return True

    def _cursor_timer_cb(self, timer):
        """Callback when the cursor timer expires.
        """
        data = timer.data
        self.gui_do_oneshot('field-info', self._showxy,
                            data.viewer, data.data_x, data.data_y)

    def _showxy(self, viewer, data_x, data_y):
        """Update the info from the last position recorded under the cursor.
        """
        self._cursor_last_update = time.time()

        try:
            image = viewer.get_vip()
            if image.ndim < 2:
                return

            settings = viewer.get_settings()
            info = image.info_xy(data_x, data_y, settings)

            # Are we reporting in data or FITS coordinates?
            off = self.settings.get('pixel_coords_offset', 0.0)
            info.x += off
            info.y += off
            if 'image_x' in info:
                info.image_x += off
            if 'image_y' in info:
                info.image_y += off

        except Exception as e:
            self.logger.warning(
                "Can't get info under the cursor: %s" % (str(e)), exc_info=True)
            return

        # TODO: can this be made more efficient?
        chname = self.get_channel_name(viewer)
        channel = self.get_channel(chname)

        self.make_callback('field-info', channel, info)

        self.update_pending()
        return True

    def motion_cb(self, viewer, button, data_x, data_y):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.showxy(viewer, data_x, data_y)
        return True

    def keypress(self, viewer, event, data_x, data_y):
        """Key press event in a channel window."""
        keyname = event.key
        chname = self.get_channel_name(viewer)
        self.logger.debug("key press (%s) in channel %s" % (
            keyname, chname))
        # TODO: keyboard accelerators to raise tabs need to be integrated into
        #   the desktop object
        if keyname == 'Z':
            self.ds.raise_tab('Zoom')
        ## elif keyname == 'T':
        ##     self.ds.raise_tab('Thumbs')
        elif keyname == 'I':
            self.ds.raise_tab('Info')
        elif keyname == 'H':
            self.ds.raise_tab('Header')
        elif keyname == 'C':
            self.ds.raise_tab('Contents')
        elif keyname == 'D':
            self.ds.raise_tab('Dialogs')
        elif keyname == 'F':
            self.build_fullscreen()
        elif keyname == 'f':
            self.toggle_fullscreen()
        elif keyname == 'm':
            self.maximize()
        elif keyname == '<':
            self.collapse_pane('left')
        elif keyname == '>':
            self.collapse_pane('right')
        elif keyname == 'n':
            self.next_channel()
        elif keyname == 'J':
            self.cycle_workspace_type()
        elif keyname == 'k':
            self.add_channel_auto()
        elif keyname == 'K':
            self.remove_channel_auto()
        elif keyname == 'f1':
            self.show_channel_names()
        ## elif keyname == 'escape':
        ##     self.reset_viewer()
        elif keyname in ('up',):
            self.prev_img()
        elif keyname in ('down',):
            self.next_img()
        elif keyname in ('left',):
            self.prev_channel()
        elif keyname in ('right',):
            self.next_channel()
        return True

    def dragdrop(self, chviewer, uris):
        """Called when a drop operation is performed on a channel viewer.
        We are called back with a URL and we attempt to (down)load it if it
        names a file.
        """
        # find out our channel
        chname = self.get_channel_name(chviewer)
        self.open_uris(uris, chname=chname)
        return True

    def force_focus_cb(self, viewer, event, data_x, data_y):
        chname = self.get_channel_name(viewer)
        channel = self.get_channel(chname)
        v = channel.viewer
        if hasattr(v, 'take_focus'):
            v.take_focus()

        if not self.settings.get('channel_follows_focus', False):
            self.change_channel(chname, raisew=True)
        return True

    def focus_cb(self, viewer, tf, name):
        """Called when ``viewer`` gets ``(tf==True)`` or loses
        ``(tf==False)`` the focus.
        """
        if not self.settings.get('channel_follows_focus', False):
            return True

        self.logger.debug("focus %s=%s" % (name, tf))
        if tf:
            if viewer != self.getfocus_viewer():
                self.change_channel(name, raisew=False)

        return True

    def show_channel_names(self):
        """Show each channel's name in its image viewer.
        Useful in 'grid' or 'stack' workspace type to identify which window
        is which.
        """
        for name in self.get_channel_names():
            channel = self.get_channel(name)
            channel.fitsimage.onscreen_message(name, delay=2.5)

    ########################################################
    ### NON-PEP8 PREDECESSORS: TO BE DEPRECATED

    def name_image_from_path(self, path, idx=None):
        self.logger.warning("This function has moved to the"
                            " 'ginga.util.iohelper' module,"
                            " and will be deprecated soon.")
        return iohelper.name_image_from_path(path, idx=idx)

    def get_fileinfo(self, filespec, dldir=None):
        self.logger.warning("This function has moved to the"
                            " 'ginga.util.iohelper' module,"
                            " and will be deprecated soon.")
        return iohelper.get_fileinfo(filespec, cache_dir=dldir)

    def stop_operation_channel(self, chname, opname):
        self.logger.warning(
            "Do not use this method name--it will be deprecated!")
        return self.stop_local_plugin(chname, opname)

    getDrawClass = get_draw_class
    getDrawClasses = get_draw_classes
    get_channelName = get_channel_name
    get_channelInfo = get_channel_info
    get_channelNames = get_channel_names
    followFocus = follow_focus
    showStatus = show_status
    getfocus_fitsimage = getfocus_viewer
    get_fitsimage = get_viewer
    get_ServerBank = get_server_bank
    getFont = get_font
    getPluginManager = get_plugin_manager
    statusMsg = status_msg


class GuiLogHandler(logging.Handler):
    """Logs to a pane in the GUI."""

    def __init__(self, fv, level=logging.NOTSET):
        self.fv = fv
        logging.Handler.__init__(self, level=level)

    def emit(self, record):
        text = self.format(record)
        self.fv.logit(text)


def _rmtmpdir(tmpdir):
    if os.path.isdir(tmpdir):
        shutil.rmtree(tmpdir)
