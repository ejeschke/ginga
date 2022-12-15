#
# compat.py -- Python compatibility shims.
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


def ep_get(group):
    """Get the entry points for a group."""
    ep = entry_points()
    if hasattr(ep, "select"):
        return ep.select(group=group)
    else:
        return ep.get(group, [])
