import asyncio
import json

from voice_core.config import Settings
from voice_core.testing import FakeLLM, FakeStt, ev

from awaaz.converse import ListenSession, parse_replies, suggest
from awaaz.profiles import Profile, ProfileStore
from voice_core.types import Turn

PROFILE = Profile(name="Asha", language="hi-IN", family_names=["Ravi"], condition="throat cancer surgery")
GOOD = json.dumps({"replies": ["गले में दर्द है", "थोड़ा कम है", "दवा कब मिलेगी?"]}, ensure_ascii=False)


class Sink:
    def __init__(self):
        self.msgs: list[dict] = []

    async def __call__(self, m: dict):
        self.msgs.append(m)

    def of(self, type_: str) -> list[dict]:
        return [m for m in self.msgs if m["type"] == type_]


async def run_session(events, llm, *, spoken=(), store=None, **kw):
    sink = Sink()
    stt = FakeStt(events)
    s = ListenSession(sink, Settings(), PROFILE, stt_factory=lambda: stt, llm=llm, store=store, **kw)
    for line in spoken:
        s.note_spoken(line)
    await s.start()
    await asyncio.sleep(0.05)
    await s.wait_idle()
    await s.close()
    return s, sink, stt


async def test_normal_transcript_gives_a_caption_and_three_suggestions():
    llm = FakeLLM([GOOD])
    s, sink, _ = await run_session([ev("connected"), ev("transcript", "दर्द कहाँ हो रहा है?", "hi-IN")], llm)
    caps = sink.of("caption")
    assert len(caps) == 1
    assert caps[0]["text"] == "दर्द कहाँ हो रहा है?" and caps[0]["lang"] == "hi-IN" and caps[0]["t"] >= 0
    sug = sink.of("suggestions")
    assert len(sug) == 1 and sug[0]["items"] == ["गले में दर्द है", "थोड़ा कम है", "दवा कब मिलेगी?"]
    assert sug[0]["for"] == caps[0]["id"]
    assert sink.msgs.index(caps[0]) < sink.msgs.index(sug[0])
    assert sink.of("status")[0]["stt"] == "connected"
    # the LLM saw the conversation and was asked for Hindi in Devanagari
    system, user = llm.calls[0][0]["content"], llm.calls[0][1]["content"]
    assert "Hindi" in system and "Devanagari" in system and "8 words" in system and "Asha" in system
    assert user.endswith("Them: दर्द कहाँ हो रहा है?")
    assert s.history[-1].speaker == "partner"


async def test_echo_of_my_own_speech_is_dropped():
    llm = FakeLLM([GOOD])
    _, sink, _ = await run_session([ev("transcript", "मुझे पानी चाहिए।", "hi-IN")], llm, spoken=["मुझे पानी चाहिए"])
    assert sink.of("caption") == [] and sink.of("suggestions") == []
    assert sink.of("echo_ignored")[0]["text"] == "मुझे पानी चाहिए।"
    assert llm.calls == []


async def test_echo_guard_only_checks_the_last_two_spoken_lines():
    _, sink, _ = await run_session([ev("transcript", "मुझे पानी चाहिए", "hi-IN")], FakeLLM([GOOD]),
                                   spoken=["मुझे पानी चाहिए", "धन्यवाद", "हाँ"])
    assert len(sink.of("caption")) == 1


async def test_noise_transcripts_are_dropped():
    _, sink, _ = await run_session([ev("transcript", "", "hi-IN"), ev("transcript", "।", "hi-IN")], FakeLLM([GOOD]))
    assert sink.of("caption") == []


async def test_bad_json_gives_the_defaults_from_top_phrases(tmp_path):
    store = ProfileStore(tmp_path / "a.db")
    store.add_phrase_use("मुझे पानी चाहिए", "hi-IN")
    _, sink, _ = await run_session([ev("transcript", "आप कैसे हैं?", "hi-IN")], FakeLLM(["sorry, I cannot"]), store=store)
    assert sink.of("suggestions")[0]["items"] == ["मुझे पानी चाहिए", "हाँ", "नहीं"]


async def test_suggest_directly_with_bad_json_and_no_store():
    items = await suggest(FakeLLM(["{not json"]), PROFILE, [Turn("partner", "नमस्ते", 0.0)])
    assert items == ["हाँ", "नहीं", "एक मिनट रुकिए, मुझे लिखने दीजिए"]


async def test_suggest_survives_llm_errors_and_uses_last_six_turns():
    class Broken:
        async def complete(self, *a, **k):
            raise RuntimeError("429 from Groq")

    assert len(await suggest(Broken(), PROFILE, [])) == 3
    llm = FakeLLM([GOOD])
    history = [Turn("partner" if i % 2 else "me", f"line {i}", float(i)) for i in range(10)]
    await suggest(llm, PROFILE, history)
    user = llm.calls[0][1]["content"]
    assert "line 3" not in user and "line 4" in user and "line 9" in user and user.count("\n") == 5


async def test_suggestions_follow_the_reply_language():
    llm = FakeLLM([json.dumps({"replies": ["ஆம்", "இல்லை", "நன்றி"]}, ensure_ascii=False)])
    _, sink, _ = await run_session([ev("transcript", "दर्द है?", "hi-IN")], llm, reply_lang="ta-IN")
    assert "Tamil" in llm.calls[0][0]["content"]
    assert sink.of("suggestions")[0]["items"] == ["ஆம்", "இல்லை", "நன்றி"]


def test_parse_replies_variants():
    assert parse_replies('["a", "b", "c"]') == ["a", "b", "c"]
    assert parse_replies('<think>hmm</think>{"replies": [" a ", "a", "", "b"]}') == ["a", "b"]
    assert parse_replies('{"suggestions": ["x"]}') == ["x"]
    assert parse_replies('{"replies": ["one two three four five six seven eight nine ten"]}') == [
        "one two three four five six seven eight"]
    assert parse_replies("no json") is None
    assert parse_replies('{"replies": "nope"}') is None


async def test_partial_replies_are_topped_up_to_three():
    items = await suggest(FakeLLM(['{"replies": ["गले में दर्द है"]}']), PROFILE, [])
    assert items == ["गले में दर्द है", "हाँ", "नहीं"]


async def test_note_spoken_joins_the_history():
    s = ListenSession(Sink(), Settings(), PROFILE, stt_factory=lambda: FakeStt([]), llm=FakeLLM())
    s.note_spoken("  गले में दर्द है ")
    assert s.history[-1].speaker == "me" and s.history[-1].text == "गले में दर्द है"


async def test_stream_settings_use_one_locale_at_16k():
    s = ListenSession(Sink(), Settings(gnani_api_key="k"), PROFILE.model_copy(update={"family_names": ["रवि"]}))
    stt = s.default_stt()
    assert stt.headers["language_code"] == "hi-IN" and stt.headers["x-sample-rate"] == "16000"
    assert stt.headers["format"] == "codemix"
    assert stt.headers["keyterms"].isascii() and "Asha" in stt.headers["keyterms"]
    auto = ListenSession(Sink(), Settings(gnani_api_key="k"), PROFILE, partner_lang="auto").default_stt()
    assert auto.headers["language_code"] == "indic-auto"


async def test_turn_mode_shares_the_gnani_gate():
    from awaaz.gate import GnaniGate

    gate = GnaniGate()
    s = ListenSession(Sink(), Settings(gnani_api_key="k", stt_mode="turn"), PROFILE, gate=gate)
    stt = s.default_stt()
    assert stt.busy is gate.lock and stt.sample_rate == 16000


async def test_stream_drop_reconnects():
    sink = Sink()
    streams = [FakeStt([ev("connected")], end="close"), FakeStt([ev("connected"), ev("transcript", "फिर से नमस्ते", "hi-IN")])]
    s = ListenSession(sink, Settings(), PROFILE, stt_factory=lambda: streams.pop(0), llm=FakeLLM([GOOD]),
                      reconnect_delays=(0.01,))
    await s.start()
    await asyncio.sleep(0.1)
    await s.wait_idle()
    await s.close()
    stt_states = [m["stt"] for m in sink.of("status")]
    assert "reconnecting" in stt_states and stt_states[-1] == "connected"
    assert sink.of("caption")[0]["text"] == "फिर से नमस्ते"


async def test_audio_is_forwarded_to_the_stream():
    stt = FakeStt([ev("connected")])
    s = ListenSession(Sink(), Settings(), PROFILE, stt_factory=lambda: stt, llm=FakeLLM())
    await s.on_audio(b"\x00" * 1024)  # before start: ignored
    await s.start()
    await s.on_audio(b"\x00" * 1024)
    await s.close()
    assert stt.sent == 1024
