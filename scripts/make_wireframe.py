"""Low-fidelity phone wireframe for Apni Awaaz -> docs/design/wireframe.svg

Run: python scripts/make_wireframe.py [out.svg]
"""
import sys
from pathlib import Path

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "docs" / "design" / "wireframe.svg"
W, H = 1260, 1610
PW, PH = 300, 610
INK, MUTE, FILL, FILL2, ACC, VIO, PAPER = "#2A2838", "#7A7690", "#ECEAF2", "#F6F5FA", "#F43F7A", "#8B5CF6", "#FBFAF7"
F = "font-family=\"'Segoe UI', 'Inter', system-ui, sans-serif\""
o = []


def t(x, y, s, size=11, fill=INK, weight=400, anchor="start", italic=False):
    st = ' font-style="italic"' if italic else ""
    s = s.replace("&", "&amp;").replace("<", "&lt;")
    o.append(f'<text x="{x}" y="{y}" {F} font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{st}>{s}</text>')


def r(x, y, w, h, rx=8, fill=FILL, stroke=None, dash=False, sw=1.2):
    sk = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
    d = ' stroke-dasharray="5 4"' if dash else ""
    o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"{sk}{d}/>')


def lines(x, y, w, n, gap=9, fill="#D9D6E3"):
    for i in range(n):
        ww = w if i < n - 1 else w * 0.62
        r(x, y + i * gap, ww, 4, 2, fill)


def tag(x, y, n, label):
    """Numbered region label."""
    o.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{VIO}"/>')
    t(x, y + 3.5, str(n), 9, "#fff", 700, "middle")
    t(x + 13, y + 4, label, 10, VIO, 600)


def phone(px, py, num, title, sub, active, body):
    r(px - 4, py - 4, PW + 8, PH + 8, 40, "#fff", INK, sw=2)
    r(px, py, PW, PH, 36, "#fff")
    # notch
    r(px + PW / 2 - 40, py + 8, 80, 14, 7, INK)
    # top bar
    sy = py + 30
    o.append(f'<rect x="{px + 16}" y="{sy + 6}" width="24" height="22" rx="7" fill="url(#wf-g)"/>')
    t(px + 48, sy + 16, title, 13, INK, 700)
    t(px + 48, sy + 29, sub, 9, MUTE)
    r(px + PW - 86, sy + 9, 70, 18, 9, "#fff", "#22B8CF")
    t(px + PW - 51, sy + 21.5, "status pill", 8.5, "#1597AB", 600, "middle")
    o.append(f'<line x1="{px}" y1="{sy + 40}" x2="{px + PW}" y2="{sy + 40}" stroke="#E4E2EC"/>')
    body(px + 16, sy + 50, PW - 32)
    # tab bar
    ty = py + PH - 58
    o.append(f'<line x1="{px}" y1="{ty}" x2="{px + PW}" y2="{ty}" stroke="#E4E2EC"/>')
    tabs = ["Speak", "Converse", "SOS", "Voice", "Profile"]
    for i, tb in enumerate(tabs):
        cx = px + 30 + i * (PW - 60) / 4
        on = tb == active
        o.append(f'<rect x="{cx - 9}" y="{ty + 10}" width="18" height="16" rx="4" fill="{ACC if on else "#CFCCDA"}"/>')
        t(cx, ty + 40, tb, 9, ACC if on else MUTE, 700 if on else 400, "middle")
    # caption
    t(px + PW / 2, py + PH + 34, f"{num} · {CAPS[num][0]}", 15, INK, 700, "middle")
    t(px + PW / 2, py + PH + 52, CAPS[num][1], 10.5, MUTE, 400, "middle")


CAPS = {
    1: ("Welcome + consent", "first run opens My voice; consent before anything"),
    2: ("Voice bank", "check old voice notes, build the voice"),
    3: ("Speak", "type in any script or tap a phrase"),
    4: ("Converse", "captions in, one-tap replies out"),
    5: ("SOS", "one button; works with the server down"),
    6: ("Profile", "who you are; delete your voice any time"),
}


def s1(x, y, w):
    t(x, y + 10, "VOICE BANK", 9, ACC, 700)
    t(x, y + 30, "Get your voice back from", 15, INK, 700)
    t(x, y + 49, "30 seconds of voice notes.", 15, INK, 700)
    lines(x, y + 60, w, 3)
    tag(x + 8, y + 102, 1, "Consent card")
    r(x, y + 114, w, 150, 12, FILL2, "#D6D2E2")
    t(x + 12, y + 136, "1. Consent", 12, INK, 700)
    r(x + 12, y + 150, 16, 16, 4, "#fff", ACC, sw=1.6)
    t(x + 36, y + 162, "This is my voice / I have permission", 10, INK)
    lines(x + 12, y + 178, w - 24, 3)
    r(x + 12, y + 214, w - 24, 36, 10, "#fff", "#C9C5D6", dash=True)
    t(x + w / 2, y + 236, "Upload + record stay locked until ticked", 10, MUTE, 600, "middle")
    tag(x + 8, y + 286, 2, "Step 2 and 3 (greyed)")
    r(x, y + 298, w, 46, 12, FILL2, "#E2DFEA")
    t(x + 12, y + 326, "2. Add 1–5 voice notes", 11, "#A9A5B8", 600)
    r(x, y + 352, w, 46, 12, FILL2, "#E2DFEA")
    t(x + 12, y + 380, "3. Build my voice", 11, "#A9A5B8", 600)
    t(x, y + 422, "API refuses without consent (HTTP 400)", 9.5, VIO, 600, italic=True)
    t(x, y + 436, "Consent time saved, shown on Profile", 9.5, VIO, 600, italic=True)


def s2(x, y, w):
    tag(x + 8, y + 8, 1, "Add notes: .opus .ogg .mp3 .wav, or record")
    r(x, y + 20, w, 40, 10, "#fff", ACC, dash=True, sw=1.4)
    t(x + w / 2, y + 45, "+ Upload voice notes   ·   Record", 11, ACC, 700, "middle")
    tag(x + 8, y + 80, 2, "Quality check per clip")
    for i, (name, chip, good) in enumerate([("note-1.opus · 10.6 s", "Good", True), ("note-2.opus · 8.1 s", "Good", True), ("note-3.opus · 2.0 s", "Too short", False)]):
        yy = y + 92 + i * 52
        r(x, yy, w, 44, 10, FILL2, "#E2DFEA")
        t(x + 10, yy + 17, name, 10.5, INK, 600)
        t(x + 10, yy + 32, "speech · clipping · SNR · Prisma text", 8.5, MUTE)
        cw = 54 if good else 66
        r(x + w - cw - 8, yy + 12, cw, 20, 10, "#E3F7EE" if good else "#FDE8EC")
        t(x + w - cw / 2 - 8, yy + 26, chip, 9.5, "#13895F" if good else "#C42B52", 700, "middle")
    tag(x + 8, y + 262, 3, "Build (Gnani voice cloning)")
    r(x, y + 274, w, 44, 12, "url(#wf-g)")
    t(x + w / 2, y + 301, "Build my voice", 13, "#fff", 700, "middle")
    tag(x + 8, y + 340, 4, "Hear a test phrase")
    r(x, y + 352, w, 76, 12, FILL2, "#E2DFEA")
    o.append(f'<circle cx="{x + 24}" cy="{y + 376}" r="12" fill="{VIO}"/>')
    o.append(f'<path d="M{x + 20} {y + 370} l10 6 -10 6z" fill="#fff"/>')
    for i in range(18):
        hgt = 6 + (i * 37 % 17)
        r(x + 46 + i * 9, y + 376 - hgt / 2, 4, hgt, 2, "#C9B8F5")
    r(x + 10, y + 398, 108, 22, 11, "#fff", ACC)
    t(x + 64, y + 413, "Sounds like me", 9.5, ACC, 700, "middle")
    r(x + 126, y + 398, 90, 22, 11, "#fff", "#C9C5D6")
    t(x + 171, y + 413, "Try other clips", 9.5, MUTE, 600, "middle")


def s3(x, y, w):
    tag(x + 8, y + 8, 1, "Switch scanning (Space / Enter / switch)")
    r(x, y + 20, w, 34, 10, FILL2, "#E2DFEA")
    t(x + 10, y + 41, "Switch scanning", 11, INK, 600)
    r(x + w - 40, y + 29, 28, 16, 8, "#D6D2E2")
    tag(x + 8, y + 72, 2, "Banked messages (original audio)")
    for i, s in enumerate(["I love you, beta", "Happy birthday"]):
        r(x + i * (w / 2 + 2), y + 84, w / 2 - 2, 40, 10, "#FFF4F7", ACC)
        t(x + i * (w / 2 + 2) + (w / 2 - 2) / 2, y + 108, s, 10, INK, 600, "middle")
    tag(x + 8, y + 142, 3, "Quick phrases (learn from use)")
    for i in range(4):
        cx, cy = x + (i % 2) * (w / 2 + 2), y + 154 + (i // 2) * 46
        r(cx, cy, w / 2 - 2, 40, 10, FILL2, "#E2DFEA")
        lines(cx + 14, cy + 15, w / 2 - 30, 2, 8, "#BDB8CC")
    tag(x + 8, y + 262, 4, "Say anything: any script, romanised")
    r(x, y + 274, w, 52, 10, "#fff", "#C9C5D6")
    t(x + 10, y + 296, "mujhe paani chahiye", 11, INK, 400, italic=True)
    for i, lg in enumerate(["hi", "ta", "bn", "mr", "te", "+5"]):
        r(x + i * 44, y + 334, 38, 22, 11, VIO if i == 0 else "#fff", VIO)
        t(x + i * 44 + 19, y + 349, lg, 9.5, "#fff" if i == 0 else VIO, 700, "middle")
    r(x, y + 364, w, 40, 12, "url(#wf-g)")
    t(x + w / 2, y + 389, "Speak", 13, "#fff", 700, "middle")
    tag(x + 8, y + 422, 5, "Badge: Your voice / Fallback / Phone")
    r(x + 150, y + 434, 118, 20, 10, "#E3F7EE")
    t(x + 209, y + 448, "● Your voice", 9.5, "#13895F", 700, "middle")


def s4(x, y, w):
    tag(x + 8, y + 8, 1, "Listen (Prisma v3.0 streaming)")
    r(x, y + 20, w, 40, 12, "#fff", ACC, sw=1.6)
    t(x + w / 2, y + 45, "● Start listening", 12, ACC, 700, "middle")
    tag(x + 8, y + 80, 2, "Live captions (aria-live)")
    for i, (s, ww) in enumerate([("Namaste Sharma ji.", 150), ("Aaj aapko kaisa lag raha hai?", 210)]):
        yy = y + 92 + i * 40
        r(x, yy, ww, 32, 12, FILL2, "#E2DFEA")
        t(x + 10, yy + 20, s, 10, INK)
    r(x + w - 120, y + 172, 120, 28, 12, "#F1ECFE")
    t(x + w - 60, y + 190, "you (not captioned)", 9, VIO, 600, "middle")
    tag(x + 8, y + 220, 3, "3 suggested replies, your language")
    for i in range(3):
        yy = y + 232 + i * 48
        r(x, yy, w, 42, 12, "#FFF4F7", ACC)
        lines(x + 14, yy + 15, w - 70, 2, 9, "#E7A6BD")
        o.append(f'<circle cx="{x + w - 22}" cy="{yy + 21}" r="10" fill="{ACC}"/>')
    tag(x + 8, y + 388, 4, "Your reply (type your own)")
    r(x, y + 400, w - 90, 36, 10, "#fff", "#C9C5D6")
    r(x + w - 84, y + 400, 84, 36, 10, "url(#wf-g)")
    t(x + w - 42, y + 422, "Speak reply", 9.5, "#fff", 700, "middle")


def s5(x, y, w):
    tag(x + 8, y + 8, 1, "One large button (260 px)")
    cx, cy = x + w / 2, y + 150
    o.append(f'<circle cx="{cx}" cy="{cy}" r="118" fill="#FFE9EE" stroke="{ACC}" stroke-width="2"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="94" fill="url(#wf-g)"/>')
    t(cx, cy + 4, "SOS", 34, "#fff", 800, "middle")
    t(cx, cy + 28, "speak for help", 10.5, "#fff", 600, "middle")
    tag(x + 8, y + 292, 2, "Message in 2 languages, large type")
    r(x, y + 304, w, 104, 12, FILL2, "#E2DFEA")
    t(x + 12, y + 330, "Mujhe madad chahiye...", 15, INK, 700)
    lines(x + 12, y + 342, w - 24, 2, 10, "#BDB8CC")
    t(x + 12, y + 384, "Enakku udhavi vendum...", 15, INK, 700)
    t(x, y + 432, "Gnani down? Phone's own voice + text", 9.5, VIO, 600, italic=True)


def s6(x, y, w):
    tag(x + 8, y + 8, 1, "About me: name, language, family")
    r(x, y + 20, w, 112, 12, FILL2, "#E2DFEA")
    for i, lb in enumerate(["Name", "Language", "Family names (help captions)"]):
        t(x + 12, y + 40 + i * 32, lb, 9, MUTE, 600)
        r(x + 12, y + 45 + i * 32, w - 24, 14, 5, "#fff", "#D6D2E2")
    tag(x + 8, y + 150, 2, "My voice: consent time, delete")
    r(x, y + 162, w, 96, 12, FILL2, "#E2DFEA")
    t(x + 12, y + 184, "Consent given 10 Nov, 19:31", 10.5, INK, 600)
    t(x + 12, y + 200, "Embedding stays on the app's server", 9, MUTE)
    r(x + 12, y + 214, 130, 32, 10, "#fff", "#D93A5E", sw=1.6)
    t(x + 77, y + 234, "Delete my voice", 10.5, "#D93A5E", 700, "middle")
    tag(x + 8, y + 276, 3, "My recordings (banked)")
    for i, s in enumerate(["I love you, beta", "Happy birthday, gudiya", "My laugh"]):
        yy = y + 288 + i * 42
        r(x, yy, w, 36, 10, FILL2, "#E2DFEA")
        o.append(f'<circle cx="{x + 18}" cy="{yy + 18}" r="9" fill="{VIO}"/>')
        t(x + 34, yy + 22, s, 10, INK, 600)
        t(x + w - 14, yy + 22, "delete", 9, "#D93A5E", 600, "end")


o.append(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
o.append('<defs><linearGradient id="wf-g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FF8A5B"/><stop offset=".5" stop-color="#F43F7A"/><stop offset="1" stop-color="#8B5CF6"/></linearGradient>'
         f'<marker id="wf-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10z" fill="{INK}"/></marker></defs>')
t(60, 58, "Apni Awaaz · phone wireframe (390 px, low fidelity)", 24, INK, 800)
t(60, 84, "The six screens and the main path through them. Numbered tags name each region; arrows show the flow. Purple notes are rules the backend enforces.", 12.5, MUTE)

xs = [60, 480, 900]
ys = [130, 880]
bodies = [s1, s2, s3, s4, s5, s6]
titles = [("My voice", "Build your voice from old notes", "Voice"), ("My voice", "Build your voice from old notes", "Voice"),
          ("Speak", "Type or tap, in your own voice", "Speak"), ("Converse", "Live captions, one-tap replies", "Converse"),
          ("SOS", "Emergency message in your voice", "SOS"), ("Profile", "You, your family, your voice", "Profile")]
for i in range(6):
    px, py = xs[i % 3], ys[i // 3]
    phone(px, py, i + 1, titles[i][0], titles[i][1], titles[i][2], bodies[i])


def arrow(d, label=None, lx=0, ly=0):
    o.append(f'<path d="{d}" fill="none" stroke="{INK}" stroke-width="2" marker-end="url(#wf-a)"/>')
    if label:
        t(lx, ly, label, 10.5, INK, 600, "middle")


mid = 130 + PH / 2
arrow(f"M{60 + PW + 12} {mid} L{480 - 14} {mid}", "tick consent", 420, mid - 10)
arrow(f"M{480 + PW + 12} {mid} L{900 - 14} {mid}", "voice built", 840, mid - 10)
# Speak -> Converse (down and around to the start of row 2)
o.append(f'<rect x="520" y="814" width="220" height="24" rx="12" fill="{PAPER}"/>')
arrow(f"M{900 + PW / 2} {130 + PH + 64} L{900 + PW / 2} {826} L{60 + PW / 2} {826} L{60 + PW / 2} {880 - 12}")
o.append(f'<rect x="510" y="812" width="240" height="26" rx="13" fill="{PAPER}" stroke="{INK}" stroke-width="1.2"/>')
t(630, 829, "then: tab bar, any screen, one tap", 10.5, INK, 600, "middle")
mid2 = 880 + PH / 2
arrow(f"M{60 + PW + 12} {mid2} L{480 - 14} {mid2}", "tab", 420, mid2 - 10)
arrow(f"M{480 + PW + 12} {mid2} L{900 - 14} {mid2}", "tab", 840, mid2 - 10)

# legend
ly = H - 40
o.append(f'<circle cx="68" cy="{ly - 4}" r="8" fill="{VIO}"/>')
t(68, ly - 0.5, "1", 9, "#fff", 700, "middle")
t(84, ly, "labelled region", 11, INK)
r(200, ly - 14, 40, 18, 9, "url(#wf-g)")
t(248, ly, "primary action", 11, INK)
r(360, ly - 14, 40, 18, 9, "#FFF4F7", ACC)
t(408, ly, "one-tap speech", 11, INK)
r(520, ly - 14, 40, 18, 9, "#fff", "#C9C5D6", dash=True)
t(568, ly, "locked / drop zone", 11, INK)
t(W - 60, ly, "Matches the built app (frontend/src/pages). Screens 1 and 2 are the two halves of My voice.", 11, MUTE, 400, "end")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">' + "".join(o) + "</svg>\n", encoding="utf-8")
print("ok", OUT)
