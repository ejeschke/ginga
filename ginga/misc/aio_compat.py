#
# aio_compat.py -- bridge between sync (thread-resolved) results and
#                  awaitables on a single asyncio event loop.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Helpers that let a result object that is normally resolved from a
worker thread (via a :class:`threading.Event`) *also* be awaited on a
single asyncio event loop.

This is what allows Ginga's :class:`~ginga.misc.Future.Future` and
:class:`~ginga.misc.Task.Task` to work unchanged with the threaded task
pool while additionally being ``await``-able when Ginga is driven by a
single event loop (e.g. in a Pyodide/browser environment).
"""
import asyncio


def get_event_loop():
    """Return the running loop if there is one, else the current loop.

    Prefers :func:`asyncio.get_running_loop` (the only correct call from
    within a coroutine) and falls back to :func:`asyncio.get_event_loop`
    for the rare case of being called outside a running loop.
    """
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.get_event_loop()


class AioCompletion:
    """Bridges a synchronously-resolved result to an awaitable.

    A host object (Future/Task) keeps one of these.  When the host
    resolves its result it calls :meth:`resolve`; any coroutine that
    ``await``-ed the host (which delegates to :meth:`__await__`) is then
    woken with the value.

    The underlying :class:`asyncio.Future` is created lazily, only if
    someone actually awaits -- so in a pure threaded environment (no
    event loop) this object costs nothing and never touches asyncio.
    """

    def __init__(self):
        self._fut = None
        self._loop = None
        self._done = False
        self._value = None

    def resolve(self, value):
        """Record the result and wake any async waiter."""
        self._value = value
        self._done = True
        fut = self._fut
        if fut is None:
            # nobody is awaiting (or only thread waiters); nothing to do
            return

        loop = self._loop

        def _set():
            if not fut.done():
                fut.set_result(value)

        # If we are resolving from a different thread than the loop
        # (e.g. a worker thread in mixed mode), marshal onto the loop.
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if loop is not None and running is not loop:
            try:
                loop.call_soon_threadsafe(_set)
            except RuntimeError:
                # loop is closed; drop it
                pass
        else:
            _set()

    def future(self):
        """Return (creating if needed) the awaitable asyncio.Future."""
        if self._fut is None:
            loop = get_event_loop()
            self._loop = loop
            self._fut = loop.create_future()
            if self._done and not self._fut.done():
                self._fut.set_result(self._value)
        return self._fut

    def __await__(self):
        return self.future().__await__()

# END
