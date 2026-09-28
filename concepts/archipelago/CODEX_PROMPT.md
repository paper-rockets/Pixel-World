# Codex prompt: art for the big Sunny Meadow archipelago

Copy everything below the line into Codex.

---

You are making art for the bigger Sunny Meadow in the Phaser game at `E:\X Phaser`. Art only: no code.

## Rules for files

- Only create NEW files, and only inside `E:\X Phaser\source_art\archipelago\` (its `ground\` and `pieces\` folders, plus `preview.png` and `notes.md`).
- Do not edit, move, rename or delete any existing file anywhere in `E:\X Phaser`.
- Do not touch the game's code or folders (`src\`, `public\`, `tools\`, `dist\`, `index.html`, `school.html`, the package files), and do not run the game or any build.

The current island stays exactly as it is. You are painting the NEW islands around it, as separate pictures. The game builds the islands from layers: a ground picture for each island, and every tree, bush, rock, fence, bridge, dock and house as its own see-through picture placed on top. So the ground pictures must contain ground only.

## Look at these first

1. `E:\X Phaser\concepts\archipelago\archipelago-concept.webp`: the approved concept (layout and look).
2. `E:\X Phaser\concepts\archipelago\ref_overview_labelled.png`: the concept with each island boxed and named.
3. `E:\X Phaser\concepts\archipelago\ref_*.png`: one close-up per island. Use each one for its island's shape and features. `ref_home_for_reference.png` is the existing home island: do not paint it.
4. `E:\X Phaser\source_art\tiny_map.png`: the current Sunny Meadow island. **Match its style, scale and pixel size exactly.** This is the most important reference.
5. `E:\X Phaser\source_art\school\ground\map_ground.png`: an example of the "ground only" picture needed (grass, paths, sand, cliffs and water, with nothing standing on it).
6. `E:\X Phaser\source_art\school\objects\`: trees, bushes, rocks, logs, stumps, reeds, flowers, lily pads, fences, gate, signs, lamps, barrels, crates, chests, bench, dock pieces and boats. **These already exist. Do not draw them.**

## Style rules for every picture

- **View:** the same as `tiny_map.png`, a top-down 3/4 view like a classic top-down RPG. The ground is seen from straight above, and upright surfaces face the viewer (south). No perspective, no tilt, no rotation, no fisheye.
- **Cliff faces:** only below the bottom (south) edge of raised ground, 30–50 px tall, made of flat-fronted, squarish tan stone slabs side by side, split by thin dark vertical cracks, with a faint lighter ledge line across them and grass hanging over the top edge, exactly like the cliffs in `tiny_map.png`. No round bulging boulders, no orange, no dark red outlines. On left and right edges, only a thin face of 8–14 px. On top (north) edges, no face: just the dark grass edge and foam.
- **Texture:** like `tiny_map.png`, no big area of grass or water is one flat colour. Grass has small lighter and darker patches and lots of tiny tufts and blades all over. Water has a light shallow band along every shore, ripple lines, and a few darker patches further out.
- **Light:** from the top-left. Lit edges are top-left, and shade falls to the bottom-right.
- **Pixel art:** chunky pixel art with 1 art pixel = 2 × 2 picture pixels, exactly like `tiny_map.png`. Hard edges, shading in 2–4 colour steps per material, and small dark outlines. No blur, no soft gradients, no glow, no film grain, no JPEG noise.
- **Scale** (same as `tiny_map.png`):

| Thing | Size in picture pixels |
|---|---|
| Capybara | 64 tall, about 50 wide |
| Duckling | 34 × 34 |
| Mama Duck | 56 × 52 |
| Cottage | 334 wide × 350 tall |
| Big round tree | about 200 wide × 190 tall |
| Bush | 70–90 wide |
| Rock | 50–60 wide |
| Main path | about 70 wide, like `tiny_map.png`'s path from the house to the dock |
| Side path | at least 60 wide (the capybara must have room on both sides) |
| Stairs in a cliff | about 80 wide, like the dock's walkway in `tiny_map.png` |
| Beach strip below a cliff | 20–60 tall |
| Foam line at the shore | 2–4 |

- **Palette:** use these colours (measured from `tiny_map.png`). Small in-between shades are fine; no new hues, and nothing brighter or stronger than these.

| Use | Colours |
|---|---|
| Grass | `#BBE056` main · `#CCE266` lighter patches · `#A7D354` soft shade · `#8CC652` and `#75B34E` tufts and clover · `#5CA357` dark edge line |
| Paths | `#FCD99C` main · `#FAD190` and `#F5CB85` pebbles and edges |
| Beach sand | `#FDE4B2` main · `#FCF4DB` light · `#F6C392` shaded by a cliff |
| Cliffs | `#D7A782` light face · `#C49679` main face · `#B2856E` shade · `#9C725D` deep shade · `#815D4C` cracks, outline and cliff foot · `#E2BE98` small highlights |
| Water | `#4FC6E8` sea · `#47ABD7` darker patches · `#6EE4FA` ripple dashes · `#55D5F2` shallow band along the shore · `#7EE9FB` and `#B3F3FB` ripple lines in the shallows · `#F3F5E6` foam |
| Stone | `#738381` stone · `#2E2F34` stone outline |
| Outlines on pieces | leaves `#0C3C1C` · stone `#1C1C24` · wood `#34140C` |

- **No text, labels, borders, frames, UI or characters anywhere.**
- **Files:** PNG only, saved straight to disk on the PC. Do not send them through the phone: that removes the transparency. Do not upscale a smaller picture; draw at full size.

## Part A: island ground pictures (save to `E:\X Phaser\source_art\archipelago\ground\`)

Each picture holds one island only, surrounded by plain open sea (main water with a few ripple lines). Leave at least 80 px of sea between the island's outer foam and every edge of the picture. No other islands in the picture.

**Only paint:** grass (with tiny flat flowers, clover and tufts), paths, sand and beaches, cliffs, stairs cut into cliffs, cave openings in cliff faces, ponds and streams with foam, flat lily pads, pebbles, tilled soil beds, and the sea.

**Never paint:** trees, bushes, standing rocks, logs, stumps, reeds, flower bushes, fences, gates, signs, lamps, houses, sheds, docks, bridges, boats, barrels, crates, crops, a campfire, falling water, characters, or shadows of any of these. The game places all of them later.

| File | Picture size | Island size | What is on it | Bridge landings |
|---|---|---|---|---|
| `w_caves_pinktree.png` | 1086 × 1448 (tall) | about 950 × 1350 | References: `ref_nw_caves.png` (north part) and `ref_w_pinktree.png` (south part), joined as one island. North part: a raised upper grass level with a tall cliff face holding **two dark cave openings**, and a notch where a waterfall will pour down into a **pond** on the lower level (paint the pond and its foam, not the falling water). South part: open grass where the pink tree will stand, and **wooden stairs down a cliff** to a small beach on the west side. Paths join everything. | East side, upper third (to the north island) · East side, lower third (to the home island) · South side (to the campfire island) |
| `sw_campfire.png` | 1448 × 1086 | about 850 × 750 | Reference: `ref_sw_campfire.png`. A round flat clearing for a campfire (bare path-coloured earth `#FCD99C`, about 140 px across), a path, **wooden stairs down the south cliff** to a curved sand beach along the south shore. | North side (to the west island) |
| `n_orchard.png` | 1448 × 1086 | about 1300 × 900 | Reference: `ref_n_orchard.png`. A wide grassy island for an orchard: open grass for rows of fruit trees; a vegetable garden area with **two tilled soil beds** (flat brown rows, about 150 × 70 px each, no plants); a winding main path from the west shore to the east shore with a branch south. | West side (to the west island) · East side (to the north-east island) |
| `ne_pond.png` | 1086 × 1448 (tall) | about 950 × 1300 | Reference: `ref_ne_pond.png`. Upper grass level at the north, **wooden stairs** down to the middle level, a small **pond** (about 200 × 120 px), a path to **wooden stairs down to a sandy beach** in the south-east corner (a rowing boat and dock will be placed there). | West side (to the north island) · South side (to the south-east island) |
| `se_meadow.png` | 1448 × 1086 | about 1300 × 950 | Reference: `ref_se_meadow.png`. A big meadow island: open grass (a big pink tree and a gate will be placed), a winding path, a **long curved beach** along the south shore (a dock will be placed there), and a small sandy inlet on the east side. | North side (to the north-east island) · West side (to the home island) |
| `islets.png` | 1448 × 1086 | 8 separate islets | Reference: `ref_islets.png`. Two about 420 × 320, three about 300 × 260, three about 200 × 180. Each one: grass top, cliff face on its south side, thin sand rim, foam. At least 120 px of sea between islets. | None |

At a bridge landing, the path must reach right to the island's edge, with grass up to the edge there (a cliff face below it is fine), so a wooden bridge can join at grass height.

## Part B: new pieces (save to `E:\X Phaser\source_art\archipelago\pieces\`)

Each piece is its own PNG with real transparency: empty pixels fully transparent (alpha 0), no white or black background, and no half-transparent halo. Wood matches `source_art\school\objects\dock_clean\` and `structures\fence_piece_01.png`.

For animation frames: every frame has the same picture size, the object stays in exactly the same place, and only the moving parts change.

| File | Size (px) | What |
|---|---|---|
| `bridge_h_200.png` | 200 × 110 | Wooden plank bridge walked left–right. Planks run top to bottom (across the walking direction), and the deck is about 60 px deep. Posts at all four corners. A low rope-and-post rail **only along the back (top) edge**, so the capybara isn't hidden. No water drawn. |
| `bridge_h_300.png` | 300 × 110 | The same bridge, longer. |
| `bridge_v_200.png` | 110 × 200 | Wooden plank bridge walked up–down. Planks run left to right, and the deck is about 70 px wide. Low rails (10–14 px) on the left and right sides, and posts at the corners. |
| `bridge_v_300.png` | 110 × 300 | The same bridge, longer. |
| `bridge_h_mid.png` | 100 × 110 | A middle section of the left–right bridge. It must repeat seamlessly left to right. |
| `bridge_h_end.png` | 40 × 110 | The left end of the left–right bridge, with its two posts. The game flips it for the right end. |
| `bridge_v_mid.png` | 110 × 100 | A middle section of the up–down bridge. It must repeat seamlessly top to bottom. |
| `bridge_v_end_top.png` | 110 × 40 | The top end of the up–down bridge, with its posts. |
| `bridge_v_end_bottom.png` | 110 × 40 | The bottom end of the up–down bridge, with its posts. |
| `waterfall_s_1.png` to `_4.png` | 64 × 96 each | A small waterfall: a ribbon of water (`#4FC6E8` with `#B3F3FB` and `#F3F5E6` streaks) pouring straight down from a flat top edge. The streaks move down a quarter of the height each frame, so the 4 frames loop smoothly. |
| `waterfall_t_1.png` to `_4.png` | 72 × 150 each | A tall waterfall, same style, 4 looping frames. |
| `splash_1.png` to `_4.png` | 100 × 40 each | White foam splash and ripples where a waterfall hits the pool, 4 looping frames. |
| `campfire_1.png` to `_4.png` | 64 × 64 each | A ring of 7–8 grey stones, three crossed logs, and small flames (`#FCE46C`, `#F7A33A`, `#E4572E`) that flicker across the 4 frames. The stones and logs don't move. |

## Also deliver

- `E:\X Phaser\source_art\archipelago\preview.png`: each island with some of the existing trees, bushes and rocks and the new bridges placed on it, so everything can be checked by eye together.
- `E:\X Phaser\source_art\archipelago\notes.md`: for each ground picture, its size and the pixel position (x, y) where each bridge-landing path meets the shore.

## Order of work

Make `sw_campfire.png` first (the smallest island) and stop. Save it and say it is ready, so it can be checked against `tiny_map.png` before anything else is made. Continue with the rest only after it is approved.

## Optional extra (a small known fix)

`boat_capy_plain_up.png`, `_down.png`, `_left.png` and `_right.png`, saved to `E:\X Phaser\source_art\archipelago\pieces\` (not into `public\`): the same as `E:\X Phaser\public\boat\boat_capy_*.png` (same sizes and positions), but the capybara has no orange shirt, like `E:\X Phaser\public\assets\capy.png`.
