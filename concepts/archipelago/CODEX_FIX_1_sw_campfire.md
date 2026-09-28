# Codex fix request 1: the campfire island

Copy everything below the line into Codex. The picture that shows each problem is
`check/review_sw_campfire.png` (made by `python tools/review_island.py source_art/archipelago/ground/sw_campfire.png`).

---

`E:\X Phaser\source_art\archipelago\ground\sw_campfire.png` has the right layout: the island's size and shape, the round clearing, the path from the north shore, the stairs down the south cliff, and the beach. Keep all of that.

But it doesn't look like part of the same map as `E:\X Phaser\source_art\tiny_map.png` yet. Please paint it again as a **new file**, `E:\X Phaser\source_art\archipelago\ground\sw_campfire_v2.png`, with the changes below. Do not change, move or delete `sw_campfire.png` or any other file. Work with `tiny_map.png` open next to your picture at the same size, and compare them often.

## What to change

1. **Grass: softer, less bright, and textured.** The main grass is `#BBE056` (yours is `#B0E02C`, which is too strong). Like `tiny_map.png`, no big area may be one flat colour: paint small lighter and darker patches (`#CCE266`, `#A7D354`) and lots of tiny scattered tufts and blades (`#8CC652`, `#75B34E`) all over the grass. Keep the little flowers and clover, but fewer and smaller.
2. **Cliffs: muted tan-brown stone, not orange.** Use light face `#D7A782`, main face `#C49679`, shade `#B2856E`, deep shade `#9C725D`, cracks and outline `#815D4C`, and `#E2BE98` for small highlights. Shape: flat-fronted, squarish stone slabs side by side, split by thin dark vertical cracks, with a faint lighter ledge line across them, exactly like the cliffs in `tiny_map.png`. No round bulging boulders and no dark red outlines.
3. **Path and clearing: paler and wider.** Colour `#FCD99C`, with `#FAD190` and `#F5CB85` only for small pebbles and the edges (yours is the more orange `#FEC580`). Make the path about **70 px wide everywhere**, like the path in `tiny_map.png` that runs from the house down to the dock. Yours is about 40 px. The capybara is 50 px wide and must have room on both sides.
4. **Stairs: wider.** About **80 px wide** (yours are about 50), as wide as the dock's walkway in `tiny_map.png`, with the same wood colours as that dock.
5. **Water: not one flat blue.** Like `tiny_map.png`: along every shore, a band of light shallow water 20–40 px wide (`#55D5F2` with `#7EE9FB` ripple lines and a few `#B3F3FB` glints), with the foam line `#F3F5E6` where it meets the land. Further out, the sea is `#4FC6E8` with scattered short ripple dashes (`#6EE4FA`) and a few slightly darker patches (`#47ABD7`).
6. **Side cliffs: thinner.** On the left and right sides of the island the cliff face is only 8–14 px wide (some of yours are over 20 px).
7. **Beach sand is nearly right.** Keep it about `#FDE4B2`, with `#F6C392` where the cliff shades it.

## Keep the same

1448 × 1086 PNG. Ground only: no trees, bushes, standing rocks, logs, stumps, fences, signs, a campfire, or anything else standing on the ground. Same chunky pixel size as `tiny_map.png`. Light from the top-left. The path still reaches the north shore for the bridge.

These fixes apply to every island you make after this one, too.

Save `sw_campfire_v2.png`, say it is ready, and stop.
