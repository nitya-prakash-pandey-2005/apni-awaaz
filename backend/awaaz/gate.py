"""One Gnani REST request at a time.

Checked on Gnani's servers (8 Nov 2026): a second concurrent short REST request on the same key gets
429 RATE_LIMITED, while an open Prisma stream plus one REST request is allowed. So every REST call in
this app (STT REST, voice embedding, clone TTS, Timbre TTS) goes through one shared gate, and a 429
(another app on the same key) is retried a couple of times with a short backoff.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from voice_core.gnani import GnaniError

log = logging.getLogger(__name__)


class GnaniGate:
    def __init__(self, retries: int = 2, backoff: tuple[float, ...] = (0.6, 1.5)):
        self.lock = asyncio.Lock()
        self.retries = retries
        self.backoff = backoff or (0.0,)

    async def run(self, fn: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        async with self.lock:
            attempt = 0
            while True:
                try:
                    return await fn(*args, **kwargs)
                except GnaniError as e:
                    if e.status != 429 or attempt >= self.retries:
                        raise
                    delay = self.backoff[min(attempt, len(self.backoff) - 1)]
                    log.info("Gnani 429, retry %d in %.1fs", attempt + 1, delay)
                    await asyncio.sleep(delay)
                    attempt += 1
