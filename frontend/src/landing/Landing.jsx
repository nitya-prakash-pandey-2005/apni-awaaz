import { useEffect, useRef } from "react";
import { ArrowRight, Check, Github, PlayCircle, ShieldCheck } from "lucide-react";
import { REPO } from "../lib/demo";
import { reducedMotion } from "../motion/prefs";
import { startLanding } from "./animate";
import {
  APP_ENTRY, COMPARE, DADI_URL, FACTS, FEATURES, PIPE_BUILD, PIPE_TALK, PUKAAR_URL, RESULTS, STORIES, VIDEO_URL,
} from "./content";

const BARS = [[130, 130.5, 94.9], [183, 118.7, 149.5], [236, 164.2, 161.9], [289, 118.7, 149.5], [342, 130.5, 94.9]];

export function Logo({ size = 40, live = false }) {
  return (
    <svg className={`lp-logo ${live ? "live" : ""}`} width={size} height={size} viewBox="0 0 512 512" aria-hidden="true">
      <defs>
        <linearGradient id="lp-g" gradientUnits="userSpaceOnUse" x1="48" y1="48" x2="464" y2="468">
          <stop offset="0" stopColor="#FF8A5B" /><stop offset=".5" stopColor="#F43F7A" /><stop offset="1" stopColor="#8B5CF6" />
        </linearGradient>
      </defs>
      <g fill="url(#lp-g)" stroke="url(#lp-g)">
        <rect x="48" y="52" width="416" height="340" rx="136" />
        <path d="M132 318 L94 462 L262 372 Z" strokeLinejoin="round" strokeWidth="28" />
      </g>
      <g fill="#FFF7F3">
        {BARS.map(([x, y, h]) => <rect key={x} className="lp-bar" x={x} y={y} width="40" height={h} rx="20" />)}
      </g>
    </svg>
  );
}

function Phone({ img, alt, eager = false }) {
  return (
    <div className="lp-phone">
      <div className="lp-phone-screen">
        <img src={`/landing/${img}.webp`} alt={alt} width="390" height="844"
          loading={eager ? "eager" : "lazy"} decoding="async" fetchpriority={eager ? "high" : "auto"} />
      </div>
    </div>
  );
}

function Count({ value, decimals = 0, format, suffix = "" }) {
  const shown = format === "in" ? value.toLocaleString("en-IN") : value.toFixed(decimals);
  return (
    <span className="lp-count" data-count={value} data-decimals={decimals} data-format={format || ""}>
      <span className="lp-count-v">{shown}</span>{suffix && <small className="lp-count-s">{suffix}</small>}
    </span>
  );
}

function Pipeline({ steps, label, id }) {
  return (
    <figure className="lp-pipe" data-pipe aria-label={label}>
      <figcaption className="lp-pipe-cap">{label}</figcaption>
      <div className="lp-pipe-track" style={{ "--n": steps.length }}>
        <svg className="lp-pipe-svg h" viewBox="0 0 1000 4" preserveAspectRatio="none" aria-hidden="true">
          <defs><linearGradient id={`${id}-h`} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1000" y2="0"><stop offset="0" stopColor="#FF8A5B" /><stop offset=".5" stopColor="#F43F7A" /><stop offset="1" stopColor="#8B5CF6" /></linearGradient></defs>
          <path className="lp-pipe-line" d="M0 2 H1000" stroke={`url(#${id}-h)`} vectorEffect="non-scaling-stroke" />
          <path className="lp-pipe-pulse" d="M0 2 H1000" pathLength="100" vectorEffect="non-scaling-stroke" />
        </svg>
        <svg className="lp-pipe-svg v" viewBox="0 0 4 1000" preserveAspectRatio="none" aria-hidden="true">
          <defs><linearGradient id={`${id}-v`} gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="0" y2="1000"><stop offset="0" stopColor="#FF8A5B" /><stop offset=".5" stopColor="#F43F7A" /><stop offset="1" stopColor="#8B5CF6" /></linearGradient></defs>
          <path className="lp-pipe-line" d="M2 0 V1000" stroke={`url(#${id}-v)`} vectorEffect="non-scaling-stroke" />
          <path className="lp-pipe-pulse" d="M2 0 V1000" pathLength="100" vectorEffect="non-scaling-stroke" />
        </svg>
        <ol className="lp-pipe-steps">
          {steps.map((s, i) => (
            <li key={s.t} className={`lp-node ${s.gnani ? "gnani" : ""} ${s.end ? "end" : ""}`}>
              <span className="lp-node-dot">{s.end ? <Logo size={26} /> : i + 1}</span>
              <span className="lp-node-t">{s.t}</span>
              <span className="lp-node-s">{s.s}</span>
            </li>
          ))}
        </ol>
      </div>
    </figure>
  );
}

export default function Landing() {
  const root = useRef(null);
  useEffect(() => {
    const prev = document.title;
    document.title = "Apni Awaaz: your own voice, back";
    document.documentElement.classList.add("lp-page");
    const stop = reducedMotion() ? () => {} : startLanding(root.current);
    return () => { stop(); document.title = prev; document.documentElement.classList.remove("lp-page"); };
  }, []);

  const motion = !reducedMotion();
  return (
    <div className={`lp ${motion ? "motion" : ""}`} ref={root}>
      <a className="lp-skip" href={APP_ENTRY}>Skip to the app</a>
      <header className="lp-nav">
        <a className="lp-brand" href="#/" aria-label="Apni Awaaz home"><Logo size={34} /><span>Apni Awaaz</span></a>
        <nav className="lp-links" aria-label="Sections">
          <a href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("lp-features")?.scrollIntoView({ behavior: motion ? "smooth" : "auto" }); }}>Features</a>
          <a href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("lp-how")?.scrollIntoView({ behavior: motion ? "smooth" : "auto" }); }}>How it works</a>
          <a href="#/" onClick={(e) => { e.preventDefault(); document.getElementById("lp-results")?.scrollIntoView({ behavior: motion ? "smooth" : "auto" }); }}>Results</a>
        </nav>
        <a className="lp-btn sm" href={APP_ENTRY}>Try it <ArrowRight size={16} /></a>
      </header>

      <main>
        <section className="lp-hero">
          <div className="lp-aura" aria-hidden="true"><i className="a1" /><i className="a2" /><i className="a3" /></div>
          <div className="lp-hero-copy">
            <div className="lp-hero-mark"><Logo size={72} live /></div>
            <p className="lp-kicker"><span lang="hi">अपनी आवाज़</span> · Built on Gnani AI</p>
            <h1 className="lp-h1" aria-label="Your own voice, back.">
              {["Your", "own", "voice,", "back."].map((w, i) => <span key={w} className={`lp-w ${i === 3 ? "grad" : ""}`} aria-hidden="true">{w} </span>)}
            </h1>
            <p className="lp-sub" data-hero>
              For people who lost their voice to oral or throat cancer, stroke or ALS. Apni Awaaz rebuilds <em>your own voice</em> from
              old WhatsApp voice notes, so you can speak again, in 10 Indian languages.
            </p>
            <div className="lp-ctas" data-hero>
              <a className="lp-btn" href={APP_ENTRY}>Try the live demo <ArrowRight size={18} /></a>
              <a className="lp-btn ghost" href={VIDEO_URL} target="_blank" rel="noreferrer"><PlayCircle size={18} /> Watch the 3-minute video</a>
            </div>
            <ul className="lp-chips" data-hero>
              <li>10 Indian languages</li><li>From old voice notes</li><li>SOS works offline</li><li>Free</li>
            </ul>
          </div>
          <div className="lp-hero-phone">
            <div className="lp-float"><Phone img="speak-hindi" alt="The Speak screen of Apni Awaaz with a Hindi sentence ready to be spoken" eager /></div>
            <div className="lp-bubble b1" aria-hidden="true"><span lang="hi">मुझे पानी चाहिए</span><small>in your voice</small></div>
            <div className="lp-bubble b2" aria-hidden="true"><b>0.67 s</b><small>to build your voice</small></div>
          </div>
        </section>

        <section className="lp-band" aria-labelledby="lp-problem">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>The problem</p>
            <h2 id="lp-problem" className="lp-h2" data-reveal>Losing your voice should not mean losing <span className="grad">yourself</span>.</h2>
            <div className="lp-facts">
              {FACTS.map((f) => (
                <article key={f.label} className="lp-fact" data-reveal>
                  <div className="lp-fact-n"><Count {...f} /></div>
                  <p className="lp-fact-l">{f.label}</p>
                  <p className="lp-fact-note">{f.note}</p>
                  <a className="lp-src" href={f.href} target="_blank" rel="noreferrer">{f.src}</a>
                </article>
              ))}
            </div>
            <div className="lp-stories">
              {STORIES.map((s) => (
                <figure key={s.name} className="lp-story" data-reveal>
                  {s.quote && <blockquote>&ldquo;{s.quote}&rdquo;</blockquote>}
                  <p>{s.text}</p>
                  <figcaption><b>{s.name}</b> · <a href={s.href} target="_blank" rel="noreferrer">{s.src}</a></figcaption>
                </figure>
              ))}
            </div>
            <p className="lp-bridge" data-reveal>Today people get an electrolarynx&rsquo;s buzz, a notebook, or an app that speaks in a stranger&rsquo;s voice. Apni Awaaz gives back the one they already had.</p>
          </div>
        </section>

        <section id="lp-features" className="lp-features" aria-label="Features">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>What it does</p>
            <h2 className="lp-h2" data-reveal>Built for the hospital bed, the kitchen and the ward round.</h2>
            {FEATURES.map((f, i) => (
              <article key={f.img} className={`lp-feature ${i % 2 ? "flip" : ""}`}>
                <div className="lp-feature-media" data-reveal="media"><Phone img={f.img} alt={`${f.kicker} screen`} /></div>
                <div className="lp-feature-copy" data-reveal>
                  <p className="lp-eyebrow">{f.kicker}</p>
                  <h3 className="lp-h3">{f.title}</h3>
                  <p className="lp-p">{f.text}</p>
                  {f.points && <ul className="lp-points">{f.points.map((p) => <li key={p}><Check size={16} /> {p}</li>)}</ul>}
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="lp-how" className="lp-how" aria-labelledby="lp-how-h">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>How it works</p>
            <h2 id="lp-how-h" className="lp-h2" data-reveal>Old voice notes in. <span className="grad">Your voice</span> out.</h2>
            <Pipeline id="pb" label="Building your voice" steps={PIPE_BUILD} />
            <Pipeline id="pt" label="Converse" steps={PIPE_TALK} />
          </div>
        </section>

        <section id="lp-results" className="lp-results" aria-labelledby="lp-results-h">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>Measured, not promised</p>
            <h2 id="lp-results-h" className="lp-h2" data-reveal>Real runs on Gnani&rsquo;s live APIs.</h2>
            <div className="lp-metrics">
              {RESULTS.map((r) => (
                <div key={r.label} className="lp-metric" data-reveal>
                  <div className="lp-metric-n"><Count {...r} /></div>
                  <p className="lp-metric-l">{r.label}</p>
                  <p className="lp-metric-note">{r.note}</p>
                </div>
              ))}
            </div>
            <p className="lp-fine" data-reveal>Synthetic voices, recorded 8 and 10 Nov 2026. Full log in the repository&rsquo;s docs/test-log.md.</p>
          </div>
        </section>

        <section className="lp-compare" aria-labelledby="lp-compare-h">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>An honest comparison</p>
            <h2 id="lp-compare-h" className="lp-h2" data-reveal>Good tools exist. None is built for India&rsquo;s bedside.</h2>
            <div className="lp-cmp">
              {COMPARE.map((c) => (
                <article key={c.name} className={`lp-cmp-card ${c.us ? "us" : ""}`} data-reveal>
                  <h3>{c.us && <Logo size={26} />}{c.name}</h3>
                  <ul>{c.rows.map((r) => <li key={r}>{c.us && <Check size={16} />}{r}</li>)}</ul>
                </article>
              ))}
            </div>
            <p className="lp-fine" data-reveal>Rebuilding a voice from WhatsApp notes is not new: ElevenLabs already does it. To our knowledge, as of Nov 2026, no free, India-first phone app combines your own voice from old notes, 10 Indian languages and a conversation mode with SOS.</p>
          </div>
        </section>

        <section className="lp-engine" aria-labelledby="lp-engine-h">
          <div className="lp-wrap">
            <p className="lp-eyebrow" data-reveal>One engine, three products</p>
            <h2 id="lp-engine-h" className="lp-h2" data-reveal>One Gnani voice engine. Three ways it helps.</h2>
            <div className="lp-trio">
              <a className="lp-prod" href={DADI_URL} target="_blank" rel="noreferrer" data-reveal><b>Dadi vs Scammers</b><span>An AI grandmother who wastes scammers&rsquo; time.</span></a>
              <a className="lp-prod" href={PUKAAR_URL} target="_blank" rel="noreferrer" data-reveal><b>Pukaar</b><span>An overflow emergency voice line for floods and disasters.</span></a>
              <a className="lp-prod us" href={APP_ENTRY} data-reveal><b>Apni Awaaz</b><span>Your own voice back, in 10 Indian languages.</span></a>
            </div>
          </div>
        </section>

        <section className="lp-final">
          <div className="lp-wrap center">
            <Logo size={64} live />
            <h2 className="lp-h2" data-reveal>Hear it for yourself.</h2>
            <p className="lp-p" data-reveal>The demo replays a real session recorded on Gnani&rsquo;s live servers. No sign-up.</p>
            <div className="lp-ctas center" data-reveal>
              <a className="lp-btn" href={APP_ENTRY}>Try the live demo <ArrowRight size={18} /></a>
              <a className="lp-btn ghost" href={REPO} target="_blank" rel="noreferrer"><Github size={18} /> Source on GitHub</a>
            </div>
          </div>
        </section>
      </main>

      <footer className="lp-foot">
        <div className="lp-wrap lp-foot-in">
          <div className="lp-foot-brand"><Logo size={28} /><span>Apni Awaaz</span></div>
          <p>Team: <b>Nitya Prakash Pandey</b> · <b>Dilavesh Kanz Nidooli</b></p>
          <p>Built on Gnani AI: voice cloning (vachana-vc-v1) · Timbre v3.0 · Prisma v3.0</p>
          <p className="lp-synth"><ShieldCheck size={15} /> The demo voice is synthetic. No real person&rsquo;s voice is used.</p>
        </div>
      </footer>
    </div>
  );
}
