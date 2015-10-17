#
# Timer.py -- GUI independent timers.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import time
import threading

from ginga.misc import Bunch, Callback
from ginga.util.heaptimer import Timer as HeapTimer, TimerHeap

class TimerError(Exception):
    pass

class TimerFactory(object):

    def __init__(self, ev_quit=None, logger=None):
        # ev_quit retained for past and possible future use
        self.ev_quit = ev_quit
        self.timer_heap = TimerHeap("TimerFactory", logger=logger)


    def timer(self):
        """Creates and returns a new Timer."""
        return Timer(self)

    def set(self, time_sec, callback_fn, *args, **kwdargs):
        """Convenience function to create and set a timer.

        Equivalent to:
            timer = timer_factory.timer()
            timer.set_callback('expired', callback_fn, *args, **kwdargs)
            timer.set(time_sec)
        """
        timer = self.timer()
        timer.set_callback('expired', callback_fn, *args, **kwdargs)
        timer.set(time_sec)
        return timer

    def clear(self, timer):
        timer.clear()

    def clear_all(self):
        self.timer_heap.remove_all_timers()

    def wait_timers(self):
        """Wait for all pending timers to expire.
        """
        #self.timer_heap.wait_timers()
        raise Exception("wait_timers() is not yet implemented")

    def wind(self):
        # For legacy compatibility
        pass

    def quit(self):
        """Terminate the timer factory.  Pending timers and events will not
        be processed.
        """
        #self.ev_quit.set()
        self.timer_heap.quit()


class Timer(Callback.Callbacks):

    def __init__(self, factory):
        super(Timer, self).__init__()

        self.tfact = factory
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self.timer = HeapTimer(self.tfact.timer_heap, 0, self._expired_cb)

        for name in ('expired', 'canceled'):
            self.enable_callback(name)

    def clear(self):
        """
        Clear a pending expiration event.
        """
        self.timer.stop()
        self.make_callback('canceled')

    def set(self, time_sec):
        """
        Set the timer for time_sec.   Any callbacks registered for the
        'expired' event will be called when the timer reaches the deadline.
        """
        self.timer.start(time_sec)

    def is_set(self):
        """
        Returns True if this timer is set.
        """
        return self.timer.is_scheduled()

    def _expired_cb(self):
        self.make_callback('expired')

    def cond_set(self, time_sec):
        self.timer.cond_start(time_sec)

    def time_left(self):
        return self.timer.remaining_time()

    def get_deadline(self):
        return self.timer.expiration_time()


def main():

    tfact = TimerFactory()

    def cb(timer, who):
        cur_time = time.time()
        cur_time_sec = float(int(cur_time))
        frac_sec = cur_time - cur_time_sec
        timestr = time.strftime("%H:%M:%S", time.localtime(cur_time_sec))
        frac = str(frac_sec).split('.')[1]
        print("[%s] Time is '%s.%s'" % (who, timestr, frac))

    cb(None, '0')
    print("Setting timers")
    t1 = tfact.set(0.0015, cb, 'B')
    t2 = tfact.set(0.0020, cb, 'D')
    t3 = tfact.set(0.0016, cb, 'C')
    t4 = tfact.set(0.0001, cb, 'A')
    t5 = tfact.set(0.0030, cb, 'E')
    t2.clear()

    print("Waiting on timers")
    try:
        #tfact.wait_timers()
        time.sleep(2)

    except KeyboardInterrupt:
        print("Caught ^C...")


if __name__ == '__main__':
    main()
