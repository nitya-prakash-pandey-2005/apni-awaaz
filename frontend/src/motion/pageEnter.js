// Gentle page entrance on route change: the page fades up and its first cards/tiles follow in a short stagger.
// Transform and opacity only, under 400 ms in total, and nothing waits on it: every element can be tapped at once.
import { animate, stagger } from "animejs";
import { reducedMotion } from "./prefs";

export function pageEnter(root = document.querySelector(".content")) {
  if (!root || reducedMotion()) return () => {};
  const head = root.querySelector(".page-head");
  const cards = [...root.querySelectorAll(".card, .sos-card, .pain-link")].slice(0, 8);
  const tiles = [...root.querySelectorAll(".phrase")].slice(0, 12);
  const anims = [];
  if (head) anims.push(animate(head, { opacity: [0.4, 1], y: [6, 0], duration: 260, ease: "outQuad" }));
  if (cards.length) anims.push(animate(cards, { opacity: [0.35, 1], y: [10, 0], delay: stagger(35), duration: 280, ease: "outQuad" }));
  if (tiles.length) anims.push(animate(tiles, { opacity: [0.5, 1], scale: [0.97, 1], delay: stagger(14, { start: 60 }), duration: 220, ease: "outQuad" }));
  return () => anims.forEach((a) => a.revert());
}
