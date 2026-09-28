"""Create numbered contact sheets for selecting crisp world sprites."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "concepts" / "asset-catalog"
OUT.mkdir(parents=True, exist_ok=True)


def components(path, minimum=300):
    image = Image.open(path).convert("RGBA")
    alpha = np.asarray(image)[..., 3] > 20
    joined = ndimage.binary_dilation(alpha, iterations=2)
    labels, _ = ndimage.label(joined)
    entries = []
    for label_id, slices in enumerate(ndimage.find_objects(labels), 1):
        if slices is None:
            continue
        ys, xs = slices
        region = (labels[ys, xs] == label_id) & alpha[ys, xs]
        if int(region.sum()) < minimum:
            continue
        rgba = np.asarray(image)[ys, xs].copy()
        rgba[~region] = 0
        sprite = Image.fromarray(rgba)
        entries.append((xs.start, ys.start, sprite))
    entries.sort(key=lambda item: (item[1] // 40, item[0]))
    return entries


def contact(name):
    entries = components(ROOT / "source_art" / f"{name}.png")
    thumb_w, thumb_h = 190, 170
    columns = 7
    rows = (len(entries) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * thumb_w, rows * thumb_h), "#172f28")
    draw = ImageDraw.Draw(sheet)
    for index, (x, y, sprite) in enumerate(entries):
        cell_x = (index % columns) * thumb_w
        cell_y = (index // columns) * thumb_h
        scale = min(1, 150 / max(sprite.width, 1), 130 / max(sprite.height, 1))
        preview = sprite.resize((max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))), Image.Resampling.NEAREST)
        px = cell_x + (thumb_w - preview.width) // 2
        py = cell_y + 26 + (132 - preview.height) // 2
        sheet.paste(preview, (px, py), preview)
        draw.text((cell_x + 8, cell_y + 7), f"{index:02d}  src {x},{y}  {sprite.width}x{sprite.height}", fill="#ffffff")
    output = OUT / f"{name}-catalog.png"
    sheet.save(output)
    print(name, len(entries), output)


for sheet_name in ["terrain_tiles", "nature_props", "buildings_structures"]:
    contact(sheet_name)

