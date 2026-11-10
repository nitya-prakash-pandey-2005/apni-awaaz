import { test } from "node:test";
import assert from "node:assert/strict";
import { canSummarise, medLine, shareText, turnsFromLines, visitMarkdown } from "./visit.js";

const RESP = {
  source: "llm", lang: "hi-IN", text_lang: "hi-IN", disclaimer: "ये नोट्स AI ने बातचीत से बनाए हैं। अपने डॉक्टर से ज़रूर पूछ लें।",
  text: { local: "मेरे विज़िट नोट्स।\nदवाइयाँ: Pantoprazole 40 mg सुबह खाली पेट 14 दिन तक।", en: "My visit notes.\nMedicines: Pantoprazole 40 mg." },
  summary: { medicines: [{ name: "Pantoprazole", dose: "40 mg", when: ["morning", "empty_stomach"], days: 14 }],
    tests: [{ en: "Blood test", hi: "ब्लड टेस्ट" }], next_visit: null, warning_signs: [], advice: [], questions_asked: [] },
};

test("turnsFromLines maps who to speaker and drops empty lines", () => {
  const t = turnsFromLines([{ who: "them", text: " Pantoprazole 40 mg ", t: 1.5 }, { who: "me", text: "" }, { who: "me", text: "Kya?" }]);
  assert.deepEqual(t, [{ speaker: "partner", text: "Pantoprazole 40 mg", t: 1.5 }, { speaker: "user", text: "Kya?" }]);
  assert.equal(canSummarise([{ who: "me", text: "hello" }]), false);
  assert.equal(canSummarise([{ who: "them", text: "hello" }]), true);
});

test("medLine keeps the dose exactly", () => {
  assert.equal(medLine(RESP.summary.medicines[0]), "Pantoprazole · 40 mg · morning, empty stomach · 14 days");
});

test("shareText carries the read-back text and the caution", () => {
  const s = shareText(RESP, "Asha");
  assert.ok(s.startsWith("Visit notes (Asha)\n") && s.includes("40 mg") && s.endsWith(RESP.disclaimer));
  assert.equal(shareText(null), "");
});

test("visitMarkdown has a medicines table and every section", () => {
  const md = visitMarkdown(RESP, new Date("2026-11-10T12:00:00Z"));
  assert.ok(md.startsWith("# Visit notes, 2026-11-10"));
  assert.ok(md.includes("| Pantoprazole | 40 mg | morning, empty stomach | 14 |"));
  for (const h of ["## Tests", "## Next visit", "## Watch for", "## Advice", "## I asked", "## In English"]) assert.ok(md.includes(h), h);
  assert.ok(md.includes("- Blood test (ब्लड टेस्ट)") && md.includes(RESP.disclaimer));
});
