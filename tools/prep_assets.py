"""Turns the art in source_art/ into game-ready pictures in public/assets/.

Run from the game folder:  python tools/prep_assets.py
It also writes src/assetInfo.json (frame sizes) so the game knows how to slice the sheets.
"""
import json
import random
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source_art"
OUT = ROOT / "public" / "assets"
OUT.mkdir(parents=True, exist_ok=True)
info = {}


def blobs(img, min_area, merge=6):
    """Find separate drawings on a transparent sheet. Returns bounding boxes (x0, y0, x1, y1)."""
    a = np.array(img)[:, :, 3] > 20
    grown = ndimage.binary_dilation(a, iterations=merge)
    lab, n = ndimage.label(grown)
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        ys, xs = sl
        area = int((a[sl] & (lab[sl] == i)).sum())
        if area >= min_area:
            boxes.append((xs.start, ys.start, xs.stop, ys.stop, i, area))
    return boxes, lab, a


def cut(img, box, lab, a):
    x0, y0, x1, y1, i, _ = box
    piece = np.array(img)[y0:y1, x0:x1].copy()
    keep = (lab[y0:y1, x0:x1] == i) & a[y0:y1, x0:x1]
    piece[~keep] = 0
    return Image.fromarray(piece).crop(Image.fromarray(piece).getbbox())


def rows_of(boxes, gap=40):
    boxes = sorted(boxes, key=lambda b: (b[1] + b[3]) / 2)
    rows, cur = [], [boxes[0]]
    for b in boxes[1:]:
        if (b[1] + b[3]) / 2 - (cur[-1][1] + cur[-1][3]) / 2 > gap:
            rows.append(cur)
            cur = [b]
        else:
            cur.append(b)
    rows.append(cur)
    return [sorted(r, key=lambda b: b[0]) for r in rows]


def strip(frames, scale, name, pad=4):
    """Lay frames side by side in equal boxes, feet on the bottom edge, centred."""
    frames = [f.resize((max(1, round(f.width * scale)), max(1, round(f.height * scale))), Image.LANCZOS) for f in frames]
    fw = max(f.width for f in frames) + pad * 2
    fh = max(f.height for f in frames) + pad * 2
    sheet = Image.new("RGBA", (fw * len(frames), fh), (0, 0, 0, 0))
    for k, f in enumerate(frames):
        sheet.alpha_composite(f, (k * fw + (fw - f.width) // 2, fh - pad - f.height))
    sheet.save(OUT / f"{name}.png", optimize=True)
    info[name] = {"frameWidth": fw, "frameHeight": fh, "frames": len(frames)}
    return sheet


# ---- player capybara: 4 rows (down, left, right, up) x 4 walk steps
img = Image.open(SRC / "player_capybara_sheet.png").convert("RGBA")
boxes, lab, a = blobs(img, 5000)
rows = rows_of(boxes)
assert [len(r) for r in rows] == [4, 4, 4, 4], [len(r) for r in rows]
frames = [cut(img, b, lab, a) for r in rows for b in r]
strip(frames, 0.68, "capy")

# ---- mommy duck + ducklings: rows 4 and 5 of the animal sheet, 12 poses each
img = Image.open(SRC / "animals_companions.png").convert("RGBA")
boxes, lab, a = blobs(img, 1500, merge=3)
rows = rows_of(boxes, gap=30)
duck_row = rows[3]
chick_row = rows[4]
assert len(duck_row) == 12 and len(chick_row) == 12, (len(duck_row), len(chick_row))
strip([cut(img, b, lab, a) for b in duck_row], 1.0, "duck")
strip([cut(img, b, lab, a) for b in chick_row], 1.0, "duckling")

# ---- hiding spots: clean the cover cut-outs (drop slivers of neighbours on the edges)
covers = {}
for name in ["bush_green", "bush_pink", "bush_flowers", "log", "rocks", "stumps"]:
    img = Image.open(SRC / f"cover_{name}.png").convert("RGBA")
    boxes, lab, a = blobs(img, 2500, merge=4)
    W, H = img.size
    inside = [b for b in boxes if b[0] > 1 and b[1] > 1 and b[2] < W - 1 and b[3] < H - 1]
    inside.sort(key=lambda b: -b[5])
    if name in ("log", "rocks", "stumps"):
        inside = inside[:2]
    else:
        inside = inside[:1]
    inside.sort(key=lambda b: b[0])
    for k, b in enumerate(inside):
        key = name if len(inside) == 1 else f"{name.rstrip('s')}_{k + 1}"
        piece = cut(img, b, lab, a)
        piece.save(OUT / f"cover_{key}.png", optimize=True)
        covers[key] = piece.size
info["covers"] = covers

# ---- small icons
for name in ["ui_duckling", "ui_duck", "ui_heart"]:
    img = Image.open(SRC / f"{name}.png").convert("RGBA")
    img.crop(img.getbbox()).save(OUT / f"{name}.png", optimize=True)

# ---- island map: paint grass over the animals drawn in the pen, then double it (crisp pixels)
random.seed(5)
im = Image.open(SRC / "tiny_map.png").convert("RGB")
m0 = np.array(im).astype(np.float32)
R, G, B = m0[..., 0], m0[..., 1], m0[..., 2]
plain = (G > R + 12) & (G > B + 45) & (m0.sum(-1) > 330)  # plain light grass
H, W = plain.shape

# small clean grass squares from the pen floor; only their texture is used, not their colour
S = 16
pool = []
for y in range(226, 300, 4):
    for x in range(440, 630, 4):
        if plain[y:y + S, x:x + S].all():
            blk = m0[y:y + S, x:x + S]
            pool.append(blk - blk.reshape(-1, 3).mean(0))

# ovals big enough to cover each animal, its outline, feet and shadow
mimg = Image.new("L", im.size, 0)
for oval in [(336, 354, 396, 421), (388, 318, 452, 386), (484, 312, 584, 404),  # ducks + capybara in the pen
             (762, 597, 876, 688), (774, 592, 814, 618), (758, 602, 800, 652), (834, 658, 874, 696),
             # ^ capybara with the green scarf, by the signpost (body, ear, back outline, shadow)
             (1041, 467, 1136, 558), (1094, 532, 1138, 564)]:  # capybara with the flower + its shadow
    ImageDraw.Draw(mimg).ellipse(oval, fill=255)
mask = np.array(mimg) > 0

# colour to paint with = average of nearby plain grass only (so hay, fence and the animals don't leak in)
wgt = (plain & ~mask).astype(np.float32)


def grass_colour(sigma):
    num = cv2.GaussianBlur(m0 * wgt[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(wgt, (0, 0), sigma)[..., None]
    return num / np.maximum(den, 1e-3), den


near, den = grass_colour(12)
wide, _ = grass_colour(35)
colour = np.where(den > 0.15, near, wide)

texture = np.zeros_like(m0)
for by in range(0, H, S):
    for bx in range(0, W, S):
        if mask[by:by + S, bx:bx + S].any():
            t = random.choice(pool)
            if random.random() < 0.5:
                t = t[:, ::-1]
            texture[by:by + S, bx:bx + S] = t[:min(S, H - by), :min(S, W - bx)]

# blend over 4 px at the oval edge so there is no hard line
edge = np.clip(cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 3) / 4, 0, 1)[..., None]
out = m0 * (1 - edge) + (colour + texture) * edge
clean = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))

# ---- paint water over the rowing boat drawn beside the dock (a real boat sprite takes its place)
w0 = np.array(clean).astype(np.float32)
R, G, B = w0[..., 0], w0[..., 1], w0[..., 2]
is_water = (B > R + 25) & (B > 120)
box = np.zeros(is_water.shape, bool)
box[898:994, 832:984] = True
box[:917, :853] = False  # keep the dock post on the left (the new boat hides its foot)
boat = ndimage.binary_fill_holes(ndimage.binary_closing(~is_water & box, iterations=3))
boat = ndimage.binary_dilation(boat, iterations=4) & box
S = 16
wpool = []
for y in range(1036, 1086 - S, 4):
    for x in range(890, 1010, 4):
        if is_water[y:y + S, x:x + S].all():
            blk = w0[y:y + S, x:x + S]
            wpool.append(blk - blk.reshape(-1, 3).mean(0))
wgt = (is_water & ~boat).astype(np.float32)
num = cv2.GaussianBlur(w0 * wgt[..., None], (0, 0), 10)
den = cv2.GaussianBlur(wgt, (0, 0), 10)[..., None]
water_colour = num / np.maximum(den, 1e-3)
num2 = cv2.GaussianBlur(w0 * wgt[..., None], (0, 0), 40)
den2 = cv2.GaussianBlur(wgt, (0, 0), 40)[..., None]
water_colour = np.where(den > 0.2, water_colour, num2 / np.maximum(den2, 1e-3))
tex = np.zeros_like(w0)
for by in range(880, 1000, S):
    for bx in range(816, 1000, S):
        t = random.choice(wpool)
        tex[by:by + S, bx:bx + S] = t[:min(S, w0.shape[0] - by), :min(S, w0.shape[1] - bx)]
edge = np.clip(cv2.distanceTransform(boat.astype(np.uint8), cv2.DIST_L2, 3) / 3, 0, 1)[..., None]
w0 = w0 * (1 - edge) + (water_colour + tex) * edge
clean = Image.fromarray(np.clip(w0, 0, 255).astype(np.uint8))

# ---- treetops: cut each big tree out of the island so the capybara can walk behind it
cm = np.array(clean).astype(np.int32)
R, G, B = cm[..., 0], cm[..., 1], cm[..., 2]
plain = (G > R + 12) & (G > B + 45) & (cm.sum(-1) > 330)
water = (B > R + 25) & (B > 120)
sandy = (R > 150) & (G > 120) & (np.abs(R - G) < 45) & (G - R < 12) & (B < 170)
ground = plain | water | sandy
TREES = {  # search box (x0, y0, x1, y1), a point on the trunk, and an oval roughly matching the leaves
    "tree_top": ((498, 0, 712, 192), (605, 165), (605, 92, 92, 86)),
    "tree_right": ((1094, 84, 1292, 306), (1180, 280), (1190, 198, 89, 98)),
    "tree_pink": ((1208, 292, 1419, 548), (1305, 505), None),  # pink leaves stand out on their own
    "tree_left": ((78, 342, 284, 570), (180, 530), (180, 455, 89, 99)),
}
yy, xx = np.mgrid[0:cm.shape[0], 0:cm.shape[1]]
trees = {}
for name, ((x0, y0, x1, y1), (tx, ty), leaf) in TREES.items():
    lab, _ = ndimage.label(~ground[y0:y1, x0:x1])
    part = lab == lab[ty - y0, tx - x0]
    if leaf:
        # light leaves look like grass, so also take the leaf oval, but in each column only down to
        # the bottom edge of the leaves (so no grass around the trunk gets drawn over the capybara)
        ex, ey, erx, ery = leaf
        oval = (((xx - ex) / erx) ** 2 + ((yy - ey) / ery) ** 2 < 1)[y0:y1, x0:x1]
        rows = np.arange(y1 - y0)[:, None]
        leaves = part & (rows < ey + ery * 0.85 - y0)  # ignore the trunk and roots
        lowest = np.where(leaves.any(0), (leaves * rows).max(0), -1)[None, :]
        part |= oval & (rows <= lowest) & ~(water | sandy)[y0:y1, x0:x1]
    part = ndimage.binary_fill_holes(ndimage.binary_closing(part, iterations=2))
    # where the trunk meets the ground: lowest tree pixel near the trunk
    base = y0 + int(np.nonzero(part[:, tx - x0 - 10:tx - x0 + 10].any(1))[0].max())
    rgba = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    rgba[..., :3] = cm[y0:y1, x0:x1]
    rgba[..., 3] = part * 255
    piece = Image.fromarray(rgba)
    bx0, by0, bx1, by1 = piece.getbbox()
    piece.crop((bx0, by0, bx1, by1)).resize(((bx1 - bx0) * 2, (by1 - by0) * 2), Image.NEAREST).save(OUT / f"{name}.png", optimize=True)
    trees[name] = {"x": x0 + bx0, "y": y0 + by0, "trunkX": tx, "base": base}
info["trees"] = trees

# ---- painted bushes, rocks, stumps, logs, lamps...: cut out so the capybara can walk behind them
level = json.loads((ROOT / "src" / "level.json").read_text(encoding="utf-8"))
pieces = []
for i, p in enumerate(level["props"]):
    x0, y0, x1, y1 = p["box"]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(cm.shape[1], x1), min(cm.shape[0], y1)
    # the thing lives inside an oval around its seed (box minus margins); inside that oval take every
    # non-grass pixel, close the gaps, and always keep the middle (light leaves look like grass)
    ex, ey = p["seed"][0] - x0, p["seed"][1] - y0
    erx, ery = (x1 - x0 - 32) / 2 + 6, (y1 - y0 - 34) / 2 + 6
    yy2, xx2 = np.mgrid[0:y1 - y0, 0:x1 - x0]
    r2 = ((xx2 - ex) / erx) ** 2 + ((yy2 - ey) / ery) ** 2
    oval = r2 < 1
    thing = ~ground[y0:y1, x0:x1] & oval
    thing = ndimage.binary_closing(thing, iterations=3) | (r2 < 0.35)
    thing = ndimage.binary_fill_holes(thing) & oval
    lab, _ = ndimage.label(thing)
    part = lab == lab[int(ey), int(ex)]
    if "rects" in p:  # traced by hand (the house: its green roof looks like grass to the colour test)
        part = np.zeros_like(part)
        for rx0, ry0, rx1, ry1 in p["rects"]:
            part[max(0, ry0 - y0):ry1 - y0, max(0, rx0 - x0):rx1 - x0] = True
    ys, xs = np.nonzero(part)
    bx0, by0, bx1, by1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    w, h = bx1 - bx0, by1 - by0
    mid = part[:, bx0 + w // 5: bx1 - w // 5] if w > 10 else part
    base = p.get("base", y0 + int(np.nonzero(mid.any(1))[0].max()))  # where it meets the ground
    rgba = np.zeros((by1 - by0, bx1 - bx0, 4), np.uint8)
    rgba[..., :3] = cm[y0 + by0:y0 + by1, x0 + bx0:x0 + bx1]
    rgba[..., 3] = part[by0:by1, bx0:bx1] * 255
    img2 = Image.fromarray(rgba).resize((w * 2, h * 2), Image.NEAREST)
    fy = float(np.clip(h * 0.14, 6, 14))  # only the bottom of each thing is solid
    pieces.append((f"prop_{i:02d}", img2, {
        "what": p["what"], "x": int(x0 + bx0), "y": int(y0 + by0), "base": base,
        "foot": {"x": round(x0 + bx0 + w / 2, 1), "y": round(base - fy, 1), "rx": round(w * 0.42, 1), "ry": round(fy, 1)},
    }))

# pack them into one picture with a frame list the game can read
sheet_w = 1024
x = y = row_h = 0
frames = {}
for key, img2, _ in pieces:
    if x + img2.width > sheet_w:
        x, y, row_h = 0, y + row_h + 2, 0
    frames[key] = (x, y, img2.width, img2.height)
    x += img2.width + 2
    row_h = max(row_h, img2.height)
sheet = Image.new("RGBA", (sheet_w, y + row_h), (0, 0, 0, 0))
for key, img2, _ in pieces:
    sheet.paste(img2, frames[key][:2])
sheet.save(OUT / "props.png", optimize=True)
atlas = {"frames": {k: {"frame": {"x": fx, "y": fy, "w": fw, "h": fh}} for k, (fx, fy, fw, fh) in frames.items()},
         "meta": {"image": "props.png", "size": {"w": sheet.width, "h": sheet.height}, "scale": 1}}
(OUT / "props.json").write_text(json.dumps(atlas))
info["props"] = {key: meta for key, _, meta in pieces}
clean.resize((clean.width * 2, clean.height * 2), Image.NEAREST).save(OUT / "island.webp", lossless=True, method=6)
info["map"] = {"width": im.width, "height": im.height, "textureScale": 2}

(ROOT / "src" / "assetInfo.json").write_text(json.dumps(info, indent=2))
print(json.dumps(info, indent=2))

# ---- match the island's pixel size ------------------------------------------------------------
# The island is drawn with chunky pixels about 2 island-pixels wide. The capybara, ducks and hiding
# spots come from bigger drawings that get shrunk in the game, which makes their pixels too small.
# Re-draw each one at the size it appears in the game, snapped to the island's 2-pixel grid, then
# store it at 2x (like the island) so the game shows it at scale 0.5.
import sys
sys.path.insert(0, str(ROOT / "tools"))
from pixelate import pixelate_mode, make_palette, chunky

BLOCK = 2      # island pixel size, in island pixels
TEX = 2        # textures are stored at 2x, like island.webp
GAME_SCALE = {"capy": 0.4, "duck": 0.5, "duckling": 0.36}  # how big each strip used to be drawn

for name, scale in GAME_SCALE.items():
    sheet = Image.open(OUT / f"{name}.png").convert("RGBA")
    fw, fh, n = info[name]["frameWidth"], info[name]["frameHeight"], info[name]["frames"]
    pal = make_palette(sheet, 48)
    cells = [pixelate_mode(sheet.crop((k * fw, 0, (k + 1) * fw, fh)), fw * scale, fh * scale, BLOCK, pal=pal) for k in range(n)]
    cw, ch = cells[0].size
    out = Image.new("RGBA", (cw * n, ch), (0, 0, 0, 0))
    for k, c in enumerate(cells):
        out.paste(c, (k * cw, 0))
    out = chunky(out, BLOCK * TEX)
    out.save(OUT / f"{name}.png", optimize=True)
    info[name] = {"frameWidth": cw * BLOCK * TEX, "frameHeight": ch * BLOCK * TEX, "frames": n}

spots = []
for i, s in enumerate(level["spots"]):
    img = Image.open(OUT / f"cover_{s['cover']}.png").convert("RGBA")
    if s.get("flip"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    px = pixelate_mode(img, img.width * s["scale"], img.height * s["scale"], BLOCK)
    chunky(px, BLOCK * TEX).save(OUT / f"spot_{i:02d}.png", optimize=True)
    spots.append(f"spot_{i:02d}")
info["spots"] = spots

heart = Image.open(OUT / "ui_heart.png").convert("RGBA")
chunky(pixelate_mode(heart, heart.width * 0.4, heart.height * 0.4, BLOCK), BLOCK * TEX).save(OUT / "heart_px.png", optimize=True)

(ROOT / "src" / "assetInfo.json").write_text(json.dumps(info, indent=2))
print("pixel-matched:", {k: info[k] for k in GAME_SCALE}, len(spots), "spots")
