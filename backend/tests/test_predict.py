import pytest
from fastapi.testclient import TestClient
from voice_core.config import Settings
from voice_core.testing import FakeLLM

from awaaz.app import create_app
from awaaz.predict import corpus, keystrokes_saved, lexicon, predict, words


def labels(text, lang="en-IN", history=()):
    return [s["label"] for s in predict(text, lang, history)]


def test_lexicon_covers_native_and_romanised_scripts():
    lex = lexicon()
    assert {"en-IN", "hi-IN", "ta-IN"} <= set(lex) and all(len(v) >= 30 for v in lex.values())
    assert any("पानी" in p for p in lex["hi-IN"]) and any("paani" in p for p in lex["hi-IN"])
    assert any("தண்ணீர்" in p for p in lex["ta-IN"]) and any("thanni" in p for p in lex["ta-IN"])


def test_words_trims_punctuation_and_case():
    assert words("  Mujhe PAANI chahiye। ") == ["mujhe", "paani", "chahiye"]


def test_phrase_completion_from_a_partial_word():
    out = predict("I need wa", "en-IN")
    assert out[0] == {"text": "I need water", "label": "I need water", "kind": "phrase"}


def test_romanised_and_native_hindi():
    assert labels("mujhe p", "hi-IN")[:2] == ["mujhe paani chahiye", "mujhe pyaas lagi hai"]
    assert "मुझे पानी चाहिए" in labels("मुझे ", "hi-IN")
    assert all(not any("ऀ" <= c <= "ॿ" for c in s) for s in labels("mujhe p", "hi-IN"))  # stays in the typed script


def test_next_word_after_a_space_and_word_completion():
    out = predict("please call ", "en-IN")
    words_ = [s for s in out if s["kind"] == "word"]
    assert words_ and words_[0]["text"].startswith("please call ") and words_[0]["text"].endswith(" ")
    assert predict("I n", "en-IN")[-1] == {"text": "I need ", "label": "need", "kind": "word"}


def test_context_from_the_middle_of_a_sentence_keeps_what_was_typed():
    out = predict("ok please c", "en-IN")
    assert out[0]["text"] == "ok Please call my son" and out[0]["kind"] == "phrase"


def test_personal_history_ranks_above_the_lexicon_and_more_uses_rank_higher():
    hist = [("Please call my son Ravi", 1)]
    assert labels("please call my ", history=hist)[0] == "Please call my son Ravi"
    hist = [("Please bring my glasses", 1), ("Please bring tea", 6)]
    assert labels("please bri", history=hist)[:2] == ["Please bring tea", "Please bring my glasses"]


def test_at_most_five_no_duplicates_and_never_the_text_itself():
    for text in ["", "I", "I need", "please ", "mujhe ", "x"]:
        out = predict(text, "hi-IN" if "mujhe" in text else "en-IN")
        keys = [s["text"].strip().lower() for s in out]
        assert len(out) <= 5 and len(keys) == len(set(keys)) and text.strip().lower() not in keys
    assert predict("I need water", "en-IN") == [] or all(s["text"].strip() != "I need water" for s in predict("I need water", "en-IN"))
    assert predict("zzz", "en-IN") == []


def test_languages_without_a_lexicon_use_english_and_history_dedupes():
    assert corpus("te-IN")[0][0] == lexicon()["en-IN"][0]
    c = corpus("en-IN", [("I need water.", 2)])
    assert c[0] == ("I need water", 7) and sum(1 for t, _ in c if t.lower() == "i need water") == 1


@pytest.mark.parametrize("pressed,text,pct", [(3, "I need water", 75), (12, "I need water", 0), (20, "abc", 0), (0, "", 0)])
def test_keystrokes_saved(pressed, text, pct):
    assert keystrokes_saved(pressed, text) == pct


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("AWAAZ_FAKE", "1")
    with TestClient(create_app(Settings(cache_dir=tmp_path), llm=FakeLLM(["x"] * 5))) as c:
        yield c


def test_predict_endpoint_learns_from_what_was_spoken(client):
    assert client.get("/api/predict", params={"text": "mujhe p", "lang": "hi-IN"}).json()["suggestions"][0]["label"] == "mujhe paani chahiye"
    for _ in range(2):
        assert client.post("/api/speak", json={"text": "mujhe pakoda chahiye", "lang": "hi-IN"}).status_code == 200
    top = client.get("/api/predict", params={"text": "mujhe p", "lang": "hi-IN"}).json()["suggestions"][0]
    assert top == {"text": "mujhe pakoda chahiye", "label": "mujhe pakoda chahiye", "kind": "phrase"}
    assert client.get("/api/predict", params={"text": "a", "lang": "xx-IN"}).status_code == 400
