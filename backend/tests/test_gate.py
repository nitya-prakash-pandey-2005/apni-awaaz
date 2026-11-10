"""Gnani allows one short REST request at a time per key (a second concurrent one gets 429)."""

import asyncio

import httpx
import numpy as np
from voice_core.audio import float_to_pcm16, wav_bytes
from voice_core.config import Settings
from voice_core.gnani import GnaniError
from voice_core.testing import FakeLLM

from awaaz import fake_mode
from awaaz.app import create_app


async def _post_speaks(app, texts):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        await c.post("/api/voice/enroll?consent=true", content=_clip_bytes())
        return await asyncio.gather(*(c.post("/api/speak", json={"text": t, "lang": "en-IN"}) for t in texts))


def _clip_bytes(seconds=10.0, hz=16000) -> bytes:
    t = np.arange(int(seconds * hz)) / hz
    x = 0.3 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 0.5 * t) > -0.3) + 0.001 * np.random.default_rng(0).standard_normal(len(t))
    return wav_bytes(float_to_pcm16(x.astype(np.float32)), hz)


async def test_parallel_speaks_never_overlap_gnani_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    state = {"now": 0, "max": 0}

    async def tts(api_key, text, *args, sample_rate=16000, **kw):
        state["now"] += 1
        state["max"] = max(state["max"], state["now"])
        await asyncio.sleep(0.05)
        state["now"] -= 1
        return b"\x01\x00" * 1600

    monkeypatch.setattr(fake_mode, "tone_pcm", tts)
    app = create_app(Settings(cache_dir=tmp_path), llm=FakeLLM())
    rs = await _post_speaks(app, ["one", "two", "three", "four"])
    assert all(r.status_code == 200 for r in rs)
    assert state["max"] == 1


async def test_a_429_is_retried_and_keeps_the_cloned_voice(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    calls = []

    async def busy_once(api_key, text, *args, sample_rate=16000, **kw):
        calls.append(text)
        if len(calls) == 1:
            raise GnaniError(429, '{"error": "RATE_LIMITED"}')
        return b"\x01\x00" * 1600

    monkeypatch.setattr(fake_mode, "tone_pcm", busy_once)
    app = create_app(Settings(cache_dir=tmp_path), llm=FakeLLM())
    (r,) = await _post_speaks(app, ["hello"])
    assert r.status_code == 200 and r.headers["x-voice"] == "clone" and len(calls) == 2
