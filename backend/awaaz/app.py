"""Apni Awaaz backend: profile, voice bank (quality check + Gnani voice cloning), speak, phrases, SOS,
and the live-caption WebSocket.

Run:  bash run_backend.sh            (port 8767; or .\\run_backend.ps1 on Windows)
No keys / bad network:  FAKE=1 bash run_backend.sh   (or .\\run_backend.ps1 -fake): fake voice, tone audio,
a scripted nurse for captions and scripted suggestions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from urllib.parse import quote

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from voice_core.audio import float_to_pcm16, read_wav, resample, wav_bytes
from voice_core.config import Settings, get_settings, repo_root
from voice_core.gnani import TtsCache, create_voice_embedding, transcribe_rest
from voice_core.llm import LLM

from .converse import ListenSession
from .fake_mode import FakeAwaazLLM, ScriptedStt, fake_clone_tts, fake_embedding, fake_timbre_tts, fake_transcribe
from .gate import GnaniGate
from .langs import ALL_VOICES, LANGS
from .phrases import QUICK, quick_phrases, sos_text, voice_test_phrase
from .profiles import Profile, ProfileStore, now_iso, voice_id
from .quality import best_clip, clip_quality, transcript_check, trim_seconds
from .speak import SAMPLE_RATE, CloneBreaker, SpeakError, purge_voice_audio, speak

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("awaaz")

MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_CLIPS = 5
SOS_GAP_S = 0.7
CONSENT_YES = {"true", "1", "yes", "on"}
NO_KEY = "The Gnani API key is missing on the server (.env). Start the backend in fake mode to try the app without keys."


def frontend_dist() -> Path:
    return repo_root() / "frontend" / "dist"


class ProfileIn(BaseModel):
    name: str = Field("", max_length=60)
    language: str = "hi-IN"
    local_language: str = "hi-IN"
    family_names: list[str] = Field(default_factory=list, max_length=8)
    condition: str = Field("", max_length=120)
    fallback_voice: str = "Shivani"

    @field_validator("language", "local_language")
    @classmethod
    def _known_language(cls, v: str) -> str:
        if v not in LANGS:
            raise ValueError("unsupported language")
        return v

    @field_validator("fallback_voice")
    @classmethod
    def _known_voice(cls, v: str) -> str:
        if v not in ALL_VOICES:
            raise ValueError("unknown Timbre v3.0 voice")
        return v

    @field_validator("family_names")
    @classmethod
    def _clean_names(cls, v: list[str]) -> list[str]:
        return [n.strip()[:40] for n in v if n and n.strip()]

    @field_validator("name", "condition")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class SpeakIn(BaseModel):
    text: str = Field(..., max_length=500)
    lang: str = "hi-IN"


class SosIn(BaseModel):
    local_lang: str | None = None


def public_profile(p: Profile | None) -> dict:
    """The profile as the browser sees it: never the embedding itself."""
    exists = p is not None
    p = p or Profile()
    d = p.model_dump(exclude={"voice"})
    d.update(exists=exists, has_voice=bool(p.voice), voice_id=voice_id(p.voice))
    return d


def wav_response(wav: bytes, meta: dict, extra: dict | None = None) -> Response:
    headers = {
        "X-Voice": meta.get("voice", "fallback"),
        "X-Voice-Name": meta.get("voice_name") or "",
        "X-Voice-Reason": meta.get("reason") or "",
        "X-Spoken-Text": quote(meta.get("spoken_text") or ""),
        "X-Translated": "1" if meta.get("translated") else "0",
        "X-Cached": "1" if meta.get("cached") else "0",
        "X-Lang-Note": meta.get("lang_note") or "",
        "Cache-Control": "no-store",
        **(extra or {}),
    }
    return Response(wav, media_type="audio/wav", headers=headers)


def load_clip(data: bytes) -> np.ndarray:
    """A 16-bit WAV (the browser converts voice notes with decodeToPcm16) -> float32 mono at 16 kHz."""
    try:
        x, hz = read_wav(data)
    except Exception:
        raise HTTPException(400, "Please send a 16-bit WAV file. (The app converts voice notes to WAV in the browser; "
                                 "if that failed, export the voice note as MP3 or WAV and try again.)") from None
    return resample(x, hz, SAMPLE_RATE) if hz != SAMPLE_RATE else x


async def read_upload(f: UploadFile) -> bytes:
    data = await f.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "This file is too large. Please use a voice note under 30 seconds.")
    return data


def create_app(settings: Settings | None = None, *, fake: bool | None = None, stt_factory=None, llm=None) -> FastAPI:
    settings = settings or get_settings()
    fake = os.environ.get("AWAAZ_FAKE") == "1" if fake is None else fake
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    store = ProfileStore(settings.cache_dir / ("awaaz_fake.db" if fake else "awaaz.db"))
    cache = TtsCache(settings.cache_dir / ("awaaz_fake" if fake else "awaaz"))
    gate = GnaniGate()          # one Gnani REST request at a time, app-wide
    breaker = CloneBreaker()
    llm = llm or (FakeAwaazLLM() if fake else LLM(settings, purpose="dialogue"))
    embed_fn = fake_embedding if fake else create_voice_embedding
    stt_rest_fn = fake_transcribe if fake else transcribe_rest
    tts_fns = dict(clone_fn=fake_clone_tts, tts_fn=fake_timbre_tts) if fake else {}

    app = FastAPI(title="Apni Awaaz")
    app.state.store = store

    def need_key() -> None:
        if not fake and not settings.gnani_api_key:
            raise HTTPException(503, NO_KEY)

    async def do_speak(text: str, code: str, p: Profile) -> tuple[bytes, dict]:
        need_key()
        try:
            return await speak(text, code, p, settings, llm, cache, gate=gate, breaker=breaker, **tts_fns)
        except ValueError as e:
            raise HTTPException(400, str(e)) from None
        except SpeakError as e:
            log.warning("speak failed: %r", e)
            raise HTTPException(502, "Could not speak right now. Please check the internet connection and try again.") from None

    # ------------------------------------------------------------------ status + profile
    @app.get("/api/health")
    async def health():
        p = store.get()
        return {
            "gnani_key": bool(settings.gnani_api_key),
            "llm_key": bool(settings.groq_api_key or settings.evon_base_url),
            "llm_provider": getattr(llm, "provider", "?"),
            "llm_model": getattr(llm, "model", "?"),
            "stt_mode": settings.stt_mode,
            "fake": fake,
            "clone": breaker.state(),
            "has_voice": bool(p and p.voice),
        }

    @app.get("/api/profile")
    async def get_profile():
        return public_profile(store.get())

    @app.put("/api/profile")
    async def put_profile(body: ProfileIn):
        p = store.get() or Profile()
        p = p.model_copy(update=body.model_dump())
        store.save(p)
        return public_profile(p)

    # ------------------------------------------------------------------ voice bank
    @app.post("/api/voice/clip-check")
    async def clip_check(audio: UploadFile = File(...)):
        x, trimmed = trim_seconds(load_clip(await read_upload(audio)), SAMPLE_RATE)
        q = clip_quality(x, SAMPLE_RATE)
        transcript = language = None
        stt_error = False
        if q["ok"]:  # only spend an STT request on clips that pass the local checks
            p = store.get() or Profile()
            codes = p.language if p.language == "en-IN" else f"{p.language},en-IN"
            names = [n for n in [p.name, *p.family_names] if n]
            try:
                if not fake and not settings.gnani_api_key:
                    raise RuntimeError("no key")
                evt = await gate.run(stt_rest_fn, settings.gnani_api_key, wav_bytes(float_to_pcm16(x), SAMPLE_RATE),
                                     language_code=codes, keyterms=names or None)
                transcript, language = evt.text, evt.language
            except Exception as e:  # the local checks still stand; we just cannot say what was heard
                log.info("clip-check STT failed: %r", e)
                stt_error = True
            q = transcript_check(q, transcript)
        return {**q, "transcript": transcript, "language": language, "trimmed": trimmed, "stt_error": stt_error,
                "filename": audio.filename}

    @app.post("/api/voice/enroll")
    async def enroll(audio: list[UploadFile] | None = File(None), consent: str = Form("")):
        if consent.strip().lower() not in CONSENT_YES:
            raise HTTPException(400, "Consent is required: confirm that this is your own voice, "
                                     "or that the person whose voice it is has agreed.")
        files = audio or []
        if not files:
            raise HTTPException(400, "Add at least one voice note first.")
        if len(files) > MAX_CLIPS:
            raise HTTPException(400, f"Please choose at most {MAX_CLIPS} voice notes.")
        clips, reports = [], []
        for f in files:
            x, trimmed = trim_seconds(load_clip(await read_upload(f)), SAMPLE_RATE)
            clips.append(x)
            reports.append({**clip_quality(x, SAMPLE_RATE), "filename": f.filename, "trimmed": trimmed})
        best = best_clip(reports)
        if best < 0:
            raise HTTPException(422, {"message": "None of these voice notes is clear enough to build a voice.",
                                      "clips": reports})
        need_key()
        try:
            emb = await gate.run(embed_fn, settings.gnani_api_key, wav_bytes(float_to_pcm16(clips[best]), SAMPLE_RATE))
        except Exception as e:
            log.warning("voice embedding failed: %r", e)
            raise HTTPException(502, "We could not build your voice right now. The app keeps working with your "
                                     "chosen standard voice; please try again later.") from None
        old = voice_id((store.get() or Profile()).voice)
        p = store.set_voice(emb, {**reports[best], "clip_index": best})
        p.consent_at = now_iso()
        store.save(p)
        if old and old != voice_id(emb):
            purge_voice_audio(cache, old)  # audio in the replaced voice goes too
        breaker.reset()  # a new voice deserves a fresh try
        return {"profile": public_profile(p), "quality": reports[best], "clips": reports, "chosen": best,
                "test_audio_url": f"/api/voice/test?lang={p.language}&v={voice_id(emb)}"}

    @app.get("/api/voice/test")
    async def voice_test(lang: str | None = None):
        p = store.get() or Profile()
        code = lang if lang in LANGS else p.language
        wav, meta = await do_speak(voice_test_phrase(code), code, p)
        return wav_response(wav, meta)

    @app.delete("/api/voice")
    async def delete_voice():
        vid = store.delete_voice()
        removed = purge_voice_audio(cache, vid)
        return {"deleted": vid is not None, "clips_removed": removed, "profile": public_profile(store.get())}

    # ------------------------------------------------------------------ speaking
    @app.post("/api/speak")
    async def speak_ep(body: SpeakIn):
        p = store.get() or Profile()
        wav, meta = await do_speak(body.text, body.lang, p)
        store.add_phrase_use(meta["spoken_text"], body.lang)
        return wav_response(wav, meta)

    @app.get("/api/phrases")
    async def phrases(lang: str = "hi-IN"):
        if lang not in LANGS:
            raise HTTPException(400, "unsupported language")
        counts = store.phrase_counts(lang)
        uses = dict(counts)
        grid = set(QUICK[lang])
        tiles = [{**t, "uses": uses.get(t["text"], 0)} for t in quick_phrases(lang)]
        frequent = [text for text, n in counts if n >= 2 and text not in grid][:6]
        return {"lang": lang, "quick": tiles, "frequent": frequent}

    @app.post("/api/sos")
    async def sos(body: SosIn | None = None):
        p = store.get() or Profile()
        local = (body.local_lang if body and body.local_lang else None) or p.local_language
        if local not in LANGS:
            raise HTTPException(400, "unsupported language")
        pieces, lines, voices, t = [], [], [], 0.0
        for i, code in enumerate(dict.fromkeys([p.language, local])):
            wav, meta = await do_speak(sos_text(code, p.name, p.family_names), code, p)
            x, hz = read_wav(wav)
            x = resample(x, hz, SAMPLE_RATE) if hz != SAMPLE_RATE else x
            if i:
                pieces.append(np.zeros(int(SOS_GAP_S * SAMPLE_RATE), dtype=np.float32))
                t += SOS_GAP_S
            start = t
            pieces.append(x)
            t += len(x) / SAMPLE_RATE
            lines.append({"lang": code, "text": meta["spoken_text"], "start_s": round(start, 3), "end_s": round(t, 3)})
            voices.append(meta["voice"])
        out = wav_bytes(float_to_pcm16(np.concatenate(pieces)), SAMPLE_RATE)
        meta = {"voice": "clone" if all(v == "clone" for v in voices) else "fallback",
                "voice_name": "own" if all(v == "clone" for v in voices) else p.fallback_voice,
                "spoken_text": " ".join(l["text"] for l in lines)}
        return wav_response(out, meta, {"X-Sos-Lines": quote(json.dumps(lines, ensure_ascii=False))})

    # ------------------------------------------------------------------ live captions
    @app.websocket("/ws/listen")
    async def ws_listen(ws: WebSocket):
        await ws.accept()
        p = store.get() or Profile()
        partner = ws.query_params.get("lang") or p.language
        partner = partner if partner == "auto" or partner in LANGS else p.language
        reply = ws.query_params.get("reply") or p.language
        reply = reply if reply in LANGS else p.language
        lock, alive, holder = asyncio.Lock(), {"v": True}, {}

        async def send_json(m: dict):
            if alive["v"]:
                async with lock:
                    await ws.send_json(m)

        factory = stt_factory
        if factory is None and fake:
            def factory():
                holder["stt"] = ScriptedStt(p.language if partner == "auto" else partner)
                return holder["stt"]
        if factory is None and not settings.gnani_api_key:
            await send_json({"type": "status", "stt": "error", "message": NO_KEY})
            await ws.close()
            return

        sess = ListenSession(send_json, settings, p, stt_factory=factory, llm=llm, store=store,
                             partner_lang=partner, reply_lang=reply, gate=gate)
        try:
            await sess.start()
        except Exception as e:
            log.warning("listen: STT did not start: %r", e)
            await send_json({"type": "status", "stt": "error",
                             "message": "Live captions are not available right now. Please check the internet connection."})
            alive["v"] = False
            await ws.close()
            return
        try:
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    await sess.on_audio(msg["bytes"])
                elif msg.get("text"):
                    try:
                        d = json.loads(msg["text"])
                    except ValueError:
                        continue
                    kind = d.get("type")
                    if kind == "spoken":
                        text = str(d.get("text") or "")[:500]
                        sess.note_spoken(text)
                        if hasattr(holder.get("stt"), "hear_self"):
                            holder["stt"].hear_self(text)  # fake mode: the phone 'hears' itself
                    elif kind == "reply_lang" and d.get("lang") in LANGS:
                        sess.set_reply_lang(d["lang"])
                    elif kind == "stop":
                        break
        except (WebSocketDisconnect, RuntimeError):
            pass
        finally:
            await sess.close()
            alive["v"] = False
            try:
                await ws.close()
            except Exception:
                pass

    dist = frontend_dist()
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")
    return app
