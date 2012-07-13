#! /usr/bin/env python
#
# grc.py -- Ginga Remote Control example client
#
#[ Eric Jeschke (eric@naoj.org) --
#  Last edit: Thu Jul 12 16:10:50 HST 2012
#]
#
# Copyright (c) 2011-2012, Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
 See the plugin RC.py for details of the server side.
 
 Example usage:

 Create a new channel:
 $ ./grc.py add_channel FOO
 
 Load a file:
 $ ./grc.py display_fitsfile FOO /home/eric/testdata/SPCAM/SUPA01118797.fits False

 Load a file, controlled from a different host:
 $ ./grc.py --host=bar --port=9000 display_fitsfile FOO /home/eric/testdata/SPCAM/SUPA01118797.fits False

 Cut levels:
 $ ./grc.py cut_levels FOO 163 1300

 Auto cut levels:
 $ ./grc.py autocuts FOO

 Zoom to a specific level:
 ./grc.py -- zoom FOO -7
 
 Zoom to fit:
 ./grc.py zoom_fit FOO
 
 Transform:
 ./grc.py transform FOO 1 0 1
 
"""
import sys
import xmlrpclib
from optparse import OptionParser

version = '20120712'


def main(options, args):

    # Get proxy to server
    url = "http://%s:%d" % (options.host, options.port)
    ginga = xmlrpclib.ServerProxy(url)

    # Lookup and invoke method on rest of parameters
    method = getattr(ginga, args[0])
    args = args[1:]
    res = method(*args)


if __name__ == "__main__":
   
    usage = "usage: %prog [options] cmd [arg] ..."
    optprs = OptionParser(usage=usage, version=('%%prog %s' % version))
    
    optprs.add_option("--debug", dest="debug", default=False, action="store_true",
                      help="Enter the pdb debugger on main()")
    optprs.add_option("--host", dest="host", metavar="HOST",
                      default="localhost", help="Connect to server at HOST")
    optprs.add_option("--port", dest="port", type="int",
                      default=9000, metavar="PORT",
                      help="Connect to server at PORT")
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

        print "%s profile:" % sys.argv[0]
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
