"""Builds the profile quote as a dot-matrix SVG. Run: python3 assets/gen.py  (needs Pillow).

The font is fetched once from google/fonts into assets/.fonts (gitignored).
Every dot is a zero-length round-capped stroke (`M x y h0`), ~12 bytes each.
"""

import random
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONT = HERE / ".fonts" / "manrope.ttf"
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/manrope/Manrope%5Bwght%5D.ttf"

THEMES = {
    "dark": dict(field="#21262d", lit="#2AABEE", off="#3d444d"),
    "light": dict(field="#e6eaef", lit="#1D93D2", off="#cdd5de"),
}

LINES = [
    "Человек формирует робототехнику",
    "по своему образу и подобию,",
    "стремясь отразить себя",
    "в искусственном.",
    "В своём желании творить",
    "он приближается к замене себя,",
    "стирая границы между ними.",
]

W, P, X0, Y0 = 1200, 5, 36, 30  # canvas width, dot pitch, margins
EM = 12  # font size in dots
LEAD = 17  # line advance in dots
R = 1.9  # dot radius


def dots(text, font):
    """Rasterise one line at 10x and sample it onto the dot grid."""
    k = 10
    l, t, r, b = font.getbbox(text)
    img = Image.new("L", (r + k * 2, EM * k * 2), 0)
    ImageDraw.Draw(img).text((0, 0), text, font=font, fill=255)
    cols, rows = img.width // k, img.height // k
    small = img.resize((cols, rows), Image.BOX)
    return [(x, y) for y in range(rows) for x in range(cols) if small.getpixel((x, y)) > 105]


def build(c):
    if not FONT.exists():
        FONT.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(FONT_URL, FONT)
    font = ImageFont.truetype(str(FONT), EM * 10)
    font.set_variation_by_axes([600])
    rnd = random.Random(7)
    H = Y0 * 2 + LEAD * P * len(LINES)
    style = [
        ".l{animation:type 1.1s steps(40,end) both}",
        "@keyframes type{from{clip-path:inset(0 100% 0 0)}to{clip-path:inset(0 0 0 0)}}",
        ".f{animation:blink 6s ease-in-out infinite}",
        "@keyframes blink{0%,70%,100%{opacity:1}82%{opacity:.1}}",
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}}",
    ]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f"<style>{''.join(style)}</style>",
           f'<defs><pattern id="g" width="{P}" height="{P}" patternUnits="userSpaceOnUse">'
           f'<circle cx="{P / 2}" cy="{P / 2}" r=".9" fill="{c["field"]}"/></pattern></defs>',
           f'<rect width="{W}" height="{H}" fill="url(#g)"/>',
           f'<g stroke-linecap="round" stroke-width="{R * 2}">']
    for i, line in enumerate(LINES):
        lit, off, flick = [], [], []
        for x, y in dots(line, font):
            cx, cy = X0 + x * P + P / 2, Y0 + (i * LEAD + y) * P + P / 2
            if cx > W - X0:
                raise SystemExit(f"line too wide: {line!r}")
            roll = rnd.random()
            (off if roll < 0.03 else flick if roll < 0.045 else lit).append(f"M{cx:g} {cy:g}h0")
        out.append(f'<g class="l" style="animation-delay:{i * 0.9:.1f}s">'
                   f'<path stroke="{c["lit"]}" d="{"".join(lit)}"/>'
                   f'<path stroke="{c["off"]}" d="{"".join(off)}"/>'
                   # a few accounts blinking online/offline, revealed with their line
                   + "".join(f'<path class="f" style="animation-delay:{7 + rnd.random() * 8:.1f}s" stroke="{c["lit"]}" d="{d}"/>' for d in flick)
                   + "</g>")
    out.append("</g></svg>")
    return "\n".join(out)


if __name__ == "__main__":
    for theme, c in THEMES.items():
        (HERE / f"quote-{theme}.svg").write_text(build(c))
