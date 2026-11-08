"""Quick phrases per language. Languages without a list use English; speak() translates on the way out."""

PHRASES = {
    "en-IN": ["Yes", "No", "Please say that again", "Thank you", "I need water", "I am in pain", "I need the toilet",
              "I am tired", "Please call my son", "Please call my daughter", "I am feeling better", "Please help me"],
    "hi-IN": ["हाँ", "नहीं", "फिर से बोलिए", "धन्यवाद", "मुझे पानी चाहिए", "मुझे दर्द हो रहा है", "मुझे बाथरूम जाना है",
              "मैं थक गया हूँ", "मेरे बेटे को बुलाइए", "मेरी बेटी को बुलाइए", "अब मैं बेहतर हूँ", "मेरी मदद कीजिए"],
    "ta-IN": ["ஆமாம்", "இல்லை", "மறுபடியும் சொல்லுங்க", "நன்றி", "எனக்கு தண்ணீர் வேணும்", "எனக்கு வலிக்குது",
              "நான் கழிவறைக்கு போகணும்", "எனக்கு களைப்பா இருக்கு", "என் மகனை கூப்பிடுங்க", "என் மகளை கூப்பிடுங்க",
              "இப்போ பரவாயில்லை", "எனக்கு உதவி பண்ணுங்க"],
}

SOS = {
    "en-IN": "Emergency! I cannot speak. Please help me and call a doctor or my family now.",
    "hi-IN": "आपातकाल! मैं बोल नहीं सकता। कृपया मेरी मदद कीजिए और अभी डॉक्टर या मेरे परिवार को बुलाइए।",
    "ta-IN": "அவசரம்! என்னால் பேச முடியாது. தயவுசெய்து எனக்கு உதவுங்கள், உடனே டாக்டரையோ என் குடும்பத்தையோ கூப்பிடுங்கள்.",
}


def default_phrases(lang: str) -> list[str]:
    return PHRASES.get(lang, PHRASES["en-IN"])


def sos_text(lang: str) -> str:
    return SOS.get(lang, SOS["en-IN"])
