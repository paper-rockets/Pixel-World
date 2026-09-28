"""Draws the big Sunny Meadow as it stands now, as one picture.

Run from the game folder:  python tools/world_preview.py   ->  check/world_now.png

- the home island (public/assets/island.webp), its outer water faded into the sea
- every island piece made so far by tools/match_island.py (public/world/islands/), in its planned
  place from tools/review_island.py's PLANNED
- islands still to come: their concept pictures, faint, in their planned places
- the planned bridges as dashed lines, between the nearest shores of each pair of islands
- the islets (public/world/islands/islets.png), each placed in open sea for this picture only
- the sea between the islands, sewn from the home island's open water, like the pieces' open water
The picture is half size (the big map is 4608 x 3456), with names and a short legend.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from match_island import quilt  # noqa: E402
from review_island import HOME_AT, HOME_FILE, PLANNED, hsv, text_font  # noqa: E402
from world_paint import bayer  # noqa: E402

WW, WH = 4608, 3456
ISLANDS_DIR = ROOT / "public" / "world" / "islands"
CONCEPTS = ROOT / "concepts" / "archipelago"
# each new island: its name on the map, its picture size, and its concept pictures (top to bottom)
NEW = {
    "w_caves_pinktree": ("West: caves and pink tree", (1086, 1448), ["ref_nw_caves.png", "ref_w_pinktree.png"]),
    "sw_campfire": ("South-west: campfire", (1448, 1086), ["ref_sw_campfire.png"]),
    "n_orchard": ("North: orchard", (1448, 1086), ["ref_n_orchard.png"]),
    "ne_pond": ("North-east: pond", (1086, 1448), ["ref_ne_pond.png"]),
    "se_meadow": ("South-east: meadow", (1448, 1086), ["ref_se_meadow.png"]),
}
BRIDGES = [("home", "w_caves_pinktree"), ("w_caves_pinktree", "n_orchard"), ("n_orchard", "ne_pond"),
           ("ne_pond", "se_meadow"), ("se_meadow", "home"), ("w_caves_pinktree", "sw_campfire")]
S = 4  # land masks for the bridges are worked out at 1/4 size


def water_of(rgb):
    h, s, v = hsv(rgb)
    return ((h > 170) & (h < 215) & (s > 0.15)) | ((v > 0.86) & (s < 0.14))


def home_piece():
    """The home island with its outer water fading out over 44 px at the picture's edges."""
    img = np.array(Image.open(HOME_FILE).convert("RGB"))[::2, ::2]
    h, w = img.shape[:2]
    water = water_of(img)
    y, x = np.arange(h)[:, None], np.arange(w)[None, :]
    d = np.minimum(np.minimum(y, x), np.minimum(h - 1 - y, w - 1 - x)).astype(np.float32)
    b = np.repeat(np.repeat(bayer((h // 2 + 1, w // 2 + 1)), 2, 0), 2, 1)[:h, :w]
    keep = np.where(water, np.clip(d / 44.0, 0, 1) > b, True)
    land = ndimage.binary_opening(~water, iterations=2)
    return np.dstack([img, keep.astype(np.uint8) * 255]), land


def ghost(name, size):
    """The concept picture of an island still to come: its land faint, its sea see-through, fitted
    inside the planned picture with 90 px of sea around it."""
    parts = [Image.open(CONCEPTS / f).convert("RGB") for f in NEW[name][2]]
    width = max(p.width for p in parts)
    art = Image.new("RGB", (width, sum(p.height for p in parts)))
    y = 0
    for p in parts:
        art.paste(p, ((width - p.width) // 2, y))
        y += p.height
    bw, bh = size[0] - 180, size[1] - 180
    k = min(bw / art.width, bh / art.height)
    art = art.resize((round(art.width * k), round(art.height * k)), Image.LANCZOS)
    rgb = np.array(art)
    land = ndimage.binary_opening(~water_of(rgb), iterations=3)
    # bits of neighbouring islands cut by the crop's edge are not this island
    lab, n = ndimage.label(land)
    if n:
        areas = ndimage.sum(land, lab, range(1, n + 1))
        edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        keep = [i for i in range(1, n + 1) if i not in edge or areas[i - 1] == areas.max()]
        land = np.isin(lab, keep)
    # the concept crops cut some land with straight edges: fade out towards the crop's edges
    hh, ww = land.shape
    yy, xx = np.arange(hh)[:, None], np.arange(ww)[None, :]
    edge_d = np.minimum(np.minimum(yy, xx), np.minimum(hh - 1 - yy, ww - 1 - xx)).astype(np.float32)
    alpha = (land * 115 * np.clip(edge_d / 70, 0, 1)).astype(np.uint8)
    out = np.zeros((size[1], size[0], 4), np.uint8)
    ox, oy = (size[0] - art.width) // 2, (size[1] - art.height) // 2
    out[oy:oy + art.height, ox:ox + art.width] = np.dstack([rgb, alpha])
    full_land = np.zeros((size[1], size[0]), bool)
    full_land[oy:oy + art.height, ox:ox + art.width] = land
    return out, full_land


def open_sea():
    """The sea between the islands, sewn from the home island's open water on the art-pixel grid
    (half size), like the open water in the island pieces. Returns rgb at half size."""
    home = np.array(Image.open(HOME_FILE).convert("RGB"))[::4, ::4]      # art pixels
    h, s, v = hsv(home)
    blue = (h > 180) & (h < 212) & (s > 0.3) & (v > 0.7)
    land = ndimage.binary_opening(~blue, iterations=1)
    ok = blue & (ndimage.distance_transform_edt(~land) > 16)
    return quilt(home, ok, WH // 2, WW // 2, block=24, overlap=6, tries=300, seed=7)


def split_islets(path):
    """Each islet of the matched islets picture as its own piece (its land and its own shore water),
    biggest first."""
    rgba = np.array(Image.open(path).convert("RGBA"))
    land = ndimage.binary_opening((rgba[..., 3] == 255) & ~water_of(rgba[..., :3]), iterations=2)
    lab, n = ndimage.label(land)
    sizes = ndimage.sum(land, lab, range(1, n + 1))
    out = []
    for i in 1 + np.flatnonzero(sizes >= 2000):
        mine = lab == i
        near = ndimage.distance_transform_edt(~mine) <= 84
        ys, xs = np.nonzero(near)
        box = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
        piece = rgba[box].copy()
        piece[..., 3] = np.where(near[box], piece[..., 3], 0)
        out.append((piece, mine[box]))
    return sorted(out, key=lambda t: -t[1].sum())


def place_islets(islets, pieces, q=8):
    """For this picture only (the islets have no planned place yet): put each islet, biggest first,
    in the most open sea left, clear of every island and of the boat's route south of the home dock."""
    h, w = WH // q, WW // q
    busy = np.zeros((h, w), bool)
    for name, rgba, (x, y), land, made in pieces:
        ys, xs = np.nonzero(land[::q, ::q])
        ys, xs = ys + y // q, xs + x // q
        ok = (ys >= 0) & (xs >= 0) & (ys < h) & (xs < w)
        busy[ys[ok], xs[ok]] = True
    busy = ndimage.binary_dilation(busy, iterations=160 // q)
    bx, by = HOME_AT[0] + 905, HOME_AT[1] + 950            # the home dock: the boat rows 330 px south
    busy[(by - 60) // q:(by + 420) // q, (bx - 120) // q:(bx + 120) // q] = True
    placed = []
    for piece, land in islets:
        fp = ndimage.binary_dilation(land[::q, ::q], iterations=60 // q)
        fh, fw = fp.shape
        free = ~ndimage.binary_dilation(busy, structure=fp[::-1, ::-1])
        free[: fh // 2 + 1] = free[-(fh - fh // 2) - 1:] = False
        free[:, : fw // 2 + 1] = free[:, -(fw - fw // 2) - 1:] = False
        if not free.any():
            continue
        room = np.where(free, ndimage.distance_transform_edt(~busy), -1)
        cy, cx = np.unravel_index(int(np.argmax(room)), room.shape)
        top, left = cy - fh // 2, cx - fw // 2
        placed.append((piece, land, (left * q, top * q)))
        grown = ndimage.binary_dilation(np.pad(fp, 160 // q), iterations=160 // q)
        y0, x0 = top - 160 // q, left - 160 // q
        sy, sx = slice(max(0, y0), min(h, y0 + grown.shape[0])), slice(max(0, x0), min(w, x0 + grown.shape[1]))
        busy[sy, sx] |= grown[sy.start - y0:sy.stop - y0, sx.start - x0:sx.stop - x0]
    return placed


def dashed(d, a, b, width, dash=40, gap=26):
    (x0, y0), (x1, y1) = a, b
    length = float(np.hypot(x1 - x0, y1 - y0))
    if length < 1:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    t = 0.0
    while t < length:
        e = min(t + dash, length)
        seg = [(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)]
        d.line(seg, fill=(60, 40, 30), width=width + 8)
        d.line(seg, fill=(255, 248, 230), width=width)
        t += dash + gap


def main():
    world = Image.new("RGBA", (WW, WH))
    land_all = np.zeros((WH, WW), bool)
    pieces = []            # (name, rgba, top-left, land in the piece, made?)
    home_rgba, home_land = home_piece()
    pieces.append(("home", home_rgba, HOME_AT, home_land, True))
    for name, (label, size, _) in NEW.items():
        at = PLANNED[name]
        f = ISLANDS_DIR / f"{name}.png"
        if f.exists():
            rgba = np.array(Image.open(f).convert("RGBA"))
            info = f.with_suffix(".json")
            pad = json.loads(info.read_text())["pad"] if info.exists() else 0
            land = (rgba[..., 3] == 255) & ~water_of(rgba[..., :3])
            land = ndimage.binary_opening(land, iterations=2)
            pieces.append((name, rgba, (at[0] - pad, at[1] - pad), land, True))
        else:
            rgba, land = ghost(name, size)
            pieces.append((name, rgba, at, land, False))

    islets_file = ISLANDS_DIR / "islets.png"
    if islets_file.exists():
        for piece, land, at in place_islets(split_islets(islets_file), pieces):
            pieces.append(("islet", piece, at, land, True))

    # land of everything that exists, for the sea's shallows and foam
    for name, rgba, (x, y), land, made in pieces:
        if made:
            h, w = land.shape
            sub = land_all[max(0, y):y + h, max(0, x):x + w]
            sub |= land[max(0, -y):max(0, -y) + sub.shape[0], max(0, -x):max(0, -x) + sub.shape[1]]
    sea = np.repeat(np.repeat(open_sea(), 2, 0), 2, 1)[:WH, :WW]
    world.paste(Image.fromarray(np.dstack([sea, np.full((WH, WW), 255, np.uint8)])), (0, 0))
    for name, rgba, at, land, made in pieces:
        world.alpha_composite(Image.fromarray(rgba), (max(0, at[0]), max(0, at[1])),
                              (max(0, -at[0]), max(0, -at[1])))

    # bridges: between the nearest shores of each pair (worked out at 1/4 size)
    small = {}
    for name, rgba, (x, y), land, made in pieces:
        m = np.zeros((WH // S, WW // S), bool)
        ys, xs = np.nonzero(land[::S, ::S])
        ys, xs = ys + y // S, xs + x // S
        ok = (ys >= 0) & (xs >= 0) & (ys < WH // S) & (xs < WW // S)
        m[ys[ok], xs[ok]] = True
        small[name] = m
    d = ImageDraw.Draw(world)
    for a, b in BRIDGES:
        dist, (iy, ix) = ndimage.distance_transform_edt(~small[b], return_indices=True)
        dist = np.where(small[a], dist, np.inf)
        k = np.unravel_index(int(np.argmin(dist)), dist.shape)
        pa = (k[1] * S, k[0] * S)
        pb = (ix[k] * S, iy[k] * S)
        dashed(d, pa, pb, 14)

    # half size, then names and the legend
    view = world.convert("RGB").resize((WW // 2, WH // 2), Image.LANCZOS)
    d = ImageDraw.Draw(view)
    big, small_font = text_font(34), text_font(24)
    for name, rgba, (x, y), land, made in pieces:
        if name == "islet":
            continue
        ys, xs = np.nonzero(land)
        cx = (x + (xs.min() + xs.max()) / 2) / 2
        ty = (y + ys.min()) / 2 + 10
        label = "Home island" if name == "home" else NEW[name][0]
        status = "done" if made else "still to make"
        for text, font, dy in [(label, big, 0), (status, small_font, 42)]:
            w = d.textlength(text, font=font)
            box = (cx - w / 2 - 12, ty + dy - 4, cx + w / 2 + 12, ty + dy + font.size + 8)
            d.rounded_rectangle(box, 10, fill=(34, 34, 38) if dy == 0 else ((46, 125, 50) if made else (120, 90, 40)))
            d.text((cx - w / 2, ty + dy), text, fill="white", font=font)
    head = Image.new("RGB", (view.width, 96), (34, 34, 38))
    hd = ImageDraw.Draw(head)
    made_n = sum(1 for n in NEW if (ISLANDS_DIR / f"{n}.png").exists()) + islets_file.exists()
    hd.text((20, 12), f"Big Sunny Meadow now: {made_n} of {len(NEW) + 1} new island pictures done",
            fill="white", font=text_font(36))
    islets_note = ("The small islets are placed automatically, for this picture only." if islets_file.exists()
                   else "The islets (a sheet of small islands) have no place yet.")
    hd.text((20, 58), "Faint = concept picture of an island still to make.  Dashed = a bridge to build.  " + islets_note,
            fill=(210, 210, 210), font=text_font(22))
    sheet = Image.new("RGB", (view.width, view.height + head.height))
    sheet.paste(head, (0, 0))
    sheet.paste(view, (0, head.height))
    out = ROOT / "check" / "world_now.png"
    sheet.save(out, optimize=True)
    print("wrote", out.relative_to(ROOT), sheet.size)


if __name__ == "__main__":
    main()
