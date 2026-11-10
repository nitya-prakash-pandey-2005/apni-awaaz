import { useEffect, useState } from "react";

const Q = "(min-width: 1200px)";
const now = () => typeof window !== "undefined" && !!window.matchMedia && window.matchMedia(Q).matches;

// True on desktop-width screens. Phones never render (or fetch for) the desktop side panel.
export default function useWide() {
  const [wide, setWide] = useState(now);
  useEffect(() => {
    const m = window.matchMedia(Q);
    const on = () => setWide(m.matches);
    m.addEventListener("change", on);
    return () => m.removeEventListener("change", on);
  }, []);
  return wide;
}
