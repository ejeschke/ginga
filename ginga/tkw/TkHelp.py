#
# TkHelp.py -- help module for Ginga Tk backend
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

class Timer(object):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, ival_sec, expire_cb, data=None, tkcanvas=None):
        """Create a timer set to expire after `ival_sec` and which will
        call the callable `expire_cb` when it expires.
        """
        self.ival_sec = ival_sec
        self.cb = expire_cb
        self.data = data
        self.tkcanvas = tkcanvas
        self._timer = None

    def start(self, ival_sec=None):
        """Start the timer.  If `ival_sec` is not None, it should
        specify the time to expiration in seconds.
        """
        if ival_sec is None:
            ival_sec = self.ival_sec

        self.cancel()

        # Tk timer set in milliseconds
        time_ms = int(ival_sec * 1000.0)
        self._timer = self.tkcanvas.after(time_ms, self._redirect_cb)

    def _redirect_cb(self):
        self._timer = None
        self.cb(self)

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        try:
            if self._timer is not None:
                self.tkcanvas.after_cancel(self._timer)
                self._timer = None
        except:
            pass
