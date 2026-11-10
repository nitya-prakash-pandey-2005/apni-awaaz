import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from voice_core.config import Settings
from voice_core.testing import FakeLLM

from awaaz import visit
from awaaz.app import create_app
from awaaz.speak import script_of

DOC = "Aapko Pantoprazole 40 mg subah khaali pet, 14 din tak lena hai. Agle Monday ko blood test karwa lijiye. " \
      "Agar khoon ki ulti ho toh turant aaiye."
TURNS = [{"speaker": "partner", "text": DOC, "t": 1.0}, {"speaker": "user", "text": "Kya main chai pi sakta hoon?", "t": 9.0}]
HINDI = [{"speaker": "partner", "text": "आपको पैंटोप्राज़ोल ४० mg सुबह खाली पेट, 14 दिन तक लेनी है। अगले सोमवार को ब्लड टेस्ट करवा लीजिए। "
                                         "अगर खून की उल्टी हो तो तुरंत आइए।", "t": 1.0}]
GOOD = {"medicines": [{"name": "Pantoprazole", "dose": "40 mg", "when": ["morning", "empty_stomach"], "days": 14}],
        "tests": [{"en": "Blood test", "hi": "ब्लड टेस्ट", "quote": "blood test karwa lijiye"}],
        "next_visit": {"en": "Next Monday, blood test", "hi": "अगले सोमवार", "quote": "Agle Monday ko"},
        "warning_signs": [{"en": "Vomiting blood: come at once", "hi": "खून की उल्टी हो तो तुरंत आएँ", "quote": "khoon ki ulti ho toh turant aaiye"}],
        "advice": [], "questions_asked": [{"en": "Can I drink tea?", "hi": "क्या मैं चाय पी सकता हूँ?", "quote": "Kya main chai pi sakta hoon?"}]}
Q = "blood test karwa lijiye"


def run(coro):
    return asyncio.run(coro)


def test_good_llm_output_is_kept():
    s, src = run(visit.extract(FakeLLM([json.dumps(GOOD)]), TURNS))
    assert src == "llm"
    assert s["medicines"] == [{"name": "Pantoprazole", "dose": "40 mg", "when": ["morning", "empty_stomach"], "days": 14}]
    assert s["tests"][0]["en"] == "Blood test" and s["warning_signs"] and s["questions_asked"]


@pytest.mark.parametrize("dose", ["400 mg", "4 mg", "40.5 mg", "50 mg"])
def test_dose_numbers_are_never_changed(dose):
    bad = {**GOOD, "medicines": [{**GOOD["medicines"][0], "dose": dose}]}
    s, _ = run(visit.extract(FakeLLM([json.dumps(bad)]), TURNS))
    assert s["medicines"][0]["dose"] == ""  # dropped, never "corrected" into something the doctor did not say


def test_days_not_said_are_dropped():
    bad = {**GOOD, "medicines": [{**GOOD["medicines"][0], "days": 21}]}
    assert run(visit.extract(FakeLLM([json.dumps(bad)]), TURNS))[0]["medicines"][0]["days"] is None


def test_adversarial_invented_medicines_are_dropped():
    bad = {**GOOD, "medicines": [*GOOD["medicines"], {"name": "Paracetamol", "dose": "500 mg", "when": ["night"], "days": 5},
                                 {"name": "Wondercure Forte", "dose": "40 mg", "when": [], "days": None}],
           "advice": [{"en": "Take Ibuprofen for pain", "hi": "दर्द में आइबुप्रोफेन लें", "quote": Q}, {"en": "Drink water", "hi": "पानी पिएँ", "quote": Q},
                      {"en": "Walk daily", "hi": "रोज़ टहलें", "quote": "roz subah 30 minute walk karein"}, {"en": "Rest", "hi": "आराम"}],
           "warning_signs": [{"en": "Fever above 102", "hi": "102 से ऊपर बुखार", "quote": Q}]}
    s, _ = run(visit.extract(FakeLLM([json.dumps(bad)]), TURNS))
    assert [m["name"] for m in s["medicines"]] == ["Pantoprazole"]
    assert [a["en"] for a in s["advice"]] == ["Drink water"]  # unsaid drug, quote not in the transcript, no quote -> dropped
    assert s["warning_signs"] == []  # 102 was never said


def test_when_tags_must_be_said():
    bad = {**GOOD, "medicines": [{**GOOD["medicines"][0], "when": ["night", "morning", "made_up"]}]}
    assert run(visit.extract(FakeLLM([json.dumps(bad)]), TURNS))[0]["medicines"][0]["when"] == ["morning"]


def test_transcript_with_no_medicines_gives_empty_lists():
    turns = [{"speaker": "partner", "text": "Namaste, aaj aap kaise hain?"}]
    s, _ = run(visit.extract(FakeLLM([json.dumps(GOOD)]), turns))
    assert s["medicines"] == [] and s["tests"] == [] and s["warning_signs"] == []


@pytest.mark.parametrize("reply", ["", "not json", json.dumps({"replies": ["a", "b", "c"]}), "{\"medicines\": 3}"])
def test_fallback_when_the_llm_fails(reply):
    s, src = run(visit.extract(FakeLLM([reply]), TURNS))
    assert src == "fallback"
    m = s["medicines"][0]
    assert (m["name"], m["dose"], m["days"]) == ("Pantoprazole", "40 mg", 14)
    assert set(m["when"]) == {"morning", "empty_stomach"}
    assert [t["en"] for t in s["tests"]] == ["Blood test"]
    assert "Monday" in s["next_visit"]["en"]
    assert "turant" in s["warning_signs"][0]["en"]
    assert s["questions_asked"][0]["en"] == "Kya main chai pi sakta hoon?"


def test_fallback_reads_devanagari_names_and_digits():
    s = visit.fallback(HINDI)
    m = s["medicines"][0]
    assert (m["name"], m["dose"], m["days"]) == ("Pantoprazole", "40 mg", 14)
    assert s["tests"][0]["en"] == "Blood test" and "सोमवार" in s["next_visit"]["hi"] and s["warning_signs"]


def test_llm_latin_name_matches_devanagari_caption():
    s = visit.sanitise(GOOD, HINDI)
    assert s["medicines"][0]["name"] == "Pantoprazole" and s["medicines"][0]["dose"] == "40 mg"


def test_fallback_never_invents():
    s = visit.fallback([{"speaker": "partner", "text": "Aap aaram kijiye aur paani piyo."}])
    assert s["medicines"] == [] and s["tests"] == [] and s["next_visit"] is None


def test_read_back_language_and_numbers():
    s = visit.sanitise(GOOD, TURNS)
    hi, en = visit.read_back(s, "hi-IN"), visit.read_back(s, "en-IN")
    assert script_of(hi) == "DEVANAGARI" and "40 mg" in hi and "14 दिन तक" in hi and "खाली पेट" in hi
    assert en.startswith("My visit notes.") and "Pantoprazole 40 mg in the morning on an empty stomach for 14 days" in en
    assert visit.text_lang("ta-IN") == "en-IN" and visit.read_back(s, "ta-IN") == en  # speak() translates on the way out
    assert visit.read_back(visit.sanitise({}, TURNS), "en-IN") == "My visit notes.\nNo medicines or tests were noted."


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    with TestClient(create_app(Settings(cache_dir=tmp_path), llm=FakeLLM([json.dumps(GOOD)]))) as c:
        yield c


def test_endpoint(client):
    client.put("/api/profile", json={"name": "Asha", "language": "hi-IN"})
    r = client.post("/api/visit/summary", json={"turns": TURNS}).json()
    assert r["source"] == "llm" and r["lang"] == "hi-IN" and r["text_lang"] == "hi-IN"
    assert script_of(r["text"]["local"]) == "DEVANAGARI" and r["text"]["en"].startswith("My visit notes.")
    assert "डॉक्टर" in r["disclaimer"] and r["summary"]["medicines"][0]["dose"] == "40 mg"
    # the read-back goes through the normal speak flow (clone -> fallback, with the honest badge)
    sp = client.post("/api/speak", json={"text": r["text"]["local"], "lang": "hi-IN", "remember": False})
    assert sp.status_code == 200 and sp.headers["X-Voice"] == "fallback"


def test_endpoint_errors(client):
    assert client.post("/api/visit/summary", json={"turns": []}).status_code == 400
    only_me = [{"speaker": "user", "text": "Kya main chai pi sakta hoon?"}]
    assert client.post("/api/visit/summary", json={"turns": only_me}).status_code == 400
    assert client.post("/api/visit/summary", json={"turns": [{"speaker": "partner", "text": "  "}]}).status_code == 400
    assert client.post("/api/visit/summary", json={"turns": TURNS, "lang": "xx-XX"}).status_code == 400
    assert client.post("/api/visit/summary", json={"turns": [{"speaker": "robot", "text": "hi"}]}).status_code == 422
    assert client.post("/api/visit/summary", json={"turns": TURNS * 101}).status_code == 422


def test_endpoint_fake_mode_uses_the_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    with TestClient(create_app(Settings(cache_dir=tmp_path))) as c:
        r = c.post("/api/visit/summary", json={"turns": TURNS, "lang": "en-IN"}).json()
    assert r["source"] == "fallback" and r["summary"]["medicines"][0]["dose"] == "40 mg" and r["text_lang"] == "en-IN"
    assert r["disclaimer"].startswith("Notes picked out automatically") and "AI" not in r["disclaimer"]  # no AI was used


def test_invented_tests_are_dropped():
    bad = {**GOOD, "tests": [GOOD["tests"][0], {"en": "MRI of the brain", "hi": "दिमाग का एमआरआई", "quote": Q},
                             {"en": "Liver panel", "hi": "लिवर पैनल", "quote": Q}], "advice": [{"en": "Get an X-ray", "hi": "एक्स-रे कराएँ", "quote": Q}]}
    s, _ = run(visit.extract(FakeLLM([json.dumps(bad)]), TURNS))
    assert [t["en"] for t in s["tests"]] == ["Blood test"] and s["advice"] == []


@pytest.mark.parametrize("latin,dev", [("Pantoprazole", "पेंटोप्रज़ोल"), ("Pantoprazole", "पैन्टोप्राजोल"), ("Paracetamol", "पैरासीटामॉल"),
                                       ("Metformin", "मेटफ़ॉर्मिन"), ("Azithromycin", "एज़िथ्रोमाइसिन"), ("Amoxicillin", "अमॉक्सीसिलीन")])
def test_devanagari_spellings_not_in_the_lexicon_still_match(latin, dev):
    turns = [{"speaker": "partner", "text": f"आपको {dev} 500 mg रात को लेनी है।"}]
    assert visit.sanitise({"medicines": [{"name": latin, "dose": "500 mg", "when": ["night"], "days": None}]}, turns)["medicines"][0]["name"] == latin
    assert visit.fallback(turns)["medicines"][0]["name"] == latin


def test_skeleton_does_not_confuse_different_medicines():
    turns = [{"speaker": "partner", "text": "आपको पैंटोप्राजोल 40 mg लेनी है।"}]
    for other in ["Omeprazole", "Paracetamol", "Amlodipine", "Atorvastatin"]:
        assert visit.sanitise({"medicines": [{"name": other, "dose": "40 mg"}]}, turns)["medicines"] == []
