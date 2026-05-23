#
# main.py -- reference viewer for the Ginga toolkit.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""This module handles the main reference viewer."""

# stdlib imports
import glob
import sys
import os
import logging
import logging.handlers
import warnings
import threading

# 3rd party
import yaml

# Local application imports
from ginga.misc.Bunch import Bunch
from ginga.misc import Task, ModuleManager, Settings, log
import ginga.version as version
import ginga.toolkit as ginga_toolkit
from ginga.util import paths, rgb_cms, compat, loader, grc

# Catch warnings
logging.captureWarnings(True)

__all__ = ['ReferenceViewer']

default_layout = ['seq', {},
                   ['vbox', dict(name='top', width=1400, height=700),  # noqa
                    dict(row=['ws', dict(name='menubar', wstype='stack',
                                         group=99)],
                         stretch=0),
                    dict(row=['hpanel', dict(name='hpnl'),
                              ['ws', dict(name='left', wstype='tabs',  # noqa
                                          width=300, height=-1, group=2),
                               # (tabname, layout), ...
                               [("Info", ['vpanel', {},
                                          ['ws', dict(name='uleft',
                                                      wstype='stack',
                                                      height=250, group=3)],
                                          ['ws', dict(name='lleft',
                                                      wstype='tabs',
                                                      height=330, group=3)],
                                          ]
                                 )]],
                              ['vbox', dict(name='main', width=600),
                               dict(row=['ws', dict(name='channels',
                                                    wstype='tabs',
                                                    group=1, use_toolbar=True,
                                                    default=True)],
                                    stretch=1),
                               dict(row=['ws', dict(name='cbar', wstype='stack',
                                                    group=99)], stretch=0),
                               dict(row=['ws', dict(name='readout',
                                                    wstype='stack',
                                                    group=99)], stretch=0),
                               dict(row=['ws', dict(name='operations',
                                                    wstype='stack',
                                                    group=99)], stretch=0),
                               ],
                              ['ws', dict(name='right', wstype='tabs',
                                          width=400, height=-1, group=2),
                               # (tabname, layout), ...
                               [("Dialogs", ['ws', dict(name='dialogs',
                                                        wstype='tabs',
                                                        group=2)
                                             ]
                                 )]
                               ],
                              ], stretch=1),  # noqa
                    dict(row=['ws', dict(name='toolbar', wstype='stack',
                                         height=40, group=2)],
                         stretch=0),
                    dict(row=['hbox', dict(name='status')], stretch=0),
                    ]]

plugins = [
    # hidden plugins, started at program initialization
    Bunch(module='Menubar', klass='GingaMenubar', workspace='menubar',
          start=True, hidden=True, category='System', menu="Menubar [G]",
          ptype='global', enabled=True),
    Bunch(module='Operations', workspace='operations', start=True,
          hidden=True, category='System', menu="Operations [G]",
          ptype='global', enabled=True),
    Bunch(module='Toolbar', klass='Toolbar', workspace='toolbar',
          start=True, hidden=True, category='System', ptype='global',
          enabled=True),
    Bunch(module='Toolbar', klass='Toolbar_Ginga_Image',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Toolbar', klass='Toolbar_Ginga_Plot',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Toolbar', klass='Toolbar_Ginga_Table',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Pan', workspace='uleft', start=True,
          hidden=True, category='System', menu="Pan [G]", ptype='global',
          enabled=True),
    Bunch(module='Info', tab='Synopsis', workspace='lleft', start=True,
          hidden=True, category='System', menu="Info [G]", ptype='global',
          enabled=True),
    Bunch(module='Info', klass='Info_Ginga_Image',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Info', klass='Info_Ginga_Plot',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Info', klass='Info_Ginga_Table',
          hidden=True, category='System', ptype='local',
          enabled=True, exclusive=False),
    Bunch(module='Thumbs', tab='Thumbs', workspace='right', start=True,
          hidden=True, category='System', menu="Thumbs [G]", ptype='global',
          enabled=True),
    Bunch(module='Contents', tab='Contents', workspace='right', start=True,
          hidden=True, category='System', menu="Contents [G]", ptype='global',
          enabled=True),
    Bunch(module='Colorbar', workspace='cbar', start=True,
          hidden=True, category='System', menu="Colorbar [G]", ptype='global',
          enabled=True),
    Bunch(module='Cursor', workspace='readout', start=True,
          hidden=True, category='System', menu="Cursor [G]", ptype='global',
          enabled=True),
    Bunch(module='Errors', tab='Errors', workspace='right', start=True,
          hidden=True, category='System', menu="Errors [G]", ptype='global',
          enabled=True),
    Bunch(module='Downloads', tab='Downloads', workspace='right', start=False,
          menu="Downloads [G]", category='Utils', ptype='global', enabled=True),

    # optional, user-started plugins
    Bunch(module='Blink', tab='Blink Channels', workspace='right', start=False,
          name='Blink[channels]', menu="Blink Channels [G]",
          category='Analysis', ptype='global', enabled=True),
    Bunch(module='Blink', workspace='dialogs', menu='Blink Images',
          name='Blink[images]', category='Analysis', ptype='local',
          enabled=True),
    Bunch(module='Crosshair', workspace='left', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='Cuts', workspace='dialogs', category='Analysis',
          ptype='local', singleton=False, enabled=True),
    Bunch(module='LineProfile', workspace='dialogs',
          category='Analysis.Datacube', ptype='local', enabled=True),
    Bunch(module='Histogram', workspace='dialogs', category='Analysis',
          ptype='local', singleton=False, enabled=True),
    Bunch(module='Overlays', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='Pick', workspace='dialogs', category='Analysis',
          ptype='local', singleton=False, enabled=True),
    Bunch(module='PixTable', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='TVMark', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='TVMask', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='WCSMatch', tab='WCSMatch', workspace='right', start=False,
          menu="WCS Match [G]", category='Analysis', ptype='global',
          enabled=True),
    Bunch(module='Command', tab='Command', workspace='lleft', start=False,
          menu="Command Line [G]", category='Debug', ptype='global',
          enabled=True),
    Bunch(module='Log', tab='Log', workspace='right', start=False,
          menu="Logger Info [G]", category='Debug', ptype='global',
          enabled=True),
    Bunch(module='MultiDim', workspace='lleft', category='Navigation',
          ptype='local', exclusive=False, enabled=True),
    Bunch(module='RC', tab='RC', workspace='right', start=False,
          menu="Remote Control [G]", category='Remote', ptype='global',
          enabled=True),
    Bunch(module='SAMP', tab='SAMP', workspace='right', start=False,
          menu="SAMP Client [G]", category='Remote', ptype='global',
          enabled=False),
    Bunch(module='Compose', workspace='dialogs', category='RGB', ptype='local',
          enabled=False),
    Bunch(module='ScreenShot', workspace='dialogs', category='RGB',
          ptype='local', enabled=True),
    Bunch(module='ColorMapPicker', tab='ColorMapPicker',
          name="ColorMapPicker[G]", menu="Set Color Map [G]",
          workspace='right', start=False,
          category='RGB', ptype='global', enabled=True),
    Bunch(module='ColorMapPicker',
          menu="Set Color Map", workspace='dialogs', category='RGB',
          ptype='local', exclusive=False, enabled=True),
    Bunch(module='PlotTable', workspace='dialogs', category='Table',
          ptype='local', singleton=False, exclusive=False, enabled=True),
    Bunch(module='Catalogs', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='Drawing', workspace='dialogs', category='Utils',
          ptype='local', singleton=False, enabled=True),
    Bunch(module='AutoLoad', workspace='dialogs', category='Utils',
          ptype='local', enabled=False),
    Bunch(module='Pipeline', workspace='dialogs', category='Photos',
          ptype='local', enabled=False),
    Bunch(module='SlideShow', workspace='dialogs', category='Photos',
          ptype='local', enabled=False),
    Bunch(module='FBrowser', workspace='dialogs', category='Utils',
          ptype='local', exclusive=False, singleton=False, enabled=True),
    Bunch(module='ChangeHistory', tab='History', workspace='right',
          menu="History [G]", start=False, category='Utils', ptype='global',
          enabled=True),
    Bunch(module='Mosaic', workspace='dialogs', category='Utils', ptype='local',
          enabled=True),
    Bunch(module='Collage', workspace='dialogs', category='Utils', ptype='local',
          enabled=True),
    Bunch(module='FBrowser', tab='Open File', workspace='right',
          name="FBrowser[G]", menu="Open File [G]", start=False,
          category='Utils', ptype='global', singleton=False, enabled=True),
    Bunch(module='Preferences', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='Ruler', workspace='dialogs', category='Utils', ptype='local',
          singleton=False, enabled=True),
    # TODO: Add SaveImage to File menu.
    Bunch(module='SaveImage', tab='SaveImage', workspace='right',
          menu="Save File [G]", start=False, category='Utils', ptype='global',
          enabled=True),
    Bunch(module='WCSAxes', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='Header', tab='Header', workspace='left', start=False,
          menu="Header [G]", hidden=False, category='Utils', ptype='global',
          enabled=True),
    Bunch(module='Zoom', tab='Zoom', workspace='left', start=False,
          menu="Zoom [G]", category='Utils', ptype='global', enabled=True),
    Bunch(module='LoaderConfig', tab='Loaders', workspace='channels',
          start=False, menu="LoaderConfig [G]", category='Debug',
          ptype='global', enabled=True),
    Bunch(module='PluginConfig', tab='Plugins', workspace='channels',
          start=False, menu="PluginConfig [G]", category='Debug',
          ptype='global', enabled=True),
]


def get_plugin_spec(module=None):
    return [spec for spec in plugins if spec['module'] == module]


class ReferenceViewer:
    """
    This class exists solely to be able to customize the reference
    viewer startup.
    """
    def __init__(self, layout=default_layout, plugins=plugins, appname='ginga',
                 basedir=None, channels=None, ev_quit=None, ws_sock=None):
        self.appname = appname
        self.basedir = basedir
        self.layout = layout
        self.ev_quit = ev_quit
        self.ws_sock = ws_sock
        if channels is None:
            channels = ['Image']
        self.channels = channels
        self.default_plugins = plugins
        self.plugins = []
        self.plugin_dct = dict()
        self.logger = None
        self.prefs = None
        self.settings = None
        self.ginga_shell = None

    def add_plugin_spec(self, spec):
        self.plugins.append(spec)
        plugin_name = self.get_plugin_name(spec)
        self.plugin_dct[plugin_name] = spec

    def clear_default_plugins(self):
        self.plugins = []
        self.plugin_dct = dict()

    def get_plugin_name(self, spec):
        if 'name' in spec:
            return spec['name']
        module = spec['module']
        if '.' in module:
            module = module.split('.')[-1]
        klass = spec.get('klass', None)
        name = module if klass is None else klass
        return name

    def add_default_plugins(self, except_global=[], except_local=[]):
        """
        Add the ginga-distributed default set of plugins to the
        reference viewer.
        """
        # add default plugins
        for spec in self.default_plugins:
            ptype = spec.get('ptype', 'local')
            if ptype == 'global' and spec.module not in except_global:
                self.add_plugin_spec(spec)

            if ptype == 'local' and spec.module not in except_local:
                self.add_plugin_spec(spec)

    def add_separately_distributed_plugins(self):
        groups = ['ginga.rv.plugins', 'ginga_plugins',
                  '{}_plugins'.format(self.appname)]
        available_methods = []

        for group in groups:
            discovered_plugins = compat.ep_get(group)
            for entry_point in discovered_plugins:
                try:
                    method = entry_point.load()
                    available_methods.append(method)

                except Exception as e:
                    print("Error trying to load entry point %s: %s" % (
                        str(entry_point), str(e)))

        for method in available_methods:
            try:
                spec = method()
                self.add_plugin_spec(spec)

            except Exception as e:
                print("Error trying to instantiate external plugin using %s: %s" % (
                    str(method), str(e)))

    def add_default_options(self, argprs):
        """
        Adds the default reference viewer startup options to an
        ArgumentParser instance `argprs`.
        """
        if hasattr(argprs, 'add_option'):
            # older OptParse
            add_argument = argprs.add_option
        else:
            # newer ArgParse
            add_argument = argprs.add_argument

        add_argument("--basedir", dest="basedir", metavar="NAME",
                     help="Specify Ginga configuration area")
        add_argument("--bufsize", dest="bufsize", metavar="NUM",
                     type=int, default=10,
                     help="Buffer length to NUM")
        add_argument('-c', "--channels", dest="channels",
                     help="Specify list of channels to create")
        add_argument("--disable-plugins", dest="disable_plugins",
                     metavar="NAMES",
                     help="Specify plugins that should be disabled")
        add_argument("--display", dest="display", metavar="HOST:N",
                     help="Use X display on HOST:N")
        add_argument("--fitspkg", dest="fitspkg", metavar="NAME",
                     default=None,
                     help="Prefer FITS I/O module NAME")
        add_argument("-g", "--geometry", dest="geometry",
                     default=None, metavar="GEOM",
                     help="X geometry for initial size and placement")
        add_argument("--minthreads", dest="minthreads", type=int,
                     default=None, metavar="NUM",
                     help="Start minimum of NUM threads in thread pool")
        add_argument("--modules", dest="modules", metavar="NAMES",
                     help="Specify additional modules to load")
        add_argument("--norestore", dest="norestore", default=False,
                     action="store_true",
                     help="Don't restore the GUI from a saved layout")
        add_argument("--nosplash", dest="nosplash", default=False,
                     action="store_true",
                     help="Don't display the splash screen")
        add_argument("--numthreads", dest="numthreads", type=int,
                     default=None, metavar="NUM",
                     help="Maximum NUM threads in thread pool")
        add_argument("--opengl", dest="opengl", default=False,
                     action="store_true",
                     help="Use OpenGL acceleration")
        add_argument("--plugins", dest="plugins", metavar="NAMES",
                     help="Specify additional plugins to load")
        add_argument("--rcport", dest="rc_port", type=int,
                     default=None, metavar="NUM",
                     help="Use PORT for Ginga Remote Control plugin")
        add_argument("--sep", dest="separate_channels", default=False,
                     action="store_true",
                     help="Load files in separate channels")
        add_argument("--suppress-fits-warnings",
                     dest="suppress_fits_warnings", default=False,
                     action="store_true",
                     help="Suppress FITS verify warnings")
        add_argument("-t", "--toolkit", dest="toolkit", metavar="NAME",
                     default=None,
                     help="Prefer GUI toolkit (gtk|qt)")
        add_argument("--wcspkg", dest="wcspkg", metavar="NAME",
                     default=None,
                     help="Prefer WCS module NAME")
        log.addlogopts(argprs)

    def setup(self):
        """
        Setup routine for running the reference viewer.

        Assumptions:
        1) Following instance variables are set as needed:
           logger, settings, prefs, appname, basedir, ev_quit, ws_sock
        2) settings should be initialized with any desired overrides.
        """
        if self.settings is None:
            raise RuntimeError("initialize settings before calling setup()")

        # default of 1000 is a little too small
        sys.setrecursionlimit(self.settings.get('recursion_limit', 2000))

        # So we can find our plugins
        sys.path.insert(0, self.basedir)
        package_home = os.path.split(sys.modules['ginga.version'].__file__)[0]
        child_dir = os.path.join(package_home, 'rv', 'plugins')
        sys.path.insert(0, child_dir)
        plugin_dir = os.path.join(self.basedir, 'plugins')
        sys.path.insert(0, plugin_dir)

        # Create the dynamic module manager
        mm = ModuleManager.ModuleManager(self.logger)
        sys.meta_path.append(mm)

        rc_port = self.settings.get('grc_port', None)
        if rc_port is not None:
            grc.default_rc_port = rc_port

        # what is the dynamic config file to load
        app_config = "{}_config".format(self.appname)
        gc = os.path.join(self.basedir, f"{app_config}.py")
        have_app_config = os.path.exists(gc)

        # User configuration, earliest possible intervention
        if have_app_config:
            try:
                app_config = mm.load_module(app_config)

                if hasattr(app_config, 'init_config'):
                    app_config.init_config(self)

            except Exception as e:
                self.logger.error("Error processing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Choose a toolkit
        toolkit = self.settings.get('widgetSet', 'choose')
        if toolkit == 'choose':
            try:
                ginga_toolkit.choose()
            except ImportError as e:
                print("UI toolkit choose error: %s" % str(e))
                sys.exit(1)
        else:
            ginga_toolkit.use(toolkit)

        tkname = ginga_toolkit.get_family()
        self.logger.info("Chosen toolkit (%s) family is '%s'" % (
            ginga_toolkit.toolkit, tkname))

        # these imports have to be here, otherwise they force the choice
        # of toolkit too early
        from ginga.rv.Control import GingaShell, GuiLogHandler

        if self.settings.get('useMatplotlibColormaps', False):
            # Add matplotlib color maps if matplotlib is installed
            try:
                from ginga import cmap
                cmap.add_matplotlib_cmaps(fail_on_import_error=False)
            except Exception as e:
                self.logger.warning(
                    "failed to load matplotlib colormaps: %s" % (str(e)))

        # Set a working RGB ICC profile if user has one
        working_profile = self.settings.get('icc_working_profile', None)
        rgb_cms.working_profile = working_profile

        # Set the WCS package
        wcspkg = self.settings.get('WCSpkg', 'choose')

        try:
            from ginga.util import wcsmod
            if wcspkg != 'choose':
                assert wcsmod.use(wcspkg) is True
        except Exception as e:
            self.logger.warning(
                "failed to set WCS package preference '{}': {}".format(wcspkg, e))

        # User wants to customize the FITS package?
        fitspkg = self.settings.get('FITSpkg', 'choose')

        supp_warn = self.settings.get('suppress_fits_warnings', False)
        if supp_warn:
            import warnings
            from astropy.io import fits
            warnings.simplefilter('ignore', fits.verify.VerifyWarning)

        try:
            from ginga.util.io import io_fits
            if fitspkg != 'choose':
                assert io_fits.use(fitspkg) is True

        except Exception as e:
            self.logger.warning(
                "failed to set FITS package preference '{}': {}".format(fitspkg, e))

        # Create and start thread pool
        min_threads = self.settings.get('min_threads', 2)
        num_threads = self.settings.get('num_threads', max(os.cpu_count(), 10))
        analyze_interval = self.settings.get('threadpool_analyze_interval_sec', None)
        thread_pool = Task.ThreadPool(numthreads=num_threads, logger=self.logger,
                                      minthreads=min_threads, ev_quit=self.ev_quit,
                                      analyze_interval=analyze_interval)
        thread_pool.startall()

        # Create the Ginga main object
        ginga_shell = GingaShell(self.logger, thread_pool, mm, self.prefs,
                                 ev_quit=self.ev_quit, ws_sock=self.ws_sock)
        self.ginga_shell = ginga_shell

        layout_file = os.path.join(self.basedir, self.settings.get('layout_file',
                                                                   'layout.json'))
        ginga_shell.set_layout(self.layout, layout_file=layout_file,
                               save_layout=self.settings.get('save_layout', True))

        # User configuration (custom star catalogs, etc.)
        if have_app_config:
            try:
                if hasattr(app_config, 'pre_gui_config'):
                    app_config.pre_gui_config(ginga_shell)
            except Exception as e:
                self.logger.error("Error importing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Build desired layout
        norestore = self.settings.get('ignore_saved_layout', False)
        ginga_shell.build_toplevel(ignore_saved_layout=norestore)

        # Did user specify a particular geometry?
        geometry = self.settings.get('geometry', None)
        if geometry is not None:
            ginga_shell.set_geometry(geometry)

        # make the list of disabled plugins
        disabled_plugins = self.settings.get('disable_plugins', [])
        if not isinstance(disabled_plugins, list):
            disabled_plugins = disabled_plugins.lower().split(',')
        disabled_plugins = set(disabled_plugins)

        # Add GUI log handler (for "Log" global plugin)
        guiHdlr = GuiLogHandler(ginga_shell)
        guiHdlr.setLevel(self.settings.get('loglevel', logging.INFO))
        fmt = logging.Formatter(log.LOG_FORMAT)
        guiHdlr.setFormatter(fmt)
        self.logger.addHandler(guiHdlr)

        # Set loader priorities, if user has saved any
        # (see LoaderConfig plugin)
        path = os.path.join(self.basedir, 'loaders.yml')
        if os.path.exists(path):
            try:
                with open(path, 'r') as in_f:
                    loader_dct = yaml.safe_load(in_f.read())

                # set saved priorities for openers
                for mimetype, m_dct in loader_dct.items():
                    for name, l_dct in m_dct.items():
                        opener = loader.get_opener(name)
                        loader.add_opener(opener, [mimetype],
                                          priority=l_dct['priority'],
                                          note=opener.__doc__)

            except Exception as e:
                self.logger.error(f"failed to process loader file '{path}': {e}",
                                  exc_info=True)

        # Does user have a saved plugin setup?  If so, check which
        # plugins should be disabled, or have a customized category or
        # workspace
        plugin_file = self.settings.get('plugin_file', None)
        if plugin_file is not None:
            plugin_file = os.path.join(self.basedir, plugin_file)
            if os.path.exists(plugin_file):
                self.logger.info("Reading plugin file '%s'..." % (plugin_file))
                try:
                    with open(plugin_file, 'r') as in_f:
                        buf = in_f.read()
                        _plugins = yaml.safe_load(buf)

                    for dct in _plugins:
                        plugin_name = self.get_plugin_name(dct)
                        if plugin_name in self.plugin_dct:
                            # we know about this plugin, override listed
                            # attributes
                            spec = self.plugin_dct[plugin_name]
                            for name in ['enabled', 'category', 'hidden',
                                         'workspace', 'tab', 'menu', 'start',
                                         'pfx', 'optray', 'singleton', 'limit',
                                         'exclusive']:
                                if name in dct:
                                    spec[name] = dct[name]
                        else:
                            # unknown plugin
                            spec = Bunch(dct)
                            self.add_plugin_spec(spec)

                except Exception as e:
                    self.logger.error(f"Error reading plugin file: {e}",
                                      exc_info=True)

        # Load any custom global plugins named on command line or in
        # general.cfg
        global_plugins = self.settings.get('global_plugins', [])
        if not isinstance(global_plugins, list):
            global_plugins = global_plugins.split(',')

        for long_plugin_name in global_plugins:
            if '.' in long_plugin_name:
                tmpstr = long_plugin_name.split('.')
                plugin_name = tmpstr[-1]
                pfx = '.'.join(tmpstr[:-1])
            else:
                plugin_name = long_plugin_name
                pfx = None
            if plugin_name in self.plugin_dct:
                spec = self.plugin_dct[plugin_name]
                spec.enabled = True
                spec.start = True
            else:
                menu_name = f"{plugin_name} [G]"
                spec = Bunch(name=plugin_name, module=plugin_name,
                             ptype='global', tab=plugin_name,
                             menu=menu_name, category="Custom",
                             enabled=True, start=True,
                             workspace='right', pfx=pfx)
                self.add_plugin_spec(spec)

        # Load any custom local plugins named on command line or in
        # general.cfg
        local_plugins = self.settings.get('local_plugins', [])
        if not isinstance(local_plugins, list):
            local_plugins = local_plugins.split(',')

        for long_plugin_name in local_plugins:
            if '.' in long_plugin_name:
                tmpstr = long_plugin_name.split('.')
                plugin_name = tmpstr[-1]
                pfx = '.'.join(tmpstr[:-1])
            else:
                plugin_name = long_plugin_name
                pfx = None
            if plugin_name in self.plugin_dct:
                spec = self.plugin_dct[plugin_name]
                spec.enabled = True
            else:
                spec = Bunch(module=plugin_name, workspace='dialogs',
                             ptype='local', category="Custom",
                             hidden=False, pfx=pfx, enabled=True)
                self.add_plugin_spec(spec)

        # Mark disabled plugins (command-line has precedence)
        for spec in self.plugins:
            if spec.module.lower() in disabled_plugins:
                spec['enabled'] = False

        # submit plugin specs to shell
        ginga_shell.set_plugins(self.plugins)

        # start any plugins that have start=True
        ginga_shell.boot_plugins()
        ginga_shell.update_pending()

        # TEMP?
        tab_names = [name.lower()
                     for name in ginga_shell.ds.get_tabnames(group=None)]
        if 'info' in tab_names:
            ginga_shell.ds.raise_tab('Info')
        if 'synopsis' in tab_names:
            ginga_shell.ds.raise_tab('Synopsis')
        if 'thumbs' in tab_names:
            ginga_shell.ds.raise_tab('Thumbs')

        # Add custom channels
        channels = self.settings.get('channels', self.channels)
        if not isinstance(channels, list):
            channels = channels.split(',')

        if len(channels) > 0:
            # populate the initial channel lineup
            for item in channels:
                if isinstance(item, str):
                    chname, wsname = item, None
                else:
                    chname, wsname = item
                ginga_shell.add_channel(chname, workspace=wsname)

            ginga_shell.change_channel(chname)

        # User configuration (custom star catalogs, etc.)
        if have_app_config:
            try:
                if hasattr(app_config, 'post_gui_config'):
                    app_config.post_gui_config(ginga_shell)

            except Exception as e:
                self.logger.error("Error processing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Redirect warnings to logger
        for hdlr in self.logger.handlers:
            logging.getLogger('py.warnings').addHandler(hdlr)

        return ginga_shell

    def process_args(self, args):
        """
        Process command line arguments.
        """
        # Display banner the first time run, unless suppressed
        show_banner = (self.appname == 'ginga')
        try:
            show_banner = self.settings.get('showBanner')

        except KeyError:
            # disable for subsequent runs
            self.settings.set(showBanner=False)
            if not os.path.exists(self.settings.preffile):
                self.settings.save()

        if len(args) == 0 and show_banner:
            self.ginga_shell.banner()

        # Handle inputs like "*.fits[ext]" that sys cmd cannot auto expand.
        expanded_args = []
        for imgfile in args:
            if '*' in imgfile:
                if '[' in imgfile and imgfile.endswith(']'):
                    s = imgfile.split('[')
                    ext = '[' + s[1]
                    imgfile = s[0]
                else:
                    ext = ''
                for fname in glob.iglob(imgfile):
                    expanded_args.append(fname + ext)
            else:
                expanded_args.append(imgfile)

        channels = self.ginga_shell.get_channel_names()
        if len(channels) > 0:
            # Assume remaining arguments are fits files and load them.
            if not self.settings.get('separate_channels', False):
                chname = channels[0]
                self.ginga_shell.gui_do(self.ginga_shell.open_uris,
                                        expanded_args,
                                        chname=chname)
            else:
                i = 0
                num_channels = len(channels)
                for imgfile in expanded_args:
                    if i < num_channels:
                        chname = channels[i]
                        i = i + 1
                    else:
                        channel = self.ginga_shell.add_channel_auto()
                        chname = channel.name
                    self.ginga_shell.gui_do(self.ginga_shell.open_uris,
                                            [imgfile],
                                            chname=chname)

    def run(self):
        """
        Activate and run the GUI event loop.
        """
        disable_warnings()
        try:
            try:
                # if there is a network component, start it
                if hasattr(self.ginga_shell, 'start'):
                    self.logger.info("starting network interface...")
                    self.ginga_shell.start()

                if hasattr(self.ginga_shell, 'get_url'):
                    base_url = self.ginga_shell.get_url()
                    if base_url is not None:
                        print(f"visit {base_url} to view the application")
                        self.logger.info(f"visit {base_url} to view the application")

                # Main loop to handle GUI events
                self.logger.info("entering mainloop...")
                self.ginga_shell.mainloop(timeout=0.001)

            except KeyboardInterrupt:
                self.logger.error("Received keyboard interrupt!")

        finally:
            self.logger.info("Shutting down...")
            self.ev_quit.set()

        sys.exit(0)

    def main(self, options, args):
        """
        Main routine for running the reference viewer.

        `options` is a ArgumentParser object that has been populated with
        values from parsing the command line.  It should at least include
        the options from add_default_options()

        `args` is a list of arguments to the viewer after parsing out
        options.  It should contain a list of files or URLs to load.
        """
        logname = self.appname.lower().replace(' ', '_')

        # create a logger
        self.logger = log.get_logger(name=logname, options=options)
        if self.ev_quit is None:
            self.ev_quit = threading.Event()

        if hasattr(options, 'basedir') and options.basedir is not None:
            # command line option overrules
            self.basedir = os.path.expanduser(options.basedir)
        if self.basedir is not None:
            # custom basedir
            paths.set_home(self.basedir)
        else:
            # stock ginga basedir
            self.basedir = paths.ginga_home

        # get settings (preferences)
        if not os.path.exists(self.basedir):
            try:
                os.mkdir(self.basedir)
            except OSError as e:
                self.logger.warning(
                    "Couldn't create %s settings area (%s): %s" % (
                        self.appname, self.basedir, str(e)))
                self.logger.warning("Preferences will not be able to be saved")

        # set up preferences
        self.prefs = Settings.Preferences(basefolder=self.basedir,
                                          logger=self.logger)

        # general settings control initialization of viewer
        settings = self.prefs.create_category('general')
        settings.set_defaults(appname=self.appname,
                              title=self.appname.capitalize(),
                              useMatplotlibColormaps=False,
                              widgetSet='choose',
                              WCSpkg='choose', FITSpkg='choose',
                              suppress_fits_warnings=False,
                              recursion_limit=2000,
                              # this only takes effect if we are using
                              # the pgwidgets backend
                              http_server=True,
                              min_threads=2,
                              num_threads=max(os.cpu_count(), 10),
                              threadpool_analyze_interval_sec=None,
                              pluginmgr_allow_nonsingletons=True,
                              icc_working_profile=None,
                              font_scaling_factor=None,
                              save_layout=True,
                              use_opengl=False,
                              layout_file='layout.json',
                              plugin_file='plugins.yml',
                              channel_prefix="Image")
        settings.load(onError='silent')
        self.settings = settings

        # ------ command line overrides for various settings -----
        #
        if hasattr(options, 'rc_port') and options.rc_port is not None:
            # user specified a custom Remote Control port
            settings.set(grc_port=options.rc_port)

        if hasattr(options, 'toolkit') and options.toolkit is not None:
            settings.set(widgetSet=options.toolkit)

        # User wants to customize the WCS package?
        if hasattr(options, 'wcspkg') and options.wcspkg is not None:
            settings.set(WCSpkg=options.wcspkg)

        # User wants to customize the FITS package?
        if hasattr(options, 'fitspkg') and options.fitspkg is not None:
            settings.set(FITSpkg=options.fitspkg)

        if (hasattr(options, 'suppress_fits_warnings') and
            options.suppress_fits_warnings):
            settings.set(suppress_fits_warnings=options.suppress_fits_warnings)

        # number of threads
        if hasattr(options, 'numthreads') and options.numthreads is not None:
            settings.set(num_threads=options.numthreads)
        if hasattr(options, 'minthreads') and options.minthreads is not None:
            settings.set(min_threads=options.minthreads)

        # OpenGL
        if hasattr(options, 'opengl') and options.opengl:
            settings.set(use_opengl=True)

        # restore the window to approximate
        if hasattr(options, 'norestore'):
            settings.set(ignore_saved_layout=options.norestore)

        # did user specify a particular geometry?
        if hasattr(options, 'geometry') and options.geometry is not None:
            settings.set(geometry=options.geometry)

        if (hasattr(options, 'disable_plugins') and
            options.disable_plugins is not None):
            settings.set(disable_plugins=options.disable_plugins)

        if hasattr(options, 'modules') and options.modules is not None:
            settings.set(global_plugins=options.modules)

        if hasattr(options, 'plugins') and options.plugins is not None:
            settings.set(local_plugins=options.plugins)

        if hasattr(options, 'channels') and options.channels is not None:
            settings.set(channels=options.channels)

        if hasattr(options, 'nosplash'):
            settings.set(showBanner=options.nosplash)

        if hasattr(options, 'separate_channels'):
            settings.set(separate_channels=options.separate_channels)

        # --------------------------------------------------------
        self.setup()

        # process non-option command line args
        self.process_args(args)

        # run the app event loop
        self.run()


def _default_showwarning(message, category, filename, lineno, file=None,
                         line=None):
    if file is None:
        file = sys.stderr
    try:
        text = warnings.formatwarning(message, category, filename,
                                      lineno, line)
        file.write(text)
    except OSError:
        pass


def disable_warnings():
    logging.captureWarnings(False)
    warnings.showwarning = _default_showwarning


def reference_viewer(sys_argv):
    """Create reference viewer from command line."""
    viewer = ReferenceViewer(layout=default_layout, plugins=plugins,
                             appname='ginga', basedir=None, channels=['Image'])
    viewer.add_default_plugins()
    viewer.add_separately_distributed_plugins()

    # Parse command line options with argparse module
    from argparse import ArgumentParser

    argprs = ArgumentParser(description="Run the Ginga reference viewer.")
    viewer.add_default_options(argprs)
    argprs.add_argument('-V', '--version', action='version',
                        version='%(prog)s {}'.format(version.version))
    (options, args) = argprs.parse_known_args(sys_argv[1:])

    if options.display:
        os.environ['DISPLAY'] = options.display

    viewer.main(options, args)


def _main():
    """Run from command line."""
    reference_viewer(sys.argv)

# END
