// Opens the built school island (dist/school.html) in a hidden Chrome and plays a whole game by itself:
// walks to every orange flower, takes them to the garden, and checks the "garden is blooming" card.
// Run after `npm run build`:  node tools/school_check.mjs [width] [height] [mobile]
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
const port = 9334;
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
  if (m.method === 'Runtime.exceptionThrown') logs.push('[EXCEPTION] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') logs.push(`[error] ${m.params.entry.text} ${m.params.entry.url || ''}`);
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; waiting.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const evaluate = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
const shot = async (name) => {
  const r = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(path.join(out, name), Buffer.from(r.result.data, 'base64'));
};
const S = `game.scene.getScene('school')`;
const state = () => evaluate(`(() => { const s = ${S}; if (!s) return 'no scene';
  return { playing: s.playing, player: [Math.round(s.player.x), Math.round(s.player.y)], carried: s.carried, planted: s.planted,
    flowers: s.flowers.map(f => f.state[0]).join(''), fps: Math.round(s.game.loop.actualFps) }; })()`);

await send('Runtime.enable');
await send('Log.enable');
await send('Page.enable');
if (MOBILE) {
  await send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 2, mobile: true });
  await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
}
const url = pageUrl('school.html');
await send('Page.navigate', { url });
await sleep(4000);
console.log('title card:', await evaluate(`document.getElementById('play').textContent`));
await shot('school-1-title.png');
await evaluate(`document.getElementById('play').click()`);
await sleep(1600);
console.log('after Play:', JSON.stringify(await state()));
await shot('school-2-playing.png');

const n = await evaluate(`${S}.flowers.length`);
for (let i = 0; i < n; i++) {
  const t0 = Date.now();
  await evaluate(`(() => { const s = ${S}; const f = s.flowers[${i}]; if (f.state === 'waiting') s.walkTo(f.x, f.y, true); })()`);
  let st;
  while (Date.now() - t0 < 30000) {
    await sleep(250);
    st = await evaluate(`${S}.flowers[${i}].state`);
    if (st !== 'waiting') break;
    if (await evaluate(`!${S}.path?.length`)) break;
  }
  console.log(`flower ${i}: ${st} after ${((Date.now() - t0) / 1000).toFixed(1)}s`, JSON.stringify(await state()));
  if (i === 1) await shot('school-3-walking.png');
}
await evaluate(`${S}.goToGarden()`);
const t1 = Date.now();
let won = false;
while (Date.now() - t1 < 40000) {
  await sleep(300);
  if (await evaluate(`!document.getElementById('win').hidden`)) { won = true; break; }
  if (Date.now() - t1 > 1500 && await evaluate(`${S}.planted === 5`)) await sleep(0);
}
await shot('school-4-garden.png');
console.log('after the garden:', JSON.stringify(await state()), 'win card shown:', won);
console.log('--- errors ---\n' + logs.join('\n'));
ws.close();
chrome.kill();
