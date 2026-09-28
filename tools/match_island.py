"""Makes a Codex island picture match the home island (source_art/tiny_map.png).

Run from the game folder:
  python tools/match_island.py source_art/archipelago/ground/sw_campfire.png

Everything Codex drew keeps its shape: the coastline, cliffs, paths, stairs and beach. What changes:
- grass, paths, beach sand, cliff faces and stairs get the home island's own colours (each one's
  light-to-dark shades are moved onto the home island's shades of the same thing)
- the flat parts of the grass and the paths get the home island's real texture, sewn from small
  overlapping pieces of its open lawns and paths
- the water is new: foam and a bright shallow band along the shore (painted like the big map's
  sea), then the home island's own open water, sewn like the grass
- the paths and stairs can be widened (see ISLANDS)

Not handled yet: water inside an island (ponds, streams) is taken for land, and ground kinds the
home island doesn't have (like tilled soil) are taken for the nearest kind it knows. A see-through
picture (an island without its water) is fine: the see-through part is taken for sea.

Writes public/world/islands/<name>.png: the island's piece of the big map, with its land and its
shore water, fading out by 80 px from the shore. If the land comes closer than that to the picture's
edge, sea is added all round, and <name>.json says by how much (`pad`: the piece's top-left corner in
the big map moves that much up and left). Also
writes check/match_<name>.png (before and after, next to the home island). Check the result with
tools/review_island.py. Add --masks to see which kind of ground each pixel was taken for
(check/masks_<name>.png), when setting up a new island in ISLANDS.
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from review_island import (HOME_BOXES, HOME_FILE, SEA as SEA_BG, box_mask, hsv, materials,  # noqa: E402
                           text_font, texture)
from world_paint import bayer, fbm, hexrgb  # noqa: E402

OUT = ROOT / "public" / "world" / "islands"

# Per island: things that can't be told apart by colour alone, and fixes to shapes.
#   stairs: boxes around wooden stairs (picture pixels, x0, y0, x1, y1)
#   widen_path: pixels to push each edge of the paths outward
#   stairs_width: how wide the stairs should end up (the home island's dock walkway is 80)
ISLANDS = {
    "sw_campfire": {
        "stairs": [(748, 732, 806, 802)],
        "widen_path": 14,
        "stairs_width": 80,
    },
    "se_meadow": {
        "stairs": [(748, 738, 860, 822)],   # already about 110 px wide
        "widen_path": 8,
    },
    "n_orchard": {
        "widen_path": 8,                    # about 47 px wide as drawn
    },
}
MARGIN = 84   # sea needed around the land for the piece's water to fade out (80 px) without being cut

# Plain ground on the home island to take each kind's colours from (x0, y0, x1, y1), picked by eye.
HOME_SAMPLES = {
    "grass": [(560, 520, 700, 670), (1150, 400, 1250, 470), (100, 420, 260, 520), (420, 470, 560, 560)],
    "path": [(700, 480, 760, 700), (460, 470, 660, 520)],
    "beach": [(150, 720, 330, 800), (1200, 800, 1350, 860)],
    "cliff": [(40, 600, 330, 760), (380, 760, 600, 840), (1150, 760, 1420, 880)],
    "stairs": [(674, 772, 746, 846)],   # the dock's walkway
}
# how much of each kind's light-to-dark range to keep (1 = all of it; cliffs are a little flatter at home)
CONTRAST = {"grass": 1.0, "path": 1.0, "beach": 1.0, "cliff": 0.85, "stairs": 0.85}

# the big map's sea painter colours (tools/build_world.py), used for the foam and shallows
SEA = {k: hexrgb(v) for k, v in {
    "sea_deep": "#44a8d8", "sea": "#4cbce4", "sea_hi": "#54c8ec", "shallow": "#64d6f4", "shallow_hi": "#84e8fc",
    "ripple": "#80e2f8", "foam": "#fafcfc", "foam_lo": "#c8f2fc",
}.items()}


def to_lab(rgb):
    f = rgb.reshape(-1, 1, 3).astype(np.float32) / 255
    return cv2.cvtColor(f, cv2.COLOR_RGB2LAB).reshape(rgb.shape).astype(np.float32)


def to_rgb(lab):
    f = cv2.cvtColor(lab.reshape(-1, 1, 3).astype(np.float32), cv2.COLOR_LAB2RGB).reshape(lab.shape)
    return np.clip(np.round(f * 255), 0, 255).astype(np.uint8)


def recolour(lab, mask, src, dst, contrast=1.0):
    """Move the shades under `mask` from the colours in `src` onto those in `dst` (Lab pixel lists).
    The middle shade lands on the home island's middle shade; lighter and darker shades keep their
    distance from it, and every shade's colour strength and hue shift the same way."""
    ms, md = np.median(src, 0), np.median(dst, 0)
    cs, cd = np.hypot(ms[1], ms[2]), np.hypot(md[1], md[2])
    turn = np.arctan2(md[2], md[1]) - np.arctan2(ms[2], ms[1])
    px = lab[mask]
    L = md[0] + (px[:, 0] - ms[0]) * contrast
    c = np.hypot(px[:, 1], px[:, 2]) * (cd / max(cs, 1e-3))
    a = np.arctan2(px[:, 2], px[:, 1]) + turn
    out = lab.copy()
    out[mask] = np.stack([np.clip(L, 0, 100), c * np.cos(a), c * np.sin(a)], -1)
    return out


def paint_water(land, seed=5):
    """The sea around `land` (bool, art pixels), like the big map's sea in tools/build_world.py:
    foam on the shore, a light shallow band, ripple dashes and the open sea. Returns rgb (h, w, 3)."""
    h, w = land.shape
    rng = np.random.default_rng(seed)
    grain = rng.random((h, w)).astype(np.float32)
    grain2 = ndimage.uniform_filter(grain, 3)
    d = ndimage.distance_transform_edt(~land)                  # art pixels from the nearest shore
    wob = fbm((h, w), 26, 3, seed + 85)
    t = d + wob * 4 + (grain2 - 0.5) * 3
    band = np.select([t < 4, t < 10, t < 22, t < 70], [0, 1, 2, 3], 4)
    lut = np.stack([SEA[k] for k in ["shallow_hi", "shallow", "sea_hi", "sea", "sea_deep"]])
    img = lut[band]
    # ripple lines: the edges of loose cells, broken into dashes
    cell = 26.0
    gy, gx = int(h / cell) + 3, int(w / cell) + 3
    seeds = (np.stack(np.meshgrid(np.arange(gx), np.arange(gy)), -1) + rng.random((gy, gx, 2)) * 0.9 + 0.05) * cell
    yy, xx = np.mgrid[:h, :w]
    cx, cy = (xx / cell).astype(int), (yy / cell).astype(int)
    f1 = np.full((h, w), 1e9, np.float32)
    f2 = np.full((h, w), 1e9, np.float32)
    for oy in (-1, 0, 1):
        for ox in (-1, 0, 1):
            s = seeds[np.clip(cy + oy, 0, gy - 1), np.clip(cx + ox, 0, gx - 1)]
            dd = np.sqrt((s[..., 0] - xx) ** 2 + ((s[..., 1] - yy) * 1.35) ** 2).astype(np.float32)
            f2 = np.where(dd < f1, f1, np.minimum(f2, dd))
            f1 = np.minimum(f1, dd)
    ripple = ((f2 - f1) < 1.0) & (fbm((h, w), 9, 2, seed + 86) > 0.22) & (d > 5)
    img[ripple & (band >= 3)] = SEA["sea_hi"]
    img[ripple & (band == 2)] = SEA["ripple"]
    img[ripple & (band < 2)] = SEA["shallow_hi"]
    # foam along the shore, and a broken second line a little way out
    img[(d > 1.6) & (d <= 2.6)] = SEA["foam_lo"]
    img[(d > 0) & (d <= 1.6)] = SEA["foam"]
    img[(np.abs(d - (7 + wob * 2.2)) < 0.75) & (fbm((h, w), 11, 2, seed + 87) > -0.25)] = SEA["foam_lo"]
    img[(d > 12) & (grain > 0.9993)] = SEA["foam"]
    return img


def load_home():
    return np.ascontiguousarray(np.array(Image.open(HOME_FILE).convert("RGB"))[::2, ::2])


def segment(img, stairs_boxes=()):
    """Which kind of ground every pixel is. Returns a dict of boolean masks."""
    h, s, v = hsv(img)
    m = materials(img)
    white = (v > 0.86) & (s < 0.14)
    blue = (h > 170) & (h < 215) & (s > 0.12)
    # foam (white that touches the sea) and the pale ring around the island belong to the water,
    # which gets painted again; white blobs inside the grass are flowers
    wl, _ = ndimage.label(white)
    touching = np.unique(wl[ndimage.binary_dilation(blue, iterations=2) & white])
    sea = blue | np.isin(wl, touching[touching > 0])
    sea = ndimage.binary_closing(sea, iterations=2, border_value=1)   # beyond the picture is sea too
    # every island in the picture (the islets picture has several); specks in the sea don't count
    lab, n = ndimage.label(~sea)
    sizes = ndimage.sum(~sea, lab, range(1, n + 1))
    land = np.isin(lab, 1 + np.flatnonzero(sizes >= max(2000, 0.02 * sizes.max())))
    land = ndimage.binary_fill_holes(land)
    greenish = (h > 55) & (h < 150) & (s > 0.2) & (v > 0.15)
    yellow = (h >= 48) & (h <= 68) & (s > 0.7) & (v > 0.8)
    stairs = np.zeros(land.shape, bool)
    for x0, y0, x1, y1 in stairs_boxes:
        stairs[y0:y1, x0:x1] = True
    stairs &= land & ~greenish
    path = m["path"] & land & ~stairs
    # a real path is big; single sandy specks in the grass fringe are not paths
    pl, n = ndimage.label(path)
    if n:
        areas = ndimage.sum(path, pl, range(1, n + 1))
        path = np.isin(pl, 1 + np.flatnonzero(areas >= 400))
    beach = m["sand"] & land & ~stairs
    # the thin orange and olive line along a path's edge is part of the path, not a cliff
    near_path = ndimage.binary_dilation(path, iterations=6)
    orangey = (h < 56) & (s > 0.25) & ~(path | beach)
    path_edge = orangey & near_path & land & ~stairs
    flowers = land & ((white & ~sea) | yellow) & ~stairs
    grass = land & greenish & ~stairs & ~flowers
    cliff = land & orangey & ~path_edge & ~stairs
    known = grass | flowers | path | path_edge | beach | cliff | stairs
    # anything left over on land takes the kind of its nearest known neighbour
    rest = land & ~known
    if rest.any():
        kinds = [grass, path, path_edge, beach, cliff, stairs]
        label_img = np.zeros(land.shape, np.int8) - 1
        for i, k in enumerate(kinds):
            label_img[k] = i
        idx = ndimage.distance_transform_edt(label_img < 0, return_distances=False, return_indices=True)
        nearest = label_img[idx[0], idx[1]]
        for i, k in enumerate(kinds):
            k |= rest & (nearest == i)
    return {"land": land, "sea": ~land, "grass": grass, "flowers": flowers, "path": path,
            "path_edge": path_edge, "beach": beach, "cliff": cliff, "stairs": stairs}


def seam(err):
    """Cheapest top-to-bottom line through `err` (rows x columns), moving at most one column per
    row. Returns a mask: True right of the line."""
    rows, cols = err.shape
    cost = err.copy()
    for i in range(1, rows):
        prev = np.pad(cost[i - 1], 1, constant_values=np.inf)
        cost[i] += np.minimum(np.minimum(prev[:-2], prev[1:-1]), prev[2:])
    cut = np.zeros(rows, int)
    cut[-1] = int(np.argmin(cost[-1]))
    for i in range(rows - 2, -1, -1):
        j = cut[i + 1]
        lo, hi = max(0, j - 1), min(cols, j + 2)
        cut[i] = lo + int(np.argmin(cost[i, lo:hi]))
    return np.arange(cols)[None, :] >= cut[:, None]


def quilt(src, ok, out_h, out_w, block=32, overlap=8, tries=600, seed=0):
    """A texture of size (out_h, out_w) sewn from overlapping square pieces of `src`, using only
    pieces where `ok` is true all over. Each piece is picked to continue what is already there, and
    joined along the line where the two differ least. Pieces start on even pixels and seams follow
    2 x 2 cells, so the art-pixel grid stays whole."""
    rng = np.random.default_rng(seed)
    B, V = block, overlap
    ii = cv2.integral(ok.astype(np.uint8))
    full = (ii[B:, B:] - ii[:-B, B:] - ii[B:, :-B] + ii[:-B, :-B]) == B * B
    ys, xs = np.nonzero(full[::2, ::2])
    cand = np.stack([ys * 2, xs * 2], 1)
    if not len(cand):
        raise ValueError("no clean pieces to sew texture from")
    srcf = src.astype(np.float32)
    step = B - V
    H = out_h + B
    W = out_w + B
    out = np.zeros((H, W, 3), np.float32)
    oy, ox = np.arange(B)[:, None], np.arange(B)[None, :]
    half = lambda e: e.reshape(e.shape[0] // 2, 2, e.shape[1] // 2, 2).sum((1, 3))
    for by in range(0, out_h, step):
        for bx in range(0, out_w, step):
            pick = cand[rng.integers(0, len(cand), tries)]
            pieces = srcf[pick[:, 0, None, None] + oy, pick[:, 1, None, None] + ox]
            err = np.zeros(tries, np.float32)
            if bx:
                err += ((pieces[:, :, :V] - out[by:by + B, bx:bx + V]) ** 2).sum((1, 2, 3))
            if by:
                err += ((pieces[:, :V, :] - out[by:by + V, bx:bx + B]) ** 2).sum((1, 2, 3))
            if bx and by:
                err -= ((pieces[:, :V, :V] - out[by:by + V, bx:bx + V]) ** 2).sum((1, 2, 3))
            good = np.flatnonzero(err <= err.min() * 1.1 + 1e-3)
            p = pieces[rng.choice(good)]
            take = np.ones((B // 2, B // 2), bool)
            if bx:
                e = half(((p[:, :V] - out[by:by + B, bx:bx + V]) ** 2).sum(-1))
                take[:, : V // 2] &= seam(e)
            if by:
                e = half(((p[:V, :] - out[by:by + V, bx:bx + B]) ** 2).sum(-1))
                take[: V // 2, :] &= seam(e.T).T
            take = np.repeat(np.repeat(take, 2, 0), 2, 1)
            region = out[by:by + B, bx:bx + B]
            region[take] = p[take]
    return out[:out_h, :out_w].astype(np.uint8)


def widen_path(rgb, seg, w, band=12, inner=8, keep_out=None):
    """Push both edges of every path outward by `w` pixels: the edge line and the grass fringe
    along it move out, and path fills the gap. Moves go in steps of 2 pixels, so the art-pixel grid
    stays whole. Returns the new picture and the new path mask."""
    P = seg["path"] | seg["path_edge"]
    H, W = P.shape
    d_out, (oy, ox) = ndimage.distance_transform_edt(~P, return_indices=True)
    d_in, (iy, ix) = ndimage.distance_transform_edt(P, return_indices=True)
    qy, qx = np.mgrid[:H, :W].astype(np.float32)
    # the direction across the path (never along it, so a path's ends don't get stretched):
    # the main direction of the path's edges over an area wider than the path
    m = ndimage.gaussian_filter(P.astype(np.float32), 3)
    gy, gx = np.gradient(m)
    jxx = ndimage.gaussian_filter(gx * gx, 14)
    jyy = ndimage.gaussian_filter(gy * gy, 14)
    jxy = ndimage.gaussian_filter(gx * gy, 14)
    theta = 0.5 * np.arctan2(2 * jxy, jxx - jyy)
    nx, ny = np.cos(theta), np.sin(theta)
    # ...pointing away from the path on each side
    away_y = np.where(P, iy - qy, qy - oy)
    away_x = np.where(P, ix - qx, qx - ox)
    flip = nx * away_x + ny * away_y < 0
    nx, ny = np.where(flip, -nx, nx), np.where(flip, -ny, ny)
    s = d_out - d_in                                  # + outside the path, - inside
    movable = seg["grass"] | seg["flowers"] | P
    if keep_out is not None:
        movable &= ~ndimage.binary_dilation(keep_out, iterations=2)
    zone = (s > -inner) & (s <= w + band) & movable
    sy = (qy - 2 * np.round(w * ny / 2)).astype(int).clip(0, H - 1)
    sx = (qx - 2 * np.round(w * nx / 2)).astype(int).clip(0, W - 1)
    zone &= movable[sy, sx]
    out = rgb.copy()
    out[zone] = rgb[sy[zone], sx[zone]]
    grown = P | (zone & (s <= w))
    return out, grown


def widen_stairs(rgb, box, width, rail=6):
    """Make the stairs in `box` `width` pixels wide: both side rails move out, and the middle
    plank columns repeat (in pairs, keeping the art-pixel grid) to fill the space between."""
    x0, y0, x1, y1 = box
    old = rgb[y0:y1, x0:x1].copy()
    ow = x1 - x0
    mid_old = (ow - 2 * rail) // 2                    # art pixels between the rails
    mid_new = (width - 2 * rail) // 2
    pairs = (np.arange(mid_new) * mid_old / mid_new).astype(int)
    mid_cols = (rail + 2 * pairs[:, None] + np.array([0, 1])[None, :]).ravel()
    cols = np.concatenate([np.arange(rail), mid_cols, np.arange(ow - rail, ow)])
    nx0 = (x0 + x1 - len(cols)) // 4 * 2              # centred, on an even pixel
    out = rgb.copy()
    out[y0:y1, nx0:nx0 + len(cols)] = old[:, cols]
    return out, (nx0, y0, nx0 + len(cols), y1)


def home_pixels(home, home_lab, kind):
    """Lab colours of plain ground of this kind on the home island."""
    h, s, v = hsv(home)
    m = np.zeros(home.shape[:2], bool)
    for x0, y0, x1, y1 in HOME_SAMPLES[kind]:
        m[y0:y1, x0:x1] = True
    m &= {
        "grass": (h > 55) & (h < 150) & (s > 0.2) & (v > 0.15),
        "path": (h > 20) & (h < 55) & (s > 0.1) & (v > 0.8),
        "beach": (h > 20) & (h < 55) & (s > 0.1) & (v > 0.8),
        "cliff": (h > 5) & (h < 45) & (s > 0.12) & (v > 0.3) & (v < 0.93),
        "stairs": (h < 45) & (s > 0.2),
    }[kind]
    return home_lab[m]


def nearest_fill(img, have):
    """Give every pixel outside `have` the colour of the nearest pixel inside it."""
    idx = ndimage.distance_transform_edt(~have, return_distances=False, return_indices=True)
    return img[idx[0], idx[1]]


def match(img, home, stairs_boxes=(), widen=0, stairs_width=0):
    seg = segment(img, stairs_boxes)
    lab = to_lab(img)
    home_lab = to_lab(home)
    out = lab
    # each kind of ground: which pixels change, and which of them set its middle shade
    for kind, change, anchor in [
        ("grass", seg["grass"], seg["grass"]),
        ("path", seg["path"] | seg["path_edge"], seg["path"]),
        ("beach", seg["beach"], seg["beach"]),
        ("cliff", seg["cliff"], seg["cliff"]),
        ("stairs", seg["stairs"], seg["stairs"]),
    ]:
        if anchor.sum() > 50:
            out = recolour(out, change, lab[anchor], home_pixels(home, home_lab, kind), CONTRAST[kind])
    rgb = to_rgb(out)
    rgb[seg["flowers"]] = img[seg["flowers"]]

    # texture: Codex's flat grass and path fill become the home island's real grass and path,
    # sewn from its open lawns and paths; clover, edges and flowers stay as Codex drew them
    ys, xs = np.nonzero(seg["land"])
    y0, x0 = ys.min() // 2 * 2, xs.min() // 2 * 2
    y1, x1 = min(ys.max() + 2, img.shape[0]), min(xs.max() + 2, img.shape[1])
    hh = home.astype(int)
    R, G, B = hh[..., 0], hh[..., 1], hh[..., 2]
    plain = {
        "grass": (G > R + 12) & (G > B + 45) & (hh.sum(-1) > 330),
        "path": (R > 235) & (G > 185) & (G < 235) & (B > 115) & (B < 190) & (R - B > 55),
    }
    textures = {}
    home_m, src_m = materials(home), materials(img)
    for seed, kind in enumerate(["grass", "path"], 1):
        if seg[kind].sum() < 500:
            continue
        # texture that is already close to the home island's stays; only a flat fill is replaced
        home_tex = texture(home, home_m[kind] & box_mask(home.shape[:2], HOME_BOXES[kind]))
        flat_fill = texture(img, src_m[kind] & seg["land"]) < 0.5 * home_tex
        if not flat_fill and not (kind == "path" and widen):
            continue
        tex = np.zeros_like(rgb)
        box = (slice(y0, y1), slice(x0, x1))
        # a flat fill gets the home island's texture; a path that keeps its own texture is tidied
        # with pieces of itself, so the tidied spots don't stand out
        source, ok = (home, plain[kind]) if flat_fill else (rgb, seg[kind])
        tex[box] = quilt(source, ok, y1 - y0, x1 - x0, seed=seed)
        textures[kind] = tex                  # a widened path is tidied with it below
        if flat_fill:
            mid = np.median(lab[seg[kind]], 0)
            flat = seg[kind] & (np.linalg.norm(lab - mid, axis=-1) < 8)
            rgb[flat] = tex[flat]

    # shapes: wider stairs and paths, so the capybara has room
    stairs_now = []
    for b in stairs_boxes:
        if stairs_width:
            rgb, b = widen_stairs(rgb, b, stairs_width)
        stairs_now.append(b)
    if widen:
        keep_out = np.zeros(seg["land"].shape, bool)
        for sx0, sy0, sx1, sy1 in stairs_now:
            keep_out[sy0:sy1, sx0:sx1] = True
        rgb, seg["path"] = widen_path(rgb, seg, widen, keep_out=keep_out)
        if "path" in textures:
            # where the path meets the top of stairs that were widened: plain path between the rails,
            # under any grass that hangs over the corners (stairs that kept their size need nothing)
            h, s, v = hsv(rgb)
            for sx0, sy0, sx1, sy1 in (stairs_now if stairs_width else []):
                land_y = slice(max(0, sy0 - 14), sy0)
                land_x = slice(sx0 + 6, sx1 - 6)
                green = (h[land_y, land_x] > 55) & (h[land_y, land_x] < 150) & (v[land_y, land_x] < 0.72)
                green = ndimage.binary_opening(green, iterations=2)   # thin slivers are not grass
                region = rgb[land_y, land_x]
                region[~green] = textures["path"][land_y, land_x][~green]
            # tiny bits of grass left lying on the path become path
            h, s, v = hsv(rgb)
            green = (h > 55) & (h < 150) & (s > 0.2)
            gl, n = ndimage.label(green)
            if n:
                areas = ndimage.sum(green, gl, range(1, n + 1))
                on_path = ndimage.mean(seg["path"], gl, range(1, n + 1))
                bits = np.isin(gl, 1 + np.flatnonzero((areas < 40) & (on_path > 0.5)))
                rgb[bits] = textures["path"][bits]

    # water: painted on the art-pixel grid (2 x 2 picture pixels), like the rest of the art
    H, W = seg["land"].shape
    land_e = np.pad(seg["land"], ((0, H % 2), (0, W % 2)))
    land_art = ndimage.binary_opening(land_e.reshape(land_e.shape[0] // 2, 2, land_e.shape[1] // 2, 2).mean((1, 3)) >= 0.5)
    up = lambda a: np.repeat(np.repeat(a, 2, 0), 2, 1)[:H, :W]
    water = up(paint_water(land_art))
    land2 = up(land_art)
    rgb = nearest_fill(rgb, seg["land"])
    rgb[~land2] = water[~land2]
    # past the foam and the bright shallows (about 14 px, like the home island's shore), the open
    # water is the home island's own open sea, sewn like the grass; the two mix over 14 px
    hh, hs, hv = hsv(home)
    home_blue = (hh > 180) & (hh < 212) & (hs > 0.3) & (hv > 0.7)
    home_land = ndimage.binary_opening(~home_blue, iterations=2)
    open_sea = home_blue & (ndimage.distance_transform_edt(~home_land) > 40)
    d1 = ndimage.distance_transform_edt(~land_art) * 2
    mix = up((np.clip((d1 - 14) / 14, 0, 1) > bayer(land_art.shape)) & (d1 <= 110))
    ys, xs = np.nonzero(mix)
    if len(ys):
        y0, x0 = ys.min() // 2 * 2, xs.min() // 2 * 2
        y1, x1 = min(ys.max() + 2, img.shape[0]), min(xs.max() + 2, img.shape[1])
        sea_tex = quilt(home, open_sea, y1 - y0, x1 - x0, seed=3)
        box = (slice(y0, y1), slice(x0, x1))
        rgb[box][mix[box]] = sea_tex[mix[box]]
    # the island's piece of the big map: its land and 36 px of its own shore water, fading out over
    # the next 44 px (dithered on the art-pixel grid, like public/world/home.webp), so it all fits in
    # the 80 px of sea that Codex leaves around an island
    d = ndimage.distance_transform_edt(~land_art) * 2
    keep = (np.clip((80 - d) / 44, 0, 1) > bayer(land_art.shape)) | land_art
    alpha = up(keep).astype(np.uint8) * 255
    return np.dstack([rgb, alpha]), seg


def before_after(img, rgba, home, seg):
    """One picture: the island before and after, then close-ups of the home island, Codex's
    picture and the result, side by side."""
    font = text_font(18)
    sea = np.array(SEA_BG, np.uint8)
    after = np.where(rgba[..., 3:] > 0, rgba[..., :3], sea).astype(np.uint8)
    ys, xs = np.nonzero(seg["land"])
    m = 60
    box = (max(0, xs.min() - m), max(0, ys.min() - m), min(img.shape[1], xs.max() + m), min(img.shape[0], ys.max() + m))
    half = 610
    scale = half / (box[2] - box[0])
    size = (half, round((box[3] - box[1]) * scale))
    top = Image.new("RGB", (half * 2 + 10, size[1] + 30), (34, 34, 38))
    d = ImageDraw.Draw(top)
    for i, (pic, label) in enumerate([(img, "original"), (after, "matched to the home island")]):
        top.paste(Image.fromarray(pic).crop(box).resize(size, Image.LANCZOS), (i * (half + 10), 30))
        d.text((i * (half + 10) + 6, 5), label, fill="white", font=font)
    # close-ups at 2x: where each kind of ground is thickest in Codex's picture
    cw, ch = 200, 130
    def window(mask):
        sc = cv2.boxFilter(mask.astype(np.float32), -1, (cw, ch), normalize=False, anchor=(0, 0),
                           borderType=cv2.BORDER_CONSTANT)[: img.shape[0] - ch, : img.shape[1] - cw]
        y, x = np.unravel_index(int(np.argmax(sc)), sc.shape)
        return int(x), int(y)
    edge = ndimage.binary_dilation(seg["path"], iterations=4) & ndimage.binary_dilation(seg["grass"], iterations=4)
    if edge.any():
        first = ("grass and path", (560, 470), window(edge))
    else:                                   # no paths (like the islets): just grass
        first = ("grass", (1022, 440), window(seg["grass"] & ~ndimage.binary_dilation(~seg["grass"], iterations=8)))
    rows = [first,
            ("cliff and beach", (1150, 700), window(seg["cliff"] | seg["stairs"])),
            ("shore", (60, 660), window(ndimage.binary_dilation(seg["sea"], iterations=6) & seg["beach"]))]
    parts = [top]
    for label, (hx, hy), (nx, ny) in rows:
        row = Image.new("RGB", (cw * 2 * 3 + 20, ch * 2 + 26), (34, 34, 38))
        d = ImageDraw.Draw(row)
        for i, (pic, x, y, who) in enumerate([(home, hx, hy, "home island"), (img, nx, ny, "original"), (after, nx, ny, "matched")]):
            row.paste(Image.fromarray(pic[y:y + ch, x:x + cw]).resize((cw * 2, ch * 2), Image.NEAREST), (i * (cw * 2 + 10), 26))
            d.text((i * (cw * 2 + 10) + 6, 4), f"{label}: {who}", fill="white", font=font)
        parts.append(row)
    sheet = Image.new("RGB", (max(p.width for p in parts), sum(p.height for p in parts) + 10 * len(parts)), (34, 34, 38))
    y = 0
    for p in parts:
        sheet.paste(p, (0, y))
        y += p.height + 10
    return sheet


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    name = re.sub(r"_v\d+$", "", src.stem)          # sw_campfire_v2 uses sw_campfire's settings
    pic = np.array(Image.open(src).convert("RGBA"))
    img = pic[..., :3].copy()
    img[pic[..., 3] < 128] = SEA_BG                 # a see-through picture (land without its water): that part is sea
    cfg = ISLANDS.get(name, {})
    if "--masks" in sys.argv:
        # for setting up a new island: which kind of ground each pixel was taken for
        seg = segment(img, cfg.get("stairs", []))
        colours = {"sea": (30, 60, 120), "grass": (70, 160, 60), "flowers": (255, 255, 255), "path": (255, 0, 255),
                   "path_edge": (255, 120, 255), "beach": (240, 220, 140), "cliff": (170, 70, 40), "stairs": (255, 200, 0)}
        vis = np.zeros(img.shape, np.uint8)
        for k, c in colours.items():
            vis[seg[k]] = c
        out = ROOT / "check" / f"masks_{src.stem}.png"
        Image.fromarray(vis).save(out)
        print("wrote", out.relative_to(ROOT))
        return
    home = load_home()
    # land closer than MARGIN to the picture's edge: add sea all round (the water is painted again
    # anyway); the piece then sits `pad` pixels further up and left in the big map
    land = segment(img)["land"]
    ys, xs = np.nonzero(land)
    margin = min(ys.min(), xs.min(), img.shape[0] - 1 - ys.max(), img.shape[1] - 1 - xs.max())
    pad = max(0, MARGIN - int(margin) + 1) // 2 * 2
    stairs = cfg.get("stairs", [])
    if pad:
        img = np.pad(img, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
        stairs = [(x0 + pad, y0 + pad, x1 + pad, y1 + pad) for x0, y0, x1, y1 in stairs]
        print(f"added {pad} px of sea on every side (the land came within {margin} px of the edge)")
    rgba, seg = match(img, home, stairs, cfg.get("widen_path", 0), cfg.get("stairs_width", 0))
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{src.stem}.png"
    Image.fromarray(rgba).save(out, optimize=True)
    out.with_suffix(".json").write_text(json.dumps({"source": src.as_posix(), "pad": pad}) + "\n")
    sheet = ROOT / "check" / f"match_{src.stem}.png"
    before_after(img, rgba, home, seg).save(sheet, optimize=True)
    print("wrote", out.relative_to(ROOT), "and", sheet.relative_to(ROOT))


if __name__ == "__main__":
    main()
