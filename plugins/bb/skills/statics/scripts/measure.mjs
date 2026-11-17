#!/usr/bin/env node
// Two ways of looking closely at a picture, both in the picture's own pixels.
//
//   node measure.mjs grid <image> <out.png> [x y w h] [--step 50]
//       Draws a labelled grid over the picture (or one area of it), so you can read off coordinates: where a
//       product's four corners sit for h.quad, where garbled print is for h.soften, where the empty space starts.
//   node measure.mjs crop <image> <out.png> x y w h
//       Zooms into one area (up to 3x), so you can read every word on a label. Do it for every pack in every ad.
//
// Works on scenes (PNG, JPEG, SVG) and on rendered ads.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch, args } from './lib/env.mjs';

const { pos, opt } = args();
const [mode, src, out, ...box] = pos;
if (!['grid', 'crop'].includes(mode) || !src || !out) {
  console.error('usage:\n  node measure.mjs grid <image> <out.png> [x y w h] [--step 50]\n  node measure.mjs crop <image> <out.png> x y w h');
  process.exit(1);
}
const b = await launch();
try {
  const p = await b.newPage({ viewport: { width: 1200, height: 1200 } });
  const url = pathToFileURL(path.resolve(src)).href;
  const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'bb-measure-')), 'm.html');
  fs.writeFileSync(tmp, `<body style="margin:0"><img id="i" src="${url}"></body>`);
  await p.goto(pathToFileURL(tmp).href, { waitUntil: 'load' });
  const [NW, NH] = await p.evaluate(() => [document.getElementById('i').naturalWidth, document.getElementById('i').naturalHeight]);
  if (!NW) throw new Error(`Couldn't open ${src}`);
  let [x, y, w, h] = box.length === 4 ? box.map(Number) : [0, 0, NW, NH];
  if (mode === 'crop' && box.length !== 4) throw new Error('crop needs x y w h');
  const step = +(opt.step || 50);
  const s = mode === 'crop' ? Math.min(3, 1100 / w, 1100 / h) : Math.min(1, 1100 / w, 1100 / h);
  const W = Math.round(w * s), H = Math.round(h * s);
  let lines = '';
  if (mode === 'grid') {
    for (let gx = Math.ceil(x / step) * step; gx < x + w; gx += step) {
      const major = gx % (step * 2) === 0;
      lines += `<div style="position:absolute;left:${(gx - x) * s}px;top:0;width:1px;height:100%;background:rgba(0,255,255,${major ? 0.75 : 0.3})"></div>`;
      if (major) lines += `<div style="position:absolute;left:${(gx - x) * s + 2}px;top:2px;font:11px monospace;color:#0ff;text-shadow:0 0 2px #000">${gx}</div>`;
    }
    for (let gy = Math.ceil(y / step) * step; gy < y + h; gy += step) {
      const major = gy % (step * 2) === 0;
      lines += `<div style="position:absolute;top:${(gy - y) * s}px;left:0;height:1px;width:100%;background:rgba(255,0,255,${major ? 0.75 : 0.3})"></div>`;
      if (major) lines += `<div style="position:absolute;top:${(gy - y) * s + 2}px;left:2px;font:11px monospace;color:#f0f;text-shadow:0 0 2px #000">${gy}</div>`;
    }
  }
  fs.writeFileSync(tmp, `<body style="margin:0;overflow:hidden;position:relative;width:${W}px;height:${H}px;background:#777"><img src="${url}" style="position:absolute;left:${-x * s}px;top:${-y * s}px;width:${NW * s}px;height:${NH * s}px">${lines}</body>`);
  await p.setViewportSize({ width: W, height: H });
  await p.goto(pathToFileURL(tmp).href, { waitUntil: 'load' });
  await p.waitForTimeout(200);
  await p.screenshot({ path: path.resolve(out), clip: { x: 0, y: 0, width: W, height: H } });
  console.log(`${path.resolve(out)}  (${mode} of ${src}: area ${x},${y} ${w}x${h} of ${NW}x${NH}, shown at ${s.toFixed(2)}x)`);
} finally { await b.close(); }
