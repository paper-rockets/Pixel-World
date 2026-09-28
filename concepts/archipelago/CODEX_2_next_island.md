# Codex message 2: skip the campfire redraw, make the next island

Use this if the user approves the fixed campfire island (`check/match_sw_campfire.png`). It replaces `CODEX_FIX_1_sw_campfire.md`. Copy everything below the line into Codex.

---

Change of plan: **don't redraw the campfire island.** If you already made `sw_campfire_v2.png`, keep it, but don't do more work on it. Claude matched `sw_campfire.png` to `tiny_map.png` in code (colours, grass texture, water, wider path and stairs), and it's approved.

Next, make **one** new island picture, `E:\X Phaser\source_art\archipelago\ground\se_meadow.png`, following Part A of `E:\X Phaser\concepts\archipelago\CODEX_PROMPT.md`, then stop.

Read `CODEX_PROMPT.md` again before you start. Its style rules have changed:

- The palette table now has colours measured from `tiny_map.png`. Use them, and nothing brighter or stronger.
- Cliffs are flat-fronted, squarish tan stone slabs with thin dark cracks, like `tiny_map.png`. No round boulders, no orange, no dark red outlines.
- No big area of grass or water is one flat colour: the grass has lighter and darker patches and lots of tiny tufts; the water has a light shallow band along the shore and ripple lines.
- Paths are about 70 px wide (like `tiny_map.png`'s path from the house down to the dock), and stairs are about 80 px wide (like that dock's walkway). The capybara is 50 px wide and needs room on both sides.

Also for `se_meadow.png`: keep at least 90 px of plain sea between the island's outer foam and every edge of the picture, so the island is at most about 1260 × 900.

The rules about files are the same: only add new files inside `E:\X Phaser\source_art\archipelago\`, and don't touch anything else.

Save `se_meadow.png`, say it is ready, and stop.
