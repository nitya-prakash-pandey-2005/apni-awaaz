// Profile: name, language, family names (sent to Prisma as keyterms), condition, fallback voice, delete my voice.
import { useEffect, useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { Badge, Card, Sheet, toast } from "../ui";
import { send, useApi } from "../lib/api";
import { LANGS, VOICES } from "../lib/langs";
import { DEMO } from "../lib/demo";
import DwellSetting from "../components/DwellSetting";
import FamilyContact from "../components/FamilyContact";

export default function Profile({ profile, reload }) {
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(false);
  const [dropMsg, setDropMsg] = useState(null); // a banked recording waiting for "Delete"
  const { data: messages, reload: reloadMessages } = useApi("/api/messages");
  useEffect(() => {
    if (profile) setForm({ ...profile, family: (profile.family_names || []).join(", ") });
  }, [profile]);
  if (!form) return <div className="empty">Loading…</div>;
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    try {
      await send("/api/profile", { method: "PUT", json: {
        name: form.name, language: form.language, condition: form.condition, fallback_voice: form.fallback_voice,
        family_names: form.family.split(",").map((s) => s.trim()).filter(Boolean),
      } });
      toast("Profile saved", "ok");
      reload();
    } catch (e) {
      toast(e.message, "warn");
    }
  };

  const del = async () => {
    try {
      await send("/api/voice", { method: "DELETE" });
      toast("Your voice was deleted", "ok");
      setConfirm(false);
      reload();
    } catch (e) {
      toast(e.message, "warn");
    }
  };

  const delMessage = async () => {
    try {
      await send(`/api/messages/${dropMsg.id}`, { method: "DELETE" });
      toast("Recording deleted", "ok");
      setDropMsg(null);
      reloadMessages();
    } catch (e) {
      toast(e.message, "warn");
    }
  };

  return (
    <div className="stack">
      <Card title="About me">
        <div className="stack-sm">
          <label className="field">Name<input className="input" value={form.name} onChange={set("name")} /></label>
          <label className="field">My language
            <select className="select" value={form.language} onChange={set("language")}>
              {LANGS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
          </label>
          <label className="field">Family names (helps captions spell them right)
            <input className="input" value={form.family} onChange={set("family")} placeholder="Ravi, Meena" />
          </label>
          <label className="field">Condition (optional; helps the reply suggestions)
            <input className="input" value={form.condition} onChange={set("condition")} placeholder="after throat surgery" />
          </label>
          <label className="field">Fallback voice (used if cloning is unavailable)
            <select className="select" value={form.fallback_voice} onChange={set("fallback_voice")}>
              {VOICES.map((v) => <option key={v}>{v}</option>)}
            </select>
          </label>
          <button className="btn primary" onClick={save}><Save size={16} /> Save</button>
        </div>
      </Card>

      <FamilyContact />
      <DwellSetting />

      <Card title="My voice" right={<Badge tone={profile.has_voice ? "green" : "muted"} dot>{profile.has_voice ? "Cloned" : "Not set"}</Badge>}>
        <p className="small muted" style={{ marginTop: 0 }}>
          {profile.has_voice ? `Consent given ${new Date(profile.consent_at).toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" })}. The voice embedding is stored only on this app's server.` : "No cloned voice. The fallback voice is used."}
        </p>
        <button className="btn danger" disabled={!profile.has_voice} onClick={() => setConfirm(true)}><Trash2 size={16} /> Delete my voice</button>
      </Card>

      <Card title="My recordings" right={<Badge tone="muted">{(messages || []).length}</Badge>}>
        {(messages || []).length === 0
          ? <p className="small muted" style={{ margin: 0 }}>No banked recordings yet. Add them on the Speak page.</p>
          : <div className="list">{messages.map((m) => (
            <div key={m.id} className="li">
              <div className="grow" style={{ minWidth: 0 }}><div className="t">{m.label}</div><div className="s">Your real voice · {m.created?.slice(0, 10)}</div></div>
              <button className="btn icon ghost" onClick={() => setDropMsg(m)} aria-label={`Delete recording: ${m.label}`}><Trash2 size={18} /></button>
            </div>))}</div>}
      </Card>

      <Sheet open={!!dropMsg} onClose={() => setDropMsg(null)} title="Delete this recording?">
        <p>“{dropMsg?.label}” is deleted from this app for good.</p>
        <div className="row"><button className="btn danger" onClick={delMessage}>Delete</button><button className="btn ghost" onClick={() => setDropMsg(null)}>Cancel</button></div>
      </Sheet>

      <Sheet open={confirm} onClose={() => setConfirm(false)} title="Delete your voice?">
        <p>This removes your cloned voice from this app. You can build it again from your clips at any time.</p>
        {DEMO && <p className="small muted">Disabled in the demo: nothing is stored here. In the real app, Delete wipes the voice embedding, the consent record and every clip made in your voice. We tested it live on 10 Nov.</p>}
        <div className="row"><button className="btn danger" disabled={DEMO} onClick={del}>Delete</button><button className="btn ghost" onClick={() => setConfirm(false)}>Cancel</button></div>
      </Sheet>
    </div>
  );
}
