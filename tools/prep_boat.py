"""Boat and wake pictures for sailing between the islands, matched to the islands' chunky pixels.

Run from the game folder:  python tools/prep_boat.py
Reads source_art/school/objects/boat/, writes public/boat/ (2x pictures) and src/boatInfo.json.
"""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from pixelate import chunky, make_palette, pixelate_mode  # noqa: E402

SRC = ROOT / "source_art" / "school" / "objects" / "boat"
OUT = ROOT / "public" / "boat"
OUT.mkdir(parents=True, exist_ok=True)
SCALE = 0.62  # boat size on the islands
BLOCK = 2
TEX = 2

pal = make_palette(Image.open(SRC / "boat_capy_down.png"), 48)
sizes = {}
for kind in ("empty", "capy"):
    for d in ("up", "down", "left", "right"):
        img = Image.open(SRC / f"boat_{kind}_{d}.png").convert("RGBA")
        img = img.crop(img.getbbox())
        px = pixelate_mode(img, img.width * SCALE, img.height * SCALE, BLOCK, pal=pal)
        chunky(px, BLOCK * TEX).save(OUT / f"boat_{kind}_{d}.png", optimize=True)
        sizes[f"boat_{kind}_{d}"] = [px.width * BLOCK, px.height * BLOCK]

# wakes keep their full canvas so the four frames line up; tip = where the V meets the boat's bow
wpal = make_palette(Image.open(SRC / "wake" / "wake_down_03.png"), 16)
for d in ("up", "down"):
    for f in range(1, 5):
        img = Image.open(SRC / "wake" / f"wake_{d}_{f:02d}.png").convert("RGBA")
        px = pixelate_mode(img, img.width * SCALE, img.height * SCALE, BLOCK, pal=wpal)
        chunky(px, BLOCK * TEX).save(OUT / f"wake_{d}_{f}.png", optimize=True)
        sizes[f"wake_{d}"] = [px.width * BLOCK, px.height * BLOCK]

icon = Image.open(SRC / "boat_empty_right.png").convert("RGBA")
icon = icon.crop(icon.getbbox())
icon.thumbnail((64, 64))
icon.save(OUT / "icon.png", optimize=True)

info = {"sizes": sizes, "wakeTip": {"down": 0.84, "up": 0.12}}
(ROOT / "src" / "boatInfo.json").write_text(json.dumps(info, indent=1))
print(json.dumps(sizes))
