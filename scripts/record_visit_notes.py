"""Record the demo's visit notes from one live run: a synthetic doctor visit, real captions, a real summary, own voice.

1. Gnani Timbre speaks a short doctor's visit (a synthetic voice, Hindi/Hinglish).
2. Gnani Prisma v3.0 (REST, codemix hi-IN,en-IN) captions it, as Converse would.
3. The visit-notes summary runs on those captions with the configured LLM (POST /api/visit/summary's code path).
4. The read-back text is spoken in the cloned voice of the demo's synthetic profile (embedding from the same voice note
   the demo uses), with vachana-vc-v1 at 16 kHz.
It needs GNANI_API_KEY and an LLM key in .env and makes 4 Gnani requests (TTS, STT, embedding, clone TTS) one at a time.

    uv run python scripts/record_visit_notes.py            # writes frontend/demo/visit.json and two WAVs
    uv run python scripts/record_visit_notes.py --fake D   # no keys, no network: tones and the keyword fallback into D
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo_session as S  # noqa: E402

RATE = 16000
DOCTOR = ("Aapko Pantoprazole 40 mg subah khaali pet, 14 din tak lena hai. Agle Monday ko blood test karwa lijiye. "
          "Agar khoon ki ulti ho toh turant aaiye.")
PATIENT = "क्या मैं चाय पी सकता हूँ?"  # the patient's reply, tapped and spoken in their own voice in Converse
DOCTOR_VOICE = "Prakash"


async def retry(fn, *a, **kw):
    for i in range(4):
        try:
            return await fn(*a, **kw)
        except Exception as e:  # one request at a time per key: a 429 means another call is in flight
            if "429" not in repr(e) or i == 3:
                raise
            await asyncio.sleep(1.5)


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fake", type=Path, help="write tones and the fallback summary to this folder instead")
    a = ap.parse_args()

    from voice_core.audio import float_to_pcm16, read_wav, wav_bytes
    from voice_core.gnani.stt_stream import SttEvent

    from awaaz import visit

    if a.fake:
        from awaaz.fake_mode import FakeAwaazLLM
        from awaaz.fake_mode import fake_embedding as embed
        from awaaz.fake_mode import tone_pcm as clone
        from awaaz.fake_mode import tone_pcm as tts

        async def stt(key, wav, **kw):
            return SttEvent("transcript", text=DOCTOR, language="hi-IN")
        key, out, llm = "", a.fake, FakeAwaazLLM()
    else:
        from voice_core.config import get_settings
        from voice_core.gnani import create_voice_embedding as embed
        from voice_core.gnani import transcribe_rest as stt
        from voice_core.gnani import tts_clone_rest as clone
        from voice_core.gnani import tts_rest as tts
        from voice_core.llm import LLM
        settings = get_settings()
        key, out, llm = settings.gnani_api_key, S.DEMO, LLM(settings)
        if not key:
            sys.exit("GNANI_API_KEY is not set in .env")
    (out / "audio").mkdir(parents=True, exist_ok=True)
    nums = {}

    t = time.perf_counter()
    pcm = await retry(tts, key, DOCTOR, voice=DOCTOR_VOICE, model="timbre-v3.0", language="hi-IN", sample_rate=RATE)
    nums["doctor_tts_ms"] = round((time.perf_counter() - t) * 1000)
    doc_wav = wav_bytes(pcm, RATE)
    (out / "audio" / "doctor-visit.wav").write_bytes(doc_wav)
    nums["doctor_audio_s"] = round(len(pcm) / 2 / RATE, 2)
    print(f"doctor audio {nums['doctor_audio_s']} s ({nums['doctor_tts_ms']} ms)")

    t = time.perf_counter()
    ev = await retry(stt, key, doc_wav, language_code="hi-IN,en-IN")
    nums["prisma_ms"] = round((time.perf_counter() - t) * 1000)
    print(f"caption ({nums['prisma_ms']} ms): {ev.text}")
    turns = [{"speaker": "partner", "text": ev.text, "t": 0.0},
             {"speaker": "user", "text": PATIENT, "t": round(nums["doctor_audio_s"] + 1.0, 2)}]

    t = time.perf_counter()
    summary, source = await visit.extract(llm, turns)
    nums["summary_ms"] = round((time.perf_counter() - t) * 1000)
    print(f"summary ({source}, {nums['summary_ms']} ms): {json.dumps(summary, ensure_ascii=False)}")
    lang = "hi-IN"
    local, en = visit.read_back(summary, lang), visit.read_back(summary, "en-IN")
    print(local)

    x, hz = read_wav((S.DEMO / "audio" / "notes" / S.USED_NOTE).read_bytes())
    emb = await retry(embed, key, wav_bytes(float_to_pcm16(x[: 30 * hz]), hz))
    t = time.perf_counter()
    voice = "clone"
    try:
        pcm = await retry(clone, key, local, emb, language=lang, sample_rate=RATE)
    except Exception as e:  # the app's speak() falls back to Timbre the same way
        print(f"clone TTS failed, using the fallback voice: {e!r}")
        voice = "fallback"
        pcm = await retry(tts, key, local, voice="Shivani", model="timbre-v3.0", language=lang, sample_rate=RATE)
    nums["readback_tts_ms"] = round((time.perf_counter() - t) * 1000)
    nums["readback_audio_s"] = round(len(pcm) / 2 / RATE, 2)
    (out / "audio" / "visit-notes.wav").write_bytes(wav_bytes(pcm, RATE))
    print(f"read-back {nums['readback_audio_s']} s in the {voice} voice ({nums['readback_tts_ms']} ms)")

    rec = {"recorded_at": datetime.now(UTC).isoformat(timespec="seconds"), "fake": bool(a.fake),
           "doctor": {"text": DOCTOR, "voice": f"Gnani Timbre v3.0 {DOCTOR_VOICE} (synthetic)", "audio": "audio/doctor-visit.wav"},
           "turns": turns, "llm": getattr(llm, "model", "?"), "numbers": nums,
           "response": {"summary": summary, "source": source, "lang": lang, "text_lang": visit.text_lang(lang),
                        "text": {"local": local, "en": en}, "disclaimer": visit.disclaimer(source, lang)},
           "readback": {"file": "audio/visit-notes.wav", "voice": voice, "text": local, "lang": lang}}
    (out / "visit.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"visit.json written to {out}")


if __name__ == "__main__":
    asyncio.run(main())
