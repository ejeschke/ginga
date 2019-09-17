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

import sys
from argparse import ArgumentParser

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
    argprs = ArgumentParser()

    argprs.add_argument("--debug", dest="debug", default=False,
                        action="store_true",
                        help="Enter the pdb debugger on main()")
    argprs.add_argument("--host", dest="host", metavar="HOST",
                        default="localhost", help="Connect to server at HOST")
    argprs.add_argument("--port", dest="port", type=int,
                        default=9000, metavar="PORT",
                        help="Connect to server at PORT")
    argprs.add_argument("--profile", dest="profile", action="store_true",
                        default=False,
                        help="Run the profiler on main()")

    (options, args) = argprs.parse_known_args(sys.argv[1:])

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
