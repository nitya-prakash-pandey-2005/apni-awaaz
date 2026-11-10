import { useEffect, useState } from "react";
import { Info, Loader2, Siren, Square } from "lucide-react";
import { Card, toast, Toggle } from "../ui";
import { LangChips, VoiceBadge } from "../components/bits";
import { fetchSos } from "../lib/api";
import { playBlob, primeAudio, stopAudio, usePlaying } from "../lib/audio";
import { langOf } from "../lib/langs";
import { load, save } from "../lib/prefs";
import { useApp } from "../state/app";

function englishPreview(p) {
  const fam = (p?.family_names || []).filter(Boolean);
  return ["Please help me.", "I have trouble speaking.", p?.name ? `My name is ${p.name}.` : null,
    fam.length ? `Please call my family: ${fam.join(", ")}.` : "Please call my family."].filter(Boolean).join(" ");
}

export default function Sos() {
  const { profile } = useApp();
  const [local, setLocal] = useState(() => load("sos-local", profile?.local_language || profile?.language || "hi-IN"));
  const [loop, setLoop] = useState(() => load("sos-loop", true));
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null); // { lines, meta }
  const [active, setActive] = useState(-1);
  const playing = usePlaying();

  useEffect(() => () => stopAudio(), []);
  useEffect(() => { if (!playing) setActive(-1); }, [playing]);

  const changeLocal = (code) => { setLocal(code); save("sos-local", code); };
  const changeLoop = (v) => { setLoop(v); save("sos-loop", v); };

  const go = async () => {
    primeAudio();
    setBusy(true);
    try {
      const { blob, meta } = await fetchSos(local);
      const lines = meta.sosLines || [];
      setRes({ lines, meta });
      setBusy(false);
      await playBlob(blob, {
        loop,
        onTime: (t) => setActive(lines.findIndex((l) => t >= l.start_s - 0.05 && t <= l.end_s + 0.35)),
      });
    } catch (e) {
      setBusy(false);
      toast(e.message, "warn");
    }
  };

  const mine = profile?.language || "hi-IN";
  return (
    <div className="narrow">
      <div className="stack">
        <section className="card alert sos-hero">
          <div className="row" style={{ gap: 12 }}>
            <span className="sos-ic"><Siren size={26} /></span>
            <div className="grow">
              <h1 className="sos-title">Need help now?</h1>
              <p className="text-2 small">One tap says your emergency message out loud, in {langOf(mine).native}
                {local !== mine ? ` and ${langOf(local).native}` : ""}, again and again until you stop it.</p>
            </div>
          </div>
          {playing ? (
            <button type="button" className="sos-btn stop" onClick={stopAudio}><Square size={30} /> Stop</button>
          ) : (
            <button type="button" className="sos-btn" onClick={go} disabled={busy}>
              {busy ? <><Loader2 size={30} className="spin" /> Getting ready…</> : <><Siren size={32} /> Speak SOS</>}
            </button>
          )}
          <div className="row between wrap" style={{ marginTop: 14, rowGap: 8 }}>
            <span className="small text-2">Repeat until I stop</span>
            <Toggle on={loop} onChange={changeLoop} label="Repeat until I stop" />
          </div>
        </section>

        {res?.lines?.length ? (
          <Card title="What it says" right={<VoiceBadge meta={res.meta} />}>
            <div className="stack">
              {res.lines.map((l, i) => (
                <p key={l.lang} className={`sos-line ${active === i ? "on" : ""}`} lang={l.lang}>{l.text}</p>
              ))}
            </div>
          </Card>
        ) : (
          <Card title="What it says">
            <p className="sos-line on" lang="en">{englishPreview(profile)}</p>
            <p className="tiny muted" style={{ marginTop: 8 }}>Spoken in your languages. Add family names in Profile.</p>
          </Card>
        )}

        <Card title="Also say it in">
          <LangChips value={local} onChange={changeLocal} label="Also say it in" />
          <p className="tiny muted" style={{ marginTop: 10 }}>Pick the language people around you speak, for example Tamil in Chennai.</p>
        </Card>

        <div className="callout">
          <Info size={18} className="c-cyan flex-none" />
          <span className="small text-2">This speaks out loud to people near you. It does not call anyone. For emergency services in India, call <b>112</b>.</span>
        </div>
      </div>
    </div>
  );
}
