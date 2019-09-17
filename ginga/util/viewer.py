# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# viewer.py -- maintains information about registered viewers for data
#

from ginga.misc import Bunch

# this holds registered viewers
viewer_db = {}


def register_viewer(vclass):
    """Register a channel viewer.

    Parameters
    ----------
    vclass : :py:class
        The class of the viewer.
    """
    global viewer_db
    viewer_db[vclass.vname] = Bunch.Bunch(name=vclass.vname,
                                          vclass=vclass,
                                          priority=0)


def get_viewers(dataobj):
    """Returns a list of viewers that are registered that can view `dataobj`,
    sorted by priority.
    """
    res = []
    for vinfo in viewer_db.values():
        vclass = vinfo.vclass
        if not hasattr(vclass, 'viewable'):
            continue
        try:
            tf = vclass.viewable(dataobj)
            if tf:
                res.append(vinfo)
        except Exception as e:
            pass

    res.sort(key=lambda v: v.priority)
    return res


def get_priority_viewers(dataobj):
    """Returns a list of viewers that are registered that can view `dataobj`,
    with all but the best (matching) priority removed.
    """
    res = get_viewers(dataobj)
    if len(res) == 0:
        return res

    # if there is more than one possible viewer, return the list of
    # those that have the best (i.e. lowest) equal priority
    priority = res[0].priority
    return [vinfo for vinfo in res if vinfo.priority <= priority]


def get_viewer_names(dataobj):
    """Returns a list of viewer names that are registered that
    can view `dataobj`.
    """
    return [vinfo.name for vinfo in get_viewers(dataobj)]
