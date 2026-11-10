// A small "Speaking…" pill with a moving waveform while any audio plays in the app.
// It never blocks a tap (pointer-events: none) and is hidden from screen readers (the audio itself is the message).
import { useEffect, useRef, useState } from "react";
import { animate, stagger, utils } from "animejs";
import { reducedMotion } from "./prefs";

let installed = false;
const listeners = new Set();
let playing = 0;
const emit = () => listeners.forEach((f) => f(playing > 0));

// HTMLMediaElement.play is wrapped once so every `new Audio(url).play()` in the app is noticed,
// including elements that are never added to the page.
function install() {
  if (installed || typeof HTMLMediaElement === "undefined") return;
  installed = true;
  const orig = HTMLMediaElement.prototype.play;
  HTMLMediaElement.prototype.play = function play(...args) {
    const el = this;
    if (!el.__aaTracked) {
      el.__aaTracked = true;
      let on = false;
      const start = () => { if (!on) { on = true; playing += 1; emit(); } };
      const stop = () => { if (on) { on = false; playing = Math.max(0, playing - 1); emit(); } };
      el.addEventListener("playing", start);
      ["pause", "ended", "error", "emptied"].forEach((e) => el.addEventListener(e, stop));
    }
    return orig.apply(el, args);
  };
}

export default function SpeakingWave() {
  const [on, setOn] = useState(false);
  const bars = useRef(null);
  useEffect(() => { install(); listeners.add(setOn); return () => { listeners.delete(setOn); }; }, []);
  useEffect(() => {
    if (!on || reducedMotion() || !bars.current) return undefined;
    const els = bars.current.querySelectorAll("i");
    const a = animate(els, {
      scaleY: () => [utils.random(25, 45) / 100, utils.random(80, 100) / 100],
      duration: () => utils.random(260, 420),
      delay: stagger(60),
      loop: true,
      alternate: true,
      ease: "inOutSine",
    });
    return () => { a.revert(); };
  }, [on]);
  return (
    <div className={`aa-speaking ${on ? "on" : ""}`} aria-hidden="true">
      <span className="aa-speaking-bars" ref={bars}>{[0, 1, 2, 3, 4, 5, 6].map((i) => <i key={i} />)}</span>
      <span>Speaking</span>
    </div>
  );
}
