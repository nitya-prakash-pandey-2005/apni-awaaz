"""Suggested replies when the LLM fails, the speech-to-text choice, cancelling stale suggestions, and phrase lists."""

import asyncio
import json

from voice_core.config import Settings
from voice_core.gnani import PrismaStream
from voice_core.testing import FakeLLM, FakeStt, ev
from voice_core.turns import TurnBasedStt
from voice_core.types import Turn

from awaaz import phrases
from awaaz.converse import ListenSession, _replies, suggest
from awaaz.fake_mode import FakeAwaazLLM
from awaaz.phrases import PHRASES, SOS, TEST, default_phrases, sos_text
from awaaz.profiles import Profile, ProfileStore
from awaaz.speak import LANGS

PROFILE = Profile(name="Asha", language="hi-IN", family_names=["Ravi"], condition="after a stroke")
GOOD = json.dumps({"replies": ["हाँ", "थोड़ा पानी", "धन्यवाद"]})


class BrokenLLM:
    async def complete(self, messages, **kw):
        raise RuntimeError("LLM down")


async def test_llm_down_gives_the_users_own_phrases_first(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    store.add_phrase_use("मुझे पानी चाहिए", "hi-IN")
    store.add_phrase_use("हाँ", "hi-IN")  # also a built-in phrase: must not appear twice
    items = await suggest(BrokenLLM(), PROFILE, [], store)
    assert items == ["मुझे पानी चाहिए", "हाँ", "नहीं"]


async def test_suggest_prompt_carries_who_the_user_is():
    llm = FakeLLM([GOOD])
    history = [Turn("partner", "दर्द है?", 1.0), Turn("user", "हाँ", 2.0)]
    assert await suggest(llm, PROFILE, history, None) == ["हाँ", "थोड़ा पानी", "धन्यवाद"]
    system, convo = llm.calls[0][0]["content"], llm.calls[0][1]["content"]
    assert "Asha cannot speak (after a stroke)" in system and "Family: Ravi." in system and "in Hindi" in system
    assert convo == "Them: दर्द है?\nMe: हाँ"


def test_replies_parsing_rules():
    assert _replies('{"replies": [" हाँ ", "नहीं", "पानी"]}') == ["हाँ", "नहीं", "पानी"]
    assert _replies('["हाँ", "नहीं", "पानी"]') == ["हाँ", "नहीं", "पानी"]  # a bare list is accepted
    assert _replies('{"replies": ["हाँ", " ", "पानी"]}') is None  # blank reply
    assert _replies('{"replies": ["हाँ", 2, "पानी"]}') is None  # not text
    assert _replies("not json") is None


def test_default_stt_follows_the_stt_mode():
    def stt_for(mode):
        s = ListenSession(None, Settings(gnani_api_key="k", stt_mode=mode), PROFILE, None, None)
        return s._default_stt()

    turn = stt_for("turn")
    assert isinstance(turn, TurnBasedStt)
    assert turn.language_code == "hi-IN,en-IN" and turn.keyterms == ["Asha", "Ravi"] and turn.sample_rate == 16000
    assert isinstance(stt_for("stream"), PrismaStream)


async def test_a_new_caption_cancels_the_stale_suggestion(tmp_path):
    sent = []

    class SlowFirstLLM:
        def __init__(self):
            self.prompts = []

        async def complete(self, messages, **kw):
            self.prompts.append(messages[1]["content"])
            if len(self.prompts) == 1:
                await asyncio.sleep(5)  # cancelled long before this ends
            return GOOD

    async def send_json(m):
        sent.append(m)

    llm = SlowFirstLLM()
    events = [ev("connected"), ev("transcript", "क्या आपको दर्द है?", "hi-IN"), ev("transcript", "पानी चाहिए?", "hi-IN")]
    s = ListenSession(send_json, Settings(), PROFILE, llm, ProfileStore(tmp_path / "p.db"),
                      stt_factory=lambda: FakeStt(events, gap=0.05))
    await s.start()
    for _ in range(200):
        if any(m["type"] == "suggestions" for m in sent):
            break
        await asyncio.sleep(0.01)
    await asyncio.sleep(0.05)
    await s.close()
    assert [m["type"] for m in sent] == ["status", "caption", "caption", "suggestions"]
    assert "पानी चाहिए?" in llm.prompts[-1]


async def test_audio_is_forwarded_to_the_stt_stream(tmp_path):
    stt = FakeStt([ev("connected")])

    async def send_json(m):
        pass

    s = ListenSession(send_json, Settings(), PROFILE, FakeLLM(), ProfileStore(tmp_path / "p.db"), stt_factory=lambda: stt)
    await s.on_audio(b"\x00\x00" * 10)  # before start(): ignored, no stream yet
    await s.start()
    await s.on_audio(b"\x00\x00" * 160)
    await s.close()
    assert stt.sent == 320


def test_phrase_lists_fall_back_to_english():
    assert default_phrases("kn-IN") == PHRASES["en-IN"]
    assert sos_text("gu-IN") == SOS["en-IN"] and phrases.test_phrase("pa-IN") == TEST["en-IN"]
    assert default_phrases("ta-IN")[0] == "ஆமாம்"


def test_phrase_tables_are_complete():
    assert set(PHRASES) <= set(LANGS) and set(PHRASES) == set(SOS) == set(TEST)
    assert all(len(v) == 12 and len(set(v)) == 12 for v in PHRASES.values())


async def test_fake_llm_suggests_in_the_asked_language():
    llm = FakeAwaazLLM()
    system = "Asha cannot speak and talks by tapping replies. Suggest exactly 3 different short replies, in Tamil in its native script"
    first = json.loads(await llm.complete([{"role": "system", "content": system}, {"role": "user", "content": "(start)"}]))["replies"]
    again = json.loads(await llm.complete([{"role": "system", "content": system}, {"role": "user", "content": "(start)"}]))["replies"]
    assert first == PHRASES["ta-IN"][:3] and again == PHRASES["ta-IN"][3:6]
    rewrite = [{"role": "system", "content": "Rewrite the user's sentence in Hindi"}, {"role": "user", "content": "paani"}]
    assert await llm.complete(rewrite) == "paani"
