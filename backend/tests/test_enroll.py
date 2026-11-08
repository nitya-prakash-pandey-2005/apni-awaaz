import numpy as np
from voice_core.audio import pink_noise

from awaaz.profiles import Profile, ProfileStore
from awaaz.quality import best_clip, clip_quality

HZ = 16000


def _speechy(seconds: float, snr_db: float = 30.0) -> np.ndarray:
    t = np.arange(int(seconds * HZ)) / HZ
    gate = (np.sin(2 * np.pi * 0.5 * t) > -0.3).astype(np.float32)  # on/off like syllables and pauses
    voice = 0.3 * np.sin(2 * np.pi * 180 * t) * gate
    noise = pink_noise(len(t))
    noise = noise / np.sqrt(np.mean(noise**2)) * 0.3 / np.sqrt(2) / 10 ** (snr_db / 20)
    return (voice + noise).astype(np.float32)


def test_clean_10s_clip_is_ok():
    q = clip_quality(_speechy(10), HZ)
    assert q["ok"], q
    assert 9.9 < q["duration_s"] < 10.1 and q["snr_db"] >= 15 and q["clipping_pct"] < 1


def test_short_clip_too_short():
    q = clip_quality(_speechy(3), HZ)
    assert not q["ok"] and "too short" in q["reasons"]


def test_clipped_clip():
    q = clip_quality(np.clip(_speechy(10) * 6, -1, 1), HZ)
    assert not q["ok"] and "clipping" in q["reasons"]


def test_noisy_clip_low_snr():
    q = clip_quality(_speechy(10, snr_db=3), HZ)
    assert not q["ok"] and "noisy" in q["reasons"]


def test_best_clip_picks_highest_snr_ok():
    clips = [clip_quality(x, HZ) for x in (_speechy(10, 20), _speechy(3, 40), _speechy(10, 35))]
    assert best_clip(clips) == 2
    assert best_clip([clips[1]]) == -1


def test_profile_store_roundtrip(tmp_path):
    s = ProfileStore(tmp_path / "p.db")
    assert s.get() is None
    s.save(Profile(name="Asha", language="hi-IN", family_names=["Ravi"]))
    s.set_voice({"embedding": [0.1], "shape": [1, 1], "dtype": "float32"}, {"snr_db": 30})
    p = s.get()
    assert p.name == "Asha" and p.voice["embedding"] == [0.1] and p.consent_at
    s.delete_voice()
    assert s.get().voice is None and s.get().consent_at is None


def test_top_phrases(tmp_path):
    s = ProfileStore(tmp_path / "p.db")
    for t in ["पानी", "पानी", "दर्द", "पानी"]:
        s.add_phrase_use(t, "hi-IN")
    s.add_phrase_use("water", "en-IN")
    assert s.top_phrases("hi-IN") == ["पानी", "दर्द"]
