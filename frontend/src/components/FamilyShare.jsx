// SOS page: send the family contact a prefilled WhatsApp or SMS in the person's language, with a map link if allowed.
import { useEffect, useState } from "react";
import { MapPin, MessageCircle, MessageSquareText } from "lucide-react";
import { getLocation, loadFamily, smsLink, sosMessage, waLink } from "../lib/family";

export default function FamilyShare({ lang }) {
  const [family] = useState(loadFamily);
  const [loc, setLoc] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | finding | found | none

  const find = async () => {
    setStatus("finding");
    const l = await getLocation();
    setLoc(l);
    setStatus(l ? "found" : "none");
  };
  useEffect(() => { // already allowed before: add the location straight away
    navigator.permissions?.query({ name: "geolocation" }).then((p) => { if (p.state === "granted") find(); }).catch(() => {});
  }, []);

  if (!family) {
    return (
      <div className="callout family-share">
        <div className="grow small">Add a family contact in <a href="#/profile">Profile</a> to send them your location with one tap.</div>
      </div>
    );
  }
  const text = sosMessage(lang, loc);
  return (
    <div className="stack-sm family-share" style={{ width: "min(100%, 420px)" }}>
      <div className="small muted">Send my location to <b>{family.name}</b> (+{family.phone})</div>
      <button className="btn block" onClick={find} disabled={status === "finding"}>
        <MapPin size={18} /> {status === "finding" ? "Finding my location…" : status === "found" ? `Location added (about ${loc.accuracy} m)` : "Add my location"}
      </button>
      {status === "none" && <div className="small muted">Location is off or not allowed. The message goes without it.</div>}
      <div className="family-actions">
        <a className="btn primary" href={waLink(family.phone, text)} target="_blank" rel="noreferrer"><MessageCircle size={18} /> WhatsApp</a>
        <a className="btn" href={smsLink(family.phone, text)}><MessageSquareText size={18} /> SMS</a>
      </div>
      <pre className="family-preview small" aria-label="Message preview">{text}</pre>
    </div>
  );
}
