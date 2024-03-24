from __future__ import annotations

import asyncio
import logging

from livekit import rtc

from ..log import logger
from . import apipe, protocol


class LogHandler(logging.Handler):
    """Log handler forwarding logs to the worker process"""

    def __init__(self, writer: protocol.ProcessPipeWriter) -> None:
        super().__init__(logging.NOTSET)
        self._writer = writer

    def emit(self, record: logging.LogRecord) -> None:
        protocol.write_msg(
            self._writer,
            protocol.Log(level=record.levelno, message=record.getMessage()),
        )


async def _run_loop(
    pipe: apipe.AsyncPipe,
    args: protocol.JobMainArgs,
) -> None:
    try:
        # connect to the rtc room as early as possible in the process lifecycle
        room = rtc.Room()
        await room.connect(args.url, args.token)

    except Exception:
        pass


def _run_job(cch: protocol.ProcessPipe, args: protocol.JobMainArgs) -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logging.basicConfig(handlers=[LogHandler(cch)], level=logging.NOTSET)
    logger.debug("process started")

    pipe = apipe.AsyncPipe(cch, loop=loop)
    loop.slow_callback_duration = 0.01  # 10ms
    loop.run_until_complete(_run_loop(pipe, args))
