"""One user profile per device (SQLite): name, language, family names, voice embedding, phrase usage."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
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
            "CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, label TEXT, mime TEXT, audio BLOB, created TEXT);"
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
        p.consent_at = datetime.now(UTC).isoformat(timespec="seconds")
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

    def phrase_counts(self, lang: str, n: int = 300) -> list[tuple[str, int]]:
        """(text, uses) of the person's most-used phrases in a language: the personal part of word prediction."""
        rows = self.db.execute("SELECT text, uses FROM phrases WHERE lang = ? ORDER BY uses DESC, rowid LIMIT ?", (lang, n))
        return [(r[0], r[1]) for r in rows]

    # message banking: the person's own recordings, kept and replayed as they are (no AI)
    def add_message(self, label: str, mime: str, audio: bytes) -> dict:
        created = datetime.now(UTC).isoformat(timespec="seconds")
        cur = self.db.execute("INSERT INTO messages (label, mime, audio, created) VALUES (?, ?, ?, ?)",
                              (label, mime, audio, created))
        self.db.commit()
        return {"id": cur.lastrowid, "label": label, "created": created}

    def list_messages(self) -> list[dict]:
        rows = self.db.execute("SELECT id, label, created FROM messages ORDER BY id")
        return [{"id": r[0], "label": r[1], "created": r[2]} for r in rows]

    def message_audio(self, mid: int) -> tuple[str, bytes] | None:
        row = self.db.execute("SELECT mime, audio FROM messages WHERE id = ?", (mid,)).fetchone()
        return (row[0], row[1]) if row else None

    def delete_message(self, mid: int) -> None:
        self.db.execute("DELETE FROM messages WHERE id = ?", (mid,))
        self.db.commit()
