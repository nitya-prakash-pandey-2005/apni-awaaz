"""AWAAZ_FAKE=1: run the whole app with no API keys (UI work, demos on bad networks, CI).

- voice embedding: a deterministic fake vector derived from the clip
- Prisma REST: a canned Hindi transcript whose length follows the clip
- clone TTS and Timbre: soft tone "speech" at 16 kHz (the clone hums lower than the fallback voice,
  so you can hear which one spoke); AWAAZ_FAKE_CLONE=fail makes cloning fail to show the fallback path
- LLM: a tiny transliteration table plus the built-in phrase tables for translation, and scripted replies
- Prisma streaming: a scripted nurse who speaks every few seconds; the app's own speech is "heard" back
  a moment later, so the echo guard visibly drops it
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import itertools
import json
import os
import re

import numpy as np

from voice_core.audio import float_to_pcm16, read_wav
from voice_core.gnani import GnaniError, SttEvent

from .phrases import QUICK

FAKE_RATE = 16000

NURSE_LINES = {
    "hi-IN": [
        "नमस्ते, आज आप कैसा महसूस कर रहे हैं?",
        "दर्द कहाँ हो रहा है, गले में या सीने में?",
        "आपने सुबह की दवाई ली थी?",
        "क्या आपको पानी चाहिए?",
        "ठीक है, मैं डॉक्टर साहब को बुलाती हूँ।",
        "आपके बेटे का फ़ोन आया था, वो शाम को आएँगे।",
    ],
    "en-IN": [
        "Good morning, how are you feeling today?",
        "Where does it hurt, in your throat or your chest?",
        "Did you take your morning medicine?",
        "Would you like some water?",
        "Okay, I will call the doctor.",
        "Your son called, he will come in the evening.",
    ],
}

REPLIES = {
    "Hindi": [
        ["आज थोड़ा बेहतर लग रहा है", "गले में दर्द है", "रात को नींद नहीं आई"],
        ["गले में दर्द है", "निगलने में दर्द होता है", "दर्द पहले से कम है"],
        ["हाँ, ले ली", "नहीं, अभी नहीं", "कौन सी दवाई?"],
        ["हाँ, थोड़ा पानी", "नहीं, अभी नहीं", "गुनगुना पानी चाहिए"],
        ["धन्यवाद", "कितनी देर लगेगी?", "ठीक है"],
        ["अच्छी ख़बर है", "उन्हें खाना लाने को कहिए", "धन्यवाद"],
    ],
    "English": [
        ["A little better today", "My throat hurts", "I could not sleep"],
        ["In my throat", "It hurts to swallow", "The pain is less now"],
        ["Yes, I took it", "No, not yet", "Which medicine?"],
        ["Yes, a little water", "No, not now", "Warm water, please"],
        ["Thank you", "How long will it take?", "Okay"],
        ["That is good news", "Ask him to bring food", "Thank you"],
    ],
    "Tamil": [
        ["இன்று கொஞ்சம் பரவாயில்லை", "தொண்டை வலிக்கிறது", "இரவு தூக்கம் வரவில்லை"],
        ["தொண்டையில் வலி", "விழுங்கும்போது வலிக்கிறது", "வலி கொஞ்சம் குறைவு"],
        ["ஆம், சாப்பிட்டேன்", "இல்லை, இன்னும் இல்லை", "எந்த மருந்து?"],
        ["ஆம், கொஞ்சம் தண்ணீர்", "இல்லை, இப்போது வேண்டாம்", "வெந்நீர் வேண்டும்"],
        ["நன்றி", "எவ்வளவு நேரம் ஆகும்?", "சரி"],
        ["நல்ல செய்தி", "சாப்பாடு கொண்டு வரச் சொல்லுங்கள்", "நன்றி"],
    ],
}

TRANSLIT = {
    "mujhe paani chahiye": "मुझे पानी चाहिए",
    "mujhe dard ho raha hai": "मुझे दर्द हो रहा है",
    "gale mein dard hai": "गले में दर्द है",
    "main theek hoon": "मैं ठीक हूँ",
    "dhanyavaad": "धन्यवाद",
    "shukriya": "शुक्रिया",
    "mera beta kab aayega": "मेरा बेटा कब आएगा?",
}

_SAMPLE_TRANSCRIPT = ("नमस्ते, ये मेरी आवाज़ का एक छोटा सा नमूना है ताकि ये ऐप बाद में मेरी आवाज़ में बोल सके। "
                      "आज मौसम अच्छा है और घर में सब ठीक हैं। शाम को हम सब साथ में चाय पीते हैं, "
                      "पुराने गाने सुनते हैं और बहुत सारी बातें करते हैं। बच्चे स्कूल की कहानियाँ सुनाते हैं।").split()


def _norm(text: str) -> str:
    return re.sub(r"[^\w\s]", "", (text or "").lower()).strip()


# ---------------------------------------------------------------- Gnani REST fakes

async def fake_embedding(api_key: str, wav: bytes, **kw) -> dict:
    await asyncio.sleep(0.3)
    seed = int(hashlib.sha1(wav).hexdigest()[:8], 16)
    vec = np.random.default_rng(seed).standard_normal(768).astype("<f4")
    return {"embedding": base64.b64encode(vec.tobytes()).decode("ascii"), "shape": [1, 768], "dtype": "float32"}


async def fake_transcribe(api_key: str, wav: bytes, *, language_code: str = "hi-IN", **kw) -> SttEvent:
    await asyncio.sleep(0.2)
    x, hz = read_wav(wav)
    n = max(4, min(len(_SAMPLE_TRANSCRIPT), int(len(x) / hz * 2.2)))
    return SttEvent("transcript", text=" ".join(_SAMPLE_TRANSCRIPT[:n]), language="hi-IN", latency_ms=180.0)


def _tone(text: str, f0: float, hz: int = FAKE_RATE) -> bytes:
    """Soft syllable-paced hum whose length follows the text (stands in for speech)."""
    secs = min(6.0, 0.07 * len(text) + 0.35)
    t = np.arange(int(secs * hz)) / hz
    voice = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in (1, 2, 3)) / 1.8
    syll = 0.55 + 0.45 * np.abs(np.sin(np.pi * t * 4.2))
    fade = np.minimum(1.0, np.minimum(t, secs - t) * 10)
    return float_to_pcm16((0.12 * voice * syll * fade).astype(np.float32))


async def fake_clone_tts(api_key: str, text: str, embedding: dict, *, sample_rate: int = FAKE_RATE, **kw) -> bytes:
    await asyncio.sleep(0.15)
    if os.environ.get("AWAAZ_FAKE_CLONE") == "fail":
        raise GnaniError(403, '{"error": "SCOPE_NOT_ALLOWED (fake)"}')
    return _tone(text, 150.0, sample_rate)


async def fake_timbre_tts(api_key: str, text: str, *, sample_rate: int = FAKE_RATE, **kw) -> bytes:
    await asyncio.sleep(0.15)
    return _tone(text, 235.0, sample_rate)


# ---------------------------------------------------------------- LLM fake

class FakeAwaazLLM:
    provider = "fake"
    model = "fake"

    async def complete(self, messages, **kw) -> str:
        await asyncio.sleep(0.05)
        system, user = messages[0]["content"], messages[-1]["content"]
        if '"replies"' in system:
            return self._replies(system, user)
        return self._rewrite(system, user)

    @staticmethod
    def _replies(system: str, convo: str) -> str:
        last = next((ln[len("Them: "):] for ln in reversed(convo.splitlines()) if ln.startswith("Them: ")), "")
        idx = next((i for lines in NURSE_LINES.values() for i, l in enumerate(lines) if _norm(l) == _norm(last)), None)
        table = next((REPLIES[name] for name in REPLIES if f"next, in {name}" in system), None)
        if idx is None or table is None:
            return "{}"  # the app then offers the user's own frequent phrases
        return json.dumps({"replies": table[idx]}, ensure_ascii=False)

    @staticmethod
    def _rewrite(system: str, text: str) -> str:
        m = re.search(r"message in (\w+)|into simple spoken (\w+)", system)
        name = (m.group(1) or m.group(2)) if m else ""
        target = next((code for code, n in _LANG_NAMES.items() if n == name), None)
        hit = TRANSLIT.get(_norm(text))
        if hit and target == "hi-IN":
            return hit
        source = hit or text
        for code, texts in QUICK.items():  # translate a built-in phrase through the phrase tables
            if source in texts and target in QUICK:
                return QUICK[target][texts.index(source)]
        return text


_LANG_NAMES = {"hi-IN": "Hindi", "en-IN": "English", "ta-IN": "Tamil", "bn-IN": "Bengali", "te-IN": "Telugu",
               "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "gu-IN": "Gujarati", "pa-IN": "Punjabi"}


# ---------------------------------------------------------------- Prisma streaming fake

class ScriptedStt:
    """Ignores the microphone; 'hears' the next nurse line every `every` seconds (the first after `first`).
    hear_self(text) makes it 'hear' the app's own speech shortly after, like a phone speaker would."""

    def __init__(self, lang: str = "hi-IN", every: float = 7.0, first: float = 1.5):
        self.lines = NURSE_LINES.get(lang, NURSE_LINES["hi-IN"])
        self.lang = lang if lang in NURSE_LINES else "hi-IN"
        self.every, self.first = every, first
        self.connected = False
        self.sent = 0
        self._closed = asyncio.Event()
        self._q: asyncio.Queue[SttEvent] = asyncio.Queue()

    async def connect(self):
        self.connected = True

    async def send_audio(self, pcm16: bytes):
        self.sent += len(pcm16)

    async def commit(self):
        pass

    def hear_self(self, text: str) -> None:
        async def later():
            await asyncio.sleep(0.8)
            await self._q.put(SttEvent("transcript", text=text, language=self.lang, latency_ms=150.0))

        asyncio.get_running_loop().create_task(later())

    async def _wait(self, secs: float) -> bool:
        """Sleeps up to `secs`, returning early with queued echo events. True when closed."""
        try:
            await asyncio.wait_for(self._closed.wait(), timeout=secs)
            return True
        except asyncio.TimeoutError:
            return False

    async def events(self):
        yield SttEvent("connected")
        delay = self.first
        for line in itertools.cycle(self.lines):
            end = asyncio.get_running_loop().time() + delay
            while True:
                left = end - asyncio.get_running_loop().time()
                if left <= 0:
                    break
                if await self._wait(min(left, 0.1)):
                    yield SttEvent("closed")
                    return
                while not self._q.empty():
                    yield self._q.get_nowait()
            yield SttEvent("speech_start")
            if await self._wait(1.0):
                break
            yield SttEvent("transcript", text=line, language=self.lang, latency_ms=170.0)
            delay = self.every
        yield SttEvent("closed")

    async def close(self):
        self.connected = False
        self._closed.set()
