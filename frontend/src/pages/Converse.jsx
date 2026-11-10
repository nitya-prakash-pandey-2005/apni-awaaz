import { useEffect, useRef, useState } from "react";
import { Ear, Loader2, Mic, MicOff, Send, Square, Volume2 } from "lucide-react";
import { Badge, Card, PageHead, toast } from "../ui";
import { LangSelect, VoiceBadge } from "../components/bits";
import { speakText, useApi } from "../lib/api";
import { playBlob, primeAudio, stopAudio, usePlaying } from "../lib/audio";
import { fallbackNote } from "../lib/copy";
import { langOf } from "../lib/langs";
import { load, save } from "../lib/prefs";
import { useApp } from "../state/app";
import { useListen } from "../state/useListen";

const STATUS = {
  off: ["muted", "Not listening"],
  connecting: ["cyan", "Starting…"],
  connected: ["green", "Listening"],
  reconnecting: ["amber", "Reconnecting…"],
  error: ["rose", "Captions unavailable"],
};

export default function Converse() {
  const { profile, health } = useApp();
  const [partner, setPartner] = useState(() => load("partner-lang", profile?.language || "hi-IN"));
  const [reply, setReply] = useState(() => load("reply-lang", profile?.language || "hi-IN"));
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(null);
  const [lastMeta, setLastMeta] = useState(null);
  const listen = useListen({ allowNoMic: !!health?.fake });
  const { data: phrases } = useApi(`/api/phrases?lang=${reply}`);
  const playing = usePlaying();
  const boxRef = useRef(null);
  const req = useRef(0);

  useEffect(() => {
    const el = boxRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [listen.items, listen.hearing]);

  const changePartner = (code) => {
    setPartner(code);
    save("partner-lang", code);
    if (listen.on) { // the caption language is fixed per stream: reconnect
      listen.stop();
      setTimeout(() => listen.start({ partner: code, reply }), 150);
    }
  };
  const changeReply = (code) => { setReply(code); save("reply-lang", code); listen.setReply(code); };

  const sayReply = async (text, key) => {
    const t = text.trim();
    if (!t) return;
    primeAudio();
    const my = ++req.current;
    setBusy(key);
    try {
      const { blob, meta } = await speakText(t, reply);
      if (my !== req.current) return;
      listen.sendSpoken(meta.spokenText || t, reply); // before it plays, so the echo guard knows
      setLastMeta(meta);
      if (key === "typed") setTyped("");
      setBusy(null);
      await playBlob(blob);
    } catch (e) {
      if (my === req.current) setBusy(null);
      toast(e.message, "warn");
    }
  };

  const quick = (phrases?.lang === reply ? phrases.quick : []).filter((p) => ["yes", "no", "wait"].includes(p.key)).map((p) => p.text);
  const sug = listen.suggestions;
  const replies = sug?.items || (sug ? null : quick);
  const [tone, label] = STATUS[listen.status] || STATUS.off;

  return (
    <div>
      <div className="desktop-only">
        <PageHead kicker="Conversation" title="Talk with the person in front of you"
          sub="Their words appear as captions. Tap one of three suggested replies, and it is spoken in your voice." />
      </div>
      <div className="converse-layout">
        <Card className="area-controls">
          <div className="grid g2 keep-2">
            <label className="field" htmlFor="partner-lang">They speak
              <LangSelect id="partner-lang" value={partner} onChange={changePartner} auto />
            </label>
            <label className="field" htmlFor="reply-lang">I reply in
              <LangSelect id="reply-lang" value={reply} onChange={changeReply} />
            </label>
          </div>
          <div className="row" style={{ marginTop: 14 }}>
            {listen.on ? (
              <button type="button" className="btn danger lg grow" onClick={listen.stop}><MicOff size={18} /> Stop listening</button>
            ) : (
              <button type="button" className="btn primary lg grow" onClick={() => { primeAudio(); listen.start({ partner, reply }); }}>
                <Mic size={18} /> Start listening
              </button>
            )}
          </div>
          <div className="row between wrap" style={{ marginTop: 10, rowGap: 6 }}>
            <Badge tone={tone} dot>{label}</Badge>
            {listen.noMic && <span className="tiny muted">No microphone: demo captions only</span>}
          </div>
          {health?.fake && (
            <p className="tiny muted" style={{ marginTop: 10 }}>
              Demo mode: a recorded nurse speaks every few seconds, so you can try this without a microphone or API keys.
            </p>
          )}
        </Card>

        <Card title="Conversation" className="area-convo" right={listen.items.length ? <button type="button" className="btn sm ghost" onClick={listen.clear}>Clear</button> : null}>
          <div className="convo" ref={boxRef} aria-live="polite">
            {!listen.items.length && !listen.hearing && (
              <div className="empty">
                Tap <b>Start listening</b>. What the other person says appears here, with three replies you can tap.
              </div>
            )}
            {listen.items.map((it) => (
              it.kind === "echo" ? (
                <div key={it.id} className="echo-note"><Ear size={13} /> Ignored the phone's own voice</div>
              ) : (
                <div key={it.id} className={`bubble ${it.kind === "me" ? "me" : "them"} talk`} lang={it.lang || undefined}>
                  {it.text}
                  <div className="meta">{it.kind === "me" ? "You said" : "They said"}{it.lang && it.lang !== "indic-auto" ? ` · ${langOf(it.lang).native}` : ""}</div>
                </div>
              )
            ))}
            {listen.hearing && <div className="bubble them talk typing" aria-label="Someone is speaking"><span /><span /><span /></div>}
          </div>
        </Card>

        <div className="area-side stack">
          <Card title={sug?.items ? "Tap to reply" : sug ? "Thinking of replies…" : "Quick answers"}
            right={playing ? <button type="button" className="btn sm danger" onClick={stopAudio}><Square size={14} /> Stop</button> : null}>
            <div className="suggest-list">
              {replies ? replies.map((r, i) => (
                <button key={`${sug?.for || "q"}-${i}`} type="button" className="suggest-btn" lang={reply} onClick={() => sayReply(r, `s${i}`)} disabled={busy === `s${i}`}>
                  {busy === `s${i}` ? <Loader2 size={18} className="spin" /> : <Volume2 size={18} />}
                  <span>{r}</span>
                </button>
              )) : [0, 1, 2].map((i) => <div key={i} className="suggest-btn skeleton" aria-hidden="true" />)}
            </div>
            {lastMeta && (
              <div className="row wrap" style={{ marginTop: 12, rowGap: 6 }}>
                <VoiceBadge meta={lastMeta} />
                {lastMeta.voice === "fallback" && <span className="tiny muted">{fallbackNote(lastMeta)}</span>}
              </div>
            )}
          </Card>
          <Card title="Or type your reply">
            <form className="row" onSubmit={(e) => { e.preventDefault(); sayReply(typed, "typed"); }}>
              <label className="sr-only" htmlFor="reply-text">Your reply</label>
              <input id="reply-text" className="input grow reply-input" value={typed} maxLength={500} onChange={(e) => setTyped(e.target.value)}
                placeholder="Any script is fine" />
              <button type="submit" className="btn primary icon reply-send" disabled={!typed.trim() || busy === "typed"} aria-label="Speak this reply">
                {busy === "typed" ? <Loader2 size={18} className="spin" /> : <Send size={18} />}
              </button>
            </form>
            <p className="tiny muted" style={{ marginTop: 8 }}>Spoken in {langOf(reply).native}{langOf(reply).native !== langOf(reply).name ? ` (${langOf(reply).name})` : ""}.</p>
          </Card>
        </div>
      </div>
    </div>
  );
}
