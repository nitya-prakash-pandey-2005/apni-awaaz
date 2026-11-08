"""One user profile per device (SQLite): name, language, family names, voice embedding, phrase usage."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel


class Profile(BaseModel):
    name: str = ""
    language: str = "hi-IN"
    family_names: list[str] = []
    condition: str = ""
    voice: dict | None = None
    voice_meta: dict | None = None
    fallback_voice: str = "Shivani"
    consent_at: str | None = None


class ProfileStore:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK (id = 1), data TEXT);"
            "CREATE TABLE IF NOT EXISTS phrases (text TEXT, lang TEXT, uses INTEGER DEFAULT 0, PRIMARY KEY (text, lang));"
        )

    def get(self) -> Profile | None:
        row = self.db.execute("SELECT data FROM profile WHERE id = 1").fetchone()
        return Profile.model_validate_json(row[0]) if row else None

    def save(self, profile: Profile) -> Profile:
        self.db.execute("INSERT OR REPLACE INTO profile (id, data) VALUES (1, ?)", (profile.model_dump_json(),))
        self.db.commit()
        return profile

    def set_voice(self, embedding: dict, source_clip_meta: dict) -> Profile:
        p = self.get() or Profile()
        p.voice, p.voice_meta = embedding, source_clip_meta
        p.consent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return self.save(p)

    def delete_voice(self) -> Profile:
        p = self.get() or Profile()
        p.voice = p.voice_meta = p.consent_at = None
        return self.save(p)

    def add_phrase_use(self, text: str, lang: str) -> None:
        self.db.execute("INSERT INTO phrases (text, lang, uses) VALUES (?, ?, 1) "
                        "ON CONFLICT (text, lang) DO UPDATE SET uses = uses + 1", (text.strip(), lang))
        self.db.commit()

    def top_phrases(self, lang: str, n: int = 12) -> list[str]:
        rows = self.db.execute("SELECT text FROM phrases WHERE lang = ? ORDER BY uses DESC, rowid LIMIT ?", (lang, n))
        return [r[0] for r in rows]
