"""Re-draws a picture with bigger, chunkier pixels so it matches the island's pixel size.

pixelate(img, out_w, out_h, block): shrinks `img` to (out_w, out_h) island pixels, but snaps it to a grid
of `block`-sized squares (the island's pixel size), keeps only the picture's own colours, and makes
every square either fully solid or fully see-through, like real pixel art.
"""
from PIL import Image
import numpy as np


def pixelate(img, out_w, out_h, block=4, colors=24):
    img = img.convert("RGBA")
    tw = max(1, round(out_w / block))
    th = max(1, round(out_h / block))
    small = img.convert("RGBa").resize((tw, th), Image.BOX).convert("RGBA")
    a = np.array(small)
    solid = a[..., 3] >= 110
    # keep the picture's own palette so outlines stay dark and colours stay flat
    src = np.array(img)
    opaque = src[src[..., 3] > 200][:, :3]
    if len(opaque) > 0:
        pal_img = Image.fromarray(opaque.reshape(-1, 1, 3).astype(np.uint8)).quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        rgb = Image.fromarray(a[..., :3]).quantize(palette=pal_img, dither=Image.Dither.NONE).convert("RGB")
        a[..., :3] = np.array(rgb)
    a[..., 3] = solid * 255
    return Image.fromarray(a)


def make_palette(img, colors=48):
    src = np.array(img.convert("RGBA"))
    opaque = src[src[..., 3] > 200][:, :3]
    return Image.fromarray(opaque.reshape(-1, 1, 3).astype(np.uint8)).quantize(colors=colors, method=Image.Quantize.MEDIANCUT)


def pixelate_mode(img, out_w, out_h, block=2, colors=48, pal=None):
    """Like pixelate(), but each big pixel takes the most common colour under it (darkest on a tie),
    which keeps small bright details (a flower, an eye) and dark outlines instead of blending them.
    Pass one shared `pal` for all frames of an animation so the colours don't flicker."""
    img = img.convert("RGBA")
    tw = max(1, round(out_w / block))
    th = max(1, round(out_h / block))
    s = 3  # look at a 3x3 patch of finer pixels for each big pixel
    fine = img.convert("RGBa").resize((tw * s, th * s), Image.LANCZOS).convert("RGBA")
    f = np.array(fine)
    pal = pal or make_palette(img, colors)
    colors = len(pal.getpalette()) // 3 if pal.getpalette() else colors
    idx = np.array(Image.fromarray(f[..., :3]).quantize(palette=pal, dither=Image.Dither.NONE))
    lut = np.array(pal.getpalette()[:colors * 3]).reshape(-1, 3)
    bright = lut.sum(1)
    solid = f[..., 3] >= 128
    out = np.zeros((th, tw, 4), np.uint8)
    for y in range(th):
        for x in range(tw):
            m = solid[y * s:(y + 1) * s, x * s:(x + 1) * s]
            if m.sum() < (s * s) / 2:
                continue
            ids = idx[y * s:(y + 1) * s, x * s:(x + 1) * s][m]
            counts = np.bincount(ids, minlength=len(lut))
            best = np.flatnonzero(counts == counts.max())
            k = best[np.argmin(bright[best])]
            out[y, x, :3] = lut[k]
            out[y, x, 3] = 255
    return Image.fromarray(out)


def chunky(img, block):
    """Blow a pixelated picture back up so each pixel becomes a `block` x `block` square."""
    return img.resize((img.width * block, img.height * block), Image.NEAREST)
