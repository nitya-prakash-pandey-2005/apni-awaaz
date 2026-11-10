// Small building blocks shared by the pages.
import { useState } from "react";
import {
  BedDouble, Check, GlassWater, HeartHandshake, Hourglass, MessageSquareText, PhoneCall, Stethoscope, Toilet,
  Trash2, Utensils, X, Bandage,
} from "lucide-react";
import { Badge, Sheet, toast } from "../ui";
import { LANGS } from "../lib/langs";
import { sendJSON } from "../lib/api";

const ICONS = { GlassWater, Bandage, Toilet, Check, X, HeartHandshake, PhoneCall, BedDouble, Utensils, Hourglass, Stethoscope };
export const PhraseIcon = ({ name, size = 20 }) => {
  const I = ICONS[name] || MessageSquareText;
  return <I size={size} />;
};

// Language chips: one tap picks the language (all 10 shown; they wrap, nothing scrolls sideways).
export function LangChips({ value, onChange, label, include = LANGS, extra }) {
  return (
    <div className="lang-chips" role="radiogroup" aria-label={label}>
      {extra}
      {include.map((l) => (
        <button key={l.code} type="button" role="radio" aria-checked={value === l.code} lang={l.code}
          className={`chip lang-chip ${value === l.code ? "on" : ""}`} onClick={() => onChange(l.code)} title={l.name}>
          {l.native}
        </button>
      ))}
    </div>
  );
}

export function LangSelect({ value, onChange, auto, id }) {
  return (
    <select id={id} className="select" value={value} onChange={(e) => onChange(e.target.value)}>
      {auto && <option value="auto">Detect automatically</option>}
      {LANGS.map((l) => <option key={l.code} value={l.code}>{l.native === l.name ? l.name : `${l.native} (${l.name})`}</option>)}
    </select>
  );
}

// Which voice just spoke: the user's own, or the standard fallback voice.
export function VoiceBadge({ meta }) {
  if (!meta) return null;
  if (meta.voice === "clone") return <Badge tone="green" dot>My voice</Badge>;
  return <Badge tone="amber" dot>Fallback voice{meta.voiceName ? `: ${meta.voiceName}` : ""}</Badge>;
}

// A big, easy-to-hit checkbox row (consent).
export function CheckRow({ checked, onChange, children, id }) {
  return (
    <label className={`check-row ${checked ? "on" : ""}`} htmlFor={id}>
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{children}</span>
    </label>
  );
}

// "Delete my voice": confirm in a sheet, then remove the voice model and all audio made with it.
export function DeleteVoiceButton({ onDeleted, block }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const del = async () => {
    setBusy(true);
    try {
      const r = await sendJSON("DELETE", "/api/voice");
      toast(r.deleted ? "Your voice has been deleted from this device." : "There was no voice to delete.", "ok");
      setOpen(false);
      onDeleted?.(r);
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <button type="button" className={`btn danger ${block ? "block" : ""}`} onClick={() => setOpen(true)}>
        <Trash2 size={16} /> Delete my voice
      </button>
      <Sheet open={open} onClose={() => !busy && setOpen(false)} title="Delete your voice?">
        <div className="stack">
          <p className="text-2">
            This removes your voice model and every clip spoken in it from this device. Your name, languages and
            phrases stay.
          </p>
          <p className="text-2">You can build your voice again later. We will ask for consent again.</p>
          <button type="button" className="btn danger lg block" onClick={del} disabled={busy}>
            <Trash2 size={18} /> {busy ? "Deleting…" : "Yes, delete my voice"}
          </button>
          <button type="button" className="btn ghost lg block" onClick={() => setOpen(false)} disabled={busy}>Keep my voice</button>
        </div>
      </Sheet>
    </>
  );
}
