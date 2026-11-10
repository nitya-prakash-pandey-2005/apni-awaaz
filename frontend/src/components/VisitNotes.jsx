// Visit notes: after a doctor or nurse visit in Converse, a checked summary of what was said (medicines, tests, next
// visit, warning signs, advice, my questions), read back in the person's own voice, downloadable and sent to family.
import { useEffect, useRef, useState } from "react";
import { Download, FileText, MessageCircle, MessageSquareText, Play, Stethoscope } from "lucide-react";
import { Badge, Card, toast } from "../ui";
import { getJSON, send } from "../lib/api";
import { DEMO, DEMO_DIR } from "../lib/demo";
import { loadFamily, smsLink, waLink } from "../lib/family";
import { canSummarise, medLine, shareText, turnsFromLines, visitMarkdown } from "../lib/visit";
import { VoiceBadge } from "../pages/Speak";

const unq = (s) => { try { return decodeURIComponent(s || ""); } catch { return s || ""; } };

function Section({ title, items, k }) {
  if (!items?.length) return null;
  return (
    <div className="visit-section">
      <h4>{title}</h4>
      <ul>{items.map((x, i) => <li key={i}>{x[k] || x.en}</li>)}</ul>
    </div>
  );
}

export default function VisitNotes({ lines, profile, listening }) {
  const [resp, setResp] = useState(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [audio, setAudio] = useState(null); // { url, voice, spoken }
  const [demoVisit, setDemoVisit] = useState(null);
  const [family] = useState(loadFamily);
  const player = useRef(null);
  const urlRef = useRef(null); // the read-back audio's object URL, freed when replaced or on leaving the page
  useEffect(() => () => { player.current?.pause(); if (urlRef.current) URL.revokeObjectURL(urlRef.current); }, []);

  // The demo summarises the doctor visit recorded in the live run (its real captions); the app uses this conversation.
  const turns = DEMO ? demoVisit?.turns || [] : turnsFromLines(lines);
  const ready = DEMO || canSummarise(lines);
  const lang = profile?.language || "hi-IN";
  const k = resp?.text_lang === "hi-IN" ? "hi" : "en";

  const make = async () => {
    setBusy(true);
    try {
      let body = { turns, lang };
      if (DEMO) {
        const v = demoVisit || await getJSON(`${DEMO_DIR}visit.json`);
        setDemoVisit(v);
        body = { turns: v.turns, lang: v.response.lang };
      }
      setResp(await (await send("/api/visit/summary", { json: body })).json());
      setAudio(null);
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setBusy(false);
    }
  };

  const play = async () => {
    if (!resp || playing) return;
    setPlaying(true);
    try {
      let a = audio;
      if (!a) {
        const r = await send("/api/speak", { json: { text: resp.text.local, lang: resp.lang, remember: false } });
        a = { url: URL.createObjectURL(await r.blob()), voice: r.headers.get("X-Voice") || "fallback", spoken: unq(r.headers.get("X-Spoken-Text")) };
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = a.url;
        setAudio(a);
      }
      player.current?.pause();
      const el = new Audio(a.url);
      player.current = el;
      await new Promise((done) => { el.onended = el.onerror = done; el.play().catch(done); });
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setPlaying(false);
    }
  };

  const playDoctor = () => {
    if (!demoVisit) return;
    player.current?.pause();
    player.current = new Audio(DEMO_DIR + demoVisit.doctor.audio);
    player.current.play().catch(() => {});
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([visitMarkdown(resp)], { type: "text/markdown;charset=utf-8" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: `visit-notes-${new Date().toISOString().slice(0, 10)}.md` });
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  if (!resp) {
    return (
      <Card title="Visit notes" icon={Stethoscope} className="visit-notes">
        <p className="small muted">
          {DEMO ? "See the notes made from a doctor visit recorded in the live session (a synthetic doctor's voice, real captions and a real summary)."
            : "After the doctor or nurse has spoken, make clear notes of what was said: medicines with dose and timing, tests, the next visit and what to watch for."}
        </p>
        <button className="btn lg primary block" onClick={make} disabled={busy || listening || !ready}>
          <FileText size={18} /> {busy ? "Making the notes…" : DEMO ? "Show the recorded visit notes" : "Make visit notes"}
        </button>
        {!DEMO && !ready && <p className="small muted">Start listening first: the notes are made from the captions.</p>}
        {!DEMO && ready && listening && <p className="small muted">Stop listening to make the notes.</p>}
      </Card>
    );
  }
  const s = resp.summary;
  const text = shareText(resp, profile?.name);
  return (
    <Card title="Visit notes" icon={Stethoscope} className="visit-notes" right={<div className="row"><VoiceBadge last={audio} />
      <Badge tone={resp.source === "llm" ? "cyan" : "amber"}>{resp.source === "llm" ? "AI, checked" : "Keyword notes"}</Badge></div>}>
      <div className="callout warn small" role="note">{resp.disclaimer}</div>
      {DEMO && demoVisit && (
        <div className="visit-said">
          <div className="small muted">What was said (live captions):</div>
          {demoVisit.turns.map((t, i) => <div key={i} className={`bubble ${t.speaker === "user" ? "me" : "them"}`}>{t.text}</div>)}
          <button className="btn" onClick={playDoctor}><Play size={16} /> Hear the doctor</button>
        </div>
      )}
      <div className="visit-section">
        <h4>Medicines</h4>
        {s.medicines.length ? (
          <table className="visit-table">
            <thead><tr><th>Medicine</th><th>Dose</th><th>When</th><th>Days</th></tr></thead>
            <tbody>{s.medicines.map((m) => (
              <tr key={m.name} aria-label={medLine(m)}><td><b>{m.name}</b></td><td>{m.dose || "–"}</td>
                <td>{medLine({ when: m.when }) || "–"}</td><td>{m.days ?? "–"}</td></tr>))}
            </tbody>
          </table>
        ) : <p className="small muted">No medicines were noted.</p>}
      </div>
      <Section title="Tests" items={s.tests} k={k} />
      <Section title="Next visit" items={s.next_visit ? [s.next_visit] : []} k={k} />
      <Section title="Watch for (go back at once)" items={s.warning_signs} k={k} />
      <Section title="Advice" items={s.advice} k={k} />
      <Section title="I asked" items={s.questions_asked} k={k} />
      <pre className="family-preview small" aria-label="Notes to read aloud">{resp.text.local}</pre>
      {audio?.spoken && audio.spoken !== resp.text.local && <div className="small muted">spoken as: {audio.spoken}</div>}
      <div className="visit-actions">
        <button className="btn lg primary" onClick={play} disabled={playing}><Play size={18} /> {playing ? "Playing…" : "Play my visit notes"}</button>
        <button className="btn lg" onClick={download}><Download size={18} /> Download notes</button>
        {audio && <a className="btn lg" href={audio.url} download="visit-notes.wav"><Download size={18} /> Download audio</a>}
      </div>
      {family ? (
        <div className="stack-sm">
          <div className="small muted">Send to <b>{family.name}</b> (+{family.phone})</div>
          <div className="family-actions">
            <a className="btn primary" href={waLink(family.phone, text)} target="_blank" rel="noreferrer"><MessageCircle size={18} /> WhatsApp</a>
            <a className="btn" href={smsLink(family.phone, text)}><MessageSquareText size={18} /> SMS</a>
          </div>
        </div>
      ) : <div className="small muted">Add a family contact in <a href="#/profile">Profile</a> to send these notes with one tap.</div>}
      <button className="btn ghost" onClick={() => { player.current?.pause(); setResp(null); setAudio(null); }}>Close the notes</button>
    </Card>
  );
}
