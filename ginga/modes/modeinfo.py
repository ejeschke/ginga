#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
if sys.version_info < (3, 8):
    # Python 3.7
    from importlib_metadata import entry_points
else:
    from importlib.metadata import entry_points


available_modes = []


def add_mode(mode_class):
    if mode_class not in available_modes:
        available_modes.append(mode_class)


def discover_modes():
    group = 'ginga_modes'
    discovered_modes = entry_points().get(group, [])
    for entry_point in discovered_modes:
        try:
            mode_class = entry_point.load()
            add_mode(mode_class)

        except Exception as e:
            print("Error trying to load entry point %s: %s" % (
                str(entry_point), str(e)))


if len(available_modes) == 0:
    discover_modes()
