"""Conversation mode: live captions of the partner (Prisma stream) and 3 suggested replies from the LLM."""

from __future__ import annotations

import asyncio
import json
import logging
import time

from voice_core.gnani import PrismaStream
from voice_core.llm import parse_json_loose
from voice_core.turns import TurnBasedStt, is_echo, is_meaningful
from voice_core.types import Turn

from .phrases import default_phrases
from .speak import LANGS

log = logging.getLogger("awaaz.converse")
RATE = 16000


def _replies(text: str) -> list[str] | None:
    try:
        obj = parse_json_loose(text).get("replies")
    except ValueError:
        try:
            obj = json.loads(text)
        except ValueError:
            return None
    if not (isinstance(obj, list) and len(obj) == 3 and all(isinstance(x, str) and x.strip() for x in obj)):
        return None
    items = [x.strip() for x in obj]
    return items if all(len(x.split()) <= 8 for x in items) else None


async def suggest(llm, profile, history: list[Turn], store) -> list[str]:
    lang = LANGS.get(profile.language, "Hindi")
    about = f"{profile.name or 'The user'} cannot speak" + (f" ({profile.condition})" if profile.condition else "")
    family = f" Family: {', '.join(profile.family_names)}." if profile.family_names else ""
    system = (f"{about} and talks by tapping replies.{family} Suggest exactly 3 different short replies they may want "
              f"to say next, in {lang} in its native script, at most 8 words each. "
              'Output only JSON: {"replies": ["...", "...", "..."]}')
    convo = "\n".join(f"{'Me' if t.speaker == 'user' else 'Them'}: {t.text}" for t in history[-6:])
    try:
        out = await llm.complete([{"role": "system", "content": system}, {"role": "user", "content": convo or "(start)"}],
                                 temperature=0.6, max_tokens=160, json_mode=True)
        items = _replies(out)
    except Exception as e:
        log.warning("suggest failed: %r", e)
        items = None
    if items:
        return items
    pool = store.top_phrases(profile.language) + default_phrases(profile.language)
    return list(dict.fromkeys(pool))[:3]


class ListenSession:
    """Binary PCM16 at 16 kHz in; {"type": "caption"} and {"type": "suggestions"} out."""

    def __init__(self, send_json, settings, profile, llm, store, stt_factory=None):
        self.send_json, self.settings, self.profile, self.llm, self.store = send_json, settings, profile, llm, store
        self.stt_factory = stt_factory or self._default_stt
        self.history: list[Turn] = []
        self.spoken: list[str] = []
        self.t0 = time.monotonic()
        self.stt = None
        self._tasks: list[asyncio.Task] = []
        self._suggest: asyncio.Task | None = None

    def _default_stt(self):
        keyterms = [x for x in [self.profile.name, *self.profile.family_names] if x]
        kw = dict(sample_rate=RATE, keyterms=keyterms or None)
        if self.settings.stt_mode == "turn":
            return TurnBasedStt(self.settings.gnani_api_key, language_code=",".join(dict.fromkeys([self.profile.language, "en-IN"])), **kw)
        return PrismaStream(self.settings.gnani_api_key, language_code="indic-auto", **kw)

    async def start(self) -> None:
        self.stt = self.stt_factory()
        await self.stt.connect()
        self._tasks.append(asyncio.create_task(self._loop()))

    async def on_audio(self, pcm16: bytes) -> None:
        if self.stt:
            await self.stt.send_audio(pcm16)

    def note_spoken(self, text: str) -> None:
        self.spoken = [*self.spoken, text][-2:]
        self.history.append(Turn("user", text, time.monotonic() - self.t0))

    async def _loop(self) -> None:
        # ponytail: no STT reconnect; the user taps the mic again. Reuse VoiceAgentSession's backoff if drops are common.
        async for e in self.stt.events():
            if e.type in ("connected", "error", "closed"):
                await self.send_json({"type": "status", "stt": e.type})
            if e.type != "transcript" or not is_meaningful(e.text) or is_echo(e.text, self.spoken):
                continue
            turn = Turn("partner", e.text, round(time.monotonic() - self.t0, 2), e.language)
            self.history.append(turn)
            await self.send_json({"type": "caption", "text": turn.text, "lang": turn.lang, "t": turn.t})
            if self._suggest and not self._suggest.done():
                self._suggest.cancel()
            self._suggest = asyncio.create_task(self._send_suggestions())

    async def _send_suggestions(self) -> None:
        items = await suggest(self.llm, self.profile, self.history, self.store)
        await self.send_json({"type": "suggestions", "items": items})

    async def close(self) -> None:
        if self.stt:
            await self.stt.close()
        for t in [*self._tasks, self._suggest]:
            if t and not t.done():
                t.cancel()
