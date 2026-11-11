#!/usr/bin/env node
// Render transparent PNG frames of an SVG overlay page with headless Chrome over CDP.
// usage: node render.js <page.html> <outdir> <fps> <duration_s> [mode] [start_s] [end_s]
// The page must define window.draw(t, mode) -> Promise. Frames are written as f%05d.png, 1080x1920, alpha.
const {spawn} = require('child_process');
const fs = require('fs'); const path = require('path');
const [,, page, outdir, fpsS, durS, mode='916', startS='0', endS=''] = process.argv;
const FPS = +fpsS, DUR = +durS, W = 1080, H = 1920;
const start = Math.round(+startS * FPS), end = endS ? Math.round(+endS * FPS) : Math.round(DUR * FPS);
fs.mkdirSync(outdir, {recursive: true});
// Copy-free headless Chrome first: every launch of the Chrome app leaves a 1.4 GB code_sign_clone copy on disk.
const CHROME = (() => {
  const home = require('os').homedir(), pw = path.join(home, 'Library/Caches/ms-playwright');
  const shells = fs.existsSync(pw) ? fs.readdirSync(pw).filter(d => d.startsWith('chromium_headless_shell-')).sort().reverse()
    .flatMap(d => ['arm64', 'x64'].map(a => path.join(pw, d, `chrome-headless-shell-mac-${a}`, 'chrome-headless-shell'))) : [];
  const c = [process.env.CHROME_PATH, process.env.CHROME_BIN, path.join(home, '.local/bin/chrome-headless'), ...shells,
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  return c.find(p => p && fs.existsSync(p)) || c[c.length - 1];
})();
if (!fs.existsSync(CHROME)) { console.error('no Chrome at ' + CHROME + ': install Google Chrome or set CHROME_PATH'); process.exit(1); }
if (typeof WebSocket === 'undefined') { console.error('render.js needs Node 22 or newer: brew install node'); process.exit(1); }
const port = 9333 + Math.floor(Math.random() * 500);
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, '--disable-gpu', '--hide-scrollbars', `--window-size=${W},${H}`,
  '--no-first-run', '--no-default-browser-check', '--user-data-dir=' + fs.mkdtempSync(path.join(require('os').tmpdir(), 'bb-drawn-chrome-')), 'about:blank'], {stdio: 'ignore'});
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  let targets = null;
  for (let i = 0; i < 50 && !(targets && targets.some(t => t.type === 'page')); i++) { await sleep(200); try { targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json(); } catch (e) {} }
  if (!targets) throw new Error('chrome did not start');
  const pageT = targets.find(t => t.type === 'page');
  const ws = new WebSocket(pageT.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = new Map();
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { const {res, rej} = pending.get(m.id); pending.delete(m.id); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); } };
  const send = (method, params = {}) => new Promise((res, rej) => { const i = ++id; pending.set(i, {res, rej}); ws.send(JSON.stringify({id: i, method, params})); });
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', {width: W, height: H, deviceScaleFactor: 1, mobile: false});
  await send('Emulation.setDefaultBackgroundColorOverride', {color: {r: 0, g: 0, b: 0, a: 0}});
  await send('Page.navigate', {url: 'file://' + path.resolve(page)});
  await sleep(600);
  await send('Runtime.evaluate', {expression: 'document.fonts ? document.fonts.ready.then(()=>true) : true', awaitPromise: true});
  const t0 = Date.now();
  for (let f = start; f < end; f++) {
    const t = f / FPS;
    await send('Runtime.evaluate', {expression: `window.draw(${t}, '${mode}')`, awaitPromise: true});
    const shot = await send('Page.captureScreenshot', {format: 'png', fromSurface: true, captureBeyondViewport: false});
    fs.writeFileSync(path.join(outdir, `f${String(f).padStart(5, '0')}.png`), Buffer.from(shot.data, 'base64'));
    if (f % 150 === 0) process.stderr.write(`frame ${f}/${end} ${((Date.now() - t0) / 1000).toFixed(0)}s\n`);
  }
  ws.close(); chrome.kill();
  console.log(`done ${end - start} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s -> ${outdir}`);
  process.exit(0);
})().catch(e => { console.error(e); chrome.kill(); process.exit(1); });
