# Codex message 2: skip the campfire redraw, make the next island

Use this if the user approves the fixed campfire island (`check/match_sw_campfire.png`). It replaces `CODEX_FIX_1_sw_campfire.md`. It carries the updated style rules itself, because the copy of `CODEX_PROMPT.md` on the PC may be the older one. Copy everything below the line into Codex.

---

Change of plan: don't redraw the campfire island. If you already made `sw_campfire_v2.png`, keep it, but don't do more work on it. Claude fixed `sw_campfire.png` in code (colours, grass texture, water, wider path and stairs), and it's approved.

Next, make ONE new island picture, then stop:
`E:\X Phaser\source_art\archipelago\ground\se_meadow.png`

**What it is:** reference `E:\X Phaser\concepts\archipelago\ref_se_meadow.png`. A big meadow island: open grass (a big pink tree and a gate will be placed later), a winding path, a long curved beach along the south shore (a dock will be placed there later), and a small sandy inlet on the east side. Bridge landings: north side (to the north-east island) and west side (to the home island). At each landing the path runs right to the island's edge, with grass up to the edge there.

**Size:** the picture is 1448 × 1086. Keep at least 90 px of plain sea between the island's outer foam and every edge of the picture, so the island is at most about 1260 × 900.

**Updated style rules.** Where these differ from `CODEX_PROMPT.md`, these win:

1. Match `E:\X Phaser\source_art\tiny_map.png` exactly. Keep it open next to your picture at the same size and compare often.
2. Colours (measured from `tiny_map.png`). Use these, and nothing brighter or stronger:
   - Grass: `#BBE056` main, `#CCE266` lighter patches, `#A7D354` soft shade, `#8CC652` and `#75B34E` tufts and clover, `#5CA357` dark edge line
   - Paths: `#FCD99C` main, `#FAD190` and `#F5CB85` for pebbles and edges
   - Beach sand: `#FDE4B2` main, `#FCF4DB` light, `#F6C392` where a cliff shades it
   - Cliffs: `#D7A782` light face, `#C49679` main face, `#B2856E` shade, `#9C725D` deep shade, `#815D4C` cracks and outline, `#E2BE98` small highlights
   - Water: `#4FC6E8` sea, `#47ABD7` darker patches, `#6EE4FA` ripple dashes, `#55D5F2` shallow band along the shore, `#7EE9FB` and `#B3F3FB` ripple lines in the shallows, `#F3F5E6` foam
3. Cliffs: flat-fronted, squarish tan stone slabs side by side, split by thin dark vertical cracks, with a faint lighter ledge line across them, exactly like the cliffs in `tiny_map.png`. No round bulging boulders, no orange, no dark red outlines. On the left and right edges of the island, the cliff face is only 8–14 px wide.
4. Texture: no big area of grass or water is one flat colour. Grass has small lighter and darker patches and lots of tiny tufts and blades all over. Water has a light shallow band along every shore, ripple lines, and a few darker patches further out.
5. Sizes: the capybara is 50 px wide. Paths are about 70 px wide everywhere, like the path in `tiny_map.png` from the house down to the dock. Stairs cut into a cliff are about 80 px wide, like that dock's walkway, with the same wood colours as the dock.

**Everything else stays the same:**
- Ground only: no trees, bushes, standing rocks, logs, stumps, fences, gates, signs, lamps, docks, bridges, boats, or anything else standing on the ground.
- The same top-down view, light from the top-left, and the same chunky pixel size as `tiny_map.png`.
- PNG, saved straight to disk.
- Only add new files inside `E:\X Phaser\source_art\archipelago\`, and don't change, move or delete anything else.

Save `se_meadow.png`, say it is ready, and stop.
