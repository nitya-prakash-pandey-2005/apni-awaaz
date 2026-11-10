"""speak() and rewrite() when things go wrong: LLM down or empty, fallback voice failing, separate caches."""

import pytest
from voice_core.config import Settings
from voice_core.gnani import TtsCache
from voice_core.testing import FakeLLM

from awaaz.profiles import Profile
from awaaz.speak import needs_rewrite, rewrite, script_of, speak

EMB = {"embedding": [0.1, 0.2], "shape": [1, 2], "dtype": "float32"}


class Recorder:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    async def __call__(self, api_key, text, *args, **kw):
        self.calls.append((text, kw))
        if self.fail:
            raise RuntimeError("TTS down")
        return b"\x01\x00" * 800


class BrokenLLM:
    def __init__(self):
        self.calls = 0

    async def complete(self, messages, **kw):
        self.calls += 1
        raise RuntimeError("LLM down")


def test_script_of_picks_the_dominant_script():
    assert script_of("मुझे water चाहिए") == "DEVANAGARI"
    assert script_of("வணக்கம்") == "TAMIL"
    assert script_of("123 !?") == "LATIN"  # no letters: treated as Latin
    assert script_of("") == "LATIN"


def test_needs_rewrite_for_scripts_no_language_uses():
    assert not needs_rewrite("मला पाणी हवे", "mr-IN")  # Marathi is written in Devanagari too
    assert needs_rewrite("مرحبا", "hi-IN")  # Arabic script maps to no supported language


async def test_llm_failure_speaks_the_original_text_and_is_not_memoised():
    llm, memo = BrokenLLM(), {}
    assert await rewrite("mujhe paani chahiye", "hi-IN", llm, memo) == ("mujhe paani chahiye", False)
    await rewrite("mujhe paani chahiye", "hi-IN", llm, memo)
    assert llm.calls == 2 and memo == {}  # a failure is retried next time, not cached


async def test_empty_llm_answer_speaks_the_original_text():
    assert await rewrite("mujhe paani chahiye", "hi-IN", FakeLLM([""])) == ("mujhe paani chahiye", False)


async def test_rewrite_is_memoised_and_quotes_are_stripped():
    llm, memo = FakeLLM(['"मुझे पानी चाहिए"']), {}
    assert await rewrite("mujhe paani chahiye", "hi-IN", llm, memo) == ("मुझे पानी चाहिए", True)
    assert await rewrite("mujhe paani chahiye", "hi-IN", llm, memo) == ("मुझे पानी चाहिए", True)
    assert len(llm.calls) == 1


async def test_rewrite_prompt_names_the_output_language():
    llm = FakeLLM(["எனக்கு தண்ணீர் வேண்டும்"])
    await rewrite("I need water", "ta-IN", llm)
    assert "in Tamil" in llm.calls[0][0]["content"] and llm.calls[0][1]["content"] == "I need water"


async def test_fallback_voice_failure_is_raised_for_the_route_to_report(tmp_path):
    with pytest.raises(RuntimeError, match="TTS down"):
        await speak("नमस्ते", "hi-IN", Profile(voice=EMB), Settings(cache_dir=tmp_path), FakeLLM(), TtsCache(tmp_path),
                    clone_fn=Recorder(fail=True), tts_fn=Recorder(fail=True))


async def test_clone_audio_goes_only_to_the_clone_cache(tmp_path):
    cache, clone_cache = TtsCache(tmp_path / "shared"), TtsCache(tmp_path / "clone")
    _, meta = await speak("नमस्ते", "hi-IN", Profile(voice=EMB), Settings(cache_dir=tmp_path), FakeLLM(), cache,
                          clone_cache=clone_cache, clone_fn=Recorder(), tts_fn=Recorder())
    assert meta["voice"] == "clone"
    assert len(list(clone_cache.dir.iterdir())) == 1 and not list(cache.dir.iterdir())


async def test_a_failed_clone_is_retried_next_time_while_the_fallback_is_cached(tmp_path):
    clone, tts = Recorder(fail=True), Recorder()
    for _ in range(2):
        _, meta = await speak("नमस्ते", "hi-IN", Profile(voice=EMB), Settings(cache_dir=tmp_path), FakeLLM(), TtsCache(tmp_path),
                              clone_fn=clone, tts_fn=tts)
        assert meta["voice"] == "fallback"
    assert len(clone.calls) == 2 and len(tts.calls) == 1


async def test_different_voices_never_share_cached_audio(tmp_path):
    clone = Recorder()
    other = {"embedding": [0.9, 0.8], "shape": [1, 2], "dtype": "float32"}
    for emb in (EMB, other):
        await speak("नमस्ते", "hi-IN", Profile(voice=emb), Settings(cache_dir=tmp_path), FakeLLM(), TtsCache(tmp_path),
                    clone_fn=clone, tts_fn=Recorder())
    assert len(clone.calls) == 2


async def test_fallback_uses_timbre_in_the_requested_language(tmp_path):
    tts = Recorder()
    await speak("வணக்கம்", "ta-IN", Profile(fallback_voice="Kalpana"), Settings(cache_dir=tmp_path), FakeLLM(), TtsCache(tmp_path),
                clone_fn=Recorder(), tts_fn=tts)
    kw = tts.calls[0][1]
    assert kw["voice"] == "Kalpana" and kw["language"] == "ta-IN" and kw["model"] == "timbre-v3.0" and kw["sample_rate"] == 16000
