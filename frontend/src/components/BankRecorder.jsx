// Message banking: record (or upload) a phrase in the person's real voice; it is replayed exactly as recorded.
import { useRef, useState } from "react";
import { Mic, Square, Upload } from "lucide-react";
import { toast } from "../ui";

async function save(label, blob) {
  const r = await fetch(`/api/messages?label=${encodeURIComponent(label)}`, {
    method: "POST", headers: { "Content-Type": blob.type || "audio/webm" }, body: blob,
  });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || `HTTP ${r.status}`);
}

export default function BankRecorder({ onSaved }) {
  const [label, setLabel] = useState("");
  const [rec, setRec] = useState(null);
  const chunks = useRef([]);

  const store = async (blob) => {
    try { await save(label.trim(), blob); toast("Saved in your own voice", "ok"); setLabel(""); onSaved?.(); }
    catch (e) { toast(`Could not save: ${e.message}`, "warn"); }
  };
  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunks.current = [];
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = () => { stream.getTracks().forEach((t) => t.stop()); store(new Blob(chunks.current, { type: mr.mimeType || "audio/webm" })); };
      mr.start();
      setRec(mr);
    } catch { toast("Microphone not available", "warn"); }
  };
  const stop = () => { rec?.stop(); setRec(null); };

  return (
    <div className="stack-sm">
      <input className="input" value={label} onChange={(e) => setLabel(e.target.value)} maxLength={80}
        placeholder="What it says, e.g. “I love you, beta” or “my laugh”" aria-label="Label for the recording" />
      <div className="row">
        {rec ? (
          <button className="btn danger grow" onClick={stop}><Square size={16} /> Stop and save</button>
        ) : (
          <button className="btn primary grow" disabled={!label.trim()} onClick={start}><Mic size={16} /> Record</button>
        )}
        <label className="btn grow" aria-disabled={!label.trim()}>
          <Upload size={16} /> Upload
          <input type="file" accept="audio/*" hidden disabled={!label.trim()} onChange={(e) => e.target.files[0] && store(e.target.files[0])} />
        </label>
      </div>
      <div className="small muted">Best recorded before surgery, or cut from old voice notes. Played back exactly as recorded: no AI.</div>
    </div>
  );
}
