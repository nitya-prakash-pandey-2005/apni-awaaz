"""The HTTP error contract, the privacy rules and the echo guard, end to end through the app in fake mode (no keys, no network)."""

import asyncio
import json
from urllib.parse import unquote

import numpy as np
import pytest
from fastapi.testclient import TestClient
from voice_core.audio import float_to_pcm16, wav_bytes
from voice_core.config import Settings
from voice_core.gnani.stt_stream import SttEvent
from voice_core.testing import FakeLLM

from awaaz import fake_mode
from awaaz.app import create_app


def _clip(seconds=10.0, hz=16000) -> bytes:
    t = np.arange(int(seconds * hz)) / hz
    x = 0.3 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 0.5 * t) > -0.3) + 0.001 * np.random.default_rng(0).standard_normal(len(t))
    return wav_bytes(float_to_pcm16(x.astype(np.float32)), hz)


@pytest.fixture
def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")

    def make(**settings):
        return TestClient(create_app(Settings(cache_dir=tmp_path, **settings)))

    return make


def test_unsupported_languages_are_rejected(make_client):
    with make_client() as c:
        assert c.put("/api/profile", json={"language": "xx-IN"}).status_code == 400
        assert c.post("/api/speak", json={"text": "hello", "lang": "fr-FR"}).status_code == 400
        assert c.get("/api/phrases?lang=de-DE").status_code == 400
        assert c.post("/api/sos", json={"local_lang": "zz-IN"}).status_code == 400


def test_empty_text_and_bad_audio_are_rejected(make_client):
    with make_client() as c:
        assert c.post("/api/speak", json={"text": "   "}).status_code == 400
        r = c.post("/api/voice/clip-check", content=b"not a wav")
        assert r.status_code == 400 and "WAV" in r.json()["detail"]


def test_consent_is_checked_before_the_audio(make_client):
    with make_client() as c:
        r = c.post("/api/voice/enroll", content=b"not a wav")
        assert r.status_code == 400 and "consent" in r.json()["detail"]
        assert c.post("/api/voice/enroll?consent=false", content=_clip()).status_code == 400
        assert c.get("/api/profile").json()["has_voice"] is False


def test_a_poor_clip_is_refused_with_its_quality_report(make_client):
    silent = wav_bytes(float_to_pcm16(np.zeros(16000 * 8, np.float32)), 16000)
    with make_client() as c:
        r = c.post("/api/voice/enroll?consent=true", content=silent)
        assert r.status_code == 422
        d = r.json()["detail"]
        assert d["message"] == "clip quality too low" and "too short" in d["quality"]["reasons"]
        assert c.get("/api/profile").json()["has_voice"] is False


def test_cloning_failure_keeps_the_fallback_voice(make_client, monkeypatch):
    async def refused(*a, **kw):
        raise RuntimeError("embedding service down")

    monkeypatch.setattr(fake_mode, "fake_embedding", refused)
    with make_client() as c:
        r = c.post("/api/voice/enroll?consent=true", content=_clip())
        assert r.status_code == 502 and "fallback voice stays on" in r.json()["detail"]
        assert c.get("/api/profile").json()["has_voice"] is False
        assert c.post("/api/speak", json={"text": "hello", "lang": "en-IN"}).headers["x-voice"] == "fallback"


def test_clip_check_survives_a_transcript_failure(make_client, monkeypatch):
    async def stt_down(*a, **kw):
        raise RuntimeError("STT down")

    monkeypatch.setattr(fake_mode, "fake_transcribe", stt_down)
    with make_client() as c:
        q = c.post("/api/voice/clip-check", content=_clip()).json()
    assert q["ok"] is True and q["text"] is None and q["lang"] is None


def test_keys_and_the_embedding_never_leave_the_server(make_client):
    with make_client(gnani_api_key="gnani-secret-123", groq_api_key="groq-secret-456") as c:
        h = c.get("/api/health")
        assert h.json()["gnani_key"] is True and h.json()["llm_key"] is True
        assert "secret" not in h.text
        enrolled = c.post("/api/voice/enroll?consent=true", content=_clip()).json()["profile"]
        profile = c.get("/api/profile").json()
    for p in (enrolled, profile):
        assert p["has_voice"] is True and "voice" not in p and "embedding" not in str(p)


def test_saving_the_profile_never_touches_the_voice_or_consent(make_client):
    with make_client() as c:
        before = c.post("/api/voice/enroll?consent=true", content=_clip()).json()["profile"]
        after = c.put("/api/profile", json={"name": "Asha", "language": "ta-IN"}).json()
        assert after["has_voice"] is True and after["consent_at"] == before["consent_at"] and after["name"] == "Asha"


def test_speak_headers_and_phrase_learning(make_client):
    with make_client() as c:
        r = c.post("/api/speak", json={"text": "मुझे पानी चाहिए", "lang": "hi-IN"})
        assert r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
        assert r.headers["x-voice"] == "fallback" and r.headers["x-translated"] == "false"
        c.post("/api/speak", json={"text": "बस", "lang": "hi-IN", "remember": False})
        phrases = c.get("/api/phrases?lang=hi-IN").json()
    assert phrases[0] == "मुझे पानी चाहिए" and "बस" not in phrases and len(phrases) == 12


def test_banked_audio_with_a_non_audio_type_is_stored_as_webm(make_client):
    with make_client() as c:
        mid = c.post("/api/messages?label=hello", content=b"abc", headers={"Content-Type": "text/plain"}).json()["id"]
        r = c.get(f"/api/messages/{mid}/audio")
    assert r.headers["content-type"] == "audio/webm" and r.content == b"abc"


def test_sos_in_one_language_when_local_matches_the_profile(make_client):
    with make_client() as c:
        r = c.post("/api/sos", json={"local_lang": "hi-IN"})
    assert r.status_code == 200 and r.content[:4] == b"RIFF" and r.headers["x-voice"] == "fallback"
    assert len(json.loads(unquote(r.headers["x-spoken-text"]))) == 1


class HearsAfterAudio:
    """STT that 'hears' the app's own sentence, then the other person, once the first audio frame arrives."""

    def __init__(self):
        self.audio = asyncio.Event()
        self.closed = asyncio.Event()

    async def connect(self):
        pass

    async def send_audio(self, pcm16):
        self.audio.set()

    async def events(self):
        yield SttEvent("connected")
        await self.audio.wait()
        yield SttEvent("transcript", text="मुझे पानी चाहिए", language="hi-IN")  # the phone hearing its own reply
        yield SttEvent("transcript", text="अभी लाती हूँ", language="hi-IN")
        await self.closed.wait()

    async def close(self):
        self.closed.set()


def test_what_the_app_says_is_not_captioned_as_the_other_person(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    good = json.dumps({"replies": ["हाँ", "धन्यवाद", "ठीक है"]})
    app = create_app(Settings(cache_dir=tmp_path), llm=FakeLLM([good] * 3), stt_factory=HearsAfterAudio)
    with TestClient(app) as c, c.websocket_connect("/ws/listen") as ws:
        assert ws.receive_json() == {"type": "status", "stt": "connected"}
        assert c.post("/api/speak", json={"text": "मुझे पानी चाहिए", "lang": "hi-IN"}).status_code == 200
        ws.send_bytes(b"\x00\x00" * 160)
        first = ws.receive_json()
    assert first["type"] == "caption" and first["text"] == "अभी लाती हूँ"


async def test_scripted_nurse_speaks_in_turn_and_stops_on_close():
    stt = fake_mode.ScriptedStt(every=0.01)
    await stt.connect()
    await stt.send_audio(b"\x00\x00")
    await stt.commit()
    seen = []
    async for e in stt.events():
        seen.append(e)
        if len(seen) == 3:
            await stt.close()
    assert [e.type for e in seen] == ["connected", "transcript", "transcript", "closed"]
    assert seen[1].text == fake_mode.NURSE[0] and not stt.connected
