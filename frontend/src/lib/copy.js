// Plain-language text for what the backend reports.

// Voice-note quality reasons (backend/awaaz/quality.py codes)
export const REASONS = {
  "too quiet": "This is almost silent. Choose a clip where the voice is clear and close.",
  "too short": "Too short. We need at least 5 seconds of talking.",
  "too long": "Long clip: we use the first 30 seconds.",
  noisy: "Too much background sound or music. A clip from a quiet room works best.",
  clipping: "Too loud, so the sound is distorted. A clip recorded a little further from the phone works better.",
  "few words": "We could not hear clear words. Use a clip where only this person is talking.",
};
export const reasonText = (r) => REASONS[r] || r;

// Why the standard (fallback) voice spoke instead of the user's own voice
export function fallbackNote(meta) {
  if (!meta || meta.voice === "clone") return "";
  switch (meta.reason) {
    case "no_voice": return "Your own voice is not set up yet. Add voice notes in My voice to hear yourself.";
    case "clone_error":
    case "clone_paused": return "Your own voice is not available right now, so a standard voice spoke. We will try your voice again in a minute.";
    case "rate_limited": return "The voice service was busy, so a standard voice spoke this time.";
    default: return "A standard voice spoke this time.";
  }
}
