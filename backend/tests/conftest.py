"""Shared test helpers. All audio here is synthetic (tones + noise): no real voices."""

from __future__ import annotations

import numpy as np
import pytest

from voice_core.audio import mix_at_snr, pink_noise


def make_speechlike(seconds: float, hz: int = 16000, snr_db: float | None = 30.0, amp: float = 0.3,
                    seed: int = 0) -> np.ndarray:
    """A speech-like test signal: 'syllables' of a 160 Hz tone with harmonics (350 ms on, 150 ms off,
    smooth edges), plus pink noise at `snr_db`. The gaps matter: the SNR estimate compares loud frames
    with the quiet frames between syllables, as in real speech."""
    n = int(seconds * hz)
    t = np.arange(n) / hz
    tone = sum(np.sin(2 * np.pi * 160 * k * t) / k for k in (1, 2, 3))
    period, on = 0.5, 0.35
    phase = np.mod(t, period)
    env = np.where(phase < on, np.sin(np.pi * np.clip(phase / on, 0, 1)) ** 0.5, 0.0)
    x = (amp * tone * env / 1.8).astype(np.float32)
    if snr_db is not None:
        x = mix_at_snr(x, pink_noise(n, seed=seed), snr_db)
    return x.astype(np.float32)


@pytest.fixture
def speechlike():
    return make_speechlike
