#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import os
import glob
import inspect

from ginga.util import paths, compat
from ginga.modes.mode_base import Mode
from ginga.misc.ModuleManager import my_import

available_modes = []


def add_mode(mode_class):
    if mode_class not in available_modes:
        available_modes.append(mode_class)


def discover_modes():
    # discover modes installed under entry point "ginga_modes"
    group = 'ginga_modes'
    discovered_modes = compat.ep_get(group)
    for entry_point in discovered_modes:
        try:
            mode_class = entry_point.load()
            add_mode(mode_class)

        except Exception as e:
            print("Error trying to load entry point %s: %s" % (
                str(entry_point), str(e)))

    # discover modes in the user's $HOME/.ginga/modes folder
    moduledir = os.path.join(paths.ginga_home, "modes")
    if os.path.isdir(moduledir):
        files = glob.glob(os.path.join(moduledir, "*.py"))
        for path in files:
            _dir, fname = os.path.split(path)
            fname, _sfx = os.path.splitext(fname)
            module = my_import(fname, path=path)
            for attr in module.__dict__.values():
                if (inspect.isclass(attr) and issubclass(attr, Mode) and
                    attr is not Mode):
                    try:
                        add_mode(attr)

                    except Exception as e:
                        print("Error trying to load mode %s: %s" % (
                            fname, str(e)))


if len(available_modes) == 0:
    discover_modes()
