"""The 10 languages Prisma and Timbre support, their scripts, and the 'does this text need rewriting?' rule."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Lang:
    code: str
    name: str        # English name, used in LLM prompts
    native: str      # shown in the UI
    script: str      # script id (see SCRIPT_RANGES)
    script_name: str


LANGS: dict[str, Lang] = {l.code: l for l in [
    Lang("hi-IN", "Hindi", "हिन्दी", "deva", "Devanagari"),
    Lang("en-IN", "English", "English", "latin", "Latin"),
    Lang("ta-IN", "Tamil", "தமிழ்", "taml", "Tamil"),
    Lang("bn-IN", "Bengali", "বাংলা", "beng", "Bengali"),
    Lang("te-IN", "Telugu", "తెలుగు", "telu", "Telugu"),
    Lang("kn-IN", "Kannada", "ಕನ್ನಡ", "knda", "Kannada"),
    Lang("ml-IN", "Malayalam", "മലയാളം", "mlym", "Malayalam"),
    Lang("mr-IN", "Marathi", "मराठी", "deva", "Devanagari"),
    Lang("gu-IN", "Gujarati", "ગુજરાતી", "gujr", "Gujarati"),
    Lang("pa-IN", "Punjabi", "ਪੰਜਾਬੀ", "guru", "Gurmukhi"),
]}

SCRIPT_RANGES = {
    "deva": (0x0900, 0x097F), "beng": (0x0980, 0x09FF), "guru": (0x0A00, 0x0A7F), "gujr": (0x0A80, 0x0AFF),
    "taml": (0x0B80, 0x0BFF), "telu": (0x0C00, 0x0C7F), "knda": (0x0C80, 0x0CFF), "mlym": (0x0D00, 0x0D7F),
}

# Timbre v3.0: every voice speaks all 10 languages (docs/01-gnani-api-reference.md)
TIMBRE_V3_VOICES = {
    "female": ["Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika"],
    "male": ["Avinash", "Prakash", "Harshad", "Devansh", "Shubham", "Yashraj"],
}
ALL_VOICES = TIMBRE_V3_VOICES["female"] + TIMBRE_V3_VOICES["male"]


def lang(code: str) -> Lang:
    try:
        return LANGS[code]
    except KeyError:
        raise ValueError(f"unsupported language: {code!r}") from None


def char_script(ch: str) -> str | None:
    o = ord(ch)
    if ch.isascii():
        return "latin" if ch.isalpha() else None
    for script, (lo, hi) in SCRIPT_RANGES.items():
        if lo <= o <= hi:
            return script
    if ch.isalpha() and o < 0x0250:  # accented Latin letters
        return "latin"
    return None


def dominant_script(text: str) -> str | None:
    """The script most letters are written in ("latin", "deva", "taml", ...), or None if no letters."""
    counts: dict[str, int] = {}
    for ch in text or "":
        s = char_script(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    return max(counts, key=counts.get) if counts else None


def needs_rewrite(text: str, out_lang: str) -> str | None:
    """None when the text can be spoken as is; "transliterate" for Latin text going to an Indic language
    (romanised Hindi such as "mujhe paani chahiye"; the LLM translates instead if it is really English);
    "translate" when the text is in another script than the output language.
    Code-mixed text ("मुझे doctor चाहिए") counts as its dominant script and is spoken as is."""
    target = lang(out_lang).script
    s = dominant_script(text)
    if s is None or s == target:
        return None
    if s == "latin":
        return "transliterate"
    return "translate"
