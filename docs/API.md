# Apni Awaaz backend API

The backend is one FastAPI app (`backend/awaaz/app.py`, built by `create_app()`), served on port 8767 by
`run_backend.sh` / `run_backend.ps1`. It has 11 REST paths under `/api`, one WebSocket (`/ws/listen`) and, when
`frontend/dist` exists, the built web app at `/`.

- **Machine-readable schema:** [`docs/api/openapi.json`](api/openapi.json), regenerated with
  `uv run python scripts/export_openapi.py` (keyless and offline: fake mode, blank settings, nothing is called).
  `--check` fails if the file is out of date. FastAPI also serves it live at `/openapi.json` and `/docs`.
- **Auth:** none. The app is single-user and meant to run on the user's own device or LAN (one profile per
  database). Do not expose it to the internet as it is.
- **Errors:** FastAPI's shape, `{"detail": "<message>"}` or `{"detail": {...}}` where noted. A JSON body that does
  not match its model gets FastAPI's standard `422` validation error.
- **Languages:** every `lang` / `language` must be one of `hi-IN, en-IN, ta-IN, te-IN, kn-IN, ml-IN, bn-IN,
  mr-IN, gu-IN, pa-IN` (`LANGS` in `backend/awaaz/speak.py`); anything else is `400 unsupported language <code>`.
- **Audio:** speech comes back as `audio/wav`, 16-bit PCM, mono, 16 kHz (`RATE` in `speak.py`). Voice-note uploads
  must be 16-bit PCM WAV (the web app converts the recording before upload).
- **Fake mode:** with `AWAAZ_FAKE=1` every route works with no keys: tones stand in for speech, the embedding is a
  hash of the clip, the clip transcript is a fixed Hindi sentence, and `/ws/listen` "hears" a scripted nurse
  (`backend/awaaz/fake_mode.py`). Fake mode uses its own database (`cache/awaaz_fake.db`) and cache folder.

## Route summary

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Which keys are set, LLM provider, STT mode, fake mode, whether a voice is enrolled |
| GET | `/api/profile` | The profile, without the voice embedding |
| PUT | `/api/profile` | Save name, language, family names, condition, fallback voice |
| POST | `/api/voice/clip-check` | Quality check (and transcript) of one voice note |
| POST | `/api/voice/enroll?consent=true` | Build the cloned voice from one clip; consent is mandatory |
| DELETE | `/api/voice` | Delete the voice, its consent record and every clip spoken in it |
| POST | `/api/speak` | Speak a sentence in the cloned voice (or the fallback voice) |
| GET | `/api/phrases?lang=` | Quick phrases: the user's most used, then the defaults |
| POST | `/api/sos` | Emergency message in the profile language and a local language, as one WAV |
| GET | `/api/predict?text=&lang=` | Up to 5 next-word / phrase suggestions from the person's own phrases and a starter lexicon |
| POST | `/api/visit/summary` | Visit notes from a Converse session: medicines, tests, next visit, warning signs, advice, questions, checked against the transcript, plus the read-back text |
| POST | `/api/pain/sentence` | "Where does it hurt?": builds the sentence to speak (then spoken through `/api/speak`) |
| POST | `/api/messages?label=` | Bank an original recording (kept and replayed as it is) |
| GET | `/api/messages` | List banked recordings |
| GET | `/api/messages/{mid}/audio` | One banked recording's audio |
| DELETE | `/api/messages/{mid}` | Delete a banked recording |
| WS | `/ws/listen` | Conversation mode: live captions of the other person and 3 suggested replies |

## Health and profile

### `GET /api/health`

```json
{"gnani_key": true, "llm_key": true, "llm_provider": "groq", "stt_mode": "stream", "fake": false, "has_voice": true}
```

`llm_key` is true when a Groq key or an Evon base URL is configured. Key values are never returned.

### `GET /api/profile`

```json
{
  "name": "Asha", "language": "hi-IN", "family_names": ["Ravi"], "condition": "",
  "voice_meta": {"duration_s": 12.4, "speech_s": 9.8, "clipping_pct": 0.0, "snr_db": 31.2, "ok": true, "reasons": []},
  "fallback_voice": "Shivani", "consent_at": "2026-11-10T13:55:02+00:00", "has_voice": true
}
```

The voice embedding (`voice`) is never sent to the browser; `has_voice` says whether one exists. `voice_meta` is the
quality report of the clip the voice was built from, and `consent_at` (UTC, ISO 8601) is when consent was given.
Before anything is saved the defaults are returned (empty name, `hi-IN`, fallback voice `Shivani`, no voice).

### `PUT /api/profile`

```bash
curl -X PUT localhost:8767/api/profile -H 'Content-Type: application/json' \
  -d '{"name": "Asha", "language": "hi-IN", "family_names": ["Ravi"], "condition": "after a stroke", "fallback_voice": "Shivani"}'
```

Body fields (all optional): `name`, `language` (default `hi-IN`), `family_names` (list), `condition`,
`fallback_voice` (a Timbre voice, default `Shivani`). These five fields are replaced as a whole, so send all of
them (an omitted field goes back to its default). The voice, its quality report and the consent time are never
changed by this route. Returns the profile as `GET /api/profile` does. `400` for an unsupported language.

## Voice enrolment

The web app checks each voice note with `clip-check`, picks the best one that passed, asks for consent, then calls
`enroll`. Both routes judge only the first 30 s of the clip, because that is all that is sent to Gnani.

### `POST /api/voice/clip-check`

Body: a 16-bit PCM WAV (any sample rate). The clip is analysed locally (`backend/awaaz/quality.py`) and transcribed
with Gnani STT (profile language plus `en-IN`).

```bash
curl -X POST localhost:8767/api/voice/clip-check -H 'Content-Type: audio/wav' --data-binary @note.wav
```

```json
{"duration_s": 12.4, "speech_s": 9.8, "clipping_pct": 0.0, "snr_db": 31.2, "ok": true, "reasons": [],
 "text": "हाँ बेटा, मैं ठीक हूँ", "lang": "hi-IN"}
```

`ok` is false with one or more `reasons`: `too short` (under 5 s of speech), `too long` (over 30 s of speech),
`clipping` (1 % or more of samples at full scale), `noisy` (estimated SNR under 15 dB), `no clear speech` (the
transcript is empty or meaningless). If the transcript call fails, `text` and `lang` are `null` and the verdict
rests on the signal checks alone. `400 send a 16-bit PCM WAV body` if the body is not a readable WAV.

### `POST /api/voice/enroll?consent=true`

Body: the chosen clip as a 16-bit PCM WAV.

```bash
curl -X POST 'localhost:8767/api/voice/enroll?consent=true' -H 'Content-Type: audio/wav' --data-binary @best.wav
```

```json
{"profile": {"...": "as GET /api/profile", "has_voice": true}, "test_text": "नमस्ते, ये मेरी आवाज़ है।"}
```

`test_text` is a short sentence in the profile language for the "hear your voice" check.

| Status | When |
|---|---|
| `400` | `consent` is missing or not true (checked before the audio is read), or the body is not a WAV |
| `422` | The clip fails the quality check: `{"detail": {"message": "clip quality too low", "quality": {...}}}` |
| `502` | Gnani voice cloning failed; the fallback voice stays on |

On success the embedding, the clip's quality report and the consent time are stored in the profile.

### `DELETE /api/voice`

Deletes the embedding, its quality report and the consent time, and empties the cloned-voice audio cache (every
sentence ever spoken in the user's voice). Returns the profile (`has_voice: false`). Name, language and banked
recordings stay.

## Speaking

### `POST /api/speak`

```bash
curl -X POST localhost:8767/api/speak -H 'Content-Type: application/json' \
  -d '{"text": "mujhe paani chahiye", "lang": "hi-IN"}' -o out.wav -D -
```

Body: `text` (required, not blank), `lang` (default `hi-IN`), `remember` (default `true`: count this sentence
for the user's most-used phrases). Returns `audio/wav` with headers:

| Header | Value |
|---|---|
| `X-Voice` | `clone` (the user's own voice) or `fallback` (the Timbre voice from the profile) |
| `X-Spoken-Text` | The sentence actually spoken, URL-encoded (it differs from `text` when it was rewritten) |
| `X-Translated` | `true` when the text was transliterated or translated into `lang` first |

Text whose script does not match `lang` (for example Hindi typed in Latin letters, or a Hindi phrase spoken in
Tamil) is first rewritten by the LLM into `lang`'s script. If the cloned voice fails, the fallback voice answers
and `X-Voice` says so. `400` for empty text or an unsupported language; `502 speech failed: ...` only when the
fallback voice fails too.

### `GET /api/phrases?lang=hi-IN`

Up to 12 strings: the user's 6 most used sentences in that language (from `/api/speak` with `remember`), then the
built-in quick phrases, without duplicates. Languages without their own list use the English one (and `/api/speak`
translates on the way out).

```json
["मुझे पानी चाहिए", "हाँ", "नहीं", "फिर से बोलिए", "धन्यवाद"]
```

### `POST /api/sos`

```bash
curl -X POST localhost:8767/api/sos -H 'Content-Type: application/json' -d '{"local_lang": "ta-IN"}' -o sos.wav -D -
```

Body: `local_lang` (optional; the language people around the user speak). Speaks the emergency message in the
profile language, then in `local_lang` if it differs, with 0.6 s of silence after each, as one WAV. Headers:
`X-Voice` is `clone` only if every part was in the cloned voice, otherwise `fallback`; `X-Spoken-Text` is a
URL-encoded JSON array of the sentences spoken. `400` for an unsupported `local_lang`. If speech fails the error
still carries the text so the app can show it in large type and read it with the phone's own voice:

```json
{"detail": {"message": "SOS speech failed: ...", "langs": ["hi-IN", "ta-IN"], "texts": ["आपातकाल! ...", "அவசரம்! ..."]}}
```

## Communication aids

### `GET /api/predict?text=mujhe pa&lang=hi-IN`
Prefix and previous-word scoring over the person's own phrase counts (ranked first) and a starter lexicon (native and romanised Hindi and Tamil, English). `text` is cut to 500 characters.
```json
{"suggestions": [
  {"text": "mujhe paani chahiye", "label": "mujhe paani chahiye", "kind": "phrase"},
  {"text": "mujhe pankha chala dijiye", "label": "pankha chala dijiye", "kind": "phrase"},
  {"text": "mujhe paani ", "label": "paani", "kind": "word"}
]}
```
`text` is the full replacement for the input box, `label` what the chip shows, `kind` is `phrase` or `word`.

### `POST /api/pain/sentence`
Body (`PainIn`): `part` (e.g. `"arm"`), `side` (`"left"`/`"right"`/null), `level` 0–10, `type` (`sharp`, `burning`, `dull`, `throbbing`, `itching`), `since` (`""`, `"just_now"`, `"today"`, `"since_yesterday"`), `lang`.
```json
{"part": "arm", "side": "left", "level": 7, "type": "sharp", "since": "today", "lang": "hi-IN"}
```
Response: the sentence in that language (Hindi and Tamil from tested templates with gender/case agreement; other languages get English, which `/api/speak` translates).
```json
{"text": "मेरी बाईं बाँह में आज से तेज़ दर्द है, दस में से सात।", "lang": "hi-IN", "template_lang": "hi"}
```
Unknown part, type or level → `400` with a message. The same templates (`backend/awaaz/data/pain.json`) drive the browser in demo mode; a test checks that both produce identical sentences.

### `POST /api/visit/summary`
Body (`VisitIn`): `turns` (at most 200; each `{"speaker": "partner" | "user", "text": "...", "t": 1.0}`: `partner` is the
doctor or nurse, `user` the patient's spoken replies) and an optional `lang` for the read-back (default: the profile language).
```json
{"turns": [{"speaker": "partner", "text": "Aapko Pantoprazole 40 mg subah khaali pet, 14 din tak lena hai. Agle Monday ko blood test karwa lijiye."},
           {"speaker": "user", "text": "क्या मैं चाय पी सकता हूँ?"}], "lang": "hi-IN"}
```
Response: the checked summary, where it came from (`llm`, or `fallback` for the keyword pass), and the text to read back
in the profile language (`text.local`, written in `text_lang`: Hindi or English templates; other languages get English,
which `/api/speak` translates) and in English (`text.en`). Each text item carries `en`, `hi` and the transcript `quote` it rests on.
```json
{"summary": {"medicines": [{"name": "Pantoprazole", "dose": "40 mg", "when": ["morning", "empty_stomach"], "days": 14}],
             "tests": [{"en": "Blood test", "hi": "ब्लड टेस्ट", "quote": "blood test karwa lijiye"}],
             "next_visit": {"en": "Next Monday", "hi": "अगले सोमवार", "quote": "Agle Monday ko"},
             "warning_signs": [], "advice": [], "questions_asked": [{"en": "Can I drink tea?", "hi": "क्या मैं चाय पी सकता हूँ?", "quote": "क्या मैं चाय पी सकता हूँ?"}]},
 "source": "llm", "lang": "hi-IN", "text_lang": "hi-IN",
 "text": {"local": "मेरे विज़िट नोट्स।\nदवाइयाँ: Pantoprazole 40 mg सुबह खाली पेट 14 दिन तक।\n…", "en": "My visit notes.\nMedicines: Pantoprazole 40 mg in the morning on an empty stomach for 14 days.\n…"},
 "disclaimer": "ये नोट्स AI ने बातचीत से बनाए हैं। अपने डॉक्टर से ज़रूर पूछ लें।"}
```
No doctor/nurse turn with text → `400`; unsupported `lang` → `400`; a bad `speaker` or more than 200 turns → `422`.
Medicines, doses, days, tests and quotes that are not in the transcript are dropped (see `backend/tests/test_visit.py`).
To read the notes aloud, POST `text.local` to `/api/speak` with `remember: false`.

## Message banking

Original recordings of the person (for example before surgery), stored and replayed exactly as recorded; no AI is
involved.

- `POST /api/messages?label=Good%20morning` with the raw recording as the body and its `Content-Type`
  (`audio/webm`, `audio/wav`, ...; anything that is not `audio/*` is stored as `audio/webm`). The label is trimmed
  to 80 characters. Returns `{"id": 1, "label": "Good morning", "created": "2026-11-10T13:55:02+00:00"}`.
  `400` without a label or audio, `413` over 8 MB.
- `GET /api/messages` returns `[{"id": 1, "label": "Good morning", "created": "..."}]` in recording order.
- `GET /api/messages/{mid}/audio` returns the recording with its stored media type, or `404`.
- `DELETE /api/messages/{mid}` returns `{"ok": true}` (also when it did not exist).

## WebSocket `/ws/listen` (conversation mode)

One socket per conversation. The client streams the microphone; the server streams back captions of what the
other person said and three suggested replies. The user answers by tapping a reply, which the web app sends to
`POST /api/speak` (not over the socket).

**Client to server:** binary frames of raw PCM16 little-endian, mono, 16 kHz, any frame size (the web app sends
small microphone frames and skips frames while more than 256 KB is buffered). Text frames are ignored.

**Server to client:** JSON text frames.

| Message | Meaning |
|---|---|
| `{"type": "status", "stt": "connected"}` | The speech-to-text stream is open |
| `{"type": "status", "stt": "error"}` / `"closed"` | The STT stream failed or ended; the user taps the mic again (there is no automatic reconnect) |
| `{"type": "status", "stt": "error", "message": "..."}` | The session itself failed |
| `{"type": "caption", "text": "क्या आपको दर्द हो रहा है?", "lang": "hi-IN", "t": 4.21}` | What the other person said; `t` is seconds since the socket opened |
| `{"type": "suggestions", "items": ["हाँ, दर्द है", "थोड़ा पानी दीजिए", "धन्यवाद"]}` | Three replies in the profile language, at most 8 words each |

Behaviour (`backend/awaaz/converse.py`):

- Speech-to-text is Gnani Prisma streaming with automatic Indian-language detection (`STT_MODE=stream`, the
  default) or turn-based REST recognition in the profile language plus English (`STT_MODE=turn`). The profile's
  name and family names are passed as key terms.
- **Echo guard:** anything the app speaks (`/api/speak`, `/api/sos`) while the socket is open is remembered (the
  last 2 sentences); a caption that matches it is the phone hearing itself and is dropped. Captions under 2
  characters are dropped too.
- After each caption the LLM suggests 3 replies from the last 6 turns, the user's condition and family names; a
  new caption cancels a suggestion still in progress. If the LLM fails or returns anything other than exactly 3
  short non-empty strings, the user's most used phrases and the built-in ones are sent instead, so suggestions
  always arrive.
- The profile is read when the socket opens; reconnect after changing the language.

Example (Python, `websockets`):

```python
import asyncio, json, websockets

async def main(pcm16: bytes):
    async with websockets.connect("ws://localhost:8767/ws/listen") as ws:
        for i in range(0, len(pcm16), 3200):  # 100 ms frames
            await ws.send(pcm16[i:i + 3200])
            await asyncio.sleep(0.1)
        async for raw in ws:
            print(json.loads(raw))
```
