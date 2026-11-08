"""Voice-note quality check before cloning: length of speech, clipping and an SNR estimate."""

from __future__ import annotations

import numpy as np

MIN_SPEECH_S, MAX_SPEECH_S, MAX_CLIP_PCT, MIN_SNR_DB = 5.0, 30.0, 1.0, 15.0


def clip_quality(pcm: np.ndarray, hz: int) -> dict:
    x = np.asarray(pcm)
    if x.dtype == np.int16:
        x = x.astype(np.float32) / 32768.0
    x = x.astype(np.float32)
    frame = max(1, hz // 50)  # 20 ms frames
    n = len(x) // frame
    rms = np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1)) if n else np.zeros(1)
    noise, speech = float(np.percentile(rms, 10)), float(np.percentile(rms, 90))
    snr_db = 20 * np.log10((speech + 1e-6) / (noise + 1e-6))
    speech_s = float(np.sum(rms > max(noise * 2, 1e-3)) * frame / hz)
    clipping_pct = float(np.mean(np.abs(x) >= 0.99) * 100) if len(x) else 0.0
    reasons = []
    if speech_s < MIN_SPEECH_S:
        reasons.append("too short")
    if speech_s > MAX_SPEECH_S:
        reasons.append("too long")
    if clipping_pct >= MAX_CLIP_PCT:
        reasons.append("clipping")
    if snr_db < MIN_SNR_DB:
        reasons.append("noisy")
    return {"duration_s": round(len(x) / hz, 2), "speech_s": round(speech_s, 2), "clipping_pct": round(clipping_pct, 2),
            "snr_db": round(float(snr_db), 1), "ok": not reasons, "reasons": reasons}


def best_clip(clips: list[dict]) -> int:
    ok = [(c["snr_db"], i) for i, c in enumerate(clips) if c.get("ok")]
    return max(ok)[1] if ok else -1
