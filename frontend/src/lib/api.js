import { useCallback, useEffect, useState } from "react";

// FastAPI errors come as {detail: "..."}, {detail: {message, ...}} or {detail: [{msg}, ...]} (validation).
export function errorText(body, fallback = "Something went wrong. Please try again.") {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (d?.message) return d.message;
  if (Array.isArray(d) && d[0]?.msg) return d[0].msg.replace(/^Value error, /, "");
  return fallback;
}

export class ApiError extends Error {
  constructor(status, body) {
    super(errorText(body, status >= 500 ? "The server could not do that right now." : "That did not work."));
    this.status = status;
    this.body = body;
  }
}

async function parse(r) {
  if (r.ok) return r.headers.get("content-type")?.includes("json") ? r.json() : r;
  let body = null;
  try { body = await r.json(); } catch { /* not JSON */ }
  throw new ApiError(r.status, body);
}

export async function getJSON(path) {
  return parse(await fetch(path, { headers: { Accept: "application/json" } }));
}

export async function sendJSON(method, path, body) {
  return parse(await fetch(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body ?? {}) }));
}

export async function postForm(path, form) {
  return parse(await fetch(path, { method: "POST", body: form }));
}

// Voice audio comes back as audio/wav with what was said, and in which voice, in headers.
export function voiceMeta(h) {
  const dec = (v) => { try { return decodeURIComponent(v || ""); } catch { return v || ""; } };
  return {
    voice: h.get("X-Voice") || "fallback",
    voiceName: h.get("X-Voice-Name") || "",
    reason: h.get("X-Voice-Reason") || "",
    spokenText: dec(h.get("X-Spoken-Text")),
    translated: h.get("X-Translated") === "1",
    cached: h.get("X-Cached") === "1",
    langNote: h.get("X-Lang-Note") || "",
    sosLines: h.get("X-Sos-Lines") ? JSON.parse(dec(h.get("X-Sos-Lines"))) : null,
  };
}

async function audioFrom(r) {
  const res = await parse(r);
  return { blob: await res.blob(), meta: voiceMeta(res.headers) };
}

export const speakText = async (text, lang) => audioFrom(await fetch("/api/speak", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, lang }),
}));
export const fetchAudio = async (url) => audioFrom(await fetch(url));
export const fetchSos = async (localLang) => audioFrom(await fetch("/api/sos", {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ local_lang: localLang }),
}));

// Small fetch hook: { data, error, loading, reload }
export function useApi(path) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const reload = useCallback(() => {
    if (!path) return Promise.resolve(null);
    setState((s) => ({ ...s, loading: true }));
    return getJSON(path)
      .then((data) => { setState({ data, error: null, loading: false }); return data; })
      .catch((error) => { setState({ data: null, error, loading: false }); return null; });
  }, [path]);
  useEffect(() => { reload(); }, [reload]);
  return { ...state, reload };
}
