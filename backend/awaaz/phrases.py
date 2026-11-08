"""Built-in words: the 12 quick phrases, the voice test phrase and the SOS message, in all 10 languages.

Wording is gender-neutral on purpose (Hindi "मुझे थकान हो रही है" rather than "मैं थक गया/गई हूँ"),
so the same tile works for every user. Keep the tile order fixed: people who tap phrases every day
rely on muscle memory. Learned phrases are shown separately ("Often said"), not mixed in.
"""

from __future__ import annotations

from .langs import LANGS

# key, English gloss, lucide icon name (the frontend maps the icon)
QUICK_KEYS: list[tuple[str, str, str]] = [
    ("water", "I need water", "GlassWater"),
    ("pain", "I am in pain", "Bandage"),
    ("toilet", "I need the toilet", "Toilet"),
    ("yes", "Yes", "Check"),
    ("no", "No", "X"),
    ("thanks", "Thank you", "HeartHandshake"),
    ("son", "Please call my son", "PhoneCall"),
    ("daughter", "Please call my daughter", "PhoneCall"),
    ("tired", "I feel tired", "BedDouble"),
    ("hungry", "I am hungry", "Utensils"),
    ("wait", "One minute, let me type", "Hourglass"),
    ("doctor", "Please call the doctor or nurse", "Stethoscope"),
]

QUICK: dict[str, list[str]] = {
    "hi-IN": ["मुझे पानी चाहिए", "मुझे दर्द हो रहा है", "मुझे टॉयलेट जाना है", "हाँ", "नहीं", "धन्यवाद",
              "मेरे बेटे को बुलाइए", "मेरी बेटी को बुलाइए", "मुझे थकान हो रही है", "मुझे भूख लगी है",
              "एक मिनट रुकिए, मुझे लिखने दीजिए", "डॉक्टर या नर्स को बुलाइए"],
    "en-IN": ["I need water", "I am in pain", "I need the toilet", "Yes", "No", "Thank you",
              "Please call my son", "Please call my daughter", "I feel tired", "I am hungry",
              "One minute, let me type", "Please call the doctor or nurse"],
    "ta-IN": ["எனக்கு தண்ணீர் வேண்டும்", "எனக்கு வலிக்கிறது", "நான் கழிவறைக்குப் போக வேண்டும்", "ஆம்", "இல்லை",
              "நன்றி", "என் மகனைக் கூப்பிடுங்கள்", "என் மகளைக் கூப்பிடுங்கள்", "எனக்குச் சோர்வாக இருக்கிறது",
              "எனக்குப் பசிக்கிறது", "ஒரு நிமிடம், நான் எழுதுகிறேன்", "டாக்டரையோ நர்ஸையோ கூப்பிடுங்கள்"],
    "bn-IN": ["আমার জল চাই", "আমার ব্যথা করছে", "আমি টয়লেটে যাব", "হ্যাঁ", "না", "ধন্যবাদ",
              "আমার ছেলেকে ডাকুন", "আমার মেয়েকে ডাকুন", "আমি ক্লান্ত", "আমার খিদে পেয়েছে",
              "এক মিনিট, আমাকে লিখতে দিন", "ডাক্তার বা নার্সকে ডাকুন"],
    "te-IN": ["నాకు నీళ్ళు కావాలి", "నాకు నొప్పిగా ఉంది", "నేను టాయిలెట్‌కి వెళ్ళాలి", "అవును", "లేదు",
              "ధన్యవాదాలు", "మా అబ్బాయిని పిలవండి", "మా అమ్మాయిని పిలవండి", "నాకు అలసటగా ఉంది",
              "నాకు ఆకలిగా ఉంది", "ఒక్క నిమిషం, నన్ను రాయనివ్వండి", "డాక్టర్‌ని లేదా నర్సుని పిలవండి"],
    "kn-IN": ["ನನಗೆ ನೀರು ಬೇಕು", "ನನಗೆ ನೋವಾಗುತ್ತಿದೆ", "ನಾನು ಶೌಚಾಲಯಕ್ಕೆ ಹೋಗಬೇಕು", "ಹೌದು", "ಇಲ್ಲ",
              "ಧನ್ಯವಾದಗಳು", "ನನ್ನ ಮಗನನ್ನು ಕರೆಯಿರಿ", "ನನ್ನ ಮಗಳನ್ನು ಕರೆಯಿರಿ", "ನನಗೆ ಸುಸ್ತಾಗಿದೆ",
              "ನನಗೆ ಹಸಿವಾಗಿದೆ", "ಒಂದು ನಿಮಿಷ, ನನಗೆ ಬರೆಯಲು ಬಿಡಿ", "ಡಾಕ್ಟರ್ ಅಥವಾ ನರ್ಸ್ ಅನ್ನು ಕರೆಯಿರಿ"],
    "ml-IN": ["എനിക്ക് വെള്ളം വേണം", "എനിക്ക് വേദനിക്കുന്നു", "എനിക്ക് ടോയ്‌ലറ്റിൽ പോകണം", "അതെ", "ഇല്ല",
              "നന്ദി", "എന്റെ മകനെ വിളിക്കൂ", "എന്റെ മകളെ വിളിക്കൂ", "എനിക്ക് ക്ഷീണമുണ്ട്",
              "എനിക്ക് വിശക്കുന്നു", "ഒരു മിനിറ്റ്, ഞാൻ എഴുതട്ടെ", "ഡോക്ടറെയോ നഴ്സിനെയോ വിളിക്കൂ"],
    "mr-IN": ["मला पाणी हवे आहे", "मला दुखत आहे", "मला शौचालयात जायचे आहे", "हो", "नाही", "धन्यवाद",
              "माझ्या मुलाला बोलवा", "माझ्या मुलीला बोलवा", "मला थकवा आला आहे", "मला भूक लागली आहे",
              "एक मिनिट थांबा, मला लिहू द्या", "डॉक्टर किंवा नर्सला बोलवा"],
    "gu-IN": ["મને પાણી જોઈએ છે", "મને દુખાવો થાય છે", "મારે ટોઇલેટ જવું છે", "હા", "ના", "આભાર",
              "મારા દીકરાને બોલાવો", "મારી દીકરીને બોલાવો", "મને થાક લાગે છે", "મને ભૂખ લાગી છે",
              "એક મિનિટ, મને લખવા દો", "ડૉક્ટર અથવા નર્સને બોલાવો"],
    "pa-IN": ["ਮੈਨੂੰ ਪਾਣੀ ਚਾਹੀਦਾ ਹੈ", "ਮੈਨੂੰ ਦਰਦ ਹੋ ਰਿਹਾ ਹੈ", "ਮੈਂ ਟਾਇਲਟ ਜਾਣਾ ਹੈ", "ਹਾਂ", "ਨਹੀਂ", "ਧੰਨਵਾਦ",
              "ਮੇਰੇ ਪੁੱਤਰ ਨੂੰ ਬੁਲਾਓ", "ਮੇਰੀ ਧੀ ਨੂੰ ਬੁਲਾਓ", "ਮੈਨੂੰ ਥਕਾਵਟ ਹੋ ਰਹੀ ਹੈ", "ਮੈਨੂੰ ਭੁੱਖ ਲੱਗੀ ਹੈ",
              "ਇੱਕ ਮਿੰਟ, ਮੈਨੂੰ ਲਿਖਣ ਦਿਓ", "ਡਾਕਟਰ ਜਾਂ ਨਰਸ ਨੂੰ ਬੁਲਾਓ"],
}

TEST_PHRASES: dict[str, str] = {
    "hi-IN": "नमस्ते, ये मेरी आवाज़ है।",
    "en-IN": "Hello, this is my voice.",
    "ta-IN": "வணக்கம், இது என் குரல்.",
    "bn-IN": "নমস্কার, এটা আমার কণ্ঠস্বর।",
    "te-IN": "నమస్కారం, ఇది నా గొంతు.",
    "kn-IN": "ನಮಸ್ಕಾರ, ಇದು ನನ್ನ ಧ್ವನಿ.",
    "ml-IN": "നമസ്കാരം, ഇത് എന്റെ ശബ്ദമാണ്.",
    "mr-IN": "नमस्कार, हा माझा आवाज आहे.",
    "gu-IN": "નમસ્તે, આ મારો અવાજ છે.",
    "pa-IN": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ, ਇਹ ਮੇਰੀ ਆਵਾਜ਼ ਹੈ।",
}

# help / cannot speak / my name is / please call my family (with names, without)
SOS: dict[str, dict[str, str]] = {
    "hi-IN": {"help": "कृपया मेरी मदद कीजिए।", "speak": "मुझे बोलने में परेशानी है।", "name": "मेरा नाम {name} है।",
              "family": "कृपया मेरे परिवार को फ़ोन कीजिए: {family}।", "family_none": "कृपया मेरे परिवार को फ़ोन कीजिए।"},
    "en-IN": {"help": "Please help me.", "speak": "I have trouble speaking.", "name": "My name is {name}.",
              "family": "Please call my family: {family}.", "family_none": "Please call my family."},
    "ta-IN": {"help": "தயவுசெய்து எனக்கு உதவுங்கள்.", "speak": "என்னால் பேச முடியவில்லை.", "name": "என் பெயர் {name}.",
              "family": "என் குடும்பத்தினரை அழையுங்கள்: {family}.", "family_none": "என் குடும்பத்தினரை அழையுங்கள்."},
    "bn-IN": {"help": "দয়া করে আমাকে সাহায্য করুন।", "speak": "আমি কথা বলতে পারছি না।", "name": "আমার নাম {name}।",
              "family": "আমার পরিবারকে ফোন করুন: {family}।", "family_none": "আমার পরিবারকে ফোন করুন।"},
    "te-IN": {"help": "దయచేసి నాకు సహాయం చేయండి.", "speak": "నేను మాట్లాడలేను.", "name": "నా పేరు {name}.",
              "family": "దయచేసి మా కుటుంబానికి ఫోన్ చేయండి: {family}.", "family_none": "దయచేసి మా కుటుంబానికి ఫోన్ చేయండి."},
    "kn-IN": {"help": "ದಯವಿಟ್ಟು ನನಗೆ ಸಹಾಯ ಮಾಡಿ.", "speak": "ನನಗೆ ಮಾತನಾಡಲು ಆಗುವುದಿಲ್ಲ.", "name": "ನನ್ನ ಹೆಸರು {name}.",
              "family": "ದಯವಿಟ್ಟು ನನ್ನ ಕುಟುಂಬಕ್ಕೆ ಫೋನ್ ಮಾಡಿ: {family}.", "family_none": "ದಯವಿಟ್ಟು ನನ್ನ ಕುಟುಂಬಕ್ಕೆ ಫೋನ್ ಮಾಡಿ."},
    "ml-IN": {"help": "ദയവായി എന്നെ സഹായിക്കൂ.", "speak": "എനിക്ക് സംസാരിക്കാൻ കഴിയില്ല.", "name": "എന്റെ പേര് {name}.",
              "family": "ദയവായി എന്റെ കുടുംബത്തെ വിളിക്കൂ: {family}.", "family_none": "ദയവായി എന്റെ കുടുംബത്തെ വിളിക്കൂ."},
    "mr-IN": {"help": "कृपया मला मदत करा.", "speak": "मला बोलता येत नाही.", "name": "माझे नाव {name} आहे.",
              "family": "कृपया माझ्या कुटुंबाला फोन करा: {family}.", "family_none": "कृपया माझ्या कुटुंबाला फोन करा."},
    "gu-IN": {"help": "કૃપા કરીને મને મદદ કરો.", "speak": "મને બોલવામાં તકલીફ છે.", "name": "મારું નામ {name} છે.",
              "family": "કૃપા કરીને મારા પરિવારને ફોન કરો: {family}.", "family_none": "કૃપા કરીને મારા પરિવારને ફોન કરો."},
    "pa-IN": {"help": "ਕਿਰਪਾ ਕਰਕੇ ਮੇਰੀ ਮਦਦ ਕਰੋ।", "speak": "ਮੈਨੂੰ ਬੋਲਣ ਵਿੱਚ ਮੁਸ਼ਕਲ ਹੈ।", "name": "ਮੇਰਾ ਨਾਮ {name} ਹੈ।",
              "family": "ਕਿਰਪਾ ਕਰਕੇ ਮੇਰੇ ਪਰਿਵਾਰ ਨੂੰ ਫ਼ੋਨ ਕਰੋ: {family}।", "family_none": "ਕਿਰਪਾ ਕਰਕੇ ਮੇਰੇ ਪਰਿਵਾਰ ਨੂੰ ਫ਼ੋਨ ਕਰੋ।"},
}

DEFAULT_REPLY_KEYS = ("yes", "no", "wait")


def _lang_or_hindi(code: str) -> str:
    return code if code in LANGS else "hi-IN"


def quick_phrases(code: str) -> list[dict]:
    texts = QUICK[_lang_or_hindi(code)]
    return [{"key": k, "text": t, "gloss": g, "icon": i} for (k, g, i), t in zip(QUICK_KEYS, texts)]


def quick_text(code: str, key: str) -> str:
    keys = [k for k, _, _ in QUICK_KEYS]
    return QUICK[_lang_or_hindi(code)][keys.index(key)]


def voice_test_phrase(code: str) -> str:
    return TEST_PHRASES[_lang_or_hindi(code)]


def sos_text(code: str, name: str = "", family: list[str] | None = None) -> str:
    t = SOS[_lang_or_hindi(code)]
    family = [f.strip() for f in (family or []) if f and f.strip()]
    parts = [t["help"], t["speak"]]
    if name.strip():
        parts.append(t["name"].format(name=name.strip()))
    parts.append(t["family"].format(family=", ".join(family)) if family else t["family_none"])
    return " ".join(parts)


def default_replies(code: str, store=None, n: int = 3) -> list[str]:
    """What to offer when the LLM gives nothing usable: the user's most used phrases, then yes / no / wait."""
    out: list[str] = []
    learned = store.top_phrases(code, n) if store is not None else []
    for text in [*learned, *(quick_text(code, k) for k in DEFAULT_REPLY_KEYS)]:
        if text not in out:
            out.append(text)
    return out[:n]
