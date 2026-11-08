# Apni Awaaz (अपनी आवाज़): your own voice, back

**Voice banking and talk-assist for Indians who have lost their voice to throat or oral cancer, stroke or ALS. Rebuild your own voice from 30 seconds of old WhatsApp voice notes, then type, tap or pick a suggested reply and speak in that voice in 10 Indian languages, with live captions of the person you're talking to.**

Built on Gnani AI: **zero-shot voice cloning** (`vachana-vc-v1`), **Timbre v3.0** (TTS), **Prisma v3.0** (live captions) and **Evon v3.3** (LLM).
Part of our entry to Gnani AI's *Great Indian AI Internship Challenge* (#GnaniAI #GreatIndianAIInternshipChallenge).

> **New here? Read `docs/START-HERE.md` first.** Status: under active development (8–10 Nov 2026). Read `docs/02-design.md`, then `docs/03-build-plan.md`. Team rules: `docs/TEAM-PLAYBOOK.md`. Task board: `docs/STATUS.md`.

## Beyond cloning
- **Message banking:** record real phrases before surgery (or cut them from old voice notes); they play back exactly as recorded, next to the cloned voice.
- **Switch scanning:** stroke and ALS users who cannot type or tap pick phrases with one switch (Space/Enter) while the highlight steps through them.

## Quick start
```bash
uv sync --all-packages
cp .env.example .env                              # add GNANI_API_KEY and GROQ_API_KEY
uv run pytest -q
bash run_backend.sh                               # port 8767; or FAKE=1 bash run_backend.sh (no keys: tones, scripted nurse)
cd frontend && npm ci && npm run dev              # http://localhost:5193 (or npm run build: the backend serves dist/)
```

## Live test checklist (real keys)
1. My voice: tick consent, upload a 20-30 s voice note (also try a WhatsApp .opus on Chrome and Safari), build, play the test phrase.
2. Speak: Hindi, Tamil and English text; romanised Hindi ("mujhe paani chahiye") with Hindi selected. Check the badge says "Your voice".
3. Converse (earphones off): someone speaks Hindi; captions and 3 replies appear in under 2 s; your own spoken reply is not captioned.
4. SOS with a second language. Profile: delete my voice, then Speak shows "Fallback voice".
Voices are cloned only with the speaker's explicit consent.

Demo, post and submission kit: [`docs/06-demo-and-post.md`](docs/06-demo-and-post.md). Live test results: [`docs/test-log.md`](docs/test-log.md).
