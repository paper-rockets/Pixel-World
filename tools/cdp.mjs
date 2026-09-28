// Tiny helper: open a built page from dist/ in a hidden Chrome and drive it.
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

export const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Chrome on the PC (or a Mac), or the Chromium that Playwright keeps on Linux. CHROME=path picks another.
export function findChrome() {
  const found = [
    process.env.CHROME,
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    path.join(process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers', 'chromium'),
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].find((p) => p && fs.existsSync(p));
  if (!found) throw new Error('Chrome not found. Set CHROME to the path of chrome.exe (or chromium).');
  return found;
}

// start a hidden Chrome that the test scripts drive through its debugging port
export function launchChrome(port, width, height) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'islands-'));
  const args = [
    '--headless=new', `--remote-debugging-port=${port}`, '--allow-file-access-from-files',
    '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required',
    `--user-data-dir=${profile}`, `--window-size=${width},${height}`,
  ];
  // cloud containers run as root with a small /dev/shm, which Chrome's sandbox and memory use don't like
  if (process.platform === 'linux') args.push('--no-sandbox', '--disable-dev-shm-usage');
  return spawn(findChrome(), [...args, 'about:blank'], { stdio: 'ignore' });
}

// a built page in dist/, with ?debug so the scripts can reach window.game
export const pageUrl = (page) => pathToFileURL(path.join(root, 'dist', page)).href + '?debug';

export async function openPage(page, { width = 1280, height = 800, mobile = false, port = 9335 } = {}) {
  const out = path.join(root, 'check');
  fs.mkdirSync(out, { recursive: true });
  const chrome = launchChrome(port, width, height);
  let target;
  for (let i = 0; i < 50 && !target; i++) {
    await sleep(200);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page'); } catch {}
  }
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r));
  let id = 0;
  const waiting = new Map();
  const errors = [];
  ws.addEventListener('message', (e) => {
    const m = JSON.parse(e.data);
    if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m); waiting.delete(m.id); }
    if (m.method === 'Runtime.exceptionThrown') errors.push('[EXCEPTION] ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
    if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errors.push(`[error] ${m.params.entry.text} ${m.params.entry.url || ''}`);
  });
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; waiting.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const evaluate = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true })).result?.result?.value;
  const shot = async (name) => {
    const r = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(out, name), Buffer.from(r.result.data, 'base64'));
  };
  await send('Runtime.enable');
  await send('Log.enable');
  await send('Page.enable');
  if (mobile) {
    await send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 2, mobile: true });
    await send('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
  }
  await send('Page.navigate', { url: pageUrl(page) });
  await sleep(4000);
  const close = () => { ws.close(); chrome.kill(); };
  return { evaluate, shot, errors, close };
}

// wait until expr is true (checked every 200 ms); returns false on timeout
export async function waitFor(evaluate, expr, ms = 20000) {
  const t0 = Date.now();
  while (Date.now() - t0 < ms) {
    if (await evaluate(expr)) return true;
    await sleep(200);
  }
  return false;
}
