// Dwell selection for head pointers and eye-gaze software that move the cursor: hold the pointer still on a
// button and it is pressed after the dwell time. Pure timing logic here (unit-tested); the DOM layer is DwellLayer.jsx.
export const DWELL_MIN = 0.6, DWELL_MAX = 2.0;
export const DWELL_SELECTOR = "button:not(:disabled), a[href], [role=button], .dwell-target, input[type=checkbox]";
export const IDLE = Object.freeze({ target: null, start: 0, fired: false });
export const clampDwell = (s) => Math.min(DWELL_MAX, Math.max(DWELL_MIN, Number(s) || 1));

/**
 * One step of the dwell clock.
 * state: { target, start, fired }; input: { target, now (ms), scrolling }; dwellMs: time to hold.
 * Returns { state, progress (0..1), fire }. Moving to another target restarts the clock; after firing, the
 * pointer must leave the target before it can fire again; scrolling cancels and never fires.
 */
export function dwellStep(state, { target, now, scrolling = false }, dwellMs) {
  if (scrolling || !target) return { state: IDLE, progress: 0, fire: false };
  if (target !== state.target) return { state: { target, start: now, fired: false }, progress: 0, fire: false };
  if (state.fired) return { state, progress: 0, fire: false };
  const progress = Math.min(1, Math.max(0, (now - state.start) / dwellMs));
  return progress >= 1 ? { state: { ...state, fired: true }, progress: 1, fire: true } : { state, progress, fire: false };
}

// Reduced motion: the ring fills in four steps instead of a smooth sweep.
export const shownProgress = (p, reduced) => (reduced ? Math.floor(p * 4) / 4 : p);

const KEY = "awaaz.dwell";
export function loadDwell() {
  try {
    const v = JSON.parse(localStorage.getItem(KEY) || "{}");
    return { on: !!v.on, seconds: clampDwell(v.seconds ?? 1) };
  } catch {
    return { on: false, seconds: 1 };
  }
}
export function saveDwell(v) {
  const out = { on: !!v.on, seconds: clampDwell(v.seconds) };
  try { localStorage.setItem(KEY, JSON.stringify(out)); } catch { /* private mode: lasts this visit */ }
  window.dispatchEvent(new CustomEvent("awaaz:dwell", { detail: out }));
  return out;
}
