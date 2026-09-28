"""Build a crisp, single-load 10x Sunny Meadow from the original art sheets."""

import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source_art"
OUT_IMAGE = ROOT / "public" / "assets" / "island-expanded.webp"
OUT_LEVEL = ROOT / "src" / "expandedLevel.json"
OUT_MASK = ROOT / "concepts" / "lost-ducklings-map-walkable-v2.png"

WORLD_W, WORLD_H = 4608, 3456
NAV_CELL = 8
ORIGINAL_OFFSET = (350, 1100)
random.seed(42)


def source_patches(kind, size=64):
    image = Image.open(SRC / "tiny_map.png").convert("RGB")
    array = np.asarray(image)
    patches = []
    for y in range(0, image.height - size, 16):
        for x in range(0, image.width - size, 16):
            patch = array[y:y + size, x:x + size]
            r, g, b = patch.reshape(-1, 3).mean(0)
            if kind == "grass" and g > r + 20 and g > b + 25 and g > 125:
                patches.append(image.crop((x, y, x + size, y + size)))
            elif kind == "water" and b > r + 28 and g > r + 25 and b > 145:
                patches.append(image.crop((x, y, x + size, y + size)))
            elif kind == "path" and r > 175 and g > 145 and b < 155 and abs(r - g) < 60:
                patches.append(image.crop((x, y, x + size, y + size)))
    if not patches:
        raise RuntimeError(f"No {kind} texture patches found")
    return patches


def texture_field(kind):
    patches = source_patches(kind)
    field = Image.new("RGB", (WORLD_W, WORLD_H))
    size = patches[0].width
    for y in range(0, WORLD_H, size):
        for x in range(0, WORLD_W, size):
            patch = random.choice(patches)
            if random.random() < 0.5:
                patch = patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if random.random() < 0.25:
                patch = patch.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            field.paste(patch, (x, y))
    return field


def full_mask_from_small(mask):
    return mask.resize((WORLD_W, WORLD_H), Image.Resampling.NEAREST)


# Irregular island silhouette on a 4-pixel grid for crisp chunky edges.
mw, mh = WORLD_W // 4, WORLD_H // 4
land_small = Image.new("L", (mw, mh), 0)
ld = ImageDraw.Draw(land_small)
ld.polygon([
    (75, 210), (130, 100), (310, 42), (520, 58), (690, 24), (920, 58),
    (1080, 160), (1135, 330), (1110, 520), (1145, 710), (1060, 820),
    (850, 850), (680, 825), (520, 860), (310, 825), (155, 745),
    (65, 610), (38, 410),
], fill=255)
for box in [(80, 80, 520, 510), (390, 45, 930, 520), (650, 135, 1130, 635),
            (120, 360, 610, 850), (450, 350, 930, 855), (730, 390, 1135, 835)]:
    ld.ellipse(box, fill=255)
for points, width in [
    ([(555, 520), (620, 585), (610, 655), (675, 720), (665, 820)], 32),
    ([(790, 545), (760, 610), (820, 680), (805, 810)], 26),
]:
    ld.line(points, fill=0, width=width, joint="curve")

land = full_mask_from_small(land_small)
water = texture_field("water")
grass = texture_field("grass")
path_texture = texture_field("path")
world = water.copy()
world.paste(grass, (0, 0), land)

# Pixel-art shoreline rings.
dilated = full_mask_from_small(land_small.filter(ImageFilter.MaxFilter(9)))
eroded_1 = full_mask_from_small(land_small.filter(ImageFilter.MinFilter(9)))
eroded_2 = full_mask_from_small(land_small.filter(ImageFilter.MinFilter(19)))
world.paste("#eaf8dc", (0, 0, WORLD_W, WORLD_H), ImageChops.subtract(dilated, land))
world.paste("#9b6d50", (0, 0, WORLD_W, WORLD_H), ImageChops.subtract(land, eroded_1))
world.paste("#f0d39a", (0, 0, WORLD_W, WORLD_H), ImageChops.subtract(eroded_1, eroded_2))

# Paths and clearings are also the navigation contract.
walk = Image.new("L", (WORLD_W, WORLD_H), 0)
wd = ImageDraw.Draw(walk)


def route(points, width=118):
    wd.line(points, fill=255, width=width, joint="curve")


def clearing(center, rx, ry=None):
    ry = ry if ry is not None else rx
    x, y = center
    wd.ellipse((x - rx, y - ry, x + rx, y + ry), fill=255)


HUB = (2300, 1580)
ORCHARD = (1250, 1050)
RUINS = (620, 650)
FOREST = (3340, 780)
MEADOW = (3550, 1580)
WETLAND = (2700, 2440)
BEACH = (720, 2500)
WEST_DOCK = (1550, 3050)
EAST_DOCK = (3950, 2880)

for args in [
    (HUB, 390, 310), (ORCHARD, 310, 250), (RUINS, 260, 220),
    (FOREST, 380, 280), (MEADOW, 350, 270), (WETLAND, 360, 260),
    (BEACH, 330, 240), (WEST_DOCK, 220, 180), (EAST_DOCK, 260, 190),
    ((1920, 1500), 300, 260),
]:
    clearing(*args)

for points in [
    [HUB, (1900, 1500), (1600, 1260), ORCHARD],
    [ORCHARD, (980, 930), (790, 780), RUINS],
    [ORCHARD, (1650, 760), (2250, 610), (2820, 650), FOREST],
    [HUB, (2650, 1370), (3020, 1080), FOREST],
    [FOREST, (3600, 1050), MEADOW],
    [HUB, (2850, 1600), MEADOW],
    [HUB, (2450, 1950), WETLAND],
    [MEADOW, (3440, 2000), (3150, 2250), WETLAND],
    [HUB, (1750, 1900), (1250, 2180), BEACH],
    [BEACH, (1000, 2780), WEST_DOCK],
    [WEST_DOCK, (2050, 2920), WETLAND],
    [WETLAND, (3300, 2620), EAST_DOCK],
    [MEADOW, (3870, 2050), EAST_DOCK],
]:
    route(points)

walk = ImageChops.multiply(walk, land)

# Preserve the original Sunny Meadow's complete walkable shape and connect it
# to the new route spine. The original layout remains the starting region.
original_level = json.loads((ROOT / "src" / "level.json").read_text(encoding="utf-8"))
original_walk = Image.new("L", (WORLD_W, WORLD_H), 0)
owd = ImageDraw.Draw(original_walk)
ox, oy = ORIGINAL_OFFSET
owd.polygon([(x + ox, y + oy) for x, y in original_level["walkable"]], fill=255)
owd.line([(1435, 1510), (1810, 1510), HUB], fill=255, width=118, joint="curve")
owd.line([(1080, 1115), (1320, 900), ORCHARD], fill=255, width=118, joint="curve")
walk = ImageChops.lighter(walk, original_walk)
world.paste("#d5b475", (0, 0, WORLD_W, WORLD_H), walk.filter(ImageFilter.MaxFilter(15)))
world.paste(path_texture, (0, 0), walk)


def crop_asset(sheet_name, box, scale=1.0):
    image = Image.open(SRC / f"{sheet_name}.png").convert("RGBA").crop(box)
    bbox = image.getbbox()
    if bbox:
        image = image.crop(bbox)
    if scale != 1:
        image = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.NEAREST)
    return image


assets = {
    "tree": crop_asset("nature_props", (0, 0, 230, 315)),
    "tree_pink": crop_asset("nature_props", (220, 0, 455, 315)),
    "tree_orange": crop_asset("nature_props", (445, 0, 705, 315)),
    "palm": crop_asset("nature_props", (700, 0, 960, 315)),
    "apple": crop_asset("nature_props", (940, 0, 1200, 315)),
    "blossom": crop_asset("nature_props", (1180, 0, 1448, 315)),
    "bush": crop_asset("nature_props", (0, 300, 175, 470)),
    "bush_pink": crop_asset("nature_props", (155, 300, 355, 470)),
    "bush_orange": crop_asset("nature_props", (335, 300, 540, 470)),
    "rocks": crop_asset("nature_props", (0, 545, 850, 715), 0.72),
    "log": crop_asset("nature_props", (840, 540, 1180, 710), 0.72),
    "stumps": crop_asset("nature_props", (1140, 535, 1448, 710), 0.75),
    "reeds": crop_asset("nature_props", (800, 720, 1448, 980), 0.62),
    "house": crop_asset("buildings_structures", (0, 0, 400, 460), 0.92),
    "orchard_house": crop_asset("buildings_structures", (390, 35, 645, 455), 0.86),
    "dock": crop_asset("buildings_structures", (0, 440, 285, 735), 0.9),
    "bridge": crop_asset("buildings_structures", (520, 430, 850, 735), 0.78),
    "fence": crop_asset("buildings_structures", (0, 730, 250, 905), 0.72),
    "gate": crop_asset("buildings_structures", (400, 730, 710, 920), 0.68),
}

objects = []


def place(name, x, base_y, flip=False):
    sprite = assets[name]
    if flip:
        sprite = sprite.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    objects.append((base_y, sprite, round(x - sprite.width / 2), round(base_y - sprite.height)))


place("house", 2380, 1370)
place("orchard_house", 1370, 1120)
place("dock", WEST_DOCK[0], 3270)
place("dock", EAST_DOCK[0], 3120, True)
place("bridge", 2730, 2570)

for x in [1700, 1870, 2040]:
    place("fence", x, 1290)
    place("fence", x, 1740, True)
for y in [1400, 1570]:
    side = assets["fence"].rotate(90, expand=True, resample=Image.Resampling.NEAREST)
    objects.append((y, side, 1570 - side.width // 2, y - side.height))
    objects.append((y, side, 2160 - side.width // 2, y - side.height))
place("gate", 1920, 1785)

for x, y in [(1020, 900), (1260, 820), (1490, 930), (1080, 1190), (1450, 1240)]:
    place("apple", x, y)
for x, y in [(3340, 1450), (3630, 1390), (3850, 1660), (3420, 1780)]:
    place("blossom" if (x + y) % 2 else "tree_pink", x, y)
for x, y in [
    (260, 560), (430, 360), (720, 300), (1050, 350), (1450, 300),
    (1950, 290), (2450, 300), (2860, 300), (3150, 350), (3500, 320),
    (3860, 420), (4200, 550), (3040, 720), (3290, 600), (3570, 700),
    (3820, 850), (3180, 1030), (4030, 1120),
]:
    place("tree", x, y)
for x, y in [(360, 820), (620, 520), (860, 650), (510, 1120)]:
    place("tree_orange", x, y)
for x, y in [(430, 2380), (680, 2720), (980, 2850), (4300, 2500)]:
    place("palm", x, y)
for x, y in [(2320, 2320), (2500, 2650), (2920, 2760), (3100, 2400), (3550, 2650)]:
    place("reeds", x, y)
for x, y in [(520, 700), (820, 560), (720, 1050), (2850, 900), (3700, 1100),
             (900, 2250), (1250, 2550), (3300, 2300), (4150, 2100)]:
    place("rocks", x, y)
for x, y in [(1150, 1500), (780, 2050), (3000, 1320), (3780, 2050)]:
    place("log", x, y)
for x, y in [(540, 1450), (1500, 2050), (3250, 1870), (4050, 1450)]:
    place("stumps", x, y)
for index, (x, y) in enumerate([
    (900, 1350), (1180, 1550), (1450, 1850), (620, 1800), (500, 2200),
    (1840, 700), (2150, 650), (2700, 1050), (2950, 1500), (3200, 2050),
    (3650, 2250), (4100, 1800), (1350, 2800), (1900, 2700), (2250, 3150),
]):
    place(["bush", "bush_pink", "bush_orange"][index % 3], x, y)

for _, sprite, x, y in sorted(objects, key=lambda item: item[0]):
    world.paste(sprite, (x, y), sprite)

# Paste the current production map at native logical resolution after the new
# territory. This keeps every original landmark and pixel exactly as shipped.
original = Image.open(ROOT / "public" / "assets" / "island.webp").convert("RGB")
original = original.resize((1448, 1086), Image.Resampling.NEAREST)
world.paste(original, ORIGINAL_OFFSET)

# Crisp transition bridges sit above both the preserved map and new territory.
for x, base_y, flip in [(1815, 1570, False), (1120, 1160, True)]:
    bridge = assets["bridge"]
    if flip:
        bridge = bridge.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    world.paste(bridge, (round(x - bridge.width / 2), round(base_y - bridge.height)), bridge)

OUT_IMAGE.parent.mkdir(parents=True, exist_ok=True)
world.save(OUT_IMAGE, "WEBP", lossless=True, method=6)

nav_mask = walk.resize((WORLD_W // NAV_CELL, WORLD_H // NAV_CELL), Image.Resampling.NEAREST)
pixels = nav_mask.load()
cols, rows = nav_mask.size
nav_rows = ["".join("1" if pixels[x, y] else "0" for x in range(cols)) for y in range(rows)]
nav_mask.resize((1152, 864), Image.Resampling.NEAREST).save(OUT_MASK)

spots = [
    (1092 + ox, 552 + oy), (817 + ox, 670 + oy), (310 + ox, 520 + oy),
    (2860, 780), (3500, 1130), (3820, 1770), (3050, 2270),
    (2450, 2500), (1720, 2860), (3500, 2730),
]
home_slots = [[x + ox, y + oy] for x, y in original_level["homeSlots"]]
level = {
    "note": "Crisp 10x single-load world preserving the original Sunny Meadow pixel-for-pixel.",
    "map": {"width": WORLD_W, "height": WORLD_H, "textureScale": 1, "texture": "assets/island-expanded.webp"},
    "legacyOffset": {"x": ox, "y": oy},
    "nav": {"cell": NAV_CELL, "cols": cols, "rows": nav_rows},
    "start": [original_level["start"][0] + ox, original_level["start"][1] + oy],
    "mommy": [original_level["mommy"][0] + ox, original_level["mommy"][1] + oy],
    "homeSlots": home_slots,
    "homeZone": {"x": original_level["homeZone"]["x"] + ox,
                 "y": original_level["homeZone"]["y"] + oy,
                 "r": original_level["homeZone"]["r"]},
    "gate": [original_level["gate"][0] + ox, original_level["gate"][1] + oy],
    "pen": {"x0": 286 + ox, "y0": 188 + oy, "x1": 662 + ox, "y1": 444 + oy},
    "boat": {"x": original_level["boat"]["x"] + ox,
             "y": original_level["boat"]["y"] + oy,
             "dir": original_level["boat"]["dir"],
             "board": [original_level["boat"]["board"][0] + ox,
                       original_level["boat"]["board"][1] + oy]},
    "spots": [{"cover": f"spot_{i:02d}", "x": x, "y": y, "fixed": i < 2} for i, (x, y) in enumerate(spots)],
    "ducklings": 5,
    "props": original_level["props"],
    "blockers": [
        {**blocker, "x": blocker["x"] + ox, "y": blocker["y"] + oy}
        for blocker in original_level["blockers"]
    ],
}
OUT_LEVEL.write_text(json.dumps(level, indent=2), encoding="utf-8")
print(json.dumps({"image": str(OUT_IMAGE), "size": [WORLD_W, WORLD_H],
                  "bytes": OUT_IMAGE.stat().st_size,
                  "walkableCells": sum(row.count("1") for row in nav_rows)}, indent=2))
