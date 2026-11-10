// Conversation mode: live captions of the partner (Prisma), 3 suggested replies, one tap speaks in the user's voice.
import { useEffect, useRef, useState } from "react";
import { Keyboard, Mic, MicOff, Play, Send, Square } from "lucide-react";
import { startMic } from "@voice/index.js";
import { Badge, Card, toast } from "../ui";
import { getJSON, useSpeak } from "../lib/api";
import { DEMO, DEMO_DIR, takeAutoplay } from "../lib/demo";
import { LANGS } from "../lib/langs";
import { VoiceBadge } from "./Speak";
import VisitNotes from "../components/VisitNotes";

const RATE = 16000;
const wsUrl = (path) => `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}${path}`;
const STT_BADGE = { idle: ["muted", "Mic off"], connecting: ["cyan", "Connecting…"], connected: ["green", "Listening"],
                    error: ["rose", "Speech service error"], closed: ["muted", "Stopped"], replay: ["cyan", "Replaying"] };

export default function Converse({ profile }) {
  const [on, setOn] = useState(false);
  const [stt, setStt] = useState("idle");
  const [lines, setLines] = useState([]); // { who: "them" | "me", text }
  const [suggestions, setSuggestions] = useState([]);
  const [typed, setTyped] = useState("");
  const [typing, setTyping] = useState(false);
  const [replyLang, setReplyLang] = useState(profile?.language || "hi-IN");
  const refs = useRef({ ws: null, mic: null });
  const endRef = useRef(null);
  const { busy, last, say } = useSpeak();

  useEffect(() => { if (profile?.language) setReplyLang(profile.language); }, [profile?.language]);
  useEffect(() => { endRef.current?.scrollIntoView({ block: "nearest" }); }, [lines]);

  const stop = () => {
    refs.current.mic?.stop();
    refs.current.ws?.close();
    refs.current.audio?.pause();
    (refs.current.timers || []).forEach(clearTimeout);
    refs.current = { ws: null, mic: null };
    setOn(false);
    setStt("idle");
  };
  useEffect(() => stop, []);

  // Demo build: replay the live session's conversation (the nurse's audio, its captions and the 3 suggestions) at its own pace.
  // No microphone and no WebSocket. answer: when it ends, tap the first suggested reply (the landing page's auto demo).
  const replay = async ({ answer = false } = {}) => {
    let c;
    try { c = await getJSON(`${DEMO_DIR}converse.json`); } catch { toast("The recorded conversation is missing from this build.", "warn"); return; }
    setLines([]);
    setSuggestions([]);
    setOn(true);
    setStt("replay");
    const audio = new Audio(DEMO_DIR + c.audio);
    const timers = c.events.map((ev) => setTimeout(() => {
      if (ev.type === "caption") setLines((l) => [...l, { who: "them", text: ev.text }]);
      else if (ev.type === "suggestions") setSuggestions(ev.items);
    }, ev.t * 1000));
    const first = c.events.find((ev) => ev.type === "suggestions")?.items?.[0];
    timers.push(setTimeout(() => {
      if (refs.current.audio !== audio) return; // stopped or restarted
      refs.current = { ws: null, mic: null };
      setOn(false);
      setStt("closed");
      if (answer && first) { // leave the 3 suggestions on screen a moment, then tap the first
        const tap = setTimeout(() => {
          if (refs.current.tap !== tap) return; // restarted, or the page was left
          refs.current = { ws: null, mic: null };
          toast("Auto demo: one tap on the first suggested reply speaks it in the cloned voice.");
          reply(first);
        }, 1500);
        refs.current = { ws: null, mic: null, tap, timers: [tap] };
      }
    }, c.duration * 1000));
    refs.current = { ws: null, mic: null, audio, timers };
    audio.play().catch(() => {});
  };

  const start = async () => {
    setStt("connecting");
    const ws = new WebSocket(wsUrl("/ws/listen"));
    ws.binaryType = "arraybuffer";
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.type === "status") {
        setStt(m.stt);
        if (m.message) toast(m.message, "warn");
      } else if (m.type === "caption") {
        setLines((l) => [...l, { who: "them", text: m.text, t: m.t }]);
      } else if (m.type === "suggestions") {
        setSuggestions(m.items);
      }
    };
    let opened = false;
    ws.onopen = () => { opened = true; };
    ws.onclose = () => {
      if (refs.current.ws !== ws) return;
      if (!opened) toast("Can't reach the Apni Awaaz server, so captions are off. Check the connection and try again.", "warn");
      stop();
    };
    refs.current.ws = ws;
    setOn(true);
    try {
      const mic = await startMic({
        targetRate: RATE,
        onFrame: (ab) => { if (ws.readyState === WebSocket.OPEN && ws.bufferedAmount < 256 * 1024) ws.send(ab); },
      });
      if (refs.current.ws === ws) refs.current.mic = mic;
      else mic.stop(); // stopped or disconnected while the mic was starting: never leave it on
    } catch (e) {
      toast(`Microphone unavailable: ${e?.message || e}`, "warn");
      if (refs.current.ws === ws) stop();
    }
  };

  const reply = async (text) => {
    if (!text.trim()) return;
    const shown = suggestions;
    setLines((l) => [...l, { who: "me", text }]);
    setSuggestions([]);
    const r = await say(text, replyLang);
    if (!r && DEMO) { setLines((l) => l.slice(0, -1)); setSuggestions(shown); return; } // not recorded: the demo said why
    if (r?.spoken && r.spoken !== text) setLines((l) => l.map((x, i) => (i === l.length - 1 ? { ...x, spoken: r.spoken } : x)));
  };

  // Demo: "Try the live demo" on the landing page lands here and plays the conversation by itself. The short delay
  // lets the page settle, and the cleanup makes React's double effect in development start it only once.
  useEffect(() => {
    if (!DEMO) return undefined;
    const t = setTimeout(() => { if (takeAutoplay()) replay({ answer: true }); }, 700);
    return () => clearTimeout(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const [tone, label] = STT_BADGE[stt] || STT_BADGE.idle;
  return (
    <div className="stack">
      <Card title="Conversation" right={<div className="row"><VoiceBadge last={last} /><Badge tone={tone} dot>{label}</Badge></div>}>
        <div className="row wrap between">
          {DEMO ? (
            <button className={`btn lg ${on ? "danger" : "primary"}`} onClick={on ? stop : () => replay()}>
              {on ? <><Square size={18} /> Stop</> : <><Play size={18} /> Play the recorded conversation</>}
            </button>
          ) : (
            <button className={`btn lg ${on ? "danger" : "primary"}`} onClick={on ? stop : start}>
              {on ? <><MicOff size={18} /> Stop listening</> : <><Mic size={18} /> Start listening</>}
            </button>
          )}
          <label className="field reply-lang">Reply in
            <select className="select" value={replyLang} onChange={(e) => setReplyLang(e.target.value)}>
              {LANGS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </label>
        </div>
        <div className="convo" aria-live="polite">
          {lines.length === 0 && <div className="empty">{DEMO ? "Tap “Play the recorded conversation” to hear a nurse recorded in the live session (a synthetic voice) and see her live captions and the 3 replies Apni Awaaz suggested." : "Tap “Start listening”. What the other person says appears here as captions."}</div>}
          {lines.map((l, i) => (
            <div key={i} className={`bubble ${l.who}`}>{l.text}{l.spoken && <div className="meta">spoken as: {l.spoken}</div>}</div>
          ))}
          <div ref={endRef} />
        </div>
      </Card>

      <Card title="Tap to reply">
        <div className="suggestions">
          {suggestions.length === 0 && <div className="small muted">Suggested replies appear after the other person speaks.</div>}
          {suggestions.map((s) => <button key={s} className="phrase suggestion" disabled={busy} onClick={() => reply(s)}>{s}</button>)}
        </div>
        {typing ? (
          <form className="row" style={{ marginTop: 12 }} onSubmit={(e) => { e.preventDefault(); reply(typed); setTyped(""); }}>
            <input className="input" value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Type your reply" aria-label="Your reply" autoFocus />
            <button className="btn primary" disabled={busy || !typed.trim()} aria-label="Speak reply"><Send size={16} /></button>
          </form>
        ) : (
          <button className="btn ghost" style={{ marginTop: 12 }} onClick={() => setTyping(true)}><Keyboard size={16} /> Type instead</button>
        )}
      </Card>

      <VisitNotes lines={lines} profile={profile} listening={on} />
    </div>
  );
}
