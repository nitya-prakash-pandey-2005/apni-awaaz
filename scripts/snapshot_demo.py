"""Snapshot the live session into static files for the no-backend demo (`npm run build:demo`, see docs/DEPLOY-VERCEL.md).

Runs the real FastAPI app in-process on a COPY of the session's database and saves every GET the app makes as JSON
under frontend/demo/. It cannot reach Gnani or Groq: every API key is blank in the Settings object (an empty env var
would fall back to .env, so Settings is built directly), the Gnani functions and the LLM raise if called, no voice
session is opened, and outgoing HTTP and WebSocket connections are blocked.

    uv run python scripts/snapshot_demo.py [--db PATH] [--nurse FULL_NURSE_WAV]

--nurse rebuilds the Converse replay (converse.json + audio/nurse.wav) from the nurse track played in the session.
The cloned-voice audio is made separately by scripts/record_demo_audio.py (needs keys).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_session as S  # noqa: E402

RATE = 16000


def lock_down():
    """Make any call to Gnani, Groq or the network fail loudly. Returns an LLM that raises."""
    import httpx
    import websockets

    async def no_http(self, request, *a, **k):
        raise RuntimeError(f"snapshot: network blocked ({request.url})")

    def no_ws(*a, **k):
        raise RuntimeError("snapshot: network blocked (websocket)")

    httpx.AsyncClient.send = no_http
    websockets.connect = no_ws

    import awaaz.app as app_mod
    from voice_core.gnani import tts as tts_mod

    tts_mod._ws_connect = no_ws

    async def no_gnani(*a, **k):
        raise RuntimeError("snapshot: Gnani is never called")

    for name in ("create_voice_embedding", "transcribe_rest", "tts_clone_rest", "tts_rest"):
        setattr(app_mod, name, no_gnani)

    class NoLLM:
        provider = model = "none"

        async def complete(self, *a, **k):
            raise RuntimeError("snapshot: the LLM is never called")

        async def stream(self, *a, **k):
            raise RuntimeError("snapshot: the LLM is never called")

    return NoLLM()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def snapshot_api(db: Path) -> None:
    os.environ.pop("AWAAZ_FAKE", None)
    llm = lock_down()
    from awaaz.app import create_app
    from fastapi.testclient import TestClient
    from voice_core.config import Settings

    def no_stt():
        raise RuntimeError("snapshot: no voice sessions")

    api, audio = S.DEMO / "snapshot", S.DEMO / "audio"
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:  # SQLite keeps the copy open on Windows
        shutil.copy(db, Path(tmp) / "awaaz.db")
        settings = Settings(gnani_api_key="", groq_api_key="", evon_base_url="", evon_api_key="", cache_dir=Path(tmp))
        app = create_app(settings, llm=llm, stt_factory=no_stt)
        with TestClient(app) as c:
            get = lambda path: c.get(path).raise_for_status()  # noqa: E731
            health = get("/api/health").json()
            write_json(api / "health.json", {**health, "has_voice": True, "demo": True})
            profile = get("/api/profile").json()
            used = next(n for n in S.NOTES if n["name"] == S.USED_NOTE)
            # the voice was deleted at the end of the session (the live delete test); show the state before that
            profile.update(has_voice=True, consent_at=S.CONSENT_AT, voice_meta=note_quality(used))
            write_json(api / "profile.json", profile)
            messages = get("/api/messages").json()
            write_json(api / "messages.json", messages)
            for m in messages:
                r = get(f"/api/messages/{m['id']}/audio")
                (audio / f"message-{m['id']}.wav").write_bytes(r.content)
            for lang in S.LANGS:
                write_json(api / f"phrases-{lang}.json", get(f"/api/phrases?lang={lang}").json())
    print(f"api: health, profile, {len(messages)} banked messages, phrases for {len(S.LANGS)} languages")


def note_quality(n: dict) -> dict:
    from voice_core.audio import read_wav

    x, hz = read_wav((S.DEMO / "audio" / "notes" / n["name"]).read_bytes())
    return {"duration_s": round(len(x) / hz, 2), "speech_s": n["speech_s"], "clipping_pct": 0.0, "snr_db": n["snr_db"],
            "ok": n["ok"], "reasons": n["reasons"], "text": n["text"], "lang": "hi-IN"}


def snapshot_voice_bank() -> None:
    clips = [{"name": n["name"], "file": f"audio/notes/{n['name']}", "quality": note_quality(n)} for n in S.NOTES]
    write_json(S.DEMO / "voice-clips.json", {"clips": clips, "used": S.USED_NOTE, "test_text": S.TEST_TEXT, "lang": S.TEST_LANG})
    print(f"voice bank: {len(clips)} notes")


def ensure_recordings() -> None:
    """recordings.json lists the cloned-voice audio. Kept as it is if present (record_demo_audio.py fills it)."""
    path = S.DEMO / "recordings.json"
    if path.exists():
        recs = json.loads(path.read_text(encoding="utf-8"))
        print(f"recordings: kept ({sum(1 for r in recs if r.get('file'))} with audio)")
        return
    from awaaz.phrases import sos_text

    recs = [{"kind": "speak", "text": t, "lang": lang, "spoken": spoken, "voice": "clone", "file": None} for t, lang, spoken in S.SPOKEN]
    recs.append({"kind": "sos", "langs": S.SOS_LANGS, "texts": [sos_text(x) for x in S.SOS_LANGS], "voice": "clone", "file": None})
    write_json(path, recs)
    print("recordings: written without audio (run scripts/record_demo_audio.py with keys)")


def speech_segments(x: np.ndarray, hz: int) -> list[tuple[float, float]]:
    f = hz // 50
    n = len(x) // f
    on = np.sqrt((x[: n * f].reshape(n, f) ** 2).mean(1)) > 0.01
    segs: list[list[float]] = []
    for i in np.flatnonzero(on):
        t = i * 0.02
        if segs and t - segs[-1][1] < 0.14:
            segs[-1][1] = t + 0.02
        else:
            segs.append([t, t + 0.02])
    return [(a, b) for a, b in segs]


def snapshot_converse(nurse: Path) -> None:
    """The nurse's first sentence, cut from the track played through Chrome's fake mic. Caption times: the end of each
    phrase plus Prisma's end-of-speech pause (0.7 s); suggestions 1 s later (the test log: within about 1 s)."""
    from voice_core.audio import float_to_pcm16, read_wav, wav_bytes

    x, hz = read_wav(nurse.read_bytes())
    segs = speech_segments(x, hz)[: len(S.NURSE_CAPTIONS)]
    t0, t1 = max(0.0, segs[0][0] - 0.5), segs[-1][1] + 2.5
    (S.DEMO / "audio").mkdir(parents=True, exist_ok=True)
    (S.DEMO / "audio" / "nurse.wav").write_bytes(wav_bytes(float_to_pcm16(x[int(t0 * hz): int(t1 * hz)]), hz))
    events = [{"t": round(end - t0 + 0.7, 2), "type": "caption", "text": text} for (_, end), text in zip(segs, S.NURSE_CAPTIONS)]
    events.append({"t": round(events[-1]["t"] + 1.0, 2), "type": "suggestions", "items": S.SUGGESTIONS})
    write_json(S.DEMO / "converse.json", {"audio": "audio/nurse.wav", "duration": round(max(t1 - t0, events[-1]["t"] + 0.5), 2),
                                          "events": events, "note": "Caption and suggestion texts are from the live session; times follow the audio."})
    print(f"converse: {t1 - t0:.1f} s of nurse audio, {len(events)} events")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=S.LIVE_DB)
    ap.add_argument("--nurse", type=Path, help="full nurse track from the session (rebuilds the Converse replay)")
    a = ap.parse_args()
    if not a.db.exists():
        sys.exit(f"no database at {a.db}")
    snapshot_api(a.db)
    snapshot_voice_bank()
    ensure_recordings()
    if a.nurse:
        snapshot_converse(a.nurse)


if __name__ == "__main__":
    main()
