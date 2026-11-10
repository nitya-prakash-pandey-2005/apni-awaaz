import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource/noto-sans-devanagari/400.css";
import "@fontsource/noto-sans-tamil/400.css";
import "@fontsource/noto-sans-bengali/400.css";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/layout.css";
import "./styles/tour.css";
import "./app.css";
import "./landing.css";
import { applySavedTheme } from "./lib/theme";
import { DEMO, installDemo } from "./lib/demo";
import App from "./App";

applySavedTheme();
installDemo(); // demo build only: answers /api from recorded files; no service worker
if ("serviceWorker" in navigator && import.meta.env.PROD && !DEMO) {
  window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").then((r) => r.update()).catch(() => {}));
}
createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
