#!/usr/bin/env python
#
# ginga.py -- FITS image viewer and tool.
#
# Eric Jeschke (eric@naoj.org)
#
"""
Copyright (c) 2011-2013  Eric R. Jeschke
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

"""
Usage:
    ginga.py [options] [fitsfile] ...
"""

# stdlib imports
import sys, os
import logging, logging.handlers
import threading

# Local application imports
from Bunch import Bunch
import Task
import ModuleManager
import Datasrc
import Settings
from Control import GingaControl, GuiLogHandler
import version

LOG_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

default_layout = ['hpanel', {},
                  ['ws', dict(name='left', width=320),
                   # (tabname, layout), ...
                   [("Info", ['vpanel', {},
                              ['ws', dict(name='uleft', height=300,
                                          show_tabs=False)],
                              ['ws', dict(name='lleft', height=430,
                                          show_tabs=False)],
                              ]
                     )]
                     ],
                  ['vbox', dict(name='main', width=700)],
                  ['ws', dict(name='right', width=400),
                   # (tabname, layout), ...
                   [("Dialogs", ['ws', dict(name='dialogs')
                                 ]
                     )]
                    ],
                  ]

global_plugins = [
    Bunch(module='Pan', tab='Pan', ws='uleft', raisekey='I'),
    Bunch(module='Info', tab='Info', ws='lleft', raisekey='I'),
    Bunch(module='Header', tab='Header', ws='left', raisekey='H'),
    Bunch(module='Zoom', tab='Zoom', ws='left', raisekey='Z'),
    Bunch(module='Thumbs', tab='Thumbs', ws='right', raisekey='T'),
    Bunch(module='Contents', tab='Contents', ws='right', raisekey='c'),
    Bunch(module='WBrowser', tab='Help', ws='right', raisekey='?'),
    Bunch(module='Errors', tab='Errors', ws='right'),
    Bunch(module='Log', tab='Log', ws='right'),
    Bunch(module='Debug', tab='Debug', ws='right'),
    ]

local_plugins = [
    Bunch(module='Pick', ws='dialogs', shortkey='f1'),
    Bunch(module='Ruler', ws='dialogs', shortkey='f2'),
    #Bunch(module='Layers', ws='dialogs', shortkey='f3'),
    Bunch(module='MultiDim', ws='dialogs', shortkey='f4'),
    Bunch(module='Cuts', ws='dialogs', shortkey='f5'),
    Bunch(module='Histogram', ws='dialogs', shortkey='f6'),
    Bunch(module='PixTable', ws='dialogs', shortkey='f7'),
    Bunch(module='Preferences', ws='dialogs', shortkey='f9'),
    Bunch(module='Catalogs', ws='dialogs', shortkey='f10'),
    Bunch(module='Drawing', ws='dialogs', shortkey='f11'),
    Bunch(module='FBrowser', ws='dialogs', shortkey='f12'),
    ]

# max size of log file before rotating
log_maxsize = 20 * 1024*1024
log_backups = 4

def main(options, args):

    # Create a logger
    logger = logging.Logger('ginga')

    fmt = logging.Formatter(LOG_FORMAT)
    if options.logfile:
        fileHdlr  = logging.handlers.RotatingFileHandler(options.logfile,
                                                         maxBytes=log_maxsize,
                                                         backupCount=log_backups)
        fileHdlr.setLevel(options.loglevel)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if options.logstderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(options.loglevel)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    # Get settings (preferences)
    try:
        basedir = os.environ['GINGA_HOME']
    except KeyError:
        basedir = os.path.join(os.environ['HOME'], '.ginga')
    prefs = Settings.Preferences(basefolder=basedir, logger=logger)
    sys.path.insert(0, basedir)

    moduleHome = os.path.split(sys.modules[__name__].__file__)[0]
    childDir = os.path.join(moduleHome, 'misc', 'plugins')
    sys.path.insert(0, childDir)
    childDir = os.path.join(basedir, 'plugins')
    sys.path.insert(0, childDir)

    # Choose a toolkit
    if options.toolkit == 'gtk':
        from gtkw.GingaGtk import GingaView
    elif options.toolkit == 'qt':
        from qtw.GingaQt import GingaView
    else:
        try:
            import gtk
            from gtkw.GingaGtk import GingaView
        except ImportError:
            try:
                from qtw.GingaQt import GingaView
            except ImportError:
                print "You need python-gtk or python-qt4 to run Ginga!"
                sys.exit(1)

    # Define class dynamically based on toolkit choice
    class Ginga(GingaControl, GingaView):

        def __init__(self, logger, threadPool, module_manager, prefs,
                     ev_quit=None, datasrc_length=20, follow_focus=False):
            GingaView.__init__(self, logger, ev_quit)
            GingaControl.__init__(self, logger, threadPool, module_manager,
                                  prefs, ev_quit=ev_quit,
                                  datasrc_length=datasrc_length,
                                  follow_focus=follow_focus)

    # Create the dynamic module manager
    mm = ModuleManager.ModuleManager(logger)

    # Create and start thread pool
    ev_quit = threading.Event()
    threadPool = Task.ThreadPool(options.numthreads, logger,
                                 ev_quit=ev_quit)
    threadPool.startall()

    # Create the Ginga main object
    ginga = Ginga(logger, threadPool, mm, prefs,
                  datasrc_length=options.bufsize,
                  ev_quit=ev_quit)
    ginga.followFocus(False)

    # Build desired layout
    ginga.build_toplevel(layout=default_layout)

    # Add desired global plugins
    for spec in global_plugins:
        ginga.add_global_plugin(spec)

    # Add GUI log handler (for "Log" global plugin)
    guiHdlr = GuiLogHandler(ginga)
    guiHdlr.setLevel(options.loglevel)
    guiHdlr.setFormatter(fmt)
    logger.addHandler(guiHdlr)

    # Load any custom modules
    if options.modules:
        modules = options.modules.split(',')
        for pluginName in modules:
            spec = Bunch(name=pluginName, module=pluginName)
            ginga.add_global_plugin(spec)

    # Load modules for "local" (per-channel) plug ins
    for spec in local_plugins:
        ginga.add_local_plugin(spec)

    # Load any custom plugins
    if options.plugins:
        plugins = options.plugins.split(',')
        for pluginName in plugins:
            spec = Bunch(module=pluginName, ws='dialogs',
                         hidden=True)
            ginga.add_local_plugin(spec)

    ginga.update_pending()

    # Add custom channels
    channels = options.channels.split(',')
    for chname in channels:
        datasrc = Datasrc.Datasrc(length=options.bufsize)
        ginga.add_channel(chname, datasrc)
    ginga.change_channel(channels[0])

    # User configuration (custom star catalogs, etc.)
    try:
        import ginga_config

        ginga_config.config(ginga)
    except ImportError, e:
        logger.error("Error importing Ginga config file: %s" % (
            str(e)))

    # Did user specify a particular geometry?
    if options.geometry:
        ginga.setGeometry(options.geometry)

    if not options.nosplash and len(args)==0:
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


if __name__ == "__main__":

    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog %s' % version.version))

    optprs.add_option("--bufsize", dest="bufsize", metavar="NUM",
                      type="int", default=25,
                      help="Buffer length to NUM")
    optprs.add_option("--channels", dest="channels", default="Image",
                      help="Specify list of channels to create")
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--display", dest="display", metavar="HOST:N",
                      help="Use X display on HOST:N")
    optprs.add_option("-g", "--geometry", dest="geometry",
                      metavar="GEOM", default="+20+100",
                      help="X geometry for initial size and placement")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--modules", dest="modules", metavar="NAMES",
                      help="Specify additional modules to load")
    optprs.add_option("--nosplash", dest="nosplash", default=False,
                      action="store_true",
                      help="Don't display the splash screen")
    optprs.add_option("--numthreads", dest="numthreads", type="int",
                      default=30, metavar="NUM",
                      help="Start NUM threads in thread pool")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("--plugins", dest="plugins", metavar="NAMES",
                      help="Specify additional plugins to load")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")
    optprs.add_option("-t", "--toolkit", dest="toolkit", metavar="NAME",
                      help="Prefer GUI toolkit (gtk|qt)")

    (options, args) = optprs.parse_args(sys.argv[1:])

    if options.display:
        os.environ['DISPLAY'] = options.display

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print "%s profile:" % sys.argv[0]
        profile.run('main(options, args)')


    else:
        main(options, args)

# END
