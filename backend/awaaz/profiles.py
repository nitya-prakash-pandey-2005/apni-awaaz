"""The user's profile (one per device in the demo) and phrase learning, in SQLite.

The voice embedding lives only here, on the user's own machine. Deleting the voice removes it (and the
consent record that went with it) so nothing in the user's voice can be made again without new consent.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

SCHEMA = """
CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS phrase_uses (
  lang TEXT NOT NULL, text TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, last REAL NOT NULL,
  PRIMARY KEY (lang, text)
);
"""


class Profile(BaseModel):
    name: str = ""
    language: str = "hi-IN"
    family_names: list[str] = Field(default_factory=list)
    condition: str = ""
    voice: dict | None = None            # Gnani voice-clone embedding {embedding, shape, dtype}
    fallback_voice: str = "Shivani"      # Timbre v3.0 voice used when cloning is unavailable
    consent_at: str | None = None        # when the speaker agreed to have their voice cloned
    local_language: str = "hi-IN"        # second SOS language (the language spoken around the user)
    voice_meta: dict | None = None       # which clip the voice was built from, its quality, voice_id


def voice_id(embedding: dict | None) -> str | None:
    """Short stable id of an embedding (names cache entries; never reveals the embedding)."""
    if not embedding:
        return None
    return hashlib.sha1(str(embedding.get("embedding", "")).encode("utf-8")).hexdigest()[:12]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


class ProfileStore:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(SCHEMA)
        self.db.commit()

    def get(self) -> Profile | None:
        row = self.db.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        return Profile.model_validate_json(row[0]) if row else None

    def save(self, profile: Profile) -> Profile:
        self.db.execute("INSERT OR REPLACE INTO profile(id, data) VALUES (1, ?)", (profile.model_dump_json(),))
        self.db.commit()
        return profile

    def set_voice(self, embedding: dict, source_clip_meta: dict) -> Profile:
        p = self.get() or Profile()
        p.voice = embedding
        p.voice_meta = {**(source_clip_meta or {}), "voice_id": voice_id(embedding), "created_at": now_iso()}
        return self.save(p)

    def delete_voice(self) -> str | None:
        """Removes the embedding and its consent record. Returns the deleted voice_id (None if there was none)."""
        p = self.get()
        if p is None or p.voice is None:
            return None
        old = voice_id(p.voice)
        p.voice, p.voice_meta, p.consent_at = None, None, None
        self.save(p)
        return old

    def add_phrase_use(self, text: str, lang: str) -> None:
        text = " ".join((text or "").split())
        if not text:
            return
        self.db.execute(
            "INSERT INTO phrase_uses(lang, text, n, last) VALUES (?, ?, 1, ?) "
            "ON CONFLICT(lang, text) DO UPDATE SET n = n + 1, last = excluded.last",
            (lang, text[:300], time.time()),
        )
        self.db.commit()

    def top_phrases(self, lang: str, n: int = 12) -> list[str]:
        rows = self.db.execute(
            "SELECT text FROM phrase_uses WHERE lang = ? ORDER BY n DESC, last DESC LIMIT ?", (lang, int(n))
        ).fetchall()
        return [r[0] for r in rows]
