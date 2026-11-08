import asyncio
import json

from voice_core.config import Settings
from voice_core.testing import FakeLLM, FakeStt, ev

from awaaz.converse import ListenSession, suggest
from awaaz.phrases import default_phrases
from awaaz.profiles import Profile, ProfileStore

PROFILE = Profile(name="Asha", language="hi-IN", family_names=["Ravi"])
GOOD = json.dumps({"replies": ["हाँ, दर्द है", "थोड़ा पानी दीजिए", "धन्यवाद"]})


async def _run(events, llm, tmp_path):
    sent = []

    async def send_json(m):
        sent.append(m)

    s = ListenSession(send_json, Settings(), PROFILE, llm, ProfileStore(tmp_path / "p.db"), stt_factory=lambda: FakeStt(events))
    s.note_spoken("मुझे पानी चाहिए")
    await s.start()
    for _ in range(100):
        if any(m["type"] == "suggestions" for m in sent):
            break
        await asyncio.sleep(0.01)
    await s.close()
    return sent


async def test_echo_dropped_partner_captioned_with_suggestions(tmp_path):
    sent = await _run([ev("connected"), ev("transcript", "मुझे पानी चाहिए", "hi-IN"),
                       ev("transcript", "क्या आपको दर्द हो रहा है?", "hi-IN")], FakeLLM([GOOD]), tmp_path)
    caps = [m for m in sent if m["type"] == "caption"]
    assert [c["text"] for c in caps] == ["क्या आपको दर्द हो रहा है?"] and caps[0]["lang"] == "hi-IN"
    sug = next(m for m in sent if m["type"] == "suggestions")
    assert sug["items"] == ["हाँ, दर्द है", "थोड़ा पानी दीजिए", "धन्यवाद"]


async def test_suggest_bad_json_gives_defaults(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    store.add_phrase_use("मुझे घर जाना है", "hi-IN")
    items = await suggest(FakeLLM(["sorry, no json"]), PROFILE, [], store)
    assert items == ["मुझे घर जाना है", *default_phrases("hi-IN")[:2]]


async def test_suggest_rejects_wrong_count_and_long_replies(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    two = json.dumps({"replies": ["हाँ", "नहीं"]})
    long = json.dumps({"replies": ["a b c d e f g h i j", "हाँ", "नहीं"]})
    for reply in (two, long):
        assert await suggest(FakeLLM([reply]), PROFILE, [], store) == default_phrases("hi-IN")[:3]


async def test_suggest_prompt_is_small(tmp_path):
    from voice_core.types import Turn
    llm = FakeLLM([GOOD])
    history = [Turn("partner", f"line {i}", float(i)) for i in range(20)]
    await suggest(llm, PROFILE, history, ProfileStore(tmp_path / "p.db"))
    user = llm.calls[0][-1]["content"]
    assert "line 19" in user and "line 13" not in user
