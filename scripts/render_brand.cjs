// Render the Apni Awaaz brand PNGs from the SVGs written by scripts/make_brand.py.
//
// Needs puppeteer-core and a local Chrome:
//   NODE_PATH=<folder with node_modules/puppeteer-core> node scripts/render_brand.cjs
// Writes frontend/public/icons/{icon-192,icon-512,icon-maskable-512,apple-touch-icon,favicon-32}.png
// and docs/brand/banner.png (2x, 1280x400 CSS px).
const path = require("path");
const fs = require("fs");
const puppeteer = require("puppeteer-core");

const ROOT = path.resolve(__dirname, "..");
const ICONS = path.join(ROOT, "frontend", "public", "icons");
const BRAND = path.join(ROOT, "docs", "brand");
const FONTS = path.join(ROOT, "frontend", "node_modules");
const CHROME = process.env.CHROME || "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const url = (p) => "file:///" + p.replace(/\\/g, "/");

async function shot(page, svgFile, size, out) {
  const html = `<html><body style="margin:0;background:transparent"><img src="${url(svgFile)}" width="${size}" height="${size}" style="display:block"></body></html>`;
  const tmp = path.join(BRAND, ".render.html");
  fs.writeFileSync(tmp, html);
  await page.setViewport({ width: size, height: size, deviceScaleFactor: 1 });
  await page.goto(url(tmp), { waitUntil: "load" });
  await page.screenshot({ path: out, omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
  fs.unlinkSync(tmp);
}

function bannerHtml() {
  const f = (p) => url(path.join(FONTS, p));
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:SG;src:url(${f("@fontsource-variable/space-grotesk/files/space-grotesk-latin-wght-normal.woff2")});font-weight:300 700}
@font-face{font-family:IN;src:url(${f("@fontsource-variable/inter/files/inter-latin-wght-normal.woff2")});font-weight:100 900}
@font-face{font-family:DV;src:url(${f("@fontsource/noto-sans-devanagari/files/noto-sans-devanagari-devanagari-600-normal.woff2")});font-weight:600}
html,body{margin:0;width:1280px;height:400px;overflow:hidden}
body{background:#0B0716;position:relative;font-family:IN,'Segoe UI',sans-serif;color:#FFF7F3}
.g1{position:absolute;left:-120px;top:-160px;width:620px;height:620px;border-radius:50%;background:radial-gradient(circle,rgba(255,138,91,.30),rgba(255,138,91,0) 65%)}
.g2{position:absolute;right:-160px;bottom:-260px;width:760px;height:760px;border-radius:50%;background:radial-gradient(circle,rgba(139,92,246,.32),rgba(139,92,246,0) 65%)}
.g3{position:absolute;left:520px;top:-200px;width:520px;height:520px;border-radius:50%;background:radial-gradient(circle,rgba(244,63,122,.18),rgba(244,63,122,0) 65%)}
.wave{position:absolute;left:0;right:0;bottom:22px;height:56px;opacity:.16}
.row{position:absolute;inset:0;display:flex;align-items:center;gap:52px;padding:0 84px}
.row img{width:236px;height:236px;filter:drop-shadow(0 18px 40px rgba(244,63,122,.35))}
h1{margin:0;font-family:SG;font-weight:700;font-size:74px;letter-spacing:-2.5px;line-height:1}
h1 .dot{color:#F43F7A;margin:0 14px}
h1 .hi{font-family:DV,'Nirmala UI',sans-serif;font-weight:600;letter-spacing:0;font-size:62px;background:linear-gradient(90deg,#FF8A5B,#F43F7A 45%,#A78BFA);-webkit-background-clip:text;background-clip:text;color:transparent}
.tag{margin-top:22px;font-family:SG;font-size:38px;font-weight:500;letter-spacing:-.5px;color:#FFD9CC}
.sub{margin-top:16px;font-size:18px;color:#B9B2CF;letter-spacing:.2px}
</style></head><body><div class="g1"></div><div class="g2"></div><div class="g3"></div>
<svg class="wave" viewBox="0 0 1280 60" preserveAspectRatio="none">${Array.from({ length: 160 }, (_, i) => {
    const h = 6 + Math.abs(Math.sin(i * 0.37) * Math.cos(i * 0.11)) * 50;
    return `<rect x="${i * 8}" y="${30 - h / 2}" width="4" height="${h}" rx="2" fill="#FFF7F3"/>`;
  }).join("")}</svg>
<div class="row"><img src="${url(path.join(BRAND, "logo.svg"))}" alt="">
<div><h1>Apni Awaaz<span class="dot">·</span><span class="hi">अपनी आवाज़</span></h1>
<div class="tag">Your own voice, back.</div>
<div class="sub">Voice banking and talk-assist in 10 Indian languages, built on Gnani AI voice cloning</div></div></div>
</body></html>`;
}

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: "new", args: ["--allow-file-access-from-files"] });
  const page = await browser.newPage();
  await shot(page, path.join(ICONS, "icon-full.svg"), 512, path.join(ICONS, "icon-512.png"));
  await shot(page, path.join(ICONS, "icon-full.svg"), 192, path.join(ICONS, "icon-192.png"));
  await shot(page, path.join(ICONS, "icon-maskable.svg"), 512, path.join(ICONS, "icon-maskable-512.png"));
  await shot(page, path.join(ICONS, "icon-maskable.svg"), 180, path.join(ICONS, "apple-touch-icon.png"));
  await shot(page, path.join(ICONS, "icon.svg"), 32, path.join(ICONS, "favicon-32.png"));

  const tmp = path.join(BRAND, ".banner.html");
  fs.writeFileSync(tmp, bannerHtml());
  await page.setViewport({ width: 1280, height: 400, deviceScaleFactor: 2 });
  await page.goto(url(tmp), { waitUntil: "networkidle0" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(BRAND, "banner.png") });
  fs.unlinkSync(tmp);
  await browser.close();
  console.log("rendered icons and banner");
})();
