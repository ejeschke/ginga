#
# GwMain.py -- application threading help routines.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, traceback
import os
import threading
import logging
import time
import ginga.util.six as six
if six.PY2:
    import thread
    import Queue
else:
    import _thread as thread
    import queue as Queue

from ginga.util.six.moves import filter
from ginga.misc import Task, Future, Callback
from collections import deque

class GwMain(Callback.Callbacks):

    def __init__(self, queue=None, logger=None, ev_quit=None, app=None,
                 thread_pool=None):
        Callback.Callbacks.__init__(self)

        self.enable_callback('shutdown')

        # You can pass in a queue if you prefer to do so
        if not queue:
            queue = Queue.PriorityQueue()
            #queue = Queue.Queue()
        self.gui_queue = queue
        # You can pass in a logger if you prefer to do so
        if logger is None:
            logger = logging.getLogger('GwMain')
        self.logger = logger
        if not ev_quit:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        self.app = app
        # Mark our thread id
        #self.gui_thread_id = None
        self.gui_thread_id = thread.get_ident()

        self.threadPool = thread_pool
        # For asynchronous tasks on the thread pool
        self.tag = 'master'
        self.shares = ['threadPool', 'logger']

        self.oneshots = {}


    def get_widget(self):
        return self.app

    def get_threadPool(self):
        return self.threadPool

    def _execute_future(self, future):
        # Execute the GUI method
        try:
            try:
                res = future.thaw(suppress_exception=False)

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
        self.gui_queue.put(future)

        my_id = thread.get_ident()
        if my_id != self.gui_thread_id:
            return future

    def gui_do(self, method, *args, **kwdargs):
        return self.gui_do_priority(0, method, *args, **kwdargs)

    def gui_call(self, method, *args, **kwdargs):
        """General method for synchronously calling into the GUI.
        This waits until the method has completed before returning.
        """
        my_id = thread.get_ident()
        if my_id == self.gui_thread_id:
            return method(*args, **kwdargs)
        else:
            future = self.gui_do(method, *args, **kwdargs)
            return future.wait()

    def gui_do_future(self, future):
        self.gui_queue.put(future)
        return future

    def gui_do_oneshot(self, catname, method, *args, **kwdargs):
        if not catname in self.oneshots:
            deq = self.oneshots.setdefault(catname, deque([], 1))
        else:
            deq = self.oneshots[catname]

        future = Future.Future()
        future.freeze(method, *args, **kwdargs)
        deq.append(future)

        my_id = thread.get_ident()
        if my_id != self.gui_thread_id:
            return future

    def nongui_do(self, method, *args, **kwdargs):
        task = Task.FuncTask(method, args, kwdargs, logger=self.logger)
        return self.nongui_do_task(task)

    def nongui_do_cb(self, tup, method, *args, **kwdargs):
        task = Task.FuncTask(method, args, kwdargs, logger=self.logger)
        task.register_callback(tup[0], args=tup[1:])
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
            raise(e)

    def is_gui_thread(self):
        my_id = thread.get_ident()
        return my_id == self.gui_thread_id

    def assert_gui_thread(self):
        my_id = thread.get_ident()
        assert my_id == self.gui_thread_id, \
               Exception("Non-GUI thread (%d) is executing GUI code!" % (
            my_id))

    def assert_nongui_thread(self):
        my_id = thread.get_ident()
        assert my_id != self.gui_thread_id, \
               Exception("GUI thread (%d) is executing non-GUI code!" % (
            my_id))

    def mainloop(self, timeout=0.001):
        # Mark our thread id
        self.gui_thread_id = thread.get_ident()

        while not self.ev_quit.isSet():

            self.update_pending(timeout=timeout)

    def gui_quit(self):
        "Call this to cause the GUI thread to quit the mainloop."""
        self.ev_quit.set()

        self.make_callback('shutdown')

        self.app.process_end()

    def _quit(self):
        self.gui_quit()

# END
