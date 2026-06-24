#
# GwMain.py -- application threading help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import traceback
import threading
import time
import asyncio

from ginga.misc import Task, Future, Callback
from ginga.misc.aio_compat import get_event_loop as aio_get_event_loop
from ginga.toolkit import toolkit
from ginga.misc import log
from collections import deque

import queue as Queue


class GwMain(Callback.Callbacks):

    def __init__(self, queue=None, logger=None, ev_quit=None, app=None,
                 thread_pool=None, task_pool=None, async_mode=None):
        Callback.Callbacks.__init__(self)

        self.enable_callback('shutdown')

        # You can pass in a queue if you prefer to do so
        if not queue:
            queue = Queue.Queue()
        self.gui_queue = queue
        self.priority_gui_queue = Queue.PriorityQueue()

        # You can pass in a logger if you prefer to do so
        if logger is None:
            logger = log.NullLogger()
        self.logger = logger

        if not ev_quit:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

        self.app = app
        # Mark our thread id
        self.gui_thread_id = threading.get_ident()

        # ``task_pool`` is the preferred name; ``thread_pool`` is kept for
        # backward compatibility.  The pool need only implement the
        # addTask/startall/stopall interface (see ginga.misc.Task).
        if task_pool is None:
            task_pool = thread_pool
        self.threadPool = task_pool

        # In "async mode" the whole application runs on a single event
        # loop (e.g. Pyodide/the browser): there is no separate GUI thread,
        # so cross-thread marshaling and blocking waits must be avoided.
        # If not specified, infer it from the pool type.
        if async_mode is None:
            async_mode = isinstance(task_pool, Task.AsyncTaskPool)
        self.async_mode = async_mode

        # handle for the periodic event pump used in async mode
        self._async_pump_interval = 0.05

        # For asynchronous tasks on the thread pool
        self.tag = 'master'
        self.shares = ['threadPool', 'logger']

        self.oneshots = {}

    def get_widget(self):
        return self.app

    def get_threadPool(self):
        return self.threadPool

    def get_taskpool_type(self):
        """Return the kind of task pool in use.

        Returns
        -------
        kind : str
            ``'async'`` if tasks run on a single event loop (e.g. when
            running in-situ under Pyodide), or ``'thread'`` if they run
            on a pool of worker threads.

        This lets callers (e.g. plugins doing network I/O) choose an
        appropriate strategy -- a synchronous ``requests`` download on a
        worker thread vs. an awaited browser fetch -- without inspecting
        internals.
        """
        return 'async' if self.async_mode else 'thread'

    def set_gui_thread(self):
        self.gui_thread_id = threading.get_ident()

    def _execute_future(self, future):
        # Execute the GUI method
        try:
            try:
                future.thaw(suppress_exception=False)

            except Exception as e:
                self.logger.error("gui event loop error: %s" % str(e))
                try:
                    (type, value, tb) = sys.exc_info()
                    tb_str = "".join(traceback.format_tb(tb))
                    self.logger.error("Traceback:\n%s" % (tb_str))

                except Exception:
                    self.logger.error("Traceback information unavailable.")

                future.resolve(e)

        except Exception as e2:
            self.logger.error("Exception resolving future: %s" % str(e2))

    def update_pending(self, timeout=0.0, elapsed_max=0.02):

        self.assert_gui_thread()

        # Process "out-of-band" events
        # self.logger.debug("1. processing out-of-band GUI events")
        try:
            self.app.process_events()

        except Exception as e:
            self.logger.error(str(e))

        # Process "in-band" GUI events
        # self.logger.debug("2. processing approx %d in-band GUI events" % (
        #                    self.gui_queue.qsize()))
        done = False
        time_start = time.time()

        # First process priority futures
        while not done:
            try:
                future = self.priority_gui_queue.get(block=False)
                self._execute_future(future)

            except Queue.Empty:
                break

            if time.time() - time_start > elapsed_max:
                done = True

        # Next process non-priority futures
        while not done:
            try:
                future = self.gui_queue.get(block=True,
                                            timeout=timeout)
                self._execute_future(future)

            except Queue.Empty:
                done = True

            if time.time() - time_start > elapsed_max:
                done = True

        # Execute all the one-shots
        # self.logger.debug("3. processing one-shot GUI events")
        deqs = list(filter(lambda deq: len(deq) > 0, self.oneshots.values()))
        for deq in deqs:
            try:
                future = deq.pop()

                self._execute_future(future)

            except IndexError:
                continue

        # Process "out-of-band" events, again
        # self.logger.debug("4. processing out-of-band GUI events")
        try:
            self.app.process_events()

        except Exception as e:
            self.logger.error(str(e))

        # self.logger.debug("5. done")

    def gui_do_priority(self, priority, method, *args, **kwdargs):
        """General method for asynchronously calling into the GUI.
        It makes a future to call the given (method) with the given (args)
        and (kwdargs) inside the gui thread.  If the calling thread is a
        non-gui thread the future is returned.
        """
        future = Future.Future(priority=priority)
        future.freeze(method, *args, **kwdargs)
        self.priority_gui_queue.put(future)

        my_id = threading.get_ident()
        if my_id != self.gui_thread_id:
            return future

    def gui_do(self, method, *args, **kwdargs):
        future = Future.Future(priority=0)
        future.freeze(method, *args, **kwdargs)
        self.gui_queue.put(future)

        my_id = threading.get_ident()
        if my_id != self.gui_thread_id:
            return future

    def gui_call(self, method, *args, **kwdargs):
        """General method for synchronously calling into the GUI.
        This waits until the method has completed before returning.
        """
        my_id = threading.get_ident()
        if my_id == self.gui_thread_id:
            return method(*args, **kwdargs)
        else:
            future = self.gui_do(method, *args, **kwdargs)
            return future.wait()

    def gui_do_future(self, future):
        self.gui_queue.put(future)
        return future

    def gui_do_oneshot(self, catname, method, *args, **kwdargs):
        if catname not in self.oneshots:
            deq = self.oneshots.setdefault(catname, deque([], 1))
        else:
            deq = self.oneshots[catname]

        future = Future.Future()
        future.freeze(method, *args, **kwdargs)
        deq.append(future)

        my_id = threading.get_ident()
        if my_id != self.gui_thread_id:
            return future

    def make_async_gui_callback(self, name, *args, **kwargs):
        # NOTE: asynchronous!
        self.gui_do(self.make_callback, name, *args, **kwargs)

    def make_gui_callback(self, name, *args, **kwargs):
        if self.is_gui_thread():
            return self.make_callback(name, *args, **kwargs)
        else:
            # note: this cannot be "gui_call"--locks viewer.
            # so call becomes async when a non-gui thread invokes it
            self.gui_do(self.make_callback, name, *args, **kwargs)

    def _make_func_task(self, method, args, kwdargs):
        # In async mode use a cooperative task that awaits coroutine
        # results on the single event loop; otherwise a plain FuncTask
        # for the thread pool.
        if self.async_mode:
            return Task.AsyncFuncTask(method, args, kwdargs, logger=self.logger)
        return Task.FuncTask(method, args, kwdargs, logger=self.logger)

    def nongui_do(self, method, *args, **kwdargs):
        task = self._make_func_task(method, args, kwdargs)
        return self.nongui_do_task(task)

    def nongui_do_cb(self, tup, method, *args, **kwdargs):
        task = self._make_func_task(method, args, kwdargs)
        _args = [] if len(tup) == 1 else tup[1:]
        task.add_callback('resolved', tup[0], *_args)
        return self.nongui_do_task(task)

    def nongui_do_future(self, future):
        task = Task.FuncTask(future.thaw, (), {}, logger=self.logger)
        return self.nongui_do_task(task)

    def nongui_do_task(self, task):
        try:
            task.init_and_start(self)
            return task
        except Exception as e:
            self.logger.error("Error starting task: %s" % (str(e)))
            raise e

    def nongui_foreach(self, items, worker, on_each=None, on_done=None,
                       yield_interval=0.05, is_cancelled=None):
        """Run ``worker(item)`` for each item off the GUI while keeping the
        UI responsive.

        In async (single event loop) mode this runs as a coroutine that
        yields control back to the loop on a time budget (see
        ``yield_interval``), so UI events and repaints are serviced as the
        work proceeds; in threaded mode it runs as a single nongui task on a
        worker thread.  The caller-facing API is identical in both modes.

        This is the cooperative escape hatch for CPU-bound "nongui" work in
        the single-threaded (browser/Pyodide) backend, where a nongui task
        is just a coroutine on the one event loop: without periodic yields a
        long loop starves the UI exactly like a synchronous call would.

        Parameters
        ----------
        items : iterable
            The work items.
        worker : callable
            ``worker(item) -> result``.  Runs off the GUI; must not touch
            widgets directly.
        on_each : callable or None
            ``on_each(item, result)``, scheduled on the GUI (via gui_do)
            after each item completes -- use for incremental display /
            progress.
        on_done : callable or None
            ``on_done(results)``, scheduled on the GUI after all items
            complete (not called if cancelled).
        yield_interval : float
            Minimum wall-clock seconds between event-loop yields (async mode
            only).  The loop is given control only after this much time has
            elapsed, *not* after every item -- each yield is a full
            round-trip to the browser event loop costing real time, so
            yielding per item would make the total cost roughly constant
            regardless of how fast the work itself is (e.g. when results are
            cached).  Yielding on a time budget keeps the UI responsive while
            letting a fast (cached) run finish with few yields.
        is_cancelled : callable or None
            ``is_cancelled() -> bool``, checked before each item; abort if
            it returns True.

        Returns the task object.
        """
        items = list(items)

        if self.async_mode:
            async def _run_async():
                results = []
                t_last = time.monotonic()
                for item in items:
                    if is_cancelled is not None and is_cancelled():
                        return
                    results.append(worker(item))
                    if on_each is not None:
                        self.gui_do(on_each, item, results[-1])
                    if time.monotonic() - t_last >= yield_interval:
                        await asyncio.sleep(0)
                        t_last = time.monotonic()
                if on_done is not None:
                    self.gui_do(on_done, results)
            return self.nongui_do(_run_async)

        def _run_thread():
            results = []
            for item in items:
                if is_cancelled is not None and is_cancelled():
                    return
                results.append(worker(item))
                if on_each is not None:
                    self.gui_do(on_each, item, results[-1])
            if on_done is not None:
                self.gui_do(on_done, results)
        return self.nongui_do(_run_thread)

    def is_gui_thread(self):
        # In async mode there is only one thread; treat it as the GUI
        # thread so gui_call() runs inline and never blocks on a future.
        if self.async_mode:
            return True
        my_id = threading.get_ident()
        return my_id == self.gui_thread_id

    def assert_gui_thread(self):
        if self.async_mode:
            return
        my_id = threading.get_ident()
        assert my_id == self.gui_thread_id, \
            Exception("Non-GUI thread (%d) is executing GUI (%d) code!" % (
                my_id, self.gui_thread_id))

    def assert_nongui_thread(self):
        # Single-threaded: everything runs on the one (GUI) thread, so
        # this assertion is not meaningful in async mode.
        if self.async_mode:
            return
        my_id = threading.get_ident()
        assert my_id != self.gui_thread_id, \
            Exception("GUI thread (%d) is executing non-GUI code!" % (
                my_id))

    def mainloop(self, timeout=0.001):
        # Mark our thread id
        self.gui_thread_id = threading.get_ident()

        if self.async_mode:
            # Single event loop.  Two sub-cases:
            #
            #  * A loop is already running (e.g. Pyodide/the browser): we
            #    cannot block, so install a cooperative pump and return --
            #    the host event loop keeps everything alive.
            #
            #  * No loop is running (e.g. a native CLI invocation with
            #    --task-pool=async): we own the loop and must run it here
            #    until quit, otherwise mainloop() would return immediately
            #    and the application would exit early.
            try:
                asyncio.get_running_loop()
                hosted = True
            except RuntimeError:
                hosted = False

            if hosted:
                self.start_async_pump()
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.start_async_pump()
            try:
                loop.run_until_complete(self._async_wait_quit())
            finally:
                loop.close()
            return

        if toolkit == 'gtk4':
            self.app.add_periodic_callback(0.1,
                                           lambda: self.update_pending(timeout=timeout))
            self.app._mainloop()
            return

        while not self.ev_quit.is_set():
            self.update_pending(timeout=timeout)

    def start_async_pump(self, interval=None):
        """Drive ``update_pending`` from a periodic callback on the running
        event loop, for single-threaded (async) operation.  Returns
        immediately; the host event loop continues running.
        """
        if interval is not None:
            self._async_pump_interval = interval
        loop = aio_get_event_loop()

        def _pump():
            if self.ev_quit.is_set():
                return
            try:
                # non-blocking: drain whatever is queued and return
                self.update_pending(timeout=0.0)
            except Exception as e:
                self.logger.error("error in event pump: %s" % (str(e),))
            loop.call_later(self._async_pump_interval, _pump)

        loop.call_soon(_pump)

    async def _async_wait_quit(self):
        """Keep the (owned) event loop alive until ``ev_quit`` is set.

        Used when running async-mode on a native platform, where we run
        the loop ourselves rather than relying on a host (browser) loop.
        """
        while not self.ev_quit.is_set():
            await asyncio.sleep(self._async_pump_interval)

    def gui_quit(self):
        """Call this to cause the GUI thread to quit the mainloop."""
        self.ev_quit.set()

        self.make_callback('shutdown')

        self.app.process_end()

    def _quit(self):
        self.gui_quit()

# END
