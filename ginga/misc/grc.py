#
# grc.py -- Ginga Remote Control example client
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""See the plugin RC.py for details of the server side.

In Ginga, start the RC plugin to enable Ginga remote control
(``Plugins->Start RC``).

Show example usage (plugin must be started)::

    $ ggrc help

"""
from __future__ import absolute_import, print_function

import sys
from optparse import OptionParser

from ..util import grc as _grc

try:
    from ..version import version
except ImportError:
    version = 'unknown'


def main(options, args):

    # Get proxy to server
    ginga = _grc.RemoteClient(options.host, options.port)

    if len(args) == 0:
        method_name = 'help'
        args, kwdargs = [], {}
    else:
        method_name = args[0]
        args, kwdargs = _grc.prep_args(args[1:])
        #print (("args=", args, "kwdargs=", kwdargs))

    # invoke method on rest of parameters
    method = ginga.lookup_attr(method_name)
    res = method(*args, **kwdargs)
    if res not in (_grc.undefined, None):
        print(res)


def _main():
    """Run from command line."""
    usage = "usage: %prog [options] cmd [arg] ..."
    optprs = OptionParser(usage=usage, version=version)

    optprs.add_option("--debug", dest="debug", default=False,
                      action="store_true",
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

        print("%s profile:" % sys.argv[0])
        profile.run('main(options, args)')

    else:
        main(options, args)

# END
