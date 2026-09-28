// Sails from the school island to Sunny Meadow and back in a hidden Chrome, with screenshots.
// Run after `npm run build`:  node tools/boat_check.mjs [width] [height] [mobile]
import { openPage, sleep, waitFor } from './cdp.mjs';

const [W, H, M] = [+(process.argv[2] || 1280), +(process.argv[3] || 800), process.argv[4] === 'mobile'];
const { evaluate, shot, errors, close } = await openPage('school.html', { width: W, height: H, mobile: M });
const island = `game.scene.getScenes(true).find(s => s.boat)`;
const where = () => evaluate(`(() => { const s = ${island}; return s && { island: s.scene.key, playing: s.playing, sailing: !!s.sailing,
  player: [Math.round(s.player.x), Math.round(s.player.y)], visible: s.player.visible,
  boat: [Math.round(s.boat.x), Math.round(s.boat.y)], sailButton: document.getElementById('sail').hidden ? null : document.getElementById('sail').textContent.trim(),
  counter: document.getElementById('count').textContent, icon: document.querySelector('#hud .pill img').getAttribute('src') }; })()`);

await evaluate(`document.getElementById('play').click()`);
await sleep(1600);
console.log('1 playing on:', JSON.stringify(await where()));

// walk to the dock end by tapping the boat
await evaluate(`(() => { const s = ${island}; s.walkTo(...s.boat.board, true); })()`);
const atDock = await waitFor(evaluate, `!document.getElementById('sail').hidden`, 15000);
console.log('2 at the dock, sail button shown:', atDock, JSON.stringify(await where()));
await shot('boat-1-dock.png');

await evaluate(`document.getElementById('sail').click()`);
await sleep(900);
console.log('3 rowing away:', JSON.stringify(await where()));
await shot('boat-2-rowing.png');

const arrived = await waitFor(evaluate, `(() => { const s = ${island}; return s && s.scene.key === 'play' && s.playing; })()`, 20000);
console.log('4 arrived on Sunny Meadow:', arrived, JSON.stringify(await where()));
await sleep(600);
await shot('boat-3-arrived.png');

// and back again: step off the dock first (the button waits until you have), then come back
await evaluate(`(() => { const s = ${island}; s.walkTo(s.boat.board[0] - 60, s.boat.board[1] - 60, true); })()`);
await sleep(1500);
console.log('5a stepped off:', JSON.stringify(await where()));
await evaluate(`(() => { const s = ${island}; s.walkTo(...s.boat.board, true); })()`);
await waitFor(evaluate, `!document.getElementById('sail').hidden`, 15000);
console.log('5 duck dock:', JSON.stringify(await where()));
await evaluate(`document.getElementById('sail').click()`);
await sleep(2400);
await shot('boat-4-arriving-school.png');
const back = await waitFor(evaluate, `(() => { const s = ${island}; return s && s.scene.key === 'school' && s.playing; })()`, 20000);
console.log('6 back at the school:', back, JSON.stringify(await where()));

// finishing an island and choosing "Sail to ..." on the win card
await evaluate(`(() => { const s = ${island}; s.flowers.forEach(f => { f.state = 'carried'; f.img.setVisible(false); }); s.planted = s.total; s.carried = 0; s.bloom(); })()`);
const card = await waitFor(evaluate, `!document.getElementById('win').hidden`, 8000);
console.log('7 win card:', card, await evaluate(`document.getElementById('winSail').textContent.trim()`));
await shot('boat-5-wincard.png');
await evaluate(`document.getElementById('winSail').click()`);
const viaCard = await waitFor(evaluate, `(() => { const s = ${island}; return s && s.scene.key === 'play' && s.playing; })()`, 20000);
console.log('8 sailed from the win card:', viaCard, JSON.stringify(await where()));

console.log('--- errors ---\n' + errors.join('\n'));
close();
