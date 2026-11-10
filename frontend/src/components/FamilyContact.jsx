// Profile: the one family contact used by "Send my location" on the SOS page. Stored only in this browser.
import { useState } from "react";
import { Trash2, UsersRound } from "lucide-react";
import { Badge, Card, toast } from "../ui";
import { forgetFamily, loadFamily, saveFamily } from "../lib/family";

export default function FamilyContact() {
  const [saved, setSaved] = useState(loadFamily);
  const [name, setName] = useState(saved?.name || "");
  const [phone, setPhone] = useState(saved?.phone ? `+${saved.phone}` : "");
  const [agree, setAgree] = useState(!!saved);

  const save = () => {
    try {
      setSaved(saveFamily({ name, phone }));
      toast("Family contact saved on this phone", "ok");
    } catch (e) {
      toast(e.message, "warn");
    }
  };
  const forget = () => { forgetFamily(); setSaved(null); setName(""); setPhone(""); setAgree(false); toast("Family contact removed", "ok"); };

  return (
    <Card title="Family contact for SOS" icon={UsersRound} right={<Badge tone={saved ? "green" : "muted"} dot>{saved ? "Saved" : "Not set"}</Badge>}>
      <div className="stack-sm">
        <label className="field">Name<input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ravi (son)" autoComplete="off" /></label>
        <label className="field">Mobile number<input className="input" type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="98765 43210" autoComplete="off" /></label>
        <label className="row small consent-line">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} />
          <span>Keep this number on this phone only. It is never sent to the Apni Awaaz server. On the SOS page, &ldquo;Send my location&rdquo; opens WhatsApp or SMS with a ready message; nothing is sent until you press Send there.</span>
        </label>
        <div className="row">
          <button className="btn primary" disabled={!agree || !phone.trim()} onClick={save}>Save contact</button>
          {saved && <button className="btn ghost" onClick={forget}><Trash2 size={16} /> Remove</button>}
        </div>
      </div>
    </Card>
  );
}
