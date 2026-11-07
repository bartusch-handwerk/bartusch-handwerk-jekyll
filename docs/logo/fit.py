#!/usr/bin/env python3
"""Fit the log geometry (origin, radii, length, bark length) to the edges of the original image."""
import json
import math

import numpy as np
from PIL import Image
from scipy.optimize import least_squares

XS = np.array((0.992, 0.373))
YS = np.array((0.0, -1.0))
ZS = np.array((-0.675, 0.548))
_pl = math.hypot(*XS)
PERP = np.array((-XS[1] / _pl, XS[0] / _pl))
TB = math.degrees(math.atan2(ZS @ PERP, YS @ PERP))
TT = TB - 180.0

im = np.asarray(Image.open("original.png").convert("RGB")).astype(int)
r, g, b = im[..., 0], im[..., 1], im[..., 2]
mx, mn = im.max(-1), im.min(-1)
white = mn > 235
wood = (r > g * 1.45) & (r > 45) & (r - b > 25) & ~white
dark = mx < 45
bark = (g >= r * 0.8) & (g > b * 1.15) & (r < 235) & ~white & ~wood
H, W = white.shape

obs = {"top": [], "bottom": [], "left": [], "boundary": [], "face": []}
for x in range(150, 330):
    col = ~white[:, x]
    ys = np.nonzero(col[:200])[0]
    if len(ys):
        obs["top"].append((x, ys[0]))
for x in range(110, 320):
    ys = np.nonzero(~white[:, x])[0]
    if len(ys):
        obs["bottom"].append((x, ys[-1]))
for y in range(90, 300):
    xs = np.nonzero(~white[y, :200])[0]
    if len(xs):
        obs["left"].append((xs[0], y))
for y in range(105, 290):
    row_b, row_w = bark[y], wood[y] | dark[y]
    xs = np.nonzero(row_b[60:260])[0]
    if not len(xs):
        continue
    # last bark pixel that is followed by 8 consecutive wood/dark pixels
    for x in range(60, 260):
        if row_b[x] and row_w[x + 1:x + 9].all():
            obs["boundary"].append((x + 1, y))
            break
for y in range(185, 335):
    for x in range(270, 380):
        if wood[y, x - 3:x].all() and dark[y, x:x + 6].all():
            obs["face"].append((x, y))
            break
obs = {k: np.array(v, float) for k, v in obs.items()}
print({k: len(v) for k, v in obs.items()})


def model(p):
    ox, oy, r0, r1, length, xb = p
    o = np.array((ox, oy))

    def rad(x):
        return r0 + (r1 - r0) * x / length

    def pt(x, th):
        t = np.radians(th)
        rr = rad(x)
        return o + x * XS + rr * np.cos(t)[..., None] * YS + rr * np.sin(t)[..., None] * ZS

    xs = np.linspace(0, length, 200)
    ths = np.linspace(TT, TB, 200)
    return {
        "top": np.array([pt(x, np.array(TT)) for x in xs]).reshape(-1, 2),
        "bottom": np.array([pt(x, np.array(TB)) for x in xs]).reshape(-1, 2),
        "left": pt(0.0, ths),
        "boundary": pt(xb, ths),
        "face": pt(length, ths),
    }


def residuals(p):
    m = model(p)
    res = []
    for k, pts in obs.items():
        d = np.sqrt(((pts[:, None, :] - m[k][None, :, :]) ** 2).sum(-1)).min(1)
        res.append(d)
    return np.concatenate(res)


p0 = np.array((121.0, 153.0, 80.0, 80.0, 243.0, 80.0))
fit = least_squares(residuals, p0, loss="soft_l1", f_scale=2.0)
res = residuals(fit.x)
print("params", dict(zip(("ox", "oy", "r0", "r1", "L", "xb"), np.round(fit.x, 2))))
print("mean residual %.2f px, 90%% %.2f px" % (res.mean(), np.percentile(res, 90)))
for k in obs:
    m = model(fit.x)[k]
    d = np.sqrt(((obs[k][:, None, :] - m[None, :, :]) ** 2).sum(-1)).min(1)
    print(f"  {k:9s} mean {d.mean():5.2f}  max {d.max():5.2f}")
json.dump(dict(zip(("ox", "oy", "r0", "r1", "L", "xb"), map(float, fit.x))), open("fit.json", "w"), indent=1)

# visual check
vis = Image.open("original.png").convert("RGB")
from PIL import ImageDraw  # noqa: E402
dr = ImageDraw.Draw(vis)
m = model(fit.x)
for k, col in (("top", "blue"), ("bottom", "blue"), ("left", "blue"), ("boundary", "cyan"), ("face", "magenta")):
    dr.line([tuple(p) for p in m[k]], fill=col, width=1)
for k, pts in obs.items():
    for x, y in pts[::3]:
        dr.point((x, y), fill="yellow")
vis.resize((1280, 960), Image.NEAREST).save("/dev/shm/fit.png")
