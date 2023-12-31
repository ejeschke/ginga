#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
try:
    import tomllib
except ImportError:
    # see setup.cfg, for python < 3.11
    import tomli as tomllib

from ginga.util import paths
from ginga.misc.Bunch import Bunch

__all__ = ['add_cursor', 'get_cursor_names', 'get_cursor_info']

available_cursors = {}


def add_cursor(name, curdct):
    if name not in available_cursors:
        bnch = Bunch(curdct)
        curpath = curdct['file']
        # make an absolute path to the cursor file
        if not curpath.startswith(os.sep):
            curpath = os.path.join(paths.ginga_pkgdir, "cursors", curpath)
        bnch.path = curpath
        bnch.name = name
        available_cursors[name] = bnch


def discover_cursors():
    # discover modes in ginga.cursors folder
    cursor_idx = os.path.join(paths.ginga_pkgdir, "cursors", "cursors.toml")
    with open(cursor_idx, 'r') as cur_f:
        buf = cur_f.read()
    cursor_config = tomllib.loads(buf)

    if 'cursors' in cursor_config:
        for curname, curdct in cursor_config['cursors'].items():
            add_cursor(curname, curdct)


def get_cursor_names():
    return list(available_cursors.keys())


def get_cursor_info(name):
    return available_cursors[name]


if len(available_cursors) == 0:
    discover_cursors()
