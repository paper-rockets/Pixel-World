"""Small painting helpers for tools/build_world.py (the big Sunny Meadow).

Everything works on numpy arrays at "art pixel" size: one array cell = one art pixel = 2 island pixels.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


def hexrgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.uint8)


def fbm(shape, cell, octaves=4, seed=0, gain=0.5):
    """Smooth random field in about -1..1. `cell` = size of the biggest blobs, in pixels."""
    rng = np.random.default_rng(seed)
    h, w = shape
    out = np.zeros(shape, np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        c = max(2.0, cell / (2 ** o))
        gw, gh = int(w / c) + 3, int(h / c) + 3
        grid = rng.standard_normal((gh, gw)).astype(np.float32)
        img = Image.fromarray(grid, "F").resize((int(gw * c), int(gh * c)), Image.BICUBIC)
        a = np.asarray(img)
        oy, ox = rng.integers(0, max(1, a.shape[0] - h)), rng.integers(0, max(1, a.shape[1] - w))
        out += amp * a[oy:oy + h, ox:ox + w]
        total += amp
        amp *= gain
    out /= total
    return out / (np.abs(out).max() + 1e-6)


_BAYER4 = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) / 16 + 1 / 32


def bayer(shape):
    h, w = shape
    return np.tile(_BAYER4, (h // 4 + 1, w // 4 + 1))[:h, :w]


def dist_out(mask):
    """Distance (pixels) from every cell outside `mask` to the nearest cell inside it (0 inside)."""
    return ndimage.distance_transform_edt(~mask)


def dist_in(mask):
    """Distance from every cell inside `mask` to the nearest cell outside it (0 outside)."""
    return ndimage.distance_transform_edt(mask)


def disk(r):
    y, x = np.ogrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r + r * 0.6


def grow(mask, r):
    return ndimage.binary_dilation(mask, structure=disk(r)) if r > 0 else mask.copy()


def shrink(mask, r):
    return ndimage.binary_erosion(mask, structure=disk(r), border_value=1) if r > 0 else mask.copy()


def shift(mask, dy=0, dx=0, fill=False):
    out = np.full_like(mask, fill)
    h, w = mask.shape
    ys = slice(max(0, dy), h + min(0, dy))
    yd = slice(max(0, -dy), h + min(0, -dy))
    xs = slice(max(0, dx), w + min(0, dx))
    xd = slice(max(0, -dx), w + min(0, -dx))
    out[ys, xs] = mask[yd, xd]
    return out


def poisson(mask, r, seed=0, tries=None, limit=None):
    """Points inside `mask`, no two closer than r (simple grid dart throwing)."""
    rng = np.random.default_rng(seed)
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return []
    n = tries or int(len(xs) / (r * r) * 3) + 10
    pick = rng.integers(0, len(xs), n)
    cell = r / 1.4143
    grid = {}
    pts = []
    for i in pick:
        x, y = xs[i] + rng.random(), ys[i] + rng.random()
        gx, gy = int(x / cell), int(y / cell)
        ok = True
        for yy in range(gy - 2, gy + 3):
            for xx in range(gx - 2, gx + 3):
                q = grid.get((xx, yy))
                if q and (q[0] - x) ** 2 + (q[1] - y) ** 2 < r * r:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            grid[(gx, gy)] = (x, y)
            pts.append((x, y))
            if limit and len(pts) >= limit:
                break
    return pts


def polyline_mask(shape, pts, width, wobble=None):
    """Thick wobbly line through pts (art pixels) as a boolean mask."""
    h, w = shape
    img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(img)
    d.line([tuple(p) for p in pts], fill=255, width=int(width), joint="curve")
    r = width / 2
    for p in (pts[0], pts[-1]):
        d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=255)
    m = np.asarray(img) > 127
    if wobble is not None:
        # push the edge in and out a little so paths never look ruled
        dd = ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)
        m = dd + wobble > 0
    return m


def smooth_curve(pts, steps=10):
    """Catmull-Rom through the points, so hand-placed corners become soft bends."""
    pts = [np.array(p, float) for p in pts]
    if len(pts) < 3:
        return [tuple(p) for p in pts]
    ext = [pts[0] * 2 - pts[1]] + pts + [pts[-1] * 2 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)))
    out.append(tuple(pts[-1]))
    return out


def paint(canvas, mask, color):
    canvas[mask] = hexrgb(color) if isinstance(color, str) else color


def paste(canvas, sprite, x, y, alpha_min=128):
    """Paste an RGBA sprite (numpy, art pixels) with its top-left at (x, y), hard edges only."""
    h, w = canvas.shape[:2]
    sh, sw = sprite.shape[:2]
    x0, y0 = int(round(x)), int(round(y))
    xa, ya = max(0, x0), max(0, y0)
    xb, yb = min(w, x0 + sw), min(h, y0 + sh)
    if xa >= xb or ya >= yb:
        return None
    s = sprite[ya - y0:yb - y0, xa - x0:xb - x0]
    m = s[..., 3] >= alpha_min
    canvas[ya:yb, xa:xb][m] = s[..., :3][m]
    return (xa, ya, xb, yb, m)
