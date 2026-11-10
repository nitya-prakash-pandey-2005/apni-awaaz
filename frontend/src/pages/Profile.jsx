import { useEffect, useState } from "react";
import { Lock, Save, Type, UserRound } from "lucide-react";
import { Card, PageHead, Seg, toast } from "../ui";
import { DeleteVoiceButton, LangSelect } from "../components/bits";
import { sendJSON } from "../lib/api";
import { CONDITIONS, VOICES } from "../lib/langs";
import { getTextSize, setTextSize } from "../lib/prefs";
import { navigate } from "../lib/router";
import { useApp } from "../state/app";

const when = (iso) => { try { return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); } catch { return iso; } };

export default function Profile() {
  const { profile, reloadProfile, reloadHealth } = useApp();
  const [form, setForm] = useState(null);
  const [busy, setBusy] = useState(false);
  const [size, setSize] = useState(getTextSize());

  useEffect(() => {
    if (profile && !form) {
      setForm({
        name: profile.name || "", language: profile.language || "hi-IN", local_language: profile.local_language || "hi-IN",
        family: (profile.family_names || []).join(", "), condition: profile.condition || "", fallback_voice: profile.fallback_voice || "Shivani",
      });
    }
  }, [profile, form]);

  if (!form) return <div className="skeleton" style={{ height: 320 }} />;
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v?.target ? v.target.value : v }));
  const names = form.family.split(",").map((s) => s.trim()).filter(Boolean);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await sendJSON("PUT", "/api/profile", {
        name: form.name, language: form.language, local_language: form.local_language,
        family_names: names, condition: form.condition, fallback_voice: form.fallback_voice,
      });
      await reloadProfile();
      toast("Saved.", "ok");
    } catch (err) {
      toast(err.message, "warn");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <PageHead kicker="Profile" title="About you" sub="This helps the app speak and listen the way you need." />
      <div className="stack">
        <Card title="Your details" icon={UserRound}>
          <form className="stack" onSubmit={submit}>
            <div className="grid g2">
              <label className="field">Name
                <input className="input" value={form.name} maxLength={60} onChange={set("name")} placeholder="For example: Asha" />
              </label>
              <label className="field">Condition (optional)
                <input className="input" list="conditions" value={form.condition} maxLength={120} onChange={set("condition")} placeholder="For example: Stroke" />
                <datalist id="conditions">{CONDITIONS.map((c) => <option key={c} value={c} />)}</datalist>
              </label>
              <label className="field" htmlFor="pf-lang">My language
                <LangSelect id="pf-lang" value={form.language} onChange={set("language")} />
              </label>
              <label className="field" htmlFor="pf-local">Language spoken around me (for SOS)
                <LangSelect id="pf-local" value={form.local_language} onChange={set("local_language")} />
              </label>
            </div>
            <label className="field">Family names, separated by commas
              <input className="input" value={form.family} onChange={set("family")} placeholder="For example: Ravi, Meena" />
              <span className="tiny muted">Live captions spell these names right, and your SOS message asks people to call them.</span>
            </label>
            <label className="field">Standard voice (speaks until your own voice is ready, or if it is unavailable)
              <select className="select" value={form.fallback_voice} onChange={set("fallback_voice")}>
                <optgroup label="Female voices">{VOICES.female.map((v) => <option key={v}>{v}</option>)}</optgroup>
                <optgroup label="Male voices">{VOICES.male.map((v) => <option key={v}>{v}</option>)}</optgroup>
              </select>
            </label>
            <button type="submit" className="btn primary lg block" disabled={busy}><Save size={18} /> {busy ? "Saving…" : "Save"}</button>
          </form>
        </Card>

        <Card title="Text size" icon={Type}>
          <div className="row between wrap" style={{ rowGap: 10 }}>
            <span className="small text-2">Bigger phrases, captions and SOS text.</span>
            <Seg options={[{ value: "normal", label: "Normal" }, { value: "large", label: "Large" }]} value={size}
              onChange={(v) => { setSize(v); setTextSize(v); }} />
          </div>
        </Card>

        <Card title="Privacy" icon={Lock} className="private">
          <ul className="plain-list">
            <li><b>Your voice model:</b> {profile?.has_voice ? `kept only on this device's server (built ${when(profile.voice_meta?.created_at)}).` : "none yet."}</li>
            <li><b>Consent:</b> {profile?.consent_at ? `given on ${when(profile.consent_at)}.` : "not given yet."}</li>
            <li><b>Sent to Gnani AI:</b> the voice clip, once, to build your voice, and each sentence you ask it to say.</li>
            <li><b>Sent to the language model:</b> sentences that need translating, and the last few lines of a conversation, to suggest replies.</li>
            <li><b>Never:</b> sold or shared by this app.</li>
          </ul>
          <div className="row wrap" style={{ marginTop: 14 }}>
            {profile?.has_voice
              ? <DeleteVoiceButton onDeleted={() => { reloadProfile(); reloadHealth(); }} />
              : <button type="button" className="btn" onClick={() => navigate("/voice")}>Build my voice</button>}
          </div>
        </Card>
      </div>
    </div>
  );
}
