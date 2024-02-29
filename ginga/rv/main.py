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
import threading

# 3rd party
import yaml

# Local application imports
from ginga.misc.Bunch import Bunch
from ginga.misc import Task, ModuleManager, Settings, log
import ginga.version as version
import ginga.toolkit as ginga_toolkit
from ginga.util import paths, rgb_cms, compat, loader

# Catch warnings
logging.captureWarnings(True)

__all__ = ['ReferenceViewer']

default_layout = ['seq', {},
                   ['vbox', dict(name='top', width=1400, height=700),  # noqa
                    dict(row=['hbox', dict(name='menu')],
                         stretch=0),
                    dict(row=['hpanel', dict(name='hpnl'),
                     ['ws', dict(name='left', wstype='tabs',  # noqa
                                 width=300, height=-1, group=2),
                      # (tabname, layout), ...
                      [("Info", ['vpanel', {},
                                 ['ws', dict(name='uleft', wstype='stack',
                                             height=250, group=3)],
                                 ['ws', dict(name='lleft', wstype='tabs',
                                             height=330, group=3)],
                                 ]
                        )]],
                     ['vbox', dict(name='main', width=600),
                      dict(row=['ws', dict(name='channels', wstype='tabs',
                                           group=1, use_toolbar=True,
                                           default=True)],
                           stretch=1),
                      dict(row=['ws', dict(name='cbar', wstype='stack',
                                           group=99)], stretch=0),
                      dict(row=['ws', dict(name='readout', wstype='stack',
                                           group=99)], stretch=0),
                      dict(row=['ws', dict(name='operations', wstype='stack',
                                           group=99)], stretch=0),
                      ],
                     ['ws', dict(name='right', wstype='tabs',
                                 width=400, height=-1, group=2),
                      # (tabname, layout), ...
                      [("Dialogs", ['ws', dict(name='dialogs', wstype='tabs',
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
    Bunch(module='Operations', workspace='operations', start=True,
          hidden=True, category='System', menu="Operations [G]",
          ptype='global', enabled=True),
    Bunch(module='Toolbar', workspace='toolbar', start=True,
          hidden=True, category='System', menu="Toolbar [G]", ptype='global',
          enabled=True),
    Bunch(module='Pan', workspace='uleft', start=True,
          hidden=True, category='System', menu="Pan [G]", ptype='global',
          enabled=True),
    Bunch(module='Info', tab='Synopsis', workspace='lleft', start=True,
          hidden=True, category='System', menu="Info [G]", ptype='global',
          enabled=True),
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
          ptype='local', enabled=True),
    Bunch(module='LineProfile', workspace='dialogs',
          category='Analysis.Datacube', ptype='local', enabled=True),
    Bunch(module='Histogram', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='Overlays', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
    Bunch(module='Pick', workspace='dialogs', category='Analysis',
          ptype='local', enabled=True),
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
          ptype='local', enabled=True),
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
          ptype='local', enabled=True),
    Bunch(module='PlotTable', workspace='dialogs', category='Table',
          ptype='local', enabled=True),
    Bunch(module='Catalogs', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='Drawing', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='AutoLoad', workspace='dialogs', category='Utils',
          ptype='local', enabled=False),
    Bunch(module='Pipeline', workspace='dialogs', category='Utils',
          ptype='local', enabled=False),
    Bunch(module='FBrowser', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='ChangeHistory', tab='History', workspace='right',
          menu="History [G]", start=False, category='Utils', ptype='global',
          enabled=True),
    Bunch(module='Mosaic', workspace='dialogs', category='Utils', ptype='local',
          enabled=True),
    Bunch(module='Collage', workspace='dialogs', category='Utils', ptype='local',
          enabled=True),
    Bunch(module='FBrowser', tab='Open File', workspace='right',
          name="FBrowser[G]", menu="Open File [G]", start=False,
          category='Utils', ptype='global', enabled=True),
    Bunch(module='Preferences', workspace='dialogs', category='Utils',
          ptype='local', enabled=True),
    Bunch(module='Ruler', workspace='dialogs', category='Utils', ptype='local',
          enabled=True),
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


class ReferenceViewer(object):
    """
    This class exists solely to be able to customize the reference
    viewer startup.
    """
    def __init__(self, layout=default_layout, plugins=plugins, appname='ginga',
                 basedir=None, channels=None):
        self.appname = appname
        self.basedir = basedir
        self.layout = layout
        if channels is None:
            channels = ['Image']
        self.channels = channels
        self.default_plugins = plugins
        self.plugins = []
        self.plugin_dct = dict()

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
                     help="Start NUM threads in thread pool")
        add_argument("--opengl", dest="opengl", default=False,
                     action="store_true",
                     help="Use OpenGL acceleration")
        add_argument("--plugins", dest="plugins", metavar="NAMES",
                     help="Specify additional plugins to load")
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

        # Create a logger
        logger = log.get_logger(name=logname, options=options)

        if options.basedir is not None:
            self.basedir = os.path.expanduser(options.basedir)
        if self.basedir is not None:
            paths.ginga_home = self.basedir
        else:
            self.basedir = paths.ginga_home

        # Get settings (preferences)
        if not os.path.exists(self.basedir):
            try:
                os.mkdir(self.basedir)
            except OSError as e:
                logger.warning(
                    "Couldn't create %s settings area (%s): %s" % (
                        self.appname, self.basedir, str(e)))
                logger.warning("Preferences will not be able to be saved")

        # Set up preferences
        prefs = Settings.Preferences(basefolder=self.basedir, logger=logger)
        settings = prefs.create_category('general')
        settings.set_defaults(title=self.appname.capitalize(),
                              useMatplotlibColormaps=False,
                              widgetSet='choose',
                              WCSpkg='choose', FITSpkg='choose',
                              suppress_fits_warnings=False,
                              recursion_limit=2000,
                              num_threads=30,
                              icc_working_profile=None,
                              font_scaling_factor=None,
                              save_layout=True,
                              use_opengl=False,
                              layout_file='layout.json',
                              plugin_file='plugins.yml',
                              channel_prefix="Image")
        settings.load(onError='silent')

        # default of 1000 is a little too small
        sys.setrecursionlimit(settings.get('recursion_limit'))

        # So we can find our plugins
        sys.path.insert(0, self.basedir)
        package_home = os.path.split(sys.modules['ginga.version'].__file__)[0]
        child_dir = os.path.join(package_home, 'rv', 'plugins')
        sys.path.insert(0, child_dir)
        plugin_dir = os.path.join(self.basedir, 'plugins')
        sys.path.insert(0, plugin_dir)

        # Create the dynamic module manager
        mm = ModuleManager.ModuleManager(logger)

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
                logger.error("Error processing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Choose a toolkit
        if options.toolkit:
            toolkit = options.toolkit
        else:
            toolkit = settings.get('widgetSet', 'choose')

        if toolkit == 'choose':
            try:
                ginga_toolkit.choose()
            except ImportError as e:
                print("UI toolkit choose error: %s" % str(e))
                sys.exit(1)
        else:
            ginga_toolkit.use(toolkit)

        tkname = ginga_toolkit.get_family()
        logger.info("Chosen toolkit (%s) family is '%s'" % (
            ginga_toolkit.toolkit, tkname))

        # these imports have to be here, otherwise they force the choice
        # of toolkit too early
        from ginga.rv.Control import GingaShell, GuiLogHandler

        if settings.get('useMatplotlibColormaps', False):
            # Add matplotlib color maps if matplotlib is installed
            try:
                from ginga import cmap
                cmap.add_matplotlib_cmaps(fail_on_import_error=False)
            except Exception as e:
                logger.warning(
                    "failed to load matplotlib colormaps: %s" % (str(e)))

        # Set a working RGB ICC profile if user has one
        working_profile = settings.get('icc_working_profile', None)
        rgb_cms.working_profile = working_profile

        # User wants to customize the WCS package?
        if options.wcspkg:
            wcspkg = options.wcspkg
        else:
            wcspkg = settings.get('WCSpkg', 'choose')

        try:
            from ginga.util import wcsmod
            if wcspkg != 'choose':
                assert wcsmod.use(wcspkg) is True
        except Exception as e:
            logger.warning(
                "failed to set WCS package preference '{}': {}".format(wcspkg, e))

        # User wants to customize the FITS package?
        if options.fitspkg:
            fitspkg = options.fitspkg
        else:
            fitspkg = settings.get('FITSpkg', 'choose')

        if options.suppress_fits_warnings:
            supp_warn = options.suppress_fits_warnings
        else:
            supp_warn = settings.get('suppress_fits_warnings', False)
        if supp_warn:
            import warnings
            from astropy.io import fits
            warnings.simplefilter('ignore', fits.verify.VerifyWarning)

        try:
            from ginga.util.io import io_fits
            if fitspkg != 'choose':
                assert io_fits.use(fitspkg) is True

        except Exception as e:
            logger.warning(
                "failed to set FITS package preference '{}': {}".format(fitspkg, e))

        ev_quit = threading.Event()
        # Create and start thread pool
        num_threads = settings.get('num_threads', 30)
        if options.numthreads is not None:
            num_threads = options.numthreads
        thread_pool = Task.ThreadPool(num_threads, logger,
                                      ev_quit=ev_quit)
        thread_pool.startall()

        # Create the Ginga main object
        ginga_shell = GingaShell(logger, thread_pool, mm, prefs,
                                 ev_quit=ev_quit)

        if options.opengl:
            settings.set(use_opengl=True)

        layout_file = os.path.join(self.basedir, settings.get('layout_file',
                                                              'layout.json'))
        ginga_shell.set_layout(self.layout, layout_file=layout_file,
                               save_layout=settings.get('save_layout', True))

        # User configuration (custom star catalogs, etc.)
        if have_app_config:
            try:
                if hasattr(app_config, 'pre_gui_config'):
                    app_config.pre_gui_config(ginga_shell)
            except Exception as e:
                logger.error("Error importing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Build desired layout
        ginga_shell.build_toplevel(ignore_saved_layout=options.norestore)

        # Did user specify a particular geometry?
        if options.geometry:
            ginga_shell.set_geometry(options.geometry)

        # make the list of disabled plugins
        if options.disable_plugins is not None:
            disabled_plugins = options.disable_plugins.lower().split(',')
        else:
            disabled_plugins = settings.get('disable_plugins', [])
            if not isinstance(disabled_plugins, list):
                disabled_plugins = disabled_plugins.lower().split(',')
        disabled_plugins = set(disabled_plugins)

        # Add GUI log handler (for "Log" global plugin)
        guiHdlr = GuiLogHandler(ginga_shell)
        guiHdlr.setLevel(options.loglevel)
        fmt = logging.Formatter(log.LOG_FORMAT)
        guiHdlr.setFormatter(fmt)
        logger.addHandler(guiHdlr)

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
                logger.error(f"failed to process loader file '{path}': {e}",
                             exc_info=True)

        # Does user have a saved plugin setup?  If so, check which
        # plugins should be disabled, or have a customized category or
        # workspace
        plugin_file = settings.get('plugin_file', None)
        if plugin_file is not None:
            plugin_file = os.path.join(self.basedir, plugin_file)
            if os.path.exists(plugin_file):
                logger.info("Reading plugin file '%s'..." % (plugin_file))
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
                                         'workspace', 'tab', 'menu',
                                         'pfx', 'optray']:
                                if name in dct:
                                    spec[name] = dct[name]
                            if spec['ptype'] == 'global':
                                spec['start'] = dct.get('start',
                                                        spec.get('start', False))
                        else:
                            # unknown plugin
                            spec = Bunch(dct)
                            self.add_plugin_spec(spec)

                except Exception as e:
                    logger.error(f"Error reading plugin file: {e}",
                                 exc_info=True)

        # Load any custom global plugins named on command line or in
        # general.cfg
        if options.modules is not None:
            global_plugins = options.modules.split(',')
        else:
            global_plugins = settings.get('global_plugins', [])
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
        if options.plugins is not None:
            local_plugins = options.plugins.split(',')
        else:
            local_plugins = settings.get('local_plugins', [])
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
        if options.channels is not None:
            channels = options.channels.split(',')
        else:
            channels = settings.get('channels', self.channels)
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
                logger.error("Error processing %s config file: %s" % (
                    self.appname, str(e)), exc_info=True)

        # Redirect warnings to logger
        for hdlr in logger.handlers:
            logging.getLogger('py.warnings').addHandler(hdlr)

        # Display banner the first time run, unless suppressed
        show_banner = (self.appname == 'ginga')
        try:
            show_banner = settings.get('showBanner')

        except KeyError:
            # disable for subsequent runs
            settings.set(showBanner=False)
            if not os.path.exists(settings.preffile):
                settings.save()

        if (not options.nosplash) and (len(args) == 0) and show_banner:
            ginga_shell.banner()

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

        if len(channels) > 0:
            # Assume remaining arguments are fits files and load them.
            if not options.separate_channels:
                chname = channels[0]
                ginga_shell.gui_do(ginga_shell.open_uris, expanded_args,
                                   chname=chname)
            else:
                i = 0
                num_channels = len(channels)
                for imgfile in expanded_args:
                    if i < num_channels:
                        chname = channels[i]
                        i = i + 1
                    else:
                        channel = ginga_shell.add_channel_auto()
                        chname = channel.name
                    ginga_shell.gui_do(ginga_shell.open_uris, [imgfile],
                                       chname=chname)

        try:
            try:
                # if there is a network component, start it
                if hasattr(ginga_shell, 'start'):
                    logger.info("starting network interface...")
                    ginga_shell.start()

                # Main loop to handle GUI events
                logger.info("entering mainloop...")
                ginga_shell.mainloop(timeout=0.001)

            except KeyboardInterrupt:
                logger.error("Received keyboard interrupt!")

        finally:
            logger.info("Shutting down...")
            ev_quit.set()

        sys.exit(0)


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
