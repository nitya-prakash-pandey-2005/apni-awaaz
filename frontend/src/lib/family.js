// SOS share to family: one saved contact (kept only in this browser), and a prefilled WhatsApp or SMS message in the
// person's language with a Google Maps link when the browser gives a location. Nothing is sent by the app itself:
// it opens WhatsApp or the SMS app, and the person (or a helper) presses Send.
const KEY = "awaaz.family";

const MSG = {
  "en-IN": { help: "Emergency! I need help now. I cannot speak, please come or call me at once.", at: "My location:", none: "(My location could not be added.)" },
  "hi-IN": { help: "आपातकाल! मुझे अभी मदद चाहिए। कृपया तुरंत आइए या फ़ोन कीजिए।", at: "मेरी लोकेशन:", none: "(लोकेशन नहीं मिल पाई।)" },
  "ta-IN": { help: "அவசரம்! எனக்கு உடனே உதவி வேண்டும். தயவுசெய்து உடனே வாருங்கள் அல்லது அழையுங்கள்.", at: "என் இருப்பிடம்:", none: "(இருப்பிடம் கிடைக்கவில்லை.)" },
};

// Digits only; a 10-digit Indian mobile number gets the 91 country code. Returns "" if it cannot be a phone number.
export function normPhone(raw) {
  let d = String(raw || "").replace(/\D/g, "");
  if (d.length === 11 && d.startsWith("0")) d = d.slice(1);
  if (d.length === 10) d = `91${d}`;
  return d.length >= 11 && d.length <= 15 ? d : "";
}

export const mapsLink = (loc) => `https://maps.google.com/?q=${loc.lat.toFixed(5)},${loc.lng.toFixed(5)}`;

export function sosMessage(lang, loc) {
  const m = MSG[lang] || MSG["en-IN"];
  return `${m.help}\n${loc ? `${m.at} ${mapsLink(loc)}` : m.none}`;
}

export const waLink = (phone, text) => `https://wa.me/${normPhone(phone)}?text=${encodeURIComponent(text)}`;
// "?&body=" is read by both Android and iOS messaging apps.
export const smsLink = (phone, text) => `sms:+${normPhone(phone)}?&body=${encodeURIComponent(text)}`;

export function loadFamily() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "null");
    return v && normPhone(v.phone) && v.consentAt ? v : null;
  } catch {
    return null;
  }
}

export function saveFamily({ name, phone }) {
  if (!normPhone(phone)) throw new Error("Enter a mobile number with 10 digits (or with the country code).");
  const v = { name: String(name || "").trim().slice(0, 40) || "Family", phone: normPhone(phone), consentAt: new Date().toISOString() };
  localStorage.setItem(KEY, JSON.stringify(v));
  return v;
}

export function forgetFamily() {
  try { localStorage.removeItem(KEY); } catch { /* nothing stored */ }
}

// The browser's location, or null if it is not allowed or takes too long.
export function getLocation(timeoutMs = 10000) {
  return new Promise((resolve) => {
    if (typeof navigator === "undefined" || !navigator.geolocation) { resolve(null); return; }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude, accuracy: Math.round(p.coords.accuracy) }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 },
    );
  });
}
