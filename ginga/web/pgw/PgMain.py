#
# PgMain.py -- web application threading help routines.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function
import sys, traceback
import os
import threading
import logging
import ginga.util.six as six
if six.PY2:
    import thread
    import Queue
else:
    import _thread as thread
    import queue as Queue

import tornado.web
import tornado.template
import tornado.ioloop

from ginga.web.pgw import templates, js, PgHelp
from ginga.misc import Task, Future, Callback

class PgMain(Callback.Callbacks):

    def __init__(self, queue=None, logger=None, ev_quit=None,
                 host='localhost', port=9909, app=None):
        super(PgMain, self).__init__()

        self.enable_callback('shutdown')

        # You can pass in a queue if you prefer to do so
        if not queue:
            queue = Queue.Queue()
        self.gui_queue = queue
        # You can pass in a logger if you prefer to do so
        if logger is None:
            logger = logging.getLogger('PgMain')
        self.logger = logger
        if not ev_quit:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        self.host = host
        self.port = port
        self.app = app
        self.gui_thread_id = None

        # Get screen size
        ## desktop = self.app.desktop()
        ## #rect = desktop.screenGeometry()
        ## rect = desktop.availableGeometry()
        ## size = rect.size()
        ## self.screen_wd = size.width()
        ## self.screen_ht = size.height()
        self.screen_wd = 600
        self.screen_ht = 800

    def get_widget(self):
        return self.app

    def get_screen_size(self):
        return (self.screen_wd, self.screen_ht)

    def update_pending(self, timeout=0.0):

        #print "1. PROCESSING OUT-BAND"
        try:
            #self.app.processEvents()
            pass
        except Exception as e:
            self.logger.error(str(e))
            # TODO: traceback!

        done = False
        while not done:
            #print "2. PROCESSING IN-BAND len=%d" % self.gui_queue.qsize()
            # Process "in-band" Qt events
            try:
                future = self.gui_queue.get(block=True,
                                            timeout=timeout)

                # Execute the GUI method
                try:
                    try:
                        res = future.thaw(suppress_exception=False)

                    except Exception as e:
                        future.resolve(e)

                        self.logger.error("gui error: %s" % str(e))
                        try:
                            (type, value, tb) = sys.exc_info()
                            tb_str = "".join(traceback.format_tb(tb))
                            self.logger.error("Traceback:\n%s" % (tb_str))

                        except Exception as e:
                            self.logger.error("Traceback information unavailable.")

                finally:
                    pass


            except Queue.Empty:
                done = True

            except Exception as e:
                self.logger.error("Main GUI loop error: %s" % str(e))
                #pass

        # Process "out-of-band" events
        #print "3. PROCESSING OUT-BAND"
        try:
            #self.app.processEvents()
            pass
        except Exception as e:
            self.logger.error(str(e))
            # TODO: traceback!


    def gui_do(self, method, *args, **kwdargs):
        """General method for asynchronously calling into the GUI.
        It makes a future to call the given (method) with the given (args)
        and (kwdargs) inside the gui thread.  If the calling thread is a
        non-gui thread the future is returned.
        """
        future = Future.Future()
        future.freeze(method, *args, **kwdargs)
        self.gui_queue.put(future)

        my_id = thread.get_ident()
        if my_id != self.gui_thread_id:
            return future

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

        ## while not self.ev_quit.isSet():
        ##     self.update_pending(timeout=timeout)
        self.start(use_thread=False)

    def start(self, use_thread=False, no_ioloop=False):
        #self.thread_pool.startall()

        js_path = os.path.dirname(js.__file__)

        # create and run the app
        self.server = tornado.web.Application([
            (r"/js/(.*\.js)", tornado.web.StaticFileHandler,
             {"path":  js_path}),
            (r"/app", PgHelp.WindowHandler,
              dict(name='Application', url='/app', app=self.app)),
            (r"/app/socket", PgHelp.ApplicationHandler,
              dict(name='ApplicationSocketInterface', app=self.app)),
            ],
               app=self.app, logger=self.logger)

        self.server.listen(self.port, self.host)
        self.base_url = "http://%s:%d/app" % (self.host, self.port)
        self.logger.info("ginga web now running at " + self.base_url)

        if no_ioloop:
            self.t_ioloop = None
        else:
            self.t_ioloop = tornado.ioloop.IOLoop.instance()
            if use_thread:
                task = Task.FuncTask2(self.t_ioloop.start)
                self.thread_pool.addTask(task)
            else:
                self.t_ioloop.start()

    def stop(self):
        # how to stop tornado server?
        if not self.t_ioloop is None:
            self.t_ioloop.stop()

        self.thread_pool.stopall()
        self.ev_quit.set()


    def gui_quit(self):
        "Call this to cause the GUI thread to quit the mainloop."""
        self.ev_quit.set()

        self.make_callback('shutdown')

        #self.app.quit()

    def _quit(self):
        self.gui_quit()


# END
