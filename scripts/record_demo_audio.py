"""Record the demo's cloned-voice audio: the sentences and the SOS spoken in the live session, in the cloned voice.

The cloned audio made during the 10 Nov session was wiped by that session's own "Delete my voice" test (as designed).
This script remakes it with the same synthetic voice note, the same models and the same calls as the app:
Gnani voice-cloning embedding from the note the app used, then vachana-vc-v1 at 16 kHz for each sentence.
It needs GNANI_API_KEY in .env and makes 1 + 7 + 2 = 10 Gnani requests, one at a time (run it when the key is free).

    uv run python scripts/record_demo_audio.py           # writes frontend/demo/audio/clone-*.wav, sos.wav, recordings.json
    uv run python scripts/record_demo_audio.py --fake D  # no keys, no network: tones into folder D (checks the plumbing)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_session as S  # noqa: E402

RATE = 16000


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fake", type=Path, help="write tones to this folder instead of calling Gnani")
    a = ap.parse_args()

    from awaaz.phrases import sos_text
    from voice_core.audio import float_to_pcm16, pcm16_to_float, read_wav, wav_bytes

    if a.fake:
        from awaaz.fake_mode import fake_embedding as embed, tone_pcm as clone
        key, out = "", a.fake
    else:
        from voice_core.config import get_settings
        from voice_core.gnani import create_voice_embedding as embed, tts_clone_rest as clone
        key, out = get_settings().gnani_api_key, S.DEMO
        if not key:
            sys.exit("GNANI_API_KEY is not set in .env")
    (out / "audio").mkdir(parents=True, exist_ok=True)

    x, hz = read_wav((S.DEMO / "audio" / "notes" / S.USED_NOTE).read_bytes())
    emb = await embed(key, wav_bytes(float_to_pcm16(x[: 30 * hz]), hz))  # the app sends at most the first 30 s
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    recs = []
    for i, (text, lang, spoken) in enumerate(S.SPOKEN, 1):
        pcm = await clone(key, spoken, emb, language=lang, sample_rate=RATE)
        name = f"audio/clone-{i:02}.wav"
        (out / name).write_bytes(wav_bytes(pcm, RATE))
        recs.append({"kind": "speak", "text": text, "lang": lang, "spoken": spoken, "voice": "clone", "file": name, "recorded_at": at})
        print(f"{name}: {len(pcm) / 2 / RATE:.1f} s  {lang}")
    parts = []
    for lang in S.SOS_LANGS:  # the same message and 0.6 s gap as POST /api/sos
        pcm = await clone(key, sos_text(lang), emb, language=lang, sample_rate=RATE)
        parts += [pcm16_to_float(pcm), np.zeros(int(0.6 * RATE), np.float32)]
    (out / "audio" / "sos.wav").write_bytes(wav_bytes(float_to_pcm16(np.concatenate(parts)), RATE))
    recs.append({"kind": "sos", "langs": S.SOS_LANGS, "texts": [sos_text(x) for x in S.SOS_LANGS], "voice": "clone",
                 "file": "audio/sos.wav", "recorded_at": at})
    (out / "recordings.json").write_text(json.dumps(recs, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"recordings.json: {len(recs)} entries in {out}")


if __name__ == "__main__":
    asyncio.run(main())
