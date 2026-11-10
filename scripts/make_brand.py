"""Generate the Apni Awaaz brand marks (SVG) from one geometric definition.

The mark is a speech bubble whose voice waveform traces a heart: vertical
audio bars whose tops and bottoms follow the classic heart curve
x = 16 sin^3 t, y = 13 cos t - 5 cos 2t - 2 cos 3t - cos 4t.

Outputs:
  docs/brand/logo.svg             transparent mark (7 bars), any background
  docs/brand/logo-small.svg       transparent mark (5 bars), for 16-32 px
  docs/brand/wordmark.svg         mark + "Apni Awaaz" + "अपनी आवाज़"
  frontend/public/icons/mark.svg  transparent 5-bar mark (the app shell's brand logo)
  frontend/public/icons/icon.svg  app icon (dark rounded tile, 5 bars; favicon and shell logo)
  frontend/public/icons/icon-full.svg      app icon tile, 7 bars (source of the 192/512 PNGs)
  frontend/public/icons/icon-maskable.svg  full-bleed tile with the mark inside the 80 % safe zone

PNG renders (icon-192.png, icon-512.png, icon-maskable-512.png,
apple-touch-icon.png, favicon-32.png, docs/brand/banner.png) are made with
headless Chrome from these SVGs; see scripts/render_brand.cjs.

Run: uv run --no-project python scripts/make_brand.py
"""

from __future__ import annotations

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "docs" / "brand"
ICONS = ROOT / "frontend" / "public" / "icons"

CORAL, ROSE, VIOLET = "#FF8A5B", "#F43F7A", "#8B5CF6"
INK = "#0B0716"
WHITE = "#FFF7F3"

# Heart curve sampled once.
_HEART = [
    (16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
    for t in (i * 2 * math.pi / 40000 for i in range(40000))
]


def heart_span(u: float, tol: float = 0.06) -> tuple[float, float]:
    """Vertical extent (ymin, ymax) of the heart at horizontal position u (heart units)."""
    ys = [y for x, y in _HEART if abs(x - u) < tol]
    return min(ys), max(ys)


def bars(n: int, width: float, gap: float, sx: float, sy: float, cx: float, cy_mid: float) -> str:
    """SVG rects for n heart-shaped waveform bars centred on (cx, cy_mid)."""
    out = []
    y_mid = (11.923 + -17.0) / 2  # vertical centre of the heart curve
    step = width + gap
    for i in range(n):
        xc = cx + (i - (n - 1) / 2) * step
        u = (xc - cx) / sx
        u = max(-15.2, min(15.2, u))
        ymin, ymax = heart_span(u)
        top = cy_mid - (ymax - y_mid) * sy
        bot = cy_mid - (ymin - y_mid) * sy
        if bot - top < width:  # never thinner than a dot
            m = (top + bot) / 2
            top, bot = m - width / 2, m + width / 2
        out.append(
            f'<rect x="{xc - width / 2:.1f}" y="{top:.1f}" width="{width:.1f}" height="{bot - top:.1f}" rx="{width / 2:.1f}"/>'
        )
    return "".join(out)


def gradient(gid: str) -> str:
    return (
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="48" y1="48" x2="464" y2="468">'
        f'<stop offset="0" stop-color="{CORAL}"/><stop offset=".5" stop-color="{ROSE}"/>'
        f'<stop offset="1" stop-color="{VIOLET}"/></linearGradient>'
    )


BUBBLE = (
    '<rect x="48" y="52" width="416" height="340" rx="136"/>'
    '<path d="M132 318 L94 462 L262 372 Z" stroke-linejoin="round" stroke-width="28"/>'
)


def mark(n_bars: int, gid: str = "aa-g") -> str:
    """The mark's inner SVG (512 x 512 space)."""
    if n_bars == 7:
        b = bars(7, 27, 10, 8.3, 7.0, 256, 222)
    else:
        b = bars(5, 40, 13, 8.2, 7.2, 256, 222)
    return (
        f"<defs>{gradient(gid)}</defs>"
        f'<g fill="url(#{gid})" stroke="url(#{gid})" stroke-width="0">{BUBBLE}</g>'
        f'<g fill="{WHITE}">{b}</g>'
    )


def svg(inner: str, view: str = "0 0 512 512", extra: str = "") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}"{extra}>{inner}</svg>\n'


def tile(n_bars: int, full_bleed: bool = False, inset: float = 0.80) -> str:
    """Dark app tile with the mark centred."""
    bg = (
        f'<rect width="512" height="512" fill="{INK}"/>'
        if full_bleed
        else f'<rect width="512" height="512" rx="116" fill="{INK}"/>'
    )
    glow = (
        '<defs><radialGradient id="aa-glow" cx=".5" cy=".42" r=".6">'
        f'<stop offset="0" stop-color="{ROSE}" stop-opacity=".32"/>'
        f'<stop offset="1" stop-color="{ROSE}" stop-opacity="0"/></radialGradient></defs>'
    )
    glow_rect = (
        '<rect width="512" height="512" fill="url(#aa-glow)"/>'
        if full_bleed
        else '<rect width="512" height="512" rx="116" fill="url(#aa-glow)"/>'
    )
    s = inset
    off = 256 * (1 - s)
    return svg(f'{glow}{bg}{glow_rect}<g transform="translate({off:.1f} {off + 8:.1f}) scale({s})">{mark(n_bars)}</g>')


def wordmark() -> str:
    m = f'<g transform="translate(0 -4) scale(0.27)">{mark(7, "aa-w")}</g>'
    text = (
        '<text x="148" y="70" font-family="\'Space Grotesk\', \'Segoe UI\', system-ui, sans-serif" '
        f'font-size="58" font-weight="700" letter-spacing="-1.5" fill="url(#aa-wt)">Apni Awaaz</text>'
        '<text x="150" y="112" font-family="\'Noto Sans Devanagari\', \'Nirmala UI\', \'Mangal\', sans-serif" '
        f'font-size="30" font-weight="600" fill="{VIOLET}">अपनी आवाज़</text>'
    )
    tg = (
        '<defs><linearGradient id="aa-wt" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="{ROSE}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient></defs>'
    )
    return svg(tg + m + text, view="0 0 480 128")


def main() -> None:
    BRAND.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)
    (BRAND / "logo.svg").write_text(svg(mark(7)), encoding="utf-8")
    (BRAND / "logo-small.svg").write_text(svg(mark(5)), encoding="utf-8")
    (BRAND / "wordmark.svg").write_text(wordmark(), encoding="utf-8")
    (ICONS / "mark.svg").write_text(svg(mark(5)), encoding="utf-8")
    (ICONS / "icon.svg").write_text(tile(5), encoding="utf-8")
    (ICONS / "icon-full.svg").write_text(tile(7), encoding="utf-8")
    (ICONS / "icon-maskable.svg").write_text(tile(7, full_bleed=True, inset=0.62), encoding="utf-8")
    print("wrote", BRAND, ICONS)


if __name__ == "__main__":
    main()
