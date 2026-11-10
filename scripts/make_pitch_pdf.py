"""Make PITCH.pdf (A4, exactly one page, logo at the top, clickable links) from PITCH.md.

Run from the repo root:
    uv run --no-project --with markdown --with pypdf python scripts/make_pitch_pdf.py

Renders the Markdown to HTML, prints it with headless Chrome, and shrinks the
font in 0.2 pt steps until the PDF is one page. Set CHROME to override the
Chrome path.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "PITCH.md"
OUT = ROOT / "PITCH.pdf"
LOGO = ROOT / "docs" / "brand" / "logo.svg"
REPO = "https://github.com/nitya-prakash-pandey-2005/apni-awaaz"
CHROME = os.environ.get("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")

CSS = """
@page { size: A4; margin: 11mm 13mm; }
* { box-sizing: border-box; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { margin: 0; font-family: 'Segoe UI', 'Nirmala UI', system-ui, sans-serif; font-size: %(fs).1fpt;
       line-height: 1.38; color: #1d1a2b; }
.head { display: flex; align-items: center; gap: 12px; padding-bottom: 7px; margin-bottom: 7px;
        border-bottom: 2.5px solid transparent;
        border-image: linear-gradient(90deg, #FF8A5B, #F43F7A, #8B5CF6) 1; }
.head svg { width: 50px; height: 50px; flex: none; }
.head h1 { margin: 0; font-size: 1.95em; letter-spacing: -0.02em; line-height: 1.1; }
.head h1 .hi { font-family: 'Nirmala UI', 'Segoe UI', sans-serif; color: #F43F7A; }
.head .tag { color: #6b6585; font-size: 1.02em; margin-top: 2px; }
h2 { font-size: 1.12em; margin: 8px 0 3px; color: #8B5CF6; text-transform: uppercase; letter-spacing: .06em; }
p { margin: 3px 0; }
ul { margin: 3px 0; padding-left: 17px; }
li { margin: 1.5px 0; }
a { color: #C2245E; text-decoration: none; border-bottom: 0.6px solid rgba(194,36,94,.35); }
code { font-family: Consolas, 'Cascadia Code', monospace; font-size: .92em; background: #f3f0fa; padding: 0 3px; border-radius: 3px; }
strong { color: #120f1f; }
em { color: #C2245E; font-style: normal; font-weight: 600; }
"""


def build_html(font_pt: float) -> str:
    md = SRC.read_text(encoding="utf-8")
    body = markdown.markdown(md, extensions=["extra", "sane_lists"])
    # Relative links point at the repository on GitHub, so they still work from the PDF.
    body = re.sub(r'href="(?!https?:|mailto:|#)([^"]+)"', rf'href="{REPO}/blob/main/\1"', body)
    logo = LOGO.read_text(encoding="utf-8")
    m = re.search(r"<h1>(.*?)</h1>", body, re.S)
    if m:
        title = m.group(1)
        main, _, tag = title.partition(":")
        main = main.replace("अपनी आवाज़", '<span class="hi">अपनी आवाज़</span>')
        head = f'<div class="head">{logo}<div><h1>{main}</h1><div class="tag">{tag.strip().capitalize()}.</div></div></div>'
        body = body[: m.start()] + head + body[m.end() :]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Apni Awaaz · one-page pitch</title>'
        f"<style>{CSS % {'fs': font_pt}}</style></head><body>{body}</body></html>"
    )


def render(font_pt: float) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        html = Path(tmp) / "pitch.html"
        html.write_text(build_html(font_pt), encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={OUT}", html.as_uri()],
            check=True, capture_output=True,
        )
    return len(PdfReader(str(OUT)).pages)


def main() -> None:
    font = float(sys.argv[1]) if len(sys.argv) > 1 else 11.0
    while font >= 7.0:
        pages = render(font)
        print(f"{font:.1f} pt -> {pages} page(s)")
        if pages == 1:
            print("wrote", OUT)
            return
        font = round(font - 0.2, 1)
    sys.exit("could not fit PITCH.md on one page")


if __name__ == "__main__":
    main()
