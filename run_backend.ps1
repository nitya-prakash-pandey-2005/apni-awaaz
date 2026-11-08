# run from the repo root; for no-keys mode first run: $env:AWAAZ_FAKE="1"
uv run uvicorn awaaz.app:create_app --factory --host 127.0.0.1 --port 8767 --reload
