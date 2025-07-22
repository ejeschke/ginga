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

    # invoke method on rest of parameters
    method = ginga.lookup_attr(method_name)
    res = method(*args, **kwdargs)
    if res not in (_grc.undefined, None):
        print(res)


def _main():
    """Run from command line."""
    argprs = ArgumentParser("Ginga Remote Control program")

    argprs.add_argument("--host", dest="host", metavar="HOST",
                        default="localhost", help="Connect to server at HOST")
    argprs.add_argument('-p', "--port", dest="port", type=int,
                        default=_grc.default_rc_port, metavar="PORT",
                        help="Connect to server at PORT")

    (options, args) = argprs.parse_known_args(sys.argv[1:])

    main(options, args)

# END
