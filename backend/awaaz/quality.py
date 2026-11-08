"""Voice-note quality checks before we build a voice from it.

Gnani's voice cloning wants 5 to 30 seconds of clean speech from one person. A bad clip (music, a noisy
room, a clipped recording) gives a voice that does not sound like the person, so we check first and
tell the family exactly what to fix.

SNR is estimated from frame loudness, without a speech model: the 90th percentile of 30 ms frame RMS is
taken as the speech level and the 10th percentile as the noise floor (the quiet gaps between words).
Continuous sound with no gaps, like music, therefore scores a low SNR, which is what we want.
"""

from __future__ import annotations

import numpy as np

FRAME_S = 0.03
MIN_SPEECH_S, MAX_SPEECH_S = 5.0, 30.0
MIN_SNR_DB = 15.0
MAX_CLIPPING_PCT = 1.0
QUIET_DBFS = -45.0  # speech frames quieter than this: the recording is nearly silent
SNR_CAP_DB = 60.0
CLIP_LEVEL = 0.99
_EPS = 1e-6


def as_float(pcm: np.ndarray) -> np.ndarray:
    """int16 (or other integer) PCM -> float32 in [-1, 1]; float input is passed through."""
    x = np.asarray(pcm)
    if np.issubdtype(x.dtype, np.integer):
        return (x.astype(np.float32) / 32768.0).ravel()
    return x.astype(np.float32).ravel()


def trim_seconds(pcm: np.ndarray, hz: int, max_s: float = MAX_SPEECH_S) -> tuple[np.ndarray, bool]:
    """Keep at most `max_s` seconds (Gnani's cloning and REST STT both take up to 30 s)."""
    limit = int(max_s * hz)
    if len(pcm) > limit:
        return pcm[:limit], True
    return pcm, False


def clip_quality(pcm: np.ndarray, hz: int) -> dict:
    """{"duration_s", "speech_s", "clipping_pct", "snr_db", "ok", "reasons"}.
    ok needs 5-30 s of speech, clipping < 1 % and SNR >= 15 dB. Reason codes: "too quiet",
    "too short", "too long", "clipping", "noisy" (the UI turns them into plain advice)."""
    x = as_float(pcm)
    n = len(x)
    duration = n / hz if hz else 0.0
    clipping = 100.0 * float(np.mean(np.abs(x) >= CLIP_LEVEL)) if n else 0.0

    flen = max(1, int(hz * FRAME_S))
    nf = n // flen
    if nf:
        frames = x[: nf * flen].reshape(nf, flen).astype(np.float64)
        db = 20 * np.log10(np.sqrt(np.mean(frames**2, axis=1)) + _EPS)
        noise_db, speech_db = float(np.percentile(db, 10)), float(np.percentile(db, 90))
        thr = max((noise_db + speech_db) / 2, noise_db + 6.0, QUIET_DBFS)
        speech_s = float(np.sum(db > thr)) * FRAME_S
    else:
        noise_db = speech_db = 20 * np.log10(_EPS)
        speech_s = 0.0
    snr = min(SNR_CAP_DB, max(0.0, speech_db - noise_db))

    reasons: list[str] = []
    if speech_db < QUIET_DBFS:
        reasons.append("too quiet")
        speech_s = 0.0
    else:
        if speech_s < MIN_SPEECH_S:
            reasons.append("too short")
        elif speech_s > MAX_SPEECH_S:
            reasons.append("too long")
        if snr < MIN_SNR_DB:
            reasons.append("noisy")
    if clipping >= MAX_CLIPPING_PCT:
        reasons.append("clipping")
    return {
        "duration_s": round(duration, 2),
        "speech_s": round(speech_s, 2),
        "clipping_pct": round(clipping, 2),
        "snr_db": round(snr, 1),
        "ok": not reasons,
        "reasons": reasons,
    }


def transcript_check(quality: dict, transcript: str | None) -> dict:
    """Adds the 'did Prisma hear real words?' check. Music, a TV or a crowd gives an empty or very short
    transcript for many seconds of sound. None (STT unavailable) leaves the verdict unchanged.
    Returns a new dict; the input is not changed."""
    if transcript is None:
        return quality
    words = len(transcript.split())
    need = max(3, int(round(0.5 * float(quality.get("speech_s") or 0))))
    q = {**quality, "reasons": list(quality.get("reasons") or [])}
    if words < need and "few words" not in q["reasons"]:
        q["reasons"].append("few words")
    q["ok"] = not q["reasons"]
    return q


def best_clip(clips: list[dict]) -> int:
    """Index of the clip with the highest SNR among the ok ones, or -1 if none is ok."""
    best, best_snr = -1, float("-inf")
    for i, c in enumerate(clips):
        if c.get("ok") and float(c.get("snr_db", 0)) > best_snr:
            best, best_snr = i, float(c["snr_db"])
    return best
