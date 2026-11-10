import itertools

import pytest
from fastapi.testclient import TestClient
from voice_core.config import Settings
from voice_core.testing import FakeLLM

from awaaz.app import create_app
from awaaz.pain import sentence, template_lang, templates

T = templates()
LANGS = ["hi-IN", "ta-IN", "en-IN"]
# Written out independently of pain.json, so a wrong gender in the data fails here.
HINDI_GENDER = {"सिर": "m", "आँख": "f", "कान": "m", "मुँह": "m", "गले": "m", "गर्दन": "f", "छाती": "f", "पेट": "m",
                "पीठ": "f", "कमर": "f", "बाँह": "f", "हाथ": "m", "टाँग": "f", "पैर": "m"}
HI_NUM = ["शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ", "दस"]


def combos():
    for p in T["parts"]:
        for side in (["left", "right"] if p["sided"] else [None]):
            for kind, since in itertools.product(T["types"], T["since"]):
                yield p, side, kind, since


def test_examples():
    assert sentence("arm", 7, "sharp", "hi-IN", "left") == "मेरी बाईं बाँह में तेज़ दर्द है, दस में से सात।"
    assert sentence("hand", 4, "burning", "hi-IN", "right", "yesterday") == "मेरे दाएँ हाथ में कल से जलन है, दस में से चार।"
    assert sentence("throat", 3, "dull", "hi-IN") == "मेरे गले में हल्का-हल्का दर्द है, दस में से तीन।"
    assert sentence("arm", 7, "sharp", "ta-IN", "left") == "என் இடது கையில் கூர்மையான வலி இருக்கு, பத்தில் ஏழு."
    assert sentence("foot", 10, "itching", "en-IN", "right", "just_now") == \
        "I have an itch in my right foot that started just now, ten out of ten."


def test_hindi_gender_data_matches_independent_table():
    assert {p["hi"]["noun"]: p["hi"]["g"] for p in T["parts"]} == HINDI_GENDER


@pytest.mark.parametrize("lang", LANGS)
def test_every_part_side_type_onset_and_level(lang):
    L = T["langs"][lang]
    n = 0
    for p, side, kind, since in combos():
        for level in range(11):
            s = sentence(p["id"], level, kind, lang, side, since)
            n += 1
            assert "{" not in s and "  " not in s and s == s.strip()
            assert L["types"][kind] in s
            if since:
                assert L["since"][since].strip() in s
            if lang == "hi-IN":
                g = HINDI_GENDER[p["hi"]["noun"]]
                words = s.split()
                assert words[0] == ("मेरे" if g == "m" else "मेरी")  # possessive agrees, oblique masculine
                if side:
                    want = {("left", "m"): "बाएँ", ("left", "f"): "बाईं", ("right", "m"): "दाएँ", ("right", "f"): "दाईं"}
                    assert words[1] == want[(side, g)]
                assert f"{p['hi']['noun']} में " in s  # the postposition follows the (oblique) noun
                assert s.endswith(f"है, दस में से {HI_NUM[level]}।")
            elif lang == "ta-IN":
                assert s.startswith("என் ") and p["ta"] in s and s.endswith(f"இருக்கு, பத்தில் {L['numbers'][level]}.")
                if side:
                    assert ("இடது " if side == "left" else "வலது ") in s
            else:
                assert s.startswith("I have ") and f"in my {side + ' ' if side else ''}{p['en']}" in s
                assert s.endswith(f", {L['numbers'][level]} out of ten.")
    assert n == 20 * 5 * 4 * 11  # 8 one-sided + 6 two-sided parts x 5 types x 4 onsets x 11 levels


def test_other_languages_fall_back_to_english_text():
    assert template_lang("te-IN") == "en-IN" and template_lang("hi-IN") == "hi-IN"
    assert sentence("chest", 6, "throbbing", "bn-IN") == sentence("chest", 6, "throbbing", "en-IN")


@pytest.mark.parametrize("args", [("knee", 5, "sharp"), ("arm", 5, "sharp"), ("chest", 5, "sharp", "hi-IN", "left"),
                                  ("chest", 11, "sharp"), ("chest", -1, "sharp"), ("chest", 5, "stabby"),
                                  ("chest", 5, "sharp", "hi-IN", None, "last week")])
def test_invalid_input_is_rejected(args):
    with pytest.raises(ValueError):
        sentence(*args)


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    with TestClient(create_app(Settings(cache_dir=tmp_path), llm=FakeLLM(["My left arm hurts."] * 5))) as c:
        yield c


def test_pain_endpoint_then_speak(client):
    r = client.post("/api/pain/sentence", json={"part": "arm", "side": "left", "level": 7, "type": "sharp", "lang": "hi-IN"})
    assert r.json() == {"text": "मेरी बाईं बाँह में तेज़ दर्द है, दस में से सात।", "lang": "hi-IN", "template_lang": "hi-IN"}
    te = client.post("/api/pain/sentence", json={"part": "head", "level": 2, "type": "dull", "lang": "te-IN"}).json()
    assert te["template_lang"] == "en-IN" and te["text"].startswith("I have")
    spoken = client.post("/api/speak", json={"text": r.json()["text"], "lang": "hi-IN"})
    assert spoken.status_code == 200 and spoken.headers["content-type"] == "audio/wav"


def test_pain_endpoint_rejects_bad_input(client):
    assert client.post("/api/pain/sentence", json={"part": "arm", "level": 3, "type": "sharp"}).status_code == 400
    assert client.post("/api/pain/sentence", json={"part": "head", "level": 3, "type": "sharp", "lang": "xx"}).status_code == 400
