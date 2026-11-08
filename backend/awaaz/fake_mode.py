"""AWAAZ_FAKE=1: run the whole app with no API keys. Tones stand in for speech; a scripted nurse talks."""

from __future__ import annotations

import asyncio
import hashlib
import itertools
import json

import numpy as np
from voice_core.audio import float_to_pcm16
from voice_core.gnani.stt_stream import SttEvent

from .phrases import default_phrases
from .speak import LANGS

NURSE = ["नमस्ते, आज आप कैसा महसूस कर रहे हैं?", "क्या आपको कहीं दर्द हो रहा है?",
         "दवाई खाने के बाद पानी पीना है।", "आपका बेटा शाम को आएगा।"]


class FakeAwaazLLM:
    """Rewrites echo the input; suggestion prompts get 3 rotating quick phrases in the asked language."""

    provider = "fake"
    model = "fake"

    def __init__(self):
        self._n = itertools.count()

    async def complete(self, messages, **kw) -> str:
        await asyncio.sleep(0.3)
        system = messages[0]["content"]
        if system.startswith("Rewrite"):
            return messages[-1]["content"]
        code = next((c for c, name in LANGS.items() if f"in {name} " in system), "hi-IN")
        pool, i = default_phrases(code), next(self._n) * 3
        return json.dumps({"replies": [pool[(i + k) % len(pool)] for k in range(3)]}, ensure_ascii=False)


async def tone_pcm(api_key, text, *args, sample_rate: int = 16000, **kw) -> bytes:
    """A soft hum whose length follows the text; the pitch differs per voice so clone and fallback sound different."""
    await asyncio.sleep(0.2)
    hz = 220 if args else 330  # args = (embedding,) for the clone call
    secs = min(5.0, 0.06 * len(text) + 0.4)
    t = np.arange(int(secs * sample_rate)) / sample_rate
    x = 0.12 * np.sin(2 * np.pi * hz * t) * np.minimum(1, np.minimum(t, secs - t) * 8)
    return float_to_pcm16(x.astype(np.float32))


async def fake_embedding(api_key, wav: bytes) -> dict:
    h = hashlib.sha1(wav[:65536]).digest()
    return {"embedding": [b / 255 for b in h[:8]], "shape": [1, 8], "dtype": "float32"}


async def fake_transcribe(api_key, wav: bytes, **kw) -> SttEvent:
    return SttEvent("transcript", text="हाँ बेटा, मैं ठीक हूँ, तुम कब आ रहे हो?", language="hi-IN")


class ScriptedStt:
    """Ignores audio; 'hears' the next nurse line every `every` seconds."""

    def __init__(self, every: float = 7.0):
        self.every = every
        self.connected = False
        self._closed = asyncio.Event()

    async def connect(self):
        self.connected = True

    async def send_audio(self, pcm16: bytes):
        pass

    async def commit(self):
        pass

    async def events(self):
        yield SttEvent("connected")
        for line in NURSE:
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=self.every)
                break
            except asyncio.TimeoutError:
                yield SttEvent("transcript", text=line, language="hi-IN", latency_ms=180.0)
        await self._closed.wait()
        yield SttEvent("closed")

    async def close(self):
        self.connected = False
        self._closed.set()
