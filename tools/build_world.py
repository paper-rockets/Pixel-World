"""Grows Sunny Meadow into a big island world around the painted home island.

Run from the game folder:  python tools/build_world.py [--quick]

The painted home island (public/assets/island.webp, Mama's pen, the house, the dock) stays exactly as
it is. New land is painted around it on three sides, across narrow channels, and two wooden bridges
join them. The new ground is painted here at "art pixel" size (1 art pixel = 2 island pixels, the
islands' chunky pixel size): grass, paths, cliffs, beaches and water, with nothing standing on it.
Every tree, bush, rock and fence is its own picture that the game draws on top, sorted by where it
touches the ground, so the capybara can walk behind all of them.

Writes:
  public/world/ground.webp      the new ground, 2304 x 1728 art pixels (the game draws it at 2x)
  public/world/home.webp        the painted island with its outer water softly faded into the new sea
  check/world_*.png             previews for checking by eye
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from world_paint import (bayer, dist_in, dist_out, fbm, grow, hexrgb, poisson,  # noqa: E402
                         polyline_mask, shift, shrink, smooth_curve)

QUICK = "--quick" in sys.argv
T0 = time.time()
OUT = ROOT / "public" / "world"
OUT.mkdir(parents=True, exist_ok=True)
(ROOT / "check").mkdir(exist_ok=True)


def log(*a):
    print(f"[{time.time() - T0:5.1f}s]", *a, flush=True)


# ------------------------------------------------------------------------------------------------
# Layout, in island pixels (the game's coordinates). The art grid is half of this.
# ------------------------------------------------------------------------------------------------
WW, WH = 4608, 3456
F = 2
AW, AH = WW // F, WH // F

HOME_W, HOME_H = 1448, 1086
OX, OY = 1584, WH - HOME_H          # the painted island sits in a bay on the south coast

# the new land: one horseshoe around the bay, clockwise from the south-west point
COAST = [
    (420, 3330), (230, 3050), (160, 2650), (250, 2250), (170, 1850), (250, 1450), (190, 1050),
    (280, 680), (460, 360), (820, 190), (1220, 240), (1470, 400), (1560, 520), (1700, 470),
    (1800, 290), (2200, 190), (2700, 230), (3050, 180), (3260, 280), (3330, 420), (3420, 300),
    (3900, 300), (4250, 480), (4400, 820), (4330, 1120), (4150, 1210), (4080, 1330), (4180, 1440),
    (4420, 1520), (4390, 1900), (4460, 2300), (4360, 2720), (4250, 3060), (3980, 3310),
    (3700, 3360), (3430, 3290), (3290, 3040), (3270, 2720), (3290, 2420), (3230, 2240),   # east channel shore
    (3000, 2140), (2700, 2170), (2400, 2120), (2100, 2160), (1800, 2130), (1520, 2170),   # north channel shore
    (1390, 2320), (1350, 2600), (1380, 2900), (1300, 3160), (1020, 3320), (720, 3380),   # west channel shore
]

BEACHES = [  # the top edge reaches into the grass, so grass and sand always meet
    [(300, 2860), (520, 2800), (820, 2840), (1080, 2880), (1250, 2990), (1270, 3150), (1060, 3270),
     (760, 3310), (480, 3270), (290, 3120)],                                             # south-west cove
    [(3390, 3040), (3600, 2960), (3900, 2970), (4150, 2980), (4260, 3090), (4060, 3260), (3760, 3310),
     (3480, 3260)],                                                                       # south-east cove
]
GENTLE = [(2560, 2170, 110)]     # extra spots where the grass slopes down to the water with no cliff

PONDS = [
    (720, 560, 125, 78),      # the hilltop spring
    (2210, 1690, 210, 125),   # wetland pools
    (2470, 1900, 150, 100),
    (3930, 1300, 120, 80),    # meadow pond
]
CREEK = [(2560, 930), (2470, 1180), (2400, 1400), (2300, 1580), (2330, 1790), (2470, 1900),
         (2520, 2040), (2560, 2200)]

PATHS = [  # (width, points)
    (56, [(1400, 2835), (1150, 2780), (1000, 2640)]),                                     # west bridge -> west land
    (48, [(1000, 2640), (820, 2800), (740, 2950)]),                                       # -> beach
    (56, [(1000, 2640), (900, 2250), (1080, 1850), (1250, 1500)]),                        # -> orchard
    (52, [(1250, 1500), (1000, 1150), (820, 820), (760, 680)]),                           # orchard -> hill
    (56, [(1250, 1500), (1700, 1430), (2150, 1350)]),                                     # orchard -> crossroads
    (48, [(2150, 1350), (2000, 1580), (1950, 1850), (2080, 2060)]),                       # wetland trail -> lookout
    (52, [(2150, 1350), (2200, 1000), (2450, 700), (2700, 560)]),                         # -> forest
    (44, [(2700, 560), (2250, 430), (1800, 520), (1300, 500), (900, 560), (760, 680)]),   # forest -> hill
    (48, [(2700, 560), (3150, 620), (3600, 820), (3750, 1050)]),                          # forest -> meadow
    (56, [(2150, 1350), (2600, 1360), (3100, 1250), (3750, 1050)]),                       # crossroads -> meadow
    (56, [(3750, 1050), (3950, 1500), (3850, 1950), (3750, 2350), (3700, 2620)]),         # meadow -> east land
    (56, [(3700, 2620), (3470, 2760), (3240, 2795)]),                                     # -> east bridge
    (48, [(3700, 2620), (3850, 2900), (3900, 3060)]),                                     # -> south-east beach
]
# the two bridges to the home island and the creek crossing: centre, direction, plank sections
BRIDGES = [
    {"at": (1500, 2835), "dir": "h", "n": 2, "home": True},      # west bridge
    {"at": (3120, 2795), "dir": "h", "n": 2, "home": True},      # east bridge
    {"at": (2425, 1357), "dir": "h", "n": 1},                     # creek on the main east path
]

ISLETS = [(90, 110, 80, 50), (4520, 140, 70, 50), (4540, 1800, 55, 90), (120, 1600, 50, 70),
          (2080, 90, 60, 40), (3500, 3440, 70, 40)]

ZONES = {  # centre, radius: used for grass colour, what grows where, and one duckling per zone
    "hill": ((800, 650), 500),
    "orchard": ((1180, 1600), 460),
    "forest": ((2450, 700), 780),
    "wetland": ((2250, 1750), 420),
    "meadow": ((3750, 1050), 600),
    "coast": ((3850, 2550), 560),
    "beach": ((820, 2850), 560),
}

# ------------------------------------------------------------------------------------------------
# Palette (sampled from the painted Sunny Meadow)
# ------------------------------------------------------------------------------------------------
C = {k: hexrgb(v) for k, v in {
    "grass": "#bce454", "grass_lo": "#b2da50", "grass_hi": "#c6e860", "tuft": "#98c848", "tuft_dk": "#7cae3c",
    "edge": "#5e9a34", "edge_dk": "#467a2c", "lip": "#a6d24c",
    "forest": "#a8d44c", "forest_lo": "#98c648", "forest_hi": "#b4dc50",
    "path": "#fcdc9c", "path_hi": "#fce6b4", "path_lo": "#f0ca88", "path_rim": "#e8c080", "pebble": "#d8b27c",
    "sand": "#fce4b0", "sand_lo": "#f8d49c", "sand_hi": "#fcecc8", "sand_sh": "#e8c28c",
    "cliff_top": "#dc9c64", "cliff": "#c48454", "cliff_mid": "#b47454", "cliff_lo": "#a4644c", "cliff_ln": "#8c5444", "cliff_base": "#7a4a3a",
    "sea_deep": "#44a8d8", "sea": "#4cbce4", "sea_hi": "#54c8ec", "shallow": "#64d6f4", "shallow_hi": "#84e8fc",
    "ripple": "#80e2f8", "foam": "#fafcfc", "foam_lo": "#c8f2fc",
}.items()}


def A(v):
    """island pixels -> art pixels"""
    return v / F


# ------------------------------------------------------------------------------------------------
# The painted home island: which parts are land, at art-pixel size
# ------------------------------------------------------------------------------------------------
home_src = Image.open(ROOT / "public" / "assets" / "island.webp").convert("RGB")      # stored at 2x
home_px = np.array(home_src.resize((HOME_W, HOME_H), Image.NEAREST)).astype(int)
hr, hg, hb = home_px[..., 0], home_px[..., 1], home_px[..., 2]
home_water = (hb > hr + 25) & (hb > 120) & (hb > hg - 10)
home_water |= (hr > 200) & (hg > 225) & (hb > 225)                     # foam counts as water
home_water = ndimage.binary_opening(home_water, iterations=1)
home_land = ndimage.binary_opening(~home_water, iterations=2)
HX, HY = OX // F, OY // F
HW, HH = HOME_W // F, HOME_H // F
home_land_a = np.array(Image.fromarray(home_land.astype(np.uint8) * 255).resize((HW, HH), Image.BOX)) > 127

# land cut off by the picture's top, left and right edges (islets): finish them with a rounded cap
caps = []
for edge_name in ("top", "left", "right"):
    line = {"top": home_land_a[0], "left": home_land_a[:, 0], "right": home_land_a[:, -1]}[edge_name]
    i = 0
    while i < len(line):
        if line[i]:
            j = i
            while j < len(line) and line[j]:
                j += 1
            if j - i >= 4:
                caps.append((edge_name, i, j))
            i = j
        else:
            i += 1
# only real islets get a cap: not the big tree's leaves or the rocks that touch the top edge
# (picture x 540-700 and 990-1080); the game draws its own tree and a rock over those
NOT_ISLETS = [(540, 700), (990, 1080)]
caps = [c for c in caps if not (c[0] == "top" and any(c[1] * F < b and c[2] * F > a for a, b in NOT_ISLETS))]
log("home island islets cut by the picture edge:", caps)


# ------------------------------------------------------------------------------------------------
# Shapes
# ------------------------------------------------------------------------------------------------
def poly_mask(points, wobble_amp=0.0, wobble_cell=60, seed=0):
    img = Image.new("L", (AW, AH), 0)
    ImageDraw.Draw(img).polygon([(A(x), A(y)) for x, y in points], fill=255)
    m = np.asarray(img) > 127
    if wobble_amp:
        sd = dist_in(m) - dist_out(m)
        wob = fbm((AH, AW), wobble_cell, 4, seed) * wobble_amp + fbm((AH, AW), 9, 2, seed + 7) * 1.6
        m = sd + wob > 0
    return m


def ellipse_mask(cx, cy, rx, ry, wobble_amp=0.0, seed=0):
    y, x = np.ogrid[:AH, :AW]
    d = np.sqrt(((x - A(cx)) / A(rx)) ** 2 + ((y - A(cy)) / A(ry)) ** 2)
    sd = (1 - d) * min(A(rx), A(ry))
    if wobble_amp:
        sd = sd + fbm((AH, AW), 30, 3, seed) * wobble_amp
    return sd > 0


def zone_weights():
    y, x = np.mgrid[:AH, :AW].astype(np.float32)
    ws = {}
    for k, ((cx, cy), r) in ZONES.items():
        d = np.sqrt((x - A(cx)) ** 2 + (y - A(cy)) ** 2) / A(r)
        ws[k] = np.exp(-(d ** 2) * 1.6)
    return ws


log("shapes")
home_box = np.zeros((AH, AW), bool)
home_box[HY:HY + HH, HX:HX + HW] = True
home_land_w = np.zeros((AH, AW), bool)
home_land_w[HY:HY + HH, HX:HX + HW] = home_land_a

wob_big = fbm((AH, AW), 70, 4, 11)
land = poly_mask(COAST, 20, 90, 11)
land &= ~grow(home_box, 40)           # keep a channel of sea around the home island
for i, (cx, cy, rx, ry) in enumerate(ISLETS):
    land |= ellipse_mask(cx, cy, rx, ry, 5, 40 + i)

# caps that finish the home island's cut-off islets, just outside the picture
cap_mask = np.zeros((AH, AW), bool)
for edge_name, i, j in caps:
    r_out = int(np.clip((j - i) * 0.45, 8, 30))
    img = Image.new("L", (AW, AH), 0)
    d = ImageDraw.Draw(img)
    if edge_name == "top":
        d.ellipse((HX + i, HY - r_out, HX + j - 1, HY + r_out), fill=255)
    elif edge_name == "left":
        d.ellipse((HX - r_out, HY + i, HX + r_out, HY + j - 1), fill=255)
    else:
        d.ellipse((HX + HW - r_out, HY + i, HX + HW + r_out, HY + j - 1), fill=255)
    # outside the picture the cap is new land; inside it, it follows the painted islet exactly, so
    # wherever the picture's edge fades out, grass shows under grass
    cap_mask |= (np.asarray(img) > 127) & (~home_box | home_land_w)
land |= cap_mask

beach_areas = np.zeros((AH, AW), bool)
for i, b in enumerate(BEACHES):
    beach_areas |= poly_mask(b, 10, 50, 21 + i)
beach_areas &= ~grow(home_box, 40)

water_in = np.zeros((AH, AW), bool)
for i, (cx, cy, rx, ry) in enumerate(PONDS):
    water_in |= ellipse_mask(cx, cy, rx, ry, 4, 60 + i)
creek_pts = [(A(x), A(y)) for x, y in smooth_curve(CREEK, 12)]
water_in |= polyline_mask((AH, AW), creek_pts, 20, fbm((AH, AW), 40, 2, 70) * 2.5)
water_in &= land

paths = np.zeros((AH, AW), bool)
path_wob = fbm((AH, AW), 60, 2, 80) * 4.0 + fbm((AH, AW), 12, 2, 81) * 2.2
for w, pts in PATHS:
    paths |= polyline_mask((AH, AW), [(A(x), A(y)) for x, y in smooth_curve(pts, 10)], A(w), path_wob)

grass_top = land & ~beach_areas & ~water_in
grass_top = ndimage.binary_opening(grass_top, iterations=2)
paths &= grass_top

# no cliff next to beaches (the cliff gets lower as it nears them)
gentle = np.clip(1 - (dist_out(beach_areas) - 3) / 22, 0, 1).astype(np.float32)
yy, xx = np.mgrid[:AH, :AW].astype(np.float32)
for cx, cy, r in GENTLE:
    d = np.sqrt((xx - A(cx)) ** 2 + (yy - A(cy)) ** 2) / A(r)
    gentle = np.maximum(gentle, np.clip((1.25 - d) / 0.35, 0, 1))

H_COAST = 15
cliff_h = np.clip(H_COAST + wob_big * 3, 11, 19) * (1 - gentle)
cliff_h = np.where(grow(water_in, 6), 3.0, cliff_h)
cliff_h = np.where(grow(cap_mask, 2), np.minimum(cliff_h, 9), cliff_h)   # islet caps: low cliffs like the painted ones
cliff_h = np.round(cliff_h).astype(int)
cliff_h[~grass_top] = 0

cliff = np.zeros((AH, AW), bool)
cliff_t = np.zeros((AH, AW), np.int16)
cliff_n = np.zeros((AH, AW), np.int16)
hsrc = np.where(grass_top, cliff_h, 0).astype(np.int16)
for k in range(1, int(cliff_h.max()) + 1):
    moved = shift(hsrc, dy=k)
    hit = (moved >= k) & ~grass_top & ~cliff
    cliff |= hit
    cliff_t[hit] = k - 1
    cliff_n[hit] = moved[hit]
cliff &= ~home_box

side = (shift(grass_top, dx=1) | shift(grass_top, dx=-1) | shift(grass_top, dx=2) | shift(grass_top, dx=-2)) & ~grass_top & ~cliff
side &= ~shift(grass_top, dy=-1) & ~home_box
side_n = side & (gentle < 0.5)

solid = grass_top | cliff | side_n
foot = np.zeros((AH, AW), bool)
strip = np.clip(6 + wob_big * 3, 3, 9).astype(int)
for k in range(1, 10):
    foot |= shift(solid, dy=k) & (strip >= k)
sand = (beach_areas | foot) & ~solid & ~home_box
sand |= grow(water_in, 2) & ~water_in & ~grass_top & ~cliff & land
sand &= ~water_in

island = solid | sand
all_land = island | home_land_w                  # the sea treats the painted island as land too
water = ~island & ~home_box
water_in &= ~cliff
sea = water & ~water_in
log("shapes done", "grass", int(grass_top.sum()), "cliff", int(cliff.sum()), "sand", int(sand.sum()))

prev = np.zeros((AH, AW, 3), np.uint8)
prev[:] = C["sea"]
prev[water_in] = C["shallow"]
prev[sand] = C["sand"]
prev[grass_top] = C["grass"]
prev[paths] = C["path"]
prev[cliff] = C["cliff"]
prev[side_n] = C["cliff_lo"]
prev[HY:HY + HH, HX:HX + HW] = np.array(home_src.resize((HW, HH), Image.BOX))
Image.fromarray(prev).save(ROOT / "check" / "world_layout.png")
log("wrote check/world_layout.png")


# ------------------------------------------------------------------------------------------------
# Painting the ground
# ------------------------------------------------------------------------------------------------
rng = np.random.default_rng(5)
img = np.zeros((AH, AW, 3), np.uint8)
grain = rng.random((AH, AW)).astype(np.float32)          # per-pixel randomness
grain2 = ndimage.uniform_filter(grain, 3)                  # tiny pixel clusters instead of salt and pepper


def pick(levels, idx):
    """levels: list of colours; idx: int array -> rgb image"""
    lut = np.stack([C[k] if isinstance(k, str) else k for k in levels])
    return lut[np.clip(idx, 0, len(levels) - 1)]


# ---- water
log("water")
water_all = ~island                        # the home island's picture covers its own part later
d_w = ndimage.distance_transform_edt(np.pad(~all_land, 40, constant_values=True))[40:-40, 40:-40]  # how far from the nearest shore
d_w_in = np.where(water_in, d_w, 0)
wob_w = fbm((AH, AW), 26, 3, 90)
t = d_w + wob_w * 4 + (grain2 - 0.5) * 3
band = np.select([t < 4, t < 10, t < 22, t < 70], [0, 1, 2, 3], 4)
band = np.where(water_in, np.minimum(band, 2), band)      # ponds and the creek stay shallow and bright
water_rgb = pick(["shallow_hi", "shallow", "sea_hi", "sea", "sea_deep"], band)
img[water_all] = water_rgb[water_all]

# ripple lines: edges of loose cells, broken into dashes
cell = 26.0
gy, gx = int(AH / cell) + 3, int(AW / cell) + 3
seeds = (np.stack(np.meshgrid(np.arange(gx), np.arange(gy)), -1) + rng.random((gy, gx, 2)) * 0.9 + 0.05) * cell
yy_i, xx_i = np.mgrid[:AH, :AW]
cx_i, cy_i = (xx_i / cell).astype(int), (yy_i / cell).astype(int)
f1 = np.full((AH, AW), 1e9, np.float32)
f2 = np.full((AH, AW), 1e9, np.float32)
for oy in (-1, 0, 1):
    for ox in (-1, 0, 1):
        sy = np.clip(cy_i + oy, 0, gy - 1)
        sx = np.clip(cx_i + ox, 0, gx - 1)
        s = seeds[sy, sx]
        dd = np.sqrt((s[..., 0] - xx_i) ** 2 + ((s[..., 1] - yy_i) * 1.35) ** 2).astype(np.float32)
        f2 = np.where(dd < f1, f1, np.minimum(f2, dd))
        f1 = np.minimum(f1, dd)
edge = (f2 - f1) < 1.0
dash = fbm((AH, AW), 9, 2, 91) > 0.22
ripple = water_all & edge & dash & (d_w > 5)
img[ripple & (band >= 3)] = C["sea_hi"]
img[ripple & (band == 2)] = C["ripple"]
img[ripple & (band < 2)] = C["shallow_hi"]
del f1, f2, seeds, yy_i, xx_i, cx_i, cy_i

# foam along every shore, and a broken second line a little way out at sea
foam1 = water_all & (d_w <= 1.6)
foam2 = water_all & (d_w > 1.6) & (d_w <= 2.6)
img[foam2] = C["foam_lo"]
img[foam1] = C["foam"]
ring = water_all & ~water_in & (np.abs(d_w - (7 + wob_w * 2.2)) < 0.75) & (fbm((AH, AW), 11, 2, 92) > -0.25)
img[ring] = C["foam_lo"]
sparkle = water_all & ~water_in & (d_w > 12) & (grain > 0.9993)
img[sparkle] = C["foam"]

# ---- sand
log("sand")
d_sand_w = dist_out(water_all)
s_mottle = fbm((AH, AW), 12, 3, 93)
sand_lvl = np.where(s_mottle > 0.5, 0, 1) + (grain2 > 0.62)
sand_rgb = pick(["sand_lo", "sand", "sand_hi"], sand_lvl)
img[sand] = sand_rgb[sand]
img[sand & (d_sand_w <= 2.5)] = C["sand_hi"]
under_cliff = sand & (shift(cliff | side_n, dy=1) | shift(cliff | side_n, dy=2))
img[under_cliff] = C["sand_sh"]

# ---- cliff faces: one or two rows of stone blocks
log("cliffs")
cols = np.zeros(AW, np.int32)
x = 0
bnd = np.zeros(AW, bool)
while x < AW:
    bnd[x] = True
    x += int(rng.integers(7, 14))
bnd2 = np.roll(bnd, 5)
slab_id = np.cumsum(bnd)
slab_id2 = np.cumsum(bnd2)
shade = rng.random(slab_id.max() + 2) < 0.35
shade2 = rng.random(slab_id2.max() + 2) < 0.35
tt, nn = cliff_t.astype(int), cliff_n.astype(int)
two_rows = nn >= 10
split = nn // 2
lower = two_rows & (tt >= split)
xs_all = np.broadcast_to(np.arange(AW), (AH, AW))
is_bnd = np.where(lower, bnd2[xs_all], bnd[xs_all])
is_left = np.where(lower, np.roll(bnd2, 1)[xs_all], np.roll(bnd, 1)[xs_all])
dark_slab = np.where(lower, shade2[slab_id2[xs_all]], shade[slab_id[xs_all]])
cl = np.full((AH, AW), 1, np.int8)                            # 0 top, 1 face, 2 face dark, 3 low, 4 line, 5 base, 6 light edge
cl[dark_slab] = 2
cl[is_left] = 6
cl[(tt >= nn - 3)] = 3
cl[is_bnd & (tt > 0)] = 4
cl[two_rows & (tt == split)] = 4
cl[two_rows & (tt == split + 1)] = 6
cl[tt <= 1] = 0
cl[(tt == nn - 1) & (nn > 3)] = 5
low = nn <= 4                                                  # pond banks: plain earth, no blocks
cl[low] = np.select([tt[low] == 0, tt[low] == nn[low] - 1], [0, 3], 2)
cliff_rgb = pick(["cliff_top", "cliff", "cliff_mid", "cliff_lo", "cliff_ln", "cliff_base", "cliff_top"], cl)
img[cliff] = cliff_rgb[cliff]
img[side_n] = C["cliff_lo"]
img[side_n & ~shift(side_n, dx=1) & ~shift(side_n, dx=-1)] = C["cliff_ln"]

# ---- grass: calm mottled field, darker in the forest
log("grass")
zw = zone_weights()
forestness = np.clip(zw["forest"] * 1.4, 0, 1)
meadowness = np.clip(zw["meadow"] * 1.2, 0, 1)
g_mottle = fbm((AH, AW), 34, 3, 94)
tone = 3.0 - forestness * 1.6 + meadowness * 0.35 + g_mottle * 0.75 + (grain2 - 0.5) * 0.9
g_lvl = np.floor(tone).astype(int)
grass_rgb = pick(["forest_lo", "forest", "grass_lo", "grass", "grass_hi"], g_lvl)
img[grass_top] = grass_rgb[grass_top]

# little grass tufts and flowers, stamped on (d = dark blade, m = mid, w/p/y = flower petals, o = flower middle)
STAMPS = {
    "tuft1": ["d.d.d", ".ddd."],
    "tuft2": [".d.d.", "d.d.d", ".ddd."],
    "tuft3": ["d..d", ".dd."],
    "clump": [".mm.", "mddm", ".dd."],
    "clump2": [".m.m.", "mmdmm", ".ddd."],
    "fw": [".w.", "wow", ".w."],
    "fp": [".p.", "pop", ".p."],
    "fy": [".y.", "yoy", ".y."],
}
STAMP_COL = {"d": C["tuft_dk"], "m": C["tuft"], "w": hexrgb("#fcfcf4"), "p": hexrgb("#f8a8bc"),
             "y": hexrgb("#fcd84c"), "o": hexrgb("#f0a030")}


def stamp(name, x, y, where):
    rows = STAMPS[name]
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == ".":
                continue
            px, py = int(x) + i, int(y) + j
            if 0 <= px < AW and 0 <= py < AH and where[py, px]:
                img[py, px] = STAMP_COL[ch]


log("tufts")
open_grass = grass_top & ~grow(paths, 2) & ~grow(~grass_top, 3)
for i, (x, y) in enumerate(poisson(open_grass, 11 if not QUICK else 20, seed=95)):
    f = forestness[int(y), int(x)]
    r = rng.random()
    if r < 0.45 + f * 0.3:
        stamp(["tuft1", "tuft2", "tuft3"][i % 3], x, y, open_grass)
    elif r < 0.7:
        stamp(["clump", "clump2"][i % 2], x, y, open_grass)
flower_bias = np.clip(zw["meadow"] * 1.6 + zw["orchard"] * 0.5 + zw["hill"] * 0.3, 0, 1)
for i, (x, y) in enumerate(poisson(open_grass, 9 if not QUICK else 18, seed=96)):
    if rng.random() < 0.05 + flower_bias[int(y), int(x)] * 0.35:
        stamp(["fw", "fp", "fy"][int(rng.integers(0, 3))], x, y, open_grass)

# ---- the grass edge: a dark line with little bumps of grass hanging over cliffs, sand and water
log("grass edge")
sd = ndimage.gaussian_filter((dist_in(grass_top) - dist_out(grass_top)).astype(np.float32), 1.5)
ny, nx = np.gradient(sd)
rim_px = grass_top & ~shrink(grass_top, 1) & ~paths
lip = grass_top.copy()
for (x, y) in poisson(rim_px, 5.0, seed=97):
    xi, yi = int(x), int(y)
    vx, vy = -nx[yi, xi], -ny[yi, xi]
    ln = np.hypot(vx, vy) + 1e-6
    vx, vy = vx / ln, vy / ln
    r = rng.uniform(2.0, 3.4)
    cx, cy = x + vx * 1.3, y + vy * 1.3
    x0, x1 = int(cx - r - 1), int(cx + r + 2)
    y0, y1 = int(cy - r - 1), int(cy + r + 2)
    if x0 < 0 or y0 < 0 or x1 >= AW or y1 >= AH:
        continue
    yy2, xx2 = np.mgrid[y0:y1, x0:x1]
    lip[y0:y1, x0:x1] |= (xx2 - cx) ** 2 + (yy2 - cy) ** 2 <= r * r
lip &= ~paths | grass_top
lip &= ~grow(beach_areas & ~grass_top, 0) | grass_top | ~paths
added = lip & ~grass_top
img[added] = C["grass"]
outline = lip & ~shrink(lip, 1)
outline &= ~(paths & grass_top)
inner = grass_top & ~shrink(grass_top, 2) & ~outline & ~paths
img[inner] = C["lip"]
img[outline] = C["edge_dk"]
grass_top_draw = lip  # what reads as grass now (used for placing things)

# ---- paths
log("paths")
pth = paths & grass_top
p_mottle = fbm((AH, AW), 14, 3, 98)
p_lvl = 1 - (p_mottle > 0.42).astype(int) + (grain2 > 0.66).astype(int)
path_rgb = pick(["path_lo", "path", "path_hi"], p_lvl)
img[pth] = path_rgb[pth]
p_rim = pth & ~shrink(pth, 1) & shift(grass_top, 0) & grow(grass_top & ~paths, 1)
img[p_rim] = C["path_rim"]
# grass creeping over the path edge
p_edge = pth & grow(grass_top & ~paths, 1)
for (x, y) in poisson(p_edge, 6.0, seed=99):
    xi, yi = int(x), int(y)
    r = rng.uniform(1.0, 2.0)
    for j in range(-2, 3):
        for i in range(-2, 3):
            if i * i + j * j <= r * r + 0.5 and 0 <= xi + i < AW and 0 <= yi + j < AH and pth[yi + j, xi + i]:
                img[yi + j, xi + i] = C["grass"]
# pebbles
for (x, y) in poisson(shrink(pth, 3), 16, seed=100):
    if rng.random() < 0.5:
        xi, yi = int(x), int(y)
        img[yi, xi] = C["pebble"]
        if rng.random() < 0.5:
            img[yi, xi + 1] = C["pebble"]
        img[yi - 1, xi] = C["path_hi"]

log("painted")
Image.fromarray(img).save(ROOT / "check" / "world_ground_raw.png")


def crops_sheet(name, spots, cw=300, ch=220, zoom=2):
    sheet = Image.new("RGB", (cw * zoom * 3 + 20, (ch * zoom + 20) * ((len(spots) + 2) // 3)), "#222")
    d = ImageDraw.Draw(sheet)
    for i, (label, (lx, ly)) in enumerate(spots):
        ax, ay = int(A(lx)) - cw // 2, int(A(ly)) - ch // 2
        c = Image.fromarray(img[max(0, ay):ay + ch, max(0, ax):ax + cw]).resize((cw * zoom, ch * zoom), Image.NEAREST)
        x, y = (i % 3) * (cw * zoom + 10), (i // 3) * (ch * zoom + 20)
        sheet.paste(c, (x, y + 20))
        d.text((x + 4, y + 4), f"{label} ({lx},{ly})", fill="white")
    sheet.save(ROOT / "check" / name)


crops_sheet("world_crops.png", [
    ("north channel cliff", (2300, 2160)), ("west bridge", (1480, 2835)), ("islet caps", (1800, 2360)),
    ("wetland", (2250, 1750)), ("sw beach", (800, 2950)), ("east bridge", (3140, 2795)),
])
log("wrote check/world_crops.png")

Image.fromarray(img).save(OUT / "ground.webp", lossless=True, method=6)
log("wrote public/world/ground.webp", (OUT / "ground.webp").stat().st_size // 1024, "KB")

# ------------------------------------------------------------------------------------------------
# The painted island, with its outer water faded into the new sea (dithered on the art-pixel grid,
# so the join has no line). Its bottom edge is the edge of the world, so that side stays as it is.
# ------------------------------------------------------------------------------------------------
log("home picture")
home2 = np.array(Image.open(ROOT / "public" / "assets" / "island.webp").convert("RGBA"))    # 2x
ylog = np.arange(HOME_H)[:, None]
xlog = np.arange(HOME_W)[None, :]
d_edge = np.minimum(np.minimum(ylog, xlog), HOME_W - 1 - xlog).astype(np.float32)
b_log = np.repeat(np.repeat(bayer((HOME_H // 2 + 1, HOME_W // 2 + 1)), 2, 0), 2, 1)[:HOME_H, :HOME_W]
keep_water = np.clip(d_edge / 44.0, 0, 1) > b_log
keep_land = np.clip(d_edge / 8.0, 0, 1) > b_log
alpha_log = np.where(home_water, keep_water, keep_land)
home2[..., 3] = np.repeat(np.repeat(alpha_log, 2, 0), 2, 1) * 255
Image.fromarray(home2).save(OUT / "home.webp", lossless=True, method=6, exact=True)
log("wrote public/world/home.webp", (OUT / "home.webp").stat().st_size // 1024, "KB")

# whole-world preview at art size: new ground with the home island on top
comp = Image.fromarray(img).convert("RGBA")
home_small = Image.fromarray(home2).resize((HW, HH), Image.NEAREST)
comp.alpha_composite(home_small, (HX, HY))
comp.convert("RGB").save(ROOT / "check" / "world_composite.png")
img_comp = np.array(comp.convert("RGB"))


def seam_sheet(name, spots, cw=260, ch=190, zoom=3):
    sheet = Image.new("RGB", (cw * zoom * 2 + 10, (ch * zoom + 20) * ((len(spots) + 1) // 2)), "#222")
    d = ImageDraw.Draw(sheet)
    for i, (label, (lx, ly)) in enumerate(spots):
        ax, ay = int(A(lx)) - cw // 2, int(A(ly)) - ch // 2
        c = Image.fromarray(img_comp[max(0, ay):ay + ch, max(0, ax):ax + cw]).resize((cw * zoom, ch * zoom), Image.NEAREST)
        x, y = (i % 2) * (cw * zoom + 10), (i // 2) * (ch * zoom + 20)
        sheet.paste(c, (x, y + 20))
        d.text((x + 4, y + 4), f"{label} ({lx},{ly})", fill="white")
    sheet.save(ROOT / "check" / name)


seam_sheet("world_seams.png", [
    ("top-left of home", (OX + 150, OY - 20)), ("top-right of home", (OX + 1250, OY - 20)),
    ("left edge of home", (OX, OY + 450)), ("right edge of home", (OX + HOME_W, OY + 450)),
])
log("wrote check/world_seams.png")
