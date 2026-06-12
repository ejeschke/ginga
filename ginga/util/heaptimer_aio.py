# -*- coding: utf-8 -*-#
#
# heaptimer_aio.py -- asyncio (single event loop) variant of heaptimer.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""An asyncio-based drop-in for :mod:`ginga.util.heaptimer`.

Provides :class:`Timer` and :class:`TimerHeap` with the same API as the
thread-based ``heaptimer`` module, but scheduling timer expirations on a
single asyncio event loop (via ``loop.call_later``) instead of spawning
``threading.Timer`` threads.  This lets
:class:`ginga.misc.Timer.TimerFactory` work in environments where threads
are unavailable or undesirable -- e.g. Pyodide running in the browser.

It is API-compatible with ``heaptimer`` so it can be substituted for it::

    from ginga.util.heaptimer_aio import Timer, TimerHeap

Notes
-----
* ``call_later`` schedules the expiration callback on the running event
  loop; nothing fires until that loop is actually running (which, in a
  browser/Pyodide app, it always is).
* Because everything runs on one event-loop thread, no locking is needed.
  The ``with timer_heap:`` context-manager protocol is preserved (as a
  no-op) only for API compatibility with the threaded version, which used
  it to hold an ``RLock``.
* The :class:`Timer` class from the threaded module is purely heap logic
  (it never touches threads itself), so it is reused as-is here.
"""
import heapq
import logging
import time

from ginga.util.heaptimer import Timer
from ginga.misc.aio_compat import get_event_loop

__author__ = 'Ginga maintainers'
__docformat__ = "restructuredtext en"

__all__ = ['Timer', 'TimerHeap']

_logger = logging.getLogger(__name__)


class TimerHeap:
    """A heap of timers whose expirations are driven by an asyncio event
    loop (the async counterpart of :class:`heaptimer.TimerHeap`).
    """

    def __init__(self, desc='An Async Timer Heap', logger=None):
        self.desc = desc
        if logger is None:
            # use module logger if user doesn't supply one
            logger = _logger
        self.logger = logger

        self.timers = {}
        self.heap = []
        # the pending ``loop.call_later`` handle, or None
        self.rtimer = None
        self.expiring = False
        self.expire_gen = 0

    def __enter__(self):
        """Context-manager protocol retained for API compatibility with the
        threaded heaptimer.  No lock is needed -- everything runs on a
        single event-loop thread."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def timer(self, jitter, action, *args, **kwargs):
        """Convenience method to create a Timer from the heap"""
        return Timer(self, jitter, action, *args, **kwargs)

    def _schedule_top(self):
        """Schedule a call_later for the soonest timer.

        Assumes the heap is non-empty and there is no pending ``rtimer``.
        """
        top = self.heap[0]
        ival = top.expire - time.time()
        if ival < 0:
            ival = 0
        loop = get_event_loop()
        self.rtimer = loop.call_later(ival, self.expire)

    def add(self, timer):
        """Add a timer to the heap"""
        if self.heap:
            top = self.heap[0]
        else:
            top = None

        assert timer not in self.timers
        self.timers[timer] = timer
        heapq.heappush(self.heap, timer)

        # Check to see if we need to reschedule the soonest expiration.
        # Only do this if we aren't already in the middle of expiring.
        if self.heap[0] != top and not self.expiring:
            if self.rtimer is not None:
                self.rtimer.cancel()
                self.rtimer = None

        # If we are expiring timers right now then that will reschedule
        # as appropriate; otherwise start one if we don't have one.
        if self.rtimer is None and not self.expiring:
            self._schedule_top()

    def expire(self):
        """Fire all timers whose deadline has passed.

        Invoked by the event loop (scheduled via ``call_later``).
        """
        try:
            # Mark expiring and forget the (now firing) handle.
            self.expire_gen += 1
            self.expiring = True
            self.rtimer = None

            while True:
                if not self.heap:
                    return

                top = self.heap[0]
                ctime = time.time()
                if top.expire > ctime:
                    return

                # remove the timer and run it
                expired = heapq.heappop(self.heap)
                del self.timers[expired]
                expired.expire = None
                expired.run()
        except Exception as ex:
            self.logger.error("Unexpected Exception: %s" % str(ex))
        finally:
            # rtimer is never set while expiring is True
            assert self.rtimer is None

            # Schedule the next expiration and clear the expiring flag.
            if self.heap:
                self._schedule_top()
            self.expiring = False

    def _remove(self, timer):
        """Remove timer from heap; presence is assumed."""
        assert timer.timer_heap == self
        del self.timers[timer]
        assert timer in self.heap
        self.heap.remove(timer)
        heapq.heapify(self.heap)

    def remove(self, timer):
        """Remove a timer from the heap, return True if already run"""
        # This is somewhat expensive as we have to heapify.
        if timer in self.timers:
            self._remove(timer)
            return False
        else:
            return True

    def remove_all_timers(self):
        """Remove all waiting timers and cancel any pending expiration."""
        if self.rtimer is not None:
            self.rtimer.cancel()

        self.timers = {}
        self.heap = []
        self.rtimer = None
        self.expiring = False

    def quit(self):
        """Cancel all pending timers.  Safe to call at shutdown."""
        self.remove_all_timers()

# END
