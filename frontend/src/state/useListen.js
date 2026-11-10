// Conversation mode: microphone (PCM16 mono 16 kHz, 512-sample frames) -> /ws/listen -> captions + suggestions.
import { useCallback, useEffect, useRef, useState } from "react";
import { startMic } from "@voice/index.js";
import { toast } from "../ui";

const RATE = 16000;
let nextId = 1;

export function useListen({ allowNoMic = false } = {}) {
  const [on, setOn] = useState(false);
  const [status, setStatus] = useState("off"); // off | connecting | connected | reconnecting | error
  const [items, setItems] = useState([]); // { id, kind: "them" | "me" | "echo", text, lang }
  const [suggestions, setSuggestions] = useState(null); // { for, items: string[] | null, lang }
  const [hearing, setHearing] = useState(false);
  const [noMic, setNoMic] = useState(false);
  const ref = useRef({ ws: null, mic: null, lastCaption: 0 });

  const add = (it) => setItems((xs) => [...xs, { id: nextId++, ...it }].slice(-60));

  const stop = useCallback(() => {
    const r = ref.current;
    r.mic?.stop();
    r.mic = null;
    const ws = r.ws;
    r.ws = null;
    if (ws) {
      try { if (ws.readyState === 1) ws.send(JSON.stringify({ type: "stop" })); } catch { /* closing */ }
      try { ws.close(); } catch { /* closed */ }
    }
    setOn(false);
    setHearing(false);
    setStatus((s) => (s === "error" ? s : "off"));
  }, []);

  const onMessage = useCallback((m) => {
    switch (m.type) {
      case "status":
        setStatus(m.stt);
        if (m.stt === "error" && m.message) toast(m.message, "warn");
        break;
      case "hearing":
        setHearing(!!m.on);
        break;
      case "caption":
        ref.current.lastCaption = m.id;
        setHearing(false);
        add({ kind: "them", text: m.text, lang: m.lang });
        setSuggestions({ for: m.id, items: null });
        break;
      case "suggestions":
        if (m.for === ref.current.lastCaption) setSuggestions({ for: m.for, items: m.items, lang: m.lang });
        break;
      case "echo_ignored":
        add({ kind: "echo", text: m.text });
        break;
      default:
        break;
    }
  }, []);

  const start = useCallback(async ({ partner, reply }) => {
    if (ref.current.ws) return;
    setStatus("connecting");
    setOn(true);
    setNoMic(false);
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/listen?lang=${encodeURIComponent(partner)}&reply=${encodeURIComponent(reply)}`);
    ws.binaryType = "arraybuffer";
    ref.current.ws = ws;
    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      try { onMessage(JSON.parse(e.data)); } catch { /* ignore bad frames */ }
    };
    ws.onclose = () => {
      if (ref.current.ws !== ws) return;
      ref.current.ws = null;
      ref.current.mic?.stop();
      ref.current.mic = null;
      setOn(false);
      setHearing(false);
      setStatus((s) => (s === "error" ? s : "off"));
    };
    ws.onerror = () => toast("Lost the connection to the app server.", "warn");
    try {
      const mic = await startMic({ targetRate: RATE, onFrame: (ab) => { if (ws.readyState === 1) ws.send(ab); } });
      if (ref.current.ws !== ws) { mic.stop(); return; } // stopped while asking for the microphone
      ref.current.mic = mic;
    } catch {
      if (!allowNoMic) {
        toast("Please allow the microphone, so the app can hear the other person.", "warn");
        stop();
        return;
      }
      setNoMic(true);
    }
  }, [allowNoMic, onMessage, stop]);

  // Tell the server what the app just said, so the echo guard drops it when the mic hears it back.
  const sendSpoken = useCallback((text, lang) => {
    const ws = ref.current.ws;
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "spoken", text }));
    add({ kind: "me", text, lang });
  }, []);

  const setReply = useCallback((lang) => {
    const ws = ref.current.ws;
    if (ws && ws.readyState === 1) ws.send(JSON.stringify({ type: "reply_lang", lang }));
  }, []);

  const clear = useCallback(() => { setItems([]); setSuggestions(null); }, []);

  useEffect(() => stop, [stop]);

  return { on, status, items, suggestions, hearing, noMic, start, stop, sendSpoken, setReply, clear };
}
