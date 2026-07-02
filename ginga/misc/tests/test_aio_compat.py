"""Unit tests for the async task-pool support: aio_compat.AioCompletion,
awaitable Future/Task, AsyncTaskPool and AsyncFuncTask.

These avoid any pytest-asyncio dependency by driving an event loop with
``asyncio.run`` inside ordinary (synchronous) test functions.
"""
import asyncio
import logging

from .. import Task, Future
from ..aio_compat import AioCompletion

logger = logging.getLogger("test_aio_compat")
logger.addHandler(logging.NullHandler())


class _Parent:
    """Mimics GwMain's task-parent contract (supplies shared attrs)."""
    def __init__(self, pool):
        self.shares = ['threadPool', 'logger']
        self.threadPool = pool
        self.logger = logger


# -- AioCompletion ----------------------------------------------------------

def test_aiocompletion_await_then_resolve():
    aio = AioCompletion()

    async def main():
        async def resolver():
            await asyncio.sleep(0.01)
            aio.resolve(42)
        asyncio.ensure_future(resolver())
        return await aio

    assert asyncio.run(main()) == 42


def test_aiocompletion_resolve_then_await():
    aio = AioCompletion()
    # resolved before anyone awaits (and before any loop exists)
    aio.resolve("ready")

    async def main():
        return await aio

    assert asyncio.run(main()) == "ready"


# -- Future awaitable -------------------------------------------------------

def test_future_threaded_wait_still_works():
    f = Future.Future()
    f.freeze(lambda: 99)
    f.thaw()
    assert f.wait() == 99


def test_future_awaitable():
    async def main():
        f = Future.Future()

        async def resolver():
            await asyncio.sleep(0.01)
            f.resolve(7)
        asyncio.ensure_future(resolver())
        return await f

    assert asyncio.run(main()) == 7


# -- Task awaitable + AsyncTaskPool -----------------------------------------

def test_threaded_pool_back_compat():
    pool = Task.ThreadPool(numthreads=2, logger=logger)
    pool.startall(wait=True)
    try:
        parent = _Parent(pool)
        t = Task.FuncTask(lambda a, b: a + b, (2, 3), {}, logger=logger)
        t.init_and_start(parent)
        assert t.wait(timeout=5) == 5
    finally:
        pool.stopall(wait=True)


def test_threaded_taskpool_alias():
    assert Task.ThreadedTaskPool is Task.ThreadPool


def test_async_pool_sync_func():
    async def main():
        pool = Task.AsyncTaskPool(logger=logger)
        pool.startall()
        parent = _Parent(pool)
        t = Task.FuncTask(lambda x: x * 10, (4,), {}, logger=logger)
        t.init_and_start(parent)
        result = await t
        pool.stopall()
        return result

    assert asyncio.run(main()) == 40


def test_async_pool_coroutine_func():
    async def main():
        pool = Task.AsyncTaskPool(logger=logger)
        pool.startall()
        parent = _Parent(pool)

        async def slow_add(a, b):
            await asyncio.sleep(0.01)
            return a + b

        t = Task.AsyncFuncTask(slow_add, (5, 6), {}, logger=logger)
        t.init_and_start(parent)
        result = await t
        pool.stopall()
        return result

    assert asyncio.run(main()) == 11


def test_async_pool_exception_resolves_task():
    async def main():
        pool = Task.AsyncTaskPool(logger=logger)
        pool.startall()
        parent = _Parent(pool)

        def boom():
            raise ValueError("kaboom")

        t = Task.FuncTask(boom, (), {}, logger=logger)
        t.init_and_start(parent)
        result = await t
        pool.stopall()
        return result

    # FuncTask.execute catches the exception and resolves it as the result
    result = asyncio.run(main())
    assert isinstance(result, ValueError)
