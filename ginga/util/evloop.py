#
# evloop.py -- asyncio/tornado event loop utilities.
#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
import asyncio


def get_event_loop():
    """Get the current asyncio event loop."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop


def get_ioloop():
    """Get the current tornado ioloop."""
    from tornado.ioloop import IOLoop

    loop = get_event_loop()

    # now we should be able to get the current tornado IOLoop,
    # which as of Tornado > v5 is a wrapper around the asyncio
    # event loop
    return IOLoop.current()
