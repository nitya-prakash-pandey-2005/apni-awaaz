"""Write the backend's OpenAPI schema to docs/api/openapi.json (keyless, offline).

The app is built in-process in fake mode (AWAAZ_FAKE=1) with a blank Settings object and a throwaway cache folder,
so no API key is read, no Gnani or LLM call can happen and the real profile database is never opened. Only the
schema is generated; no route is called.

    uv run python scripts/export_openapi.py [--out docs/api/openapi.json] [--check]

--check exits 1 if the file on disk differs from the current schema (use it after changing a route).
The /ws/listen WebSocket is not part of OpenAPI; docs/API.md documents its protocol.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build_schema() -> dict:
    os.environ["AWAAZ_FAKE"] = "1"
    from voice_core.config import Settings

    from awaaz.app import create_app

    # ignore_cleanup_errors: on Windows the app's SQLite file is still open when the folder is removed
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        app = create_app(Settings(cache_dir=Path(tmp)))  # blank keys: Settings() never reads .env
        return app.openapi()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=ROOT / "docs" / "api" / "openapi.json")
    ap.add_argument("--check", action="store_true", help="fail if the file is out of date instead of writing it")
    args = ap.parse_args()
    text = json.dumps(build_schema(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = args.out.read_text(encoding="utf-8") if args.out.exists() else ""
        if current != text:
            print(f"{args.out} is out of date: run scripts/export_openapi.py", file=sys.stderr)
            return 1
        print(f"{args.out} is up to date")
        return 0
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8", newline="\n")
    paths = json.loads(text)["paths"]
    print(f"wrote {args.out}: {len(paths)} paths")
    for p, ops in paths.items():
        print(f"  {' '.join(m.upper() for m in ops):<12} {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
