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
import traceback

if sys.version_info < (3, 8):
    # Python 3.7
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points

# Local application imports
from ginga.misc.Bunch import Bunch
from ginga.misc import Task, ModuleManager, Settings, log
import ginga.version as version
import ginga.toolkit as ginga_toolkit
from ginga.util import paths, rgb_cms, json

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
          ptype='global'),
    Bunch(module='Toolbar', workspace='toolbar', start=True,
          hidden=True, category='System', menu="Toolbar [G]", ptype='global'),
    Bunch(module='Pan', workspace='uleft', start=True,
          hidden=True, category='System', menu="Pan [G]", ptype='global'),
    Bunch(module='Info', tab='Synopsis', workspace='lleft', start=True,
          hidden=True, category='System', menu="Info [G]", ptype='global'),
    Bunch(module='Thumbs', tab='Thumbs', workspace='right', start=True,
          hidden=True, category='System', menu="Thumbs [G]", ptype='global'),
    Bunch(module='Contents', tab='Contents', workspace='right', start=True,
          hidden=True, category='System', menu="Contents [G]", ptype='global'),
    Bunch(module='Colorbar', workspace='cbar', start=True,
          hidden=True, category='System', menu="Colorbar [G]", ptype='global'),
    Bunch(module='Cursor', workspace='readout', start=True,
          hidden=True, category='System', menu="Cursor [G]", ptype='global'),
    Bunch(module='Errors', tab='Errors', workspace='right', start=True,
          hidden=True, category='System', menu="Errors [G]", ptype='global'),
    Bunch(module='Downloads', tab='Downloads', workspace='right', start=False,
          menu="Downloads [G]", category='Utils', ptype='global'),

    # optional, user-started plugins
    Bunch(module='Blink', tab='Blink Channels', workspace='right', start=False,
          menu="Blink Channels [G]", category='Analysis', ptype='global'),
    Bunch(module='Blink', workspace='dialogs', menu='Blink Images',
          category='Analysis', ptype='local'),
    Bunch(module='Crosshair', workspace='left', category='Analysis',
          ptype='local'),
    Bunch(module='Cuts', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='LineProfile', workspace='dialogs',
          category='Analysis.Datacube', ptype='local'),
    Bunch(module='Histogram', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='Overlays', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='Pick', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='PixTable', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='TVMark', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='TVMask', workspace='dialogs', category='Analysis',
          ptype='local'),
    Bunch(module='WCSMatch', tab='WCSMatch', workspace='right', start=False,
          menu="WCS Match [G]", category='Analysis', ptype='global'),
    Bunch(module='Command', tab='Command', workspace='lleft', start=False,
          menu="Command Line [G]", category='Debug', ptype='global'),
    Bunch(module='Log', tab='Log', workspace='right', start=False,
          menu="Logger Info [G]", category='Debug', ptype='global'),
    Bunch(module='MultiDim', workspace='lleft', category='Navigation',
          ptype='local'),
    Bunch(module='RC', tab='RC', workspace='right', start=False,
          menu="Remote Control [G]", category='Remote', ptype='global'),
    Bunch(module='SAMP', tab='SAMP', workspace='right', start=False,
          menu="SAMP Client [G]", category='Remote', ptype='global'),
    Bunch(module='Compose', workspace='dialogs', category='RGB', ptype='local'),
    Bunch(module='ScreenShot', workspace='dialogs', category='RGB',
          ptype='local'),
    Bunch(module='ColorMapPicker', tab='ColorMapPicker',
          menu="Set Color Map [G]", workspace='right', start=False,
          category='RGB', ptype='global'),
    Bunch(module='PlotTable', workspace='dialogs', category='Table',
          ptype='local'),
    Bunch(module='Catalogs', workspace='dialogs', category='Utils',
          ptype='local'),
    Bunch(module='Drawing', workspace='dialogs', category='Utils',
          ptype='local'),
    ## Bunch(module='Pipeline', workspace='dialogs', category='Utils',
    ##       ptype='local'),
    Bunch(module='FBrowser', workspace='dialogs', category='Utils',
          ptype='local'),
    Bunch(module='ChangeHistory', tab='History', workspace='right',
          menu="History [G]", start=False, category='Utils', ptype='global'),
    Bunch(module='Mosaic', workspace='dialogs', category='Utils', ptype='local'),
    Bunch(module='Collage', workspace='dialogs', category='Utils', ptype='local'),
    Bunch(module='FBrowser', tab='Open File', workspace='right',
          menu="Open File [G]", start=False, category='Utils', ptype='global'),
    Bunch(module='Preferences', workspace='dialogs', category='Utils',
          ptype='local'),
    Bunch(module='Ruler', workspace='dialogs', category='Utils', ptype='local'),
    # TODO: Add SaveImage to File menu.
    Bunch(module='SaveImage', tab='SaveImage', workspace='right',
          menu="Save File [G]", start=False, category='Utils', ptype='global'),
    Bunch(module='WCSAxes', workspace='dialogs', category='Utils',
          ptype='local'),
    Bunch(module='WBrowser', tab='Help', workspace='channels', start=False,
          menu="Help [G]", category='Help', ptype='global'),
    Bunch(module='Header', tab='Header', workspace='left', start=False,
          menu="Header [G]", hidden=False, category='Utils', ptype='global'),
    Bunch(module='Zoom', tab='Zoom', workspace='left', start=False,
          menu="Zoom [G]", category='Utils', ptype='global'),
]


class ReferenceViewer(object):
    """
    This class exists solely to be able to customize the reference
    viewer startup.
    """
    def __init__(self, layout=default_layout, plugins=plugins):
        self.layout = layout
        self.channels = ['Image']
        self.default_plugins = plugins
        self.plugins = []

    def add_plugin_spec(self, spec):
        self.plugins.append(spec)

    def clear_default_plugins(self):
        self.plugins = []

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
        groups = ['ginga.rv.plugins']
        available_methods = []

        for group in groups:
            discovered_plugins = entry_points().get(group, [])
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
        add_argument("--debug", dest="debug", default=False,
                     action="store_true",
                     help="Enter the pdb debugger on main()")
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
                     default=30, metavar="NUM",
                     help="Start NUM threads in thread pool")
        add_argument("--opencv", dest="opencv", default=False,
                     action="store_true",
                     help="Use OpenCv acceleration")
        add_argument("--opengl", dest="opengl", default=False,
                     action="store_true",
                     help="Use OpenGL acceleration")
        add_argument("--plugins", dest="plugins", metavar="NAMES",
                     help="Specify additional plugins to load")
        add_argument("--profile", dest="profile", action="store_true",
                     default=False,
                     help="Run the profiler on main()")
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

        # Create a logger
        logger = log.get_logger(name='ginga', options=options)

        if options.basedir is not None:
            paths.ginga_home = os.path.expanduser(options.basedir)

        # Get settings (preferences)
        basedir = paths.ginga_home
        if not os.path.exists(basedir):
            try:
                os.mkdir(basedir)
            except OSError as e:
                logger.warning(
                    "Couldn't create ginga settings area (%s): %s" % (
                        basedir, str(e)))
                logger.warning("Preferences will not be able to be saved")

        # Set up preferences
        prefs = Settings.Preferences(basefolder=basedir, logger=logger)
        settings = prefs.create_category('general')
        settings.set_defaults(useMatplotlibColormaps=False,
                              widgetSet='choose',
                              WCSpkg='choose', FITSpkg='choose',
                              suppress_fits_warnings=False,
                              recursion_limit=2000,
                              icc_working_profile=None,
                              font_scaling_factor=None,
                              save_layout=True,
                              use_opengl=False,
                              layout_file='layout',
                              plugin_file='plugins.json',
                              channel_prefix="Image")
        settings.load(onError='silent')

        # default of 1000 is a little too small
        sys.setrecursionlimit(settings.get('recursion_limit'))

        # So we can find our plugins
        sys.path.insert(0, basedir)
        package_home = os.path.split(sys.modules['ginga.version'].__file__)[0]
        child_dir = os.path.join(package_home, 'rv', 'plugins')
        sys.path.insert(0, child_dir)
        plugin_dir = os.path.join(basedir, 'plugins')
        sys.path.insert(0, plugin_dir)

        gc = os.path.join(basedir, "ginga_config.py")
        have_ginga_config = os.path.exists(gc)

        # User configuration, earliest possible intervention
        if have_ginga_config:
            try:
                import ginga_config

                if hasattr(ginga_config, 'init_config'):
                    ginga_config.init_config(self)

            except Exception as e:
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))

                except Exception:
                    tb_str = "Traceback information unavailable."

                logger.error("Error processing Ginga config file: %s" % (
                    str(e)))
                logger.error("Traceback:\n%s" % (tb_str))

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
            from ginga.util import io_fits, loader
            if fitspkg != 'choose':
                assert io_fits.use(fitspkg) is True
                # opener name is not necessarily the same
                opener = loader.get_opener(io_fits.fitsLoaderClass.name)
                # set this opener as the priority one
                opener.priority = -99

        except Exception as e:
            logger.warning(
                "failed to set FITS package preference '{}': {}".format(fitspkg, e))

        # Check whether user specified deprecated --opencv option
        if options.opencv:
            logger.warning("--opencv switch is deprecated; "
                           "OpenCv will be used by default if installed")

        if options.opengl:
            settings.set(use_opengl=True)

        # Create the dynamic module manager
        mm = ModuleManager.ModuleManager(logger)

        # Create and start thread pool
        ev_quit = threading.Event()
        thread_pool = Task.ThreadPool(options.numthreads, logger,
                                      ev_quit=ev_quit)
        thread_pool.startall()

        # Create the Ginga main object
        ginga_shell = GingaShell(logger, thread_pool, mm, prefs,
                                 ev_quit=ev_quit)

        layout_file = os.path.join(basedir, settings.get('layout_file',
                                                         'layout'))
        ginga_shell.set_layout(self.layout, layout_file=layout_file,
                               save_layout=settings.get('save_layout', True))

        # User configuration (custom star catalogs, etc.)
        if have_ginga_config:
            try:
                if hasattr(ginga_config, 'pre_gui_config'):
                    ginga_config.pre_gui_config(ginga_shell)
            except Exception as e:
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))

                except Exception:
                    tb_str = "Traceback information unavailable."

                logger.error("Error importing Ginga config file: %s" % (
                    str(e)))
                logger.error("Traceback:\n%s" % (tb_str))

        # Build desired layout
        ginga_shell.build_toplevel(ignore_saved_layout=options.norestore)

        # Does user have a customized plugin setup?  If so, override the
        # default plugins to be that
        plugin_file = settings.get('plugin_file', None)
        if plugin_file is not None:
            plugin_file = os.path.join(basedir, plugin_file)
            if os.path.exists(plugin_file):
                logger.info("Reading plugin file '%s'..." % (plugin_file))
                try:
                    with open(plugin_file, 'r') as in_f:
                        buf = in_f.read()
                        self.plugins = json.loads(buf)
                except Exception as e:
                    logger.error("Error reading plugin file: %s" % (str(e)))

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

        # Add GUI log handler (for "Log" global plugin)
        guiHdlr = GuiLogHandler(ginga_shell)
        guiHdlr.setLevel(options.loglevel)
        fmt = logging.Formatter(log.LOG_FORMAT)
        guiHdlr.setFormatter(fmt)
        logger.addHandler(guiHdlr)

        # Load any custom modules
        if options.modules is not None:
            modules = options.modules.split(',')
        else:
            modules = settings.get('global_plugins', [])
            if not isinstance(modules, list):
                modules = modules.split(',')

        for long_plugin_name in modules:
            if '.' in long_plugin_name:
                tmpstr = long_plugin_name.split('.')
                plugin_name = tmpstr[-1]
                pfx = '.'.join(tmpstr[:-1])
            else:
                plugin_name = long_plugin_name
                pfx = None
            menu_name = "%s [G]" % (plugin_name)
            spec = Bunch(name=plugin_name, module=plugin_name,
                         ptype='global', tab=plugin_name,
                         menu=menu_name, category="Custom",
                         workspace='right', pfx=pfx)
            self.add_plugin_spec(spec)

        # Load any custom local plugins
        if options.plugins is not None:
            plugins = options.plugins.split(',')
        else:
            plugins = settings.get('local_plugins', [])
            if not isinstance(plugins, list):
                plugins = plugins.split(',')

        for long_plugin_name in plugins:
            if '.' in long_plugin_name:
                tmpstr = long_plugin_name.split('.')
                plugin_name = tmpstr[-1]
                pfx = '.'.join(tmpstr[:-1])
            else:
                plugin_name = long_plugin_name
                pfx = None
            spec = Bunch(module=plugin_name, workspace='dialogs',
                         ptype='local', category="Custom",
                         hidden=False, pfx=pfx)
            self.add_plugin_spec(spec)

        # Mark disabled plugins
        for spec in self.plugins:
            if spec.get('enabled', None) is None:
                spec['enabled'] = (False if spec.module.lower() in disabled_plugins
                                   else True)
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

        if len(channels) == 0:
            # should provide at least one default channel?
            channels = [settings.get('channel_prefix', "Image")]

        # populate the initial channel lineup
        for item in channels:
            if isinstance(item, str):
                chname, wsname = item, None
            else:
                chname, wsname = item
            ginga_shell.add_channel(chname, workspace=wsname)

        ginga_shell.change_channel(chname)

        # User configuration (custom star catalogs, etc.)
        if have_ginga_config:
            try:
                if hasattr(ginga_config, 'post_gui_config'):
                    ginga_config.post_gui_config(ginga_shell)

            except Exception as e:
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))

                except Exception:
                    tb_str = "Traceback information unavailable."

                logger.error("Error processing Ginga config file: %s" % (
                    str(e)))
                logger.error("Traceback:\n%s" % (tb_str))

        # Redirect warnings to logger
        for hdlr in logger.handlers:
            logging.getLogger('py.warnings').addHandler(hdlr)

        # Display banner the first time run, unless suppressed
        show_banner = True
        try:
            show_banner = settings.get('showBanner')

        except KeyError:
            # disable for subsequent runs
            settings.set(showBanner=False)
            if not os.path.exists(settings.preffile):
                settings.save()

        if (not options.nosplash) and (len(args) == 0) and show_banner:
            ginga_shell.banner(raiseTab=True)

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

    # TO BE DEPRECATED-- DO NOT USE!!!

    def add_global_plugin_spec(self, spec):
        if 'ptype' not in spec:
            spec['ptype'] = 'global'
        self.plugins.append(spec)

    def add_local_plugin_spec(self, spec):
        if 'ptype' not in spec:
            spec['ptype'] = 'local'
        self.plugins.append(spec)

    def add_local_plugin(self, module_name, ws_name,
                         path=None, klass=None, pfx=None, category=None):
        self.add_plugin_spec(
            Bunch(module=module_name, workspace=ws_name, category=category,
                  ptype='local', path=path, klass=klass, pfx=pfx))

    def add_global_plugin(self, module_name, ws_name,
                          path=None, klass=None, category='Global',
                          tab_name=None, start_plugin=True, pfx=None):
        self.add_plugin_spec(
            Bunch(module=module_name, workspace=ws_name, tab=tab_name,
                  path=path, klass=klass, category=category,
                  ptype='global', start=start_plugin, pfx=pfx))


def reference_viewer(sys_argv):
    """Create reference viewer from command line."""
    viewer = ReferenceViewer(layout=default_layout)
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

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('viewer.main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys_argv[0]))
        profile.runctx('viewer.main(options, args)',
                       dict(options=options, args=args, viewer=viewer), {})

    else:
        viewer.main(options, args)


def _main():
    """Run from command line."""
    reference_viewer(sys.argv)

# END
