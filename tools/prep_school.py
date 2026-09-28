"""Builds the Willingdon School island from the layered pack in source_art/school/.

Run from the game folder:  python tools/prep_school.py
Writes public/school/ (ground, walk map, object atlas, capybara) and src/school/assets.json.
Also writes check/school_preview.png with walls and walk area drawn on, for checking by eye.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from pixelate import chunky, make_palette, pixelate_mode  # noqa: E402

SRC = ROOT / "source_art" / "school"
OUT = ROOT / "public" / "school"
OUT.mkdir(parents=True, exist_ok=True)
scene = json.loads((ROOT / "src" / "school" / "scene.json").read_text(encoding="utf-8"))
W, H = scene["size"]
BLOCK = 2  # the ground's pixel size
TEX = 2    # textures are stored at 2x
CELL = 2   # walk map resolution
info = {"size": [W, H], "start": scene["start"], "exit": scene["exit"], "boat": scene["boat"]}

# ---- ground (2x, crisp)
ground = Image.open(SRC / "ground" / "map_ground.png").convert("RGB")
ground.resize((W * TEX, H * TEX), Image.NEAREST).save(OUT / "ground.webp", lossless=True, method=6)

# ---- where you can walk: grass, paths, sand and the court; not water, foam or cliff faces
g = np.array(ground).astype(int)
R, G, B = g[..., 0], g[..., 1], g[..., 2]
water = (B > R + 25) & (B > 120)
foam = (R > 200) & (G > 225) & (B > 225)
grass = (G > R + 12) & (G > B + 35)
sand = (R > 215) & (G > 170) & (B > 110) & (R >= G) & ~foam
court = (np.abs(R - G) < 18) & (np.abs(G - B) < 28) & (R > 110) & (R < 205)
walk = (grass | sand | court) & ~water & ~foam
walk = ndimage.binary_opening(walk, iterations=1)
walk = ndimage.binary_closing(walk, iterations=3)
walk = ndimage.binary_fill_holes(walk)
for x0, y0, x1, y1 in scene.get("walkRects", []):
    walk[y0:y1, x0:x1] = True
lab, _ = ndimage.label(walk)
sx, sy = scene["start"]
walk = lab == lab[sy, sx]
cells = walk.reshape(H // CELL, CELL, W // CELL, CELL).mean(axis=(1, 3)) > 0.5
Image.fromarray((cells * 255).astype(np.uint8)).save(OUT / "walk.png", optimize=True)
info["walk"] = {"file": "walk.png", "cell": CELL}

# ---- objects: size, pixel-match, find the solid base, pack into one picture
pieces = []
objects = []
for o in scene["objects"]:
    img = Image.open(SRC / o["file"]).convert("RGBA")
    img = img.crop(img.getbbox())
    w, h = img.width * o["scale"], img.height * o["scale"]
    px = pixelate_mode(img, w, h, BLOCK)
    w, h = px.width * BLOCK, px.height * BLOCK  # exact size after snapping to the grid
    a = np.array(px)[..., 3] > 0
    ys = np.nonzero(a.any(1))[0]
    band = a[max(0, ys.max() - max(2, round(px.height * 0.18))):ys.max() + 1]
    cols = np.nonzero(band.any(0))[0]
    bw = (cols.max() - cols.min() + 1) * BLOCK
    bcx = (cols.min() + cols.max() + 1) / 2 * BLOCK
    left = o["x"] - w / 2
    top = o["y"] - h
    ry = float(np.clip(h * 0.12, 6, 14))
    entry = {
        "id": o["id"], "key": o["id"], "x": round(left, 1), "y": round(top, 1), "w": w, "h": h,
        "base": o["y"], "role": o.get("role"), "ground": bool(o.get("ground") or o.get("under")),
        "foot": None,
    }
    if o.get("solid", True) and not entry["ground"]:
        entry["foot"] = {"type": "ellipse", "x": round(left + bcx, 1), "y": round(o["y"] - ry, 1), "rx": round(bw * 0.46, 1), "ry": round(ry, 1)}
    if o.get("role") == "garden":  # the whole stone ring is solid, flowers get planted inside it
        entry["foot"] = {"type": "ellipse", "x": o["x"], "y": round(o["y"] - h * 0.42, 1), "rx": round(w * 0.46, 1), "ry": round(h * 0.4, 1)}
    objects.append(entry)
    pieces.append((o["id"], chunky(px, BLOCK * TEX)))

# the school is big, so it gets its own picture; everything else shares one
atlas_w = 2048
x = y = row_h = 0
frames = {}
for key, im in pieces:
    if key == "school":
        im.save(OUT / "school.png", optimize=True)
        continue
    if x + im.width > atlas_w:
        x, y, row_h = 0, y + row_h + 2, 0
    frames[key] = (x, y, im.width, im.height)
    x += im.width + 2
    row_h = max(row_h, im.height)
sheet = Image.new("RGBA", (atlas_w, y + row_h), (0, 0, 0, 0))
for key, im in pieces:
    if key in frames:
        sheet.paste(im, frames[key][:2])
sheet.save(OUT / "objects.png", optimize=True)
(OUT / "objects.json").write_text(json.dumps({
    "frames": {k: {"frame": {"x": fx, "y": fy, "w": fw, "h": fh}} for k, (fx, fy, fw, fh) in frames.items()},
    "meta": {"image": "objects.png", "size": {"w": sheet.width, "h": sheet.height}, "scale": 1},
}))
info["objects"] = objects
info["blockRects"] = scene.get("blockRects", [])

# ---- the orange-shirt capybara: 4 rows (down, left, right, up) x 4 steps, cut from the full sheet
sheet_img = Image.open(SRC / "player" / "player_capybara_orange_shirt_sheet.png").convert("RGBA")
alpha = np.array(sheet_img)[..., 3] > 20
lab, _ = ndimage.label(ndimage.binary_dilation(alpha, iterations=3))
boxes = []
for i, sl in enumerate(ndimage.find_objects(lab), 1):
    if (sl[0].stop - sl[0].start) * (sl[1].stop - sl[1].start) > 3000:
        boxes.append((sl, i))
boxes.sort(key=lambda b: ((b[0][0].start + b[0][0].stop) // 2 // 150, b[0][1].start))
assert len(boxes) == 16, len(boxes)
raw = []
for sl, i in boxes:
    piece = np.array(sheet_img)[sl].copy()
    piece[~((lab[sl] == i) & alpha[sl])] = 0
    raw.append(Image.fromarray(piece))
target_h = 64  # the capybara's height on the island, same as on the duck island
scale = target_h / np.median([f.height for f in raw[:4]])
fw = max(f.width for f in raw)
fh = max(f.height for f in raw)
cell_w, cell_h = int(fw * scale) + 8, int(fh * scale) + 8
cell_w += cell_w % 2
cell_h += cell_h % 2
pal = make_palette(sheet_img, 48)
strip = []
for f in raw:
    small = pixelate_mode(f, f.width * scale, f.height * scale, BLOCK, pal=pal)
    cell = Image.new("RGBA", (cell_w // BLOCK, cell_h // BLOCK), (0, 0, 0, 0))
    cell.alpha_composite(small, ((cell.width - small.width) // 2, cell.height - small.height - 1))
    strip.append(cell)
cw, ch = strip[0].size
out = Image.new("RGBA", (cw * 16, ch), (0, 0, 0, 0))
for k, c in enumerate(strip):
    out.paste(c, (k * cw, 0))
chunky(out, BLOCK * TEX).save(OUT / "capy.png", optimize=True)
info["capy"] = {"frameWidth": cw * BLOCK * TEX, "frameHeight": ch * BLOCK * TEX, "frames": 16}

# ---- icons for the screen overlay
flower = Image.open(SRC / "objects" / "school_props" / "orange_flower_collectible.png").convert("RGBA")
flower.crop(flower.getbbox()).save(OUT / "ui_flower.png", optimize=True)
garden = Image.open(SRC / "objects" / "school_props" / "remembrance_garden.png").convert("RGBA")
garden = garden.crop(garden.getbbox())
garden.thumbnail((96, 96))
garden.save(OUT / "ui_garden.png", optimize=True)

(ROOT / "src" / "school" / "assets.json").write_text(json.dumps(info, indent=1))

# ---- preview for checking by eye
prev = ground.convert("RGBA")
shade = Image.new("RGBA", prev.size, (0, 0, 0, 0))
shade_px = np.zeros((H, W, 4), np.uint8)
shade_px[~walk] = (255, 0, 0, 70)
prev.alpha_composite(Image.fromarray(shade_px))
order = sorted(objects, key=lambda e: (not e["ground"], e["base"]))
for e in order:
    im = sheet.crop((frames[e["key"]][0], frames[e["key"]][1], frames[e["key"]][0] + frames[e["key"]][2], frames[e["key"]][1] + frames[e["key"]][3])) if e["key"] in frames else Image.open(OUT / "school.png")
    im = im.resize((round(e["w"]), round(e["h"])), Image.NEAREST)
    prev.alpha_composite(im, (round(e["x"]), round(e["y"])))
d = ImageDraw.Draw(prev)
for e in objects:
    f = e["foot"]
    if f:
        d.ellipse((f["x"] - f["rx"], f["y"] - f["ry"], f["x"] + f["rx"], f["y"] + f["ry"]), outline=(255, 255, 0, 255), width=2)
for x0, y0, x1, y1 in scene.get("blockRects", []):
    d.rectangle((x0, y0, x1, y1), outline=(255, 0, 255, 255), width=2)
d.ellipse((sx - 7, sy - 7, sx + 7, sy + 7), fill=(0, 120, 255, 255))
(ROOT / "check").mkdir(exist_ok=True)
prev.convert("RGB").save(ROOT / "check" / "school_preview.png")
print("objects:", len(objects), "atlas:", sheet.size, "capy frame:", info["capy"])
