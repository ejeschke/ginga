#
# TkHelp.py -- help module for Ginga Tk backend
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.

from ginga.misc import Bunch, Callback

class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0, tkcanvas=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self.tkcanvas = tkcanvas
        self._timer = None

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def start(self, duration=None):
        """Start the timer.  If `duration` is not None, it should
        specify the time to expiration in seconds.
        """
        if duration is None:
            duration = self.duration

        self.set(duration)

    def set(self, duration):

        self.stop()

        # Tk timer set in milliseconds
        time_ms = int(duration * 1000.0)
        self._timer = self.tkcanvas.after(time_ms, self._redirect_cb)

    def _redirect_cb(self):
        self._timer = None
        self.make_callback('expired')

    def stop(self):
        try:
            if self._timer is not None:
                self.tkcanvas.after_cancel(self._timer)
                self._timer = None
        except:
            pass

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel
