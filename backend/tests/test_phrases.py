from awaaz.langs import LANGS, dominant_script
from awaaz.phrases import (QUICK, QUICK_KEYS, SOS, TEST_PHRASES, default_replies, quick_phrases, sos_text,
                           voice_test_phrase)
from awaaz.profiles import ProfileStore


def test_every_language_has_all_built_in_words():
    assert set(QUICK) == set(LANGS) == set(TEST_PHRASES) == set(SOS)
    for code, texts in QUICK.items():
        assert len(texts) == len(QUICK_KEYS) == 12, code
        assert len(set(texts)) == 12, code


def test_built_in_words_are_written_in_the_language_s_own_script():
    for code, L in LANGS.items():
        for text in [*QUICK[code], TEST_PHRASES[code], *SOS[code].values()]:
            assert dominant_script(text) == L.script, (code, text)


def test_quick_phrases_shape():
    tiles = quick_phrases("ta-IN")
    assert tiles[0] == {"key": "water", "text": "எனக்கு தண்ணீர் வேண்டும்", "gloss": "I need water", "icon": "GlassWater"}
    assert quick_phrases("xx-YY") == quick_phrases("hi-IN")
    assert voice_test_phrase("hi-IN") == "नमस्ते, ये मेरी आवाज़ है।"


def test_sos_text_with_and_without_family():
    full = sos_text("hi-IN", "Asha", ["Ravi", " Meena "])
    assert full == ("कृपया मेरी मदद कीजिए। मुझे बोलने में परेशानी है। मेरा नाम Asha है। "
                    "कृपया मेरे परिवार को फ़ोन कीजिए: Ravi, Meena।")
    assert sos_text("en-IN") == "Please help me. I have trouble speaking. Please call my family."


def test_default_replies_prefer_learned_phrases(tmp_path):
    assert default_replies("hi-IN") == ["हाँ", "नहीं", "एक मिनट रुकिए, मुझे लिखने दीजिए"]
    store = ProfileStore(tmp_path / "a.db")
    for text in ["मुझे पानी चाहिए", "हाँ", "मुझे पानी चाहिए"]:
        store.add_phrase_use(text, "hi-IN")
    assert default_replies("hi-IN", store) == ["मुझे पानी चाहिए", "हाँ", "नहीं"]  # learned first, no duplicates
