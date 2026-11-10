"""'Where does it hurt?': builds one natural pain sentence from a body part, side, 0-10 level, pain type and onset.

Templates live in data/pain.json, shared with the web app so the static demo builds the same sentence.
Hindi, Tamil and English have native templates; other languages get the English sentence, which speak()
then translates into the chosen language on the way out (the existing speak/translate path).
"""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "pain.json"


@cache
def templates() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def part(pid: str) -> dict:
    for p in templates()["parts"]:
        if p["id"] == pid:
            return p
    raise ValueError(f"unknown body part {pid!r}")


def template_lang(lang: str) -> str:
    """The language the sentence is written in: a native template if there is one, else English."""
    return lang if lang in templates()["langs"] else "en-IN"


def sentence(part_id: str, level: int, kind: str, lang: str = "hi-IN", side: str | None = None, since: str = "") -> str:
    t = templates()
    p = part(part_id)
    if kind not in t["types"]:
        raise ValueError(f"unknown pain type {kind!r}")
    if since not in t["since"]:
        raise ValueError(f"unknown onset {since!r}")
    if not 0 <= int(level) <= 10:
        raise ValueError("level must be 0-10")
    if p["sided"] != (side in ("left", "right")):
        raise ValueError(f"{part_id} needs side left/right" if p["sided"] else f"{part_id} has no side")
    tl = template_lang(lang)
    L = t["langs"][tl]
    fields = {"type": L["types"][kind], "since": L["since"][since], "level": L["numbers"][int(level)]}
    if tl == "hi-IN":
        g = p["hi"]["g"]
        fields |= {"my": L["my"][g], "part": p["hi"]["noun"], "side": L["side"][side][g] if side else ""}
    else:
        fields |= {"part": p["ta"] if tl == "ta-IN" else p["en"], "side": L["side"][side] if side else ""}
    return L["template"].format(**fields)
