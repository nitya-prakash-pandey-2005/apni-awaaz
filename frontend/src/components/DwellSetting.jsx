// Profile: "Select by holding the pointer still" (dwell selection for head pointers and eye-gaze software).
import { useState } from "react";
import { MousePointerClick } from "lucide-react";
import { Card, Toggle } from "../ui";
import { DWELL_MAX, DWELL_MIN, loadDwell, saveDwell } from "../lib/dwell";

export default function DwellSetting() {
  const [cfg, setCfg] = useState(loadDwell);
  const update = (patch) => setCfg(saveDwell({ ...cfg, ...patch }));
  return (
    <Card title="Select by holding the pointer still" icon={MousePointerClick} right={<Toggle on={cfg.on} onChange={(on) => update({ on })} label="Select by holding the pointer still" />}>
      <p className="small muted" style={{ marginTop: 0 }}>
        For a head pointer, eye-gaze software or a mouse you cannot click: rest the pointer on a phrase, chip or body part and a ring fills; when it is full, it is pressed. Moving away or scrolling cancels it. Touch screens work as usual.
      </p>
      <div className="dwell-row">
        <label htmlFor="dwell-time" className="small">Hold for</label>
        <input id="dwell-time" type="range" min={DWELL_MIN} max={DWELL_MAX} step={0.1} value={cfg.seconds} disabled={!cfg.on}
          onChange={(e) => update({ seconds: Number(e.target.value) })} aria-valuetext={`${cfg.seconds.toFixed(1)} seconds`} />
        <b className="mono">{cfg.seconds.toFixed(1)} s</b>
      </div>
    </Card>
  );
}
