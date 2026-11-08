from voice_core.config import Settings
from voice_core.gnani import TtsCache
from voice_core.testing import FakeLLM

from awaaz.profiles import Profile
from awaaz.speak import needs_rewrite, speak

EMB = {"embedding": [0.1, 0.2], "shape": [1, 2], "dtype": "float32"}


class Recorder:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    async def __call__(self, api_key, text, *args, **kw):
        self.calls.append((text, kw))
        if self.fail:
            raise RuntimeError("clone rejected")
        return b"\x01\x00" * 800


def _env(tmp_path):
    return Settings(cache_dir=tmp_path), TtsCache(tmp_path)


def test_needs_rewrite():
    assert needs_rewrite("mujhe paani chahiye", "hi-IN")
    assert not needs_rewrite("मुझे पानी चाहिए", "hi-IN")
    assert not needs_rewrite("I need water", "en-IN")
    assert needs_rewrite("मुझे पानी चाहिए", "ta-IN")


async def test_romanised_hindi_is_rewritten_then_cloned(tmp_path):
    settings, cache = _env(tmp_path)
    llm, clone, tts = FakeLLM(["मुझे पानी चाहिए।"]), Recorder(), Recorder()
    wav, meta = await speak("mujhe paani chahiye", "hi-IN", Profile(voice=EMB), settings, llm, cache,
                            clone_fn=clone, tts_fn=tts)
    assert wav[:4] == b"RIFF" and len(llm.calls) == 1
    assert meta == {"voice": "clone", "spoken_text": "मुझे पानी चाहिए।", "translated": True}
    assert clone.calls[0][0] == "मुझे पानी चाहिए।" and not tts.calls


async def test_clone_failure_falls_back_to_timbre(tmp_path):
    settings, cache = _env(tmp_path)
    clone, tts = Recorder(fail=True), Recorder()
    _, meta = await speak("नमस्ते", "hi-IN", Profile(voice=EMB, fallback_voice="Lakshmi"), settings, FakeLLM(), cache,
                          clone_fn=clone, tts_fn=tts)
    assert meta["voice"] == "fallback" and tts.calls[0][1]["voice"] == "Lakshmi"


async def test_no_voice_uses_fallback(tmp_path):
    settings, cache = _env(tmp_path)
    clone, tts = Recorder(), Recorder()
    _, meta = await speak("hello", "en-IN", None, settings, FakeLLM(), cache, clone_fn=clone, tts_fn=tts)
    assert meta["voice"] == "fallback" and not clone.calls and meta["translated"] is False


async def test_cache_hit_skips_second_tts(tmp_path):
    settings, cache = _env(tmp_path)
    clone = Recorder()
    for _ in range(2):
        await speak("नमस्ते", "hi-IN", Profile(voice=EMB), settings, FakeLLM(), cache, clone_fn=clone, tts_fn=Recorder())
    assert len(clone.calls) == 1
