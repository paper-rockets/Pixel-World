# Handoff: Capybara Islands (Phaser game)

Last updated 2026-09-28. Read this first before changing anything in `E:\X Phaser`.

## Right now

**Waiting for Codex art for the big Sunny Meadow.** The user asked to pause after the Codex prompt was written.

- The prompt is `concepts/archipelago/CODEX_PROMPT.md`. It is art only: Codex may only add new files in `source_art/archipelago/`.
- Codex makes `source_art/archipelago/ground/sw_campfire.png` first and stops.
- **Next step:** compare that picture with `source_art/tiny_map.png` for style, pixel size, scale, palette, view angle and light. It must be ground only: no trees, rocks, fences and so on. Tell the user what matches and what doesn't, so they can approve it or send fixes to Codex.
- The game in the folder is the normal small Sunny Meadow and works. The two published links show the same version.

See "Big Sunny Meadow" below for the full plan.

## What this is

A small, kid-friendly, touch-first island game made with **Phaser 4.2.1** and **Vite 8**. The player is a capybara. There are two islands, and a rowing boat sails between them:

| Island | Scene key | Quest | Page | Published link (private Artifact) |
|---|---|---|---|---|
| Sunny Meadow | `play` | **Lost Ducklings**: find 5 hidden ducklings and walk them home to Mama Duck's pen | `index.html` | https://claude.ai/artifact/Bs7u7asAyYAcS7rZK4gPWU |
| Willingdon School | `school` | **Help the Orange Garden Bloom**: find 5 orange flowers and plant them in the remembrance garden | `school.html` | https://claude.ai/artifact/GftTNSMgSK1qiTqHYBUWoo |

Both pages contain both islands; each page just starts on its own island. There's no git repo in this folder; "commit" means save to disk.

## The user

- Plain language only. Avoid jargon.
- Tests on a phone (Samsung, Chrome) and an older tablet (Galaxy Tab S6 Lite 2020 is the worst case).
- Sends screenshots with circles drawn on problems, and asks to see the full map as an image.
- Art comes from **Codex** (image generation). Claude does the design, code and fixes, and writes the prompts for Codex. Before writing a Codex prompt, check it against the current files, and always limit Codex to adding new art files.
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

**Publishing:** do this for both pages after every change, because they share code.

```bash
python tools/make_artifact.py index    # -> artifact/index.html        + artifact/files.json
python tools/make_artifact.py school   # -> artifact/school/index.html + artifact/school/files.json
```

Then publish with the Artifact tool: `file_path` = that `index.html`, `root` = `E:\X Phaser\dist`, `files` = the map in `files.json`. Set old JS file names to `null`, because JS names change on every build. Publishing to the same `file_path` keeps the same link.

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
| `concepts/archipelago/` | The chosen concept, one reference crop per island, and `CODEX_PROMPT.md` |
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

## Known small issues

- The passenger-boat picture shows the orange-shirt capybara on both islands, but the Sunny Meadow capybara has no shirt. The Codex prompt asks for plain-capybara boat pictures as an optional extra.
- **The hiding-spot wiggle is too big.** When a duckling quacks, its bush or rock pops to about 1.7 times its size for a moment. In `PlayScene.js` the tween uses `s.scale` from `level.json` (0.58–0.85), but the cover is drawn at `SPOT_SCALE` 0.5. The fix is to tween relative to the drawn scale. Not fixed yet.
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
- New Codex pieces: bridges (whole and modular), waterfalls, a splash and a campfire, all animated in 4 frames.

**Planned positions** (game pixels, world 4608 x 3456, top-left corner of each picture; adjust to the real art):

| Island | Top-left |
|---|---|
| home | (1580, 1300) |
| west (tall) | (440, 420) |
| south-west | (160, 1780) |
| north | (1500, 60) |
| north-east (tall) | (3000, 60) |
| south-east | (3100, 1560) |

- **Bridges:** home to west, west to north, north to north-east, north-east to south-east, south-east to home, and west to south-west. That makes loops with no dead ends.
- **Home island bridge points:** west shore at picture (40, 460) and east shore at (1440, 420). Both are an easy walk from the house. A north bridge would be hidden behind the house, and its area is only reachable the long way round the pen.
- **Ducklings:** 8 in total, 1 on the home island and 1 on each new island. The start card text ("5 babies") and the counter then need to say 8.
- **Boat:** keep the channel south of the home dock clear, because the boat rows 330 px straight down from its mooring.

**To build once the art is approved**
1. **Island pictures:**
   - Cut each one to its land plus about 60 px of water.
   - Fade the water edge into the sea like `home.webp`.
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
