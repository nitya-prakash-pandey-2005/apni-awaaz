import { useCallback, useEffect, useState } from "react";
import { toast } from "../ui";

export async function getJSON(path) {
  const r = await fetch(path, { headers: { Accept: "application/json" } });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

// fetch that throws the server's `detail` message on errors
export async function send(path, { method = "POST", json, body } = {}) {
  const init = { method };
  if (json !== undefined) {
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(json);
  } else if (body !== undefined) {
    init.headers = { "Content-Type": "audio/wav" };
    init.body = body;
  }
  let r;
  try {
    r = await fetch(path, init);
  } catch {
    throw new Error("Can't reach the Apni Awaaz server. Check the connection and try again.");
  }
  if (!r.ok) {
    let msg = `${path} → ${r.status}`, detail;
    try {
      detail = (await r.json()).detail;
      msg = typeof detail === "string" ? detail : detail?.message || msg;
    } catch { /* not JSON */ }
    throw Object.assign(new Error(msg), { detail });
  }
  return r;
}

// Small fetch hook: { data, error, loading, reload }
export function useApi(path, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const reload = useCallback(() => {
    if (!path) return;
    setState((s) => ({ ...s, loading: true }));
    getJSON(path)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => setState({ data: null, error, loading: false }));
  }, [path]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(reload, [reload, ...deps]); // eslint-disable-line react-hooks/exhaustive-deps
  return { ...state, reload };
}

export function playBlob(blob) {
  const url = URL.createObjectURL(blob);
  const a = new Audio(url);
  return new Promise((resolve) => {
    a.onended = a.onerror = () => { URL.revokeObjectURL(url); resolve(); };
    a.play().catch(() => resolve());
  });
}

const unq = (s) => { try { return decodeURIComponent(s || ""); } catch { return s || ""; } };

// POSTs to a WAV-returning route and starts playing it. Returns { voice, spoken, played } (spoken: string or list).
export async function speakVia(path, json) {
  const r = await send(path, { json });
  const blob = await r.blob();
  const spoken = unq(r.headers.get("X-Spoken-Text"));
  const out = { voice: r.headers.get("X-Voice") || "fallback", spoken: path === "/api/sos" ? JSON.parse(spoken || "[]") : spoken };
  return { ...out, played: playBlob(blob) };
}

// { busy, last, say(text, lang, remember) }; `last.voice` is "clone" or "fallback"
export function useSpeak() {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const say = useCallback(async (text, lang, remember = true) => {
    if (!text?.trim()) return null;
    setBusy(true);
    try {
      const r = await speakVia("/api/speak", { text, lang, remember });
      setLast({ ...r, text });
      await r.played;
      return r;
    } catch (e) {
      toast(e.message, "warn");
      return null;
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, last, say };
}
