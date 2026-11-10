import { useEffect } from "react";
import { AudioLines, MessagesSquare, Siren, UserRound, Volume2 } from "lucide-react";
import { useRoute } from "./lib/router";
import AppShell from "./shell/AppShell";
import { Badge, PageHead, Toasts } from "./ui";
import { useApi } from "./lib/api";
import { DEMO, REPO } from "./lib/demo";
import VoiceBank from "./pages/VoiceBank";
import Speak from "./pages/Speak";
import Pain from "./pages/Pain";
import Converse from "./pages/Converse";
import Sos from "./pages/Sos";
import Profile from "./pages/Profile";
import DwellLayer from "./components/DwellLayer";

const NAV = [{ group: "Apni Awaaz", items: [
  { to: "/speak", label: "Speak", icon: Volume2 },
  { to: "/converse", label: "Converse", icon: MessagesSquare },
  { to: "/sos", label: "SOS", icon: Siren },
  { to: "/voice", label: "My voice", short: "Voice", icon: AudioLines },
  { to: "/profile", label: "Profile", icon: UserRound },
] }];
const TITLES = [
  ["/speak", "Speak", "Type or tap, heard in your own voice"],
  ["/pain", "Where does it hurt?", "Tap the body, say how bad"],
  ["/converse", "Converse", "Live captions and one-tap replies"],
  ["/sos", "SOS", "Emergency message in your voice"],
  ["/voice", "My voice", "Build your voice from old voice notes"],
  ["/profile", "Profile", "You, your family, your voice"],
];
const HEADS = {
  "/speak": ["अपनी आवाज़", "Speak in your own voice.", "Type in any script or tap a phrase. It speaks in your cloned voice, in any of 10 Indian languages."],
  "/pain": ["दर्द कहाँ है?", "Where does it hurt?", "Tap the body, choose how bad and what kind. One clear sentence is spoken in your voice, in your language."],
  "/converse": ["Conversation", "Hear them. Answer in one tap.", "Captions show what the other person says. Pick one of three suggested replies and it is spoken in your voice."],
  "/sos": ["Emergency", "Call for help in your own voice.", null],
  "/voice": ["Voice bank", "Get your voice back from 30 seconds of voice notes.", "Gnani zero-shot voice cloning builds your voice from old WhatsApp notes. Only with your consent; delete it any time."],
  "/profile": ["Profile", "About you.", null],
};

// Used when the server can't be reached, so every page (above all SOS) still renders.
const OFFLINE_PROFILE = { name: "", language: "hi-IN", family_names: [], condition: "", fallback_voice: "Shivani", has_voice: false };

function HealthPill({ health }) {
  if (DEMO) return <Badge tone="cyan" dot>Recorded demo</Badge>;
  if (!health) return <Badge tone="muted" dot>Server offline</Badge>;
  if (health.fake) return <Badge tone="amber" dot>Fake mode: no API keys</Badge>;
  if (!health.gnani_key || !health.llm_key) return <Badge tone="rose" dot>API keys missing</Badge>;
  return <Badge tone="green" dot>Gnani live</Badge>;
}

export default function App() {
  const route = useRoute();
  const { data: health, reload: reloadHealth } = useApi("/api/health");
  const { data: loaded, error, reload } = useApi("/api/profile");
  const profile = loaded || (error ? OFFLINE_PROFILE : null);
  const path = HEADS[route.path] ? route.path : null;
  useEffect(() => {
    if (!path && profile) window.location.hash = profile.has_voice ? "/speak" : "/voice";
  }, [path, profile]);

  const page = { "/speak": Speak, "/pain": Pain, "/converse": Converse, "/sos": Sos, "/voice": VoiceBank, "/profile": Profile }[path];
  const [kicker, title, sub] = HEADS[path] || [];
  return (
    <>
      <AppShell
        path={route.path}
        brand={{ name: "Apni Awaaz", sub: "Your own voice · Gnani", logo: "/icons/mark.svg", href: "#/speak" }}
        nav={NAV}
        titles={TITLES}
        topRight={<HealthPill health={health} />}
        footer={<div className="pill-src">Built on Gnani AI: voice cloning (vachana-vc-v1) · Timbre v3.0 · Prisma v3.0</div>}
      >
        {DEMO && (
          <div className="callout demo-banner" role="note">
            <div className="grow">Interactive demo: replays a real session recorded on Gnani's live servers on 10 Nov 2026 with a synthetic voice. Run it locally with your own keys to clone your voice → <a href={REPO} target="_blank" rel="noreferrer">GitHub</a></div>
          </div>
        )}
        {path && <PageHead kicker={kicker} title={title} sub={sub} />}
        {error && !loaded && (
          <div className="callout warn" role="alert" style={{ marginBottom: 14 }}>
            <div className="grow">Can't reach the Apni Awaaz server. SOS still works in the phone's own voice.</div>
            <button className="btn sm" onClick={() => { reload(); reloadHealth(); }}>Retry</button>
          </div>
        )}
        {page && profile && (() => { const P = page; return <P profile={profile} reload={reload} />; })()}
      </AppShell>
      <Toasts />
      <DwellLayer />
    </>
  );
}
