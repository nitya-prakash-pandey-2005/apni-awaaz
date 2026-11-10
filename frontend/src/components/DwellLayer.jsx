// Dwell selection: while on, holding a mouse / head pointer / eye-gaze cursor still on a button, phrase, chip or body
// region fills a ring and then presses it. Touch is ignored (a tap already works); scrolling cancels.
import { useEffect, useRef, useState } from "react";
import { DWELL_SELECTOR, IDLE, dwellStep, loadDwell, shownProgress } from "../lib/dwell";

const NOT_HERE = "textarea, select, input:not([type=checkbox]), .no-dwell";

export default function DwellLayer() {
  const [cfg, setCfg] = useState(loadDwell);
  const [ring, setRing] = useState(null); // { x, y, p }
  const st = useRef({ state: IDLE, x: 0, y: 0, has: false, scrollUntil: 0, el: null, p: -1 });

  useEffect(() => {
    const on = (e) => setCfg(e.detail);
    window.addEventListener("awaaz:dwell", on);
    return () => window.removeEventListener("awaaz:dwell", on);
  }, []);

  useEffect(() => {
    if (!cfg.on) { setRing(null); return undefined; }
    const s = st.current;
    const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    const move = (e) => { if (e.pointerType === "touch") { s.has = false; return; } s.x = e.clientX; s.y = e.clientY; s.has = true; };
    const leave = () => { s.has = false; };
    const scrolled = () => { s.scrollUntil = performance.now() + 400; };
    window.addEventListener("pointermove", move, { passive: true });
    document.documentElement.addEventListener("pointerleave", leave);
    window.addEventListener("blur", leave);
    window.addEventListener("scroll", scrolled, { passive: true, capture: true });
    window.addEventListener("wheel", scrolled, { passive: true });
    let raf = 0;
    const tick = () => {
      const now = performance.now();
      const hit = s.has ? document.elementFromPoint(s.x, s.y) : null;
      const el = hit && !hit.closest(NOT_HERE) ? hit.closest(DWELL_SELECTOR) : null;
      const r = dwellStep(s.state, { target: el, now, scrolling: now < s.scrollUntil }, cfg.seconds * 1000);
      s.state = r.state;
      if (s.el !== el) { s.el?.classList.remove("dwell-on"); el?.classList.add("dwell-on"); s.el = el; }
      if (r.fire && el) el.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true, view: window }));
      const p = el && r.progress > 0 && !r.state.fired ? shownProgress(r.progress, reduced) : -1;
      if (p !== s.p) { s.p = p; setRing(p >= 0 ? { x: s.x, y: s.y, p } : null); }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      s.el?.classList.remove("dwell-on");
      Object.assign(s, { el: null, state: IDLE, p: -1 });
      setRing(null);
      window.removeEventListener("pointermove", move);
      document.documentElement.removeEventListener("pointerleave", leave);
      window.removeEventListener("blur", leave);
      window.removeEventListener("scroll", scrolled, { capture: true });
      window.removeEventListener("wheel", scrolled);
    };
  }, [cfg.on, cfg.seconds]);

  if (!ring) return null;
  return <div className="dwell-ring" aria-hidden="true" style={{ left: ring.x, top: ring.y, "--p": ring.p }} />;
}
