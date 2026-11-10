import { useRef, useState } from "react";
import { History, Loader2, Repeat2, Square, Volume2 } from "lucide-react";
import { Card, PageHead, toast } from "../ui";
import { LangChips, PhraseIcon, VoiceBadge } from "../components/bits";
import { speakText, useApi } from "../lib/api";
import { playBlob, primeAudio, stopAudio, usePlaying } from "../lib/audio";
import { fallbackNote } from "../lib/copy";
import { langOf } from "../lib/langs";
import { load, save } from "../lib/prefs";
import { useApp } from "../state/app";

const HISTORY_MAX = 15;

export default function Speak() {
  const { profile, reloadHealth } = useApp();
  const [text, setText] = useState("");
  const [lang, setLang] = useState(() => load("out-lang", profile?.language || "hi-IN"));
  const [busy, setBusy] = useState(null); // which button is fetching audio
  const [last, setLast] = useState(null);
  const [history, setHistory] = useState(() => load("history", []));
  const { data: phrases, reload: reloadPhrases } = useApi(`/api/phrases?lang=${lang}`);
  const playing = usePlaying();
  const req = useRef(0);

  const changeLang = (code) => { setLang(code); save("out-lang", code); };

  const say = async (raw, key, sayLang = lang, { clear } = {}) => {
    const t = raw.trim();
    if (!t) return;
    primeAudio();
    const my = ++req.current;
    setBusy(key);
    try {
      const { blob, meta } = await speakText(t, sayLang);
      if (my !== req.current) return; // a newer tap won
      const item = { typed: t, spoken: meta.spokenText || t, lang: sayLang, voice: meta.voice, voiceName: meta.voiceName, at: Date.now() };
      setLast({ ...item, meta });
      setHistory((h) => {
        const next = [item, ...h.filter((x) => !(x.spoken === item.spoken && x.lang === item.lang))].slice(0, HISTORY_MAX);
        save("history", next);
        return next;
      });
      if (clear) setText("");
      if (meta.voice === "fallback" && meta.reason !== "no_voice") reloadHealth();
      setBusy(null);
      await playBlob(blob);
      reloadPhrases();
    } catch (e) {
      if (my === req.current) setBusy(null);
      toast(e.message, "warn");
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      say(text, "compose", lang, { clear: true });
    }
  };

  const L = langOf(lang);
  const tiles = phrases?.lang === lang ? phrases.quick : [];
  const frequent = phrases?.lang === lang ? phrases.frequent : [];

  return (
    <div>
      <PageHead kicker="Speak" title="What would you like to say?"
        sub={profile?.name ? `Type it, or tap a phrase, ${profile.name}. It is spoken out loud.` : "Type it, or tap a phrase. It is spoken out loud."} />
      <div className="speak-layout">
        <Card className="compose area-compose">
          <label className="sr-only" htmlFor="say-text">Type what you want to say</label>
          <textarea id="say-text" className="textarea say-box" rows={3} maxLength={500} value={text}
            onChange={(e) => setText(e.target.value)} onKeyDown={onKey}
            placeholder="Type in any script. For example: mujhe paani chahiye" />
          <div className="row between wrap" style={{ marginTop: 8, rowGap: 6 }}>
            <span className="tiny muted">Hindi in English letters works too. Press Enter to speak.</span>
            <span className="tiny muted mono">{text.length}/500</span>
          </div>
          <div className="hud" style={{ margin: "14px 0 8px" }}>Speak in</div>
          <LangChips value={lang} onChange={changeLang} label="Speak in" />
          <div className="row" style={{ marginTop: 14 }}>
            <button type="button" className="btn primary lg grow speak-btn" disabled={!text.trim() || busy === "compose"}
              onClick={() => say(text, "compose", lang, { clear: true })}>
              {busy === "compose" ? <><Loader2 size={20} className="spin" /> Getting your voice…</> : <><Volume2 size={20} /> Speak</>}
            </button>
            {playing && (
              <button type="button" className="btn lg danger" onClick={stopAudio} aria-label="Stop speaking"><Square size={18} /> Stop</button>
            )}
          </div>
          {last && (
            <div className="last-said">
              <div className="row between wrap" style={{ rowGap: 6 }}>
                <span className="hud">Just said · {langOf(last.lang).native}</span>
                <VoiceBadge meta={last.meta} />
              </div>
              <p className="said" lang={last.lang}>{last.spoken}</p>
              {last.meta.translated && <p className="tiny muted">You typed: {last.typed}</p>}
              {last.meta.voice === "fallback" && <p className="tiny muted" style={{ marginTop: 4 }}>{fallbackNote(last.meta)}</p>}
              <button type="button" className="btn sm" style={{ marginTop: 10 }} disabled={busy === "again"}
                onClick={() => say(last.typed, "again", last.lang)}>
                <Repeat2 size={15} /> Say it again
              </button>
            </div>
          )}
        </Card>

        <Card title="Quick phrases" className="area-phrases" right={<span className="tiny muted">{L.native}</span>}>
          {frequent.length > 0 && (
            <>
              <div className="hud" style={{ marginBottom: 8 }}>Often said</div>
              <div className="chips" style={{ marginBottom: 14 }}>
                {frequent.map((f) => (
                  <button key={f} type="button" className="chip big-chip" lang={lang} onClick={() => say(f, `f:${f}`)} disabled={busy === `f:${f}`}>{f}</button>
                ))}
              </div>
            </>
          )}
          <div className="phrase-grid">
            {tiles.length ? tiles.map((t) => (
              <button key={t.key} type="button" className={`phrase-tile ${busy === t.key ? "busy" : ""}`} onClick={() => say(t.text, t.key)}>
                <span className="ic">{busy === t.key ? <Loader2 size={20} className="spin" /> : <PhraseIcon name={t.icon} />}</span>
                <span className="txt" lang={lang}>{t.text}</span>
                {lang !== "en-IN" && <span className="gloss">{t.gloss}</span>}
              </button>
            )) : Array.from({ length: 12 }, (_, i) => <div key={i} className="phrase-tile skeleton" aria-hidden="true" />)}
          </div>
        </Card>

        <Card title="Recently said" icon={History} className="area-history">
          {history.length ? (
            <div className="list">
              {history.map((h, i) => (
                <div key={`${h.at}-${i}`} className="li">
                  <span className="grow">
                    <div className="t wrap-text" lang={h.lang}>{h.spoken}</div>
                    <div className="s">{langOf(h.lang).native} · {h.voice === "clone" ? "my voice" : `fallback voice${h.voiceName ? `: ${h.voiceName}` : ""}`}</div>
                  </span>
                  <button type="button" className="btn icon sm" aria-label="Say it again" disabled={busy === `h${i}`}
                    onClick={() => say(h.typed, `h${i}`, h.lang)}>
                    {busy === `h${i}` ? <Loader2 size={15} className="spin" /> : <Volume2 size={15} />}
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">What you say appears here, so you can say it again with one tap.</div>
          )}
        </Card>
      </div>
    </div>
  );
}
