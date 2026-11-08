import json
from urllib.parse import unquote

import numpy as np
import pytest
from fastapi.testclient import TestClient

from voice_core.audio import float_to_pcm16, read_wav, wav_bytes
from voice_core.config import Settings
from voice_core.testing import FakeStt, ev

from awaaz.app import create_app

HZ = 16000
NURSE = "दर्द कहाँ हो रहा है?"


@pytest.fixture
def make_client(tmp_path):
    clients = []

    def make(events=None, gap=0.0):
        events = events if events is not None else [ev("connected"), ev("transcript", NURSE, "hi-IN")]
        app = create_app(Settings(cache_dir=tmp_path / "cache"), fake=True,
                         stt_factory=lambda: FakeStt(list(events), gap=gap))
        c = TestClient(app)
        c.__enter__()
        clients.append(c)
        return c

    yield make
    for c in clients:
        c.__exit__(None, None, None)


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def wav(speechlike):
    def make(seconds=10.0, snr_db=30.0, seed=0):
        return wav_bytes(float_to_pcm16(speechlike(seconds, HZ, snr_db=snr_db, seed=seed)), HZ)
    return make


def enroll(client, *clips, consent="true"):
    files = [("audio", (f"note{i}.wav", c, "audio/wav")) for i, c in enumerate(clips)]
    data = {} if consent is None else {"consent": consent}
    return client.post("/api/voice/enroll", files=files, data=data)


def test_health_reports_fake_mode(client):
    h = client.get("/api/health").json()
    assert h["fake"] is True and h["gnani_key"] is False and h["clone"]["available"] is True
    assert h["has_voice"] is False


def test_profile_get_put(client):
    p = client.get("/api/profile").json()
    assert p["exists"] is False and p["has_voice"] is False and "voice" not in p
    body = {"name": "Asha", "language": "ta-IN", "local_language": "hi-IN", "family_names": ["Ravi", " ", "Meena"],
            "condition": "Throat cancer surgery", "fallback_voice": "Lakshmi"}
    r = client.put("/api/profile", json=body)
    assert r.status_code == 200
    p = client.get("/api/profile").json()
    assert p["exists"] is True and p["name"] == "Asha" and p["language"] == "ta-IN"
    assert p["family_names"] == ["Ravi", "Meena"] and p["fallback_voice"] == "Lakshmi"
    assert client.put("/api/profile", json={**body, "language": "xx-YY"}).status_code == 422
    assert client.put("/api/profile", json={**body, "fallback_voice": "Nobody"}).status_code == 422


def test_clip_check_good_short_and_broken(client, wav):
    good = client.post("/api/voice/clip-check", files={"audio": ("a.wav", wav(10), "audio/wav")}).json()
    assert good["ok"] is True and good["transcript"] and good["language"] == "hi-IN" and good["trimmed"] is False
    short = client.post("/api/voice/clip-check", files={"audio": ("b.wav", wav(3), "audio/wav")}).json()
    assert short["ok"] is False and "too short" in short["reasons"] and short["transcript"] is None
    long_ = client.post("/api/voice/clip-check", files={"audio": ("c.wav", wav(40), "audio/wav")}).json()
    assert long_["trimmed"] is True and long_["duration_s"] == 30.0
    r = client.post("/api/voice/clip-check", files={"audio": ("x.opus", b"OggS not a wav", "audio/ogg")})
    assert r.status_code == 400 and "WAV" in r.json()["detail"]


def test_enroll_without_consent_is_refused(client, wav):
    for consent in (None, "", "false", "no"):
        r = enroll(client, wav(), consent=consent)
        assert r.status_code == 400 and "consent" in r.json()["detail"].lower()
    assert client.get("/api/profile").json()["has_voice"] is False


def test_enroll_with_consent_builds_the_voice(client, wav):
    r = enroll(client, wav(10, 20, seed=1), wav(3, 40, seed=2), wav(12, 35, seed=3))
    assert r.status_code == 200
    body = r.json()
    assert "embedding" not in json.dumps(body)  # the embedding never leaves the server
    assert body["chosen"] == 2 and [c["ok"] for c in body["clips"]] == [True, False, True]
    p = body["profile"]
    assert p["has_voice"] is True and p["consent_at"] and p["voice_meta"]["filename"] == "note2.wav"
    assert client.get("/api/profile").json()["has_voice"] is True
    t = client.get(body["test_audio_url"])
    assert t.status_code == 200 and t.headers["content-type"] == "audio/wav"
    assert t.headers["x-voice"] == "clone" and unquote(t.headers["x-spoken-text"]) == "नमस्ते, ये मेरी आवाज़ है।"
    assert read_wav(t.content)[1] == HZ


def test_enroll_with_only_bad_clips_explains_why(client, wav):
    r = enroll(client, wav(3), wav(10, snr_db=3))
    assert r.status_code == 422
    clips = r.json()["detail"]["clips"]
    assert "too short" in clips[0]["reasons"] and "noisy" in clips[1]["reasons"]
    assert enroll(client).status_code == 400  # no clip at all


def test_speak_returns_wav_with_voice_header(client, wav):
    r = client.post("/api/speak", json={"text": "mujhe paani chahiye", "lang": "hi-IN"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    assert r.headers["x-voice"] == "fallback" and r.headers["x-voice-reason"] == "no_voice"
    assert unquote(r.headers["x-spoken-text"]) == "मुझे पानी चाहिए" and r.headers["x-translated"] == "1"
    x, hz = read_wav(r.content)
    assert hz == HZ and len(x) > HZ // 2
    enroll(client, wav())
    r = client.post("/api/speak", json={"text": "मुझे पानी चाहिए", "lang": "hi-IN"})
    assert r.headers["x-voice"] == "clone" and r.headers["x-translated"] == "0"


def test_speak_rejects_bad_input(client):
    assert client.post("/api/speak", json={"text": "   ", "lang": "hi-IN"}).status_code == 400
    assert client.post("/api/speak", json={"text": "hello", "lang": "xx-YY"}).status_code == 400
    assert client.post("/api/speak", json={"text": "x" * 501, "lang": "en-IN"}).status_code == 422


def test_clone_failure_keeps_working_with_the_fallback_voice(client, wav, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE_CLONE", "fail")
    enroll(client, wav())
    r = client.post("/api/speak", json={"text": "धन्यवाद", "lang": "hi-IN"})
    assert r.status_code == 200 and r.headers["x-voice"] == "fallback" and r.headers["x-voice-reason"] == "clone_error"
    assert client.get("/api/health").json()["clone"]["available"] is False


def test_delete_voice_removes_it_and_its_audio(client, wav, tmp_path):
    enroll(client, wav())
    client.post("/api/speak", json={"text": "नमस्ते", "lang": "hi-IN"})
    tts_dir = tmp_path / "cache" / "awaaz_fake" / "tts"
    assert any(p.name.startswith("c-") for p in tts_dir.iterdir())
    r = client.delete("/api/voice")
    assert r.status_code == 200 and r.json()["deleted"] is True and r.json()["clips_removed"] >= 2
    p = client.get("/api/profile").json()
    assert p["has_voice"] is False and p["consent_at"] is None
    assert not any(p.name.startswith("c-") for p in tts_dir.iterdir())
    assert client.post("/api/speak", json={"text": "नमस्ते", "lang": "hi-IN"}).headers["x-voice"] == "fallback"
    assert client.delete("/api/voice").json()["deleted"] is False


def test_phrases_and_learning(client):
    r = client.get("/api/phrases", params={"lang": "ta-IN"}).json()
    assert len(r["quick"]) == 12 and r["quick"][0]["text"] == "எனக்கு தண்ணீர் வேண்டும்" and r["frequent"] == []
    for _ in range(2):
        client.post("/api/speak", json={"text": "मेरा चश्मा कहाँ है?", "lang": "hi-IN"})
    client.post("/api/speak", json={"text": "मुझे पानी चाहिए", "lang": "hi-IN"})
    r = client.get("/api/phrases", params={"lang": "hi-IN"}).json()
    assert r["frequent"] == ["मेरा चश्मा कहाँ है?"]  # grid phrases are not repeated
    assert r["quick"][0]["uses"] == 1
    assert client.get("/api/phrases", params={"lang": "zz"}).status_code == 400


def test_listen_ws_gives_caption_and_suggestions(client):
    with client.websocket_connect("/ws/listen?lang=hi-IN&reply=hi-IN") as ws:
        msgs = []
        while not any(m["type"] == "suggestions" for m in msgs):
            msgs.append(ws.receive_json())
        ws.send_bytes(b"\x00" * 1024)
        ws.send_json({"type": "stop"})
    cap = next(m for m in msgs if m["type"] == "caption")
    sug = next(m for m in msgs if m["type"] == "suggestions")
    assert cap["text"] == NURSE and len(sug["items"]) == 3 and all(sug["items"])


def test_listen_ws_drops_my_own_voice(make_client):
    c = make_client(events=[ev("connected"), ev("transcript", "मुझे पानी चाहिए", "hi-IN"), ev("transcript", NURSE, "hi-IN")],
                    gap=0.15)
    with c.websocket_connect("/ws/listen") as ws:
        ws.send_json({"type": "spoken", "text": "मुझे पानी चाहिए"})
        msgs = []
        while not any(m["type"] == "suggestions" for m in msgs):
            msgs.append(ws.receive_json())
    assert [m["text"] for m in msgs if m["type"] == "echo_ignored"] == ["मुझे पानी चाहिए"]
    assert [m["text"] for m in msgs if m["type"] == "caption"] == [NURSE]


def test_sos_speaks_both_languages(client):
    client.put("/api/profile", json={"name": "Asha", "language": "hi-IN", "local_language": "ta-IN",
                                     "family_names": ["Ravi"], "condition": "", "fallback_voice": "Shivani"})
    r = client.post("/api/sos", json={})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav"
    lines = json.loads(unquote(r.headers["x-sos-lines"]))
    assert [l["lang"] for l in lines] == ["hi-IN", "ta-IN"]
    assert "Ravi" in lines[0]["text"] and lines[0]["end_s"] <= lines[1]["start_s"]
    x, hz = read_wav(r.content)
    assert hz == HZ and abs(len(x) / HZ - lines[1]["end_s"]) < 0.05
    one = json.loads(unquote(client.post("/api/sos", json={"local_lang": "hi-IN"}).headers["x-sos-lines"]))
    assert [l["lang"] for l in one] == ["hi-IN"]  # same language twice is said once


def test_fake_mode_from_environment(tmp_path, monkeypatch, wav):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    app = create_app(Settings(cache_dir=tmp_path / "c"))
    with TestClient(app) as c:
        assert c.get("/api/health").json()["fake"] is True
        assert enroll(c, wav()).status_code == 200
        with c.websocket_connect("/ws/listen?lang=hi-IN") as ws:
            first = [ws.receive_json() for _ in range(2)]
        assert first[0] == {"type": "status", "stt": "connected"}


def test_scripted_stt_and_fake_llm_suggestions_match():
    import asyncio

    from awaaz.fake_mode import FakeAwaazLLM, ScriptedStt
    from awaaz.converse import suggest
    from awaaz.profiles import Profile
    from voice_core.types import Turn

    stt = ScriptedStt("hi-IN", every=0.01, first=0.01)

    async def first_transcript():
        await stt.connect()
        async for e in stt.events():
            if e.type == "transcript":
                await stt.close()
                return e

    e = asyncio.run(first_transcript())
    items = asyncio.run(suggest(FakeAwaazLLM(), Profile(language="en-IN"), [Turn("partner", e.text, 0.0)]))
    assert len(items) == 3 and items[0] == "A little better today"


def test_static_frontend_is_served_when_built(tmp_path, monkeypatch):
    import awaaz.app as app_mod

    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><title>Apni Awaaz</title>", encoding="utf-8")
    monkeypatch.setattr(app_mod, "frontend_dist", lambda: dist)
    with TestClient(create_app(Settings(cache_dir=tmp_path / "c"), fake=True)) as c:
        assert "Apni Awaaz" in c.get("/").text
        assert c.get("/api/health").status_code == 200
