import asyncio

import pytest

from voice_core.audio import read_wav
from voice_core.config import Settings
from voice_core.gnani import GnaniError, TtsCache
from voice_core.testing import FakeLLM

import awaaz.speak as speak_mod
from awaaz.gate import GnaniGate
from awaaz.langs import dominant_script, needs_rewrite
from awaaz.profiles import Profile, voice_id
from awaaz.speak import CloneBreaker, SpeakError, purge_voice_audio, speak

EMB = {"embedding": "ZmFrZS1lbWJlZGRpbmc=", "shape": [1, 768], "dtype": "float32"}
PCM = b"\x01\x00" * 1600  # 0.1 s of 16 kHz PCM16


class FakeRest:
    """Stands in for tts_clone_rest / tts_rest: records calls; raises the queued errors first."""

    def __init__(self, errors=()):
        self.calls: list[dict] = []
        self.errors = list(errors)

    async def __call__(self, api_key, text, *args, **kw):
        self.calls.append({"text": text, "args": args, **kw})
        await asyncio.sleep(0)
        if self.errors:
            raise self.errors.pop(0)
        return PCM


@pytest.fixture
def env(tmp_path, monkeypatch):
    clone, timbre = FakeRest(), FakeRest()
    monkeypatch.setattr(speak_mod, "tts_clone_rest", clone)
    monkeypatch.setattr(speak_mod, "tts_rest", timbre)
    ns = type("Env", (), {})()
    ns.clone, ns.timbre = clone, timbre
    ns.settings = Settings(gnani_api_key="k", cache_dir=tmp_path)
    ns.cache = TtsCache(tmp_path / "awaaz")
    ns.profile = Profile(name="Asha", language="hi-IN", family_names=["Ravi"], voice=EMB)
    ns.kw = dict(gate=GnaniGate(backoff=(0, 0)), breaker=CloneBreaker())
    return ns


def test_dominant_script_and_rewrite_rules():
    assert dominant_script("mujhe paani chahiye") == "latin"
    assert dominant_script("मुझे doctor चाहिए") == "deva"
    assert dominant_script("எனக்கு தண்ணீர் வேண்டும்") == "taml"
    assert dominant_script("123 ?!") is None
    assert needs_rewrite("mujhe paani chahiye", "hi-IN") == "transliterate"
    assert needs_rewrite("मुझे पानी चाहिए", "hi-IN") is None
    assert needs_rewrite("मला पाणी हवे", "mr-IN") is None  # Marathi shares Devanagari
    assert needs_rewrite("मुझे पानी चाहिए", "ta-IN") == "translate"
    assert needs_rewrite("मुझे पानी चाहिए", "en-IN") == "translate"
    assert needs_rewrite("I need water", "en-IN") is None
    assert needs_rewrite("108", "ta-IN") is None


async def test_romanised_hindi_is_transliterated_once_then_spoken_in_my_voice(env):
    llm = FakeLLM(["मुझे पानी चाहिए"])
    wav, meta = await speak("mujhe paani chahiye", "hi-IN", env.profile, env.settings, llm, env.cache, **env.kw)
    assert len(llm.calls) == 1
    prompt = llm.calls[0][0]["content"]
    assert "Hindi" in prompt and "Devanagari" in prompt and "Ravi" in prompt
    assert llm.calls[0][-1]["content"] == "mujhe paani chahiye"
    assert meta["spoken_text"] == "मुझे पानी चाहिए" and meta["translated"] is True
    assert meta["voice"] == "clone" and meta["rewrite"] == "transliterate"
    assert env.clone.calls[0]["text"] == "मुझे पानी चाहिए"
    assert env.clone.calls[0]["args"][0] == EMB
    assert env.clone.calls[0]["language"] == "hi-IN" and env.clone.calls[0]["sample_rate"] == 16000
    assert env.timbre.calls == []
    x, hz = read_wav(wav)
    assert hz == 16000 and len(x) == len(PCM) // 2


async def test_native_script_needs_no_llm(env):
    llm = FakeLLM(["should not be used"])
    _, meta = await speak("मुझे पानी चाहिए", "hi-IN", env.profile, env.settings, llm, env.cache, **env.kw)
    assert llm.calls == [] and meta["spoken_text"] == "मुझे पानी चाहिए" and meta["translated"] is False


async def test_cross_language_translates_to_tamil(env):
    llm = FakeLLM(["“எனக்கு தண்ணீர் வேண்டும்”\n"])
    _, meta = await speak("मुझे पानी चाहिए", "ta-IN", env.profile, env.settings, llm, env.cache, **env.kw)
    assert "Tamil" in llm.calls[0][0]["content"]
    assert meta["spoken_text"] == "எனக்கு தண்ணீர் வேண்டும்"  # quotes and newline cleaned
    assert env.clone.calls[0]["language"] == "ta-IN"


async def test_clone_failure_falls_back_to_timbre_and_pauses_cloning(env):
    env.clone.errors = [GnaniError(503, "busy")]
    wav, meta = await speak("नमस्ते", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta["voice"] == "fallback" and meta["reason"] == "clone_error" and meta["voice_name"] == "Shivani"
    assert env.timbre.calls[0]["voice"] == "Shivani" and env.timbre.calls[0]["model"] == "timbre-v3.0"
    assert env.timbre.calls[0]["language"] == "hi-IN" and env.timbre.calls[0]["sample_rate"] == 16000
    assert read_wav(wav)[1] == 16000
    # the breaker skips cloning for a while instead of waiting for it to fail on every tap
    _, meta2 = await speak("धन्यवाद", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta2["voice"] == "fallback" and meta2["reason"] == "clone_paused"
    assert len(env.clone.calls) == 1


async def test_timeout_style_errors_also_fall_back(env):
    env.clone.errors = [TimeoutError("read timeout")]
    _, meta = await speak("नमस्ते", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta["voice"] == "fallback"


async def test_no_voice_uses_fallback_without_calling_clone(env):
    p = env.profile.model_copy(update={"voice": None, "fallback_voice": "Avinash"})
    _, meta = await speak("नमस्ते", "hi-IN", p, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta["voice"] == "fallback" and meta["reason"] == "no_voice" and meta["voice_name"] == "Avinash"
    assert env.clone.calls == [] and env.timbre.calls[0]["voice"] == "Avinash"


async def test_cache_hit_makes_no_second_tts_or_llm_call(env):
    llm = FakeLLM(["मुझे पानी चाहिए"])
    wav1, m1 = await speak("mujhe paani chahiye", "hi-IN", env.profile, env.settings, llm, env.cache, **env.kw)
    wav2, m2 = await speak("  mujhe   paani chahiye ", "hi-IN", env.profile, env.settings, llm, env.cache, **env.kw)
    assert wav1 == wav2 and len(env.clone.calls) == 1 and len(llm.calls) == 1
    assert m1["cached"] is False and m2["cached"] is True
    assert m2["spoken_text"] == "मुझे पानी चाहिए" and m2["voice"] == "clone" and m2["translated"] is True
    # another language or another voice is a different cache entry
    await speak("mujhe paani chahiye", "mr-IN", env.profile, env.settings, FakeLLM(["मला पाणी हवे"]), env.cache, **env.kw)
    assert len(env.clone.calls) == 2


async def test_rate_limit_is_retried_by_the_gate(env):
    env.clone.errors = [GnaniError(429, "RATE_LIMITED"), GnaniError(429, "RATE_LIMITED")]
    _, meta = await speak("नमस्ते", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta["voice"] == "clone" and len(env.clone.calls) == 3


async def test_rejected_language_retries_without_language(env):
    env.clone.errors = [GnaniError(400, '{"error": "unsupported language"}')]
    _, meta = await speak("ਮੈਨੂੰ ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ", "pa-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    assert meta["voice"] == "clone" and meta["lang_note"] == "auto"
    assert env.clone.calls[0]["language"] == "pa-IN" and env.clone.calls[1]["language"] is None


async def test_llm_failure_speaks_the_original_text(env):
    class BrokenLLM:
        async def complete(self, *a, **k):
            raise RuntimeError("groq down")

    _, meta = await speak("mujhe paani chahiye", "hi-IN", env.profile, env.settings, BrokenLLM(), env.cache, **env.kw)
    assert meta["spoken_text"] == "mujhe paani chahiye" and meta["translated"] is False and meta["voice"] == "clone"


async def test_both_voices_failing_raises(env):
    env.clone.errors = [GnaniError(500, "x")]
    env.timbre.errors = [GnaniError(500, "y")]
    with pytest.raises(SpeakError):
        await speak("नमस्ते", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)


async def test_empty_text_and_unknown_language_are_rejected(env):
    with pytest.raises(ValueError):
        await speak("   ", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    with pytest.raises(ValueError):
        await speak("hello", "xx-YY", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)


async def test_purge_voice_audio_removes_only_that_voice(env):
    await speak("नमस्ते", "hi-IN", env.profile, env.settings, FakeLLM(), env.cache, **env.kw)
    other = env.profile.model_copy(update={"voice": None})
    await speak("नमस्ते", "hi-IN", other, env.settings, FakeLLM(), env.cache, **env.kw)
    before = sorted(p.name for p in env.cache.dir.iterdir())
    assert len(before) == 4  # audio + meta for each voice
    assert purge_voice_audio(env.cache, voice_id(EMB)) == 2
    after = sorted(p.name for p in env.cache.dir.iterdir())
    assert len(after) == 2 and all(n.startswith("t-Shivani_") for n in after)


async def test_gate_runs_one_request_at_a_time():
    gate, active, peak = GnaniGate(), [0], [0]

    async def job():
        active[0] += 1
        peak[0] = max(peak[0], active[0])
        await asyncio.sleep(0.01)
        active[0] -= 1
        return "ok"

    assert await asyncio.gather(*[gate.run(job) for _ in range(5)]) == ["ok"] * 5
    assert peak[0] == 1


async def test_gate_gives_up_after_retries():
    calls = []

    async def always_429():
        calls.append(1)
        raise GnaniError(429, "RATE_LIMITED")

    with pytest.raises(GnaniError):
        await GnaniGate(retries=2, backoff=(0, 0)).run(always_429)
    assert len(calls) == 3
