# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
# viewer.py -- maintains information about registered viewers for data
#
import uuid

from ginga.misc import Bunch, Callback, Settings, log

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
            self.logger = log.NullLogger()

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

    def get_thumbnail_array(self, dataobj, size):
        """Render a thumbnail of `dataobj` as this viewer would show it.

        Parameters
        ----------
        dataobj : subclass of `~ginga.BaseImage.ViewerObjectBase`
            The data to draw.  Not necessarily the object this viewer is
            currently showing -- a thumbnail is wanted precisely when it
            is not.

        size : tuple of (int, int)
            The (width, height) bounding box, in pixels.  The result may
            come back smaller in either axis, since an implementation
            keeps its own aspect ratio, but not larger.

        Returns
        -------
        arr_np : ndarray or `None`
            An RGB array of shape (ht, wd, 3) and dtype uint8, or `None`
            if this viewer cannot render a thumbnail of `dataobj` -- in
            which case the caller should fall back to a placeholder.

        A viewer that can draw its data should override this.  Doing so
        is much to be preferred over screenshotting the viewer's widget:
        a widget can only be captured while it exists and is on screen,
        which is backend-specific and false in exactly the case a
        thumbnail is for, and what comes back is a picture of whatever
        the widget happens to be scrolled to.

        Called on the GUI thread, since an implementation may need to
        reach a toolkit-owned object such as a matplotlib figure.  It
        must not require the viewer's widget to be realized or mapped.
        """
        return None

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
        except Exception:
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
