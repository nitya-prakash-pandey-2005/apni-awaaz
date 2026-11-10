// Voice bank: consent, add 1-5 clips (upload or record), per-clip quality, build the voice, hear the test phrase.
import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Mic, Play, Square, Upload, Wand2, X } from "lucide-react";
import { decodeToPcm16, pcmToWav, startMic } from "@voice/index.js";
import { Badge, Card, toast } from "../ui";
import { getJSON, send, useSpeak } from "../lib/api";
import { DEMO, DEMO_DIR } from "../lib/demo";
import { navigate } from "../lib/router";

const RATE = 16000;
const MAX_CLIPS = 5;
const REASON = {
  "too short": "less than 5 s of speech",
  "too long": "more than 30 s of speech (only the first 30 s are used)",
  clipping: "too loud (clipping)",
  noisy: "too noisy or music in the background",
  "no clear speech": "no clear speech heard",
};

function ClipRow({ clip, onRemove }) {
  const q = clip.quality;
  return (
    <div className="li">
      <div className="grow" style={{ minWidth: 0 }}>
        <div className="t">{clip.name}</div>
        <div className="s">
          {clip.error ? clip.error
            : !q ? "Checking…"
            : `${q.speech_s}s speech · SNR ${q.snr_db} dB${q.text ? ` · “${q.text}”` : ""}`}
        </div>
        {q && !q.ok && <div className="tiny" style={{ color: "var(--rose)" }}>{q.reasons.map((r) => REASON[r] || r).join(", ")}</div>}
      </div>
      {clip.url && <button className="btn icon sm ghost" onClick={() => new Audio(clip.url).play().catch(() => {})} aria-label={`Play ${clip.name}`}><Play size={15} /></button>}
      {clip.error ? <Badge tone="rose">Can't read</Badge> : q ? <Badge tone={q.ok ? "green" : "rose"} dot>{q.ok ? "Good" : "Try another"}</Badge> : <Badge tone="cyan">…</Badge>}
      {!DEMO && <button className="btn icon sm ghost" onClick={onRemove} aria-label={`Remove ${clip.name}`}><X size={15} /></button>}
    </div>
  );
}

export default function VoiceBank({ profile, reload }) {
  const [consent, setConsent] = useState(false);
  const [clips, setClips] = useState([]);
  const [building, setBuilding] = useState(false);
  const [built, setBuilt] = useState(null); // { test_text } after a successful enrol
  const [cloneError, setCloneError] = useState(null);
  const [rec, setRec] = useState(null); // { mic, frames, t0 }
  const fileRef = useRef(null);
  const recRef = useRef(null);
  useEffect(() => { recRef.current = rec; }, [rec]);
  useEffect(() => () => recRef.current?.mic.stop(), []); // leaving the page mid-recording turns the mic off
  const { busy, say } = useSpeak();
  const [demo, setDemo] = useState(null); // demo build: the voice notes checked and used in the live session
  useEffect(() => {
    if (!DEMO) return;
    setConsent(true);
    getJSON(`${DEMO_DIR}voice-clips.json`).then((d) => {
      setDemo(d);
      setClips(d.clips.map((c) => ({ id: c.name, name: c.name, quality: c.quality, url: DEMO_DIR + c.file })));
    }).catch(() => {});
  }, []);

  const update = (id, patch) => setClips((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const addPcm = async (name, pcm) => {
    const id = Math.random().toString(36).slice(2);
    const wav = pcmToWav(pcm, RATE);
    setClips((cs) => [...cs, { id, name, wav }].slice(-MAX_CLIPS));
    try {
      const r = await send("/api/voice/clip-check", { body: wav });
      update(id, { quality: await r.json() });
    } catch (e) {
      update(id, { error: e.message });
    }
  };

  const onFiles = async (files) => {
    for (const f of Array.from(files).slice(0, MAX_CLIPS)) {
      try {
        await addPcm(f.name, await decodeToPcm16(f, RATE));
      } catch {
        setClips((cs) => [...cs, { id: f.name + Date.now(), name: f.name, error: "Please export as MP3/WAV" }].slice(-MAX_CLIPS));
      }
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  const toggleRec = async () => {
    if (rec) {
      rec.mic.stop();
      setRec(null);
      const n = rec.frames.reduce((s, f) => s + f.length, 0);
      const pcm = new Int16Array(n);
      let o = 0;
      for (const f of rec.frames) { pcm.set(f, o); o += f.length; }
      await addPcm(`Recording ${new Date().toLocaleTimeString()}`, pcm);
      return;
    }
    const frames = [];
    try {
      const mic = await startMic({ targetRate: RATE, onFrame: (ab) => frames.push(new Int16Array(ab)) });
      setRec({ mic, frames });
    } catch (e) {
      toast(`Microphone unavailable: ${e?.message || e}`, "warn");
    }
  };

  const okClips = clips.filter((c) => c.quality?.ok);
  const best = okClips.reduce((b, c) => (!b || c.quality.snr_db > b.quality.snr_db ? c : b), null); // same rule as backend best_clip

  const build = async () => {
    if (!best || !consent) return;
    setBuilding(true);
    setCloneError(null);
    try {
      const r = await (await send("/api/voice/enroll?consent=true", { body: best.wav })).json();
      setBuilt(r);
      reload();
      await say(r.test_text, r.profile.language, false);
    } catch (e) {
      setCloneError(e.message);
      toast("Voice cloning failed. The fallback voice stays on.", "warn");
    } finally {
      setBuilding(false);
    }
  };

  return (
    <div className="stack voice-page">
      {profile?.has_voice && !built && (
        <div className="callout ok"><CheckCircle2 size={18} color="var(--green)" />
          <div className="grow">{DEMO ? "This voice was built live on 10 Nov from the notes below." : "Your voice is ready. Add new clips below to rebuild it."}</div>
          <button className="btn sm" onClick={() => navigate("/speak")}>Speak</button>
        </div>
      )}

      <Card title="1. Consent">
        <label className="consent">
          <input type="checkbox" checked={consent} disabled={DEMO} onChange={(e) => setConsent(e.target.checked)} />
          <span>This is <b>my own voice</b>, or the speaker has given me explicit permission to clone it. I understand the voice is used only to speak for me, and I can delete it at any time.</span>
        </label>
      </Card>

      <Card title="2. Add 1–5 voice notes" right={<Badge tone="muted">{clips.length}/{MAX_CLIPS}</Badge>}>
        <p className="small muted" style={{ marginTop: 0 }}>Old WhatsApp voice notes work (.opus, .ogg, .mp3, .wav). Pick clips with 5–30 seconds of only your voice, no music.{!consent && " Tick the consent box first: clips are checked by Gnani's speech service."}{DEMO && " In the demo you can play the three synthetic notes checked live on 10 Nov; uploading and recording are off."}</p>
        <div className="row wrap">
          <input ref={fileRef} type="file" accept="audio/*,.opus,.ogg,.m4a" multiple hidden onChange={(e) => onFiles(e.target.files)} />
          <button className="btn" disabled={DEMO || !consent} onClick={() => fileRef.current?.click()}><Upload size={16} /> Upload clips</button>
          <button className={`btn ${rec ? "danger" : "ghost"}`} disabled={DEMO || (!consent && !rec)} onClick={toggleRec}>{rec ? <><Square size={16} /> Stop recording</> : <><Mic size={16} /> Record</>}</button>
        </div>
        {clips.length > 0 && <div className="list" style={{ marginTop: 10 }}>{clips.map((c) => <ClipRow key={c.id} clip={c} onRemove={() => setClips((cs) => cs.filter((x) => x.id !== c.id))} />)}</div>}
      </Card>

      <Card title="3. Build my voice">
        {!consent && <p className="small muted" style={{ marginTop: 0 }}>Tick the consent box first.</p>}
        {consent && !best && <p className="small muted" style={{ marginTop: 0 }}>Add at least one clip marked “Good”.</p>}
        {best && <p className="small muted" style={{ marginTop: 0 }}>Uses the clearest clip: <b>{best.name}</b>.</p>}
        {demo && (
          <div className="stack-sm" style={{ marginBottom: 12 }}>
            <div className="callout">Built live from {demo.used}. Test phrase: “{demo.test_text}”</div>
            <button className="btn ghost" disabled={busy} onClick={() => say(demo.test_text, demo.lang, false)}><Play size={16} /> Play the test phrase</button>
          </div>
        )}
        <button className="btn primary lg block" disabled={DEMO || !consent || !best || building} onClick={build}>
          <Wand2 size={18} /> {building ? "Building your voice…" : "Build my voice"}
        </button>
        {cloneError && <div className="callout warn" style={{ marginTop: 10 }}>Cloning failed: {cloneError}. The app keeps working with the fallback voice <b>{profile?.fallback_voice || "Shivani"}</b>.</div>}
        {built && (
          <div className="stack-sm" style={{ marginTop: 12 }}>
            <div className="callout">Test phrase: “{built.test_text}”</div>
            <div className="row wrap">
              <button className="btn success" onClick={() => navigate("/speak")}>Sounds like me</button>
              <button className="btn ghost" disabled={busy} onClick={() => say(built.test_text, built.profile.language, false)}>Play again</button>
              <button className="btn ghost" onClick={() => { setBuilt(null); setClips([]); }}>Try other clips</button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
