#
# main.py -- reference viewer for the Ginga toolkit.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""This module handles the main reference viewer."""
from __future__ import print_function

# stdlib imports
import glob
import sys
import os
import logging
import logging.handlers
import threading
import traceback

# Local application imports
from ginga.misc.Bunch import Bunch
from ginga.misc import Task, ModuleManager, Settings, log
import ginga.version as version
import ginga.toolkit as ginga_toolkit
from ginga.util import paths

# Catch warnings
logging.captureWarnings(True)

__all__ = ['ReferenceViewer']

default_layout = ['seq', {},
                   ['vbox', dict(name='top', width=1520, height=900),
                    dict(row=['hbox', dict(name='menu')],
                         stretch=0),
                    dict(row=['hpanel', dict(name='hpnl'),
                     ['ws', dict(name='left', wstype='tabs',
                                 width=300, height=-1, group=2),
                      # (tabname, layout), ...
                      [("Info", ['vpanel', {},
                                 ['ws', dict(name='uleft', wstype='stack',
                                             height=300, group=3)],
                                 ['ws', dict(name='lleft', wstype='tabs',
                                             height=430, group=3)],
                                 ]
                        )]],
                     ['vbox', dict(name='main', width=700),
                      dict(row=['ws', dict(name='channels', wstype='tabs',
                                           group=1, use_toolbar=True)],
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
                     ], stretch=1),
                    dict(row=['ws', dict(name='toolbar', wstype='stack',
                                         height=40, group=2)],
                         stretch=0),
                    dict(row=['hbox', dict(name='status')], stretch=0),
                    ]]

global_plugins = [
    Bunch(module='Operations', workspace='operations', start=True,
          hidden=True, category='system'),
    Bunch(module='Toolbar', workspace='toolbar', start=True,
          hidden=True, category='system'),
    Bunch(module='Pan', workspace='uleft', start=True,
          hidden=True, category='system'),
    Bunch(module='Info', tab='Synopsis', workspace='lleft', start=True,
          hidden=True, category='system'),
    Bunch(module='Header', tab='Header', workspace='left', start=True,
          hidden=True, category='system'),
    Bunch(module='Zoom', tab='Zoom', workspace='left', start=True,
          hidden=True, category='system'),
    Bunch(module='Thumbs', tab='Thumbs', workspace='right', start=True,
          hidden=True, category='system'),
    Bunch(module='Contents', tab='Contents', workspace='right', start=True,
          hidden=True, category='system'),
    Bunch(module='Colorbar', workspace='cbar', start=True,
          hidden=True, category='system'),
    Bunch(module='Cursor', workspace='readout', start=True,
          hidden=True, category='system'),
    Bunch(module='Errors', tab='Errors', workspace='right', start=True,
          hidden=True, category='system'),
    Bunch(module='Command', tab='Command', workspace='lleft', start=False,
          category='Global'),
    Bunch(module='WBrowser', tab='Help', workspace='channels', start=False,
          category='Global'),
    Bunch(module='FBrowser', tab='Open File', workspace='right', start=False,
          category='Global'),
    Bunch(module='Blink', tab='Blink Channels', workspace='right', start=False,
          category='Global'),
    Bunch(module='ColorMapPicker', tab='Color Map Picker', workspace='right',
          start=False, category='Global'),
    # TODO: Move SaveImage to File menu.
    Bunch(module='SaveImage', tab='Save File', workspace='right', start=False,
          category='Global'),
    Bunch(module='RC', tab='RC', workspace='right', start=False,
          category='Global'),
    Bunch(module='WCSMatch', tab='WCSMatch', workspace='right', start=False,
          category='Global'),
    Bunch(module='ChangeHistory', tab='History', workspace='right', start=False,
          category='Global'),
    Bunch(module='SAMP', tab='SAMP', workspace='right', start=False,
          category='Global'),
    Bunch(module='IRAF', tab='IRAF', workspace='right', start=False,
          category='Global'),
    Bunch(module='Log', tab='Log', workspace='right', start=False,
          category='Global'),
    ]

local_plugins = [
    Bunch(module='Pick', workspace='dialogs', category=None),
    Bunch(module='Ruler', workspace='dialogs', category=None),
    Bunch(module='MultiDim', workspace='lleft', category=None),
    Bunch(module='Cuts', workspace='dialogs', category=None),
    Bunch(module='Histogram', workspace='dialogs', category=None),
    Bunch(module='Crosshair', workspace='dialogs', category=None),
    Bunch(module='Overlays', workspace='dialogs', category=None),
    Bunch(module='WCSAxes', workspace='dialogs', category=None),
    Bunch(module='TVMark', workspace='dialogs', category=None),
    Bunch(module='TVMask', workspace='dialogs', category=None),
    Bunch(module='Blink', workspace='dialogs', category=None),
    Bunch(module='LineProfile', workspace='dialogs', category=None),
    Bunch(module='PixTable', workspace='dialogs', category=None),
    Bunch(module='Preferences', workspace='dialogs', category=None),
    Bunch(module='Catalogs', workspace='dialogs', category=None),
    Bunch(module='Mosaic', workspace='dialogs', category=None),
    Bunch(module='Drawing', workspace='dialogs', category=None),
    Bunch(module='FBrowser', workspace='dialogs', category=None),
    Bunch(module='Compose', workspace='dialogs', category=None),
    Bunch(module='PlotTable', workspace='dialogs', category=None),
    Bunch(module='ScreenShot', workspace='dialogs', category=None),
    ]


class ReferenceViewer(object):
    """
    This class exists solely to be able to customize the reference
    viewer startup.
    """
    def __init__(self, layout=default_layout):
        self.local_plugins = []
        self.global_plugins = []
        self.layout = layout

    def add_local_plugin_spec(self, spec):
        self.local_plugins.append(spec)

    def add_global_plugin_spec(self, spec):
        self.global_plugins.append(spec)

    def add_local_plugin(self, module_name, ws_name,
                         path=None, klass=None, pfx=None, category=None):
        self.add_local_plugin_spec(
            Bunch(module=module_name, workspace=ws_name, category=category,
                  path=path, klass=klass, pfx=pfx))

    def add_global_plugin(self, module_name, ws_name,
                          path=None, klass=None, category='Global',
                          tab_name=None, start_plugin=True, pfx=None):
        self.add_global_plugin_spec(
            Bunch(module=module_name, workspace=ws_name, tab=tab_name,
                  path=path, klass=klass, category=category,
                  start=start_plugin, pfx=pfx))

    def clear_default_plugins(self):
        self.local_plugins = []
        self.global_plugins = []

    def add_default_plugins(self, except_global=[], except_local=[]):
        """
        Add the ginga-distributed default set of plugins to the
        reference viewer.
        """
        # add default global plugins
        for spec in global_plugins:
            if spec.module not in except_global:
                self.add_global_plugin_spec(spec)

        # add default local plugins
        for spec in local_plugins:
            if spec.module not in except_local:
                self.add_local_plugin_spec(spec)

    def add_separately_distributed_plugins(self):
        from pkg_resources import iter_entry_points
        groups = ['ginga.rv.plugins']
        available_methods = []

        for group in groups:
            for entry_point in iter_entry_points(group=group, name=None):
                try:
                    method = entry_point.load()
                    available_methods.append(method)

                except Exception as e:
                    print("Error trying to load entry point %s: %s" % (
                        str(entry_point), str(e)))

        for method in available_methods:
            try:
                spec = method()
                if 'start' in spec:
                    # global plugin
                    # TODO: need a better differentiator
                    self.add_global_plugin_spec(spec)
                else:
                    # local plugin
                    self.add_local_plugin_spec(spec)

            except Exception as e:
                print("Error trying to instantiate external plugin using %s: %s" % (
                    str(method), str(e)))

    def add_default_options(self, optprs):
        """
        Adds the default reference viewer startup options to an
        OptionParser instance `optprs`.
        """
        optprs.add_option("--bufsize", dest="bufsize", metavar="NUM",
                          type="int", default=10,
                          help="Buffer length to NUM")
        optprs.add_option('-c', "--channels", dest="channels", default="Image",
                          help="Specify list of channels to create")
        optprs.add_option("--debug", dest="debug", default=False,
                          action="store_true",
                          help="Enter the pdb debugger on main()")
        optprs.add_option("--disable-plugins", dest="disable_plugins",
                          metavar="NAMES",
                          help="Specify plugins that should be disabled")
        optprs.add_option("--display", dest="display", metavar="HOST:N",
                          help="Use X display on HOST:N")
        optprs.add_option("--fitspkg", dest="fitspkg", metavar="NAME",
                          default=None,
                          help="Prefer FITS I/O module NAME")
        optprs.add_option("-g", "--geometry", dest="geometry",
                          default=None, metavar="GEOM",
                          help="X geometry for initial size and placement")
        optprs.add_option("--modules", dest="modules", metavar="NAMES",
                          help="Specify additional modules to load")
        optprs.add_option("--nosplash", dest="nosplash", default=False,
                          action="store_true",
                          help="Don't display the splash screen")
        optprs.add_option("--numthreads", dest="numthreads", type="int",
                          default=30, metavar="NUM",
                          help="Start NUM threads in thread pool")
        optprs.add_option("--opencv", dest="opencv", default=False,
                          action="store_true",
                          help="Use OpenCv acceleration")
        optprs.add_option("--opencl", dest="opencl", default=False,
                          action="store_true",
                          help="Use OpenCL acceleration")
        optprs.add_option("--plugins", dest="plugins", metavar="NAMES",
                          help="Specify additional plugins to load")
        optprs.add_option("--profile", dest="profile", action="store_true",
                          default=False,
                          help="Run the profiler on main()")
        optprs.add_option("--sep", dest="separate_channels", default=False,
                          action="store_true",
                          help="Load files in separate channels")
        optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                          default=None,
                          help="Prefer GUI toolkit (gtk|qt)")
        optprs.add_option("--wcspkg", dest="wcspkg", metavar="NAME",
                          default=None,
                          help="Prefer WCS module NAME")
        log.addlogopts(optprs)

    def main(self, options, args):
        """
        Main routine for running the reference viewer.

        `options` is a OptionParser object that has been populated with
        values from parsing the command line.  It should at least include
        the options from add_default_options()

        `args` is a list of arguments to the viewer after parsing out
        options.  It should contain a list of files or URLs to load.
        """

        # Create a logger
        logger = log.get_logger(name='ginga', options=options)

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
        settings.load(onError='silent')
        settings.set_defaults(useMatplotlibColormaps=False,
                              widgetSet='choose',
                              WCSpkg='choose', FITSpkg='choose',
                              recursion_limit=2000,
                              save_layout=False)

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
                cmap.add_matplotlib_cmaps()
            except Exception as e:
                logger.warning(
                    "failed to load matplotlib colormaps: %s" % (str(e)))

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
                "failed to set WCS package preference: %s" % (str(e)))

        # User wants to customize the FITS package?
        if options.fitspkg:
            fitspkg = options.fitspkg
        else:
            fitspkg = settings.get('FITSpkg', 'choose')

        try:
            from ginga.util import io_fits
            if wcspkg != 'choose':
                assert io_fits.use(fitspkg) is True
        except Exception as e:
            logger.warning(
                "failed to set FITS package preference: %s" % (str(e)))

        # Check whether user wants to use OpenCv
        use_opencv = settings.get('use_opencv', False)
        if use_opencv or options.opencv:
            from ginga import trcalc
            try:
                trcalc.use('opencv')
            except Exception as e:
                logger.warning(
                    "failed to set OpenCv preference: %s" % (str(e)))

        # Check whether user wants to use OpenCL
        use_opencl = settings.get('use_opencl', False)
        if use_opencl or options.opencl:
            from ginga import trcalc
            try:
                trcalc.use('opencl')
            except Exception as e:
                logger.warning(
                    "failed to set OpenCL preference: %s" % (str(e)))

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

        layout_file = None
        if settings.get('save_layout', False):
            layout_file = os.path.join(basedir, 'layout')

        ginga_shell.set_layout(self.layout, layout_file=layout_file)

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
        ginga_shell.build_toplevel()

        # Did user specify a particular geometry?
        if options.geometry:
            ginga_shell.set_geometry(options.geometry)

        # make the list of disabled plugins
        disabled_plugins = []
        if not (options.disable_plugins is None):
            disabled_plugins = options.disable_plugins.lower().split(',')

        # Add desired global plugins
        for spec in self.global_plugins:
            if not spec.module.lower() in disabled_plugins:
                ginga_shell.add_global_plugin(spec)

        # Add GUI log handler (for "Log" global plugin)
        guiHdlr = GuiLogHandler(ginga_shell)
        guiHdlr.setLevel(options.loglevel)
        fmt = logging.Formatter(log.LOG_FORMAT)
        guiHdlr.setFormatter(fmt)
        logger.addHandler(guiHdlr)

        # Load any custom modules
        if options.modules:
            modules = options.modules.split(',')
            for long_plugin_name in modules:
                if '.' in long_plugin_name:
                    tmpstr = long_plugin_name.split('.')
                    plugin_name = tmpstr[-1]
                    pfx = '.'.join(tmpstr[:-1])
                else:
                    plugin_name = long_plugin_name
                    pfx = None
                spec = Bunch(name=plugin_name, module=plugin_name,
                             tab=plugin_name, workspace='right', pfx=pfx)
                ginga_shell.add_global_plugin(spec)

        # Load modules for "local" (per-channel) plug ins
        for spec in self.local_plugins:
            if not spec.module.lower() in disabled_plugins:
                ginga_shell.add_local_plugin(spec)

        # Load any custom plugins
        if options.plugins:
            plugins = options.plugins.split(',')
            for long_plugin_name in plugins:
                if '.' in long_plugin_name:
                    tmpstr = long_plugin_name.split('.')
                    plugin_name = tmpstr[-1]
                    pfx = '.'.join(tmpstr[:-1])
                else:
                    plugin_name = long_plugin_name
                    pfx = None
                spec = Bunch(module=plugin_name, workspace='dialogs',
                             hidden=False, pfx=pfx)
                ginga_shell.add_local_plugin(spec)

        ginga_shell.update_pending()

        # TEMP?
        tab_names = list(map(lambda name: name.lower(),
                             ginga_shell.ds.get_tabnames(group=None)))
        if 'info' in tab_names:
            ginga_shell.ds.raise_tab('Info')
        if 'synopsis' in tab_names:
            ginga_shell.ds.raise_tab('synopsis')
        if 'thumbs' in tab_names:
            ginga_shell.ds.raise_tab('Thumbs')

        # Add custom channels
        channels = options.channels.split(',')
        for chname in channels:
            ginga_shell.add_channel(chname)
        ginga_shell.change_channel(channels[0])

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
        showBanner = True
        try:
            showBanner = settings.get('showBanner')

        except KeyError:
            # disable for subsequent runs
            settings.set(showBanner=False)
            settings.save()

        if (not options.nosplash) and (len(args) == 0) and showBanner:
            ginga_shell.banner(raiseTab=True)

        # Handle inputs like "*.fits[ext]" that sys cmd cannot auto expand.
        expanded_args = []
        for imgfile in args:
            if '*' in imgfile:
                if '[' in imgfile and imgfile.endswith(']'):
                    s = imgfile.split('[')
                    ext = '[' + s[1]
                else:
                    ext = ''
                for fname in glob.iglob(s[0]):
                    expanded_args.append(fname + ext)
            else:
                expanded_args.append(imgfile)

        # Assume remaining arguments are fits files and load them.
        chname = None
        for imgfile in expanded_args:
            if options.separate_channels and (chname is not None):
                channel = ginga_shell.add_channel_auto()
            else:
                channel = ginga_shell.get_channel_info()
            chname = channel.name
            ginga_shell.nongui_do(ginga_shell.load_file, imgfile,
                                  chname=chname)

        try:
            try:
                # if there is a network component, start it
                if hasattr(ginga_shell, 'start'):
                    task = Task.FuncTask2(ginga_shell.start)
                    thread_pool.addTask(task)

                # Main loop to handle GUI events
                logger.info("Entering mainloop...")
                ginga_shell.mainloop(timeout=0.001)

            except KeyboardInterrupt:
                logger.error("Received keyboard interrupt!")

        finally:
            logger.info("Shutting down...")
            ev_quit.set()

        sys.exit(0)


def reference_viewer(sys_argv):
    """Create reference viewer from command line."""
    viewer = ReferenceViewer(layout=default_layout)
    viewer.add_default_plugins()
    viewer.add_separately_distributed_plugins()

    # Parse command line options with optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage,
                          version=('%%prog %s' % version.version))
    viewer.add_default_options(optprs)

    (options, args) = optprs.parse_args(sys_argv[1:])

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
        profile.run('viewer.main(options, args)')

    else:
        viewer.main(options, args)


def _main():
    """Run from command line."""
    reference_viewer(sys.argv)

# END
