#
# GtkMain.py -- pygtk threading help routines.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""
GUI threading help routines.

Usage:

   import GtkMain

   # See constructor for GtkMain for options
   self.mygtk = GtkMain.GtkMain()

   # NOT THIS
   #gtk.main()
   # INSTEAD, main thread calls this:
   self.mygtk.mainloop()
   
   # (asynchronous call)
   self.mygtk.gui_do(method, arg1, arg2, ... argN, kwd1=val1, ..., kwdN=valN)

   # OR 
   # (synchronous call)
   res = self.mygtk.gui_call(method, arg1, arg2, ... argN, kwd1=val1, ..., kwdN=valN)

   # To cause the GUI thread to terminate the mainloop
   self.mygtk.qui_quit()
   
   """
import sys, traceback
import thread, threading
import logging
import Queue as que

import gtk
from ginga.misc import Task, Future


class GtkMain(object):

    def __init__(self, queue=None, logger=None, ev_quit=None):
        # You can pass in a queue if you prefer to do so
        if not queue:
            queue = que.Queue()
        self.gui_queue = queue
        # You can pass in a logger if you prefer to do so
        if logger == None:
            logger = logging.getLogger('GtkHelper')
        self.logger = logger
        if not ev_quit:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        
        self.gui_thread_id = None
        
    def update_pending(self, timeout=0.0):
        """Process all pending GTK events and return.  _timeout_ is a tuning
        parameter for performance.
        """
        # Process "out-of-band" GTK events
        try:
            while gtk.events_pending():
                #gtk.main_iteration(False)
                gtk.main_iteration()
        finally:
            pass

        done = False
        while not done:
            # Process "in-band" GTK events
            try:
                future = self.gui_queue.get(block=True, 
                                            timeout=timeout)

                # Execute the GUI method
                try:
                    try:
                        res = future.thaw(suppress_exception=False)

                    except Exception, e:
                        future.resolve(e)

                        self.logger.error("gui error: %s" % str(e))
                        try:
                            (type, value, tb) = sys.exc_info()
                            tb_str = "".join(traceback.format_tb(tb))
                            self.logger.error("Traceback:\n%s" % (tb_str))

                        except Exception, e:
                            self.logger.error("Traceback information unavailable.")

                finally:
                    pass

                    
            except que.Empty:
                done = True
                
            except Exception, e:
                self.logger.error("Main GUI loop error: %s" % str(e))
                
        # Process "out-of-band" GTK events again
        try:
            while gtk.events_pending():
                #gtk.main_iteration(False)
                gtk.main_iteration()
        finally:
            pass

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
        except Exception, e:
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

        while not self.ev_quit.isSet():
            self.update_pending(timeout=timeout)

    def gui_quit(self):
        "Call this to cause the GUI thread to quit the mainloop."""
        self.ev_quit.set()
        

# END
