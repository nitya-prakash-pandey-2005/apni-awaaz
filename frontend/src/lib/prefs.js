// Small per-device preferences (localStorage; every access is guarded because storage can be blocked).
export function load(key, fallback) {
  try {
    const v = localStorage.getItem(`awaaz-${key}`);
    return v == null ? fallback : JSON.parse(v);
  } catch { return fallback; }
}

export function save(key, value) {
  try { localStorage.setItem(`awaaz-${key}`, JSON.stringify(value)); } catch { /* storage blocked */ }
}

// Text size: "normal" | "large" (bigger phrase tiles, captions and SOS text for tired eyes).
export function getTextSize() { return load("text-size", "normal"); }
export function setTextSize(v) {
  save("text-size", v);
  document.documentElement.setAttribute("data-text", v);
}
export function applySavedTextSize() {
  document.documentElement.setAttribute("data-text", getTextSize());
}
