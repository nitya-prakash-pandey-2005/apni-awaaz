"""Facts of the live session replayed by the static demo (10 Nov 2026, real Gnani + Groq, synthetic voices only).

Every value below was observed in that run (docs/test-log.md, 10 Nov 19:30 row). The "old voice notes" and the nurse
are synthetic Gnani Timbre v3.0 voices (Shubham and Kalpana); no real person's voice is used anywhere.
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "frontend" / "demo"  # copied to dist/demo by `npm run build:demo`
LIVE_DB = REPO / "cache" / "awaaz.db.screenshots-2026-11-10"  # git-ignored database left by that run
LANGS = ["hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "bn-IN", "mr-IN", "gu-IN", "pa-IN"]

# The voice was deleted at the end of the run (the live "Delete my voice" test). The demo shows the state before that.
CONSENT_AT = "2026-11-10T14:00:59+00:00"  # 19:30:59 IST, shown on the Profile page during the run

# Voice bank: the 3 synthetic notes as checked live (speech seconds, SNR and Prisma v3.0 transcript from the run).
NOTES = [
    {"name": "PTT-20240312-WA0007.wav", "speech_s": 7.64, "snr_db": 101.4, "ok": True, "reasons": [],
     "text": "अरे बेटा, मैं घर पहुँच गया हूँ, रास्ते में थोड़ी बारिश थी पर सब ठीक है, तुम खाना खा लेना। और मां को बोल देना कि मैं शाम को phone करूंगा।"},
    {"name": "PTT-20240521-WA0015.wav", "speech_s": 6.12, "snr_db": 105.3, "ok": True, "reasons": [],
     "text": "हाँ रमेश भाई, कल सुबह दस बजे मंदिर के पास मिलते हैं। वो सारे कागज साथ लेकर आना, बाकी बात वहीं आराम से करेंगे।"},
    {"name": "PTT-20240602-WA0021.wav", "speech_s": 1.02, "snr_db": 101.8, "ok": False, "reasons": ["too short"],
     "text": "हाँ, ठीक है।"},
]
USED_NOTE = "PTT-20240521-WA0015.wav"  # the clearest good clip, used for the embedding
TEST_TEXT, TEST_LANG = "नमस्ते, ये मेरी आवाज़ है।", "hi-IN"

# Everything spoken in the cloned voice (vachana-vc-v1) during the run: typed text, language, what was spoken.
SPOKEN = [
    (TEST_TEXT, TEST_LANG, TEST_TEXT),
    ("मेरा गला ठीक नहीं है, पर मैं आपकी हर बात सुन रहा हूँ।", "hi-IN", "मेरा गला ठीक नहीं है, पर मैं आपकी हर बात सुन रहा हूँ।"),
    ("mujhe paani chahiye", "hi-IN", "मुझे पानी चाहिए"),  # romanised, rewritten by the LLM before cloning
    ("வணக்கம் டாக்டர், நான் இப்போ நல்லா இருக்கேன்.", "ta-IN", "வணக்கம் டாக்டர், நான் இப்போ நல்லா இருக்கேன்."),
    ("मैं ठीक हूँ, धन्यवाद।", "hi-IN", "मैं ठीक हूँ, धन्यवाद।"),  # the reply tapped in Converse
    ("मुझे थोड़ा आराम करना है।", "hi-IN", "मुझे थोड़ा आराम करना है।"),
    ("कृपया डॉक्टर को बुलाइए।", "hi-IN", "कृपया डॉक्टर को बुलाइए।"),
]
SOS_LANGS = ["hi-IN", "ta-IN"]  # the SOS pressed with Tamil as the second language

# Converse: the nurse's first sentence, as Prisma v3.0 captioned it live, and the 3 replies the LLM suggested.
NURSE_CAPTIONS = ["नमस्ते शर्मा जी।", "आज आपको कैसा लग रहा है?"]
SUGGESTIONS = ["मैं ठीक हूँ, धन्यवाद।", "थोड़ा थका हुआ हूँ।", "सब कुछ ठीक है।"]
