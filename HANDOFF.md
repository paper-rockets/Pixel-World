# Handoff: Capybara Islands (Phaser game)

Last updated 2026-09-28 (second session). Read this first before changing anything in `E:\X Phaser`.

The folder is also on GitHub now: `paper-rockets/pixel-world`, work branch `claude/pixel-word-i-project-1c0cdp`. Cloud sessions (claude.ai/code) work in a fresh Linux copy of it, commit there and push to that branch; bring the changes to the PC with `git pull`.

## Right now

**4 of the 6 new island pictures are done and matched to the home island (plus a second set of islets). Next: the two pond islands (`match_island.py` needs pond handling first), then the bridges, waterfalls, campfire and vegetable-bed pieces.**

| Island | Made by | Original check | After `match_island.py` |
|---|---|---|---|
| south-west campfire (`sw_campfire`) | Codex | 6 to fix | 0 to fix (cliffs are still Codex's rounded blocks, in the home island's tan) |
| south-east meadow (`se_meadow`) | ChatGPT image generation | 5 to fix | 0 to fix |
| islets (`islets`, 8 small islands in one picture) | ChatGPT image generation | 5 to fix | 0 to fix |
| islets, second set (`islets_2`, 8 more) | ChatGPT image generation | 4 to fix | 0 to fix |
| north orchard (`n_orchard`) | ChatGPT image generation | 5 to fix | 0 to fix |

- **Campfire** (`check/review_sw_campfire.png`, `check/match_sw_campfire.png`): Codex's grass was too strong and flat, the cliffs round orange boulders, the water flat, and the path (~40 px) and stairs (~50 px) only as wide as the capybara. The user asked whether Claude could fix it instead of Codex: `match_island.py` fixed everything but the rounded cliff blocks. Rebuilding those from the home island's slabs looked worse (streaky), so it was dropped.
- **Meadow** (`check/review_se_meadow.png`, `check/match_se_meadow.png`): the user was away from Codex and used ChatGPT with `concepts/archipelago/CHATGPT_2_se_meadow.md` and three numbered reference pictures. It came out much closer than Codex's first try: ground only, flat tan slab cliffs, textured grass, wide stairs. It needed stronger colours softened, paths widened from ~46 to ~62 px, and 26 px of sea added around it (the land came within 58 px of the picture's edge). The user's zip (`island_ground_only_complete_set.zip`) also had `se_meadow_alt_no_water.png`: that is a different drawing, not a cut-out of `se_meadow.png` (tall pillar cliffs, a small rock, no stairs, land almost touching the edges). It's kept as a spare and not used.
- **Islets** (`check/review_islets.png`, `check/match_islets.png`): ChatGPT with `concepts/archipelago/CHATGPT_3_islets.md`. Eight round grassy islands with slab cliffs and sand rims, close to the style on the first try. They needed softer colours, the home island's water, and 42 px of sea added (land came within 43 px of the edge). The zip (`islets_complete_package_clean.zip`) also had a "no water" picture, though the prompt asked for one: the same layout but a different drawing (bigger islands, taller cliffs, wide sand). The user asked to use it too, so it's the second set, `source_art/archipelago/ground/islets_2.png` (see-through where the sea goes; `match_island.py` fills that with sea). It needed 60 px of sea added (land came within 24 px of the edge). The islets have no planned place yet; `world_preview.py` scatters all 16 into open sea for the picture only.
- **Orchard** (`check/review_n_orchard.png`, `check/match_n_orchard.png`): ChatGPT with `concepts/archipelago/CHATGPT_4_n_orchard.md`; the user pasted the picture straight into the chat (a full-size PNG), not as a zip. One wide island with a T of paths: west edge to east edge (the bridge landings), and a short branch south to a lookout. It needed softer grass, the home island's water, paths widened from ~47 to ~63 px, and 50 px of sea added (land came within 34 px of the edge). It's bigger than asked (1370 x 938 against 1150 x 800) but fits its planned place. Left as drawn: a small grey rock in the water at the foot of the west cliff (out of reach), and the smooth grass north of the crossing, where the vegetable garden goes.
- The orchard's vegetable beds were left out of its ground picture on purpose: they come later as a separate flat piece with their fence and crops.
- **Next:** `w_caves_pinktree` and `ne_pond`, which both have a pond. `match_island.py` can't handle ponds yet (see "Fixing new island art"), so add that when the first one comes in, before trusting its output. Reuse the ChatGPT prompt shape: numbered reference pictures, "picture 1, 2, 3", ground only, the sizes stated against the pictures, and "give it to me as a .zip with just this one picture inside" (the user asked for zips; they come back through the chat as uploads).
- Other prompts on file: `concepts/archipelago/CODEX_2_next_island.md` (the meadow for Codex, with the updated style rules), and `concepts/archipelago/CODEX_FIX_1_sw_campfire.md` (a Codex redraw of the campfire island, if flat-slab cliffs are ever wanted there). `concepts/archipelago/CODEX_PROMPT.md` has the measured palette, the cliff shape, the texture rule, and the real path and stair widths.
- The game itself is the normal small Sunny Meadow and works. Both published links were updated on 2026-09-28 with the hiding-spot wiggle fix (Lost Ducklings version 9, Orange Garden version 5).

See "Big Sunny Meadow" below for the full plan.

## What this is

A small, kid-friendly, touch-first island game made with **Phaser 4.2.1** and **Vite 8**. The player is a capybara. There are two islands, and a rowing boat sails between them:

| Island | Scene key | Quest | Page | Published link (private Artifact) |
|---|---|---|---|---|
| Sunny Meadow | `play` | **Lost Ducklings**: find 5 hidden ducklings and walk them home to Mama Duck's pen | `index.html` | https://claude.ai/artifact/Bs7u7asAyYAcS7rZK4gPWU |
| Willingdon School | `school` | **Help the Orange Garden Bloom**: find 5 orange flowers and plant them in the remembrance garden | `school.html` | https://claude.ai/artifact/GftTNSMgSK1qiTqHYBUWoo |

Both pages contain both islands; each page just starts on its own island.

## The user

- Plain language only. Avoid jargon.
- Tests on a phone (Samsung, Chrome) and an older tablet (Galaxy Tab S6 Lite 2020 is the worst case).
- Sends screenshots with circles drawn on problems, and asks to see the full map as an image.
- Art comes from **Codex** (image generation). Claude does the design, code and fixes, and writes the prompts for Codex. Before writing a Codex prompt, check it against the current files, and always limit Codex to adding new art files.
- When away from Codex, the user makes art with **ChatGPT image generation**. ChatGPT can't open the project's files, so give it numbered reference pictures to attach, and write the prompt about "picture 1, 2, 3" instead of file paths (see `concepts/archipelago/CHATGPT_2_se_meadow.md`). Good references: `source_art/school/ground/map_ground.png` (ground only, flat tan cliff slabs, the right texture), `source_art/tiny_map.png` (style and scale), and the island's `concepts/archipelago/ref_*.png` (layout).
- The Orange Garden is an **Orange Shirt Day** theme. Keep it quiet and respectful: no timer, score, coins or prizes. It must **not** become a step in any unlock or progress chain. The theme stays limited to the capybara's orange tee and the garden. The user's pack deliberately removed a display board. An "Every Child Matters" line was offered but not added.

## How to run, test and publish

```bash
npm run dev          # http://localhost:8180 , phone on same Wi-Fi: http://192.168.0.22:8180
npm run build        # -> dist/ (two pages: index.html + school.html)
```

**Testing:**
- **Browser pane:** it usually can't start a server here, because the 5-per-folder limit is used up by other chats. If the Vite server is already running (it was on 2026-09-28), open `http://localhost:8180/?debug` with `preview_start` and a `url`, which works.
- **No sign-in:** the pane can't open claude.ai artifact links.
- **Otherwise:** test with hidden Chrome against `dist/`, which needs no server. Run `npm run build` first.

```bash
node tools/headless_check.mjs 1280 800 desktop full   # plays a whole Lost Ducklings game, checks the win card
node tools/school_check.mjs 412 892 mobile            # plays a whole Orange Garden game
node tools/boat_check.mjs 412 892 mobile              # sails school -> meadow -> school, and from the win card
node tools/headless_check.mjs 412 892 mobile poses    # puts the capybara at spots in tools/poses.json, saves close-ups
```

Screenshots go to `check/`. Opening a page with `?debug` exposes `window.game`. Many screenshots in one turn get dropped, so combine them into one contact sheet with PIL before viewing.

- The scripts find Chrome by themselves (`findChrome` in `tools/cdp.mjs`): Chrome on the PC, or the Chromium that cloud containers have. `CHROME=<path>` picks another.
- In a cloud container, run `npm ci` first. The Google font can't load there (the network proxy blocks it), so the test browser shows a fallback font and logs one font error. That isn't a game bug.
- `check/` is in git, and test runs overwrite its screenshots. Put them back with `git checkout -- check/` unless the new ones are wanted.

**Checking new island art from Codex:**

```bash
python tools/review_island.py source_art/archipelago/ground/<name>.png   # -> check/review_<name>.png
```

It compares each kind of ground (grass, path, beach sand, cliff face, water) with the home island (colour, colour strength, texture), checks the island's size and the sea around it, and measures how wide the paths are. The picture shows both islands where they are planned in the big map, close-ups next to the same kind of ground on the home island, the capybara on the narrowest path, and colour swatches. It needs Pillow, numpy, scipy and OpenCV (in the cloud: `pip install pillow numpy scipy opencv-python-headless`).

**Fixing new island art from Codex** (about a minute per island):

```bash
python tools/match_island.py source_art/archipelago/ground/<name>.png          # -> public/world/islands/<name>.png + check/match_<name>.png
python tools/review_island.py public/world/islands/<name>.png                  # -> check/review_<name>_matched.png
python tools/match_island.py source_art/archipelago/ground/<name>.png --masks  # -> check/masks_<name>.png (which pixel is which ground)
```

- Keeps every shape Codex drew. Recolours grass, path, beach, cliffs and stairs onto the home island's shades.
- Replaces the flat grass, path and open water with the home island's own texture, sewn from small overlapping pieces of `tiny_map.png`. The foam and bright shallows along the shore are painted like the big map's sea.
- Saves the island's piece for the big map: its land plus its shore water, fading out by 80 px. If the land comes closer than that to the picture's edge, sea is added all round, and `public/world/islands/<name>.json` says by how much (`pad`: the piece's top-left moves up and left by that much).
- Grass or path texture that is already close to the home island's is kept; only a flat fill is replaced.
- Per island settings go in `ISLANDS` at the top of the file: boxes around stairs (they can't be told from cliffs by colour), how far to widen the paths, and how wide to make the stairs. Check `--masks` for a new island first.
- Several islands in one picture work (the islets): both tools keep every island bigger than 2% of the largest, and the check sheet shows a grass close-up when there's no path.
- See-through pictures work too (an island without its water, like `islets_2.png`): anything more than half see-through is taken for sea.
- A cove (sand between grass and the sea) is beach, not path: sand with more than 20% sea around it is beach. Real paths have 5% or less, even where they run to the island's edge.
- Sand is told from pale cliff faces by hue: sand is yellow-beige (hue above 28), while even the palest cliffs are more orange. Pale specks in the grass smaller than 400 px aren't paths.
- See the whole map with `python tools/world_preview.py` (about a minute). Its sea is sewn from the home island's open water, as planned for the real map, so the pieces fade into it without a seam. Every islets picture (`islets*.png`) is cut into single islands, each with only the water nearest to it, and each is dropped into the most open sea, clear of the islands and of the boat's channel. Add `--full` for a full-size copy (`check/world_now_full.jpg`, about 5 MB, not kept in git) when the user wants to zoom in.
- Not handled yet: ponds and streams (inland water is taken for land), and ground the home island doesn't have (like tilled soil; the orchard's soil beds were kept out of its picture for this reason). Add pond handling before running it on `w_caves_pinktree` or `ne_pond`.

**Publishing:** do this for both pages after every change, because they share code.

```bash
python tools/make_artifact.py index    # -> artifact/index.html        + artifact/files.json
python tools/make_artifact.py school   # -> artifact/school/index.html + artifact/school/files.json
```

Then publish with the Artifact tool: `file_path` = that `index.html`, `root` = `E:\X Phaser\dist`, `files` = the map in `files.json`. Set old JS file names to `null`, because JS names change on every build. Publishing to the same `file_path` keeps the same link.

- From a new conversation (like a cloud session), first `read` each link, then publish with `url` = the link; `root` is the clone's `dist` folder. List the live files with `action: list, scope: files` to find the old JS names.
- When only code changed, `files` only needs the new JS files plus `null` for the old ones; every picture and sound stays as it is.

## Where things are

| Path | What |
|---|---|
| `source_art/` | The user's original art, untouched. School pack v3 is in `source_art/school/`. Codex's new archipelago art goes into `source_art/archipelago/`. |
| `public/assets/` | Sunny Meadow pictures (made by `tools/prep_assets.py`) |
| `public/school/` | School pictures (made by `tools/prep_school.py`) |
| `public/boat/` | Boat and wake pictures (made by `tools/prep_boat.py`) |
| `public/world/` | Output of the code-painted big-map attempt (`ground.webp`, `home.webp`). Not used by the game. |
| `src/game.js` | Makes the Phaser game with both islands; `startGame('play' \| 'school')` |
| `src/PlayScene.js` | Sunny Meadow / Lost Ducklings |
| `src/school/SchoolScene.js` | School / Orange Garden |
| `src/boat.js` | Boat, sail button, depart/arrive, switching islands |
| `src/nav.js` | Walking and pathfinding, shared: `new Nav({ width, height, start, ground(x,y), blockers })` |
| `src/ui.js`, `src/style.css` | HTML screen overlay: counter, sound, arrow, toast, sail button, start/win cards |
| `src/level.json` | Sunny Meadow layout: walk outline, walls, hiding spots, pen, gate, boat, painted objects to cut out ("props") |
| `src/school/scene.json` | School layout: each object's ground point, scale, solid, role; start; boat |
| `tools/pixelate.py` | Re-draws sprites on the islands' 2-pixel grid (`pixelate_mode` keeps eyes, flowers and outlines) |
| `tools/build_world.py`, `tools/world_paint.py` | Claude's big-map generator (see below). The ground painting was rejected; the sea, the blending and the object placement are reusable. |
| `tools/review_island.py` | Checks a Codex island picture against the home island and makes `check/review_<name>.png` (see "Checking new island art") |
| `tools/match_island.py` | Makes a Codex island picture match the home island (see "Fixing new island art") |
| `tools/world_preview.py` | The whole big map as it stands (`check/world_now.png`): the home island, every matched piece in its planned place, faint concept pictures for islands still to make, and the planned bridges. The user likes seeing this after each new island. |
| `public/world/islands/` | Matched island pieces for the big map (made by `tools/match_island.py`). Not used by the game yet. |
| `concepts/archipelago/` | The chosen concept, one reference crop per island, `CODEX_PROMPT.md`, and the fix requests (`CODEX_FIX_*.md`) |
| `concepts/codex_attempt/` | Codex's broken 10x map, kept only for the record |
| `AGENTS.md` | Codex's own instruction file. Codex also works in this folder. |

## Rules learned the hard way

1. **Layered art only.** Sunny Meadow is a flat painted picture, so every tree, bush and rock had to be cut out and its walls traced by hand, and each guess became a bug. The school came as a layered pack (clean ground + separate objects), and it just worked. Require layered packs for every new island.
2. **Match the pixel size.** Island art has chunky pixels, about **2 map pixels** per art pixel. Any sprite that gets shrunk must go through `pixelate_mode` onto that grid, and be stored at 2x and drawn at scale 0.5. The user noticed when sprites had finer pixels.
3. **Draw order = where things touch the ground.** Depth is the object's bottom y. Only the base of an object is solid. Trees and bushes turn see-through when the capybara is behind them.
4. **Phaser 4 easing names must be long**, like `'Sine.easeInOut'`, for camera `pan`/`zoomTo`. A short name like `'Sine.inOut'` throws inside the game loop and freezes everything.
5. **Boat moorings must sit fully in water.** The first school spot put the bow on the sand. The sail button sits at the top of the screen, because at the school the dock is at the bottom edge of the map.
6. **Never hide painted things under a sprite; paint them out.** Anything in front of the player turns see-through, so a capybara painted into the Sunny Meadow picture and hidden under a bush showed through ("creepy hidden capy"). The painted ducks and all three painted capybaras are now painted over with grass in `prep_assets.py` (the `for oval in [...]` list).
7. **The pack's separate capybara frame files are badly cut.** Cut frames from the full sheet instead (`prep_school.py` does this).
8. **Ground painted in code doesn't match the painted islands.** The user rejected it as "style is mismatched". Ground must come from Codex as ground-only pictures.
9. **Codex edits this folder too.** It rewrote `src/PlayScene.js` on 2026-09-28. Before editing, check file dates for recent changes, never work on the same files at the same time, and tell Codex to only add files in its own folder.
10. **Fading one picture's water into another sea:** make the outer water see-through in a dither pattern on the art-pixel grid (2 x 2 map pixels), over about 44 map pixels from the edge. The join disappears completely (`public/world/home.webp`, made in `build_world.py`). Land cut off at a picture's edge needs a small cap of new land.
11. **Codex doesn't follow bare numbers or palettes closely.** Asked for 90–110 px paths, it drew about 40, and it painted stronger colours than the palette it was given. Give every size a thing to match in `tiny_map.png` ("as wide as the path from the house to the dock"), and measure what comes back with `tools/review_island.py` instead of judging by eye. ChatGPT is the same: asked for 70 px paths it draws about 47, and asked for 90–120 px of sea around the land it leaves 24–58. `match_island.py` fixes both (`widen_path` 8, and it adds sea), so there's no need to ask again.
12. **Fix Codex's colours and texture in code, not its shapes.** Recolouring and sewing texture from the home island's own pixels match well; that isn't the rejected "ground painted in code", because every textured pixel comes from `tiny_map.png`. Widening paths and stairs also works. Redrawing shapes doesn't: rebuilding the cliffs from the home island's slabs came out streaky. Ask Codex for shapes.
13. **Tell path from beach by what borders the sand, not by its colour.** Sand bordered mostly by grass is path; sand bordered by cliffs and sea is beach. ChatGPT paints the two nearly the same colour, and the old colour split gave different answers from run to run.
14. **Image generators' "extra versions" can be different drawings.** ChatGPT's "transparent" meadow had other paths, tall pillar cliffs and a rock, and its "no water" islets had other island shapes. It added the islets one even when asked for a single picture. Compare every file before using it.

## Known small issues

- The passenger-boat picture shows the orange-shirt capybara on both islands, but the Sunny Meadow capybara has no shirt. The Codex prompt asks for plain-capybara boat pictures as an optional extra.
- An empty stray folder `E:\X%20Phaser` exists, left by an old test script. Deleting it was blocked, so the user can delete it.

## Big Sunny Meadow (the current project)

**History (2026-09-28)**
- **Codex's attempt:** Codex tried a 10x map by code. It came out as a patchwork of squares cut from the old picture (the user called it "a puzzle"). Its files are in `concepts/codex_attempt/`, and `src/PlayScene.js` was put back on the small island.
- **Claude's attempt:** Claude painted new ground in code around the untouched home island (`tools/build_world.py`, previews in `check/world_full.png`). Rejected for mismatched style.

**Chosen direction:** the archipelago in `concepts/archipelago/archipelago-concept.webp`.
- The home island stays exactly as it is, in the middle.
- New islands sit around it across channels, joined by wooden bridges:
  - west: caves, waterfall and pink tree, one tall picture
  - south-west: campfire
  - north: orchard and vegetable beds
  - north-east: pond and small beach
  - south-east: meadow and long beach
  - a sheet of islets
- Each new island is a Codex ground-only picture at the home island's exact scale.
- Trees, bushes, rocks, logs, reeds, flowers, lily pads, fences, signs, lamps, barrels, crates and dock pieces come from `source_art/school/objects/`.
- New Codex pieces: bridges (whole and modular), waterfalls, a splash and a campfire, all animated in 4 frames. Also the orchard's vegetable beds: a flat piece of soil and crops that lies on the ground (drawn under the capybara), with a fence around it.

**Planned positions** (game pixels, world 4608 x 3456, top-left corner of each picture; adjust to the real art):

| Island | Top-left |
|---|---|
| home | (1580, 1300) |
| west (tall) | (440, 420) |
| south-west | (160, 1780) |
| north | (1500, 60) |
| north-east (tall) | (3000, 60) |
| south-east | (3100, 1560) |
| islets | not placed yet: cut `public/world/islands/islets.png` and `islets_2.png` into single islands and spread them over open sea |

- **Bridges:** home to west, west to north, north to north-east, north-east to south-east, south-east to home, and west to south-west. That makes loops with no dead ends.
- **Home island bridge points:** west shore at picture (40, 460) and east shore at (1440, 420). Both are an easy walk from the house. A north bridge would be hidden behind the house, and its area is only reachable the long way round the pen.
- **Ducklings:** 8 in total, 1 on the home island and 1 on each new island. The start card text ("5 babies") and the counter then need to say 8.
- **Boat:** keep the channel south of the home dock clear, because the boat rows 330 px straight down from its mooring.

**To build once the art is approved**
1. **Island pictures:**
   - Cut each one to its land plus about 60 px of water.
   - Fade the water edge into the sea like `home.webp`.
   - `tools/match_island.py` already does both (fading out by 80 px) and matches the colours, so this step is mostly done for each island that comes through it.
   - The sea between the islands should be sewn from the home island's open water too, like the islands' water (`quilt` in `match_island.py`), so the pieces fade into the same water.
   - Work out where you can walk from the colours (grass, sand and path yes; water and cliff faces no), adding stairs by hand.
   - Watch texture memory on the Tab S6 Lite: several 2x island pictures are heavy, so store new islands no bigger than they need to be.
2. **Sea:** reuse the sea painter from `build_world.py` for the water between the islands.
3. **Objects:** place them with the placement code in `build_world.py` (foot walls, see-through when behind, shadows on the ground), plus bridges, waterfalls and the campfire.
4. **Walking:** bake every wall into one walk map, like the school's `walk.png`. `Nav.canStand` checks every blocker each time, which is far too slow with hundreds of objects.
   - The A* heap uses small arrays, and path straightening checks lines from the far end. Speed both up for long paths across the big map.
5. **`PlayScene`:** load the world file, the island pictures and the objects picture sheet. The title screen shows the home island, as now.
6. **Test and publish:** play a full game in hidden Chrome, check phone and tablet sizes, then republish both pages.

## Earlier plan (on hold while the big Sunny Meadow is built)

The user's direction: an **archipelago world map under clouds**. Each region is a separate medium-sized map connected by boat routes. Finding **map pages** clears clouds, and **repairing docks** opens ferry routes. Locked islands show as silhouettes marked "Route not open yet"; only show ones that will really be made. Region order: Sunny Meadow, Willingdon School, Harbour Village, Bamboo Rainwood, Lotus Marsh, Orchard Hills, Mountain Springs.

Suggested build order:

1. **World map screen + saving progress.** Boat trips go through the map, with a boat moving along a dotted route. Progress is saved in the browser (localStorage, wrapped in try/catch). This needs world-map art from Codex: sea, island + silhouette per region, clouds, route pieces, layout.json and a preview.
2. **One reusable "find things, bring them somewhere" quest type**, set up from a small file per island. Move the ducklings and flowers onto it. No new art needed.
3. **Map pages** hidden on the two islands; finding them clears clouds. Needs a torn map-page picture.
4. **Harbour Village** as the first new island, with the dock-repair quest. Needs a full layered pack.

Lantern trail (night lighting) and waterwheel (moving water) need new mechanics, so they come later.

## Design skill

The Impeccable design skill was loaded on 2026-09-28. Its check found no `PRODUCT.md` or `DESIGN.md`, and treats the game's current look as the design authority. For on-screen UI work (counter, cards, messages), follow its quality rules and offer `init` if a design brief is wanted.
