// "Where does it hurt?": tap the body, set how bad (0-10) and what kind; one natural sentence is spoken in the person's voice.
import { useEffect, useMemo, useState } from "react";
import { Volume2 } from "lucide-react";
import { Badge, Card, Seg, toast } from "../ui";
import { send, useSpeak } from "../lib/api";
import { LangChips, langName } from "../lib/langs";
import { PAIN, painSentence, partLabel, partOf, templateLang } from "../lib/pain";
import { speak as speakLocally } from "../lib/speech";
import { DEMO } from "../lib/demo";
import { VoiceBadge } from "./Speak";

const TYPES = [["sharp", "Sharp"], ["burning", "Burning"], ["dull", "Dull, aching"], ["throbbing", "Throbbing"], ["itching", "Itching"]];
const SINCE = [["", "Don't say"], ["just_now", "Just now"], ["today", "Today"], ["yesterday", "Since yesterday"]];
const FACES = [[0, "😀", "No pain"], [2, "🙂", "A little"], [4, "😐", "Some"], [6, "🙁", "Quite bad"], [8, "😣", "Very bad"], [10, "😭", "Worst"]];
const levelColor = (n) => `hsl(${120 - n * 12} 75% 52%)`;

// Body regions in a 200 x 400 box. Front view: the person's left is on the viewer's right (as when facing someone).
const SHAPES = {
  head: { e: [100, 38, 24, 28] },
  eye: { left: { e: [111, 33, 7, 6] }, right: { e: [89, 33, 7, 6] } },
  ear: { left: { e: [127, 40, 6, 10] }, right: { e: [73, 40, 6, 10] } },
  mouth: { e: [100, 53, 10, 5] },
  throat: { r: [86, 68, 28, 16] },
  neck: { r: [86, 66, 28, 18] },
  chest: { r: [64, 86, 72, 56] },
  stomach: { r: [68, 144, 64, 52] },
  upper_back: { r: [64, 86, 72, 60] },
  lower_back: { r: [68, 148, 64, 48] },
  arm: { left: { r: [140, 88, 24, 98] }, right: { r: [36, 88, 24, 98] } },
  hand: { left: { e: [152, 202, 13, 16] }, right: { e: [48, 202, 13, 16] } },
  leg: { left: { r: [102, 200, 28, 146] }, right: { r: [70, 200, 28, 146] } },
  foot: { left: { e: [118, 364, 17, 11] }, right: { e: [82, 364, 17, 11] } },
};
const mirror = ({ e, r }) => (e ? { e: [200 - e[0], ...e.slice(1)] } : { r: [200 - r[0] - r[2], ...r.slice(1)] });

function regions(view) {
  const out = [];
  for (const p of PAIN.parts) {
    if (p.view !== "both" && p.view !== view) continue;
    const s = SHAPES[p.id];
    if (!p.sided) out.push({ part: p.id, side: null, shape: s });
    else for (const side of ["right", "left"]) out.push({ part: p.id, side, shape: view === "front" ? s[side] : mirror(s[side]) });
  }
  return out;
}

function BodyMap({ view, sel, onPick }) {
  const list = useMemo(() => regions(view), [view]);
  const [lx, rx] = view === "front" ? [178, 22] : [22, 178]; // where the person's left / right is drawn
  return (
    <svg className="body-map" viewBox="0 0 200 400" role="group" aria-label={`Body, ${view} view. Choose where it hurts.`}>
      {list.map(({ part, side, shape }) => {
        const on = sel.part === part && sel.side === side;
        const label = partLabel(part, side);
        const props = {
          className: `body-part dwell-target ${on ? "on" : ""}`, role: "button", tabIndex: 0, "aria-label": label, "aria-pressed": on,
          onClick: () => onPick(part, side),
          onKeyDown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onPick(part, side); } },
        };
        return shape.e
          ? <ellipse key={`${part}-${side}`} cx={shape.e[0]} cy={shape.e[1]} rx={shape.e[2]} ry={shape.e[3]} {...props}><title>{label}</title></ellipse>
          : <rect key={`${part}-${side}`} x={shape.r[0]} y={shape.r[1]} width={shape.r[2]} height={shape.r[3]} rx={12} {...props}><title>{label}</title></rect>;
      })}
      <text x={lx} y={392} className="body-side" textAnchor="middle" aria-hidden="true">L</text>
      <text x={rx} y={392} className="body-side" textAnchor="middle" aria-hidden="true">R</text>
    </svg>
  );
}

export default function Pain({ profile }) {
  const [view, setView] = useState("front");
  const [sel, setSel] = useState({ part: null, side: null });
  const [level, setLevel] = useState(5);
  const [type, setType] = useState("sharp");
  const [since, setSince] = useState("");
  const [lang, setLang] = useState(profile?.language || "hi-IN");
  const [device, setDevice] = useState(null); // demo: spoken with the phone's own voice
  const { busy, last, say } = useSpeak();
  useEffect(() => { if (profile?.language) setLang(profile.language); }, [profile?.language]);

  const ready = !!sel.part;
  const text = ready ? painSentence({ ...sel, level, type, since, lang }) : "";
  const tl = templateLang(lang);
  const pick = (part, side) => setSel({ part, side });

  const speakIt = async () => {
    if (!ready || busy) return;
    if (DEMO) { // no server in the demo: the phone reads it, and the badge says so
      setDevice({ voice: "device" });
      speakLocally(text, { lang: tl });
      return;
    }
    try {
      const r = await send("/api/pain/sentence", { json: { ...sel, level, type, since, lang } });
      setDevice(null);
      await say((await r.json()).text, lang);
    } catch (e) {
      toast(e.message, "warn");
    }
  };

  const partChips = PAIN.parts.filter((p) => p.view === "both" || p.view === view)
    .flatMap((p) => (p.sided ? ["left", "right"].map((s) => [p.id, s]) : [[p.id, null]]));

  return (
    <div className="stack pain">
      <Card title="1. Where does it hurt?" right={<Seg options={[{ value: "front", label: "Front" }, { value: "back", label: "Back" }]} value={view} onChange={setView} />}>
        <div className="pain-body">
          <BodyMap view={view} sel={sel} onPick={pick} />
          <div className="part-chips" role="group" aria-label="Body parts">
            {partChips.map(([part, side]) => {
              const on = sel.part === part && sel.side === side;
              return <button key={`${part}-${side}`} type="button" aria-pressed={on} className={`chip part-chip ${on ? "on" : ""}`} onClick={() => pick(part, side)}>{partLabel(part, side)}</button>;
            })}
          </div>
        </div>
        <div className="small muted" style={{ marginTop: 8 }}>L and R are the person's own left and right ({view === "front" ? "front view: as if you are facing them" : "back view: seen from behind"}).</div>
      </Card>

      <Card title="2. How bad is it?" right={<Badge tone={level >= 7 ? "rose" : level >= 4 ? "amber" : "green"}>{level} / 10</Badge>}>
        <div className="faces" role="group" aria-label="Pain level faces">
          {FACES.map(([n, face, label]) => (
            <button key={n} type="button" className={`face dwell-target ${level === n ? "on" : ""}`} aria-pressed={level === n} aria-label={`${n} out of 10: ${label}`}
              style={{ "--c": levelColor(n) }} onClick={() => setLevel(n)}>
              <span aria-hidden="true">{face}</span><small>{n}</small>
            </button>
          ))}
        </div>
        <input className="pain-slider" type="range" min={0} max={10} step={1} value={level} style={{ "--c": levelColor(level) }}
          onChange={(e) => setLevel(Number(e.target.value))} aria-label="Pain level from 0 to 10" aria-valuetext={`${level} out of 10`} />
      </Card>

      <Card title="3. What kind of pain?">
        <div className="phrase-grid pain-types">
          {TYPES.map(([v, l]) => <button key={v} type="button" aria-pressed={type === v} className={`phrase ${type === v ? "picked" : ""}`} onClick={() => setType(v)}>{l}</button>)}
        </div>
        <div className="pain-since" role="group" aria-label="Since when">
          {SINCE.map(([v, l]) => <button key={v || "none"} type="button" aria-pressed={since === v} className={`chip ${since === v ? "on" : ""}`} onClick={() => setSince(v)}>{l}</button>)}
        </div>
      </Card>

      <Card title="4. Say it" right={<VoiceBadge last={device || last} />}>
        <div className="stack-sm">
          <LangChips value={lang} onChange={setLang} />
          <p className="pain-sentence" lang={tl.slice(0, 2)} aria-live="polite">{ready ? text : "Tap where it hurts on the body or in the list."}</p>
          {ready && tl !== lang && <div className="small muted">Written in English; {DEMO ? "the phone reads it in English in the demo" : `spoken in ${langName(lang)} (translated on the way out)`}.</div>}
          <button className="btn primary lg block speak-btn" disabled={!ready || busy} onClick={speakIt}>
            <Volume2 size={22} /> {busy ? "Speaking…" : "Speak"}
          </button>
          {DEMO && <div className="small muted">In the demo the phone's own voice reads the sentence. The real app speaks it in your cloned voice.</div>}
        </div>
      </Card>
    </div>
  );
}
