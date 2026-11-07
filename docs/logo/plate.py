#!/usr/bin/env python3
"""Cut the bare-wood surface out of the original image, retouch saw and kerf, write wood_plate.png."""
import json
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

fit = json.load(open("fit.json"))
XS = np.array((0.992, 0.373))
YS = np.array((0.0, -1.0))
ZS = np.array((-0.675, 0.548))
_pl = math.hypot(*XS)
PERP = np.array((-XS[1] / _pl, XS[0] / _pl))
TB = math.degrees(math.atan2(ZS @ PERP, YS @ PERP))
TT = TB - 180.0
O = np.array((fit["ox"], fit["oy"]))
R = (fit["r0"] + fit["r1"]) / 2
L, XB = fit["L"], fit["xb"]


def E(x, th, r=R):
    t = math.radians(th)
    return O + x * XS + r * math.cos(t) * YS + r * math.sin(t) * ZS


def arc(x, a0, a1, n=90, r=R):
    return [tuple(E(x, a0 + (a1 - a0) * i / n, r)) for i in range(n + 1)]


im = Image.open("original.png").convert("RGB")
a = np.asarray(im).astype(float)
Hh, Ww = a.shape[:2]

# visible bare-wood surface: between bark boundary and end face, inset a little
surface = arc(L, TT, TT - 180) + arc(XB, TB, TT)
m = Image.new("L", (Ww, Hh), 0)
ImageDraw.Draw(m).polygon(surface, fill=255)
ImageDraw.Draw(m).polygon(arc(L, 0, 360), fill=0)
valid = ndimage.binary_erosion(np.asarray(m) > 0, iterations=4)

# old saw (blade, handle, ferrule) and old kerf line
r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
mx, mn = a.max(-1), a.min(-1)
box = np.zeros_like(valid)
box[200:280, 215:320] = True
grey = (mx - mn < 30) & (mn > 110)
handle = (r_ > 150) & (g_ > 90) & (b_ > 60) & (r_ - b_ < 140)
saw = ndimage.binary_dilation((grey | handle) & box, iterations=5)
saw = ndimage.binary_closing(saw, iterations=3)
kerf = np.zeros_like(valid)
kd = ImageDraw.Draw(Image.fromarray(np.zeros((Hh, Ww), np.uint8)))
ki = Image.new("L", (Ww, Hh), 0)
ImageDraw.Draw(ki).line([tuple(E(XB + (L - XB) * 0.80, 50)), tuple(E(L + 4, 50))], fill=255, width=7)
kerf = np.asarray(ki) > 0
# only pixels that really are wood: no background, no anti-aliased silhouette, no bark
light = mn > 120
barkish = (g_ >= r_ * 0.8) & (g_ > b_ * 1.15)
valid &= ~(ndimage.binary_dilation(light | barkish, iterations=2) & ~(saw | kerf))
holes = valid & (saw | kerf)
good = valid & ~holes

# fill holes row by row: clone the texture from the left and blend towards the right edge colour
out = a.copy()
for y in range(Hh):
    row = holes[y]
    if not row.any():
        continue
    xs = np.nonzero(row)[0]
    runs = np.split(xs, np.nonzero(np.diff(xs) > 1)[0] + 1)
    for run in runs:
        x0, x1 = run[0], run[-1] + 1
        n = x1 - x0
        src0 = x0 - n
        if src0 < 0 or not good[y, src0:x0].all() or x1 >= Ww or not good[y, x1]:
            continue
        # low frequencies: linear blend between the colours left and right of the hole
        left = a[y, max(0, x0 - 4):x0].mean(0)
        right = a[y, x1:min(Ww, x1 + 4)].mean(0)
        ramp = np.linspace(0, 1, n + 2)[1:-1, None]
        base = left + ramp * (right - left)
        # high frequencies: grain cloned from the left
        clone = a[y, src0:x0]
        detail = clone - ndimage.uniform_filter1d(clone, size=9, axis=0, mode="nearest")
        out[y, x0:x1] = base + 0.8 * detail
        good[y, x0:x1] = True
sm = ndimage.uniform_filter1d(out, size=3, axis=0, mode="nearest")
out[holes] = sm[holes]
# remove isolated GIF dither specks
med = ndimage.median_filter(out, size=(3, 3, 1))
speck = good & (np.abs(out - med).sum(-1) > 70)
out[speck] = med[speck]
# continue the surface smoothly beyond the good area (normalized convolution), far away: nearest
w = good.astype(float)
ext = out.copy()
filled = good.copy()
for sigma in (2.0, 4.0, 8.0):
    num = np.stack([ndimage.gaussian_filter(out[..., c] * w, sigma) for c in range(3)], -1)
    den = ndimage.gaussian_filter(w, sigma)
    ok = (den > 0.05) & ~filled
    ext[ok] = num[ok] / den[ok, None]
    filled |= ok
out = ext
idx = ndimage.distance_transform_edt(~filled, return_distances=False, return_indices=True)
out = out[idx[0], idx[1]]

# soften the old GIF dithering a little, crop to the wood area and upscale
xs = [p[0] for p in surface]
ys = [p[1] for p in surface]
pad = 6
bx0, by0 = int(min(xs)) - pad, int(min(ys)) - pad
bx1, by1 = int(math.ceil(max(xs))) + pad, int(math.ceil(max(ys))) + pad
plate = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).crop((bx0, by0, bx1, by1))
plate = plate.filter(ImageFilter.GaussianBlur(0.7))
scale = int(sys.argv[1]) if len(sys.argv) > 1 else 3
plate = plate.resize((plate.width * scale, plate.height * scale), Image.LANCZOS)
plate.save("wood_plate.jpg", quality=92)
json.dump({"x": bx0, "y": by0, "w": bx1 - bx0, "h": by1 - by0}, open("wood_plate.json", "w"))

dbg = np.asarray(im).copy()
dbg[holes] = (0, 160, 255)
Image.fromarray(dbg).crop((bx0, by0, bx1, by1)).resize(((bx1 - bx0) * 2, (by1 - by0) * 2), Image.NEAREST).save(
    "/dev/shm/plate_holes.png")
print("plate", plate.size, "box", (bx0, by0, bx1, by1), "holes", int(holes.sum()))
