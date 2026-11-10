# Deploy the static demo on Vercel

The live link is a **static demo build** of the real Apni Awaaz app. It has no backend and never calls Gnani or Groq, so it costs nothing to host and cannot use up API credits.

It replays a real session recorded on Gnani's live servers on 10 Nov 2026, with synthetic voices only. In the demo:
- **Speak** plays the sentences spoken live in the cloned voice, with the "Your voice" badge. Other text typed in "Say anything" is read by the phone's own voice, with the "Phone's voice" badge; another quick phrase shows: "In the demo, tap one of the recorded phrases; run it locally with your keys to speak anything." The banked messages play as recorded. Word and phrase suggestions and the keystrokes-saved count work as in the real app (built in the browser from the same word list).
- **Where does it hurt?** builds the same sentence as the server (same templates) and the phone's own voice reads it, with the "Phone's voice" badge.
- **My voice** shows the three synthetic voice notes and their live quality results. Visitors can play each note and the test phrase. Uploading, recording and building are off.
- **Converse** has "Play the recorded conversation": the nurse's audio, her live captions and the 3 suggested replies at the pace of the audio. Tapping the recorded reply plays it in the cloned voice. There is no microphone and no WebSocket.
- **SOS** plays the recorded Hindi + Tamil SOS. Without that recording, it falls back to the phone's own voice, as the real app does when Gnani is down.
- **Profile:** Save and Delete my voice explain that they are off in the demo. The family contact for SOS and dwell selection work, because they are stored only in the browser; SOS then offers WhatsApp and SMS links with the location if the visitor allows it.
- A banner on every page says what the demo is and links to GitHub. The service worker is off in the demo, and an old one is unregistered.

The normal build (`npm run build`) is unchanged. It contains no demo files, and the demo code is switched off.

## How it works
- `npm run build:demo` runs `vite build --mode demo`. `frontend/.env.demo` sets `VITE_DEMO=1`, and `vite.config.js` copies `frontend/demo/` to `dist/demo/`.
- `frontend/src/lib/demo.js` answers every `/api` call in the browser from `dist/demo/`: GETs from `snapshot/*.json`, Speak and SOS from `recordings.json` and its audio, `/api/visit/summary` and the visit-notes read-back from `visit.json`, `/api/predict` and `/api/pain/sentence` computed in the browser (`lib/predict.js`, `lib/pain.js`, on the same JSON as the server in `backend/awaaz/data/`), and everything else with a friendly "off in the demo" message.
- `frontend/demo/` holds the recorded session:

| File | What it is | Made by |
|---|---|---|
| `snapshot/*.json` | health, profile, banked messages, quick phrases for 10 languages | `scripts/snapshot_demo.py` |
| `audio/message-*.wav` | the two banked messages (synthetic, Timbre Shubham) | `scripts/snapshot_demo.py` |
| `voice-clips.json`, `audio/notes/*.wav` | the three synthetic voice notes and their live quality results | `scripts/snapshot_demo.py` (facts in `scripts/demo_session.py`) |
| `converse.json`, `audio/nurse.wav` | the nurse's sentence (synthetic, Timbre Kalpana), captions and suggestions | `scripts/snapshot_demo.py --nurse` |
| `recordings.json`, `audio/clone-*.wav`, `audio/sos.wav` | the sentences and the SOS in the cloned voice | `scripts/record_demo_audio.py` (needs keys) |
| `visit.json`, `audio/doctor-visit.wav`, `audio/visit-notes.wav` | Visit notes: a synthetic doctor visit (Timbre Prakash), its Prisma captions, the summary and the read-back in the cloned voice | `scripts/record_visit_notes.py` (needs keys; 4 Gnani requests and 1 LLM call) |

## Before the first deploy: record the cloned-voice audio (once, about 10 Gnani requests)
The cloned audio from the 10 Nov session was wiped by that session's own "Delete my voice" test, which is the feature working as designed. Until it is recorded again, the demo's Speak and Converse replies show the friendly message, and SOS uses the phone's voice.

When the Gnani key is free (one request at a time):
```bash
uv run python scripts/record_demo_audio.py   # 1 embedding + 9 speech calls, about 30 s
git add frontend/demo && git commit -m "demo: cloned-voice recordings"
```
It uses the same synthetic voice note (`PTT-20240521-WA0015.wav`), the same models (`vachana-vc-v1` at 16 kHz) and the same sentences as the live session. To check the plumbing with no keys: `uv run python scripts/record_demo_audio.py --fake <scratch folder>`.

## Deploy
1. On vercel.com: **Add New → Project →** import `nitya-prakash-pandey-2005/apni-awaaz`.
2. Leave **Root Directory** as the repo root. `vercel.json` sets everything: no framework, `cd frontend && npm install`, `cd frontend && npm run build:demo`, output `frontend/dist`. The build needs `../voice-core/web`, which is why it runs from the root.
3. Add no environment variables. The demo needs no keys, so never add `GNANI_API_KEY` or `GROQ_API_KEY` to Vercel.
4. Deploy, open the link on a phone, and replace `*[live demo link]*` (and `*[video link]*`) at the top of `README.md` and `PITCH.md`. Then regenerate the one-page PDF: `uv run --no-project --with markdown --with pypdf python scripts/make_pitch_pdf.py`.

To check locally first: `cd frontend && npm run build:demo && npx serve dist` (or `python -m http.server -d dist 8790`), with no backend running. Afterwards run `npm run build` again: the backend serves `frontend/dist`, and a demo build there would answer from the recording instead of the server.

## Refresh the snapshot after a new live session
1. Run the app live and use it (synthetic voices only), then stop the server.
2. Move the database aside, for example `cache/awaaz.db` → `cache/awaaz.db.session-<date>`.
3. Update `scripts/demo_session.py` with that session's facts: the voice notes and their results, what was spoken, the captions and the suggestions.
4. `uv run python scripts/snapshot_demo.py --db cache/awaaz.db.session-<date> [--nurse path/to/nurse.wav]`. This step is offline: blank keys, a raising LLM, the network blocked.
5. When the key is free: `uv run python scripts/record_demo_audio.py`.
6. `cd frontend && npm run build:demo`, check it, then commit `frontend/demo/` and `scripts/demo_session.py`.
