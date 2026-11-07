#!/usr/bin/env python3
"""Generator for the Bartusch logo (log with two-man saw and bench).

Everything is modelled in 3D (X = log axis, Y = up, Z = towards the viewer)
and projected with the parallel projection read off the original render.
"""
import base64
import json
import math
import os
import random
import sys

# ---------------------------------------------------------------- vectors

def norm(v):
    length = math.sqrt(sum(c * c for c in v))
    return tuple(c / length for c in v)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def add(*vs):
    return tuple(sum(c) for c in zip(*vs))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, k):
    return tuple(x * k for x in a)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


# ------------------------------------------------------------- projection
XS = (0.992, 0.373)   # screen vector of one unit along X (log axis)
YS = (0.0, -1.0)      # screen vector of one unit up
ZS = (-0.675, 0.548)  # screen vector of one unit towards the viewer
CAM = norm((0.675, 0.795, 0.992))
LIGHT = norm((-0.40, 0.80, 0.45))
HALF = norm(add(LIGHT, CAM))

ORIGIN = (121.79, 155.98)  # screen position of the left end centre of the log (fitted, see fit.py)


def P(x, y, z):
    return (ORIGIN[0] + x * XS[0] + z * ZS[0], ORIGIN[1] + x * XS[1] - y + z * ZS[1])


_pl = math.hypot(*XS)
PERP = (-XS[1] / _pl, XS[0] / _pl)          # screen unit vector perpendicular to the axis
FY = YS[0] * PERP[0] + YS[1] * PERP[1]
FZ = ZS[0] * PERP[0] + ZS[1] * PERP[1]
TB = math.degrees(math.atan2(FZ, FY))      # silhouette angle, bottom/front
TT = TB - 180.0                            # silhouette angle, top/back
FMAX = math.hypot(FY, FZ)


def foff(th):
    t = math.radians(th)
    return math.cos(t) * FY + math.sin(t) * FZ


def E(x, th, r, yc=0.0, zc=0.0):
    t = math.radians(th)
    return P(x, yc + r * math.cos(t), zc + r * math.sin(t))


def surf_normal(th):
    t = math.radians(th)
    return (0.0, math.cos(t), math.sin(t))


def arc(x, r, a0, a1, yc=0.0, zc=0.0, step=3.0):
    n = max(6, int(abs(a1 - a0) / step))
    return [E(x, a0 + (a1 - a0) * i / n, r, yc, zc) for i in range(n + 1)]


def cyl_outline(x0, x1, r, yc=0.0, zc=0.0):
    """Silhouette of a cylinder segment along X (end x1 visible, end x0 hidden)."""
    return arc(x1, r, TT, TT - 180, yc, zc) + arc(x0, r, TB, TT, yc, zc)


def ellipse(x, r, yc=0.0, zc=0.0):
    return arc(x, r, 0, 360, yc, zc)


# ---------------------------------------------------------------- colours

def shade(alb, n, amb=0.40, kd=0.80, ks=0.0, sp=18):
    n = norm(n)
    lam = max(0.0, dot(n, LIGHT))
    spec = ks * max(0.0, dot(n, HALF)) ** sp
    return tuple(min(255.0, max(0.0, c * (amb + kd * lam) + 255 * spec)) for c in alb)


def hexc(c):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def scale(c, k):
    return tuple(min(255.0, v * k) for v in c)


# ------------------------------------------------------------------- svg

class Svg:
    def __init__(self):
        self.defs = []
        self.body = []
        self.n = 0
        self.pts = []

    def uid(self, p):
        self.n += 1
        return f"{p}{self.n}"

    def d(self, pts, close=True):
        self.pts.extend(pts)
        s = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        return s + ("Z" if close else "")

    def path_str(self, pts, fill="none", close=True, extra=""):
        return f'<path d="{self.d(pts, close)}" fill="{fill}" {extra}/>'

    def path(self, pts, fill="none", close=True, extra="", track=True):
        if not track:
            s = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + ("Z" if close else "")
        else:
            s = self.d(pts, close)
        self.body.append(f'<path d="{s}" fill="{fill}" {extra}/>')

    def lin_grad(self, p1, p2, stops):
        gid = self.uid("g")
        st = "".join(f'<stop offset="{o:.3f}" stop-color="{c}"/>' for o, c in stops)
        self.defs.append(
            f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{p1[0]:.1f}" y1="{p1[1]:.1f}" '
            f'x2="{p2[0]:.1f}" y2="{p2[1]:.1f}">{st}</linearGradient>')
        return f"url(#{gid})"

    def clip(self, pts):
        cid = self.uid("c")
        s = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"
        self.defs.append(f'<clipPath id="{cid}"><path d="{s}"/></clipPath>')
        return cid

    def open_group(self, attrs=""):
        self.body.append(f"<g {attrs}>")

    def close_group(self):
        self.body.append("</g>")

    def bbox(self):
        xs = [p[0] for p in self.pts]
        ys = [p[1] for p in self.pts]
        return min(xs), min(ys), max(xs), max(ys)


def cyl_gradient(svg, xm, r, alb, yc=0.0, zc=0.0, th0=None, th1=None, **kw):
    """Gradient across a cylinder along X; colour depends on the surface angle."""
    c = P(xm, yc, zc)
    p1 = (c[0] - PERP[0] * r * FMAX, c[1] - PERP[1] * r * FMAX)
    p2 = (c[0] + PERP[0] * r * FMAX, c[1] + PERP[1] * r * FMAX)
    stops = []
    for i in range(19):
        th = TT + 180.0 * i / 18
        o = (foff(th) + FMAX) / (2 * FMAX)
        stops.append((o, hexc(shade(alb, surf_normal(th), **kw))))
    return svg.lin_grad(p1, p2, stops)


# ------------------------------------------------------------------ parts
R = 80.33      # wood radius (fitted to the original)
RB = R + 2.0   # bark radius
L = 248.2      # log length (fitted)
XB = 75.55     # bark section length (fitted)
TH_A = 50.0    # saw cut, front edge angle
TH_B = -60.0   # saw cut, back edge angle
XSAW = 218.4   # saw position: blade leaves the log where it does in the original
DIP_FRONT = -3.0

BARK = (174, 160, 94)
BENCH = (205, 155, 95)
STEEL = (205, 210, 214)
HANDLE = (218, 138, 82)
AXIS_ANGLE = math.degrees(math.atan2(XS[1], XS[0]))

# Bark: fractal noise as height map, mottled olive/golden colour, self-shadowing (emboss via offset)
# and a slight darkening towards the bare wood.
BARK_FILTER = (
    '<filter id="{id}" color-interpolation-filters="sRGB">'
    '<feTurbulence type="fractalNoise" baseFrequency="{fx} {fy}" numOctaves="4" seed="4" result="t"/>'
    '<feColorMatrix in="t" type="matrix" values="1 0 0 0 0  1 0 0 0 0  1 0 0 0 0  0 0 0 0 1" result="h"/>'
    '<feColorMatrix in="h" type="matrix" values="1.9 0 0 0 -0.12  1.85 0 0 0 -0.12  1.7 0 0 0 -0.12  0 0 0 0 1" result="g"/>'
    '<feOffset in="h" dx="1.2" dy="1.2" result="hs"/>'
    '<feComposite in="h" in2="hs" operator="arithmetic" k1="0" k2="5" k3="-5" k4="1" result="s"/>'
    '<feTurbulence type="fractalNoise" baseFrequency="0.02 0.03" numOctaves="2" seed="9" result="t2"/>'
    '<feColorMatrix in="t2" type="matrix" values="0.7 0 0 0 0.6  0.35 0 0 0 0.76  0.5 0 0 0 0.6  0 0 0 0 1" result="tint"/>'
    '<feBlend in="SourceGraphic" in2="g" mode="multiply" result="a"/>'
    '<feBlend in="a" in2="s" mode="multiply" result="b"/>'
    '<feBlend in="b" in2="tint" mode="multiply" result="c"/>'
    '<feComposite in="c" in2="SourceAlpha" operator="in"/></filter>')

def filtered(svg, element, filter_def, centre, angle=None):
    """Apply a noise filter in a rotated frame (default: aligned with the log axis)."""
    fid = svg.uid("f")
    svg.defs.append(filter_def.replace("{id}", fid))
    cx, cy = centre
    a = AXIS_ANGLE if angle is None else angle
    svg.body.append(f'<g transform="rotate({a:.2f} {cx:.1f} {cy:.1f})"><g filter="url(#{fid})">'
                    f'<g transform="rotate({-a:.2f} {cx:.1f} {cy:.1f})">{element}</g></g></g>')


def bark_outline(rnd, rough=True):
    j = (lambda a: rnd.uniform(-a, a)) if rough else (lambda a: 0.0)
    pts = arc(XB, RB, TT, TT - 180)
    n = 18
    pts += [E(XB - XB * i / n, TB, RB + j(0.7)) for i in range(1, n + 1)]
    m = 45
    pts += [E(0, TB - 180.0 * i / m, RB + j(0.7)) for i in range(1, m + 1)]
    pts += [E(XB * i / n, TT, RB + j(0.7)) for i in range(1, n)]
    return pts


def draw_bark(svg, rnd, detail=True, icon=False):
    outline = bark_outline(rnd, rough=detail and not icon)
    el = svg.path_str(outline, cyl_gradient(svg, XB / 2, RB, BARK, amb=0.40, kd=0.85, ks=0.05, sp=10))
    if detail or icon:
        fx, fy = (0.045, 0.07) if icon else (0.07, 0.11)
        filtered(svg, el, BARK_FILTER.replace("{fx}", str(fx)).replace("{fy}", str(fy)), P(XB / 2, 0, 0))
    else:
        svg.body.append(el)
    a, b = P(-RB * 0.5, 0, 0), P(XB, 0, 0)
    gid = svg.uid("g")
    svg.defs.append(
        f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{a[0]:.1f}" y1="{a[1]:.1f}" '
        f'x2="{b[0]:.1f}" y2="{b[1]:.1f}"><stop offset="0.35" stop-color="#1a1405" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#1a1405" stop-opacity="0.35"/></linearGradient>')
    svg.path(outline, f"url(#{gid})", track=False)
    # bark ring visible at the step down to the bare wood
    ring = ellipse(XB, RB) + ellipse(XB, R)[::-1]
    svg.path(ring, hexc(shade((120, 70, 35), (1, 0, 0), amb=0.55)), extra='fill-rule="evenodd"')


HERE = os.path.dirname(os.path.abspath(__file__))


def draw_wood(svg, rnd, detail=True, icon=False):
    """Bare wood: surface of the original render, cut out and retouched by plate.py."""
    outline = cyl_outline(XB, L, R)
    meta = json.load(open(os.path.join(HERE, "wood_plate.json")))
    data = base64.b64encode(open(os.path.join(HERE, "wood_plate.jpg"), "rb").read()).decode()
    cid = svg.clip(outline)
    svg.d(outline)
    svg.body.append(f'<image href="data:image/jpeg;base64,{data}" x="{meta['x']}" y="{meta['y']}" '
                    f'width="{meta['w']}" height="{meta['h']}" preserveAspectRatio="none" '
                    f'clip-path="url(#{cid})"/>')


def draw_end_face(svg):
    c = P(L, 0, 0)
    svg.path(ellipse(L, R), svg.lin_grad(add(c, (-55, 45)), add(c, (45, -55)),
                                        [(0, "#4a1a0a"), (0.35, "#2a0d05"), (1, "#100403")]))
    # saw cut across the end face
    svg.path([E(L, TH_A, R), E(L, TH_B, R)], "none", close=False,
             extra='stroke="#5e2812" stroke-width="1.1"')


def teeth(p_from, p_to, size, pitch):
    """Saw teeth along the -X edge from p_from to p_to (3D)."""
    v = sub(p_to, p_from)
    ln = math.sqrt(dot(v, v))
    u = mul(v, 1 / ln)
    n = int(ln / pitch)
    pts = []
    for i in range(n):
        base = add(p_from, mul(u, i * pitch))
        tip = add(p_from, mul(u, (i + 0.35) * pitch), (-size, 0, 0))
        pts += [base, tip]
    return pts


def dip(d, deg):
    """Tilt direction d downwards by deg degrees (the blade bows like in the original)."""
    t = math.radians(deg)
    return norm(add(mul(d, math.cos(t)), (0, -math.sin(t), 0)))


SAW_A = (XSAW, R * math.cos(math.radians(TH_A)), R * math.sin(math.radians(TH_A)))
# The saw stands slightly skewed to the log (back end 10 units further left), like in the original.
SAW_B = (XSAW - 10.0, R * math.cos(math.radians(-50.0)), R * math.sin(math.radians(-50.0)))
SAW_D = norm(sub(SAW_B, SAW_A))
SAW_BOT = add(SAW_A, mul(dip(mul(SAW_D, -1), DIP_FRONT), 72))
SAW_TOP = add(SAW_B, mul(dip(SAW_D, 10.0), 76))
BLADE_W = 15.0


def draw_blade(svg, start, end, detail=True, icon=False):
    """Blade from the point where it leaves the log (start) to the handle (end)."""
    w = 22.0 if icon else BLADE_W
    wt = 10.0 if icon else 7.0
    v = sub(end, start)
    ln = math.sqrt(dot(v, v))
    u = mul(v, 1 / ln)
    mid = add(start, mul(u, ln - 12))

    def hx(k):
        return (k / 2, 0, 0)

    ls, lm, le = sub(start, hx(w)), sub(mid, hx(w)), sub(end, hx(wt))
    rs, rm, re_ = add(start, hx(w)), add(mid, hx(w)), add(end, hx(wt))
    left = teeth(ls, lm, 4.2, 5.6) if (detail and not icon) else [ls]
    pts3 = left + [lm, le, re_, rm, rs]
    col = shade(STEEL, (0, 1, 0), amb=0.55, kd=0.45, ks=0.25, sp=8)
    svg.path([P(*q) for q in pts3],
             svg.lin_grad(P(*ls), P(*rs), [(0, hexc(scale(col, 0.85))), (0.5, hexc(scale(col, 1.08))),
                                           (1, hexc(scale(col, 0.92)))]),
             extra='stroke="#8d949a" stroke-width="0.5" stroke-linejoin="round"')


def draw_handle(svg, centre, icon=False):
    """T-handle along X with rounded ends and a small metal ferrule in the middle."""
    x, y, z = centre
    r = 6.5 if icon else 4.3
    half, fl = 22.0, 4.0
    grad = cyl_gradient(svg, x, r, HANDLE, y, z, amb=0.45, kd=0.75, ks=0.30, sp=10)
    rr = FMAX * r

    def cap(xx):
        c = P(xx, y, z)
        svg.pts.extend([(c[0] - rr, c[1] - rr), (c[0] + rr, c[1] + rr)])
        svg.body.append(f'<circle cx="{c[0]:.1f}" cy="{c[1]:.1f}" r="{rr:.2f}" fill="{grad}"/>')

    cap(x - half)
    svg.path(cyl_outline(x - half, x - fl, r, y, z), grad)
    fr = r + 0.5
    svg.path(cyl_outline(x - fl, x + fl, fr, y, z),
             cyl_gradient(svg, x, fr, (222, 224, 228), y, z, amb=0.55, kd=0.5, ks=0.45, sp=10))
    svg.path(cyl_outline(x + fl, x + half, r, y, z), grad)
    cap(x + half)


def draw_kerf(svg):
    pts = [E(x, TH_A, R) for x in (XSAW + BLADE_W / 2, L)]
    svg.path(pts, "none", close=False, extra='stroke="#2a0b04" stroke-width="1.3" stroke-linecap="round"')


# ------------------------------------------------------------------ bench

def box(svg, rnd, o, e1, e2, e3, alb, detail=True):
    faces = []
    for a, b, c in ((e1, e2, e3), (e2, e3, e1), (e3, e1, e2)):
        nn = norm(cross(a, b))
        if dot(nn, c) < 0:
            nn = mul(nn, -1)
        if dot(nn, CAM) > 0:
            base, n = add(o, c), nn
        else:
            base, n = o, mul(nn, -1)
        if dot(n, CAM) <= 0:
            continue
        faces.append((base, a, b, n))
    for base, a, b, n in faces:
        quad = [base, add(base, a), add(base, a, b), add(base, b)]
        col = shade(alb, n, amb=0.45, kd=0.75)
        svg.path([P(*q) for q in quad], hexc(col),
                 extra=f'stroke="{hexc(col)}" stroke-width="0.35" stroke-linejoin="round"')
        if detail:
            la, lb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))
            long_, short = (a, b) if la >= lb else (b, a)
            if max(la, lb) > 25:
                for _ in range(rnd.randint(2, 4)):
                    f = rnd.uniform(0.12, 0.88)
                    s0 = rnd.uniform(0.0, 0.25)
                    s1 = rnd.uniform(0.6, 1.0)
                    seg = []
                    for i in range(9):
                        t = s0 + (s1 - s0) * i / 8
                        ff = f + 0.06 * math.sin(t * rnd.uniform(4, 9))
                        seg.append(P(*add(base, mul(long_, t), mul(short, min(0.97, max(0.03, ff))))))
                    svg.path(seg, "none", close=False, track=False,
                             extra=f'stroke="{hexc(scale(col, 0.72))}" stroke-width="0.6" stroke-opacity="0.55"')


def plank_yz(svg, rnd, x0, x1, p0, p1, w, alb=BENCH, detail=True):
    dy, dz = p1[0] - p0[0], p1[1] - p0[1]
    ln = math.hypot(dy, dz)
    py, pz = -dz / ln, dy / ln
    o = (L + x0, p0[0] - py * w / 2, p0[1] - pz * w / 2)
    box(svg, rnd, o, (x1 - x0, 0, 0), (0, dy, dz), (0, py * w, pz * w), alb, detail)


def draw_bench(svg, rnd, detail=True, icon=False):
    g = -R          # ground level
    seat_y = -6.0
    blen = 158.0    # bench length
    fx0, fx1 = blen - 12, blen - 2   # right side frame
    # backrest geometry (in the Y/Z plane)
    b0 = (seat_y, -6.0)
    b1 = (72.0, -40.0)
    bl = math.hypot(b1[0] - b0[0], b1[1] - b0[1])
    bu = ((b1[0] - b0[0]) / bl, (b1[1] - b0[1]) / bl)
    bn = (-bu[1], bu[0])      # normal towards the front
    if bn[1] < 0:
        bn = (-bn[0], -bn[1])

    def bp(s, t=0.0):
        return (b0[0] + bu[0] * s + bn[0] * t, b0[1] + bu[1] * s + bn[1] * t)

    # posts behind the backrest slats
    plank_yz(svg, rnd, 0, 8, bp(-6, 0), bp(70, 0), 8, detail=detail)
    plank_yz(svg, rnd, fx0, fx1, bp(-6, 0), bp(16 + 2 * 21 + 18, 0), 8, detail=detail)
    # backrest slats
    slats = [(14, 30), (42, 62)] if icon else [(16 + k * 21, 30 + k * 21) for k in range(3)]
    for s, s_end in slats:
        p0 = bp(s, 4.0)
        p1 = bp(s_end, 4.0)
        o = (L + 0, p0[0], p0[1])
        box(svg, rnd, o, (blen, 0, 0), (0, p1[0] - p0[0], p1[1] - p0[1]),
            (0, bn[0] * 5, bn[1] * 5), BENCH, detail)
    # rear leg (right) and seat rail
    plank_yz(svg, rnd, fx0, fx1, (g, -28), (seat_y - 8, -6), 8, detail=detail)
    box(svg, rnd, (L + fx0, seat_y - 15, -8), (fx1 - fx0, 0, 0), (0, 9, 0), (0, 0, 76), BENCH, detail)
    # seat slats, back to front
    for z0, dz in ([(-6, 32), (32, 32)] if icon else [(-6 + k * 18, 14) for k in range(4)]):
        box(svg, rnd, (L + 0, seat_y - 6, z0), (blen, 0, 0), (0, 6, 0), (0, 0, dz), BENCH, detail)
    # front leg (right) and armrest
    plank_yz(svg, rnd, fx0, fx1, (g, 76), (24, 62), 8, detail=detail)
    box(svg, rnd, (L + fx0 - 2, 24, -24), (fx1 - fx0 + 4, 0, 0), (0, 6, 0), (0, 0, 96), BENCH, detail)


# ------------------------------------------------------------------ build

def build(detail=True, seed=11, icon=False):
    rnd = random.Random(seed)
    svg = Svg()
    # behind the log: upper blade and top handle
    draw_blade(svg, SAW_B, SAW_TOP, detail, icon)
    draw_handle(svg, SAW_TOP, icon)
    draw_bark(svg, rnd, detail, icon)
    draw_wood(svg, rnd, detail, icon)
    draw_kerf(svg)
    draw_end_face(svg)
    draw_blade(svg, SAW_A, SAW_BOT, detail, icon)
    draw_handle(svg, SAW_BOT, icon)
    draw_bench(svg, rnd, detail, icon)
    return svg


def render(svg, pad=6, underlay=None, opacity=1.0, viewbox=None):
    x0, y0, x1, y1 = viewbox or svg.bbox()
    if viewbox is None:
        x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    w, h = x1 - x0, y1 - y0
    under = ""
    if underlay:
        under = f'<image href="{underlay}" x="0" y="0" width="640" height="480"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" '
            f'width="{w:.0f}" height="{h:.0f}">'
            f'<defs>{"".join(svg.defs)}</defs>{under}'
            f'<g opacity="{opacity}">{"".join(svg.body)}</g></svg>')


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "logo"
    s = build(detail=(mode != "simple"))
    if mode in ("square", "square-icon"):
        s = build(detail=(mode == "square"), icon=(mode == "square-icon"))
        x0, y0, x1, y1 = s.bbox()
        side = max(x1 - x0, y1 - y0) + 4
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        print(render(s, viewbox=(cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)))
    elif mode == "overlay":
        print(render(s, underlay="original.png", opacity=0.55, viewbox=(0, 0, 640, 480)))
    else:
        print(render(s))
