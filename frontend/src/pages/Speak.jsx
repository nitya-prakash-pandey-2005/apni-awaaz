// Speak board: type in any script, pick a language, tap a quick phrase; spoken in the user's own voice.
import { useEffect, useState } from "react";
import { Heart, History, Radio, ScanLine, Volume2 } from "lucide-react";
import { Badge, Card, Seg } from "../ui";
import { useApi, useSpeak } from "../lib/api";
import { LangChips } from "../lib/langs";
import { useScan } from "../lib/scan";
import BankRecorder from "../components/BankRecorder";
import { DEMO, messageAudioUrl, recordedPhrases, recordingsReady } from "../lib/demo";

const SPEEDS = [{ value: 1000, label: "Fast" }, { value: 1500, label: "Medium" }, { value: 2500, label: "Slow" }];
const playOriginal = (m) => new Audio(messageAudioUrl(m.id)).play().catch(() => {});

export function VoiceBadge({ last }) {
  if (!last) return null;
  if (last.voice === "device") return <Badge tone="rose" dot>Phone's voice</Badge>;
  return last.voice === "clone" ? <Badge tone="green" dot>Your voice</Badge> : <Badge tone="amber" dot>Fallback voice</Badge>;
}

export default function Speak({ profile }) {
  const [lang, setLang] = useState(profile?.language || "hi-IN");
  const [text, setText] = useState("");
  const [history, setHistory] = useState([]);
  const { busy, last, say } = useSpeak();
  const { data: phrases, reload } = useApi(`/api/phrases?lang=${lang}`);
  const { data: messages, reload: reloadMessages } = useApi("/api/messages");
  const [scanOn, setScanOn] = useState(false);
  const [speed, setSpeed] = useState(1500);
  const items = [...(messages || []).map((m) => ({ kind: "msg", m })), ...(phrases || []).map((p) => ({ kind: "phrase", p }))];
  useEffect(() => { if (profile?.language) setLang(profile.language); }, [profile?.language]);
  const [recorded, setRecorded] = useState([]); // demo build: sentences spoken live, with their recorded audio
  const [ready, setReady] = useState(true);
  useEffect(() => { if (DEMO) { recordedPhrases(lang).then(setRecorded); recordingsReady().then(setReady); } }, [lang]);

  const speak = async (t) => {
    const r = await say(t, lang);
    if (r) {
      setHistory((h) => [{ text: t, spoken: r.spoken, lang }, ...h].slice(0, 20));
      reload();
    }
  };

  const pick = (i) => { const it = items[i]; if (it && !busy) (it.kind === "msg" ? playOriginal(it.m) : speak(it.p)); }; // one at a time
  const scan = useScan({ count: items.length, active: scanOn, intervalMs: speed, onSelect: pick });
  const nMsg = (messages || []).length;

  return (
    <div className="stack">
      <Card title="Switch scanning" icon={ScanLine} right={<label className="row small"><input type="checkbox" checked={scanOn} onChange={(e) => setScanOn(e.target.checked)} /> On</label>}>
        <div className="small muted">For stroke and ALS users who cannot type or tap: the highlight moves by itself; press Space or Enter (or an assistive switch), or the big button, to speak the highlighted phrase.</div>
        {scanOn && (
          <div className="stack-sm" style={{ marginTop: 10 }}>
            <Seg options={SPEEDS} value={speed} onChange={setSpeed} />
            <button className="btn primary lg block" onClick={scan.select}>Select</button>
          </div>
        )}
      </Card>

      {nMsg > 0 && (
        <Card title="In my own recorded voice" icon={Heart}>
          <div className="phrase-grid">
            {messages.map((m, i) => (
              <button key={m.id} className={`phrase banked ${scan.idx === i ? "scan-on" : ""}`} onClick={() => playOriginal(m)}>{m.label}</button>
            ))}
          </div>
        </Card>
      )}
      {DEMO && (
        <Card title="Spoken live in the recorded session" icon={Radio}>
          {recorded.length > 0
            ? <div className="phrase-grid">{recorded.map((r) => <button key={r.file} className="phrase" disabled={busy} onClick={() => speak(r.text)}>{r.text}</button>)}</div>
            : <div className="small muted">{ready ? "Nothing was recorded live in this language." : "The cloned-voice recordings are not in this build yet."}</div>}
        </Card>
      )}
      <Card title="Say anything" right={<VoiceBadge last={last} />}>
        <div className="stack-sm">
          <textarea className="textarea big-text" rows={3} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Type in any script — “mujhe paani chahiye” works too" aria-label="Text to speak"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); speak(text); } }} />
          <LangChips value={lang} onChange={setLang} />
          <button className="btn primary lg block speak-btn" disabled={busy || !text.trim()} onClick={() => speak(text)}>
            <Volume2 size={22} /> {busy ? "Speaking…" : "Speak"}
          </button>
          {last?.spoken && last.spoken !== last.text && <div className="small muted">Spoken as: {last.spoken}</div>}
        </div>
      </Card>

      <Card title="Quick phrases">
        <div className="phrase-grid">
          {(phrases || []).map((p, i) => (
            <button key={p} className={`phrase ${scan.idx === nMsg + i ? "scan-on" : ""}`} disabled={busy} onClick={() => speak(p)}>{p}</button>
          ))}
        </div>
      </Card>

      <Card title="Bank a message in your real voice" icon={Heart}>
        {DEMO ? <div className="small muted">Recording new messages is off in the demo. The two above were banked during the live session (synthetic voice).</div>
          : <BankRecorder onSaved={reloadMessages} />}
      </Card>

      {history.length > 0 && (
        <Card title="History" icon={History}>
          <div className="list">
            {history.map((h, i) => (
              <button key={i} className="li" onClick={() => say(h.text, h.lang)}>
                <div className="grow" style={{ minWidth: 0 }}><div className="t">{h.spoken || h.text}</div><div className="s">{h.lang}</div></div>
                <Volume2 size={16} />
              </button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
