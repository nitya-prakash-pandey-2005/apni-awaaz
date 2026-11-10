// Visit notes: pure helpers (no React) for the Converse "Visit notes" card. Unit-tested in visit.test.js.

export const WHEN_EN = {
  morning: "morning", afternoon: "afternoon", evening: "evening", night: "night", empty_stomach: "empty stomach",
  before_food: "before food", after_food: "after food", once_daily: "once a day", twice_daily: "twice a day",
  thrice_daily: "three times a day", as_needed: "only when needed",
};

// Converse lines ({ who: "them" | "me", text, t? }) -> the turns POST /api/visit/summary takes.
export function turnsFromLines(lines) {
  return (lines || [])
    .filter((l) => l && typeof l.text === "string" && l.text.trim())
    .map((l) => ({ speaker: l.who === "me" ? "user" : "partner", text: l.text.trim(), ...(typeof l.t === "number" ? { t: l.t } : {}) }))
    .slice(-200);
}

export const canSummarise = (lines) => turnsFromLines(lines).some((t) => t.speaker === "partner");

export function medLine(m) {
  const bits = [m.name, m.dose, (m.when || []).map((w) => WHEN_EN[w] || w).join(", "), m.days ? `${m.days} days` : ""];
  return bits.filter(Boolean).join(" · ");
}

// The WhatsApp / SMS text: the read-back text in the person's language, then the AI-notes caution. Kept short for SMS.
export function shareText(resp, name = "") {
  if (!resp?.text) return "";
  const who = name ? ` (${name})` : "";
  return `Visit notes${who}\n${resp.text.local}\n\n${resp.disclaimer}`;
}

// The downloadable notes: Markdown with the structured sections in English and the read-back text as made.
export function visitMarkdown(resp, when = new Date()) {
  if (!resp?.summary) return "";
  const s = resp.summary;
  const out = [`# Visit notes, ${when.toISOString().slice(0, 10)}`, "", `> ${resp.disclaimer}`, ""];
  out.push("## Medicines", "");
  if (s.medicines.length) {
    out.push("| Medicine | Dose | When | Days |", "|---|---|---|---|");
    for (const m of s.medicines) out.push(`| ${m.name} | ${m.dose || "-"} | ${(m.when || []).map((w) => WHEN_EN[w] || w).join(", ") || "-"} | ${m.days ?? "-"} |`);
  } else out.push("None noted.");
  const list = (title, items) => {
    out.push("", `## ${title}`, "");
    if (!items?.length) out.push("None noted.");
    for (const x of items || []) out.push(`- ${x.en}${x.hi && x.hi !== x.en ? ` (${x.hi})` : ""}`);
  };
  list("Tests", s.tests);
  list("Next visit", s.next_visit ? [s.next_visit] : []);
  list("Watch for", s.warning_signs);
  list("Advice", s.advice);
  list("I asked", s.questions_asked);
  out.push("", "## Read-back text", "", resp.text.local, "");
  if (resp.text.en !== resp.text.local) out.push("## In English", "", resp.text.en, "");
  out.push(`_Made by Apni Awaaz (${resp.source === "llm" ? "AI summary, checked against the transcript" : "keyword notes, no AI"})._`, "");
  return out.join("\n");
}
