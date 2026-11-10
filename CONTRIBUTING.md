# Contributing to Apni Awaaz

Thank you for helping people speak again in their own voice. This guide covers setup, the checks every change must
pass and the rules that keep users' voices safe.

## Setup

Python 3.12 with [uv](https://docs.astral.sh/uv/), and Node 20 or newer.

```bash
uv sync --all-packages
cd frontend && npm ci && cd ..
```

You do not need any API key to develop or test. Run the whole app offline in fake mode (tones stand in for speech,
a scripted nurse talks in conversation mode):

```bash
AWAAZ_FAKE=1 uv run python -m uvicorn awaaz.app:create_app --factory --host 127.0.0.1 --port 8767
cd frontend && npm run dev   # http://localhost:5193, proxies /api and /ws to the backend
```

For live Gnani and LLM calls, copy `.env.example` to `.env` and add your own keys. Never commit `.env`.

## Before you open a pull request

CI (`.github/workflows/ci.yml`) runs these on Ubuntu; run them locally first:

```bash
uv run python -m pytest -q          # backend and voice-core tests, no keys, no network
uv run --with ruff ruff check backend
cd frontend && npm run build && npm run build:demo
```

On Windows, use `uv run python -m pytest` rather than a `pytest.exe` launcher (Smart App Control can block it).

If you change a route, regenerate the API schema and update [docs/API.md](docs/API.md):

```bash
uv run python scripts/export_openapi.py
```

## How the code is organised

- `backend/awaaz/`: the FastAPI app and its modules (see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)).
- `voice-core/`: the shared voice engine (Gnani STT and TTS, voice cloning, the LLM adapter). It is shared with the
  team's other products, so change it there first and keep this copy in sync.
- `frontend/`: the React PWA; `npm run build:demo` builds the static demo that replays a recorded session.

`create_app()` takes its LLM and speech-to-text stream as arguments; tests pass fakes from `voice_core.testing`
instead of patching globals. Add a test with every behaviour change, and prefer testing through the HTTP API.

## Rules that are not negotiable

- **Consent first.** Never add a path that builds or uses a cloned voice without the `consent=true` check in
  `enroll()`. Clone only your own voice, or a voice whose owner has agreed.
- **The embedding stays on the server.** Never return `profile.voice` from any route; responses expose only
  `has_voice`.
- **Delete means delete.** Anything new that is generated in the user's voice must live under the clone cache so
  `DELETE /api/voice` removes it.
- **Say which voice spoke.** If audio is not in the cloned voice, report `X-Voice: fallback`.
- **One Gnani request at a time.** Route every new Gnani REST call through the gate in `create_app()`.
- **Synthetic voices only in tests, demos and screenshots.** Never commit a real person's recording.
- **Accessibility:** keep large tap targets, keep switch scanning working with Space and Enter, and announce
  captions and errors to screen readers.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `ci:`,
`chore:`), one logical change per commit, with the reason in the body when it is not obvious.

## License

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
