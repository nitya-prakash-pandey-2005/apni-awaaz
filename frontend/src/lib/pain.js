// "Where does it hurt?" sentence builder. Same templates and rules as backend/awaaz/pain.py (one shared JSON),
// so the static demo builds exactly the sentence the server would.
import T from "@data/pain.json";

export const PAIN = T;
export const templateLang = (lang) => (T.langs[lang] ? lang : "en-IN");
export const partOf = (id) => T.parts.find((p) => p.id === id);

export function painSentence({ part, side = null, level, type, since = "", lang = "hi-IN" }) {
  const p = partOf(part);
  if (!p) throw new Error(`unknown body part ${part}`);
  if (!T.types.includes(type) || !T.since.includes(since) || !(level >= 0 && level <= 10)) throw new Error("invalid pain details");
  if (p.sided !== (side === "left" || side === "right")) throw new Error(p.sided ? `${part} needs a side` : `${part} has no side`);
  const tl = templateLang(lang);
  const L = T.langs[tl];
  const f = { type: L.types[type], since: L.since[since], level: L.numbers[level] };
  if (tl === "hi-IN") Object.assign(f, { my: L.my[p.hi.g], part: p.hi.noun, side: side ? L.side[side][p.hi.g] : "" });
  else Object.assign(f, { part: tl === "ta-IN" ? p.ta : p.en, side: side ? L.side[side] : "" });
  return L.template.replace(/\{(\w+)\}/g, (_, k) => f[k]);
}

// English label for a part and side, e.g. "Left arm"
export const partLabel = (part, side) => {
  const en = partOf(part)?.en || part;
  const s = side ? `${side} ${en}` : en;
  return s[0].toUpperCase() + s.slice(1);
};
