// The 10 languages Gnani Prisma and Timbre support (same list as backend/awaaz/langs.py).
export const LANGS = [
  { code: "hi-IN", name: "Hindi", native: "हिन्दी" },
  { code: "en-IN", name: "English", native: "English" },
  { code: "ta-IN", name: "Tamil", native: "தமிழ்" },
  { code: "bn-IN", name: "Bengali", native: "বাংলা" },
  { code: "te-IN", name: "Telugu", native: "తెలుగు" },
  { code: "kn-IN", name: "Kannada", native: "ಕನ್ನಡ" },
  { code: "ml-IN", name: "Malayalam", native: "മലയാളം" },
  { code: "mr-IN", name: "Marathi", native: "मराठी" },
  { code: "gu-IN", name: "Gujarati", native: "ગુજરાતી" },
  { code: "pa-IN", name: "Punjabi", native: "ਪੰਜਾਬੀ" },
];
export const langOf = (code) => LANGS.find((l) => l.code === code) || LANGS[0];
export const langLabel = (code) => {
  const l = langOf(code);
  return l.native === l.name ? l.name : `${l.native} · ${l.name}`;
};

// Timbre v3.0 voices: each speaks all 10 languages. Used until (or whenever) the cloned voice is unavailable.
export const VOICES = {
  female: ["Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika"],
  male: ["Avinash", "Prakash", "Harshad", "Devansh", "Shubham", "Yashraj"],
};

export const CONDITIONS = [
  "Throat or voice box surgery",
  "Mouth or tongue cancer surgery",
  "Stroke",
  "ALS / MND",
  "Parkinson's",
  "Other",
];
