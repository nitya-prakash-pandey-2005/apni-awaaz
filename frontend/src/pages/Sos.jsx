// SOS: speaks the emergency message in the user's voice, in their language and a local language, in large type.
import { useState } from "react";
import { Siren } from "lucide-react";
import { toast } from "../ui";
import { speakVia } from "../lib/api";
import { LANGS } from "../lib/langs";
import { VoiceBadge } from "./Speak";

export default function Sos({ profile }) {
  const [local, setLocal] = useState("hi-IN");
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);

  const sos = async () => {
    setBusy(true);
    try {
      const r = await speakVia("/api/sos", { local_lang: local });
      setLast(r);
      await r.played;
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="sos-card">
      <button className="sos-btn" onClick={sos} disabled={busy} aria-label="Speak the emergency message">
        <Siren size={48} />
        <span>{busy ? "Speaking…" : "SOS"}</span>
      </button>
      <label className="field">Also say it in
        <select className="select" value={local} onChange={(e) => setLocal(e.target.value)}>
          {LANGS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
        </select>
      </label>
      <VoiceBadge last={last} />
      {(last?.spoken || []).map((t, i) => <p key={i} className="sos-text">{t}</p>)}
      {!last && <p className="small muted">Speaks in {LANGS.find((l) => l.value === profile?.language)?.label || "your language"}, then in the language you pick.</p>}
    </div>
  );
}
