"""Word and phrase prediction for the Speak box: fewer keystrokes for people who type slowly.

Scores come from a small corpus: the person's own spoken phrases (weighted by how often they used them)
plus a starter lexicon per language (data/lexicon.json, shared with the web app for the static demo).
Two kinds of suggestion, both from prefix matching on whole words:
- phrase completions: a known phrase whose first words match the last words typed (more matched context ranks higher);
- word completions and next words: bigram (previous word -> word) and unigram counts.
Pure functions, no model and no network: fast enough to run on every keystroke. Mirrored in frontend/src/lib/predict.js.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path

DATA = Path(__file__).parent / "data" / "lexicon.json"
PERSONAL_BASE, PERSONAL_PER_USE, LEXICON_WEIGHT = 3, 2, 1
_TRIM = re.compile(r"[\s।.!?,]+$")


@cache
def lexicon() -> dict[str, list[str]]:
    return {k: v for k, v in json.loads(DATA.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def words(text: str) -> list[str]:
    return _TRIM.sub("", text.strip().lower()).split()


def corpus(lang: str, history=()) -> list[tuple[str, int]]:
    """(phrase, weight): the person's phrases first, then the starter lexicon (English for languages without one)."""
    seen, out = set(), []
    for text, uses in history:
        t = _TRIM.sub("", text.strip())
        if t and t.lower() not in seen:
            seen.add(t.lower())
            out.append((t, PERSONAL_BASE + PERSONAL_PER_USE * max(0, int(uses))))
    for t in lexicon().get(lang) or lexicon()["en-IN"]:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append((t, LEXICON_WEIGHT))
    return out


def predict(text: str, lang: str = "hi-IN", history=(), k: int = 5) -> list[dict]:
    """Up to k suggestions [{"text": the whole new box text, "label": what the chip shows, "kind": "phrase" | "word"}]."""
    raw = text.split()
    at_word_start = not text or text[-1].isspace()
    typed = words(text)
    prefix = "" if at_word_start or not typed else typed[-1]
    done = typed if at_word_start else typed[:-1]
    keep = raw if at_word_start else raw[:-1]  # the typed words, in the person's own spelling and case
    phrases = corpus(lang, history)
    found: dict[str, tuple[float, int, dict]] = {}

    def add(score: float, order: int, out: str, label: str, kind: str) -> None:
        key = out.strip().lower()
        if key == text.strip().lower() or (key in found and found[key][0] >= score):
            return
        found[key] = (score, order, {"text": out, "label": label, "kind": kind})

    for i, (p, weight) in enumerate(phrases):
        pw = words(p)
        for j in range(min(len(done), len(pw) - 1), -1, -1):  # longest overlap of the typed context with the phrase start
            if pw[:j] == done[len(done) - j:] and pw[j].startswith(prefix) and (j or prefix or not done):
                add(weight * (1 + j) * 10, i, " ".join([*keep[: len(keep) - j], p]), p, "phrase")
                break

    uni: dict[str, int] = {}
    bi: dict[tuple[str, str], int] = {}
    shown: dict[str, str] = {}  # lower-case word -> its spelling in the corpus ("I", "Ravi")
    for p, weight in phrases:
        orig = _TRIM.sub("", p).split()
        pw = ["<s>", *words(p)]
        for (a, b), o in zip(zip(pw, pw[1:], strict=False), orig, strict=False):  # shortest wins, as in the JS mirror
            bi[(a, b)] = bi.get((a, b), 0) + weight
            uni[b] = uni.get(b, 0) + weight
            shown.setdefault(b, o)
    prev = done[-1] if done else "<s>"
    cands = [w for w in uni if w.startswith(prefix) and w != prefix]
    follows = [w for w in cands if bi.get((prev, w))]  # words seen after the previous word; else any word with the prefix
    for i, w in enumerate(follows or (cands if prefix else [])):
        add(3 * bi.get((prev, w), 0) + uni[w], len(phrases) + i, " ".join([*keep, shown[w]]) + " ", shown[w], "word")

    ranked = [d for _, _, d in sorted(found.values(), key=lambda t: (-t[0], t[1]))]
    phrase_hits = [d for d in ranked if d["kind"] == "phrase"][:3]
    return (phrase_hits + [d for d in ranked if d["kind"] == "word"])[:k]


def keystrokes_saved(pressed: int, text: str) -> int:
    """Percent of letters the person did not have to type (0 if they typed more keys than letters)."""
    n = len(text)
    return max(0, int(100 * (1 - pressed / n) + 0.5)) if n else 0  # rounds half up, like the web app
