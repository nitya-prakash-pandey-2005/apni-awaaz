// Every number and claim below is taken from the README (sources linked there) and docs/test-log.md.
import { REPO } from "../lib/demo";

export const VIDEO_URL = `${REPO}#readme`;
export const AWAAZ_URL = "https://apni-awaaz-kappa.vercel.app/";
export const DADI_URL = "https://dadi-vs-scammers.vercel.app/";
export const PUKAAR_URL = "https://pukaar-snowy.vercel.app/";
export const DADI_REPO = "https://github.com/nitya-prakash-pandey-2005/dadi-vs-scammers";
export const PUKAAR_REPO = "https://github.com/nitya-prakash-pandey-2005/pukaar";
export const APP_ENTRY = "#/app"; // not a page: App.jsx sends it to /speak or /voice like a first run

const IARC_INDIA = "https://gco.iarc.who.int/media/globocan/factsheets/populations/356-india-fact-sheet.pdf";

export const FACTS = [
  { value: 205878, format: "in", label: "new lip and oral cavity cancer cases in India", note: "GLOBOCAN 2024. The most common cancer in Indian men.", href: IARC_INDIA, src: "IARC GLOBOCAN 2024" },
  { value: 12.9, decimals: 1, suffix: " lakh", label: "new strokes in India in 2019", note: "About 96.5 lakh people are living after a stroke.", href: "https://theprint.in/health/india-recorded-13-lakh-stroke-cases-in-2019-highest-in-southeast-asia-finds-lancet-study/1798324", src: "Lancet study, via ThePrint" },
  { value: 0, label: "Indian languages in Apple Personal Voice", note: "English US, Spanish Mexico and Mandarin only, and it needs a fresh recording made while you can still speak.", href: "https://www.apple.com/ios/feature-availability/", src: "Apple feature availability" },
];

export const STORIES = [
  { name: "Shrenik Shah", text: "Had his voice box removed in 1997 for stage IV vocal-cord cancer. He wrote on paper for three months, then taught himself to speak with an electrolarynx.", href: "https://cancerworld.net/shrenik-shah-the-voice-that-transcends-sound/", src: "Cancerworld" },
  { name: "Sapna Rana", text: "A Radio Mirchi Mumbai voice for about 20 years, she lost her speech to ALS and rebuilt her own voice with ElevenLabs. She now speaks Hindi and English with it.", href: "https://cxotoday.com/media-coverage/elevenlabs-charts-next-phase-of-india-growth-at-first-summit-in-bengaluru/", src: "CXOToday" },
  { name: "Alice Harty", text: "Lost her voice after a laryngectomy. Her voice was rebuilt from about three minutes of old recordings that family and friends sent in.", quote: "The greatest gift I could ask for.", href: "https://www.wbur.org/upnext/2026/08/13/artifical-intelligence-ai-voice-clone-cancer-als", src: "WBUR" },
];

export const FEATURES = [
  { img: "voice-clips", kicker: "Voice bank", title: "Your voice, rebuilt from old voice notes.", text: "Upload a few WhatsApp notes recorded before the illness. Each clip is checked for length, clipping, noise and clear speech, and nothing is uploaded until you tick consent. Gnani builds your voice from 5 to 30 seconds of audio.", points: ["Quality check on every clip", "Consent first, always", "No new recording session"] },
  { img: "speak-tamil", kicker: "Speak", title: "Type in any script. Hear yourself.", text: "Type in Devanagari, Tamil or plain Latin letters. “mujhe paani chahiye” is spoken as मुझे पानी चाहिए, in your own voice, in any of 10 Indian languages.", points: ["Code-mix and romanised typing", "Tamil in the cloned voice of a Hindi speaker"] },
  { img: "speak-banked", kicker: "Quick phrases + banked messages", title: "The words that matter, one tap away.", text: "Big phrase tiles for daily needs, and banked messages recorded before surgery (“I love you, beta”, a laugh) that play back exactly as recorded, with no AI." },
  { img: "speak-scanning", kicker: "Switch scanning + dwell", title: "For hands that can no longer tap.", text: "A highlight steps through phrases; one press of a switch, Space or Enter speaks it. For a head pointer or eye-gaze, resting the pointer fills a ring and presses for you." },
  { img: "pain-body", kicker: "Where does it hurt?", title: "Tap the body. Say how bad.", text: "Tap a body part, pick 0 to 10 and the kind of pain. One clear, grammatical sentence is spoken in your voice, in your language. No typing at all." },
  { img: "speak-predict", kicker: "Word prediction", title: "Fewer keystrokes, every sentence.", text: "Up to five big chips offer the next word or the whole phrase, learned from what you have said before. An honest “Keystrokes saved” count shows the effort it saves." },
  { img: "converse-reply", kicker: "Converse", title: "Hear them. Answer in one tap.", text: "Gnani Prisma captions what the other person says, live. Three suggested replies appear within about a second; tap one and it is spoken in your voice." },
  { img: "visit-notes", kicker: "Visit notes", title: "What the doctor said, in your own voice.", text: "After a doctor or nurse visit, one tap turns the captions and your replies into clear notes: a medicines table (name, dose, when, how many days), tests, the next visit and what to watch for. Play them back in your voice, download them, or send them to family.", points: ["Marked as made by AI: check with the doctor", "Replay what you could not ask them to repeat"] },
  { img: "sos-spoken", kicker: "SOS", title: "Help, in your own voice, even offline.", text: "One large button speaks an emergency message in two languages and shows it in large type. If the server is down it still works in the phone’s voice, and it can share your location with family on WhatsApp or SMS." },
  { img: "profile-consent", kicker: "Privacy", title: "Your voice stays yours.", text: "The voice embedding never reaches the browser. “Delete my voice” removes the embedding, the consent record and every clip made in your voice. In our test: 9 cloned clips on disk → 0." },
];

export const PIPE_BUILD = [
  { t: "Old voice notes", s: "WhatsApp, 5–30 s" },
  { t: "Quality check", s: "noise, clipping, speech" },
  { t: "Consent", s: "ticked, timestamped" },
  { t: "Voice-clone embedding", s: "Gnani, 0.67 s", gnani: true },
  { t: "vachana-vc-v1", s: "Gnani speech", gnani: true },
  { t: "Your voice", s: "10 languages", end: true },
];
export const PIPE_TALK = [
  { t: "Partner speaks", s: "doctor, family" },
  { t: "Prisma captions", s: "Gnani, live", gnani: true },
  { t: "3 suggestions", s: "one tap" },
  { t: "Your voice", s: "~1.3 s reply", end: true },
];

export const RESULTS = [
  { value: 0.67, decimals: 2, suffix: " s", label: "to build your voice", note: "Gnani embedding call, 10 Nov" },
  { value: 1.2, decimals: 1, tail: "–1.65", suffix: " s", label: "to speak a sentence", note: "in the cloned voice, 8 Nov" },
  { value: 7, suffix: " / 7", label: "cloned clips understood word for word", note: "re-transcribed by Prisma, Hindi and Tamil" },
  { value: 256, label: "automated tests passing", note: "244 Python + 12 JavaScript" },
];

export const COMPARE = [
  { name: "Apple Personal Voice", rows: ["No Indian language", "Needs a fresh recording while you can still speak", "Free on Apple devices"] },
  { name: "ElevenLabs Impact Program", rows: ["Already clones from WhatsApp notes", "14 Indian languages", "A general voice platform, not built around conversation, to our knowledge", "Free licence, apply first"] },
  { name: "Apni Awaaz", us: true, rows: ["Your own voice from notes you already have", "10 Indian languages, code-mix and romanised typing", "Conversation first: phrases, live captions, suggested replies", "SOS that works when the server is down", "Free, no application step"] },
];

// Server time per step on 10 Nov (README "Measured results"); ranges are min-max over the runs logged.
export const TIMINGS = [
  { step: "Check a voice note", min: 0.27, max: 0.69 },
  { step: "Build your voice", min: 0.67, max: 0.67 },
  { step: "Converse reply in your voice", min: 1.3, max: 1.3 },
  { step: "Speak a sentence in your voice", min: 1.5, max: 2.2 },
];
