// Profile: name, language, family names (sent to Prisma as keyterms), condition, fallback voice, delete my voice.
import { useEffect, useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { Badge, Card, Sheet, toast } from "../ui";
import { send } from "../lib/api";
import { LANGS, VOICES } from "../lib/langs";

export default function Profile({ profile, reload }) {
  const [form, setForm] = useState(null);
  const [confirm, setConfirm] = useState(false);
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

      <Card title="My voice" right={<Badge tone={profile.has_voice ? "green" : "muted"} dot>{profile.has_voice ? "Cloned" : "Not set"}</Badge>}>
        <p className="small muted" style={{ marginTop: 0 }}>
          {profile.has_voice ? `Consent given ${profile.consent_at}. The voice embedding is stored only on this app's server.` : "No cloned voice. The fallback voice is used."}
        </p>
        <button className="btn danger" disabled={!profile.has_voice} onClick={() => setConfirm(true)}><Trash2 size={16} /> Delete my voice</button>
      </Card>

      <Sheet open={confirm} onClose={() => setConfirm(false)} title="Delete your voice?">
        <p>This removes your cloned voice from this app. You can build it again from your clips at any time.</p>
        <div className="row"><button className="btn danger" onClick={del}>Delete</button><button className="btn ghost" onClick={() => setConfirm(false)}>Cancel</button></div>
      </Sheet>
    </div>
  );
}
