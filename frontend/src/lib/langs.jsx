export const LANGS = [
  { value: "hi-IN", label: "हिन्दी" }, { value: "en-IN", label: "English" }, { value: "ta-IN", label: "தமிழ்" },
  { value: "te-IN", label: "తెలుగు" }, { value: "kn-IN", label: "ಕನ್ನಡ" }, { value: "ml-IN", label: "മലയാളം" },
  { value: "bn-IN", label: "বাংলা" }, { value: "mr-IN", label: "मराठी" }, { value: "gu-IN", label: "ગુજરાતી" },
  { value: "pa-IN", label: "ਪੰਜਾਬੀ" },
];
export const langName = (code) => LANGS.find((l) => l.value === code)?.label || code;
export const VOICES = ["Shivani", "Lakshmi", "Kalpana", "Chetana", "Vasudha", "Riyaa", "Tarika",
  "Avinash", "Prakash", "Harshad", "Devansh", "Shubham", "Yashraj"]; // Timbre v3.0: every voice speaks all 10 languages

export function LangChips({ value, onChange }) {
  return (
    <div className="lang-chips" role="radiogroup" aria-label="Language">
      {LANGS.map((l) => (
        <button key={l.value} type="button" role="radio" aria-checked={value === l.value}
          className={`chip ${value === l.value ? "on" : ""}`} onClick={() => onChange(l.value)}>{l.label}</button>
      ))}
    </div>
  );
}
