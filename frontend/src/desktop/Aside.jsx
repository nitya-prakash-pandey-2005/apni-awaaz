// Desktop-only right column (>= 1200 px): context, the person's own recordings and plain explanations.
// Uses only real data: the profile, and in the demo build the recordings captured on Gnani's live servers.
import { useEffect, useState } from "react";
import { AudioLines, BadgeCheck, ClipboardList, Ear, History, KeyRound, Lightbulb, MessagesSquare, ShieldCheck, Siren, Sparkles } from "lucide-react";
import { Badge, Card } from "../ui";
import { DEMO, DEMO_DIR } from "../lib/demo";
import { langName } from "../lib/langs";
import Wave from "./Wave";

function useDemoJson(name) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!DEMO) return undefined;
    let alive = true;
    fetch(`${DEMO_DIR}${name}.json`).then((r) => (r.ok ? r.json() : null)).then((d) => alive && setData(d)).catch(() => {});
    return () => { alive = false; };
  }, [name]);
  return data;
}

const day = (iso) => { try { return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" }); } catch { return ""; } };

function Steps({ items }) {
  return (
    <ol className="aa-steps">
      {items.map(([t, s], i) => <li key={t}><span className="aa-step-n">{i + 1}</span><span><b>{t}</b><small>{s}</small></span></li>)}
    </ol>
  );
}

function Tips({ items }) {
  return <ul className="aa-tips">{items.map((t) => <li key={t}>{t}</li>)}</ul>;
}

function VoiceCard({ profile }) {
  const clips = useDemoJson("voice-clips");
  const m = profile?.voice_meta;
  const list = clips?.clips || [];
  const note = list.find((c) => m?.text && c.quality?.text === m.text) || list.find((c) => c.quality?.ok);
  return (
    <Card title="Your voice" icon={AudioLines} right={profile?.has_voice ? <Badge tone="green" dot>Cloned voice</Badge> : <Badge tone="amber" dot>Fallback: {profile?.fallback_voice || "Shivani"}</Badge>} className="aa-aside-card glowy">
      {profile?.has_voice
        ? <p className="small muted aa-lead">Every sentence is spoken in the voice rebuilt from {profile?.name ? `${profile.name.split(" ")[0]}'s` : "your"} old voice notes{profile?.consent_at ? `, with consent given on ${day(profile.consent_at)}` : ""}.</p>
        : <p className="small muted aa-lead">No cloned voice yet. Add a few old voice notes on My voice to build it; until then a stock Gnani voice speaks.</p>}
      {note && <div className="aa-sub-h">Voice note it was built from</div>}
      {note && <Wave url={`${DEMO_DIR}${note.file}`} label={`voice note ${note.name}`} />}
      {m && (
        <dl className="aa-kv">
          <div><dt>Length</dt><dd className="num">{m.duration_s?.toFixed(1)} s</dd></div>
          <div><dt>Speech</dt><dd className="num">{m.speech_s?.toFixed(1)} s</dd></div>
          <div><dt>Clipping</dt><dd className="num">{m.clipping_pct?.toFixed(1)}%</dd></div>
          <div><dt>Language</dt><dd>{langName(m.lang || profile?.language)}</dd></div>
        </dl>
      )}
      {m?.text && <p className="aa-quote" lang={(m.lang || "hi-IN").slice(0, 2)}>&ldquo;{m.text}&rdquo;</p>}
    </Card>
  );
}

function History_({ title = "Spoken in your voice", filter = () => true, limit = 4 }) {
  const recs = useDemoJson("recordings");
  const list = (Array.isArray(recs) ? recs : []).filter((r) => r.file && filter(r)).slice(0, limit);
  if (!DEMO || !list.length) return null;
  return (
    <Card title={title} icon={History} right={<Badge tone="cyan">Live · 10 Nov</Badge>} className="aa-aside-card">
      <div className="aa-hist">
        {list.map((r) => (
          <div key={r.file} className="aa-hist-row">
            <div className="aa-hist-t" lang={(r.lang || "hi-IN").slice(0, 2)}>{r.spoken || r.text || "SOS message"}</div>
            <div className="aa-hist-s">{r.kind === "sos" ? "SOS · two languages" : langName(r.lang)}{r.spoken && r.text && r.spoken !== r.text ? ` · typed "${r.text}"` : ""}</div>
            <Wave url={`${DEMO_DIR}${r.file}`} label={r.spoken || r.text || "SOS message"} height={34} compact />
          </div>
        ))}
      </div>
    </Card>
  );
}

function SpeakAside({ profile }) {
  return (
    <>
      <VoiceCard profile={profile} />
      <History_ filter={(r) => r.kind === "speak"} />
      <Card title="Quick tips" icon={Lightbulb} className="aa-aside-card">
        <Tips items={[
          "Type in Latin letters: “mujhe paani chahiye” is spoken as मुझे पानी चाहिए.",
          "Prediction chips finish the word or the whole phrase; your own phrases rank first.",
          "Can’t tap? Turn on Switch scanning and press Space, Enter or a switch.",
          "Head pointer or eye-gaze? Profile → Select by holding the pointer still.",
        ]} />
      </Card>
    </>
  );
}

function ConverseAside({ profile }) {
  const fam = profile?.family_names || [];
  return (
    <>
      <Card title="Conversation context" icon={MessagesSquare} className="aa-aside-card glowy">
        <p className="small muted aa-lead">Suggested replies are written for {profile?.name || "you"}{profile?.condition ? `, ${profile.condition}` : ""}, in {langName(profile?.language || "hi-IN")}.</p>
        {fam.length > 0 && <><div className="aa-sub-h">Names the captions listen for</div><div className="aa-tags">{fam.map((n) => <span key={n} className="aa-tag">{n}</span>)}</div></>}
      </Card>
      <Card title="How Converse works" icon={Ear} className="aa-aside-card">
        <Steps items={[
          ["They speak", "The phone listens to the other person."],
          ["Live captions", "Gnani Prisma v3.0 writes what they said, in their language."],
          ["Three replies", "Suggestions appear within about a second."],
          ["One tap", "Your reply is spoken in your own voice."],
        ]} />
      </Card>
      <Card title="After a doctor's visit" icon={ClipboardList} className="aa-aside-card">
        <p className="small muted aa-lead">Tap <b>{DEMO ? "Show the recorded visit notes" : "Make visit notes"}</b>: the captions and your replies become a medicines table, tests, the next visit and what to watch for, read back in your own voice. Made by AI, so check them with the doctor.</p>
      </Card>
      <History_ title="Replies spoken in your voice" filter={(r) => r.kind === "speak" && r.lang === (profile?.language || "hi-IN")} limit={3} />
    </>
  );
}

function VoiceAside({ profile }) {
  return (
    <>
      <VoiceCard profile={profile} />
      <Card title="What the checks mean" icon={BadgeCheck} className="aa-aside-card">
        <dl className="aa-explain">
          <div><dt>Length</dt><dd>Gnani needs 5 to 30 s of clear speech. A note with less is flagged; a long note is judged on the 30 s actually used.</dd></div>
          <div><dt>Clipping</dt><dd>Audio recorded too loud loses detail. Clipped notes are flagged so the clone does not copy the distortion.</dd></div>
          <div><dt>Noise</dt><dd>Traffic, fans or TV behind the voice. Quieter notes make a closer voice.</dd></div>
          <div><dt>Clear speech</dt><dd>Gnani Prisma transcribes the note. If it hears no clear words, the note is not used.</dd></div>
        </dl>
      </Card>
      <Card title="Consent first" icon={KeyRound} className="aa-aside-card">
        <p className="small muted aa-lead">Nothing is uploaded until you tick consent. Building a voice without it is refused by the server (HTTP 400 in our tests). Delete my voice wipes the embedding, the consent record and every clip made in your voice.</p>
      </Card>
    </>
  );
}

function SosAside() {
  return (
    <>
      <Card title="What SOS does" icon={Siren} className="aa-aside-card glowy">
        <Steps items={[
          ["Speaks for you", "An emergency message in your voice, in your language and a second one."],
          ["Shows it large", "The same words in big type, for anyone nearby to read."],
          ["Works offline", "If the server or Gnani is down, the phone’s own voice reads it."],
          ["Tells family", "WhatsApp or SMS with your location. You press Send; the app never sends anything itself."],
        ]} />
      </Card>
      <History_ title="SOS recorded in the cloned voice" filter={(r) => r.kind === "sos"} limit={1} />
    </>
  );
}

function ProfileAside() {
  return (
    <>
      <Card title="Your privacy" icon={ShieldCheck} className="aa-aside-card glowy">
        <Steps items={[
          ["The voice stays on the server", "The embedding goes only to Gnani, inside each speech request, and never reaches the browser."],
          ["Delete my voice", "Removes the embedding, the consent record and every clip made in your voice."],
          ["Family contact stays on the phone", "Saved in this browser only after you tick consent; remove it any time."],
          ["Location only when asked", "It goes only into the message you send yourself."],
        ]} />
      </Card>
      <Card title="Why we ask" icon={Sparkles} className="aa-aside-card">
        <Tips items={[
          "Your name, family names and condition help suggested replies sound like you.",
          "Family names help the captions spell them right.",
          "Your language is the one SOS and Speak use first.",
        ]} />
      </Card>
    </>
  );
}

function PainAside({ profile }) {
  return (
    <>
      <Card title="One clear sentence" icon={Sparkles} className="aa-aside-card glowy">
        <Steps items={[
          ["Where", "Tap the body, or one of the large body-part buttons."],
          ["How bad", "Faces from 0 to 10."],
          ["What kind", "The kind of pain, and since when."],
          ["Spoken", `A grammatical sentence in ${langName(profile?.language || "hi-IN")}, in your voice.`],
        ]} />
      </Card>
      <Card title="Checked by tests" icon={BadgeCheck} className="aa-aside-card">
        <p className="small muted aa-lead">Every body part, side, pain type, onset and level 0 to 10 is generated and checked: 4,400 sentences per language in Hindi, Tamil and English.</p>
      </Card>
    </>
  );
}

const BY_PATH = { "/speak": SpeakAside, "/converse": ConverseAside, "/voice": VoiceAside, "/sos": SosAside, "/profile": ProfileAside, "/pain": PainAside };

export const hasAside = (path) => !!BY_PATH[path];

export default function Aside({ path, profile }) {
  const A = BY_PATH[path];
  if (!A) return null;
  return <aside className="aa-aside" aria-label="More about this page"><A profile={profile} /></aside>;
}
