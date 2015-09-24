#
# main.py -- reference viewer for the Ginga toolkit.
#
# Eric Jeschke (eric@naoj.org, eric@redskiesatnight.com)
#
"""
Copyright (c) 2011-2015  Eric R. Jeschke
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

    Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

    Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the
    distribution.

    Neither the name of the Eric R. Jeschke nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
'AS IS' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from __future__ import print_function

# stdlib imports
import sys, os
import logging, logging.handlers
import threading
import traceback

# Local application imports
from ginga.misc.Bunch import Bunch
from ginga.misc import Task, ModuleManager, Datasrc, Settings, log
import ginga.version as version
import ginga.toolkit as ginga_toolkit
from ginga import AstroImage
from ginga.util import paths

default_layout = ['seq', {},
                   ['vbox', dict(name='top', width=1520, height=900),
                    dict(row=['hbox', dict(name='menu')],
                         stretch=0),
                    dict(row=['hpanel', dict(name='hpnl'),
                     ['ws', dict(name='left', width=300, group=2),
                      # (tabname, layout), ...
                      [("Info", ['vpanel', {},
                                 ['ws', dict(name='uleft', height=300,
                                             show_tabs=False, group=3)],
                                 ['ws', dict(name='lleft', height=430,
                                             show_tabs=True, group=3)],
                                 ]
                        )]],
                     ['vbox', dict(name='main', width=700),
                      dict(row=['ws', dict(wstype='tabs', name='channels',
                                           group=1)], stretch=1)],
                     ['ws', dict(name='right', width=430, group=2),
                      # (tabname, layout), ...
                      [("Dialogs", ['ws', dict(name='dialogs', group=2)
                                    ]
                        )]
                      ],
                     ], stretch=1),
                    dict(row=['ws', dict(name='toolbar', height=40,
                                             show_tabs=False, group=2)],
                         stretch=0),
                    dict(row=['hbox', dict(name='status')], stretch=0),
                    ]]

global_plugins = [
    Bunch(module='Toolbar', tab='Toolbar', ws='toolbar'),
    Bunch(module='Pan', tab='_pan', ws='uleft', raisekey=None),
    Bunch(module='Info', tab='Synopsis', ws='lleft', raisekey=None),
    Bunch(module='Header', tab='Header', ws='left', raisekey='H'),
    Bunch(module='Zoom', tab='Zoom', ws='left', raisekey='Z'),
    Bunch(module='Thumbs', tab='Thumbs', ws='right', raisekey='T'),
    Bunch(module='Contents', tab='Contents', ws='right', raisekey='c'),
    Bunch(module='WBrowser', tab='Help', ws='channels', raisekey='?', start=False),
    Bunch(module='Errors', tab='Errors', ws='right', start=True),
    Bunch(module='RC', tab='RC', ws='right', start=False),
    Bunch(module='SAMP', tab='SAMP', ws='right', start=False),
    Bunch(module='IRAF', tab='IRAF', ws='right', start=False),
    Bunch(module='Log', tab='Log', ws='right', start=False),
    Bunch(module='Debug', tab='Debug', ws='right', start=False),
    ]

local_plugins = [
    Bunch(module='Pick', ws='dialogs', shortkey='f1'),
    Bunch(module='Ruler', ws='dialogs', shortkey='f2'),
    Bunch(module='MultiDim', ws='lleft', shortkey='f4'),
    Bunch(module='Cuts', ws='dialogs', shortkey='f5'),
    Bunch(module='Histogram', ws='dialogs', shortkey='f6'),
    Bunch(module='Overlays', ws='dialogs'),
    Bunch(module='Blink', ws='dialogs'),
    Bunch(module='PixTable', ws='dialogs', shortkey='f7'),
    Bunch(module='Preferences', ws='dialogs', shortkey='f9'),
    Bunch(module='Catalogs', ws='dialogs', shortkey='f10'),
    Bunch(module='Mosaic', ws='dialogs'),
    # Not ready for prime time
    #Bunch(module='Pipeline', ws='dialogs'),
    Bunch(module='Drawing', ws='dialogs', shortkey='f11'),
    Bunch(module='FBrowser', ws='dialogs', shortkey='f12'),
    Bunch(module='Compose', ws='dialogs'),
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

    def add_local_plugin(self, module_name, ws_name):
        self.local_plugins.append(
            Bunch(module=module_name, ws=ws_name))

    def add_global_plugin(self, module_name, ws_name,
                          tab_name=None, start_plugin=True):
        if tab_name is None:
            tab_name = module_name

        self.global_plugins.append(
            Bunch(module=module_name, ws=ws_name, tab=tab_name,
                  start=start_plugin))

    def add_default_plugins(self):
        """
        Add the ginga-distributed default set of plugins to the
        reference viewer.
        """
        # add default global plugins
        for bnch in global_plugins:
            start = bnch.get('start', True)
            self.add_global_plugin(bnch.module, bnch.ws,
                          tab_name=bnch.tab, start_plugin=start)

        # add default local plugins
        for bnch in local_plugins:
            self.add_local_plugin(bnch.module, bnch.ws)

    def add_default_options(self, optprs):
        """
        Adds the default reference viewer startup options to an
        OptionParser instance `optprs`.
        """
        optprs.add_option("--bufsize", dest="bufsize", metavar="NUM",
                          type="int", default=10,
                          help="Buffer length to NUM")
        optprs.add_option("--channels", dest="channels", default="Image",
                          help="Specify list of channels to create")
        optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                          help="Enter the pdb debugger on main()")
        optprs.add_option("--disable-plugins", dest="disable_plugins",
                          metavar="NAMES",
                          help="Specify plugins that should be disabled")
        optprs.add_option("--display", dest="display", metavar="HOST:N",
                          help="Use X display on HOST:N")
        optprs.add_option("--fits", dest="fits", metavar="NAME",
                          default=None,
                          help="Prefer FITS I/O module NAME")
        optprs.add_option("-g", "--geometry", dest="geometry",
                          metavar="GEOM",
                          help="X geometry for initial size and placement")
        optprs.add_option("--log", dest="logfile", metavar="FILE",
                          help="Write logging output to FILE")
        optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                          type='int', default=logging.INFO,
                          help="Set logging level to LEVEL")
        optprs.add_option("--lognull", dest="nulllogger", default=False,
                          action="store_true",
                          help="Use a null logger")
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
        optprs.add_option("--stderr", dest="logstderr", default=False,
                          action="store_true",
                          help="Copy logging also to stderr")
        optprs.add_option("--plugins", dest="plugins", metavar="NAMES",
                          help="Specify additional plugins to load")
        optprs.add_option("--profile", dest="profile", action="store_true",
                          default=False,
                          help="Run the profiler on main()")
        optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                          default=None,
                          help="Prefer GUI toolkit (gtk|qt)")
        optprs.add_option("--wcs", dest="wcs", metavar="NAME",
                          default=None,
                          help="Prefer WCS module NAME")

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
                logger.warn("Couldn't create ginga settings area (%s): %s" % (
                    basedir, str(e)))
                logger.warn("Preferences will not be able to be saved")

        # Set up preferences
        prefs = Settings.Preferences(basefolder=basedir, logger=logger)
        settings = prefs.createCategory('general')
        settings.load(onError='silent')
        settings.setDefaults(useMatplotlibColormaps=False,
                             widgetSet='choose',
                             WCSpkg='choose', FITSpkg='choose',
                             recursion_limit=2000)

        # default of 1000 is a little too small
        sys.setrecursionlimit(settings.get('recursion_limit'))

        # So we can find our plugins
        sys.path.insert(0, basedir)
        moduleHome = os.path.split(sys.modules['ginga.version'].__file__)[0]
        childDir = os.path.join(moduleHome, 'misc', 'plugins')
        sys.path.insert(0, childDir)
        pluginDir = os.path.join(basedir, 'plugins')
        sys.path.insert(0, pluginDir)

        # Choose a toolkit
        if options.toolkit:
            toolkit = options.toolkit
        else:
            toolkit = settings.get('widgetSet', 'choose')

        ginga_toolkit.use(toolkit)
        tkname = ginga_toolkit.get_family()
        logger.info("Chosen toolkit (%s) family is '%s'" % (
            ginga_toolkit.toolkit, tkname))

        if tkname == 'gtk':
            from ginga.gtkw.GingaGtk import GingaView
        elif tkname == 'qt':
            from ginga.qtw.GingaQt import GingaView
        else:
            try:
                from ginga.qtw.GingaQt import GingaView
            except ImportError:
                try:
                    from ginga.gtkw.GingaGtk import GingaView
                except ImportError:
                    print("You need python-gtk or python-qt4 to run Ginga!")
                    sys.exit(1)

        # these imports have to be here, otherwise they force the choice
        # of toolkit too early
        from ginga.Control import GingaControl, GuiLogHandler

        # Define class dynamically based on toolkit choice
        class Ginga(GingaControl, GingaView):

            def __init__(self, logger, threadPool, module_manager, prefs,
                         ev_quit=None):
                GingaView.__init__(self, logger, ev_quit)
                GingaControl.__init__(self, logger, threadPool, module_manager,
                                      prefs, ev_quit=ev_quit)

        if settings.get('useMatplotlibColormaps', False):
            # Add matplotlib color maps if matplotlib is installed
            try:
                from ginga import cmap
                cmap.add_matplotlib_cmaps()
            except Exception as e:
                logger.warn("failed to load matplotlib colormaps: %s" % (str(e)))

        # User wants to customize the WCS package?
        if options.wcs:
            wcspkg = options.wcs
        else:
            wcspkg = settings.get('WCSpkg', 'choose')

        try:
            from ginga.util import wcsmod
            assert wcsmod.use(wcspkg) == True
        except Exception as e:
            logger.warn("failed to set WCS package preference: %s" % (str(e)))

        # User wants to customize the FITS package?
        if options.fits:
            fitspkg = options.fits
        else:
            fitspkg = settings.get('FITSpkg', 'choose')

        try:
            from ginga.util import io_fits
            assert io_fits.use(fitspkg) == True
        except Exception as e:
            logger.warn("failed to set FITS package preference: %s" % (str(e)))

        # Check whether user wants to use OpenCv
        use_opencv = settings.get('use_opencv', False)
        if use_opencv or options.opencv:
            from ginga import trcalc
            try:
                trcalc.use('opencv')
            except Exception as e:
                logger.warn("failed to set OpenCv preference: %s" % (str(e)))

        # Create the dynamic module manager
        mm = ModuleManager.ModuleManager(logger)

        # Create and start thread pool
        ev_quit = threading.Event()
        threadPool = Task.ThreadPool(options.numthreads, logger,
                                     ev_quit=ev_quit)
        threadPool.startall()

        # Create the Ginga main object
        ginga = Ginga(logger, threadPool, mm, prefs, ev_quit=ev_quit)
        ginga.set_layout(self.layout)

        gc = os.path.join(basedir, "ginga_config.py")
        have_ginga_config = os.path.exists(gc)

        # User configuration (custom star catalogs, etc.)
        if have_ginga_config:
            try:
                import ginga_config

                ginga_config.pre_gui_config(ginga)
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
        ginga.build_toplevel()

        # Did user specify a particular geometry?
        if options.geometry:
            ginga.setGeometry(options.geometry)

        # make the list of disabled plugins
        disabled_plugins = []
        if not (options.disable_plugins is None):
            disabled_plugins = options.disable_plugins.lower().split(',')

        # Add desired global plugins
        for spec in self.global_plugins:
            if not spec.module.lower() in disabled_plugins:
                ginga.add_global_plugin(spec)

        # Add GUI log handler (for "Log" global plugin)
        guiHdlr = GuiLogHandler(ginga)
        guiHdlr.setLevel(options.loglevel)
        fmt = logging.Formatter(log.LOG_FORMAT)
        guiHdlr.setFormatter(fmt)
        logger.addHandler(guiHdlr)

        # Load any custom modules
        if options.modules:
            modules = options.modules.split(',')
            for pluginName in modules:
                spec = Bunch(name=pluginName, module=pluginName,
                             tab=pluginName, ws='right')
                ginga.add_global_plugin(spec)

        # Load modules for "local" (per-channel) plug ins
        for spec in self.local_plugins:
            if not spec.module.lower() in disabled_plugins:
                ginga.add_local_plugin(spec)

        # Load any custom plugins
        if options.plugins:
            plugins = options.plugins.split(',')
            for pluginName in plugins:
                spec = Bunch(module=pluginName, ws='dialogs',
                             hidden=False)
                ginga.add_local_plugin(spec)

        ginga.update_pending()

        # TEMP?
        tab_names = list(map(lambda name: name.lower(),
                             ginga.ds.get_tabnames(group=None)))
        if 'info' in tab_names:
            ginga.ds.raise_tab('Info')
        if 'thumbs' in tab_names:
            ginga.ds.raise_tab('Thumbs')

        # User configuration (custom star catalogs, etc.)
        if have_ginga_config:
            try:
                ginga_config.post_gui_config(ginga)
            except Exception as e:
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "\n".join(traceback.format_tb(tb))

                except Exception:
                    tb_str = "Traceback information unavailable."

                logger.error("Error processing Ginga config file: %s" % (
                    str(e)))
                logger.error("Traceback:\n%s" % (tb_str))

        # Add custom channels
        channels = options.channels.split(',')
        for chname in channels:
            datasrc = Datasrc.Datasrc(length=options.bufsize)
            ginga.add_channel(chname, datasrc)
        ginga.change_channel(channels[0])

        # Display banner the first time run, unless suppressed
        showBanner = True
        try:
            showBanner = settings.get('showBanner')

        except KeyError:
            # disable for subsequent runs
            settings.set(showBanner=False)
            settings.save()

        if (not options.nosplash) and (len(args) == 0) and showBanner:
            ginga.banner()

        # Assume remaining arguments are fits files and load them.
        for imgfile in args:
            ginga.nongui_do(ginga.load_file, imgfile)

        try:
            try:
                # Main loop to handle GUI events
                logger.info("Entering mainloop...")
                ginga.mainloop(timeout=0.001)

            except KeyboardInterrupt:
                logger.error("Received keyboard interrupt!")

        finally:
            logger.info("Shutting down...")
            ev_quit.set()

        sys.exit(0)

def reference_viewer(sys_argv):

    viewer = ReferenceViewer(layout=default_layout)
    viewer.add_default_plugins()

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

# END
