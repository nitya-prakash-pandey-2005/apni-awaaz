// Word and phrase prediction: a line-for-line mirror of backend/awaaz/predict.py (same lexicon JSON),
// used by the static demo so suggestions work with no server.
import LEX from "@data/lexicon.json";

const PERSONAL_BASE = 3, PERSONAL_PER_USE = 2, LEXICON_WEIGHT = 1;
const TRIM = /[\s।.!?,]+$/u;
const trim = (s) => s.trim().replace(TRIM, "");
export const words = (text) => trim(text.toLowerCase()).split(/\s+/).filter(Boolean);

export function corpus(lang, history = []) {
  const seen = new Set(), out = [];
  for (const [text, uses] of history) {
    const t = trim(text);
    if (t && !seen.has(t.toLowerCase())) { seen.add(t.toLowerCase()); out.push([t, PERSONAL_BASE + PERSONAL_PER_USE * Math.max(0, uses | 0)]); }
  }
  for (const t of LEX[lang] || LEX["en-IN"]) if (!seen.has(t.toLowerCase())) { seen.add(t.toLowerCase()); out.push([t, LEXICON_WEIGHT]); }
  return out;
}

const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);

export function predict(text, lang = "hi-IN", history = [], k = 5) {
  const raw = text.split(/\s+/).filter(Boolean);
  const atWordStart = !text || /\s$/u.test(text);
  const typed = words(text);
  const prefix = atWordStart || !typed.length ? "" : typed[typed.length - 1];
  const done = atWordStart ? typed : typed.slice(0, -1);
  const keep = atWordStart ? raw : raw.slice(0, -1);
  const phrases = corpus(lang, history);
  const found = new Map();
  const add = (score, order, out, label, kind) => {
    const key = out.trim().toLowerCase();
    if (key === text.trim().toLowerCase() || (found.has(key) && found.get(key)[0] >= score)) return;
    found.set(key, [score, order, { text: out, label, kind }]);
  };

  phrases.forEach(([p, weight], i) => {
    const pw = words(p);
    for (let j = Math.min(done.length, pw.length - 1); j >= 0; j--) {
      if (same(pw.slice(0, j), done.slice(done.length - j)) && pw[j].startsWith(prefix) && (j || prefix || !done.length)) {
        add(weight * (1 + j) * 10, i, [...keep.slice(0, keep.length - j), p].join(" "), p, "phrase");
        break;
      }
    }
  });

  const uni = new Map(), bi = new Map(), shown = new Map();
  for (const [p, weight] of phrases) {
    const orig = trim(p).split(/\s+/).filter(Boolean);
    const pw = ["<s>", ...words(p)];
    for (let n = 0; n < pw.length - 1 && n < orig.length; n++) {
      const key = `${pw[n]}\u0000${pw[n + 1]}`;
      bi.set(key, (bi.get(key) || 0) + weight);
      uni.set(pw[n + 1], (uni.get(pw[n + 1]) || 0) + weight);
      if (!shown.has(pw[n + 1])) shown.set(pw[n + 1], orig[n]);
    }
  }
  const prev = done.length ? done[done.length - 1] : "<s>";
  const big = (w) => bi.get(`${prev}\u0000${w}`) || 0;
  const cands = [...uni.keys()].filter((w) => w.startsWith(prefix) && w !== prefix);
  const follows = cands.filter((w) => big(w));
  (follows.length ? follows : prefix ? cands : []).forEach((w, i) => {
    add(3 * big(w) + uni.get(w), phrases.length + i, [...keep, shown.get(w)].join(" ") + " ", shown.get(w), "word");
  });

  const ranked = [...found.values()].sort((a, b) => b[0] - a[0] || a[1] - b[1]).map((t) => t[2]);
  const ph = ranked.filter((d) => d.kind === "phrase").slice(0, 3);
  return [...ph, ...ranked.filter((d) => d.kind === "word")].slice(0, k);
}

export const keystrokesSaved = (pressed, text) => {
  const n = text.length;
  return n ? Math.max(0, Math.round(100 * (1 - pressed / n))) : 0;
};
