#!/usr/bin/env bash
# Run from the repo root. FAKE=1 bash run_backend.sh for no-keys mode.
[ "${FAKE:-0}" = "1" ] && export AWAAZ_FAKE=1
exec uv run uvicorn awaaz.app:create_app --factory --host 127.0.0.1 --port 8767
