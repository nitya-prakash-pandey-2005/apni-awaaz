import { useEffect, useMemo } from "react";
import { AudioLines, MessageSquareText, MessagesSquare, Siren, UserRound } from "lucide-react";
import { useRoute, navigate } from "./lib/router";
import AppShell from "./shell/AppShell";
import { Badge, Toasts } from "./ui";
import { useApi } from "./lib/api";
import { AppCtx } from "./state/app";
import Welcome from "./pages/Welcome";
import VoiceBank from "./pages/VoiceBank";
import Speak from "./pages/Speak";
import Converse from "./pages/Converse";
import Sos from "./pages/Sos";
import Profile from "./pages/Profile";

const NAV = [
  { group: "Talk", items: [
    { to: "/speak", label: "Speak", short: "Speak", icon: MessageSquareText },
    { to: "/converse", label: "Conversation", short: "Converse", icon: MessagesSquare },
    { to: "/sos", label: "SOS", short: "SOS", icon: Siren },
  ] },
  { group: "Setup", items: [
    { to: "/voice", label: "My voice", short: "Voice", icon: AudioLines },
    { to: "/profile", label: "Profile and privacy", short: "Profile", icon: UserRound },
  ] },
];
const TITLES = [
  ["/welcome", "Welcome", "Apni Awaaz · अपनी आवाज़"],
  ["/speak", "Speak", "Type or tap, hear your own voice"],
  ["/converse", "Conversation", "Live captions and quick replies"],
  ["/sos", "SOS", "Ask the people around you for help"],
  ["/voice", "My voice", "Build your voice from voice notes"],
  ["/profile", "Profile and privacy", "Your details, your data"],
];
const PAGES = { "/welcome": Welcome, "/speak": Speak, "/converse": Converse, "/sos": Sos, "/voice": VoiceBank, "/profile": Profile };

function VoicePill({ health, profile }) {
  if (!health) return <Badge tone="muted" dot>Server offline</Badge>;
  const demo = health.fake ? <span className="desktop-only"> · demo mode</span> : null;
  if (!health.fake && !health.gnani_key) return <Badge tone="rose" dot>API key missing</Badge>;
  if (profile?.has_voice && health.clone?.available) return <Badge tone="green" dot>My voice{demo}</Badge>;
  if (profile?.has_voice) return <Badge tone="amber" dot>Fallback voice for now{demo}</Badge>;
  return <Badge tone="cyan" dot>Standard voice{demo}</Badge>;
}

export default function App() {
  const route = useRoute();
  const { data: profile, reload: reloadProfile, loading } = useApi("/api/profile");
  const { data: health, reload: reloadHealth } = useApi("/api/health");

  useEffect(() => {
    if (loading) return;
    if (route.path === "/" || route.path === "" || !PAGES[route.path]) navigate(profile?.exists ? "/speak" : "/welcome");
  }, [route.path, profile, loading]);

  // keep the voice pill honest: re-check every 30 s (the clone breaker reopens after a minute)
  useEffect(() => {
    const id = setInterval(reloadHealth, 30000);
    return () => clearInterval(id);
  }, [reloadHealth]);

  const ctx = useMemo(() => ({ profile, health, reloadProfile, reloadHealth }), [profile, health, reloadProfile, reloadHealth]);
  const Page = PAGES[route.path];

  return (
    <AppCtx.Provider value={ctx}>
      <AppShell
        path={route.path}
        brand={{ name: "Apni Awaaz", sub: "Your own voice", logo: "/icons/icon.svg", href: "#/speak" }}
        nav={NAV}
        titles={TITLES}
        topRight={<VoicePill health={health} profile={profile} />}
        footer={<div className="pill-src">Built on Gnani AI: voice cloning (vachana-vc-v1) · Timbre v3.0 · Prisma v3.0</div>}
      >
        {!profile && loading ? <div className="skeleton" style={{ height: 240 }} /> : Page ? <Page key={route.path} query={route.query} /> : null}
      </AppShell>
      <Toasts />
    </AppCtx.Provider>
  );
}
