// Single-switch scanning: the highlight steps through the items; Space / Enter (what most assistive switches send) picks one.
import { useCallback, useEffect, useRef, useState } from "react";

export function useScan({ count, active, intervalMs = 1500, onSelect }) {
  const [idx, setIdx] = useState(0);
  const ref = useRef({ idx: 0, onSelect });
  ref.current.onSelect = onSelect;
  useEffect(() => { ref.current.idx = idx; }, [idx]);
  useEffect(() => {
    if (!active || !count) return undefined;
    setIdx(0);
    const t = setInterval(() => setIdx((i) => (i + 1) % count), intervalMs);
    return () => clearInterval(t);
  }, [active, count, intervalMs]);
  const select = useCallback(() => ref.current.onSelect?.(ref.current.idx), []);
  useEffect(() => {
    if (!active) return undefined;
    const onKey = (e) => {
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target?.tagName)) return; // typing, not a switch press
      if (e.key === " " || e.key === "Enter") { e.preventDefault(); select(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, select]);
  useEffect(() => {
    if (active) document.querySelector(".scan-on")?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [active, idx]);
  return { idx: active ? idx : -1, select };
}
