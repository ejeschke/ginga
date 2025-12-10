# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# viewer.py -- maintains information about registered viewers for data
#
import uuid
import logging

from ginga.misc import Bunch, Callback, Settings

# this holds registered viewers
viewer_db = {}


class ViewerBase(Callback.Callbacks):
    """An abstract base class for Ginga viewers.
    """

    # subclass should define these two class attributes for viewer name
    # and types that can be viewed
    vname = 'Abstract Ginga Viewer'
    vtypes = []

    @classmethod
    def viewable(cls, dataobj):
        """Test whether `dataobj` is viewable by this viewer.

        Subclass should override this, normally implemented by checking
        whether `dataobj` is an instance of one of the classes listed
        in class variable `vtypes`.
        """
        return False

    def __init__(self, logger=None, settings=None):
        """An abstract base class for Ginga viewers.

        Parameters
        ----------
        logger : :py:class:`~logging.Logger` or `None`
            Logger for tracing and debugging. If not given, one will be created.

        settings : `~ginga.misc.Settings.SettingGroup` or `None`
            Viewer preferences. If not given, one will be created.

        """
        Callback.Callbacks.__init__(self)

        if logger is not None:
            self.logger = logger
        else:
            self.logger = logging.Logger('ViewerLogger')

        # Create settings and set defaults
        if settings is None:
            settings = Settings.SettingGroup(logger=self.logger)
        self.settings = settings

        self.allowed_modes = None

        # for debugging
        self.viewer_id = str(uuid.uuid4())
        self.name = self.viewer_id

    def __str__(self):
        return self.name

    def set_name(self, name):
        """Set viewer name."""
        self.name = name

    def get_settings(self):
        """Get the settings used by this instance.

        Returns
        -------
        settings : `~ginga.misc.Settings.SettingGroup`
            Settings.

        """
        return self.settings

    def get_logger(self):
        """Get the logger used by this instance.

        Returns
        -------
        logger : :py:class:`~logging.Logger`
            Logger.

        """
        return self.logger

    def initialize_channel(self, fv, channel):
        """Subclass should override if there is any initialization when
        added to a channel in the reference viewer.
        """
        pass

    def set_allowed_modes(self, mode_list: list or None):
        if mode_list is None:
            mode_list = []
        self.allowed_modes = set(mode_list)

    def is_mode_allowed(self, mode: str):
        return self.allowed_modes is None or mode in self.allowed_modes


def register_viewer(vclass, priority=0):
    """Register a channel viewer.

    Parameters
    ----------
    vclass : :py:class
        The class of the viewer.
    """
    global viewer_db
    viewer_db[vclass.vname] = Bunch.Bunch(name=vclass.vname,
                                          vclass=vclass,
                                          priority=priority)


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


def get_vinfo(vname):
    return viewer_db[vname]
