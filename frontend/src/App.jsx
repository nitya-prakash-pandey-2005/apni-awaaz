import { useEffect } from "react";
import { AudioLines, MessagesSquare, Siren, UserRound, Volume2 } from "lucide-react";
import { useRoute } from "./lib/router";
import AppShell from "./shell/AppShell";
import { Badge, PageHead, Toasts } from "./ui";
import { useApi } from "./lib/api";
import VoiceBank from "./pages/VoiceBank";
import Speak from "./pages/Speak";
import Converse from "./pages/Converse";
import Sos from "./pages/Sos";
import Profile from "./pages/Profile";

const NAV = [{ group: "Apni Awaaz", items: [
  { to: "/speak", label: "Speak", icon: Volume2 },
  { to: "/converse", label: "Converse", icon: MessagesSquare },
  { to: "/sos", label: "SOS", icon: Siren },
  { to: "/voice", label: "My voice", short: "Voice", icon: AudioLines },
  { to: "/profile", label: "Profile", icon: UserRound },
] }];
const TITLES = [
  ["/speak", "Speak", "Type or tap, heard in your own voice"],
  ["/converse", "Converse", "Live captions and one-tap replies"],
  ["/sos", "SOS", "Emergency message in your voice"],
  ["/voice", "My voice", "Build your voice from old voice notes"],
  ["/profile", "Profile", "You, your family, your voice"],
];
const HEADS = {
  "/speak": ["अपनी आवाज़", "Speak in your own voice.", "Type in any script or tap a phrase. It speaks in your cloned voice, in any of 10 Indian languages."],
  "/converse": ["Conversation", "Hear them. Answer in one tap.", "Captions show what the other person says. Pick one of three suggested replies and it is spoken in your voice."],
  "/sos": ["Emergency", "Call for help in your own voice.", null],
  "/voice": ["Voice bank", "Get your voice back from 30 seconds of voice notes.", "Gnani zero-shot voice cloning builds your voice from old WhatsApp notes. Only with your consent; delete it any time."],
  "/profile": ["Profile", "About you.", null],
};

function HealthPill({ health }) {
  if (!health) return <Badge tone="muted" dot>Server offline</Badge>;
  if (health.fake) return <Badge tone="amber" dot>Fake mode: no API keys</Badge>;
  if (!health.gnani_key || !health.llm_key) return <Badge tone="rose" dot>API keys missing</Badge>;
  return <Badge tone="green" dot>Gnani live</Badge>;
}

export default function App() {
  const route = useRoute();
  const { data: health } = useApi("/api/health");
  const { data: profile, reload } = useApi("/api/profile");
  const path = HEADS[route.path] ? route.path : null;
  useEffect(() => {
    if (!path && profile) window.location.hash = profile.has_voice ? "/speak" : "/voice";
  }, [path, profile]);

  const page = { "/speak": Speak, "/converse": Converse, "/sos": Sos, "/voice": VoiceBank, "/profile": Profile }[path];
  const [kicker, title, sub] = HEADS[path] || [];
  return (
    <>
      <AppShell
        path={route.path}
        brand={{ name: "Apni Awaaz", sub: "Your own voice · Gnani", logo: "/icons/icon.svg", href: "#/speak" }}
        nav={NAV}
        titles={TITLES}
        topRight={<HealthPill health={health} />}
        footer={<div className="pill-src">Built on Gnani AI: voice cloning (vachana-vc-v1) · Timbre v3.0 · Prisma v3.0</div>}
      >
        {path && <PageHead kicker={kicker} title={title} sub={sub} />}
        {page && profile && (() => { const P = page; return <P profile={profile} reload={reload} />; })()}
      </AppShell>
      <Toasts />
    </>
  );
}
