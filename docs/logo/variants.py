#!/usr/bin/env python3
"""Writes the logo variants: picture mark, favicon and picture mark with lettering.

Run from this folder:
    python3 fit.py               # fit the log geometry to original.png         -> fit.json
    python3 plate.py 3           # cut out and retouch the bare-wood surface     -> wood_plate.jpg/.json
    python3 variants.py OUTDIR   # bartusch-logo-bildmarke.svg, bartusch-logo-schriftzug.svg, bartusch-favicon.svg
    python3 overview.py OUTDIR original.png OUT.png   # preview sheet (original vs. new)
The PNG exports were rendered with rsvg-convert (1600 px / 2400 px wide), favicon.ico with Pillow
from rsvg-convert renders at 16, 32, 48 and 256 px. gen.py holds the drawing itself.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontTools.pens.svgPathPen import SVGPathPen  # noqa: E402
from fontTools.pens.transformPen import TransformPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

import gen  # noqa: E402

FONT_BOLD = "/usr/share/fonts/TTF/OpenSans-Bold.ttf"
FONT_SEMI = "/usr/share/fonts/TTF/OpenSans-SemiBold.ttf"
COLOR_NAME = "#4a3728"     # dark walnut, header colour of the website
COLOR_TAGLINE = "#8b5e3c"  # wood brown, link colour of the website


class Font:
    def __init__(self, path):
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f["head"].unitsPerEm
        self.cap = self.f["OS/2"].sCapHeight

    def width(self, text, size, tracking=0.0):
        s = size / self.upm
        w = sum(self.gs[self.cmap[ord(c)]].width * s for c in text)
        return w + tracking * (len(text) - 1)

    def path(self, text, size, x, y, tracking=0.0):
        s = size / self.upm
        pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
        cx = 0.0
        for c in text:
            g = self.gs[self.cmap[ord(c)]]
            g.draw(TransformPen(pen, (s, 0, 0, -s, x + cx, y)))
            cx += g.width * s + tracking
        return pen.getCommands()


def mark(detail=True, icon=False):
    s = gen.build(detail=detail, icon=icon)
    x0, y0, x1, y1 = s.bbox()
    pad = 6
    return s, (x0 - pad, y0 - pad, x1 + pad, y1 + pad)


def svg_doc(w, h, defs, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.1f} {h:.1f}" '
            f'width="{w:.0f}" height="{h:.0f}"><title>{title}</title>'
            f'<defs>{defs}</defs>{body}</svg>\n')


def write_mark(fn):
    s, (x0, y0, x1, y1) = mark()
    w, h = x1 - x0, y1 - y0
    body = f'<g transform="translate({-x0:.1f} {-y0:.1f})">{"".join(s.body)}</g>'
    open(fn, "w").write(svg_doc(w, h, "".join(s.defs), body, "Bartusch Holz und Handwerk"))
    return w, h


def write_favicon(fn):
    s, (x0, y0, x1, y1) = mark(detail=False, icon=True)
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    body = f'<g transform="translate({side / 2 - cx:.1f} {side / 2 - cy:.1f})">{"".join(s.body)}</g>'
    open(fn, "w").write(svg_doc(side, side, "".join(s.defs), body, "Bartusch Holz und Handwerk"))


def write_lettering(fn):
    s, (x0, y0, x1, y1) = mark()
    mw, mh = x1 - x0, y1 - y0
    bold, semi = Font(FONT_BOLD), Font(FONT_SEMI)

    name, tag = "Bartusch", "Holz und Handwerk"
    name_size = 168.0
    name_w = bold.width(name, name_size)
    # tagline: natural width about 92 % of the name, the rest is letter spacing
    tag_size = 0.92 * name_w / semi.width(tag, 1.0)
    tag_track = (name_w - semi.width(tag, tag_size)) / (len(tag) - 1)

    name_cap = bold.cap / bold.upm * name_size
    tag_cap = semi.cap / semi.upm * tag_size
    gap = 0.30 * name_cap
    block_h = name_cap + gap + tag_cap
    tx = mw + 0.14 * mh
    top = (mh - block_h) / 2
    name_base = top + name_cap
    tag_base = name_base + gap + tag_cap

    d_name = bold.path(name, name_size, tx, name_base)
    d_tag = semi.path(tag, tag_size, tx, tag_base, tag_track)
    w = tx + name_w + 8
    body = (f'<g transform="translate({-x0:.1f} {-y0:.1f})">{"".join(s.body)}</g>'
            f'<path d="{d_name}" fill="{COLOR_NAME}"/>'
            f'<path d="{d_tag}" fill="{COLOR_TAGLINE}"/>')
    open(fn, "w").write(svg_doc(w, mh, "".join(s.defs), body, "Bartusch Holz und Handwerk"))
    return w, mh, tag_size, tag_track


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    print("bildmarke", write_mark(os.path.join(out, "bartusch-logo-bildmarke.svg")))
    write_favicon(os.path.join(out, "bartusch-favicon.svg"))
    print("schriftzug", write_lettering(os.path.join(out, "bartusch-logo-schriftzug.svg")))
