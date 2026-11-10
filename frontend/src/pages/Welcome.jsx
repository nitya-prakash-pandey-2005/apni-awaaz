import { useState } from "react";
import { AudioLines, HandHeart, Keyboard, Languages, ShieldCheck } from "lucide-react";
import { Card, Fade, PageHead, toast } from "../ui";
import { CheckRow, LangSelect } from "../components/bits";
import { sendJSON } from "../lib/api";
import { navigate } from "../lib/router";
import { save } from "../lib/prefs";
import { useApp } from "../state/app";

const STEPS = [
  { icon: AudioLines, title: "Add old voice notes", body: "WhatsApp voice notes from before work well. Half a minute of clear talking is enough." },
  { icon: HandHeart, title: "We rebuild the voice", body: "Gnani AI learns how the voice sounds, so the app can speak like you again." },
  { icon: Keyboard, title: "Type, tap or pick a reply", body: "Type in any script, tap a phrase, or tap a suggested reply. It speaks in your voice." },
  { icon: Languages, title: "In 10 Indian languages", body: "Even in a language you never spoke, like Hindi to a nurse in Delhi." },
];

export default function Welcome() {
  const { profile, reloadProfile } = useApp();
  const [name, setName] = useState(profile?.name || "");
  const [language, setLanguage] = useState(profile?.language || "hi-IN");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);

  const saveProfile = async (next) => {
    setBusy(true);
    try {
      const p = profile || {};
      await sendJSON("PUT", "/api/profile", {
        name: name.trim(), language,
        local_language: p.exists ? p.local_language : language,
        family_names: p.family_names || [], condition: p.condition || "", fallback_voice: p.fallback_voice || "Shivani",
      });
      await reloadProfile();
      if (next === "/voice") save("consent-ticked", new Date().toISOString());
      navigate(next);
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="narrow">
      <PageHead kicker="Apni Awaaz · अपनी आवाज़" title="Speak again, in your own voice"
        sub="For anyone who has lost their voice, or is losing it: after throat or mouth surgery, a stroke, ALS or Parkinson's. Family members are welcome to set this up." />
      <div className="stack">
        <Fade>
          <div className="grid g2">
            {STEPS.map((s, i) => (
              <div key={s.title} className="card tight step">
                <span className="step-n">{i + 1}</span>
                <div className="grow">
                  <div className="row"><s.icon size={17} className="c-pink" /><b>{s.title}</b></div>
                  <p className="small text-2" style={{ marginTop: 4 }}>{s.body}</p>
                </div>
              </div>
            ))}
          </div>
        </Fade>

        <Card title="About you">
          <div className="grid g2">
            <label className="field">Your name (optional)
              <input className="input" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} placeholder="For example: Asha" autoComplete="name" />
            </label>
            <label className="field" htmlFor="welcome-lang">The language you usually speak
              <LangSelect id="welcome-lang" value={language} onChange={setLanguage} />
            </label>
          </div>
        </Card>

        <Card title="Your voice, your consent" icon={ShieldCheck} className="private">
          <ul className="plain-list">
            <li>Only use voice notes of your own voice, or of someone who has agreed to this.</li>
            <li>Your voice model is kept only on this device's server, never in the app's own cloud.</li>
            <li>Gnani AI receives the clip once to build the voice, and the sentences you ask it to say.</li>
            <li>You can delete your voice at any time, with one tap.</li>
          </ul>
          <div style={{ marginTop: 14 }}>
            <CheckRow id="consent" checked={consent} onChange={setConsent}>
              This is my own voice, or the person whose voice it is has agreed to have it rebuilt.
            </CheckRow>
          </div>
        </Card>

        <div className="stack-sm">
          <button type="button" className="btn primary lg block" disabled={!consent || busy} onClick={() => saveProfile("/voice")}>
            <AudioLines size={18} /> Continue to my voice
          </button>
          <button type="button" className="btn ghost lg block" disabled={busy} onClick={() => saveProfile("/speak")}>
            Skip for now and use a standard voice
          </button>
          {!consent && <p className="tiny muted center-text">Tick the consent box to build your own voice. You can also start with a standard voice.</p>}
        </div>
      </div>
    </div>
  );
}
