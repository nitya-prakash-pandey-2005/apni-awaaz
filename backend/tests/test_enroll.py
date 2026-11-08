import numpy as np

from awaaz.profiles import Profile, ProfileStore, voice_id
from awaaz.quality import best_clip, clip_quality, transcript_check, trim_seconds

HZ = 16000


def test_clean_speechlike_clip_is_ok(speechlike):
    q = clip_quality(speechlike(10, HZ, snr_db=30), HZ)
    assert set(q) == {"duration_s", "speech_s", "clipping_pct", "snr_db", "ok", "reasons"}
    assert q["ok"] is True and q["reasons"] == []
    assert q["duration_s"] == 10.0
    assert 5 <= q["speech_s"] <= 10
    assert q["snr_db"] >= 25
    assert q["clipping_pct"] < 1


def test_short_clip_is_too_short(speechlike):
    q = clip_quality(speechlike(3, HZ), HZ)
    assert q["ok"] is False and "too short" in q["reasons"]


def test_clipped_clip_is_flagged(speechlike):
    x = np.clip(speechlike(10, HZ) * 6, -1.0, 1.0)
    q = clip_quality(x, HZ)
    assert q["ok"] is False and "clipping" in q["reasons"]
    assert q["clipping_pct"] >= 1


def test_noisy_clip_is_flagged(speechlike):
    q = clip_quality(speechlike(10, HZ, snr_db=5), HZ)
    assert q["ok"] is False and "noisy" in q["reasons"]
    assert q["snr_db"] < 15


def test_very_noisy_long_clip_says_noisy_not_too_short(speechlike):
    q = clip_quality(speechlike(12, HZ, snr_db=0), HZ)
    assert q["reasons"] == ["noisy"]  # a 12 s clip must not be called "too short"
    q = clip_quality(speechlike(3, HZ, snr_db=0), HZ)
    assert q["reasons"] == ["too short", "noisy"]


def test_continuous_sound_like_music_is_flagged():
    # a sustained chord with no pauses (music-like): no quiet gaps, so the SNR estimate is low
    t = np.arange(10 * HZ) / HZ
    x = (0.2 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 277 * t) + np.sin(2 * np.pi * 330 * t)) / 3).astype(np.float32)
    q = clip_quality(x, HZ)
    assert q["ok"] is False and "noisy" in q["reasons"]


def test_silence_is_too_quiet():
    q = clip_quality(np.zeros(10 * HZ, dtype=np.float32), HZ)
    assert q["ok"] is False and q["reasons"] == ["too quiet"]
    assert q["speech_s"] == 0


def test_int16_input_is_accepted(speechlike):
    x = (speechlike(8, HZ) * 32767).astype(np.int16)
    assert clip_quality(x, HZ)["ok"] is True


def test_long_clip_is_trimmed_to_30_seconds(speechlike):
    x = speechlike(40, HZ)
    y, trimmed = trim_seconds(x, HZ, 30)
    assert trimmed is True and len(y) == 30 * HZ
    z, trimmed = trim_seconds(y[: 10 * HZ], HZ, 30)
    assert trimmed is False and len(z) == 10 * HZ


def test_best_clip_picks_highest_snr_among_ok(speechlike):
    clips = [clip_quality(speechlike(10, HZ, snr_db=20, seed=1), HZ),
             clip_quality(speechlike(3, HZ, snr_db=40, seed=2), HZ),   # best SNR but too short
             clip_quality(speechlike(10, HZ, snr_db=35, seed=3), HZ),
             clip_quality(speechlike(10, HZ, snr_db=25, seed=4), HZ)]
    assert [c["ok"] for c in clips] == [True, False, True, True]
    assert best_clip(clips) == 2
    assert best_clip([clips[1]]) == -1
    assert best_clip([]) == -1


def test_transcript_check_flags_clips_with_too_few_words(speechlike):
    q = clip_quality(speechlike(10, HZ), HZ)
    heard = transcript_check(q, "नमस्ते मैं आज आपको अपनी आवाज़ का एक छोटा सा नमूना भेज रहा हूँ")
    assert heard["ok"] is True and heard["reasons"] == []
    music = transcript_check(q, "ला ला")
    assert music["ok"] is False and "few words" in music["reasons"]
    assert transcript_check(q, None) == q  # STT unavailable: no verdict on words
    assert q["reasons"] == []  # the input is not mutated


def test_profile_store_roundtrip(tmp_path):
    store = ProfileStore(tmp_path / "awaaz.db")
    assert store.get() is None
    store.save(Profile(name="Asha", language="ta-IN", family_names=["Ravi", "Meena"], condition="Throat cancer surgery"))
    again = ProfileStore(tmp_path / "awaaz.db").get()  # persisted on disk
    assert again.name == "Asha" and again.language == "ta-IN" and again.family_names == ["Ravi", "Meena"]
    assert again.voice is None and again.fallback_voice == "Shivani" and again.consent_at is None


def test_set_voice_and_delete_voice(tmp_path):
    store = ProfileStore(tmp_path / "awaaz.db")
    store.save(Profile(name="Asha", language="hi-IN", consent_at="2026-11-08T20:00:00+05:30"))
    emb = {"embedding": "AAAA", "shape": [1, 768], "dtype": "float32"}
    p = store.set_voice(emb, {"duration_s": 12.0, "snr_db": 31.2})
    assert p.voice == emb
    assert p.voice_meta["voice_id"] == voice_id(emb) and p.voice_meta["snr_db"] == 31.2
    assert store.get().voice == emb
    old = store.delete_voice()
    assert old == voice_id(emb)
    p = store.get()
    assert p.voice is None and p.voice_meta is None and p.consent_at is None
    assert p.name == "Asha"  # the rest of the profile stays
    assert store.delete_voice() is None


def test_set_voice_without_profile_creates_one(tmp_path):
    store = ProfileStore(tmp_path / "awaaz.db")
    store.set_voice({"embedding": "BBBB"}, {})
    assert store.get().voice == {"embedding": "BBBB"}


def test_voice_id_is_stable_and_distinct():
    a, b = {"embedding": "AAAA"}, {"embedding": "BBBB"}
    assert voice_id(a) == voice_id(dict(a)) and voice_id(a) != voice_id(b) and len(voice_id(a)) == 12


def test_phrase_learning(tmp_path):
    store = ProfileStore(tmp_path / "awaaz.db")
    assert store.top_phrases("hi-IN") == []
    for text in ["पानी चाहिए", "दर्द हो रहा है", "पानी चाहिए", " पानी चाहिए ", "धन्यवाद", "दर्द हो रहा है"]:
        store.add_phrase_use(text, "hi-IN")
    store.add_phrase_use("தண்ணீர் வேண்டும்", "ta-IN")
    store.add_phrase_use("   ", "hi-IN")  # ignored
    assert store.top_phrases("hi-IN") == ["पानी चाहिए", "दर्द हो रहा है", "धन्यवाद"]
    assert store.top_phrases("hi-IN", n=1) == ["पानी चाहिए"]
    assert store.top_phrases("ta-IN") == ["தண்ணீர் வேண்டும்"]
    assert store.phrase_counts("hi-IN") == [("पानी चाहिए", 3), ("दर्द हो रहा है", 2), ("धन्यवाद", 1)]
