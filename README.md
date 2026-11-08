# Apni Awaaz (अपनी आवाज़): your own voice, back

**Voice banking and talk-assist for Indians who have lost their voice to throat or oral cancer, stroke or ALS. Rebuild your own voice from 30 seconds of old WhatsApp voice notes, then type, tap or pick a suggested reply and speak in that voice in 10 Indian languages, with live captions of the person you're talking to.**

Built on Gnani AI: **zero-shot voice cloning** (`vachana-vc-v1`), **Timbre v3.0** (TTS), **Prisma v3.0** (live captions) and **Evon v3.3** (LLM).
Part of our entry to Gnani AI's *Great Indian AI Internship Challenge* (#GnaniAI #GreatIndianAIInternshipChallenge).

> Status: under active development (8–10 Nov 2026). Read `docs/02-design.md`, then `docs/03-build-plan.md`. Team rules: `docs/TEAM-PLAYBOOK.md`. Task board: `docs/STATUS.md`.

## Quick start
```bash
bash ../dadi-vs-scammers/scripts/sync-core.sh
uv sync --all-packages
cp .env.example .env
uv run pytest -q
cd frontend && npm install && npm run dev         # http://localhost:5193
```
Voices are cloned only with the speaker's explicit consent.
