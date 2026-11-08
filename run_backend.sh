#!/usr/bin/env bash
# Run from the repo root. FAKE=1 bash run_backend.sh for no-keys mode (fake voice, tone audio, scripted nurse).
[ "${FAKE:-0}" = "1" ] && export AWAAZ_FAKE=1
exec uv run python -m uvicorn awaaz.app:create_app --factory --host 127.0.0.1 --port 8767
