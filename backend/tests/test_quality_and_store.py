"""Voice-note quality edge cases and the profile store's consent, deletion and persistence behaviour."""

from datetime import datetime

import numpy as np

from awaaz.profiles import Profile, ProfileStore
from awaaz.quality import best_clip, clip_quality

HZ = 16000
EMB = {"embedding": [0.1, 0.2], "shape": [1, 2], "dtype": "float32"}


def _speechy(seconds: float) -> np.ndarray:
    t = np.arange(int(seconds * HZ)) / HZ
    gate = (np.sin(2 * np.pi * 0.5 * t) > -0.3).astype(np.float32)
    noise = 0.001 * np.random.default_rng(0).standard_normal(len(t))
    return (0.3 * np.sin(2 * np.pi * 180 * t) * gate + noise).astype(np.float32)


def test_int16_input_is_judged_like_float_input():
    x = _speechy(10)
    as_int16 = (x * 32767).astype(np.int16)
    a, b = clip_quality(x, HZ), clip_quality(as_int16, HZ)
    assert a["ok"] and b["ok"] and abs(a["snr_db"] - b["snr_db"]) < 0.5 and a["speech_s"] == b["speech_s"]


def test_more_than_30_s_of_speech_is_too_long():
    q = clip_quality(_speechy(60), HZ)  # about 60 % of it is voiced
    assert q["speech_s"] > 30 and "too long" in q["reasons"] and not q["ok"]


def test_silence_and_empty_input_fail_without_crashing():
    silent = clip_quality(np.zeros(10 * HZ, np.float32), HZ)
    assert not silent["ok"] and {"too short", "noisy"} <= set(silent["reasons"])
    empty = clip_quality(np.zeros(0, np.float32), HZ)
    assert not empty["ok"] and empty["duration_s"] == 0 and empty["clipping_pct"] == 0


def test_best_clip_is_minus_one_when_nothing_passed():
    assert best_clip([{"ok": False, "snr_db": 40}, {"ok": False, "snr_db": 30}]) == -1
    assert best_clip([]) == -1


def test_set_voice_records_consent_and_delete_clears_it(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    store.save(Profile(name="Asha", language="ta-IN"))
    p = store.set_voice(EMB, {"snr_db": 31.0, "ok": True})
    assert p.voice == EMB and p.voice_meta["snr_db"] == 31.0 and p.name == "Asha"
    consent = datetime.fromisoformat(p.consent_at)
    assert consent.utcoffset().total_seconds() == 0  # stored in UTC
    gone = store.delete_voice()
    assert gone.voice is None and gone.voice_meta is None and gone.consent_at is None
    assert gone.name == "Asha" and gone.language == "ta-IN"  # only the voice and its consent go


def test_profile_and_phrases_survive_a_restart(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    store.set_voice(EMB, {"ok": True})
    store.add_phrase_use("  पानी  ", "hi-IN")
    store.add_message("hello", "audio/wav", b"RIFF")
    store.db.close()
    again = ProfileStore(tmp_path / "p.db")
    assert again.get().voice == EMB
    assert again.top_phrases("hi-IN") == ["पानी"]  # stored trimmed
    assert [m["label"] for m in again.list_messages()] == ["hello"]


def test_phrase_counts_are_per_language_and_ordered_by_use(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    for text, lang, n in [("water", "en-IN", 1), ("help", "en-IN", 3), ("पानी", "hi-IN", 5)]:
        for _ in range(n):
            store.add_phrase_use(text, lang)
    assert store.top_phrases("en-IN") == ["help", "water"]
    assert store.top_phrases("en-IN", n=1) == ["help"]
    assert store.top_phrases("ta-IN") == []


def test_set_voice_without_a_saved_profile_starts_from_defaults(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    assert store.get() is None
    p = store.set_voice(EMB, {"ok": True})
    assert p.language == "hi-IN" and p.fallback_voice == "Shivani" and store.get().voice == EMB


def test_messages_are_listed_in_order_and_deleted_one_by_one(tmp_path):
    store = ProfileStore(tmp_path / "p.db")
    a = store.add_message("first", "audio/webm", b"a")
    b = store.add_message("second", "audio/wav", b"b")
    assert [m["label"] for m in store.list_messages()] == ["first", "second"]
    assert store.message_audio(b["id"]) == ("audio/wav", b"b")
    store.delete_message(a["id"])
    assert [m["id"] for m in store.list_messages()] == [b["id"]] and store.message_audio(a["id"]) is None
