"""Speak text in the user's cloned voice (Gnani vachana-vc-v1), with Timbre fallback and a disk cache."""

from __future__ import annotations

import hashlib
import logging
import unicodedata

from voice_core.audio import wav_bytes
from voice_core.gnani import tts_clone_rest, tts_rest

log = logging.getLogger("awaaz.speak")
RATE = 16000  # speakerphone quality
LANGS = {
    "hi-IN": "Hindi", "en-IN": "English", "ta-IN": "Tamil", "te-IN": "Telugu", "kn-IN": "Kannada",
    "ml-IN": "Malayalam", "bn-IN": "Bengali", "mr-IN": "Marathi", "gu-IN": "Gujarati", "pa-IN": "Punjabi",
}
_SCRIPT_LANGS = {
    "LATIN": {"en-IN"}, "DEVANAGARI": {"hi-IN", "mr-IN"}, "BENGALI": {"bn-IN"}, "TAMIL": {"ta-IN"},
    "TELUGU": {"te-IN"}, "KANNADA": {"kn-IN"}, "MALAYALAM": {"ml-IN"}, "GUJARATI": {"gu-IN"}, "GURMUKHI": {"pa-IN"},
}
_rewrites: dict[tuple[str, str], str] = {}  # ponytail: unbounded in-memory memo, fine for one user


def script_of(text: str) -> str:
    counts: dict[str, int] = {}
    for ch in text:
        if ch.isalpha():
            s = unicodedata.name(ch, "LATIN").split()[0]
            counts[s] = counts.get(s, 0) + 1
    return max(counts, key=counts.get) if counts else "LATIN"


def needs_rewrite(text: str, out_lang: str) -> bool:
    return out_lang not in _SCRIPT_LANGS.get(script_of(text), set())


async def rewrite(text: str, out_lang: str, llm) -> tuple[str, bool]:
    if not needs_rewrite(text, out_lang):
        return text, False
    if (text, out_lang) in _rewrites:
        return _rewrites[(text, out_lang)], True
    lang = LANGS.get(out_lang, out_lang)
    msgs = [{"role": "system", "content": f"Rewrite the user's sentence in {lang}, in its native script. If it is already {lang} "
                                          "in Latin letters, transliterate it; otherwise translate it. Keep names. Output only the sentence."},
            {"role": "user", "content": text}]
    try:
        out = (await llm.complete(msgs, temperature=0.2, max_tokens=160)).strip().strip('"')
    except Exception as e:
        log.warning("rewrite failed: %r", e)
        out = ""
    if not out:
        return text, False
    _rewrites[(text, out_lang)] = out
    return out, True


async def speak(text: str, out_lang: str, profile, settings, llm, cache, *,
                clone_fn=tts_clone_rest, tts_fn=tts_rest) -> tuple[bytes, dict]:
    spoken, translated = await rewrite(text.strip(), out_lang, llm)
    meta = {"voice": "clone", "spoken_text": spoken, "translated": translated}
    if profile and profile.voice:
        emb_id = hashlib.sha1(str(profile.voice.get("embedding", ""))[:4096].encode()).hexdigest()[:12]
        key = cache.key(spoken, clone=emb_id, language=out_lang, sample_rate=RATE)
        pcm = cache.get(key)
        if pcm is None:
            try:
                pcm = await clone_fn(settings.gnani_api_key, spoken, profile.voice, language=out_lang, sample_rate=RATE)
                cache.put(key, pcm)
            except Exception as e:
                log.warning("clone TTS failed, using fallback voice: %r", e)
        if pcm is not None:
            return wav_bytes(pcm, RATE), meta
    voice = profile.fallback_voice if profile else "Shivani"
    kw = dict(voice=voice, model="timbre-v3.0", language=out_lang, sample_rate=RATE)
    key = cache.key(spoken, **kw)
    pcm = cache.get(key)
    if pcm is None:
        pcm = await tts_fn(settings.gnani_api_key, spoken, **kw)
        cache.put(key, pcm)
    return wav_bytes(pcm, RATE), {**meta, "voice": "fallback"}
