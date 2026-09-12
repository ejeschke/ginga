#
# test_threadpool.py -- a pool that grows with demand and shrinks when idle
#
"""The pool starts at ``minthreads`` and grows towards ``numthreads`` as work
arrives faster than idle workers can take it, then retires workers that have
had nothing to do.  Neither decision needs a thread of its own watching the
pool: growth happens on the thread that submitted the work and found nobody
idle, retirement on the worker that has been idle too long.

Most of what is pinned here is that accounting.  Two of these tests exist
because the accounting was wrong in ways that looked like slowness rather
than breakage.
"""

import logging
import threading
import time

import pytest

from ginga.misc import Task


@pytest.fixture
def logger():
    log = logging.getLogger('threadpool-test')
    log.addHandler(logging.NullHandler())
    log.setLevel(logging.CRITICAL)
    return log


@pytest.fixture
def pool(logger):
    made = []

    def _make(**kwargs):
        kwargs.setdefault('logger', logger)
        kwargs.setdefault('idle_limit_sec', 60.0)
        p = Task.ThreadPool(**kwargs)
        p.startall(wait=True)
        made.append(p)
        return p

    yield _make
    for p in made:
        try:
            p.stopall(wait=True)
        except Exception:
            pass


def occupy(p, count, release):
    """Submit `count` tasks that each block until `release` is set."""
    started = threading.Semaphore(0)

    def work():
        started.release()
        release.wait(20)

    for _ in range(count):
        p.addTask(Task.FuncTask2(work))
    return started


def wait_for(predicate, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


# ------------------------------------------------------------- growth --

def test_it_grows_to_meet_a_burst(pool):
    """The reason the pool expands at all.

    Regression: a worker started *because* work was queued also announced
    itself as idle, so the next submission consumed the permit that its own
    growth had just created.  The pool then grew at half the rate work
    arrived -- 34 workers for 64 simultaneous tasks -- which looks like the
    machine being slow rather than like a bug.
    """
    p = pool(numthreads=64, minthreads=4)
    assert wait_for(lambda: len(p.running) == 4), 'starts at minthreads'

    release = threading.Event()
    try:
        occupy(p, 64, release)
        assert wait_for(lambda: len(p.running) == 64), (
            'grew to %d of 64' % (len(p.running),))
    finally:
        release.set()


def test_it_grows_no_further_than_numthreads(pool):
    p = pool(numthreads=16, minthreads=4)
    release = threading.Event()
    try:
        occupy(p, 64, release)
        assert wait_for(lambda: len(p.running) == 16)
        time.sleep(0.5)
        assert len(p.running) == 16
    finally:
        release.set()


def test_a_floor_above_the_ceiling_is_brought_down_to_it(pool):
    """Regression, and a startup hang rather than a wrong number.

    startall(wait=True) waits for minthreads workers to register, and the
    pool will not start more than numthreads -- so a floor above the ceiling
    waited for workers that could never arrive, and waited for good.  A
    service handed --minthreads greater than --numthreads simply never came
    up, and said nothing about why.
    """
    p = pool(numthreads=6, minthreads=30)

    assert p.minthreads == 6
    assert len(p.running) == 6

    done = threading.Event()
    p.addTask(Task.FuncTask2(done.set))
    assert done.wait(10), 'and it serves'


def test_a_fixed_pool_stays_fixed(pool):
    """minthreads defaulting to numthreads is what every existing caller
    gets, and it must behave exactly as it always did."""
    p = pool(numthreads=8)
    assert p.minthreads == 8

    release = threading.Event()
    try:
        occupy(p, 32, release)
        time.sleep(0.5)
        assert len(p.running) == 8
    finally:
        release.set()


def test_an_idle_pool_does_not_grow(pool):
    """A submission that an idle worker will take must not start a thread."""
    p = pool(numthreads=16, minthreads=4)
    done = threading.Event()
    p.addTask(Task.FuncTask2(done.set))

    assert done.wait(10)
    time.sleep(0.3)
    assert len(p.running) == 4


# --------------------------------------------------------- contraction --

def test_it_retires_workers_when_the_work_stops(pool):
    p = pool(numthreads=32, minthreads=4, idle_limit_sec=0.5)
    release = threading.Event()
    occupy(p, 32, release)
    assert wait_for(lambda: len(p.running) > 4)
    peak = len(p.running)
    release.set()

    assert wait_for(lambda: len(p.running) == 4, timeout=25.0), (
        'went from %d down to %d, not 4' % (peak, len(p.running)))


def test_it_never_retires_below_minthreads(pool):
    p = pool(numthreads=16, minthreads=6, idle_limit_sec=0.5)
    assert wait_for(lambda: len(p.running) == 6)

    time.sleep(2.5)
    assert len(p.running) == 6


def test_a_retired_worker_can_be_put_back_to_work(pool):
    """A worker is not offered again until its old thread has been joined.

    Handing it back while it was still finishing raised RuntimeError from
    start(), which the pool swallowed -- so the growth simply did not
    happen.
    """
    p = pool(numthreads=16, minthreads=2, idle_limit_sec=0.5)
    release = threading.Event()
    occupy(p, 16, release)
    assert wait_for(lambda: len(p.running) == 16)
    release.set()
    assert wait_for(lambda: len(p.running) == 2, timeout=25.0)

    second = threading.Event()
    try:
        occupy(p, 16, second)
        assert wait_for(lambda: len(p.running) == 16), (
            'only got back to %d' % (len(p.running),))
    finally:
        second.set()


# ------------------------------------------------------------ priority --

def test_priority_is_off_by_default(pool):
    """Nearly every caller submits everything at one priority, and an
    ordered queue costs more than a plain one."""
    p = pool(numthreads=1)
    assert not p.priority

    order = []
    gate = threading.Event()
    p.addTask(Task.FuncTask2(lambda: gate.wait(10)))
    time.sleep(0.2)
    for name in ('a', 'b', 'c'):
        p.addTask(Task.FuncTask2(lambda n=name: order.append(n)), priority=9)
    gate.set()

    assert wait_for(lambda: len(order) == 3)
    assert order == ['a', 'b', 'c'], 'first come, first served'


def test_priority_orders_the_queue_when_asked_for(pool):
    p = pool(numthreads=1, minthreads=1, priority=True)
    order = []
    gate = threading.Event()
    p.addTask(Task.FuncTask2(lambda: gate.wait(10)))
    time.sleep(0.2)
    for pri, name in ((5, 'low'), (1, 'high'), (5, 'low2')):
        p.addTask(Task.FuncTask2(lambda n=name: order.append(n)),
                  priority=pri)
    gate.set()

    assert wait_for(lambda: len(order) == 3)
    assert order == ['high', 'low', 'low2']


def test_equal_priorities_are_ordered_by_arrival_not_compared(pool):
    """Regression.  The queue held (priority, task), so two equal priorities
    sent Python on to compare the tasks -- which do not compare -- and the
    submission raised TypeError inside the queue."""
    p = pool(numthreads=1, minthreads=1, priority=True)
    seen = []
    gate = threading.Event()
    p.addTask(Task.FuncTask2(lambda: gate.wait(10)))
    time.sleep(0.2)
    for i in range(5):
        p.addTask(Task.FuncTask2(lambda n=i: seen.append(n)), priority=3)
    gate.set()

    assert wait_for(lambda: len(seen) == 5)
    assert seen == [0, 1, 2, 3, 4]


# ----------------------------------------------------------- lifecycle --

def test_the_work_actually_runs(pool):
    p = pool(numthreads=4)
    results = []
    for i in range(20):
        p.addTask(Task.FuncTask2(lambda n=i: results.append(n)))

    assert wait_for(lambda: len(results) == 20)
    assert sorted(results) == list(range(20))


def test_stopall_brings_every_worker_down(logger):
    p = Task.ThreadPool(numthreads=8, logger=logger)
    p.startall(wait=True)
    assert len(p.running) == 8

    p.stopall(wait=True)
    assert p.running == []
    assert p.status == 'down'


def test_a_pool_can_be_started_again_after_being_stopped(logger):
    p = Task.ThreadPool(numthreads=4, logger=logger)
    p.startall(wait=True)
    p.stopall(wait=True)

    p.startall(wait=True)
    try:
        done = threading.Event()
        p.addTask(Task.FuncTask2(done.set))
        assert done.wait(10)
    finally:
        p.stopall(wait=True)


def test_add_threads_raises_the_ceiling(pool):
    p = pool(numthreads=4, minthreads=2)
    p.add_threads(8)
    assert p.numthreads == 12

    release = threading.Event()
    try:
        occupy(p, 12, release)
        assert wait_for(lambda: len(p.running) == 12)
    finally:
        release.set()


def test_worker_status_reports_the_running_workers(pool):
    p = pool(numthreads=4)
    status = p.workerStatus()

    assert len(status) == 4
    assert all(isinstance(entry, tuple) for entry in status)


class Recording:
    """A logger that keeps the reports it is given."""

    def __init__(self):
        self.reports = []

    def info(self, msg, *args, **kwargs):
        self.reports.append(msg % args if args else msg)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


def test_periodic_analysis_costs_a_thread_only_when_asked_for():
    """It used to ride on the pool-monitoring thread, which every pool kept
    whether anyone wanted reports or not."""
    quiet = Task.ThreadPool(numthreads=2, logger=Recording())
    quiet.startall(wait=True)
    try:
        assert quiet._analyze_thread is None
    finally:
        quiet.stopall(wait=True)


def test_periodic_analysis_still_reports_when_it_is_asked_for():
    log = Recording()
    p = Task.ThreadPool(numthreads=2, logger=log, analyze_interval=0.3)
    p.startall(wait=True)
    try:
        assert p._analyze_thread is not None
        assert wait_for(
            lambda: sum(1 for r in log.reports
                        if 'analyzing active threads' in r) >= 2,
            timeout=10.0)
    finally:
        p.stopall(wait=True)

    assert p._analyze_thread is None, 'stopall takes it with the pool'


def test_there_is_no_pool_monitoring_thread(pool):
    """Growth happens on the submitting thread and retirement on the worker,
    so nothing watches the pool."""
    p = pool(numthreads=4)

    assert not hasattr(p, 'mon_thread') or p.mon_thread is None
    assert not hasattr(p, 'pool_attendant')
