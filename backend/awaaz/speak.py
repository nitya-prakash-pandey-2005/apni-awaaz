"""Speak: typed text (any script) -> the user's own voice (Gnani voice cloning, vachana-vc-v1).

1. Cache first: the same sentence in the same voice and language is only ever paid for once.
2. If the text is not in the output language's script (romanised Hindi, or Hindi text spoken in Tamil),
   the LLM rewrites it in that language's native script.
3. Clone TTS with the user's embedding. On any failure, or with no voice yet, a Timbre v3.0 voice the
   user picked speaks instead, and the result says so (the UI shows a "fallback voice" badge).
   A failed clone pauses cloning for a while (CloneBreaker) so every tap is not slowed by a dead API.
All synthesis is 16 kHz WAV (speakerphone quality).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time

from voice_core.audio import wav_bytes
from voice_core.gnani import GnaniError, TtsCache, tts_clone_rest, tts_rest

from .gate import GnaniGate
from .langs import lang, needs_rewrite
from .profiles import Profile, voice_id

log = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CLONE_TIMEOUT_S = 30.0
FALLBACK_MODEL = "timbre-v3.0"
_THINK_RE = re.compile(r"<think>.*?</think>", re.S)
_QUOTES = "\"'“”‘’«»`"


class SpeakError(Exception):
    """Neither the cloned voice nor the fallback voice could speak."""


class CloneBreaker:
    """After a clone failure, skip cloning for a while: 10 minutes for errors that will not fix themselves
    (401/402/403/404: key, credits, scope), 1 minute for anything else (5xx, timeouts, network)."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.down_until = 0.0
        self.last_error: str | None = None

    def available(self) -> bool:
        return self.clock() >= self.down_until

    def trip(self, err: BaseException) -> None:
        secs = 600.0 if getattr(err, "status", None) in (401, 402, 403, 404) else 60.0
        self.down_until = self.clock() + secs
        self.last_error = repr(err)[:300]

    def reset(self) -> None:
        self.down_until, self.last_error = 0.0, None

    def state(self) -> dict:
        wait = max(0.0, self.down_until - self.clock())
        return {"available": wait == 0.0, "retry_in_s": round(wait), "last_error": self.last_error}


default_gate = GnaniGate()
default_breaker = CloneBreaker()


def normalise_text(text: str) -> str:
    return " ".join((text or "").split())


def ensure_wav(data: bytes, hz: int = SAMPLE_RATE) -> bytes:
    """Gnani returns raw PCM16 for container "raw"; pass a WAV through unchanged if one comes back."""
    return data if data[:4] == b"RIFF" else wav_bytes(data, hz)


def voice_tag(profile: Profile, clone: bool) -> str:
    return f"c-{voice_id(profile.voice)}" if clone else f"t-{profile.fallback_voice}"


def cache_key(cache: TtsCache, tag: str, text: str, out_lang: str) -> str:
    return f"{tag}_{cache.key(text, lang=out_lang, sr=SAMPLE_RATE)}"


def _cache_get(cache: TtsCache, key: str) -> tuple[bytes, dict] | None:
    audio = cache.get(key)
    if audio is None:
        return None
    raw = cache.get(key + ".meta")
    try:
        meta = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        meta = {}
    return audio, meta


def _cache_put(cache: TtsCache, key: str, wav: bytes, meta: dict) -> None:
    cache.put(key, wav)
    cache.put(key + ".meta", json.dumps(meta, ensure_ascii=False).encode("utf-8"))


def purge_voice_audio(cache: TtsCache, vid: str | None) -> int:
    """Deletes every cached clip made in the cloned voice `vid` (part of 'delete my voice')."""
    if not vid:
        return 0
    n = 0
    for p in cache.dir.glob(f"c-{vid}_*.bin"):
        p.unlink(missing_ok=True)
        n += 1
    return n


def clean_llm_line(raw: str) -> str:
    text = _THINK_RE.sub("", raw or "")
    line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return line.strip(_QUOTES + " ").strip()[:500]


async def rewrite_text(text: str, out_lang: str, profile: Profile, llm) -> str:
    """Translate or transliterate into the output language's native script (one short LLM call)."""
    L = lang(out_lang)
    names = [n for n in [profile.name, *profile.family_names] if n]
    keep = f" Keep names ({', '.join(names)}) as names." if names else " Keep names as names."
    if L.script == "latin":
        system = f"Translate the user's message into simple spoken English.{keep} Output only the sentence."
    else:
        system = (f"Rewrite the user's message in {L.name}, written in {L.script_name} script. If it is romanised "
                  f"{L.name} (typed in English letters), transliterate it; otherwise translate it into natural "
                  f"spoken {L.name}.{keep} Output only the sentence.")
    raw = await llm.complete([{"role": "system", "content": system}, {"role": "user", "content": text}],
                             temperature=0.2, max_tokens=200)
    return clean_llm_line(raw)


async def _clone(text: str, out_lang: str, embedding: dict, settings, gate: GnaniGate) -> tuple[bytes, str | None]:
    kw = dict(sample_rate=SAMPLE_RATE, container="raw", timeout=CLONE_TIMEOUT_S)
    try:
        return await gate.run(tts_clone_rest, settings.gnani_api_key, text, embedding, language=out_lang, **kw), None
    except GnaniError as e:
        # design call: if cloning rejects the language, let the model pick it from the script instead
        if e.status in (400, 422) and "language" in (e.body or "").lower():
            return await gate.run(tts_clone_rest, settings.gnani_api_key, text, embedding, language=None, **kw), "auto"
        raise


async def speak(text: str, out_lang: str, profile: Profile, settings, llm, cache: TtsCache, *,
                gate: GnaniGate | None = None, breaker: CloneBreaker | None = None) -> tuple[bytes, dict]:
    """Returns (WAV bytes, meta). meta: voice ("clone"|"fallback"), spoken_text, translated, plus
    rewrite, lang, cached, voice_name, reason (why the fallback spoke) and lang_note."""
    text = normalise_text(text)
    if not text:
        raise ValueError("nothing to say")
    lang(out_lang)  # validates
    gate = gate or default_gate
    breaker = breaker or default_breaker

    has_voice = bool(profile.voice)
    try_clone = has_voice and breaker.available()
    reason = None if try_clone else ("no_voice" if not has_voice else "clone_paused")
    clone_key = cache_key(cache, voice_tag(profile, True), text, out_lang) if has_voice else None
    fb_key = cache_key(cache, voice_tag(profile, False), text, out_lang)

    if clone_key:  # anything already said in the user's own voice replays for free, even while cloning is paused
        hit = _cache_get(cache, clone_key)
        if hit:
            return hit[0], {**hit[1], "cached": True}
    if not try_clone:
        hit = _cache_get(cache, fb_key)
        if hit:
            return hit[0], {**hit[1], "cached": True, "reason": reason}

    spoken, translated, mode = text, False, needs_rewrite(text, out_lang)
    if mode:
        try:
            out = await rewrite_text(text, out_lang, profile, llm)
            if out:
                spoken, translated = out, out != text
        except Exception as e:  # the LLM is a nicety here: speak the original text rather than nothing
            log.warning("rewrite failed (%r); speaking the text as typed", e)
    base = {"spoken_text": spoken, "translated": translated, "rewrite": mode if translated else None,
            "lang": out_lang, "cached": False}

    if try_clone:
        try:
            pcm, note = await _clone(spoken, out_lang, profile.voice, settings, gate)
            wav = ensure_wav(pcm)
            meta = {**base, "voice": "clone", "voice_name": "own", "reason": None, "lang_note": note}
            _cache_put(cache, clone_key, wav, meta)
            return wav, meta
        except asyncio.CancelledError:
            raise
        except Exception as e:
            limited = isinstance(e, GnaniError) and e.status == 429
            reason = "rate_limited" if limited else "clone_error"
            if not limited:
                breaker.trip(e)
            log.warning("voice clone failed (%r); using the fallback voice", e)
            hit = _cache_get(cache, fb_key)
            if hit:
                return hit[0], {**hit[1], "cached": True, "reason": reason}

    try:
        pcm = await gate.run(tts_rest, settings.gnani_api_key, spoken, voice=profile.fallback_voice,
                             model=FALLBACK_MODEL, language=out_lang, speed=1.0, sample_rate=SAMPLE_RATE,
                             container="raw")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        raise SpeakError(f"could not speak: {e!r}") from e
    wav = ensure_wav(pcm)
    meta = {**base, "voice": "fallback", "voice_name": profile.fallback_voice, "reason": reason, "lang_note": None}
    _cache_put(cache, fb_key, wav, meta)
    return wav, meta
