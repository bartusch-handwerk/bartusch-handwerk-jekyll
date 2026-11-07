#!/usr/bin/env python3
"""Builds the overview sheet (original vs. new, lettering, favicon on light/dark tabs)."""
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

d = sys.argv[1]
orig_png, out_png = sys.argv[2], sys.argv[3]


def render(svg, out, w=None, h=None):
    args = ["rsvg-convert"]
    if w:
        args += ["-w", str(w)]
    if h:
        args += ["-h", str(h)]
    subprocess.run(args + [f"{d}/{svg}", "-o", out], check=True)
    return Image.open(out).convert("RGBA")


F = "/usr/share/fonts/TTF/OpenSans-SemiBold.ttf"
lab, small = ImageFont.truetype(F, 22), ImageFont.truetype(F, 16)
W, pad, MH = 1400, 40, 420
orig = Image.open(orig_png).convert("RGBA")
orig = orig.crop(orig.convert("L").point(lambda v: 255 if v < 245 else 0).getbbox())
orig = orig.resize((int(orig.width * MH / orig.height), MH), Image.LANCZOS)
mark = render("bartusch-logo-bildmarke.svg", "/dev/shm/_m.png", h=MH)
word = render("bartusch-logo-schriftzug.svg", "/dev/shm/_w.png", w=W - 2 * pad)
fav = {s: render("bartusch-favicon.svg", f"/dev/shm/_f{s}.png", w=s, h=s) for s in (16, 32, 48, 64)}

rowh = 64 * 3 + 20
H = pad + 34 + MH + pad + 34 + word.height + pad + 34 + 2 * (rowh + 18) + pad
out = Image.new("RGB", (W, H), "white")
dr = ImageDraw.Draw(out)
grey = (110, 100, 90)
y = pad
dr.text((pad, y), "Original (Vorlage)", font=lab, fill=grey)
dr.text((W // 2 + 10, y), "Neu: Bildmarke", font=lab, fill=grey)
y += 34
out.paste(orig, (pad + (W // 2 - pad - orig.width) // 2, y), orig)
out.paste(mark, (W // 2 + 10 + (W // 2 - pad - 10 - mark.width) // 2, y), mark)
y += MH + pad
dr.text((pad, y), "Neu: mit Schriftzug (für Rechnungen)", font=lab, fill=grey)
y += 34
out.paste(word, (pad, y), word)
y += word.height + pad
dr.text((pad, y), "Neu: Favicon (vereinfacht), links Originalgröße, rechts dreifach vergrößert", font=lab, fill=grey)
y += 34
for bg, name in (((241, 243, 244), "helle Tab-Leiste"), ((32, 33, 36), "dunkle Tab-Leiste")):
    dr.rectangle((pad, y, W - pad, y + rowh), fill=bg)
    dr.text((pad + 12, y + 8), name, font=small, fill=(120, 120, 120) if bg[0] > 100 else (170, 170, 170))
    x = pad + 180
    for s, im in fav.items():
        out.paste(im, (x, y + 10 + (rowh - 20 - s) // 2), im)
        x += s + 24
    x += 40
    for s, im in fav.items():
        big = im.resize((s * 3, s * 3), Image.NEAREST)
        out.paste(big, (x, y + 10 + (rowh - 20 - s * 3) // 2), big)
        x += s * 3 + 24
    y += rowh + 18
out.save(out_png)
print(out.size)
