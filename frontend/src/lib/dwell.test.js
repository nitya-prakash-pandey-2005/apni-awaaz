// npm test  (node --test src/lib)
import test from "node:test";
import assert from "node:assert/strict";
import { IDLE, clampDwell, dwellStep, shownProgress } from "./dwell.js";

const run = (events, ms = 1000) => {
  let s = IDLE;
  return events.map((e) => { const r = dwellStep(s, e, ms); s = r.state; return r; });
};

test("fires once after holding still for the dwell time", () => {
  const r = run([{ target: "A", now: 0 }, { target: "A", now: 500 }, { target: "A", now: 1000 }, { target: "A", now: 1500 }, { target: "A", now: 3000 }]);
  assert.deepEqual(r.map((x) => x.fire), [false, false, true, false, false]);
  assert.equal(r[1].progress, 0.5);
});

test("moving to another target restarts the clock", () => {
  const r = run([{ target: "A", now: 0 }, { target: "A", now: 900 }, { target: "B", now: 950 }, { target: "B", now: 1900 }, { target: "B", now: 1950 }]);
  assert.deepEqual(r.map((x) => x.fire), [false, false, false, false, true]);
});

test("must leave and come back to fire again", () => {
  const r = run([{ target: "A", now: 0 }, { target: "A", now: 1000 }, { target: null, now: 1100 }, { target: "A", now: 1200 }, { target: "A", now: 2200 }]);
  assert.deepEqual(r.map((x) => x.fire), [false, true, false, false, true]);
});

test("scrolling cancels and never fires", () => {
  const r = run([{ target: "A", now: 0 }, { target: "A", now: 800, scrolling: true }, { target: "A", now: 1200 }, { target: "A", now: 1700 }, { target: "A", now: 2200 }]);
  assert.deepEqual(r.map((x) => x.fire), [false, false, false, false, true]);
});

test("dwell time is clamped to 0.6-2.0 s and reduced motion steps the ring", () => {
  assert.equal(clampDwell(0.1), 0.6);
  assert.equal(clampDwell(5), 2);
  assert.equal(clampDwell("1.4"), 1.4);
  assert.equal(shownProgress(0.6, true), 0.5);
  assert.equal(shownProgress(0.6, false), 0.6);
});
