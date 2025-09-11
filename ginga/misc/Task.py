#
# Task.py -- Basic command pattern and thread pool implementation.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import sys
import time
import threading

import queue as Queue

# NOTE: See http://bugs.python.org/issue7946
# we cannot effectively use threading for loading files/network/etc.
# without setting the switchinterval down on python 3 due to the new
# GIL implementation
_swival = 0.000001
sys.setswitchinterval(_swival)

from . import Callback  # noqa


class TaskError(Exception):
    """Exception generated for task errors"""
    pass


class TaskTimeout(TaskError):
    """Exception generated when timing out waiting on a task"""
    pass


class UserTaskException(Exception):
    pass


# ------------ BASIC TASKS ------------

class Task(Callback.Callbacks):
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

        self.enable_callback('resolved')

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
                    self.__dict__[var] = taskParent.__dict__[var]

        else:
            #raise TaskError("Cannot initialize task without a taskParent!")
            pass

        # Generate our own unique tag.  'tagger' should have been transmitted
        # from the parent task
        if not self.tag:
            try:
                self.tag = str(taskParent) + '.' + self.tagger.get_tag(self)
            except Exception:
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
        if self.threadPool is not None:
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

        if not self.ev_done.is_set():
            raise TaskTimeout("Task %s timed out." % self)

        # --> self.result is set
        # If it is an exception, then raise it in this waiter
        if isinstance(self.result, Exception):
            raise self.result

        # Release waiters and perform callbacks
        # done() has already been called, because of self.ev_done check
        # "asynchronous" tasks should could call done() here
        #self.done(self.result)

        return self.result

    def step(self):
        """If a task has a way of stepping through an operation.  It can
        implement this method.  Subclass should not call super.step().
        """
        raise TaskError("Task %s: subclass should override step() method!" %
                        self)

    def execute(self):
        """This method does the work of a task (if executed by the
        thread pool) and returns when it is finished.  *** Subclass should
        override this method! ***  It should take no arguments, and can
        return anything.
        """
        raise TaskError("Task %s: subclass should override execute() method!" %
                        self)

    def done(self, result, noraise=False):
        """This method is called when a task has finished executing.
        Subclass can override this method if desired, but should call
        superclass method at the end.
        """
        # [??] Should this be in a critical section?

        # Has done() already been called on this task?
        if self.ev_done.is_set():
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
        self.make_callback('resolved', self.result)

        # If the result is an exception, then our final act is to raise
        # it in the caller, unless the caller explicitly supressed that
        if isinstance(result, Exception) and (not noraise):
            raise result

        return result

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
                self.logger.error("Task '%s' terminated with exception: %s" %
                                  (str(self), str(e)), exc_info=True)
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
            self.logger.debug('SeqSet task %i has completed with result %s' %
                              (self.index, res))

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


class ConcurrentAndTaskset(Task):
    """Compound task that runs a set of tasks concurrently, and does not
    return until they all terminate.
    """

    def __init__(self, taskseq):

        super(ConcurrentAndTaskset, self).__init__()

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
                    #self.logger.warning("Subtask propagated exception: %s" % str(e))
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


class QueueTaskset(Task):
    """Compound task that runs a set of tasks that it reads from a queue
    concurrently.  If _waitflag_ is True, then it will run each task to
    completion before starting the next task.
    """

    def __init__(self, queue, waitflag=True, timeout=0.1, ev_quit=None):

        super(QueueTaskset, self).__init__()

        self.queue = queue
        self.waitflag = waitflag
        self.lock = threading.RLock()
        self.timeout = timeout
        self.task = None
        self.ev_cancel = threading.Event()
        self.ev_pause = threading.Event()
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit

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

        # put termination sentinel
        self.queue.put(None)

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
        while not self.ev_quit.is_set():
            try:
                self.check_state()

                task = self.queue.get(block=True, timeout=self.timeout)
                if task is None:
                    # termination sentinel
                    break

                self.task = task

                task.add_callback('resolved', self.child_done)

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
                    self.logger.error("Task '%s' terminated with exception: %s" %
                                      (str(task), str(e)), exc_info=True)

                    # If task raised exception then it didn't call done,
                    task.done(e, noraise=True)

            except Queue.Empty:
                # No task available.  Continue trying to get one.
                continue

        # TODO: should we wait for self.count > 0?
        self.logger.debug("Queue Taskset terminating")

        return self.result

    def child_done(self, task, result):
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
        # global termination flag
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        # local termination flag
        self.my_quit = threading.Event()
        self.tpool = tpool
        self.lock = threading.RLock()
        self.thread = None
        self.status = 'stopped'
        self.time_idle = None
        self.tid = None

    def setstatus(self, status):
        """Sets our status field so that others can inquire what we are doing.
        Set of status:
          starting, idle
        """
        with self.lock:
            self.status = status
            if status == 'idle':
                self.time_idle = time.time()
            else:
                self.time_idle = None

    def getstatus(self):
        """Returns our status--a string describing what we are doing.
        """
        with self.lock:
            return (self.status, self.time_idle)

    def execute(self, task):
        """Execute a task.
        """

        taskid = str(task)
        res = None
        try:
            # Try to run the task.  If we catch an exception, then
            # it becomes the result.
            self.setstatus('executing %s' % taskid)

            self.logger.debug("now executing task '%s'" % taskid)
            try:
                res = task.execute()

            except UserTaskException as e:
                res = e

            except Exception as e:
                self.logger.error("Task '%s' raised exception: %s" %
                                  (str(task), str(e)), exc_info=True)
                res = e

        finally:
            self.logger.debug("done executing task '%s'" % str(task))

            self.setstatus('cleaning %s' % taskid)
            # Wake up waiters on other threads
            task.done(res, noraise=True)

            self.setstatus('idle')

    # Basic task execution loop.  Dequeue a task and run it, then look
    # for another one
    def taskloop(self, ev_start):
        self.tid = threading.get_ident()
        self.setstatus('starting')
        self.logger.debug(f"thread {self.tid} starting worker thread loop.")

        # If we were handed a thread pool upon startup, then register
        # ourselves with it.
        if self.tpool is not None:
            self.tpool.register_up(self)

        try:
            self.setstatus('idle')
            if ev_start is not None:
                ev_start.set()
            while not self.ev_quit.is_set() and not self.my_quit.is_set():
                try:
                    # Wait on our queue for a task; will timeout in
                    # self.timeout secs
                    (priority, task) = self.queue.get(block=True,
                                                      timeout=self.timeout)
                    if task is None:
                        # termination sentinel
                        self.queue.put((priority, task))
                        break

                    self.execute(task)

                except Queue.Empty as e:
                    # Reach here when we time out waiting for a task
                    if self.tpool is not None and self.time_idle is not None:
                        idle_sec = time.time() - self.time_idle
                        if (self.tpool.idle_limit_sec is not None and
                            idle_sec > self.tpool.idle_limit_sec):
                            self.tpool.offer_to_quit(self)

        finally:
            if self.tpool is not None:
                self.tpool.register_dn(self)

            self.setstatus('stopped')

        self.logger.debug(f"thread {self.tid} exiting.")

    def start(self, wait=False):
        if self.thread is not None:
            raise RuntimeError("A worker thread is already running")
        self.my_quit.clear()
        ev_start = None
        if wait:
            ev_start = threading.Event()
        self.thread = threading.Thread(target=self.taskloop, args=[ev_start])
        self.thread.start()

        if wait:
            ev_start.wait()

    def stop(self):
        self.my_quit.set()

    def cleanup(self):
        if self.thread is not None:
            alive = self.thread.is_alive()
            if not alive:
                self.thread.join()
            self.thread = None


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
                 minthreads=None, idle_limit_sec=10.0,
                 workerClass=WorkerThread, analyze_interval=None):

        self.numthreads = max(1, numthreads)
        self.logger = logger
        if ev_quit is None:
            ev_quit = threading.Event()
        self.ev_quit = ev_quit
        self.lock = threading.RLock()
        self.workerClass = workerClass
        if minthreads is None:
            minthreads = numthreads
        self.minthreads = max(0, minthreads)
        self.idle_limit_sec = idle_limit_sec
        self.mon_thread = None
        self._analyze_time = 0.0
        self.analyze_interval = analyze_interval

        self.queue = PriorityQueue()

        # Used to synchronize thread pool startup (see register() method)
        self.regcond = threading.Condition()
        self.mp_cond = threading.Condition()
        self.status = 'down'
        self.waiting = [self.workerClass(self.queue, logger=self.logger,
                                         ev_quit=self.ev_quit, tpool=self)
                        for i in range(self.numthreads)]
        self.running = []
        self.cleanup = []

    def startall(self, wait=False, **kwargs):
        """Start all of the threads in the thread pool.  If _wait_ is True
        then don't return until all threads are up and running.  Any extra
        keyword arguments are passed to the worker thread constructor.
        """
        if self.mon_thread is not None:
            self.logger.error("ignoring duplicate request to start thread pool")
            return

        self.logger.debug("startall called, starting pool attendant thread")
        self.status = 'start'
        self.mon_thread = threading.Thread(target=self.pool_attendant, args=[])
        self.mon_thread.start()

        # if started with wait=True, then expect that threads will register
        # themselves and last one up will set status to "up"
        if wait:
            with self.regcond:
                # Threads are on the way up.  Wait until last one starts.
                while self.status != 'up' and not self.ev_quit.is_set():
                    self.logger.debug("waiting for threads: count=%d" %
                                      len(self.running))
                    self.regcond.wait()
        self.logger.debug("startall done")

    def stopall(self, wait=False):
        """Stop all threads in the worker pool.  If _wait_ is True
        then don't return until all threads are down.
        """
        self.logger.debug("stopall called")
        with self.lock:
            self.status = 'stop'
        # Signal to all threads to terminate.
        self.ev_quit.set()

        if wait:
            with self.regcond:
                # Threads are on the way down.  Wait until last one quits.
                while self.status != 'down':
                    self.logger.debug("waiting for threads: count=%d" %
                                      len(self.running))
                    self.regcond.wait()

        self.mon_thread.join()
        self.mon_thread = None
        self.logger.debug("stopall done")

    def add_threads(self, add_numthreads, minthreads=None):
        with self.regcond:
            self.waiting.extend([self.workerClass(self.queue,
                                                  logger=self.logger,
                                                  ev_quit=self.ev_quit,
                                                  tpool=self)
                                 for i in range(add_numthreads)])
            self.numthreads += add_numthreads
            if minthreads is not None:
                self.minthreads = max(0, minthreads)

    def workerStatus(self):
        with self.regcond:
            return list(map(lambda t: t.getstatus(), self.running))

    def addTask(self, task, priority=0):
        """Add a task to the queue of tasks.

        The task will be executed in a worker thread as soon as one is available.
        Tasks are executed in first-come-first-served order.
        """
        self.queue.put((priority, task))
        with self.mp_cond:
            # wake up pool attendant thread to check on things
            self.mp_cond.notify()

    def pool_attendant(self):
        """Monitor the thread pool as the "pool attendant".

        A thread is started in this method to monitor the thread pool and
        clean up or activate new threads as needed.
        """
        self.logger.debug("starting the thread pool attendant loop...")
        while not self.ev_quit.is_set():
            if self.analyze_interval is not None:
                cur_time = time.time()
                if cur_time - self._analyze_time > self.analyze_interval:
                    self._analyze_time = cur_time
                    self.analyze_threads()

            worker = None
            with self.regcond:
                # join threads that have exited
                while len(self.cleanup) > 0:
                    dead_worker = self.cleanup.pop()
                    dead_worker.cleanup()

                num_running = len(self.running)
                if (num_running < self.minthreads or
                    self.queue.qsize() > 0 and num_running < self.numthreads):
                    assert (len(self.waiting) > 0)
                    worker = self.waiting[0]

            if worker is not None:
                worker.start(wait=True)
            else:
                with self.mp_cond:
                    self.mp_cond.wait(timeout=0.25)

        self.logger.debug("stopping the thread pool attendant loop...")

    def analyze_threads(self):
        self.logger.info("--- analyzing active threads...")
        count = 0
        for thread in threading.enumerate():
            count += 1
            if thread.ident is None:
                # Exclude threads that haven't started yet
                self.logger.info(f"{count:3d}: thread named {thread.name} is initializing...")
                continue

            self.logger.info(f"{count:3d}: thread name: {thread.name}, thread id: {thread.ident}")
            try:
                # Get the top-level stack frame for the thread
                frame = sys._current_frames().get(thread.ident)
                if frame:
                    # Iterate through the stack frames to find the current function
                    while frame:
                        function_name = frame.f_code.co_name
                        self.logger.info(f"currently in function: {function_name}")
                        frame = frame.f_back   # Move to the calling frame
                        if function_name != '<module>':
                            # Stop if we're not in the global scope
                            break
                else:
                    self.logger.warning("could not retrieve stack frame for this thread (might be idle or finished).")
            except Exception as e:
                self.logger.error(f"error inspecting thread {thread.name}: {e}")
        self.logger.info("--- done analyzing")

    def delTask(self, taskid):
        self.logger.error("delTask not yet implemented")

    def purgeTasks(self):
        self.logger.error("purgeTasks not yet implemented")

    def offer_to_quit(self, worker):
        """Called by WorkerThread objects when they have been idle
        for a certain period.
        """
        with self.regcond:
            if len(self.running) <= self.minthreads or self.queue.qsize() > 0:
                return

            worker.stop()

    def register_up(self, worker):
        """Called by WorkerThread objects to register themselves.

        Acquire the condition variable for the WorkerThread objects.
        Increment the running-thread count.  If we are the last thread to
        start, set status to 'up'.  This allows startall() to complete
        if it was called with wait=True.
        """
        with self.regcond:
            self.waiting.remove(worker)
            self.running.append(worker)
            num_running = len(self.running)
            self.logger.debug("register_up: (%d) count is %d" % (
                worker.tid, num_running))
            if num_running == self.minthreads:
                self.status = 'up'
                self.regcond.notify()

    def register_dn(self, worker):
        """Called by WorkerThread objects to de-register themselves.

        Acquire the condition variable for the WorkerThread objects.
        Decrement the running-thread count.  If we are the last thread to
        start, release the ThreadPool thread, which is stuck in start()
        """
        with self.regcond:
            self.running.remove(worker)
            self.waiting.append(worker)
            self.cleanup.append(worker)
            num_running = len(self.running)
            self.logger.debug("register_dn: (%d) count is %d" % (
                worker.tid, num_running))
            with self.mp_cond:
                # wake up pool attendant to clean up thread
                self.mp_cond.notify()
            if num_running == 0:
                self.status = 'down'
                self.regcond.notify()

    # TO BE DEPRECATED
    addThreads = add_threads


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


# END
