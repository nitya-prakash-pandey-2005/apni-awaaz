import json
from urllib.parse import unquote

import numpy as np
import pytest
from fastapi.testclient import TestClient
from voice_core.audio import float_to_pcm16, wav_bytes
from voice_core.config import Settings
from voice_core.testing import FakeLLM, FakeStt, ev

from awaaz import fake_mode
from awaaz.app import create_app

GOOD = json.dumps({"replies": ["हाँ", "थोड़ा पानी", "धन्यवाद"]})


def _clip(seconds=10.0, hz=16000) -> bytes:
    t = np.arange(int(seconds * hz)) / hz
    x = 0.3 * np.sin(2 * np.pi * 180 * t) * (np.sin(2 * np.pi * 0.5 * t) > -0.3) + 0.001 * np.random.default_rng(0).standard_normal(len(t))
    return wav_bytes(float_to_pcm16(x.astype(np.float32)), hz)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    stt = lambda: FakeStt([ev("connected"), ev("transcript", "क्या आपको दर्द हो रहा है?", "hi-IN")])  # noqa: E731
    with TestClient(create_app(Settings(cache_dir=tmp_path), llm=FakeLLM([GOOD] * 5), stt_factory=stt)) as c:
        yield c


def test_health_and_profile(client):
    assert client.get("/api/health").json()["fake"] is True
    p = client.put("/api/profile", json={"name": "Asha", "language": "hi-IN", "family_names": ["Ravi"]}).json()
    assert p["name"] == "Asha" and p["has_voice"] is False and "voice" not in p
    assert client.get("/api/profile").json()["family_names"] == ["Ravi"]


def test_clip_check(client):
    q = client.post("/api/voice/clip-check", content=_clip(), headers={"Content-Type": "audio/wav"}).json()
    assert q["ok"] and q["text"] and q["lang"] == "hi-IN"
    bad = client.post("/api/voice/clip-check", content=_clip(3), headers={"Content-Type": "audio/wav"}).json()
    assert not bad["ok"] and "too short" in bad["reasons"]
    assert client.post("/api/voice/clip-check", content=b"not a wav").status_code == 400


def test_long_voice_note_is_judged_on_the_30_s_actually_used(client):
    long = _clip(60)  # a one-minute WhatsApp note: about 37 s of speech
    q = client.post("/api/voice/clip-check", content=long).json()
    assert q["ok"], q
    assert client.post("/api/voice/enroll?consent=true", content=long).status_code == 200


def test_clip_with_no_clear_speech_is_flagged(tmp_path, monkeypatch):
    async def music_only(api_key, wav, **kw):  # Prisma hears nothing usable (music, two people talking over each other)
        return fake_mode.SttEvent("transcript", text="", language=None)

    monkeypatch.setenv("AWAAZ_FAKE", "1")
    monkeypatch.setattr(fake_mode, "fake_transcribe", music_only)
    with TestClient(create_app(Settings(cache_dir=tmp_path))) as c:
        q = c.post("/api/voice/clip-check", content=_clip()).json()
    assert not q["ok"] and "no clear speech" in q["reasons"]


def test_enroll_needs_consent_then_speaks_in_clone_voice(client):
    assert client.post("/api/voice/enroll", content=_clip()).status_code == 400
    assert client.post("/api/voice/enroll?consent=false", content=_clip()).status_code == 400
    assert client.post("/api/voice/enroll?consent=true", content=_clip(3)).status_code == 422
    r = client.post("/api/voice/enroll?consent=true", content=_clip()).json()
    assert r["profile"]["has_voice"] and r["profile"]["consent_at"] and r["test_text"]
    s = client.post("/api/speak", json={"text": "नमस्ते", "lang": "hi-IN"})
    assert s.status_code == 200 and s.headers["content-type"] == "audio/wav" and s.content[:4] == b"RIFF"
    assert s.headers["x-voice"] == "clone" and unquote(s.headers["x-spoken-text"]) == "नमस्ते"
    assert client.delete("/api/voice").json()["has_voice"] is False
    assert client.post("/api/speak", json={"text": "नमस्ते", "lang": "hi-IN"}).headers["x-voice"] == "fallback"


def test_delete_voice_also_deletes_audio_made_in_that_voice(client, tmp_path):
    cached = lambda: sorted(tmp_path.rglob("*.bin"))  # noqa: E731
    assert client.post("/api/voice/enroll?consent=true", content=_clip()).status_code == 200
    assert client.post("/api/speak", json={"text": "मुझे पानी चाहिए", "lang": "hi-IN"}).headers["x-voice"] == "clone"
    assert len(cached()) == 1
    client.delete("/api/voice")
    assert cached() == []


def test_phrases_learn_from_use(client):
    assert len(client.get("/api/phrases?lang=hi-IN").json()) == 12
    client.post("/api/speak", json={"text": "चाय पीनी है", "lang": "hi-IN"})
    assert client.get("/api/phrases?lang=hi-IN").json()[0] == "चाय पीनी है"
    assert client.get("/api/phrases?lang=kn-IN").json()[0] == "Yes"  # English list, translated when spoken


def test_sos_speaks_two_languages(client):
    client.put("/api/profile", json={"name": "Asha", "language": "ta-IN"})
    r = client.post("/api/sos", json={"local_lang": "hi-IN"})
    assert r.status_code == 200 and r.content[:4] == b"RIFF"
    texts = json.loads(unquote(r.headers["x-spoken-text"]))
    assert len(texts) == 2 and texts[0].startswith("அவசரம்") and texts[1].startswith("आपातकाल")


def test_listen_ws_caption_and_suggestions(client):
    client.put("/api/profile", json={"name": "Asha", "language": "hi-IN"})
    with client.websocket_connect("/ws/listen") as ws:
        ws.send_bytes(b"\x00\x00" * 512)
        seen = {}
        for _ in range(10):
            m = ws.receive_json()
            seen[m["type"]] = m
            if "suggestions" in seen:
                break
        assert seen["caption"]["text"] == "क्या आपको दर्द हो रहा है?"
        assert seen["suggestions"]["items"] == ["हाँ", "थोड़ा पानी", "धन्यवाद"]


def test_fake_mode_boots_without_overrides(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    with TestClient(create_app(Settings(cache_dir=tmp_path))) as c:
        assert c.post("/api/voice/enroll?consent=true", content=_clip()).status_code == 200
        assert c.post("/api/speak", json={"text": "mujhe paani chahiye", "lang": "hi-IN"}).headers["x-voice"] == "clone"


def test_message_banking_keeps_the_original_recording(client):
    audio = b"RIFF" + b"\x00" * 2000
    r = client.post("/api/messages?label=I love you, beta", content=audio, headers={"Content-Type": "audio/wav"})
    assert r.status_code == 200 and r.json()["label"] == "I love you, beta"
    mid = r.json()["id"]
    assert [m["label"] for m in client.get("/api/messages").json()] == ["I love you, beta"]
    got = client.get(f"/api/messages/{mid}/audio")
    assert got.content == audio and got.headers["content-type"] == "audio/wav"
    assert client.post("/api/messages?label=x", content=b"").status_code == 400
    assert client.post("/api/messages?label=", content=audio).status_code == 400
    assert client.post("/api/messages?label=big", content=b"0" * (8 * 1024 * 1024 + 1)).status_code == 413
    assert client.delete(f"/api/messages/{mid}").status_code == 200 and client.get("/api/messages").json() == []
    assert client.get(f"/api/messages/{mid}/audio").status_code == 404
