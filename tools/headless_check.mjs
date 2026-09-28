// Opens the built game (dist/) in a hidden Chrome, presses Play, taps the island, and saves screenshots.
// Run after `npm run build`:  node tools/headless_check.mjs [width] [height] [mobile]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { launchChrome, pageUrl } from './cdp.mjs';

const W = +(process.argv[2] || 1280);
const H = +(process.argv[3] || 800);
const MOBILE = process.argv[4] === 'mobile';
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'check');
fs.mkdirSync(out, { recursive: true });
const port = 9333;
const chrome = launchChrome(port, W, H);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 50 && !target; i++) {
  await sleep(200);
  try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page'); } catch {}
}
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r));
let id = 0;
const waiting = new Map();
const logs = [];
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data);
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
  if (m.method === 'Runtime.consoleAPICalled') logs.push(`[${m.params.type}] ` + m.params.args.map((a) => a.value ?? a.description).join(' '));
  if (m.method === 'Runtime.exceptionThrown') logs.push('[EXCEPTION] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Log.entryAdded') logs.push(`[${m.params.entry.level}] ${m.params.entry.text} ${m.params.entry.url || ''}`);
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waiting.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const shot = async (name) => {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(out, name), Buffer.from(r.result.data, 'base64'));
};
const tap = async (x, y, holdMs = 60) => {
  if (MOBILE) {
    await send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [{ x, y }] });
    await sleep(holdMs);
    await send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  } else {
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x, y });
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x, y, button: 'left', clickCount: 1 });
    await sleep(holdMs);
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x, y, button: 'left', clickCount: 1 });
  }
};
const state = () => evaluate(`(() => { const s = window.game?.scene?.getScene('play'); if (!s) return 'no scene';
  return { playing: s.playing, player: [Math.round(s.player.x), Math.round(s.player.y)], path: s.path?.length ?? null,
    zoom: +s.cameras.main.zoom.toFixed(2), followers: s.followers.length, home: s.homeCount, total: s.total,
    chicks: s.chicks.map(c => c.state[0] + '@' + Math.round(c.gx) + ',' + Math.round(c.gy)).join(' '),
    fps: Math.round(s.game.loop.actualFps), frame: s.game.loop.frame }; })()`);

await send('Runtime.enable');
await send('Log.enable');
await send('Page.enable');
if (MOBILE) {
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
}
const url = pageUrl('index.html');
await send('Page.navigate', { url });
await sleep(4000);
console.log('play button:', await evaluate(`document.getElementById('play').textContent + ' disabled=' + document.getElementById('play').disabled`));
console.log('state 1:', JSON.stringify(await state()));
await shot('1-title.png');

const play = await evaluate(`(() => { const r = document.getElementById('play').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; })()`);
await tap(play[0], play[1]);
await sleep(1600);
console.log('state 2 (after Play):', JSON.stringify(await state()));
await shot('2-playing.png');

// tap to the lower-left of the capybara, then hold to the right
await tap(W * 0.3, H * 0.7);
await sleep(1500);
console.log('state 3 (after tap):', JSON.stringify(await state()));
await shot('3-walked.png');

if (process.argv[5] === 'poses') {
  // put the capybara at spots the user reported and save a close-up of each
  const poses = JSON.parse(fs.readFileSync(path.join(root, 'tools', 'poses.json'), 'utf8'));
  for (const [i, p] of poses.entries()) {
    // move to the nearest spot the capybara can really stand on
    const at = await evaluate(`(() => { const s = game.scene.getScene('play'); let best = null;
      for (let r = 0; r <= 60 && !best; r += 2) for (let a = 0; a < 360 && !best; a += 10) {
        const x = ${p.x} + r * Math.cos(a * Math.PI / 180), y = ${p.y} + r * Math.sin(a * Math.PI / 180);
        if (s.nav.canStand(x, y)) best = [Math.round(x), Math.round(y)]; }
      best = best || [${p.x}, ${p.y}];
      s.path = null; s.player.setPosition(best[0], best[1]);
      s.facing = '${p.face}'; s.player.anims.stop(); s.player.setFrame({ down: 0, left: 4, right: 8, up: 12 }['${p.face}']);
      s.cameras.main.stopFollow(); s.cameras.main.centerOn(best[0], best[1] - 20); return best; })()`);
    await sleep(500);
    console.log(`pose ${i} ${p.name}: asked ${p.x},${p.y} -> stands at ${at}`);
    await shot(`pose-${i}.png`);
  }
}

if (process.argv[5] === 'full') {
  // close-ups: capybara just behind, then just in front of, the painted bush by the cliff (350, 604)
  const pose = async (x, y, face, name) => {
    await evaluate(`(() => { const s = game.scene.getScene('play'); s.path = null; s.player.setPosition(${x}, ${y});
      s.facing = '${face}'; s.player.setFrame({ down: 0, left: 4, right: 8, up: 12 }['${face}']);
      s.cameras.main.stopFollow(); s.cameras.main.centerOn(${x}, ${y} - 20); })()`);
    await sleep(300);
    await shot(name);
  };
  const bush = await evaluate(`Object.values(game.scene.getScene('play').nav.blockers).length`);
  console.log('walls:', bush);
  await pose(350, 612, 'left', '4-behind-bush.png');
  await pose(350, 700, 'left', '5-front-of-bush.png');
  await evaluate(`game.scene.getScene('play').cameras.main.startFollow(game.scene.getScene('play').player, false, 0.15, 0.15)`);
  await evaluate(`(() => { const s = game.scene.getScene('play'); s.player.setPosition(880, 440); s.trail = []; })()`);

  // play a whole game: walk to each hiding duckling, then take everyone home
  const n = await evaluate(`game.scene.getScene('play').chicks.length`);
  for (let i = 0; i < n; i++) {
    const t0 = Date.now();
    await evaluate(`(() => { const s = game.scene.getScene('play'); const c = s.chicks[${i}]; if (c.state === 'hidden') s.walkTo(c.gx, c.gy, true); })()`);
    let st;
    while (Date.now() - t0 < 30000) {
      await sleep(250);
      st = await evaluate(`game.scene.getScene('play').chicks[${i}].state`);
      if (st !== 'hidden') break;
      const idle = await evaluate(`!game.scene.getScene('play').path?.length`);
      if (idle) break;
    }
    console.log(`duckling ${i}: ${st} after ${((Date.now() - t0) / 1000).toFixed(1)}s`, JSON.stringify(await state()));
  }
  await shot('6-line-of-ducklings.png');
  await evaluate(`game.scene.getScene('play').goHome()`);
  const t1 = Date.now();
  while (Date.now() - t1 < 40000) {
    await sleep(300);
    if (await evaluate(`!document.getElementById('win').hidden`)) break;
  }
  console.log('after going home:', JSON.stringify(await state()), 'win card shown:', await evaluate(`!document.getElementById('win').hidden`));
  await shot('7-win.png');
}

console.log('--- console ---\n' + logs.join('\n'));
ws.close();
chrome.kill();
