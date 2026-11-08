"""Conversation mode: live captions of the other person (Prisma streaming STT at 16 kHz) and three
suggested replies after every caption, so the user can answer with one tap.

The phone also hears its own speech. Every line the app speaks is passed to note_spoken(); a transcript
that matches one of the last two spoken lines is dropped (voice_core.turns.is_echo).
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import re
import time
from typing import Awaitable, Callable

from voice_core.gnani import PrismaStream, SttEvent
from voice_core.llm import LLM, parse_json_loose
from voice_core.turns import TurnBasedStt, is_echo, is_meaningful
from voice_core.types import Turn

from .gate import GnaniGate
from .langs import lang
from .phrases import default_replies
from .profiles import Profile

log = logging.getLogger(__name__)
SendJson = Callable[[dict], Awaitable[None]]

STT_SAMPLE_RATE = 16000
HISTORY_TURNS = 6          # Groq free tier is ~8k tokens/minute: keep prompts short
MAX_WORDS = 8
SUGGEST_TIMEOUT_S = 6.0
_THINK_RE = re.compile(r"<think>.*?</think>", re.S)
_ARRAY_RE = re.compile(r"\[[^\[\]]*\]", re.S)
_QUOTES = "\"'“”‘’`"


def parse_replies(raw: str) -> list[str] | None:
    """Replies from an LLM answer: {"replies": [...]} (or any list in the object) or a bare JSON array.
    Cleans, de-duplicates and cuts each reply to 8 words. None when there is no list at all."""
    text = _THINK_RE.sub("", raw or "")
    items = None
    try:
        obj = parse_json_loose(text)
        items = obj.get("replies") or obj.get("suggestions")
        if items is None:
            items = next((v for v in obj.values() if isinstance(v, list)), None)
    except ValueError:
        m = _ARRAY_RE.search(text)
        if m:
            try:
                items = json.loads(m.group(0))
            except ValueError:
                items = None
    if not isinstance(items, list):
        return None
    out: list[str] = []
    for it in items:
        if not isinstance(it, str):
            continue
        words = it.strip().strip(_QUOTES).split()
        reply = " ".join(words[:MAX_WORDS])
        if reply and reply not in out:
            out.append(reply)
    return out


def suggest_messages(profile: Profile, history: list[Turn]) -> list[dict]:
    L = lang(profile.language)
    script = f", written in {L.script_name} script" if L.script != "latin" else ""
    who = profile.name.strip() or "the user"
    cond = f" ({profile.condition.strip()})" if profile.condition.strip() else ""
    fam = f" Family: {', '.join(profile.family_names)}." if profile.family_names else ""
    system = (f"You suggest replies for {who}, who cannot speak{cond} and answers by tapping one of your suggestions. "
              f"Write exactly 3 different short replies, at most {MAX_WORDS} words each, that {who} might want to say "
              f"next, in {L.name}{script}. Vary them: a direct answer, a detail, a question or request.{fam} "
              'Reply with JSON only: {"replies": ["...", "...", "..."]}')
    convo = "\n".join(f"{'Them' if t.speaker == 'partner' else 'Me'}: {t.text}" for t in history[-HISTORY_TURNS:])
    return [{"role": "system", "content": system}, {"role": "user", "content": convo or "(the conversation is starting)"}]


async def suggest(llm, profile: Profile, history: list[Turn], *, store=None) -> list[str]:
    """Exactly 3 replies (each at most 8 words) in profile.language. Invalid or missing LLM output is
    replaced by defaults: the user's most used phrases, then yes / no / one minute."""
    defaults = default_replies(profile.language, store, n=3)
    try:
        raw = await asyncio.wait_for(
            llm.complete(suggest_messages(profile, history), temperature=0.6, max_tokens=160, json_mode=True),
            SUGGEST_TIMEOUT_S)
        items = parse_replies(raw) or []
    except asyncio.CancelledError:
        raise
    except Exception as e:
        log.warning("suggest failed: %r", e)
        items = []
    for d in defaults:
        if len(items) >= 3:
            break
        if d not in items:
            items.append(d)
    return items[:3]


class ListenSession:
    """One conversation. Feed it the microphone (PCM16 mono 16 kHz) with on_audio(); it sends
    {"type": "caption", "id", "text", "lang", "t"} and then {"type": "suggestions", "for", "items"},
    plus {"type": "status", "stt"}, {"type": "hearing", "on"} and {"type": "echo_ignored", "text"}."""

    def __init__(self, send_json: SendJson, settings, profile: Profile, stt_factory=None, *, llm=None, store=None,
                 partner_lang: str | None = None, reply_lang: str | None = None, gate: GnaniGate | None = None,
                 reconnect_delays: tuple[float, ...] = (0.5, 1, 2, 4, 8)):
        self.send_json = send_json
        self.settings = settings
        self.profile = profile
        self.stt_factory = stt_factory or self.default_stt
        self.llm = llm
        self.store = store
        self.partner_lang = partner_lang or profile.language   # "auto" = Prisma's indic-auto
        self.reply_lang = reply_lang or profile.language
        self.gate = gate
        self.reconnect_delays = reconnect_delays
        self.history: list[Turn] = []
        self._spoken: list[str] = []
        self._ids = itertools.count(1)
        self._t0 = time.monotonic()
        self._stt = None
        self._stt_task: asyncio.Task | None = None
        self._suggest_task: asyncio.Task | None = None
        self._closing = False

    # ------------------------------------------------------------------ setup
    def stt_language_code(self) -> str:
        return "indic-auto" if self.partner_lang == "auto" else lang(self.partner_lang).code

    def default_stt(self):
        names = [n for n in [self.profile.name, *self.profile.family_names] if n and n.strip()]
        kw = dict(language_code=self.stt_language_code(), sample_rate=STT_SAMPLE_RATE, fmt="codemix",
                  keyterms=names or None)
        if self.settings.stt_mode == "turn":
            stt = TurnBasedStt(self.settings.gnani_api_key, **kw)
            if self.gate is not None:
                stt.busy = self.gate.lock  # its REST calls queue behind ours: one Gnani request at a time
            return stt
        return PrismaStream(self.settings.gnani_api_key, vad={"x-min-silence-ms": "500"}, **kw)

    def _llm(self):
        if self.llm is None:
            self.llm = LLM(self.settings, purpose="dialogue")
        return self.llm

    def now(self) -> float:
        return time.monotonic() - self._t0

    # ------------------------------------------------------------------ lifecycle
    async def start(self) -> None:
        self._t0 = time.monotonic()
        await self._open()

    async def _open(self) -> None:
        stt = self.stt_factory()
        await stt.connect()
        self._stt = stt
        self._stt_task = asyncio.create_task(self._loop(stt))

    async def close(self) -> None:
        self._closing = True
        for t in (self._suggest_task, self._stt_task):
            if t and not t.done():
                t.cancel()
        if self._stt is not None:
            try:
                await self._stt.close()
            except Exception:
                pass

    async def wait_idle(self, timeout: float = 3.0) -> None:
        """For tests: wait for a pending suggestion."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            t = self._suggest_task
            if t is None or t.done():
                return
            await asyncio.sleep(0.01)

    # ------------------------------------------------------------------ input
    async def on_audio(self, pcm16: bytes) -> None:
        stt = self._stt
        if self._closing or stt is None or not getattr(stt, "connected", False):
            return
        try:
            await stt.send_audio(pcm16)
        except Exception as e:  # the socket died; the loop notices and reconnects
            log.info("send_audio failed: %r", e)

    def note_spoken(self, text: str) -> None:
        text = " ".join((text or "").split())
        if not text:
            return
        self._spoken = (self._spoken + [text])[-5:]
        self.history.append(Turn("me", text, round(self.now(), 2), self.reply_lang))

    def set_reply_lang(self, code: str) -> None:
        self.reply_lang = lang(code).code

    # ------------------------------------------------------------------ STT
    async def _loop(self, stt) -> None:
        try:
            async for ev in stt.events():
                if ev.type == "closed":
                    break
                await self._on_event(ev)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.warning("stt loop error: %r", e)
        if not self._closing:
            await self._reconnect()

    async def _reconnect(self) -> None:
        await self._send({"type": "status", "stt": "reconnecting"})
        for delay in self.reconnect_delays:
            await asyncio.sleep(delay)
            if self._closing:
                return
            try:
                await self._open()
                await self._send({"type": "status", "stt": "connected"})
                return
            except Exception as e:
                log.info("stt reconnect failed: %r", e)
        await self._send({"type": "status", "stt": "error", "message": "Live captions are not available right now."})

    async def _on_event(self, ev: SttEvent) -> None:
        if ev.type == "connected":
            await self._send({"type": "status", "stt": "connected"})
        elif ev.type in ("speech_start", "processing"):
            await self._send({"type": "hearing", "on": True})
        elif ev.type == "transcript":
            await self._send({"type": "hearing", "on": False})
            await self._on_transcript(ev)
        elif ev.type == "error":
            log.info("stt error event: %s", ev.raw)

    async def _on_transcript(self, ev: SttEvent) -> None:
        text = (ev.text or "").strip()
        if not is_meaningful(text):
            return
        if is_echo(text, self._spoken):
            await self._send({"type": "echo_ignored", "text": text})
            return
        turn = Turn("partner", text, round(self.now(), 2), ev.language or self.stt_language_code(), ev.latency_ms)
        self.history.append(turn)
        cid = next(self._ids)
        await self._send({"type": "caption", "id": cid, "text": text, "lang": turn.lang, "t": turn.t})
        if self._suggest_task and not self._suggest_task.done():
            self._suggest_task.cancel()  # only the newest caption needs replies
        self._suggest_task = asyncio.create_task(self._suggestions(cid))

    async def _suggestions(self, cid: int) -> None:
        profile = self.profile.model_copy(update={"language": self.reply_lang})
        items = await suggest(self._llm(), profile, list(self.history), store=self.store)
        await self._send({"type": "suggestions", "for": cid, "items": items, "lang": self.reply_lang})

    async def _send(self, msg: dict) -> None:
        try:
            await self.send_json(msg)
        except Exception as e:
            log.info("send_json failed: %r", e)
