// One place to ask whether the person wants less motion (very common for this audience).
export const reducedMotion = () =>
  typeof window === "undefined" || !window.matchMedia || window.matchMedia("(prefers-reduced-motion: reduce)").matches;

// The installed PWA opens straight into the app (start_url /#/speak); only browsers see the landing page.
export const standalone = () =>
  typeof window !== "undefined" && !!window.matchMedia && (window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true);
