"""Visit notes: after a doctor or nurse visit in Converse, a short structured summary of what was said.

One LLM JSON call extracts medicines (name, dose, when, days), tests, the next visit, warning signs, advice and the
patient's own questions. Everything it returns is checked against the transcript before it is shown:
- a medicine is kept only if its name was said (Latin or Devanagari spelling from a small lexicon, or verbatim);
- every number (dose, days, dates) must appear in the transcript, so "40 mg" can never become "400 mg";
- an item that names a known medicine nobody said is dropped (no invented drugs);
- "when" is a fixed set of tags, each kept only if one of its words was said.
If the LLM fails, a deterministic keyword/regex pass over the transcript gives the same shape, so the feature works
offline or rate-limited. The read-back text is built from templates (Hindi, English), never free-written by the LLM.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from voice_core.llm import parse_json_loose

log = logging.getLogger("awaaz.visit")
DISCLAIMER = {"en-IN": "Notes made by AI from the conversation. Check with your doctor.",
              "hi-IN": "ये नोट्स AI ने बातचीत से बनाए हैं। अपने डॉक्टर से ज़रूर पूछ लें।"}
MAX_ITEMS = 6
MAX_LEN = 140

# A small lexicon of common Indian outpatient medicines: Latin name -> other spellings heard in captions.
DRUGS = {
    "Pantoprazole": ["pantoprazole", "pantop", "pan 40", "पैंटोप्राज़ोल", "पैंटोप्राजोल", "पेंटोप्राजोल", "पैन्टोप्राज़ोल"],
    "Omeprazole": ["omeprazole", "omez", "ओमेप्राज़ोल", "ओमेप्राजोल"],
    "Paracetamol": ["paracetamol", "crocin", "dolo", "पैरासिटामोल", "पेरासिटामोल", "क्रोसिन", "डोलो"],
    "Ibuprofen": ["ibuprofen", "brufen", "आइबुप्रोफेन", "ब्रूफेन"],
    "Amoxicillin": ["amoxicillin", "amoxycillin", "एमोक्सिसिलिन", "अमोक्सिसिलिन"],
    "Azithromycin": ["azithromycin", "azithral", "एज़िथ्रोमाइसिन", "एजिथ्रोमाइसिन"],
    "Metformin": ["metformin", "मेटफॉर्मिन", "मेटफोर्मिन"],
    "Amlodipine": ["amlodipine", "एम्लोडिपिन", "अम्लोडिपिन"],
    "Atorvastatin": ["atorvastatin", "एटोरवास्टेटिन"],
    "Aspirin": ["aspirin", "ecosprin", "एस्पिरिन", "इकोस्प्रिन"],
    "Cetirizine": ["cetirizine", "सेटिरिज़िन", "सेटीरिज़ीन", "सेटिरिजिन"],
    "Levothyroxine": ["levothyroxine", "thyronorm", "थायरोनॉर्म"],
    "Ondansetron": ["ondansetron", "ondem", "ओन्डेनसेट्रॉन"],
    "Domperidone": ["domperidone", "डोमपेरिडोन"],
    "Insulin": ["insulin", "इंसुलिन", "इन्सुलिन"],
    "ORS": ["ors", "ओआरएस"],
}
TESTS = {
    "Blood test": ["blood test", "खून की जांच", "खून की जाँच", "ब्लड टेस्ट"],
    "Sugar test": ["sugar test", "शुगर टेस्ट", "शुगर की जांच"],
    "Urine test": ["urine test", "पेशाब की जांच", "यूरिन टेस्ट"],
    "X-ray": ["x-ray", "x ray", "xray", "एक्स-रे", "एक्सरे", "एक्स रे"],
    "Ultrasound": ["ultrasound", "sonography", "अल्ट्रासाउंड", "सोनोग्राफी"],
    "ECG": ["ecg", "ईसीजी"],
    "CT scan": ["ct scan", "सीटी स्कैन"],
    "MRI": ["mri", "एमआरआई"],
    "Endoscopy": ["endoscopy", "एंडोस्कोपी"],
}
# "when" tags -> words that must have been said for the tag to stay; and how each tag reads out.
WHEN = {
    "morning": ["subah", "morning", "सुबह", "सवेरे"],
    "afternoon": ["dopahar", "afternoon", "दोपहर"],
    "evening": ["shaam", "sham", "evening", "शाम"],
    "night": ["raat", "night", "bedtime", "रात", "सोने से पहले"],
    "empty_stomach": ["khaali pet", "khali pet", "empty stomach", "खाली पेट", "ख़ाली पेट"],
    "before_food": ["khane se pehle", "khaane se pehle", "before food", "before meal", "खाने से पहले"],
    "after_food": ["khane ke baad", "khaane ke baad", "after food", "after meal", "खाने के बाद"],
    "once_daily": ["once a day", "din mein ek", "दिन में एक", "एक बार"],
    "twice_daily": ["twice", "do baar", "दो बार", "दिन में दो"],
    "thrice_daily": ["three times", "teen baar", "तीन बार"],
    "as_needed": ["zarurat", "if needed", "when needed", "ज़रूरत", "जरूरत"],
}
WHEN_TEXT = {
    "en-IN": {"morning": "in the morning", "afternoon": "in the afternoon", "evening": "in the evening", "night": "at night",
              "empty_stomach": "on an empty stomach", "before_food": "before food", "after_food": "after food",
              "once_daily": "once a day", "twice_daily": "twice a day", "thrice_daily": "three times a day",
              "as_needed": "only when needed"},
    "hi-IN": {"morning": "सुबह", "afternoon": "दोपहर", "evening": "शाम", "night": "रात को", "empty_stomach": "खाली पेट",
              "before_food": "खाने से पहले", "after_food": "खाने के बाद", "once_daily": "दिन में एक बार",
              "twice_daily": "दिन में दो बार", "thrice_daily": "दिन में तीन बार", "as_needed": "ज़रूरत पड़ने पर"},
}
TEMPLATES = {
    "en-IN": {"title": "My visit notes.", "meds": "Medicines:", "for_days": "for {n} days", "tests": "Tests:",
              "next": "Next visit:", "watch": "Go back at once if:", "advice": "Advice:", "asked": "I asked:",
              "none": "No medicines or tests were noted."},
    "hi-IN": {"title": "मेरे विज़िट नोट्स।", "meds": "दवाइयाँ:", "for_days": "{n} दिन तक", "tests": "जाँच:",
              "next": "अगली बार:", "watch": "इनमें से कुछ हो तो तुरंत जाएँ:", "advice": "सलाह:", "asked": "मैंने पूछा:",
              "none": "कोई दवा या जाँच नहीं लिखी गई।"},
}
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_DOSE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|ml|mcg|g|gm|units?|tablets?|tabs?|capsules?|drops?|"
                      r"एमजी|मिलीग्राम|एमएल|गोली|गोलियाँ|गोलियां|टैबलेट|कैप्सूल|बूँद|बूंद)(?![a-z])", re.I)
_DAYS_RE = re.compile(r"(\d+)\s*(?:din|days?|दिन)", re.I)
_NEXT_RE = re.compile(r"agl[ae]|next|monday|tuesday|wednesday|thursday|friday|saturday|sunday|hafte|week|"
                      r"अगल[ेा]|सोमवार|मंगलवार|बुधवार|गुरुवार|शुक्रवार|शनिवार|रविवार|हफ़्ते|हफ्ते|फिर से (?:आ|दिखा)", re.I)
_WARN_RE = re.compile(r"(agar|if|अगर|यदि).*(turant|immediately|emergency|foran|तुरंत|फ़ौरन|फौरन)", re.I)
_ASK_RE = re.compile(r"\?|\b(kya|kab|kitn[ae]|kaise|kyun|what|when|how|why|can i|should i)\b|क्या|कब|कितन|कैसे|क्यों", re.I)


def ascii_digits(s: str) -> str:
    """Devanagari and other Indic digits -> 0-9, so '४०' and '40' compare equal."""
    return "".join(str(unicodedata.digit(c)) if c.isdigit() and not c.isascii() else c for c in s)


def _norm(s: str) -> str:
    return " ".join(ascii_digits(unicodedata.normalize("NFC", str(s))).casefold().split())


def transcript(turns: list[dict]) -> str:
    return "\n".join(f"{'Patient' if t['speaker'] == 'user' else 'Doctor'}: {t['text']}" for t in turns)


def _numbers(s: str) -> set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in _NUM_RE.findall(ascii_digits(str(s)))}


def _numbers_said(s: str, said: str) -> bool:
    return _numbers(s) <= _numbers(said)


def _said(words: list[str], said: str) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(_norm(w))}(?!\w)", said) for w in words)


def _drug_key(name: str) -> str | None:
    n = _norm(name)
    for key, aliases in DRUGS.items():
        if n == key.casefold() or n in aliases or any(a in n for a in [key.casefold(), *aliases] if len(a) > 3):
            return key
    return None


def _names_unsaid(text: str, said: str) -> bool:
    """True if `text` names a lexicon medicine or test that nobody said: the guard against invented drugs and tests."""
    t = _norm(text)
    for key, aliases in [*DRUGS.items(), *TESTS.items()]:
        words = [key.casefold(), *aliases]
        if _said(words, t) and not _said(words, said):
            return True
    return False


def _test_said(item: dict, said: str) -> bool:
    """A test is kept only if it names a lexicon test that was said, or its words are in the transcript verbatim."""
    for v in (item["en"], item["hi"]):
        n = _norm(v)
        if n in said or any(_said([k.casefold(), *a], n) and _said([k.casefold(), *a], said) for k, a in TESTS.items()):
            return True
    return False


def _grounded(quote: str, said: str) -> bool:
    """The item's quote (the transcript words it rests on) must really be in the transcript: >= 60% of its words."""
    words = re.findall(r"\w+", _norm(quote))
    have = set(re.findall(r"\w+", said))
    return bool(words) and sum(w in have for w in words) >= max(1, 0.6 * len(words))


def _text(x, said: str) -> dict | None:
    """An {"en", "hi", "quote"} item kept only if its quote is in the transcript, its numbers were said and it
    names no medicine or test that nobody said."""
    if not isinstance(x, dict):
        return None
    en, hi, quote = (str(x.get(k) or "").strip()[:MAX_LEN] for k in ("en", "hi", "quote"))
    en, hi = en or hi, hi or en
    if not en or not _grounded(quote, said):
        return None
    if not all(_numbers_said(v, said) and not _names_unsaid(v, said) for v in (en, hi)):
        return None
    return {"en": en, "hi": hi, "quote": quote}


def _items(xs, said: str) -> list[dict]:
    out = [_text(x, said) for x in (xs if isinstance(xs, list) else [])]
    return list({o["en"]: o for o in out if o}.values())[:MAX_ITEMS]


def _medicine(m, said: str) -> dict | None:
    if not isinstance(m, dict) or not str(m.get("name") or "").strip():
        return None
    name = str(m["name"]).strip()[:60]
    key = _drug_key(name)
    if key:
        if not _said([key.casefold(), *DRUGS[key]], said):
            return None
        name = key
    elif _norm(name) not in said or not _numbers_said(name, said):
        return None  # not in the lexicon: kept only if the exact name is in the transcript
    dose = str(m.get("dose") or "").strip()[:40]
    if dose and not (_numbers_said(dose, said) if _numbers(dose) else _norm(dose) in said):
        dose = ""  # a dose whose number nobody said is dropped, never "corrected"
    days = m.get("days")
    days = str(days).strip() if isinstance(days, (int, str)) and str(days).strip() else None
    if days and (not days.isdigit() or days not in _numbers(said)):
        days = None
    when = [w for w in (m.get("when") if isinstance(m.get("when"), list) else []) if w in WHEN and _said(WHEN[w], said)]
    return {"name": name, "dose": dose, "when": list(dict.fromkeys(when)), "days": int(days) if days else None}


def sanitise(obj, turns: list[dict]) -> dict:
    """Keep only what the transcript supports. Anything else is dropped; empty lists are fine."""
    said = _norm(transcript(turns))
    obj = obj if isinstance(obj, dict) else {}
    meds = [_medicine(m, said) for m in (obj.get("medicines") if isinstance(obj.get("medicines"), list) else [])]
    meds = list({m["name"]: m for m in meds if m}.values())[:MAX_ITEMS]
    return {"medicines": meds, "tests": [t for t in _items(obj.get("tests"), said) if _test_said(t, said)], "next_visit": _text(obj.get("next_visit"), said) if obj.get("next_visit") else None,
            "warning_signs": _items(obj.get("warning_signs"), said), "advice": _items(obj.get("advice"), said),
            "questions_asked": _items(obj.get("questions_asked"), said)}


def _sentences(turns: list[dict], speaker: str) -> list[str]:
    out = []
    for t in turns:
        if t["speaker"] == speaker:
            out += [s.strip() for s in re.split(r"(?<=[.!?।])\s+", t["text"]) if s.strip()]
    return out


def fallback(turns: list[dict]) -> dict:
    """No LLM: lexicon and regex over the doctor's sentences; the sentences themselves are quoted, never rewritten."""
    doc = _sentences(turns, "partner")
    meds, tests, nxt, warn = {}, {}, None, []
    for s in doc:
        n = _norm(s)
        for key, aliases in DRUGS.items():
            if key not in meds and _said([key.casefold(), *aliases], n):
                dose = _DOSE_RE.search(ascii_digits(s))
                days = _DAYS_RE.search(ascii_digits(s))
                meds[key] = {"name": key, "dose": f"{dose.group(1)} {dose.group(2)}" if dose else "",
                             "when": [w for w, words in WHEN.items() if _said(words, n)], "days": int(days.group(1)) if days else None}
        for key, aliases in TESTS.items():
            if key not in tests and _said([key.casefold(), *aliases], n):
                tests[key] = {"en": key, "hi": aliases[-1], "quote": s}
        if _WARN_RE.search(n):
            warn.append({"en": s, "hi": s, "quote": s})
        elif nxt is None and _NEXT_RE.search(n):
            nxt = {"en": s, "hi": s, "quote": s}
    asked = [{"en": s, "hi": s, "quote": s} for s in _sentences(turns, "user") if _ASK_RE.search(_norm(s))]
    return sanitise({"medicines": list(meds.values()), "tests": list(tests.values()), "next_visit": nxt,
                     "warning_signs": warn, "advice": [], "questions_asked": asked}, turns)


def _prompt() -> str:
    tags = ", ".join(WHEN)
    return ("You turn a doctor's visit into notes for a patient who cannot speak. Use ONLY what is in the transcript; "
            "never add a medicine, test, number or advice that was not said. Copy doses and numbers exactly as said. "
            "Write each text item as 'en' (simple English), 'hi' (simple Hindi, Devanagari) and 'quote' (the exact transcript "
            "words it comes from, copied as written). Empty lists are fine. "
            f"'when' uses only these tags: {tags}. Output only JSON: "
            '{"medicines":[{"name":"","dose":"","when":[],"days":null}],"tests":[{"en":"","hi":"","quote":""}],'
            '"next_visit":{"en":"","hi":"","quote":""} or null,"warning_signs":[{"en":"","hi":"","quote":""}],"advice":[{"en":"","hi":"","quote":""}],'
            '"questions_asked":[{"en":"","hi":"","quote":""}]}. questions_asked = what the Patient asked.')


async def extract(llm, turns: list[dict]) -> tuple[dict, str]:
    """(summary, source): source is "llm" or "fallback"."""
    try:
        out = await llm.complete([{"role": "system", "content": _prompt()}, {"role": "user", "content": transcript(turns)[:6000]}],
                                 temperature=0.1, max_tokens=700, json_mode=True)
        obj = parse_json_loose(out)
        if not isinstance(obj.get("medicines"), list):
            raise ValueError("no medicines list")
        return sanitise(obj, turns), "llm"
    except Exception as e:
        log.warning("visit summary LLM failed, using the keyword fallback: %r", e)
        return fallback(turns), "fallback"


def text_lang(lang: str) -> str:
    """The language the read-back text is written in: a template if there is one, else English (speak() translates)."""
    return lang if lang in TEMPLATES else "en-IN"


def read_back(summary: dict, lang: str) -> str:
    """The plain-language notes to read aloud, from templates only (nothing free-written)."""
    tl = text_lang(lang)
    L, W, k = TEMPLATES[tl], WHEN_TEXT[tl], "hi" if tl == "hi-IN" else "en"
    parts = [L["title"]]
    meds = []
    for m in summary["medicines"]:
        bits = [m["name"], m["dose"], *[W[w] for w in m["when"]], L["for_days"].format(n=m["days"]) if m["days"] else ""]
        meds.append(" ".join(b for b in bits if b))
    if meds:
        parts.append(f"{L['meds']} " + "; ".join(meds) + ("।" if tl == "hi-IN" else "."))
    if summary["tests"]:
        parts.append(f"{L['tests']} " + ", ".join(t[k] for t in summary["tests"]) + ("।" if tl == "hi-IN" else "."))
    if not meds and not summary["tests"]:
        parts.append(L["none"])
    if summary["next_visit"]:
        parts.append(f"{L['next']} {summary['next_visit'][k]}")
    for key, head in (("warning_signs", "watch"), ("advice", "advice"), ("questions_asked", "asked")):
        if summary[key]:
            parts.append(f"{L[head]} " + " ".join(x[k] for x in summary[key]))
    return "\n".join(parts)
