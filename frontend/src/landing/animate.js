// All landing-page motion (anime.js v4). Transform, opacity and SVG stroke only.
// Returns a cleanup function. Never called when the person prefers reduced motion.
import { animate, createScope, stagger, svg, utils } from "animejs";

const fmt = (el, v) => {
  const d = Number(el.dataset.decimals || 0);
  return el.dataset.format === "in" ? Math.round(v).toLocaleString("en-IN") : v.toFixed(d);
};

function countUp(el) {
  const out = el.querySelector(".lp-count-v");
  const target = Number(el.dataset.count);
  if (!out || !target) return;
  const o = { v: 0 };
  out.textContent = fmt(el, 0);
  animate(o, { v: target, duration: 1600, ease: "outExpo", onUpdate: () => { out.textContent = fmt(el, o.v); } });
}

function speakBars(root) {
  root.querySelectorAll(".lp-logo.live .lp-bar").forEach((bar, i) => {
    const r = (a, b) => utils.random(a, b) / 100;
    animate(bar, {
      scaleY: [r(35, 60), 1, r(45, 75), r(88, 100), r(40, 60)],
      duration: utils.random(1500, 2100),
      delay: (i % 5) * 90,
      ease: "inOutSine",
      loop: true,
      alternate: true,
    });
  });
}

function pipeline(fig) {
  const lines = fig.querySelectorAll(".lp-pipe-line");
  lines.forEach((l) => animate(svg.createDrawable(l), { draw: ["0 0", "0 1"], duration: 1400, ease: "inOutQuad" }));
  animate(fig.querySelectorAll(".lp-node"), { opacity: [0, 1], scale: [0.85, 1], delay: stagger(200), duration: 600, ease: "outBack(1.6)" });
  animate(fig.querySelectorAll(".lp-pipe-pulse"), { strokeDashoffset: [100, -16], duration: 2600, delay: 1400, loop: true, ease: "inOutSine" });
  animate(fig.querySelectorAll(".lp-node-dot"), {
    scale: [1, 1.12, 1], delay: stagger(260, { start: 1600 }), duration: 520, loop: true, loopDelay: 1500, ease: "outQuad",
  });
}

export function startLanding(root) {
  if (!root) return () => {};
  let io;
  const scope = createScope({ root }).add(() => {
    // Hero: words rise in, copy follows, phone floats, aura drifts.
    animate(root.querySelectorAll(".lp-w"), { opacity: [0, 1], y: ["0.5em", "0em"], rotate: [3, 0], delay: stagger(90, { start: 120 }), duration: 900, ease: "outExpo" });
    animate(root.querySelectorAll("[data-hero]"), { opacity: [0, 1], y: [14, 0], delay: stagger(110, { start: 480 }), duration: 800, ease: "outQuart" });
    animate(root.querySelector(".lp-hero-phone"), { opacity: [0, 1], y: [40, 0], scale: [0.96, 1], duration: 1200, delay: 300, ease: "outExpo" });
    animate(root.querySelector(".lp-float"), { y: [-6, 8], rotate: [-1.2, 0.4], duration: 4200, loop: true, alternate: true, ease: "inOutSine" });
    animate(root.querySelectorAll(".lp-bubble"), { opacity: [0, 1], scale: [0.8, 1], delay: stagger(350, { start: 1100 }), duration: 700, ease: "outBack(1.7)" });
    animate(root.querySelectorAll(".lp-bubble"), { y: [0, -8], duration: 2800, delay: stagger(700, { start: 1800 }), loop: true, alternate: true, ease: "inOutSine" });
    animate(root.querySelector(".a1"), { x: ["-6%", "8%"], y: ["-4%", "6%"], scale: [1, 1.15], duration: 9000, loop: true, alternate: true, ease: "inOutSine" });
    animate(root.querySelector(".a2"), { x: ["6%", "-8%"], y: ["4%", "-6%"], scale: [1.1, 0.95], duration: 11000, loop: true, alternate: true, ease: "inOutSine" });
    animate(root.querySelector(".a3"), { x: ["-4%", "5%"], y: ["6%", "-3%"], scale: [0.95, 1.12], duration: 13000, loop: true, alternate: true, ease: "inOutSine" });
    speakBars(root);
  });

  // Scroll reveals: content is visible by default in the CSS; JS hides it only until it is in view.
  const seen = new WeakSet();
  io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting || seen.has(e.target)) return;
      seen.add(e.target);
      io.unobserve(e.target);
      const el = e.target;
      if (el.matches("[data-pipe]")) { el.classList.add("in"); pipeline(el); return; }
      if (el.dataset.reveal === "chart") {
        animate(el, { opacity: [0, 1], y: [20, 0], duration: 700, ease: "outExpo" });
        animate(el.querySelectorAll(".lp-chart-bar"), { scaleX: [0, 1], delay: stagger(140, { start: 250 }), duration: 900, ease: "outExpo" });
        animate(el.querySelectorAll(".lp-chart-v"), { opacity: [0, 1], delay: stagger(140, { start: 700 }), duration: 500, ease: "outQuad" });
        return;
      }
      const media = el.dataset.reveal === "media";
      animate(el, { opacity: [0, 1], y: [media ? 48 : 24, 0], scale: media ? [0.94, 1] : [1, 1], duration: media ? 1100 : 800, ease: "outExpo", onBegin: () => el.classList.add("in") });
      el.querySelectorAll?.("[data-count]").forEach(countUp);
    });
  }, { rootMargin: "0px 0px -12% 0px", threshold: 0.12 });
  root.querySelectorAll("[data-reveal], [data-pipe]").forEach((el) => io.observe(el));

  return () => { io?.disconnect(); scope.revert(); utils.remove(root.querySelectorAll("*")); };
}
