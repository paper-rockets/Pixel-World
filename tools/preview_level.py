"""Draws the walk area, walls and hiding spots on top of the island so they can be checked by eye.
Run: python tools/preview_level.py  -> writes level_preview.png in the game folder."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
lv = json.loads((ROOT / "src/level.json").read_text())
A = ROOT / "public/assets"
base = Image.open(A / "island.webp").convert("RGBA")
base = base.resize((base.width // 2, base.height // 2), Image.LANCZOS)
ov = Image.new("RGBA", base.size, (0, 0, 0, 0))
d = ImageDraw.Draw(ov)
d.polygon([tuple(p) for p in lv["walkable"]], outline=(0, 255, 60, 255), width=3)
for b in lv["blockers"]:
    if b["type"] == "rect":
        d.rectangle((b["x"], b["y"], b["x"] + b["w"], b["y"] + b["h"]), fill=(255, 0, 0, 70), outline=(255, 0, 0, 200))
    else:
        d.ellipse((b["x"] - b["rx"], b["y"] - b["ry"], b["x"] + b["rx"], b["y"] + b["ry"]), fill=(255, 0, 0, 70), outline=(255, 0, 0, 200))
z = lv["homeZone"]
d.ellipse((z["x"] - z["r"], z["y"] - z["r"], z["x"] + z["r"], z["y"] + z["r"]), outline=(255, 255, 0, 255), width=3)
base.alpha_composite(ov)
for s in lv["spots"]:
    c = Image.open(A / f"cover_{s['cover']}.png").convert("RGBA")
    c = c.resize((round(c.width * s["scale"]), round(c.height * s["scale"])), Image.LANCZOS)
    base.alpha_composite(c, (round(s["x"] - c.width / 2), round(s["y"] - c.height)))
duck = Image.open(A / "duck.png").convert("RGBA")
fw = json.loads((ROOT / "src/assetInfo.json").read_text())["duck"]["frameWidth"]
f0 = duck.crop((0, 0, fw, duck.height)).resize((fw // 2, duck.height // 2), Image.LANCZOS)
base.alpha_composite(f0, (lv["mommy"][0] - f0.width // 2, lv["mommy"][1] - f0.height))
chick = Image.open(A / "duckling.png").convert("RGBA")
cw = json.loads((ROOT / "src/assetInfo.json").read_text())["duckling"]["frameWidth"]
c0 = chick.crop((0, 0, cw, chick.height)).resize((round(cw * .37), round(chick.height * .37)), Image.LANCZOS)
for x, y in lv["homeSlots"]:
    base.alpha_composite(c0, (x - c0.width // 2, y - c0.height))
d = ImageDraw.Draw(base)
sx, sy = lv["start"]
d.ellipse((sx - 8, sy - 8, sx + 8, sy + 8), fill=(0, 120, 255, 255))
base.convert("RGB").save(ROOT / "level_preview.png")
print("ok")
