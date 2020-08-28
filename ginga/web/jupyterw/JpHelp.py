#
# JpHelp.py -- Jupyter web notebook help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import time
import random
import datetime
import threading

from tornado.ioloop import IOLoop

from ginga.misc import Bunch, Callback, log

default_timer_interval_msec = 10


class TimerFactory(object):
    """
    As long as Jupyter notebooks use Tornado we can count on using the
    tornado io loop to help us implement a timer.  But if that ever changes
    we need to update this class to use a new mechanism.
    """

    def __init__(self, logger=None):
        self.timer_lock = threading.RLock()
        self.timer_cnt = 0
        self.timer = {}
        self.base_interval_msec = default_timer_interval_msec
        self._timeout = None
        if logger is None:
            # substitute a null logger if user didn't provide one
            logger = log.get_logger(name='timerfactory', null=True,
                                    level=50)
        self.logger = logger

    def wind(self):
        # randomize the first timeout so we don't get every timer
        # expiring at the same time
        interval = random.randint(1, self.base_interval_msec)  # nosec
        delta = datetime.timedelta(milliseconds=interval)
        self._timeout = IOLoop.current().add_timeout(delta, self.timer_tick)

    def timer_tick(self):
        """Callback executed every self.base_interval_msec to check timer
        expirations.
        """
        # TODO: should exceptions thrown from this be caught and ignored
        self.process_timers()

        delta = datetime.timedelta(milliseconds=self.base_interval_msec)
        self._timeout = IOLoop.current().add_timeout(delta, self.timer_tick)

    def process_timers(self):
        self.logger.debug("check timers")
        funcs = []
        with self.timer_lock:
            for key, bnch in self.timer.items():
                if (bnch.deadline is not None) and \
                   (time.time() >= bnch.deadline):
                    bnch.deadline = None
                    funcs.append(bnch.func)

        for func in funcs:
            try:
                func()
            except Exception as e:
                pass
            # self.logger.debug("update should have been called.")

    def add_timer(self, func):
        with self.timer_lock:
            if self._timeout is None:
                self.wind()

            name = self.timer_cnt
            self.timer_cnt += 1
            timer = Bunch.Bunch(deadline=None, func=func, name=name)
            self.timer[name] = timer
            return timer

    def remove_timer(self, timer):
        with self.timer_lock:
            name = timer.name
            del self.timer[name]

    def reset_timer(self, timer, time_sec):
        with self.timer_lock:
            if timer not in self.timer:
                self.timer[timer.name] = timer
            self.logger.debug("setting timer...")
            timer.deadline = time.time() + time_sec


default_timer_factory = TimerFactory()


class Timer(Callback.Callbacks):
    """Abstraction of a GUI-toolkit implemented timer."""

    def __init__(self, duration=0.0, timer_factory=None):
        """Create a timer set to expire after `duration` sec.
        """
        super(Timer, self).__init__()

        if timer_factory is None:
            timer_factory = default_timer_factory
        self.timer_factory = timer_factory

        self.duration = duration
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self._timer = self.timer_factory.add_timer(self._redirect_cb)

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

        self.timer_factory.reset_timer(self._timer, duration)

    def _redirect_cb(self):
        self.make_callback('expired')

    def stop(self):
        try:
            self.timer_factory.remove_timer(self._timer)
        except Exception:
            pass

    def cancel(self):
        """Cancel this timer.  If the timer is not running, there
        is no error.
        """
        self.stop()
        self.make_callback('canceled')

    clear = cancel
