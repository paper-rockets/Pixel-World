"""Checks a new island ground picture (from Codex) against the home island, source_art/tiny_map.png.

Run from the game folder:
  python tools/review_island.py source_art/archipelago/ground/sw_campfire.png [x y]
  x y (optional): where the picture's top-left corner goes in the big map (game pixels), for the
  layout preview. Known file names already have their planned spot (see PLANNED).

Prints how each ground material (grass, path, beach sand, cliff face, water) compares with the home
island: colour, colour strength and texture. Also checks the size, the sea around the island, and how
wide the paths are compared with the capybara.

Writes check/review_<name>.png: both islands side by side at the same scale, close-ups of the new
island next to the same kind of ground on the home island, the capybara at game size on the new
island's narrowest path, and colour swatches.
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from world_paint import bayer  # noqa: E402

# the home island as the game shows it: tiny_map.png with the painted animals and boat painted out
# (stored at 2x with doubled pixels, so every second pixel is the 1x picture)
HOME_FILE = ROOT / "public" / "assets" / "island.webp"
HOME_AT = (1580, 1300)            # the home island's top-left corner in the big map
PLANNED = {                       # the new islands' planned top-left corners (see HANDOFF.md)
    "w_caves_pinktree": (440, 420),
    "sw_campfire": (160, 1780),
    "n_orchard": (1500, 60),
    "ne_pond": (3000, 60),
    "se_meadow": (3100, 1560),
}
SEA = (77, 192, 230)              # the game's sea colour, #4dc0e6
CAPY_W = 50                       # the capybara's body width at game size (facing down)
MIN_PATH = 60                     # narrowest path that doesn't look cramped (home paths are 60-75)

# Plain open ground on the home island to compare with (x0, y0, x1, y1), picked by eye:
# no trees, bushes, rocks, fences, animals or wood in these boxes.
HOME_BOXES = {
    "grass": [(560, 520, 700, 670), (1150, 400, 1250, 470), (100, 420, 260, 520), (420, 470, 560, 560)],
    "path": [(700, 480, 760, 700), (460, 470, 660, 520)],
    "sand": [(150, 720, 330, 800), (1200, 800, 1350, 860)],
    "cliff": [(40, 600, 330, 760), (380, 760, 600, 840), (1150, 760, 1420, 880)],
    "water": [(60, 900, 300, 1086), (1100, 960, 1448, 1086), (40, 640, 300, 900)],
}
# close-ups of the home island for each kind of ground (top-left corner, 1x)
HOME_CLOSE = {"cliff": (1170, 720), "grass": (560, 520), "shore": (60, 660)}
CLOSE = (200, 130)                # close-up size at 1x
ZOOM = 3
NAMES = {"grass": "grass", "path": "path", "sand": "beach sand", "cliff": "cliff face", "water": "water"}


def hsv(img):
    f = img.astype(np.float32) / 255.0
    mx, mn = f.max(-1), f.min(-1)
    d = mx - mn
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    h = np.zeros(mx.shape, np.float32)
    m = d > 1e-6
    i = m & (mx == r)
    h[i] = ((g - b)[i] / d[i]) % 6
    i = m & (mx == g) & ~(mx == r)
    h[i] = (b - r)[i] / d[i] + 2
    i = m & (mx == b) & ~(mx == r) & ~(mx == g)
    h[i] = (r - g)[i] / d[i] + 4
    return h * 60, np.where(mx > 0, d / np.maximum(mx, 1e-6), 0), mx


def materials(img):
    """Masks for each ground material, from colour alone (fine for a ground-only picture)."""
    h, s, v = hsv(img)
    white = (v > 0.88) & (s < 0.12)
    water = ((h > 170) & (h < 215) & (s > 0.15)) | white
    grass = (h > 55) & (h < 130) & (s > 0.2) & (v > 0.72)
    sandy = (h > 20) & (h < 55) & (s > 0.12) & (s < 0.56) & (v > 0.86)
    cliff = (h < 40) & (s > 0.25) & (v > 0.35) & (v < 0.95) & ~sandy
    # a path runs between grass: sand bordered mostly by grass is path, and sand bordered mostly by
    # cliffs and sea is beach (a path can run right down to the sea, and paths and beaches can be
    # painted in nearly the same colour, so neither tells them apart)
    beach = np.zeros_like(sandy)
    path = sandy
    greenish = (h > 55) & (h < 170) & (s > 0.2) & (v > 0.25)  # grass, including its dark edge lines
    lab, n = ndimage.label(path)
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        sl = tuple(slice(max(0, s.start - 14), s.stop + 14) for s in sl)
        part = lab[sl] == i
        # look 5-12 px out, past the thin blend line along a path's edge
        ring = ndimage.binary_dilation(part, iterations=12) & ~ndimage.binary_dilation(part, iterations=5)
        if greenish[sl][ring].mean() < 0.4:
            beach[sl] |= part
    return {"grass": grass, "path": sandy & ~beach, "sand": beach, "cliff": cliff, "water": water & ~white}


def texture(img, mask, win=16):
    """How much the brightness varies inside small squares that are mostly this material (0 = flat fill)."""
    lum = img.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    out = []
    for y in range(0, img.shape[0] - win, win):
        for x in range(0, img.shape[1] - win, win):
            if mask[y:y + win, x:x + win].mean() >= 0.85:
                out.append(lum[y:y + win, x:x + win].std())
    return float(np.median(out)) if out else float("nan")


def lab_of(rgb):
    return cv2.cvtColor(np.uint8([[rgb]]), cv2.COLOR_RGB2LAB)[0, 0].astype(np.float32) * [100 / 255, 1, 1] - [0, 128, 128]


def stats(img, mask):
    px = img[mask]
    if len(px) < 50:
        return None
    med = np.median(px, 0)
    h, s, v = hsv(med.reshape(1, 1, 3))
    return {"rgb": med, "sat": float(s[0, 0]) * 100, "tex": texture(img, mask), "n": int(mask.sum())}


def text_font(px):
    """Pillow's built-in font at this size (Pillow 10.1+), or its small basic font on older versions."""
    try:
        return ImageFont.load_default(size=px)
    except TypeError:
        return ImageFont.load_default()


def hexc(c):
    return "#%02X%02X%02X" % tuple(int(round(float(v))) for v in c)


def box_mask(shape, boxes):
    m = np.zeros(shape, bool)
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = True
    return m


def faded(img):
    """RGBA copy whose outer water dithers away over 44 px (on the 2 px art grid), like build_world.py."""
    h, w = img.shape[:2]
    hh, ss, vv = hsv(img)
    water = ((hh > 170) & (hh < 215) & (ss > 0.15)) | ((vv > 0.88) & (ss < 0.12))
    y, x = np.arange(h)[:, None], np.arange(w)[None, :]
    d = np.minimum(np.minimum(y, x), np.minimum(h - 1 - y, w - 1 - x)).astype(np.float32)
    b = np.repeat(np.repeat(bayer((h // 2 + 1, w // 2 + 1)), 2, 0), 2, 1)[:h, :w]
    keep = np.where(water, np.clip(d / 44.0, 0, 1) > b, True)
    return Image.fromarray(np.dstack([img, keep.astype(np.uint8) * 255]))


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = Path(sys.argv[1])
    name = path.stem
    raw = np.array(Image.open(path).convert("RGBA"))
    alpha = raw[..., 3] if (raw[..., 3] < 255).any() else None   # an island piece from match_island.py
    new = raw[..., :3].copy()
    if alpha is not None:
        new[alpha < 128] = SEA                                   # the big map's sea shows through
    home = np.ascontiguousarray(np.array(Image.open(HOME_FILE).convert("RGB"))[::2, ::2])
    at = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) >= 4 else PLANNED.get(re.sub(r"_v\d+$", "", name))  # sw_campfire_v2 -> sw_campfire
    info = path.with_suffix(".json")
    if at and len(sys.argv) < 4 and info.exists():
        pad = json.loads(info.read_text())["pad"]      # extra sea added around it by match_island.py
        at = (at[0] - pad, at[1] - pad)
    H, W = new.shape[:2]
    report = []

    def say(ok, text):
        ok = None if ok is None else bool(ok)
        mark = {True: "OK  ", False: "FIX ", None: "note"}[ok]
        report.append((ok, text))
        print(f"  [{mark}] {text}")

    print(f"Island check: {path.name} ({W} x {H}) against the home island")

    # ---- materials: colour, colour strength, texture
    hm = materials(home)
    nm = materials(new)
    _, s_new, v_new = hsv(new)
    foam = (v_new > 0.88) & (s_new < 0.12)
    shore_water = ndimage.distance_transform_edt(nm["water"] | foam) <= 100
    nm["water"] &= shore_water
    if alpha is not None:
        nm["water"] &= alpha >= 128      # only the piece's own water, not the plain sea shown through it
    rows = []
    for key in ["grass", "path", "sand", "cliff", "water"]:
        # on the home island the boxes already say which sand is path and which is beach
        hmask = hm["path"] | hm["sand"] if key in ("path", "sand") else hm[key]
        a = stats(home, hmask & box_mask(hmask.shape, HOME_BOXES[key]))
        b = stats(new, nm[key])
        if not b:
            say(None, f"{NAMES[key]}: none found in the new picture")
            continue
        rows.append((key, a, b))
        de = float(np.linalg.norm(lab_of(a["rgb"]) - lab_of(b["rgb"])))
        tex = b["tex"] / a["tex"] if a["tex"] > 0 else 1
        same_strength = abs(b["sat"] - a["sat"]) < 10
        what = f"{NAMES[key]}: home {hexc(a['rgb'])} (strength {a['sat']:.0f}%), new {hexc(b['rgb'])} (strength {b['sat']:.0f}%)"
        if de < 7 and same_strength:
            say(True, what + " - colour matches")
        elif de < 12 and same_strength:
            say(None, what + f" - colour is a little off, probably fine (difference {de:.0f}; under 7 looks the same)")
        else:
            word = "stronger" if b["sat"] > a["sat"] + 10 else "weaker" if b["sat"] < a["sat"] - 10 else "different"
            say(False, what + f" - colour is {word} (difference {de:.0f}; under 7 looks the same)")
        if not np.isnan(tex) and key in ("grass", "water"):
            if tex < 0.5:
                say(False, f"{NAMES[key]} texture: new {b['tex']:.1f} vs home {a['tex']:.1f} - much flatter than the home island")
            else:
                say(True, f"{NAMES[key]} texture: new {b['tex']:.1f} vs home {a['tex']:.1f}")

    # ---- size and sea around the island
    land = ndimage.binary_opening(~(nm["water"] | ~shore_water) & ~foam, iterations=2)
    lab, n = ndimage.label(land)
    sizes = ndimage.sum(land, lab, range(1, n + 1))
    big = lab == 1 + int(np.argmax(sizes))
    ys, xs = np.nonzero(big)
    margin = min(xs.min(), ys.min(), W - 1 - xs.max(), H - 1 - ys.max())
    say(margin >= 80, f"island {xs.max() - xs.min() + 1} x {ys.max() - ys.min() + 1}, closest sea edge {margin} px (need 80+)")
    specks = int(sum(1 for s in sizes if s > 200)) - 1
    if specks > 0:
        say(None, f"{specks} other patch(es) of land or colour in the sea")

    # ---- path width: twice the distance from the middle of the path to its edge, measured along
    # the middle line of every big stretch of path (small sandy specks don't count)
    pmask = ndimage.binary_opening(nm["path"], iterations=2)
    pmask = ndimage.binary_fill_holes(ndimage.binary_closing(pmask, iterations=3))  # pebbles on the path
    lab, n = ndimage.label(pmask)
    areas = ndimage.sum(pmask, lab, range(1, n + 1))
    pmask = np.isin(lab, 1 + np.flatnonzero(areas >= 2000))
    dt = ndimage.distance_transform_edt(pmask)
    ridge = (dt == ndimage.maximum_filter(dt, 5)) & (dt > 6)
    narrow = None
    if ridge.any():
        ry, rx = np.nonzero(ridge)
        widths = 2 * dt[ry, rx]
        typical = float(np.median(widths))
        # a narrow spot: the 10th-narrowest percent, so the rounded tip at a path's end doesn't count
        k = int(np.argsort(widths)[len(widths) // 10])
        narrow = (int(rx[k]), int(ry[k]), float(widths[k]))
        say(typical >= MIN_PATH, f"paths are about {typical:.0f} px wide (home paths are 60-75, the capybara is {CAPY_W}); "
            f"a narrow spot is {narrow[2]:.0f} px at ({narrow[0]}, {narrow[1]})")

    # ---- the picture
    font = text_font(22)
    small = text_font(17)
    cw, ch = CLOSE
    col_w = cw * ZOOM
    sheet_w = col_w * 2 + 30
    parts = []

    def title(text, size=font, pad=10):
        im = Image.new("RGB", (sheet_w, getattr(size, "size", 11) + pad * 2), (34, 34, 38))
        ImageDraw.Draw(im).text((12, pad), text, fill="white", font=size)
        return im

    what = "matched to the home island by tools/match_island.py" if path.parent.name == "islands" else "new"
    parts.append(title(f"Island check: {path.name} ({what}) vs the home island", font, 14))

    # the results, one line each
    res = Image.new("RGB", (sheet_w, 26 * len(report) + 12), (34, 34, 38))
    d = ImageDraw.Draw(res)
    for i, (ok, text) in enumerate(report):
        mark, colour = {True: ("OK", (120, 220, 120)), False: ("FIX", (255, 140, 110)), None: ("note", (200, 200, 200))}[ok]
        d.text((12, 6 + i * 26), mark, fill=colour, font=small)
        d.text((62, 6 + i * 26), text.split(" (difference")[0], fill="white", font=small)
    parts.append(res)

    # both islands in the big map, same scale
    if at:
        ww, wh = 4608, 3456
        world = Image.new("RGBA", (ww, wh), SEA + (255,))
        piece = Image.fromarray(np.dstack([new, alpha])) if alpha is not None else faded(new)
        world.alpha_composite(piece, at)
        world.alpha_composite(faded(home), HOME_AT)
        x0 = max(0, min(at[0], HOME_AT[0]) - 40)
        y0 = max(0, min(at[1], HOME_AT[1]) - 40)
        x1 = min(ww, max(at[0] + W, HOME_AT[0] + home.shape[1]) + 40)
        y1 = min(wh, max(at[1] + H, HOME_AT[1] + home.shape[0]) + 40)
        view = world.crop((x0, y0, x1, y1)).convert("RGB")
        s = sheet_w / view.width
        view = view.resize((sheet_w, round(view.height * s)), Image.LANCZOS)
        d = ImageDraw.Draw(view)
        for label, (lx, ly) in (("new", (at[0] + xs.min(), at[1] + ys.min())), ("home", HOME_AT)):
            px, py = (lx - x0) * s, (ly - y0) * s
            d.rectangle((px, py, px + 58, py + 26), fill=(34, 34, 38))
            d.text((px + 6, py + 3), label, fill="white", font=small)
        parts.append(title("Both islands where they are planned in the big map, same scale"))
        parts.append(view)

    # close-ups: the most cliff / grass / shore in the new picture, next to the same on the home island
    def best_window(score):
        sc = cv2.boxFilter(score.astype(np.float32), -1, (cw, ch), normalize=False, anchor=(0, 0),
                           borderType=cv2.BORDER_CONSTANT)[: H - ch, : W - cw]
        y, x = np.unravel_index(int(np.argmax(sc)), sc.shape)
        return int(x), int(y)

    sea_edge = ndimage.binary_dilation(nm["water"] | foam, iterations=3)
    shore = sea_edge & nm["sand"]            # a beach meeting the sea, like the home close-up
    if shore.sum() < 200:
        shore = sea_edge & (nm["grass"] | nm["cliff"])
    picks = {
        "cliff": best_window(nm["cliff"]),
        "grass": best_window(nm["grass"] & ~ndimage.binary_dilation(~nm["grass"], iterations=6)),
        "shore": best_window(shore),
    }
    for key, (nx, ny) in picks.items():
        hx, hy = HOME_CLOSE[key]
        row = Image.new("RGB", (sheet_w, ch * ZOOM), (34, 34, 38))
        row.paste(Image.fromarray(home[hy:hy + ch, hx:hx + cw]).resize((col_w, ch * ZOOM), Image.NEAREST), (10, 0))
        row.paste(Image.fromarray(new[ny:ny + ch, nx:nx + cw]).resize((col_w, ch * ZOOM), Image.NEAREST), (col_w + 20, 0))
        parts.append(title(f"{key}: home island ({hx}, {hy})  |  new ({nx}, {ny})   {ZOOM}x zoom", small, 6))
        parts.append(row)

    # the capybara at game size on the narrowest path of each island
    capy = Image.open(ROOT / "public" / "assets" / "capy.png").convert("RGBA")
    down = capy.crop((0, 0, 148, 128)).resize((74, 64), Image.NEAREST)

    def with_capy(img, fx, fy):
        pic = Image.fromarray(img).convert("RGBA")
        pic.alpha_composite(down, (int(fx - down.width / 2), int(fy - down.height * 0.97)))
        x0 = int(np.clip(fx - cw / 2, 0, pic.width - cw))
        y0 = int(np.clip(fy - ch * 0.6, 0, pic.height - ch))
        return pic.crop((x0, y0, x0 + cw, y0 + ch)).convert("RGB").resize((col_w, ch * ZOOM), Image.NEAREST)

    if narrow:
        row = Image.new("RGB", (sheet_w, ch * ZOOM), (34, 34, 38))
        row.paste(with_capy(home, 712, 700), (10, 0))
        row.paste(with_capy(new, narrow[0], narrow[1] + 20), (col_w + 20, 0))
        parts.append(title(f"the capybara at game size ({CAPY_W} px wide) on a path: home  |  new, narrowest spot", small, 6))
        parts.append(row)

    # colour swatches
    sw = Image.new("RGB", (sheet_w, 150), (34, 34, 38))
    d = ImageDraw.Draw(sw)
    bw = (sheet_w - 20) // max(1, len(rows))
    for i, (key, a, b) in enumerate(rows):
        x = 10 + i * bw
        d.text((x, 6), NAMES[key], fill="white", font=small)
        d.rectangle((x, 30, x + bw // 2 - 6, 100), fill=tuple(int(v) for v in a["rgb"]))
        d.rectangle((x + bw // 2, 30, x + bw - 12, 100), fill=tuple(int(v) for v in b["rgb"]))
        d.text((x, 106), f"home {a['sat']:.0f}%", fill="white", font=small)
        d.text((x + bw // 2, 106), f"new {b['sat']:.0f}%", fill="white", font=small)
    parts.append(title("colours (left = home, right = new; % = colour strength)", small, 6))
    parts.append(sw)

    total_h = sum(p.height for p in parts)
    sheet = Image.new("RGB", (sheet_w, total_h), (34, 34, 38))
    y = 0
    for p in parts:
        sheet.paste(p, (0, y))
        y += p.height
    matched = path.parent.name == "islands"                     # a piece made by tools/match_island.py
    out = ROOT / "check" / f"review_{name}{'_matched' if matched else ''}.png"
    out.parent.mkdir(exist_ok=True)
    sheet.save(out, optimize=True)
    fixes = sum(1 for ok, _ in report if ok is False)
    print(f"{fixes} thing(s) to fix. Wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
