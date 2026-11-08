# Apni Awaaz: implementation plan

> **For agentic workers:** execute task by task with TDD. Claim tasks in `docs/STATUS.md`.

**Goal:** a mobile-first web app (PWA) that clones the user's voice from voice notes (Gnani voice cloning) and speaks typed text, quick phrases or suggested replies in that voice in 10 Indian languages, with live captions of the conversation partner.
**Architecture:** reuses `voice-core` (contract `voice-core/README.md`: `create_voice_embedding`, `tts_clone_rest`, `TtsCache`, `PrismaStream`, `transcribe_rest`, `LLM`, `turns.is_echo`). Adds `awaaz` backend (profiles, enrolment quality checks, speak, suggest), FastAPI, and React + ui-kit pages.
**Spec:** `docs/02-design.md`.

## Global constraints
- Gnani constraints as in Dadi's plan. Synthesis at **16000 Hz** (`sample_rate=16000`, `container wav`). Listening (captions) STT at 16 kHz, `language_code` = the profile language plus `en-IN`, `format codemix`.
- Consent is mandatory: `POST /api/voice/enroll` without `consent=true` returns 400.
- Ports: backend **8767**, frontend **5193**.
- Every screen works at 390 px (this is a phone app first).

## Review focus
1. **WhatsApp .opus clip** uploaded on Chrome and on Safari: `decodeToPcm16` must work. If decoding fails, tell the user "Please export as MP3/WAV" (test the error path in Task 1's UI step).
2. **Clip with music or two speakers:** the quality check flags it (low SNR, or the Prisma transcript is empty or very short), and the user is asked for another clip (test in Task 1).
3. **Cloning API unavailable or rejecting:** the app falls back to a chosen Timbre v3.0 voice, shows a "fallback voice" badge and keeps working (test in Task 2).
4. **Echo:** in conversation mode the phone hears its own speech; those captions must be dropped (test in Task 3).
5. **Romanised Hindi typed by the user** ("mujhe paani chahiye") with output language Hindi: speak it naturally. Transliterate to Devanagari via the LLM before TTS when the text is Latin-script and the target is an Indic language (test in Task 2).

---

### Task 0: Bootstrap
Like Pukaar Task 0: workspace (`apni-awaaz`, package `awaaz`), sync `voice-core`, frontend from the Dadi frontend's ui-kit parts, ports 8767/5193. Commit.

### Task 1: Enrolment + quality
**Files:** `backend/awaaz/quality.py`, `backend/awaaz/profiles.py`, test `backend/tests/test_enroll.py`
**Produces:**
- `clip_quality(pcm: np.ndarray, hz: int) -> dict` → `{"duration_s", "speech_s", "clipping_pct", "snr_db", "ok": bool, "reasons": [str]}`. `ok` requires speech_s in 5–30, clipping < 1%, SNR ≥ 15 dB. SNR is estimated from frame RMS: the 90th percentile is speech, the 10th is noise.
- `best_clip(clips: list[dict]) -> int` (index of the highest SNR among `ok` clips, else -1)
- `ProfileStore(path)`: `get() -> Profile | None`, `save(profile)`, `set_voice(embedding: dict, source_clip_meta: dict)`, `delete_voice()`, `add_phrase_use(text, lang)`, `top_phrases(lang, n=12) -> list[str]`
- `Profile` (pydantic): `name`, `language`, `family_names: list[str]`, `condition: str`, `voice: dict | None` (embedding), `fallback_voice: str = "Shivani"`, `consent_at: str | None`
**Tests:** a synthetic 10 s tone plus pink noise at 30 dB → ok; 3 s → not ok with reason "too short"; a clipped signal → reason "clipping"; `best_clip` picks the highest SNR; `delete_voice` sets voice None.

### Task 2: Speak service
**Files:** `backend/awaaz/speak.py`, test `backend/tests/test_speak.py`
**Produces:** `async speak(text, out_lang, profile, settings, llm, cache) -> tuple[bytes, dict]` → (WAV bytes, `{"voice": "clone"|"fallback", "spoken_text": str, "translated": bool}`). Steps: if `out_lang` differs from the detected script language, or the text is Latin-script and `out_lang` is Indic → LLM rewrite ("Translate/transliterate to <lang> in native script; keep names; output only the sentence"); then `tts_clone_rest` with `profile.voice`; on any error or missing voice → `tts` with `fallback_voice` (model `timbre-v3.0`). Cache by (text, lang, voice id).
**Tests (fakes):** Latin "mujhe paani chahiye" with hi-IN → the LLM is called once and `spoken_text` is the FakeLLM output; clone failure → `voice == "fallback"`; a cache hit makes no second TTS call.

### Task 3: Converse service
**Files:** `backend/awaaz/converse.py`, test `backend/tests/test_converse.py`
**Produces:** `ListenSession(send_json, settings, profile, stt_factory=None)` (opens Prisma stream at 16 kHz; on a transcript → drops it if `is_echo` against the last 2 spoken lines or not meaningful; sends `{"type":"caption","text","lang","t"}`; then `suggest()` → `{"type":"suggestions","items":[3 strings]}`); `note_spoken(text)` (for the echo guard); `async suggest(llm, profile, history) -> list[str]` (JSON array of exactly 3 replies, ≤ 8 words each, in `profile.language`; invalid JSON → 3 defaults from `top_phrases`).
**Tests:** an echo transcript is dropped; a normal one yields a caption and 3 suggestions; bad JSON → the defaults.

### Task 4: FastAPI app
**Routes:** `GET /api/health`; `GET/PUT /api/profile`; `POST /api/voice/clip-check` (multipart wav → `clip_quality` + `transcribe_rest` text/lang); `POST /api/voice/enroll` (multipart wav + `consent` → embedding → profile; returns the test-phrase audio URL); `DELETE /api/voice`; `POST /api/speak {text, lang}` → `audio/wav` (headers `X-Voice: clone|fallback`); `GET /api/phrases?lang=`; `WS /ws/listen` (binary PCM16 16 kHz in; captions and suggestions out); `POST /api/sos` → WAV of the SOS message (user language plus the selected local language).
**Tests:** enroll without consent → 400; speak returns `audio/wav`; listen WS with FakeStt yields caption + suggestions.

### Task 5: Frontend
**Pages:** `Welcome.jsx` (consent), `VoiceBank.jsx` (clip picker using `decodeToPcm16`, a quality badge per clip, build, test phrase), `Speak.jsx`, `Converse.jsx`, `Sos.jsx`, `Profile.jsx`. Mobile tabs: Speak · Converse · SOS · Voice · Profile.
**Pinned UI:** big tap targets (≥ 56 px on the phrase grid); suggestion chips appear in under 2 s after a caption; a "fallback voice" badge when `X-Voice: fallback`; the delete-voice confirm sheet.
**Verify:** `npm run build`; screenshots at 390 and 1440 px.

### Task 6: Live test + demo
- Enrol with the team member's own 20–30 s voice note (consent given by that person). Speak Hindi, Tamil and English sentences; record what sounds good or bad in `docs/test-log.md`.
- Demo script (60 s): "This is my voice" (real) → "Imagine I lost it" → type → it speaks in my voice → a nurse speaks Hindi, captions appear, tap a suggestion → it answers in my voice, in Hindi → finally it speaks Tamil, a language I don't speak, in my voice → "Built on Gnani voice cloning, Timbre and Prisma".
- README with what, why, prior art, architecture, models used, privacy and setup.
