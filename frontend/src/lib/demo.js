import { painSentence, templateLang } from "./pain";
import { predict } from "./predict";

// Static demo build (npm run build:demo): no backend. Every /api call is answered from files in /demo/,
// snapshotted from a real live session (scripts/snapshot_demo.py). Nothing here reaches Gnani or Groq.
export const DEMO = import.meta.env.VITE_DEMO === "1";
export const DEMO_DIR = "/demo/";
export const REPO = "https://github.com/nitya-prakash-pandey-2005/apni-awaaz";
export const DEMO_SPEAK_MSG = "In the demo, tap one of the recorded phrases; run it locally with your keys to speak anything.";

const OFF = {
  "/api/voice/clip-check": "Checking new voice notes is off in the demo. Run it locally with your keys to try your own.",
  "/api/voice/enroll": "Building a new voice is off in the demo. Run it locally with your keys to clone your own voice.",
  "/api/voice": "Nothing is stored in the demo, so there is no voice to delete. In the real app this wipes the embedding, the consent record and every clip made in your voice.",
  "/api/messages": "Banking new recordings is off in the demo.",
  "/api/profile": "Saving is off in the demo. Run it locally to keep your own profile.",
};

export const messageAudioUrl = (id) => (DEMO ? `${DEMO_DIR}audio/message-${id}.wav` : `/api/messages/${id}/audio`);

let realFetch = null;
let recordings = null; // [{ kind: "speak" | "sos", text, lang, spoken, voice, file, langs?, texts? }]

async function loadRecordings() {
  if (!recordings) {
    try {
      recordings = await (await realFetch(`${DEMO_DIR}recordings.json`)).json();
    } catch {
      recordings = [];
    }
  }
  return recordings;
}

export const recordingsReady = async () => (await loadRecordings()).some((r) => r.file);

export async function recordedPhrases(lang) {
  return (await loadRecordings()).filter((r) => r.kind === "speak" && r.lang === lang && r.file);
}

const norm = (s) => (s || "").trim().replace(/[।.!?]+$/u, "").trim();
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json" } });

async function wav(rec, spokenHeader) {
  const blob = await (await realFetch(DEMO_DIR + rec.file)).blob();
  return new Response(blob, { status: 200, headers: {
    "Content-Type": "audio/wav", "X-Voice": rec.voice, "X-Spoken-Text": encodeURIComponent(spokenHeader),
    "X-Translated": String(norm(rec.text) !== norm(rec.spoken)) } });
}

async function handle(url, method, body) {
  const p = url.pathname;
  if (method === "GET") {
    if (p === "/api/predict") { // computed in the browser from the same lexicon as the server
      const q = url.searchParams;
      return json({ suggestions: predict(q.get("text") || "", q.get("lang") || "hi-IN") });
    }
    if (p === "/api/phrases") return realFetch(`${DEMO_DIR}snapshot/phrases-${url.searchParams.get("lang") || "hi-IN"}.json`);
    const name = { "/api/health": "health", "/api/profile": "profile", "/api/messages": "messages" }[p];
    return name ? realFetch(`${DEMO_DIR}snapshot/${name}.json`) : json({ detail: "Not part of the demo." }, 404);
  }
  if (p === "/api/pain/sentence" && method === "POST") { // built in the browser from the same templates as the server
    const b = JSON.parse(body || "{}");
    try {
      return json({ text: painSentence(b), lang: b.lang, template_lang: templateLang(b.lang) });
    } catch (e) {
      return json({ detail: e.message }, 400);
    }
  }
  if (p === "/api/speak" && method === "POST") {
    const { text, lang } = JSON.parse(body || "{}");
    const rec = (await recordedPhrases(lang)).find((r) => norm(r.text) === norm(text) || norm(r.spoken) === norm(text));
    return rec ? wav(rec, rec.spoken) : json({ detail: DEMO_SPEAK_MSG }, 409);
  }
  if (p === "/api/sos" && method === "POST") {
    const rec = (await loadRecordings()).find((r) => r.kind === "sos" && r.file);
    if (rec) return wav(rec, JSON.stringify(rec.texts));
    const sos = (await loadRecordings()).find((r) => r.kind === "sos") || {};
    return json({ detail: { message: "The recorded SOS is not in this demo build", langs: sos.langs || ["en-IN"], texts: sos.texts || [] } }, 502);
  }
  const off = OFF[p.startsWith("/api/messages/") ? "/api/messages" : p];
  return json({ detail: off || "Not part of the demo." }, 409);
}

// Call once before the app renders.
export function installDemo() {
  if (!DEMO || realFetch) return;
  realFetch = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const url = new URL(typeof input === "string" ? input : input.url, window.location.href);
    if (url.origin !== window.location.origin || !url.pathname.startsWith("/api/")) return realFetch(input, init);
    return handle(url, (init.method || "GET").toUpperCase(), init.body);
  };
  // The demo never caches the app offline: remove a worker left by an earlier non-demo build.
  navigator.serviceWorker?.getRegistrations?.().then((rs) => rs.forEach((r) => r.unregister())).catch(() => {});
}
