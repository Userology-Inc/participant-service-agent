import asyncio
import functools

from . import debug, duplex_unix, itertools
from .channel import Chan, ChanClosed, ChanReceiver, ChanSender
from .interval import Interval, interval
from .sleep import Sleep, SleepFinished, sleep
from .task_set import TaskSet


async def gracefully_cancel(*futures: asyncio.Future):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    waiters = []

    for fut in futures:
        waiter = loop.create_future()
        cb = functools.partial(_release_waiter, waiter)
        waiters.append((waiter, cb))
        fut.add_done_callback(cb)
        fut.cancel()

    try:
        for waiter, _ in waiters:
            await waiter
    finally:
        for i, fut in enumerate(futures):
            _, cb = waiters[i]
            fut.remove_done_callback(cb)


def _release_waiter(waiter, *args):
    if not waiter.done():
        waiter.set_result(None)


__all__ = [
    "ChanClosed",
    "Chan",
    "ChanSender",
    "ChanReceiver",
    "channel",
    "Interval",
    "interval",
    "Sleep",
    "SleepFinished",
    "sleep",
    "TaskSet",
    "debug",
    "gracefully_cancel",
    "duplex_unix",
    "itertools",
]
