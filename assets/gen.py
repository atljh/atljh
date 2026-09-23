"""Builds the profile SVGs. Run: python3 assets/gen.py  (needs Pillow + fonttools).

Fonts are fetched once from google/fonts into assets/.fonts (gitignored),
subset to the glyphs actually used and embedded as base64 WOFF — GitHub
serves README images through a proxy that blocks external font requests.
"""

import base64
import io
import random
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
FONTS = HERE / ".fonts"
GF = "https://github.com/google/fonts/raw/main/ofl/"
SRC = {
    "unbounded": "unbounded/Unbounded%5Bwght%5D.ttf",
    "manrope": "manrope/Manrope%5Bwght%5D.ttf",
    "serif": "ptserif/PT_Serif-Web-Italic.ttf",
}

THEMES = {
    "dark": dict(field="#21262d", lit="#2AABEE", off="#3d444d", text="#e6edf3",
                 muted="#9198a1", border="#30363d", quote="#c9d1d9"),
    "light": dict(field="#e6eaef", lit="#1D93D2", off="#cdd5de", text="#1f2328",
                  muted="#59636e", border="#d1d9e0", quote="#31363c"),
}




def font_path(key):
    p = FONTS / f"{key}.ttf"
    if not p.exists():
        FONTS.mkdir(exist_ok=True)
        urllib.request.urlretrieve(GF + SRC[key], p)
    return p


def pil_font(key, size, wght=None):
    f = ImageFont.truetype(str(font_path(key)), size)
    if wght:
        f.set_variation_by_axes([wght])
    return f


def embed(key, text, wght=None):
    """@font-face with a base64 WOFF holding only the glyphs of `text`."""
    tt = TTFont(font_path(key))
    if wght and "fvar" in tt:
        tt = instancer.instantiateVariableFont(tt, {"wght": wght})
    opts = subset.Options()
    opts.flavor = "woff"
    opts.layout_features = ["kern", "liga"]
    s = subset.Subsetter(opts)
    s.populate(text=text)
    s.subset(tt)
    buf = io.BytesIO()
    tt.flavor = "woff"
    tt.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    name = f"pp-{key}{wght or ''}"  # never a generic keyword like `serif`
    return name, f"@font-face{{font-family:{name};src:url(data:font/woff;base64,{b64}) format('woff')}}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace("'", "&#39;")


def dotmatrix(text, cols):
    """Rasterise `text` in Unbounded Black and sample it onto a dot grid."""
    f = pil_font("unbounded", 400, 850)
    gap = 40  # letters touch at dot resolution without extra tracking
    _, t, _, b = f.getbbox(text)
    width = sum(f.getlength(ch) for ch in text) + gap * (len(text) - 1)
    img = Image.new("L", (int(width) + 40, b - t + 40), 0)
    d, x = ImageDraw.Draw(img), 20
    for ch in text:
        d.text((x, 20 - t), ch, font=f, fill=255)
        x += f.getlength(ch) + gap
    img = img.crop(img.getbbox())
    cell = img.width / cols
    rows = round(img.height / cell)
    small = img.resize((cols, rows), Image.BOX)
    return [(x, y) for y in range(rows) for x in range(cols) if small.getpixel((x, y)) > 140], rows


MOTION = """
.d{animation:on .6s cubic-bezier(.2,.7,.2,1) both;transform-box:fill-box;transform-origin:center}
.p{animation:on .6s cubic-bezier(.2,.7,.2,1) both,blink 6s ease-in-out infinite}
@keyframes on{from{opacity:0;transform:scale(.2)}}
@keyframes blink{0%,70%,100%{opacity:1}82%{opacity:.15}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def banner(c):
    W, H, P, X0, Y0 = 1200, 430, 12, 48, 48
    dots, rows = dotmatrix("atljh", 80)
    rnd = random.Random(7)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f"<style>{MOTION}</style>",
           f'<defs><pattern id="f" width="{P}" height="{P}" patternUnits="userSpaceOnUse">'
           f'<circle cx="{P/2}" cy="{P/2}" r="1.3" fill="{c["field"]}"/></pattern>'
           f'<linearGradient id="g" x2="1"><stop offset=".35" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
           f'<mask id="m"><rect width="{W}" height="{H}" fill="url(#g)"/></mask></defs>',
           f'<rect width="{W}" height="{rows * P + Y0 + 24}" fill="url(#f)" mask="url(#m)"/>']
    for x, y in dots:
        cx, cy = X0 + x * P + P / 2, Y0 + y * P + P / 2
        delay = x * 0.022 + rnd.random() * 0.12
        roll = rnd.random()
        if roll < 0.035:  # an account that went offline
            out.append(f'<circle class="d" style="animation-delay:{delay:.2f}s" cx="{cx}" cy="{cy}" r="4.3" fill="{c["off"]}"/>')
        elif roll < 0.07:  # ...and a few flickering ones
            out.append(f'<circle class="p" style="animation-delay:{delay:.2f}s,{2 + rnd.random() * 6:.1f}s" cx="{cx}" cy="{cy}" r="4.3" fill="{c["lit"]}"/>')
        else:
            out.append(f'<circle class="d" style="animation-delay:{delay:.2f}s" cx="{cx}" cy="{cy}" r="4.3" fill="{c["lit"]}"/>')
    out.append("</svg>")
    return "\n".join(out), Y0 + rows * P + 24


def quote(c, lines, link=None):
    """Serif lines behind a blue rule; `link` (a word in them) is painted blue."""
    W, size, lh = 1200, 30, 46
    fq, css = embed("serif", "".join(lines))
    H = len(lines) * lh + 28
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
           f"<style>{css}</style>",
           f'<rect x="48" y="6" width="3" height="{H - 12}" fill="{c["lit"]}"/>']
    for i, l in enumerate(lines):
        l = esc(l)
        if link:
            l = l.replace(link, f'<tspan fill="{c["lit"]}">{link}</tspan>')
        out.append(f'<text x="78" y="{40 + i * lh}" font-family="{fq}" font-size="{size}" fill="{c["quote"]}">{l}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    for theme, c in THEMES.items():
        svg, h = banner(c)
        (HERE / f"banner-{theme}.svg").write_text(svg.replace('height="430"', f'height="{h}"').replace("0 0 1200 430", f"0 0 1200 {h}"))
        (HERE / f"now-{theme}.svg").write_text(quote(c, ["Now building GramGPT"], link="GramGPT"))


if __name__ == "__main__":
    main()
