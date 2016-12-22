# -*- coding: utf-8 -*-#
#
# Copyright (c) 2014 by Christian E. Hopps.
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import heapq
import logging
import random
import time
import threading
import functools

__author__ = 'Christian Hopps'
__version__ = '1.0'
__docformat__ = "restructuredtext en"


_logger = logging.getLogger(__name__)


@functools.total_ordering
class Timer (object):
    def __init__ (self, heap, jitter, action, *args, **kwargs):
        self.jitter = jitter
        self.action = action
        self.args = args
        self.kwargs = kwargs
        self.expire = None
        self.timer_heap = heap
        self.logger = heap.logger

    def run(self):
        try:
            self.action(*self.args, **self.kwargs)
        except Exception as ex:
            self.logger.error("Ignoring uncaught exception within timer action: %s", str(ex))

    def __hash__(self):
        return id(self)

    def __lt__(self, other):
        if other is None:
            return -1
        return self.expire < other.expire

    def __eq__(self, other):
        return id(self) == id(other)

    def is_scheduled(self):
        with self.timer_heap:
            return self.expire is not None

    def start(self, time_sec):
        self.stop()

        self.start_time = time.time()
        if self.jitter:
            self.expire = self.start_time + time_sec * (
                1 - random.random() * self.jitter)
        else:
            self.expire = self.start_time + time_sec

        self.timer_heap.add(self)

    def cond_start(self, time_sec):
        with self.timer_heap:
            if not self.is_scheduled():
                self.start(time_sec)

    def elapsed_time(self):
        """Return the elapsed time since the timer was started."""
        return time.time() - self.start_time

    def remaining_time(self):
        """Return the remaining time to the timer expiration.
        If the timer has already expired then None is returned.
        """
        if self.expire is None:
            return 0.0
        return self.expire - time.time()

    def stop(self):
        had_run = self.timer_heap.remove(self)
        self.expire = None
        return had_run


class TimerHeap(object):
    def __init__(self, desc='A Timer Heap', logger=None):
        self.desc = desc
        if logger is None:
            # use module logger if user doesn't supply one
            logger = _logger
        self.logger = logger

        self.timers = {}
        self.heap = []
        self.lock = threading.RLock()
        self.rtimer = None
        self.expiring = False
        self.expire_gen = 0

    def __enter__(self):
        """Use with statement to hold lock"""
        return self.lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Use with statement to hold lock"""
        return self.lock.release()

    def timer(self, jitter, action, *args, **kwargs):
        """Convenience method to create a Timer from the heap"""
        return Timer(self, jitter, action, *args, **kwargs)

    def add(self, timer):
        """Add a timer to the heap"""
        with self.lock:
            if self.heap:
                top = self.heap[0]
            else:
                top = None

            assert timer not in self.timers
            self.timers[timer] = timer
            heapq.heappush(self.heap, timer)

            # Check to see if we need to reschedule our main timer.
            # Only do this if we aren't expiring in the other thread.
            if self.heap[0] != top and not self.expiring:
                if self.rtimer is not None:
                    self.rtimer.cancel()
                    # self.rtimer.join()
                    self.rtimer = None

            # If we are expiring timers right now then that will reschedule
            # as appropriate otherwise let's start a timer if we don't have
            # one
            if self.rtimer is None and not self.expiring:
                top = self.heap[0]
                ival = top.expire - time.time()
                if ival < 0:
                    ival = 0
                self.rtimer = threading.Timer(ival, self.expire)
                self.rtimer.start()

    def expire(self):
        try:
            # Set expiring variable and forget old timer.
            with self.lock:
                self.expire_gen += 1
                self.expiring = True
                self.rtimer = None

            while True:
                with self.lock:
                    if not self.heap:
                        return

                    top = self.heap[0]
                    ctime = time.time()
                    if top.expire > ctime:
                        return

                    # remove the timer
                    expired = heapq.heappop(self.heap)
                    del self.timers[expired]

                    # Ok to run with lock as we use RLock
                    # Much safer for things like caches
                    expired.expire = None
                    expired.run()
        except Exception as ex:
            self.logger.error("Unexpected Exception: %s" % str(ex))
        finally:
            # This is never set while expiring is True
            assert self.rtimer is None

            with self.lock:
                # Now grab the next timer and set our real-time timer and unset expiring
                if self.heap:
                    top = self.heap[0]
                    ival = top.expire - time.time()
                    if ival < 0:
                        ival = 0
                    self.rtimer = threading.Timer(ival, self.expire)
                    self.rtimer.start()
                self.expiring = False

    def _remove(self, timer):
        """Remove timer from heap lock and presence are assumed"""
        assert timer.timer_heap == self
        del self.timers[timer]
        assert timer in self.heap
        self.heap.remove(timer)
        heapq.heapify(self.heap)

    def remove(self, timer):
        """Remove a timer from the heap, return True if already run"""
        with self.lock:
            # This is somewhat expensive as we have to heapify.
            if timer in self.timers:
                self._remove(timer)
                return False
            else:
                return True

    def remove_all_timers(self):
        """Remove all waiting timers and terminate any blocking threads."""
        with self.lock:
            if self.rtimer is not None:
                self.rtimer.cancel()

            self.timers = {}
            self.heap = []
            self.rtimer = None
            self.expiring = False

    def quit(self):
        """Execute this method before your program exit to make sure it
        doesn't block on waiting for a timer thread to terminate."""
        self.remove_all_timers()
