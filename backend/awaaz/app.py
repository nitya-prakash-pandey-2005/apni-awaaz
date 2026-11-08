"""FastAPI app: profile, voice enrolment (with consent), speak, SOS and the live-captions WebSocket.

Run:  bash run_backend.sh            (port 8767)
No keys:  FAKE=1 bash run_backend.sh   (tones instead of speech, a scripted nurse)
"""

from __future__ import annotations

import json
import logging
import os
from urllib.parse import quote

import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from voice_core.audio import float_to_pcm16, read_wav, wav_bytes
from voice_core.config import Settings, get_settings, repo_root
from voice_core.gnani import TtsCache, create_voice_embedding, transcribe_rest, tts_clone_rest, tts_rest
from voice_core.llm import LLM
from voice_core.turns import is_meaningful

from . import fake_mode
from .converse import ListenSession
from .phrases import default_phrases, sos_text, test_phrase
from .profiles import Profile, ProfileStore
from .quality import clip_quality
from .speak import LANGS, RATE, speak

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("awaaz")
MAX_CLIP_S = 30  # Gnani voice cloning takes 5-30 s of reference audio


class ProfileIn(BaseModel):
    name: str = ""
    language: str = "hi-IN"
    family_names: list[str] = []
    condition: str = ""
    fallback_voice: str = "Shivani"


class SpeakIn(BaseModel):
    text: str
    lang: str = "hi-IN"
    remember: bool = True  # count it for phrase learning


class SosIn(BaseModel):
    local_lang: str | None = None


def public(p: Profile) -> dict:
    d = p.model_dump(exclude={"voice"})
    return {**d, "has_voice": p.voice is not None}


def create_app(settings: Settings | None = None, *, llm=None, stt_factory=None) -> FastAPI:
    settings = settings or get_settings()
    fake = os.environ.get("AWAAZ_FAKE") == "1"
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    store = ProfileStore(settings.cache_dir / ("awaaz_fake.db" if fake else "awaaz.db"))
    cache = TtsCache(settings.cache_dir / ("fake" if fake else ""))
    llm = llm or (fake_mode.FakeAwaazLLM() if fake else LLM(settings))
    if fake:
        clone_fn = tts_fn = fake_mode.tone_pcm
        embed_fn, transcribe_fn = fake_mode.fake_embedding, fake_mode.fake_transcribe
        stt_factory = stt_factory or fake_mode.ScriptedStt
    else:
        clone_fn, tts_fn, embed_fn, transcribe_fn = tts_clone_rest, tts_rest, create_voice_embedding, transcribe_rest
    live: set[ListenSession] = set()
    rewrites: dict = {}  # ponytail: unbounded in-memory memo of LLM rewrites, fine for one user
    app = FastAPI(title="Apni Awaaz")

    def profile() -> Profile:
        return store.get() or Profile()

    def check_lang(lang: str) -> str:
        if lang not in LANGS:
            raise HTTPException(400, f"unsupported language {lang}")
        return lang

    async def wav_in(request: Request) -> tuple[np.ndarray, int]:
        try:
            return read_wav(await request.body())
        except Exception:
            raise HTTPException(400, "send a 16-bit PCM WAV body") from None

    async def say(text: str, lang: str) -> tuple[bytes, dict]:
        wav, meta = await speak(text, lang, profile(), settings, llm, cache, clone_fn=clone_fn, tts_fn=tts_fn, memo=rewrites)
        for s in live:
            s.note_spoken(meta["spoken_text"])  # echo guard: captions of our own speech are dropped
        return wav, meta

    @app.get("/api/health")
    async def health():
        return {"gnani_key": bool(settings.gnani_api_key), "llm_key": bool(settings.groq_api_key or settings.evon_base_url),
                "llm_provider": settings.llm_provider, "stt_mode": settings.stt_mode, "fake": fake,
                "has_voice": profile().voice is not None}

    @app.get("/api/profile")
    async def get_profile():
        return public(profile())

    @app.put("/api/profile")
    async def put_profile(body: ProfileIn):
        check_lang(body.language)
        return public(store.save(profile().model_copy(update=body.model_dump())))

    @app.post("/api/voice/clip-check")
    async def clip_check(request: Request):
        x, hz = await wav_in(request)
        q = clip_quality(x, hz)
        try:
            ev = await transcribe_fn(settings.gnani_api_key, wav_bytes(float_to_pcm16(x[: MAX_CLIP_S * hz]), hz),
                                     language_code=",".join(dict.fromkeys([profile().language, "en-IN"])))
            q["text"], q["lang"] = ev.text, ev.language
            if not is_meaningful(ev.text):
                q["ok"], q["reasons"] = False, [*q["reasons"], "no clear speech"]
        except Exception as e:
            log.warning("clip transcript failed: %r", e)
            q["text"] = q["lang"] = None
        return q

    @app.post("/api/voice/enroll")
    async def enroll(request: Request, consent: bool = False):
        if not consent:
            raise HTTPException(400, "consent=true is required: clone only your own voice, or with the speaker's permission")
        x, hz = await wav_in(request)
        q = clip_quality(x, hz)
        if not q["ok"]:
            raise HTTPException(422, {"message": "clip quality too low", "quality": q})
        try:
            emb = await embed_fn(settings.gnani_api_key, wav_bytes(float_to_pcm16(x[: MAX_CLIP_S * hz]), hz))
        except Exception as e:
            log.warning("voice cloning failed: %r", e)
            raise HTTPException(502, f"voice cloning failed, the fallback voice stays on: {e}") from None
        p = store.set_voice(emb, q)
        return {"profile": public(p), "test_text": test_phrase(p.language)}

    @app.delete("/api/voice")
    async def delete_voice():
        return public(store.delete_voice())

    @app.post("/api/speak")
    async def speak_route(body: SpeakIn):
        if not body.text.strip():
            raise HTTPException(400, "text is empty")
        lang = check_lang(body.lang)
        try:
            wav, meta = await say(body.text, lang)
        except Exception as e:
            log.warning("speak failed: %r", e)
            raise HTTPException(502, f"speech failed: {e}") from None
        if body.remember:
            store.add_phrase_use(body.text, lang)
        return Response(wav, media_type="audio/wav", headers={
            "X-Voice": meta["voice"], "X-Spoken-Text": quote(meta["spoken_text"]), "X-Translated": str(meta["translated"]).lower()})

    @app.get("/api/phrases")
    async def phrases(lang: str = "hi-IN"):
        return list(dict.fromkeys(store.top_phrases(check_lang(lang), 6) + default_phrases(lang)))[:12]

    @app.post("/api/sos")
    async def sos(body: SosIn):
        p = profile()
        langs = list(dict.fromkeys([p.language, check_lang(body.local_lang or p.language)]))
        parts, texts, voices = [], [], set()
        for lang in langs:
            wav, meta = await say(sos_text(lang), lang)
            parts += [read_wav(wav)[0], np.zeros(int(0.6 * RATE), np.float32)]
            texts.append(meta["spoken_text"])
            voices.add(meta["voice"])
        out = wav_bytes(float_to_pcm16(np.concatenate(parts)), RATE)
        return Response(out, media_type="audio/wav", headers={
            "X-Voice": "clone" if voices == {"clone"} else "fallback",
            "X-Spoken-Text": quote(json.dumps(texts, ensure_ascii=False))})

    @app.websocket("/ws/listen")
    async def ws_listen(ws: WebSocket):
        await ws.accept()

        async def send_json(m: dict):
            try:
                await ws.send_json(m)
            except Exception:
                pass

        sess = ListenSession(send_json, settings, profile(), llm, store, stt_factory=stt_factory)
        live.add(sess)
        try:
            await sess.start()
            while True:
                msg = await ws.receive()
                if msg.get("type") == "websocket.disconnect":
                    break
                if msg.get("bytes"):
                    await sess.on_audio(msg["bytes"])
        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception as e:
            log.warning("listen session failed: %r", e)
            await send_json({"type": "status", "stt": "error", "message": str(e)})
        finally:
            live.discard(sess)
            await sess.close()

    dist = repo_root() / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=str(dist), html=True), name="web")
    return app
