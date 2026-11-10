// One shared audio element for everything the app says.
// iPhones only let a page play sound that starts from a tap. Our audio arrives a moment after the tap
// (it is made on the server), so every tap handler calls primeAudio() first: that unlocks the shared
// element inside the tap, and the real clip can then play on it when it arrives.
import { useSyncExternalStore } from "react";

const SILENT = "data:audio/wav;base64,UklGRmQBAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YUABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="; // 20 ms of silence
let el = null;
let url = null;
let playing = false;
let token = 0;
const subs = new Set();
const emit = () => subs.forEach((f) => f());

function audio() {
  if (!el && typeof Audio !== "undefined") {
    el = new Audio();
    el.preload = "auto";
  }
  return el;
}

export function primeAudio() {
  const a = audio();
  if (!a || playing) return;
  try {
    a.src = SILENT;
    const p = a.play();
    if (p?.catch) p.catch(() => {});
  } catch { /* nothing to unlock */ }
}

function setPlaying(v) {
  if (playing !== v) { playing = v; emit(); }
}

// Plays a WAV blob. Resolves true when it finished, false if it was stopped or failed.
// onTime(seconds) is called while it plays (for highlighting the SOS line being spoken).
export function playBlob(blob, { loop = false, onTime } = {}) {
  stopAudio();
  const a = audio();
  if (!a) return Promise.resolve(false);
  const my = ++token;
  url = URL.createObjectURL(blob);
  a.loop = loop;
  a.src = url;
  return new Promise((resolve) => {
    const done = (ok) => {
      a.onended = a.onerror = a.ontimeupdate = null;
      if (my === token) setPlaying(false);
      resolve(ok);
    };
    a.onended = () => done(true);
    a.onerror = () => done(false);
    a.ontimeupdate = onTime ? () => onTime(a.currentTime) : null;
    a.onpause = () => { if (my === token && !a.ended) done(false); };
    setPlaying(true);
    const p = a.play();
    if (p?.catch) p.catch(() => done(false));
  });
}

export function stopAudio() {
  token += 1;
  const a = el;
  if (a) {
    a.onpause = null;
    try { a.pause(); } catch { /* already stopped */ }
    a.loop = false;
  }
  if (url) { URL.revokeObjectURL(url); url = null; }
  setPlaying(false);
}

export function usePlaying() {
  return useSyncExternalStore((f) => { subs.add(f); return () => subs.delete(f); }, () => playing);
}
