#
# Task.py -- Basic command pattern and thread pool implementation.
#
# Eric Jeschke (eric@naoj.org)
#
# Copyright (c) Eric R. Jeschke.  All rights reserved.
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
from __future__ import print_function

import sys, time, os
import ginga.util.six as six
if six.PY2:
    import thread
    import Queue
else:
    import _thread as thread
    import queue as Queue
    # see http://bugs.python.org/issue7946
    _swival = 0.000001
    sys.setswitchinterval(_swival)

import threading
import traceback
 
from ginga.util.six.moves import map, zip


class TaskError(Exception):
    """Exception generated for task errors"""
    pass

class TaskTimeout(TaskError):
    """Exception generated when timing out waiting on a task"""
    pass

class UserTaskException(Exception):
    pass


# ------------ BASIC TASKS ------------

class Task(object):
    """This class implements a basic Task (command) abstraction.  The
    methods define the interface for starting, cancelling, waiting on a
    task, etc.
    """

    def __init__(self):
        """
        The constructor sets bare essentials for a Task object.  See the
        initialize() and start() methods.
        """
        self.ev_done = threading.Event()
        self.callbacks = Queue.Queue()
        self.tag = None
        self.logger = None
        self.threadPool = None
        # Lock for task state critical sections
        self.tlock = threading.RLock()
        # Parent task can set this (or add to it) explicitly to determine
        # which values will be copied when it calls initialize() on a child
        # task.
        self.shares = ['logger', 'threadPool', 'shares']

        super(Task, self).__init__()


    def initialize(self, taskParent, override=None):
        """This method initializes a task for (re)use.  taskParent is the
        object instance of the parent task, or a 'task environment' (something
        that runs tasks).
        If subclass overrides this method, it should call the superclass
        method at some point.

        - Copy shared data from taskParent, overriding items from _override_
          if they are present there ('contagion' of task values).
        - Generate a unique tag, to be used with the Gen2 Monitor.
        - Clear done event, initialize times and result.
        """
        # For now, punt if we have no apparent parent
        if taskParent and hasattr(taskParent, 'shares'):
            # Copy some variables from our parent task, unless they are being
            # overridden explicitly.  Using this general "contagion" mechanism,
            # a task can cause it's children to have values available to them
            # without passing them explicitly.
            for var in taskParent.shares:
                if override and var in override:
                    self.__dict__[var] = override[var]
                else:
                    #print "COPYING VAR FROM PARENT: %s(%s)" % (var, str(taskParent.__dict__[var]))
                    self.__dict__[var] = taskParent.__dict__[var]

        else:
            #raise TaskError("Cannot initialize task without a taskParent!")
            pass

        # Generate our own unique tag.  'tagger' should have been transmitted
        # from the parent task
        if not self.tag:
            try:
                self.tag = str(taskParent) + '.' + self.tagger.get_tag(self)
            except:
                # Failed--fall back to internal tagger
                self.tag = get_tag(taskParent)
            
        # Some per-task specific initialization
        self.ev_done.clear()
        self.starttime = time.time()
        self.endtime = 0
        self.totaltime = 0
        self.result = None

        return self.tag

    def start(self):
        """This method starts a task executing and returns immediately.
        Subclass should override this method, if it has an asynchronous
        way to start the task and return immediately.
        """
        if self.threadPool:
            self.threadPool.addTask(self)

            # Lets other threads have a chance to run
            time.sleep(0)
        else:
            raise TaskError("start(): nothing to start for task %s" % self)


    def init_and_start(self, taskParent, override={}):
        """Convenience method to initialize and start a task.
        """
        tag = self.initialize(taskParent, override=override)
        self.start()

        return tag

        
    def check_state(self):
        """Abstract method that should check for pause, cancellation, or
        any other sort of preemption event.
        """
        pass


    def extend_shares(self, varlist):
        shares = set(self.shares)
        for var in varlist:
            if hasattr(self, var):
                shares.add(var)
        
        self.shares = shares

                
    def stop(self):
        """This method cancels an executing task (if possible).
        Subclass should override this method.
        Return True if task could be cancelled, False if not?
        """
        raise TaskError("Task %s: subclass should override stop() method!" % (
                        self))

    def pause(self):
        """This method pauses an executing task (if possible).
        Subclass should override this method.
        Return True if task could be paused, False if not?
        """
        raise TaskError("Task %s: subclass should override pause() method!" % (
                        self))

    def resume(self):
        """This method resumes an executing task (if possible).
        Subclass should override this method, should not call super.resume().
        Return True if task could be resumed, False if not?
        """
        raise TaskError("Task %s: subclass should override resume() method!" % (
            self))

    def wait(self, timeout=None):
        """This method waits for an executing task to finish.
        Subclass can override this method if necessary.
        """
        self.ev_done.wait(timeout=timeout)

        if not self.ev_done.isSet():
            raise TaskTimeout("Task %s timed out." % self)

        # --> self.result is set
        # If it is an exception, then raise it in this waiter
        if isinstance(self.result, Exception):
            raise self
        
        # Release waiters and perform callbacks
        # done() has already been called, because of self.ev_done check
        # "asynchronous" tasks should could call done() here
        #self.done(self.result)

        return self.result


    def step(self):
        """If a task has a way of stepping through an operation.  It can
        implement this method.  Subclass should not call super.step().
        """
        raise TaskError("Task %s: subclass should override step() method!" % \
                        self)


    def execute(self):
        """This method does the work of a task (if executed by the
        thread pool) and returns when it is finished.  *** Subclass should
        override this method! ***  It should take no arguments, and can
        return anything.
        """
        raise TaskError("Task %s: subclass should override execute() method!" % \
                        self)


    def done(self, result, noraise=False):
        """This method is called when a task has finished executing.
        Subclass can override this method if desired, but should call
        superclass method at the end.
        """
        # [??] Should this be in a critical section?

        # Has done() already been called on this task?
        if self.ev_done.isSet():
            # ??
            if isinstance(self.result, Exception) and (not noraise):
                raise self.result
            return self.result
        
        # calculate running time and other finalization
        self.endtime = time.time()
        try:
            self.totaltime = self.endtime - self.starttime
        except AttributeError:
            # task was not initialized properly
            self.totaltime = 0.0
        self.result = result

        # Release thread waiters
        self.ev_done.set()

        # Perform callbacks for event-style waiters
        self.do_callbacks()

        # If the result is an exception, then our final act is to raise
        # it in the caller, unless the caller explicitly supressed that
        if isinstance(result, Exception) and (not noraise):
            raise result

        return result


    def register_callback(self, fn, args=None):
        """This method is called to register a callback function to be
        called when a task terminates.
        Subclass should probably not override this method.
        """
        if args is None:
            args = []
            
        if callable(fn):
            self.callbacks.put((fn, args))
        else:
            raise TaskError("Function argument is not a callable: %s" % \
                            str(fn))


    def do_callbacks(self):
        """Makes callbacks on all registered functions waiting on this task.
        """
        
        while not self.callbacks.empty():
            (fn, rest) = self.callbacks.get()

            args = [self.result]
            args.extend(rest)
            
            fn(*args)


    def get_tag(self):
        """This is only valid AFTER initialize() has been called on the task.
        """
        return self.tag

    def __str__(self):
        """Returns a string representation of a task (e.g. for debugging).
        Subclass can override this method if desired.
        """
        return str(self.tag)

    def __lt__(self, other):
        return False

    def getExecutionTime(self):
        return self.totaltime
    

    def runTask(self, task, timeout=None):
        """Run a child task to completion.  Returns the result of
        the child task.
        """
        # Initialize the task.
        task.initialize(self)

        # Start the task.
        task.start()

        # Lets other threads run
        time.sleep(0)

        # Wait for it to finish.
        res = task.wait(timeout=timeout)

        # Now we're done
        return res

    
    def run(self, task, timeout=None):
        """Run a child task to completion.  Returns the result of
        the child task.  Simply calls runTask().
        """
        return self.runTask(task, timeout=timeout)

        
# For testing...

class printTask(Task):
    """Simple task that prints msg."""
    def __init__(self, msg):
        self.msg = msg
        super(printTask, self).__init__()

    def execute(self):
        print(self.msg)
        
class sleepTask(Task):
    """Simple task that sleeps for delay seconds."""
    def __init__(self, delay):
        self.delay = delay
        super(sleepTask, self).__init__()

    def execute(self):
        self.ev_done.wait(timeout=self.delay)
        
class FuncTask(Task):
    """Simple task that calls func and returns func's return value."""
    def __init__(self, func, args, kwdargs, logger=None):
        self.func = func
        self.args = args
        self.kwdargs = kwdargs
        self.logger = logger
        super(FuncTask, self).__init__()
        
    def execute(self):
        if self.logger:
            # Cap logging size around 500 characters
            s_args = str(self.args)
            if len(s_args) > 500:
                s_args = s_args[:500]
            s_kwdargs = str(self.kwdargs)
            if len(s_kwdargs) > 500:
                s_kwdargs = s_kwdargs[:500]
            self.logger.debug("Running %s(%s, %s)" % (
                self.func.__name__, s_args, s_kwdargs))
            s_args = None
            s_kwdargs = None

        try:
            res = self.func(*self.args, **self.kwdargs)
            self.done(res)

            if self.logger:
                self.logger.debug("Function returned %s" % (
                    str(res)))
                
        except Exception as e:
            if self.logger:
                self.logger.error("Task '%s' terminated with exception: %s" % \
                                  (str(self), str(e)))
                try:
                    (type, value, tb) = sys.exc_info()
                    self.logger.error("Traceback:\n%s" % \
                                      "".join(traceback.format_tb(tb)))

                    tb = None
                except Exception:
                    self.logger.error("Traceback information unavailable.")
            self.done(e)


class FuncTask2(FuncTask):
    """Simple task that calls func and returns func's return value.
    This version lets you specify the positional and keyword arguments
    more naturally 'in place' in the constructor.
    """
    def __init__(self, func, *args, **kwdargs):
        super(FuncTask2, self).__init__(func, args, kwdargs)

    def set_logger(self, logger):
        self.logger = logger
        

def make_tasker(func):
    """make_tasker takes a callable (function, method, etc.) and returns
    a new factory function for generating tasks.  Each factory function is
    designed to consume its arguments and return a task that, when executed,
    will call the function upon the arguments.

    TODO: deprecate this and just use FuncTask, which is easier to
    understand--must change a number of programs first.
    """
    def anonFunc(*args, **kwdargs):
        class anonTask(Task):
            def execute(self):
                self.logger.debug("Executing fn %s" % func)
                try:
                    val = func(*args, **kwdargs)

                    self.logger.debug("Done executing fn %s" % func)
                    return val
                
                except Exception as e:
                    # Log error message and re-raise exception.
                    self.logger.error("fn %s raised exception: %s" % (
                        func, str(e)))
                    raise e

        return anonTask()
    return anonFunc


# ------------ COMPOUND TASKS ------------

class SequentialTaskset(Task):
    """Compound task that runs a series of tasks sequentially.
    """
    
    def __init__(self, taskseq):

        super(SequentialTaskset, self).__init__()

        self.tasklist = list(taskseq)


    def initialize(self, taskParent, **kwdargs):
        self.index = 0

        super(SequentialTaskset, self).initialize(taskParent, **kwdargs)

        
    def step(self):
        """Run the next child task and wait for completion (no timeout)."""
        if self.index >= len(self.tasklist):
            raise TaskError("step(): sequential compound task %s finished" % self)
            
        self.check_state()

        # Select next task from the set and advance the index
        self.task = self.tasklist[self.index]
        self.index += 1

        return self.runTask(self.task)


    def execute(self):
        """Run all child tasks, in order, waiting for completion of each.
        Return the result of the final child task's execution.
        """
        while self.index < len(self.tasklist):
            res = self.step()
            self.logger.debug('SeqSet task %i has completed with result %s' % \
                             (self.index,res))

        # Returns result of last task to quit
        return res


    def stop(self):
        """Interrupt/cancel execution, but will allow current child task
        to complete."""
        #self.ev_intr.set()

        try:
            self.task.stop()

        except TaskError as e:
            self.logger.error("Error cancelling child task: %s" % (str(e)))
            
            
    def addTask(self, task):
        """Append a task to the task sequence.  If the SequentialTaskset has
        already completed execution, this will do nothing unless it is
        restarted (initialize(), start()).
        """
        self.tasklist.append(task)
            

class oldConcurrentAndTaskset(Task):
    """Compound task that runs a set of tasks concurrently, and does not
    return until they all terminate.
    """
    
    def __init__(self, taskseq):

        super(oldConcurrentAndTaskset, self).__init__()

        self.taskseq = taskseq
        self.ev_intr = threading.Event()
        # Used to synchronize compound task termination
        self.regcond = threading.Condition()


    def execute(self):
        """Run all child tasks concurrently in separate threads.
        Return 0 after all child tasks have completed execution.
        """
        self.count = 0
        self.taskset = []
        self.results = {}
        self.totaltime = time.time()

        # Register termination callbacks for all my child tasks.
        for task in self.taskseq:
            self.taskset.append(task)
            task.register_callback(self.child_done, args=[self.count, task])
            self.count += 1

        self.numtasks = self.count
        
        # Now start each child task.
        with self.regcond:
            for task in self.taskset:
                task.initialize(self)

                task.start()

            # Account for time needed to start subtasks
            self.totaltime = time.time() - self.totaltime

            # Now give up the critical section and wait for last child
            # task to terminate.
            while self.count > 0:
                self.regcond.wait()

        # Scan results for errors (exceptions) and raise the first one we find
        for key in self.results.keys():
            value = self.results[key]
            if isinstance(value, Exception):
                (count, task) = key
                self.logger.error("Child task %s terminated with exception: %s" % (
                    task.tag, str(value)))
                raise value

        return 0
            

    def child_done(self, result, count, task):
        """Acquire the condition variable for the compound task object.
        Decrement the thread count.  If we are the last thread to
        finish, release compound task thread, which is blocked in execute().
        """
        with self.regcond:
            self.logger.debug('Concurrent task %d/%d has completed' % (
                self.count, self.numtasks))
            self.count -= 1
            self.taskset.remove(task)
            self.totaltime += task.getExecutionTime()
            self.results[(count, task)] = result
            if self.count <= 0:
                self.regcond.notifyAll()


    def stop(self):
        """Call stop() on all child tasks, and ignore TaskError exceptions.
        Behavior depends on what the child tasks' stop() method does."""
        for task in self.taskset:
            try:
                task.stop()

            except TaskError as e:
                # Task does not have a way to stop it.
                # TODO: notify who?
                pass


    def addTask(self, task):
        """Add a task to the task set.
        """
        with self.regcond:
            self.taskset.append(task)
            task.register_callback(self.child_done, args=[self.numtasks, task])
            self.numtasks += 1
            self.count += 1

        task.initialize(self)
        task.start()

class newConcurrentAndTaskset(Task):
    """Compound task that runs a set of tasks concurrently, and does not
    return until they all terminate.
    """
    
    def __init__(self, taskseq):

        super(newConcurrentAndTaskset, self).__init__()

        self.taskseq = taskseq
        # tuning value for polling inefficiency
        self.idletime = 0.001

        # internal mutex
        self._lock_c = threading.RLock()


    def execute(self):
        """Run all child tasks concurrently in separate threads.
        Return last result after all child tasks have completed execution.
        """

        with self._lock_c:
            self.count = 0
            self.numtasks = 0
            self.taskset = []
            self.results = {}
            self.totaltime = time.time()
            # Start all tasks
            for task in self.taskseq:
                self.taskset.append(task)
                self.numtasks += 1
                task.init_and_start(self)

        num_tasks = self.getNumTasks()
        # Wait on each task to clean up results
        while num_tasks > 0:

            self.check_state()
            
            for i in range(num_tasks):
                try:
                    try:
                        task = self.getTask(i)
                    except IndexError:
                        # A task got deleted from the set.  Jump back out
                        # to outer loop and repoll the number of tasks
                        break
                                        
                    #self.logger.debug("waiting on %s" % task)
                    res = task.wait(timeout=self.idletime)
                
                    #self.logger.debug("finished: %s" % task)
                    self.child_done(res, task)

                except TaskTimeout:
                    continue

                except Exception as e:
                    #self.logger.warn("Subtask propagated exception: %s" % str(e))
                    self.child_done(e, task)
                    continue

            # wait a bit and try again
            #self.ev_quit.wait(self.idletime)

            # re-get number of tasks, in case some were added or deleted
            num_tasks = self.getNumTasks()

        # Scan results for errors (exceptions) and raise the first one we find
        for key in self.results.keys():
            value = self.results[key]
            if isinstance(value, Exception):
                (count, task) = key
                self.logger.error("Child task %s terminated with exception: %s" % (
                    task.tag, str(value)))
                raise value

        # Return value of last child to complete
        return value
            

    def child_done(self, result, task):
        with self._lock_c:
            self.count += 1
            self.logger.debug('Concurrent task %d/%d has completed' % (
                    self.count, self.numtasks))
            self.taskset.remove(task)
            self.totaltime += task.getExecutionTime()
            self.results[(self.count, task)] = result


    def stop(self):
        """Call stop() on all child tasks, and ignore TaskError exceptions.
        Behavior depends on what the child tasks' stop() method does."""
        with self._lock_c:
            for task in self.taskset:
                try:
                    task.stop()

                except TaskError as e:
                    # Task does not have a way to stop it.
                    # TODO: notify who?
                    pass
        
        # stop ourself
        #self.ev_intr.set()


    def addTask(self, task):
        """Add a task to the task set.
        """
        # Try to start task first.  If it fails then we don't need to
        # undo adding it to taskset
        task.initialize(self)
        task.start()

        with self._lock_c:
            self.numtasks += 1
            self.taskset.append(task)

    def getTask(self, i):
        with self._lock_c:
            return self.taskset[i]

    def getNumTasks(self):
        """Get the set of active tasks.
        """
        with self._lock_c:
            return len(self.taskset)

        
class ConcurrentAndTaskset(newConcurrentAndTaskset):
    pass

class QueueTaskset(Task):
    """Compound task that runs a set of tasks that it reads from a queue
    concurrently.  If _waitflag_ is True, then it will run each task to
    completion before starting the next task.
    """
    
    def __init__(self, queue, waitflag=True, timeout=0.1):

        super(QueueTaskset, self).__init__()

        self.queue = queue
        self.waitflag = waitflag
        self.lock = threading.RLock()
        self.timeout = timeout
        self.task = None
        self.ev_cancel = threading.Event()
        self.ev_pause = threading.Event()


    def flush(self):
        # Flush queue of pending tasks
        self.logger.debug("Flushing queue.")
        while True:
            try:
                self.queue.get(block=False)
            except Queue.Empty:
                break

            
    def stop(self):
        self.flush()
        #self.ev_intr.set()

        try:
            if self.task:
                self.task.stop()

        except TaskError as e:
            #self.logger.error("Error cancelling child task: %s" % (str(e)))
            pass

            
    def stop_child(self):
        self.flush()

        try:
            if self.task:
                self.task.stop()

        except TaskError as e:
            #self.logger.error("Error cancelling child task: %s" % (str(e)))
            pass

            
    def execute(self):
        self.count = 0
        self.totaltime = 0
        self.logger.debug("Queue Taskset starting")
        while True:
            try:
                self.check_state()

                task = self.queue.get(block=True, timeout=self.timeout)
                self.task = task

                task.register_callback(self.child_done, args=[task])

                with self.lock:
                    self.count += 1

                self.ev_cancel.clear()
                try:
                    task.initialize(self)

                    self.logger.debug("Starting task '%s'" % str(task))
                    task.start()

                    if self.waitflag:
                        res = task.wait()

                        self.logger.debug("Task %s terminated with result %s" % (
                                          (str(task), str(res))))
                except Exception as e:
                    self.logger.error("Task '%s' terminated with exception: %s" % \
                                      (str(task), str(e)))
                    try:
                        (type, value, tb) = sys.exc_info()
                        self.logger.debug("Traceback:\n%s" % \
                                          "".join(traceback.format_tb(tb)))

                        # NOTE: to avoid creating a cycle that might cause
                        # problems for GC--see Python library doc for sys
                        # module
                        tb = None

                    except Exception as e:
                        self.logger.debug("Traceback information unavailable.")

                    # If task raised exception then it didn't call done,
                    task.done(e, noraise=True)

            except Queue.Empty:
                # No task available.  Continue trying to get one.
                continue


        # TODO: should we wait for self.count > 0?
        self.logger.debug("Queue Taskset terminating")
        
        return self.result
            

    def child_done(self, result, task):
        with self.lock:
            self.count -= 1
            self.totaltime += task.getExecutionTime()
            self.result = result


    def cancel(self):
        self.flush()

        super(QueueTaskset, self).cancel()

            
    def addTask(self, task):
        self.queue.put(task)
            
# ------------ PRIORITY QUEUES ------------

class PriorityQueue(Queue.PriorityQueue):
    pass
        

# ------------ WORKER THREADS ------------

class _WorkerReset(Exception):
    """Local exception used to reset a worker thread."""
    pass

class WorkerThread(object):
    """Container for a thread in which to call the execute() method of a task.
    A WorkerThread object waits on the task queue, executes a task when it
    appears, and repeats.  A call to start() is necessary to start servicing
    the queue, and a call to stop() will terminate the service.
    """

    def __init__(self, queue, logger=None, ev_quit=None,
                 timeout=0.2, tpool=None):

        self.queue = queue
        self.logger = logger
        self.timeout = timeout
        if ev_quit:
            self.ev_quit = ev_quit
        else:
            self.ev_quit = threading.Event()
        self.tpool = tpool
        self.lock = threading.RLock()
        self.status = 'stopped'
        self.time_start = 0.0


    def setstatus(self, status):
        """Sets our status field so that others can inquire what we are doing.
        Set of status:
          starting, idle
        """
        with self.lock:
            self.status = status
        

    def getstatus(self):
        """Returns our status--a string describing what we are doing.
        """
        with self.lock:
            return (self.status, self.time_start)
        

    def execute(self, task):
        """Execute a task. 
        """

        taskid = str(task)
        res = None
        try:
            # Try to run the task.  If we catch an exception, then
            # it becomes the result.
            self.time_start = time.time()
            self.setstatus('executing %s' % taskid)

            self.logger.debug("now executing task '%s'" % taskid)
            try:
                res = task.execute()

            except UserTaskException as e:
                res = e
                
            except Exception as e:
                self.logger.error("Task '%s' raised exception: %s" % \
                                  (str(task), str(e)))
                res = e
                try:
                    (type, value, tb) = sys.exc_info()
                    self.logger.debug("Traceback:\n%s" % \
                                      "".join(traceback.format_tb(tb)))

                    # NOTE: to avoid creating a cycle that might cause
                    # problems for GC--see Python library doc for sys
                    # module
                    tb = None

                except Exception as e:
                    self.logger.debug("Traceback information unavailable.")

        finally:
            self.logger.debug("done executing task '%s'" % str(task))

            self.setstatus('cleaning %s' % taskid)
            # Wake up waiters on other threads
            task.done(res, noraise=True)

            self.time_start = 0.0
            self.setstatus('idle')

        
    # Basic task execution loop.  Dequeue a task and run it, then look
    # for another one
    def taskloop(self):
        self.setstatus('starting')
        self.logger.debug('Starting worker thread loop.')

        # If we were handed a thread pool upon startup, then register
        # ourselves with it.
        if self.tpool:
            self.tpool.register_up()

        try:
            self.setstatus('idle')
            while not self.ev_quit.isSet():
                try:
                    
                    # Wait on our queue for a task; will timeout in
                    # self.timeout secs
                    (priority, task) = self.queue.get(block=True,
                                                      timeout=self.timeout)

                    self.execute(task)
                    
                except _WorkerReset:
                    self.logger.info("Worker reset!")
                
                except Queue.Empty as e:
                    # Reach here when we time out waiting for a task
                    pass

        finally:
            self.logger.debug('Stopping worker thread loop.')

            if self.tpool:
                self.tpool.register_dn()

            self.setstatus('stopped')

            
    def start(self):
        self.thread = threading.Thread(target=self.taskloop, args=[])
        self.thread.start()
        
    def stop(self):
        self.ev_quit.set()
        
# ------------ THREAD POOL ------------

class ThreadPool(object):
    """A simple thread pool for executing tasks asynchronously.

    self.status states:
        down    no threads are ready for service
        up      all threads are ready for service
        start   threads are starting, but not all of them are up yet
        stop    threads are stopping, but not all of them are down yet
    """

    def __init__(self, numthreads=1, logger=None, ev_quit=None,
                 workerClass=WorkerThread):

        self.numthreads = numthreads
        self.logger = logger
        if ev_quit:
            self.ev_quit = ev_quit
        else:
            self.ev_quit = threading.Event()
        self.lock = threading.RLock()
        self.workerClass = workerClass

        self.queue = PriorityQueue()
        self.workers = []
        self.tids = []

        # Used to synchronize thread pool startup (see register() method)
        self.regcond = threading.Condition()
        self.runningcount = 0
        self.status = 'down'


    def startall(self, wait=False, **kwdargs):
        """Start all of the threads in the thread pool.  If _wait_ is True
        then don't return until all threads are up and running.  Any extra
        keyword arguments are passed to the worker thread constructor.
        """
        self.logger.debug("startall called")
        with self.regcond:
            while self.status != 'down':
                if self.status in ('start', 'up') or self.ev_quit.isSet():
                    # For now, abandon additional request to start
                    self.logger.error("ignoring duplicate request to start thread pool")
                    return

                self.logger.debug("waiting for threads: count=%d" % \
                                  self.runningcount)
                self.regcond.wait()

            #assert(self.status == 'down')
            if self.ev_quit.isSet():
                return
            
            self.runningcount = 0
            self.status = 'start'
            self.workers = []
            if wait:
                tpool = self
            else:
                tpool = None

            # Start all worker threads
            self.logger.debug("starting threads in thread pool")
            for i in range(self.numthreads):
                t = self.workerClass(self.queue, logger=self.logger,
                                     ev_quit=self.ev_quit, tpool=tpool,
                                     **kwdargs)
                self.workers.append(t)
                t.start()

            if wait:
                # Threads are on the way up.  Wait until last one starts.
                while self.status != 'up' and not self.ev_quit.isSet():
                    self.logger.debug("waiting for threads: count=%d" % \
                                      self.runningcount)
                    self.regcond.wait()

            self.logger.debug("startall done")


    def addThreads(self, numthreads, **kwdargs):
        with self.regcond:
            # Start all worker threads
            self.logger.debug("adding %d threads to thread pool" % (
                numthreads))
            for i in range(numthreads):
                t = self.workerClass(self.queue, logger=self.logger,
                                     ev_quit=self.ev_quit, tpool=self.tpool,
                                     **kwdargs)
                self.workers.append(t)
                t.start()

            self.numthreads += numthreads

    def stopall(self, wait=False):
        """Stop all threads in the worker pool.  If _wait_ is True
        then don't return until all threads are down.
        """
        self.logger.debug("stopall called")
        with self.regcond:
            while self.status != 'up':
                if self.status in ('stop', 'down') or self.ev_quit.isSet():
                    # For now, silently abandon additional request to stop
                    self.logger.warn("ignoring duplicate request to stop thread pool.")
                    return
                
                self.logger.debug("waiting for threads: count=%d" % \
                                  self.runningcount)
                self.regcond.wait()

            #assert(self.status == 'up')
            self.logger.debug("stopping threads in thread pool")
            self.status = 'stop'
            # Signal to all threads to terminate.
            self.ev_quit.set()

            if wait:
                # Threads are on the way down.  Wait until last one quits.
                while self.status != 'down':
                    self.logger.debug("waiting for threads: count=%d" % \
                                      self.runningcount)
                    self.regcond.wait()

            self.logger.debug("stopall done")


    def workerStatus(self):
        return list(map(lambda t: t.getstatus(), self.workers))


    def addTask(self, task, priority=0):
        """Add a task to the queue of tasks.

        The task will be executed in a worker thread as soon as one is available.
        Tasks are executed in first-come-first-served order.
        """
        self.queue.put((priority, task))


    def delTask(self, taskid):
        self.logger.error("delTask not yet implemented")


    def purgeTasks(self):
        self.logger.error("purgeTasks not yet implemented")


    def register_up(self):
        """Called by WorkerThread objects to register themselves.

        Acquire the condition variable for the WorkerThread objects.
        Increment the running-thread count.  If we are the last thread to
        start, set status to 'up'.  This allows startall() to complete
        if it was called with wait=True.
        """
        with self.regcond:
            self.runningcount += 1
            tid = thread.get_ident()
            self.tids.append(tid)
            self.logger.debug("register_up: (%d) count is %d" % \
                              (tid, self.runningcount))
            if self.runningcount == self.numthreads:
                self.status = 'up'
            self.regcond.notify()


    def register_dn(self):
        """Called by WorkerThread objects to register themselves.

        Acquire the condition variable for the WorkerThread objects.
        Decrement the running-thread count.  If we are the last thread to
        start, release the ThreadPool thread, which is stuck in start()
        """
        with self.regcond:
            self.runningcount -= 1
            tid = thread.get_ident()
            self.tids.remove(tid)
            self.logger.debug("register_dn: count_dn is %d" % self.runningcount)
            self.logger.debug("register_dn: remaining: %s" % str(self.tids))
            if self.runningcount == 0:
                self.status = 'down'
            self.regcond.notify()

 
# ------------ SUPPORT FUNCTIONS ------------

_lock_seqnum = threading.Lock()
_count_seqnum = 0

def get_tag(taskParent):
    global _count_seqnum
    with _lock_seqnum:
        generic_id = 'task%d' % (_count_seqnum)
        _count_seqnum += 1
        
    if taskParent:
        tag = str(taskParent) + '.' + generic_id
    else:
        tag = generic_id
    
    return tag
    

#END
