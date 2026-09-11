#
# log.py -- logging routines for Ginga
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import itertools
import os
import logging
import logging.handlers
import threading
import queue
import time

LOG_FORMAT = '%(asctime)s | %(levelname)1.1s | %(filename)s:%(lineno)d (%(funcName)s) | %(message)s'

# max size of log file before rotating
log_maxsize = 20 * 1024 * 1024
log_backups = 4


class BatchingQueueListener:
    """Drain a logging queue on a background thread, delivering records to a
    handler in *batches* rather than one at a time.

    A batch is flushed when either ``max_records`` records have piled up or
    ``interval`` seconds have elapsed since the first record in the current
    batch -- whichever comes first.  This collapses many GUI / web-socket log
    writes into a single one, which matters when the GUI handler's sink is
    expensive (e.g. a websocket round-trip per line).

    The handler must implement ``handle_batch(records)``.  This is a
    thread-based listener (it owns its own daemon thread), so it is only
    suitable on backends that have threads -- i.e. not the in-situ/Pyodide
    case, which runs a single event loop.
    """

    _SENTINEL = object()

    def __init__(self, log_queue, handler, max_records=200, interval=0.25):
        self.queue = log_queue
        self.handler = handler
        self.max_records = max_records
        self.interval = interval
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run,
                                        name="ginga-gui-log", daemon=True)
        self._thread.start()

    def stop(self):
        # wake the thread if it is blocked in get(), then wait for it to drain
        self.queue.put(self._SENTINEL)
        t = self._thread
        if t is not None:
            t.join()
            self._thread = None

    def _run(self):
        batch = []
        deadline = None
        while True:
            timeout = (None if deadline is None
                       else max(0.0, deadline - time.monotonic()))
            try:
                rec = self.queue.get(timeout=timeout)
            except queue.Empty:
                rec = None
            if rec is self._SENTINEL:
                break
            if rec is not None:
                if not batch:
                    # first record of a new batch -- start the clock
                    deadline = time.monotonic() + self.interval
                batch.append(rec)
            if batch and (len(batch) >= self.max_records or
                          (deadline is not None and
                           time.monotonic() >= deadline)):
                self._deliver(batch)
                batch = []
                deadline = None
        # flush whatever is left on shutdown
        if batch:
            self._deliver(batch)

    def _deliver(self, records):
        try:
            self.handler.handle_batch(records)
        except Exception:
            # never let a logging failure kill the listener thread
            pass


#: What the hand-written NullLogger printed when given a file, kept so that
#: output looks the same as it did.
NULL_LOG_FORMAT = '| %(levelname)1.1s | %(message)s'


class NullLogger(logging.Logger):
    """A logger for code that has not been given one.

    Used in place of a real logger when logging should be suppressed, or to
    avoid the overhead of one.

    It is a real :py:class:`logging.Logger`, which is what makes it safe to
    put in place of one.  The stand-in it replaces accepted the level
    methods and little else, and what it did accept it did not always
    honour:

    * ``critical()`` could not be called at all -- its ``msg`` was declared
      keyword-only after ``*args``, so every call raised TypeError;
    * ``exception()``, ``log()``, ``isEnabledFor()`` and ``setLevel()`` were
      simply absent, so code written against the standard library got an
      AttributeError from the object meant to stand in for it;
    * ``error()`` accepted ``exc_info`` and ignored it;
    * arguments were accepted and dropped, so ``info("x %s", 1)`` logged the
      format string;
    * ``addHandler()`` did nothing, so a handler added to one was silently
      never used.

    Taking the arguments rather than a pre-formatted message is also what
    makes it cheap: a disabled logger never formats them, where a caller
    interpolating its own pays whether or not anything reads the result.

    :param name: As :py:class:`logging.Logger`.  One is invented when none
        is given, so that two throwaway loggers cannot share handlers.
    :param level: As :py:class:`logging.Logger`.  The default discards
        everything -- it is above CRITICAL, so no record is built at any
        level -- unless ``f_out`` says otherwise.
    :param f_out: Write records here instead of discarding them.
    """

    #: Names for the unnamed.  Deliberately not registered with the logging
    #: manager: these are throwaways, and a process that makes many should
    #: not accumulate them.
    _serial = itertools.count()

    def __init__(self, name=None, level=None, f_out=None):
        if name is None:
            name = 'ginga-null-%d' % (next(self._serial),)
        if level is None:
            # Nothing at all, unless somewhere was named to write it.
            level = (logging.DEBUG if f_out is not None
                     else logging.CRITICAL + 1)
        super().__init__(name, level)

        # This stands in for having no logger, not for a quiet route into
        # the root logger's handlers.
        self.propagate = False

        if f_out is None:
            self.addHandler(logging.NullHandler())
        else:
            handler = logging.StreamHandler(f_out)
            handler.setFormatter(logging.Formatter(NULL_LOG_FORMAT))
            self.addHandler(handler)

    def warn(self, msg, *args, **kwargs):
        """Kept because callers use it and Python 3.13 removed it."""
        return self.warning(msg, *args, **kwargs)


def get_logger(name='ginga', level=None, null=False,
               options=None, log_file=None, log_stderr=False):

    if null or ((options is not None) and hasattr(options, 'nulllogger') and
                options.nulllogger):
        # User wants a Null Logger
        return NullLogger()

    # Create a logger
    logger = logging.Logger('ginga')

    if level is None:
        if (options is not None) and (options.loglevel is not None):
            level = options.loglevel
        else:
            level = logging.WARN

    fmt = logging.Formatter(LOG_FORMAT)
    if (not log_file) and (options is not None) and (options.logfile is not None):
        log_file = options.logfile

    if log_file is not None:
        if ((options is not None) and (getattr(options, 'rmlog', False)) and
                os.path.exists(log_file)):
            os.remove(log_file)
        # TODO: get maxsize and backup from options, if present
        fileHdlr = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=log_maxsize, backupCount=log_backups)
        fileHdlr.setLevel(level)
        fileHdlr.setFormatter(fmt)
        logger.addHandler(fileHdlr)

    if (not log_stderr) and (options is not None) and (options.logstderr):
        log_stderr = options.logstderr

    if log_stderr:
        stderrHdlr = logging.StreamHandler()
        stderrHdlr.setLevel(level)
        stderrHdlr.setFormatter(fmt)
        logger.addHandler(stderrHdlr)

    if ((options is not None) and hasattr(options, 'pidfile') and
        options.pidfile is not None):
        # user specified a path to a pid file
        with open(options.pidfile, 'w') as pid_f:
            pid_f.write("{}\n".format(os.getpid()))

    return logger


def addlogopts(parser):
    if hasattr(parser, 'add_option'):
        # older OptParse
        add_argument = parser.add_option
    else:
        # newer ArgParse
        add_argument = parser.add_argument

    add_argument("--log", dest="logfile", metavar="FILE",
                 help="Write logging output to FILE")
    add_argument("--loglevel", dest="loglevel", metavar="LEVEL",
                 default=20, type=int,
                 help="Set logging level to LEVEL")
    add_argument("--lognull", dest="nulllogger", default=False,
                 action="store_true",
                 help="Use a null logger")
    add_argument("--logsize", dest="logsize", metavar="NUMBYTES",
                 type=int, default=log_maxsize,
                 help="Set maximum logging level to NUMBYTES")
    add_argument("--logbackups", dest="logbackups", metavar="NUM",
                 type=int, default=log_backups,
                 help="Set maximum number of backups to NUM")
    add_argument("--pidfile", dest="pidfile", metavar="FILE",
                 help="Write pid of process to FILE")
    add_argument("--rmlog", dest="rmlog", default=False,
                 action="store_true",
                 help="Remove log if present (don't append)")
    add_argument("--stderr", dest="logstderr", default=False,
                 action="store_true",
                 help="Copy logging also to stderr")
