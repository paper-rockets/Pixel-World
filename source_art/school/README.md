# Willingdon School — Layered Asset Pack

Everything in this pack is separated for map building. The only opaque full-map image is `ground/map_ground.png`; it contains terrain only.

## Main files

- `ground/map_ground.png` — 1448 × 1086 terrain layer: grass, paths, sand, paved schoolyard, water, shore and cliffs.
- `objects/school/school_map_ready_700px.png` — corrected front-view school, exactly 700 px wide.
- `objects/school/school_native.png` — native transparent school sprite before the small fit adjustment.
- `objects/school_props/` — playground, remembrance garden and orange-flower collectibles.
- `objects/schoolyard/` — separate bench, bike rack, basketball hoop, flagpole and exact court/hopscotch overlay.
- `objects/fences/` — up/down fence segment plus four transparent corner orientations.
- `objects/dock_clean/` — modular wood-only dock segments and platform with no water, sand or shoreline pixels.
- `objects/boat/` — empty and orange-shirt passenger boats in four directions, plus four-frame directional wake loops.
- `objects/nature/` — 91 separately cut transparent trees, bushes, rocks, logs, stumps, mushrooms, reeds and flowers.
- `objects/structures/` — separately cut transparent cottages, horizontal fences, signs, lanterns and containers. The old terrain-backed dock cuts have been removed.
- `objects/loose_favorites/` — the loose bushes, rocks, logs and stumps that worked well in the earlier pack.
- `player/player_capybara_orange_shirt_sheet.png` — full 4 × 4 orange-shirt animation sheet.
- `player/frames/` — the same 16 animation frames as individual transparent PNG files.
- `layout.json` and `placement.csv` — suggested positions; all coordinates use the top-left of the 1448 × 1086 map.
- `quest.json` — gentle “Collect Orange Flowers” challenge configuration.
- `boat_travel.json` — recommended departure, fade, arrival, bobbing and wake timing.
- `audio/` — pickup, chime and capybara sounds from the supplied assets.

## Layer order

1. Ground
2. Low plants, flowers and ground props
3. School, playground, trees, rocks, fences and other structures
4. Player and NPCs
5. Foreground cover objects and UI

The light Orange Shirt Day theme is carried only by the capybara's orange tee and the peaceful orange-flower garden. The challenge has no timer, score or coins: collect five orange flowers, then bring them to the remembrance garden.

The suggested spawn is at `(724, 900)` and the Sunny Meadow exit rectangle begins at `(664, 930)`, both on reachable sand.
