// A real waveform for a recording, with a live progress cursor (wavesurfer.js v7, BSD-3, loaded only when shown).
import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { reducedMotion } from "../motion/prefs";

export default function Wave({ url, label, height = 44, compact = false }) {
  const box = useRef(null);
  const ws = useRef(null);
  const [state, setState] = useState({ ready: false, playing: false, failed: false, t: 0, d: 0 });

  useEffect(() => {
    let alive = true;
    let inst;
    import("wavesurfer.js").then(({ default: WaveSurfer }) => {
      if (!alive || !box.current) return;
      inst = WaveSurfer.create({
        container: box.current, url, height, barWidth: 3, barGap: 2, barRadius: 3, cursorWidth: 2,
        waveColor: "rgba(183, 189, 216, 0.38)", progressColor: "#ff6f9c", cursorColor: "#ffb199",
        normalize: true, dragToSeek: true, interact: true,
      });
      ws.current = inst;
      inst.on("ready", (d) => alive && setState((s) => ({ ...s, ready: true, d })));
      inst.on("play", () => alive && setState((s) => ({ ...s, playing: true })));
      inst.on("pause", () => alive && setState((s) => ({ ...s, playing: false })));
      inst.on("finish", () => alive && setState((s) => ({ ...s, playing: false })));
      inst.on("timeupdate", (t) => alive && setState((s) => ({ ...s, t })));
      inst.on("error", () => alive && setState((s) => ({ ...s, failed: true })));
    }).catch(() => alive && setState((s) => ({ ...s, failed: true })));
    return () => { alive = false; try { inst?.destroy(); } catch { /* already gone */ } };
  }, [url, height]);

  const toggle = () => ws.current?.playPause();
  const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
  return (
    <div className={`aa-wave ${compact ? "compact" : ""} ${state.playing ? "playing" : ""}`}>
      <button className="btn icon aa-wave-btn" onClick={toggle} disabled={!state.ready} aria-label={`${state.playing ? "Pause" : "Play"} ${label}`}>
        {state.playing ? <Pause size={18} /> : <Play size={18} />}
      </button>
      <div className="aa-wave-body">
        <div className="aa-wave-stage" style={{ height }}>
          <div ref={box} className="aa-wave-canvas" aria-hidden="true" />
          {!state.ready && !state.failed && <div className={`aa-wave-skel ${reducedMotion() ? "" : "shimmer"}`} aria-hidden="true" />}
        </div>
        {!compact && <div className="aa-wave-time num">{state.failed ? "Audio not available" : `${fmt(state.t)} / ${fmt(state.d)}`}</div>}
      </div>
    </div>
  );
}
