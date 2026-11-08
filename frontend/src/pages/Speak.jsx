// Speak board: type in any script, pick a language, tap a quick phrase; spoken in the user's own voice.
import { useEffect, useState } from "react";
import { History, Volume2 } from "lucide-react";
import { Badge, Card } from "../ui";
import { useApi, useSpeak } from "../lib/api";
import { LangChips } from "../lib/langs";

export function VoiceBadge({ last }) {
  if (!last) return null;
  return last.voice === "clone" ? <Badge tone="green" dot>Your voice</Badge> : <Badge tone="amber" dot>Fallback voice</Badge>;
}

export default function Speak({ profile }) {
  const [lang, setLang] = useState(profile?.language || "hi-IN");
  const [text, setText] = useState("");
  const [history, setHistory] = useState([]);
  const { busy, last, say } = useSpeak();
  const { data: phrases, reload } = useApi(`/api/phrases?lang=${lang}`);
  useEffect(() => { if (profile?.language) setLang(profile.language); }, [profile?.language]);

  const speak = async (t) => {
    const r = await say(t, lang);
    if (r) {
      setHistory((h) => [{ text: t, spoken: r.spoken, lang }, ...h].slice(0, 20));
      reload();
    }
  };

  return (
    <div className="stack">
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
          {(phrases || []).map((p) => (
            <button key={p} className="phrase" disabled={busy} onClick={() => speak(p)}>{p}</button>
          ))}
        </div>
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
