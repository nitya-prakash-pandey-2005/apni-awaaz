# Run from the repo root. Add -fake for no-keys mode (fake voice, tone audio, scripted nurse and suggestions).
param([switch]$fake)
if ($fake -or $env:FAKE -eq "1") { $env:AWAAZ_FAKE = "1" } else { Remove-Item Env:AWAAZ_FAKE -ErrorAction SilentlyContinue }
uv run python -m uvicorn awaaz.app:create_app --factory --host 127.0.0.1 --port 8767
