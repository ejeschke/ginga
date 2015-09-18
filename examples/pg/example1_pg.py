#! /usr/bin/env python
#
# example1_pg.py -- Simple FITS viewer in an HTML5 canvas web browser.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c)  Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
This example illustrates using a Ginga widget in a web browser,  All the
rendering is done on the server side and the browser only acts as a display
front end.  Using this you could create an analysis type environment on a
server and view it via a browser.

Usage:
(server side)
    ./example1_pg.py -p 6500 --host='' -d /path/to/root/of/fits/files \
        --loglevel=20

Use --host='' if you want to listen on all network interfaces.

(client side)
From the browser, type in a URL based on the port that you chose above, e.g.:

    http://servername:6500/viewer?id=v1&width=600&height=600&path=some/file.fits

The `path` should be to a file *on the server side, relative to the directory
specified using -d.

If `width` and `height` are omitted they default to the browser's page size.
NOTE that because all rendering is done on the server side, you will achieve
better performance if you choose a smaller rendering size.

`id` is an identifier that will identify the same viewer each time you
request it.

You will need a reasonably modern web browser with HTML5 canvas support.
Tested with Chromium 41.0.2272.76, Firefox 37.0.2, Safari 7.1.6
"""
from __future__ import print_function
import sys, os
import logging

from ginga.misc import log
from ginga.web.pgw import ipg


def main(options, args):

    logger = log.get_logger("example2", options=options)

    server = ipg.make_server(logger=logger, basedir=options.basedir,
                             numthreads=options.numthreads, host=options.host,
                             port=options.port, use_opencv=options.use_opencv)

    try:
        server.start(use_thread=False)

    except KeyboardInterrupt:
        logger.info("Interrupted!")
        server.stop()

    logger.info("Server terminating...")


if __name__ == "__main__":

    # Parse command line options with nifty optparse module
    from optparse import OptionParser

    usage = "usage: %prog [options] cmd [args]"
    optprs = OptionParser(usage=usage, version=('%%prog'))

    optprs.add_option("-d", "--basedir", dest="basedir", metavar="DIR",
                      default=".",
                      help="Directory which is at the base of file open requests")
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--host", dest="host", metavar="HOST",
                      default="localhost",
                      help="HOST used to decide which interfaces to listen on")
    optprs.add_option("--log", dest="logfile", metavar="FILE",
                      help="Write logging output to FILE")
    optprs.add_option("--loglevel", dest="loglevel", metavar="LEVEL",
                      type='int', default=logging.INFO,
                      help="Set logging level to LEVEL")
    optprs.add_option("--numthreads", dest="numthreads", type="int",
                      default=5, metavar="NUM",
                      help="Start NUM threads in thread pool")
    optprs.add_option("--stderr", dest="logstderr", default=False,
                      action="store_true",
                      help="Copy logging also to stderr")
    optprs.add_option("--opencv", dest="use_opencv", default=False,
                      action="store_true",
                      help="Use OpenCv acceleration")
    optprs.add_option("-p", "--port", dest="port",
                      type='int', default=8080, metavar="PORT",
                      help="Default PORT to use for the web socket")
    optprs.add_option("--profile", dest="profile", action="store_true",
                      default=False,
                      help="Run the profiler on main()")

    (options, args) = optprs.parse_args(sys.argv[1:])

    # Are we debugging this?
    if options.debug:
        import pdb

        pdb.run('main(options, args)')

    # Are we profiling this?
    elif options.profile:
        import profile

        print(("%s profile:" % sys.argv[0]))
        profile.run('main(options, args)')


    else:
        main(options, args)

# END
