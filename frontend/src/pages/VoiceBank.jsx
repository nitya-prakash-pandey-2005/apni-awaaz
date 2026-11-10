import { useEffect, useRef, useState } from "react";
import { CheckCircle2, FileAudio, Loader2, Mic, Play, RotateCcw, ShieldCheck, Sparkles, Square, Upload, X } from "lucide-react";
import { decodeToPcm16, pcmToWav, startMic } from "@voice/index.js";
import { Badge, Card, PageHead, toast } from "../ui";
import { CheckRow, DeleteVoiceButton, VoiceBadge } from "../components/bits";
import { fetchAudio, postForm } from "../lib/api";
import { playBlob, primeAudio, stopAudio, usePlaying } from "../lib/audio";
import { fallbackNote, reasonText } from "../lib/copy";
import { load, save } from "../lib/prefs";
import { navigate } from "../lib/router";
import { useApp } from "../state/app";

const RATE = 16000;
const MAX_CLIPS = 5;
const MAX_S = 30;
const DECODE_FAIL = "We could not open this file. Please export the voice note as MP3 or WAV and add it again.";
let nextId = 1;
let recCount = 0;

const fmtS = (s) => `${Math.round(s)} s`;
const when = (iso) => { try { return new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }); } catch { return iso; } };

function ClipRow({ clip, onRemove }) {
  const r = clip.result;
  let badge;
  if (clip.status === "decoding") badge = <Badge tone="muted"><Loader2 size={12} className="spin" /> Opening…</Badge>;
  else if (clip.status === "checking") badge = <Badge tone="cyan"><Loader2 size={12} className="spin" /> Checking…</Badge>;
  else if (clip.status === "error") badge = <Badge tone="rose" dot>Could not use</Badge>;
  else if (r?.ok) badge = <Badge tone="green" dot>Good</Badge>;
  else badge = <Badge tone="amber" dot>Needs another clip</Badge>;
  return (
    <div className="clip-row">
      <span className="clip-ic">{clip.recorded ? <Mic size={17} /> : <FileAudio size={17} />}</span>
      <div className="grow">
        <div className="row between wrap" style={{ rowGap: 6 }}>
          <b className="clip-name">{clip.name}</b>
          {badge}
        </div>
        {r && (
          <div className="tiny muted" style={{ marginTop: 3 }}>
            {fmtS(r.duration_s)} long · {fmtS(r.speech_s)} of talking · clarity {Math.round(r.snr_db)} dB
            {clip.trimmed || r.trimmed ? " · first 30 s used" : ""}
          </div>
        )}
        {clip.status === "error" && <p className="small c-rose" style={{ marginTop: 4 }}>{clip.error}</p>}
        {r && !r.ok && (
          <ul className="reasons">{r.reasons.map((x) => <li key={x}>{reasonText(x)}</li>)}</ul>
        )}
        {r?.transcript && <p className="heard small" lang={r.language || undefined}>We heard: “{r.transcript}”</p>}
        {r?.ok && r.stt_error && <p className="tiny muted" style={{ marginTop: 4 }}>We could not check the words right now, but the sound is clear.</p>}
      </div>
      <button type="button" className="btn icon sm ghost" onClick={onRemove} aria-label={`Remove ${clip.name}`}><X size={15} /></button>
    </div>
  );
}

export default function VoiceBank() {
  const { profile, reloadProfile, reloadHealth } = useApp();
  const [clips, setClips] = useState([]);
  const [consent, setConsent] = useState(() => !!load("consent-ticked", null));
  const [building, setBuilding] = useState(false);
  const [built, setBuilt] = useState(null); // enroll response
  const [testMeta, setTestMeta] = useState(null);
  const [rec, setRec] = useState(null); // { seconds }
  const [showWizard, setShowWizard] = useState(!profile?.has_voice);
  const fileRef = useRef(null);
  const recRef = useRef(null);
  const playing = usePlaying();

  useEffect(() => () => { recRef.current?.mic?.stop(); stopAudio(); }, []);

  const update = (id, patch) => setClips((cs) => cs.map((c) => (c.id === id ? { ...c, ...patch } : c)));

  const check = async (id, wav, name) => {
    update(id, { status: "checking", wav });
    try {
      const form = new FormData();
      form.append("audio", wav, `${name.replace(/\.[^.]+$/, "")}.wav`);
      const result = await postForm("/api/voice/clip-check", form);
      update(id, { status: "done", result });
    } catch (e) {
      update(id, { status: "error", error: e.message });
    }
  };

  const addFiles = async (fileList) => {
    const room = MAX_CLIPS - clips.length;
    const files = Array.from(fileList || []).slice(0, Math.max(0, room));
    if (fileList?.length > room) toast(`You can add up to ${MAX_CLIPS} voice notes.`, "info");
    const items = files.map((f) => ({ id: nextId++, name: f.name || "Voice note", status: "decoding", file: f }));
    setClips((cs) => [...cs, ...items]);
    for (const it of items) { // one at a time: gentle on slow networks and on Gnani's one-request limit
      let pcm;
      try {
        pcm = await decodeToPcm16(it.file, RATE);
      } catch {
        update(it.id, { status: "error", error: DECODE_FAIL });
        continue;
      }
      const trimmed = pcm.length > MAX_S * RATE;
      if (trimmed) pcm = pcm.subarray(0, MAX_S * RATE);
      update(it.id, { trimmed });
      await check(it.id, pcmToWav(pcm, RATE), it.name);
    }
  };

  const startRec = async () => {
    if (clips.length >= MAX_CLIPS) return toast(`You can add up to ${MAX_CLIPS} voice notes.`, "info");
    const frames = [];
    try {
      const mic = await startMic({ targetRate: RATE, onFrame: (ab) => frames.push(new Int16Array(ab)) });
      const t0 = Date.now();
      const timer = setInterval(() => {
        const s = (Date.now() - t0) / 1000;
        setRec({ seconds: s });
        if (s >= MAX_S) stopRec();
      }, 200);
      recRef.current = { mic, frames, timer };
      setRec({ seconds: 0 });
    } catch {
      toast("Please allow the microphone to record.", "warn");
    }
  };

  const stopRec = async () => {
    const r = recRef.current;
    if (!r) return;
    recRef.current = null;
    clearInterval(r.timer);
    r.mic.stop();
    setRec(null);
    const n = r.frames.reduce((a, f) => a + f.length, 0);
    const pcm = new Int16Array(n);
    let o = 0;
    for (const f of r.frames) { pcm.set(f, o); o += f.length; }
    const id = nextId++;
    const name = `Recording ${++recCount}`;
    setClips((cs) => [...cs, { id, name, status: "checking", recorded: true }]);
    await check(id, pcmToWav(pcm, RATE), name);
  };

  const good = clips.filter((c) => c.result?.ok && c.wav);
  const busyClips = clips.some((c) => c.status === "decoding" || c.status === "checking");

  const playTest = async (url) => {
    primeAudio();
    try {
      const { blob, meta } = await fetchAudio(url);
      setTestMeta(meta);
      await playBlob(blob);
    } catch (e) {
      toast(e.message, "warn");
    }
  };

  const build = async () => {
    primeAudio();
    setBuilding(true);
    setBuilt(null);
    setTestMeta(null);
    try {
      const form = new FormData();
      good.forEach((c) => form.append("audio", c.wav, `${c.name.replace(/\.[^.]+$/, "")}.wav`));
      form.append("consent", consent ? "true" : "false");
      const r = await postForm("/api/voice/enroll", form);
      save("consent-ticked", new Date().toISOString());
      setBuilt(r);
      await Promise.all([reloadProfile(), reloadHealth()]);
      await playTest(r.test_audio_url);
    } catch (e) {
      toast(e.message, "warn");
    } finally {
      setBuilding(false);
    }
  };

  const restart = () => {
    stopAudio();
    setClips([]);
    setBuilt(null);
    setTestMeta(null);
    setShowWizard(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const chosenName = built ? built.clips[built.chosen]?.filename : null;
  const meta = profile?.voice_meta;

  return (
    <div className="narrow">
      <PageHead kicker="Voice bank" title="Your voice"
        sub="Add 1 to 5 voice notes where you are talking. We check each one, then build your voice from the clearest." />
      <div className="stack">
        {built && (
          <Card title="Listen: is this your voice?" icon={Sparkles} className="good">
            <p className="hi big-line" lang={profile?.language}>{testMeta?.spokenText || "…"}</p>
            <div className="row wrap" style={{ marginTop: 10 }}>
              <VoiceBadge meta={testMeta} />
              {chosenName && <span className="tiny muted">Built from {chosenName}</span>}
            </div>
            {testMeta?.voice === "fallback" && (
              <div className="callout" style={{ marginTop: 12 }}>
                <span className="small">Your voice model is saved, but cloning is not available right now, so you heard a
                  standard voice. The app will use your own voice as soon as it is back.</span>
              </div>
            )}
            <div className="grid g3" style={{ marginTop: 14 }}>
              <button type="button" className="btn success lg" onClick={() => { toast("Your voice is ready.", "ok"); navigate("/speak"); }}>
                <CheckCircle2 size={18} /> Sounds like me
              </button>
              <button type="button" className="btn lg" onClick={() => playTest(built.test_audio_url)} disabled={playing}>
                <Play size={18} /> Play again
              </button>
              <button type="button" className="btn ghost lg" onClick={restart}><RotateCcw size={18} /> Try other clips</button>
            </div>
          </Card>
        )}

        {profile?.has_voice && !built && (
          <Card title="Your voice is ready" icon={CheckCircle2} className="good"
            right={<button type="button" className="btn sm" onClick={() => playTest(`/api/voice/test?lang=${profile.language}&v=${profile.voice_id}`)} disabled={playing}><Play size={14} /> Play test</button>}>
            <p className="small text-2">
              Built on {when(meta?.created_at)}{meta?.filename ? ` from ${meta.filename}` : ""}
              {meta?.speech_s ? `, ${Math.round(meta.speech_s)} seconds of talking` : ""}.
              {profile.consent_at ? ` Consent given on ${when(profile.consent_at)}.` : ""}
            </p>
            {testMeta && <div className="row" style={{ marginTop: 10 }}><VoiceBadge meta={testMeta} /><span className="tiny muted">{fallbackNote(testMeta)}</span></div>}
            <div className="row wrap" style={{ marginTop: 14 }}>
              {!showWizard && <button type="button" className="btn" onClick={() => setShowWizard(true)}><RotateCcw size={16} /> Build it again from other clips</button>}
              <DeleteVoiceButton onDeleted={() => { reloadProfile(); reloadHealth(); setTestMeta(null); setShowWizard(true); }} />
            </div>
          </Card>
        )}

        {showWizard && !built && (
          <>
            <Card title="1. Add voice notes" icon={Upload}>
              <p className="small text-2">
                Pick clips where only this person is talking, in a quiet place: 10 to 30 seconds each is best.
                WhatsApp voice notes (.opus), MP3, M4A and WAV all work.
              </p>
              <input ref={fileRef} type="file" accept="audio/*,.opus,.ogg,.oga,.mp3,.m4a,.aac,.wav" multiple hidden
                onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
              <div className="grid g2" style={{ marginTop: 14 }}>
                <button type="button" className="btn primary lg" onClick={() => fileRef.current?.click()} disabled={clips.length >= MAX_CLIPS || !!rec}>
                  <Upload size={18} /> Choose voice notes
                </button>
                {rec ? (
                  <button type="button" className="btn danger lg" onClick={stopRec}>
                    <Square size={16} /> Stop recording ({Math.floor(rec.seconds)} s)
                  </button>
                ) : (
                  <button type="button" className="btn lg" onClick={startRec} disabled={clips.length >= MAX_CLIPS}>
                    <Mic size={18} /> Record now
                  </button>
                )}
              </div>
              <p className="tiny muted" style={{ marginTop: 8 }}>
                Still able to speak? Record 20 to 30 seconds of yourself talking now, while your voice is strong. This is called voice banking.
              </p>
              {clips.length > 0 && (
                <div className="clip-list">
                  {clips.map((c) => (
                    <ClipRow key={c.id} clip={c} onRemove={() => setClips((cs) => cs.filter((x) => x.id !== c.id))} />
                  ))}
                </div>
              )}
            </Card>

            <Card title="2. Consent" icon={ShieldCheck} className="private">
              <CheckRow id="vb-consent" checked={consent} onChange={setConsent}>
                This is my own voice, or the person whose voice it is has agreed to have it rebuilt.
              </CheckRow>
              <p className="tiny muted" style={{ marginTop: 8 }}>
                The clearest clip is sent to Gnani AI once to build the voice model. The model is kept only on this device's server.
              </p>
            </Card>

            <div className="stack-sm">
              <button type="button" className="btn primary lg block" onClick={build}
                disabled={!good.length || !consent || building || busyClips}>
                {building ? <><Loader2 size={18} className="spin" /> Building your voice…</> : <><Sparkles size={18} /> Build my voice</>}
              </button>
              <p className="tiny muted center-text">
                {!clips.length ? "Add at least one voice note to begin."
                  : busyClips ? "Checking your clips…"
                  : !good.length ? "None of these clips is clear enough yet. Try another voice note."
                  : !consent ? "Tick the consent box to continue."
                  : `${good.length} good clip${good.length > 1 ? "s" : ""}. We will use the clearest one.`}
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
