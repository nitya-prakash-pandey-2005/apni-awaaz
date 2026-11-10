"""One Gnani REST request at a time, with a short retry on 429.

Live finding (8 Nov 2026): a key allows one short REST request at a time; a second concurrent one gets
429 RATE_LIMITED (an open Prisma stream plus one REST request is fine). This repo's copy of voice-core has
no gate, so every REST call the app makes (clip transcript, voice embedding, clone TTS, Timbre TTS) goes
through this one. Without it a double tap, a switch press while speaking, or Speak during a clip check gets a
429 on the clone call, and speak() silently answers in the fallback voice.
"""

from __future__ import annotations

import asyncio
import functools
import logging

from voice_core.gnani import GnaniError

log = logging.getLogger("awaaz.gate")


class GnaniGate:
    def __init__(self, retries: int = 2, backoff: tuple[float, ...] = (0.5, 1.5)):
        self.lock = asyncio.Lock()
        self.retries, self.backoff = retries, backoff

    def wrap(self, fn):
        @functools.wraps(fn)
        async def gated(*args, **kwargs):
            async with self.lock:
                for attempt in range(self.retries + 1):
                    try:
                        return await fn(*args, **kwargs)
                    except GnaniError as e:
                        if e.status != 429 or attempt == self.retries:
                            raise
                        delay = self.backoff[min(attempt, len(self.backoff) - 1)]
                        log.info("Gnani busy (429), retry %d in %.1fs", attempt + 1, delay)
                        await asyncio.sleep(delay)
        return gated
