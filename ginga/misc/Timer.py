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


class TimerError(Exception):
    pass

class TimerFactory(object):

    def __init__(self, ev_quit=None):
        self.ev_timer = threading.Event()

        if not ev_quit:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        self.lock = threading.Condition()

        # minimum time to wait efficiently until the next event
        self.waittime = 0.0
        self.waittime_reset = 1.0
        # flag to tell us if a new timer has been set
        self.newtimer = False
        # list of timers waiting to expire
        self.waiters = []

    def timer(self):
        """Creates and returns a new Timer."""
        return Timer(self)
    
    def reset_waittime(self):
        """Internal routine used to reset the time until the next event.
        """
        with self.lock:
            cur_time = time.time()
            self.waittime = self.waittime_reset
            if len(self.waiters) > 0:
                timer = self.waiters[0]
                deadline = timer.get_deadline()
                self.waittime = deadline - cur_time
            else:
                #print "notifying"
                self.lock.notifyAll()

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
        """Clears timer `timer`.
        """
        with self.lock:
            # remove from timer dict
            if not timer in self.waiters:
                return
            self.waiters.remove(timer)
            self.waiters = sorted(self.waiters,
                                  key=lambda t: t.get_deadline())
            self.ev_timer.set()

        timer.make_callback('cancelled')

    def clear_all(self):
        """Clears all pending timers.
        """
        with self.lock:
            waiters = self.waiters
            self.waiters = []
            self.ev_timer.set()

        for timer in waiters:
            timer.make_callback('cancelled')

    def add_timer(self, timer):
        """Adds a new timer to be managed.
        """
        with self.lock:
            if not timer in self.waiters:
                self.waiters.append(timer)
            self.waiters = sorted(self.waiters,
                                  key=lambda t: t.get_deadline())
            self.ev_timer.set()
        
    def is_set(self, timer):
        """Returns True if `timer` is set.
        """
        with self.lock:
            return timer in self.waiters

    def release_expired(self):
        """Internal routine to release expired timers and make callbacks.
        """
        #print "checking for releases"
        with self.lock:
            cur_time = time.time()

            rel = []
            for i in range(len(self.waiters)):
                timer = self.waiters[i]
                if timer.get_deadline() <= cur_time:
                    rel.insert(0, (timer, i))
                else:
                    break

            for timer, i in rel:
                # remove from wait list
                self.waiters.pop(i)

        for timer, i in rel:
            #print "making callback for id %d" % (timer.id)
            timer.make_callback('expired')

        self.reset_waittime()

    def wait_timers(self):
        """Wait for all pending timers to expire.
        """

        while not self.ev_quit.isSet():
            with self.lock:
                num_waiters = len(self.waiters)
                if num_waiters > 0:
                    #print "going to wait on %d timers" % (num_waiters)
                    self.lock.wait()
                    #print "woke up"
                else:
                    #print "returning"
                    return

    def quit(self):
        """Terminate the timer factory.  Pending timers and events will not
        be processed.
        """
        self.ev_quit.set()
        self.ev_timer.set()

        
    def mainloop(self):
        """Main loop of the timer factory.  A thread needs to run here to
        handle pending timer events.
        """
        while not self.ev_quit.isSet():

            self.ev_timer.wait(self.waittime)

            # <-- a timer as expired, or list of timers may have changed
            with self.lock:
                self.ev_timer.clear()
                
                cur_time = time.time()
                release = False

                if len(self.waiters) > 0:
                    # first waiter always has the shortest deadline
                    timer = self.waiters[0]
                    if timer.get_deadline() <= cur_time:
                        release = True
                        
            # there are expired timers, release them
            if release:
                self.release_expired()


    def wind(self, use_thread=True):
        """Start a thread in the TimerFactory mainloop().
        """
        if use_thread:
            t = threading.Thread(target=self.mainloop, args=[])
            t.start()

        else:
            self.mainloop()
        

class Timer(Callback.Callbacks):

    def __init__(self, factory):
        super(Timer, self).__init__()
        
        self.tfact = factory
        # For storing aritrary data with timers
        self.data = Bunch.Bunch()

        self.deadline = 0.0
        self.interval = 0.0
        self.lock = threading.RLock()

        for name in ('expired', 'cancelled'):
            self.enable_callback(name)

    def clear(self):
        """
        Clear a pending expiration event.
        """
        self.tfact.clear(self)

    def set(self, time_sec):
        """
        Set the timer for time_sec.   Any callbacks registered for the
        'expired' event will be called when the timer reaches the deadline.
        """
        with self.lock:
            cur_time = time.time()
            self.deadline = cur_time + time_sec
            self.interval = time_sec
        self.tfact.add_timer(self)

    def is_set(self):
        """
        Returns True if this timer is set.
        """
        return self.tfact.is_set(self)        

    def cond_set(self, time_sec):
        with self.tfact.lock:
            if not self.is_set():
                self.set(time_sec)
                
    def time_left(self):
        """
        Returns the amount of time left before this timer expires.
        May be negative if the timer has already expired.
        """
        with self.lock:
            delta = self.deadline - time.time()
        return delta

    def get_deadline(self):
        with self.lock:
            return self.deadline
        

def main():

    tfact = TimerFactory()
    tfact.wind()

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
        tfact.wait_timers()

    except KeyboardInterrupt:
        print("Caught ^C...")
    tfact.quit()
    
    
if __name__ == '__main__':
    main()

