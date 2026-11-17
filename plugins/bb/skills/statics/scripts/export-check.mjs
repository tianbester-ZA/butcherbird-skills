#!/usr/bin/env node
// Checks the editable files before anyone opens them. Run it after export.mjs.
//
//   node export-check.mjs <out folder> [name-filter] [--edit <folder>] [--compare]
//
// For every <id>_<size>.svg in <out>/edit (or --edit):
//   1. Fonts: every font-family in the file is the PostScript name of a font in edit/fonts. A family name such as
//      "Geist" opens without a warning but the editor quietly picks another weight, so this is checked by name.
//   2. Chrome: draws the SVG and compares it with the PNG (average difference, and the worst 48px square).
//   3. Words: every word in the ad is live text in the SVG, nothing missing, nothing extra.
//   4. VectorCraft, if this Mac has its CLI: opens the file headless, exports a PNG and reports its warnings.
//      Zero font warnings is a pass. Its picture is compared with the PNG too.
// --compare also writes <edit>/_compare.jpg: the PNG, Chrome's SVG and VectorCraft's SVG side by side.
// Exit 0 only when every file passes.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { launch, args, SIZES, sizeOf, vectorcraftCli, needDir, cmd } from './lib/env.mjs';
import { postscriptName } from './lib/fontname.mjs';
import { board } from './lib/board.mjs';

const { pos, opt } = args(undefined, ['compare']);
const [outDir, filter] = pos;
if (!outDir) { console.error('usage: node export-check.mjs <out folder> [name-filter] [--edit <folder>] [--compare]'); process.exit(1); }
const dir = path.resolve(outDir), edit = path.resolve(opt.edit || path.join(dir, 'edit'));
needDir(dir, 'Give the out folder render.mjs wrote to.');
if (!fs.existsSync(edit)) throw new Error(`No editable files yet at ${edit}. Run: ${cmd('export.mjs', dir)}`);
const LIMIT = { mean: 3, worst: 60 }; // average and worst-square difference, 0 to 255; real exports run 0.4 to 2.2 mean
const VC_LIMIT = { mean: 6, worst: 90 }; // VectorCraft draws text and soft edges a little differently from Chrome

const shipped = new Set();
for (const f of fs.existsSync(path.join(edit, 'fonts')) ? fs.readdirSync(path.join(edit, 'fonts')) : []) {
  const n = postscriptName(path.join(edit, 'fonts', f)); if (n) shipped.add(n);
}
const cli = vectorcraftCli();
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'bb-statics-check-'));

const browser = await launch();
const cmp = await browser.newPage();
const b64 = (f) => fs.readFileSync(f).toString('base64');
const diff = (a, b) => cmp.evaluate(async ([a, b]) => {
  const load = async (s) => { const i = new Image(); i.src = 'data:image/png;base64,' + s; await i.decode(); const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const x = c.getContext('2d'); x.drawImage(i, 0, 0); return x.getImageData(0, 0, c.width, c.height); };
  const A = await load(a), B = await load(b);
  if (A.width !== B.width || A.height !== B.height) return { mean: 255, worst: 255, at: [0, 0], note: `size ${B.width}x${B.height}` };
  const w = A.width, h = A.height, T = 48, tiles = new Map(); let sum = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const i = (y * w + x) * 4, d = (Math.abs(A.data[i] - B.data[i]) + Math.abs(A.data[i + 1] - B.data[i + 1]) + Math.abs(A.data[i + 2] - B.data[i + 2])) / 3;
    sum += d; const k = ((y / T) | 0) * 1000 + ((x / T) | 0); tiles.set(k, (tiles.get(k) || 0) + d);
  }
  let worst = 0, wk = 0; for (const [k, v] of tiles) if (v > worst) { worst = v; wk = k; }
  return { mean: sum / (w * h), worst: worst / (T * T), at: [(wk % 1000) * T, ((wk / 1000) | 0) * T] };
}, [a, b]);

const files = fs.readdirSync(edit).filter((f) => f.endsWith('.svg') && sizeOf(f) && (!filter || f.includes(filter))).sort();
if (!files.length) { console.error(`No editable files in ${edit}. Run export.mjs first.`); process.exit(1); }
let failed = 0;
const pics = {};
for (const f of files) {
  const base = f.replace(/\.svg$/, ''), H = SIZES[sizeOf(f)][1], svgFile = path.join(edit, f), pngFile = path.join(dir, base + '.png');
  const svg = fs.readFileSync(svgFile, 'utf8'), bad = [], notes = [];

  // 1. fonts named by PostScript name
  const families = [...new Set([...svg.matchAll(/font-family="([^"]+)"/g)].map((m) => m[1]))];
  for (const fam of families) if (!shipped.has(fam)) bad.push(`font "${fam}" isn't the PostScript name of any font in edit/fonts`);

  // 2. Chrome render vs PNG
  const page = await browser.newPage({ viewport: { width: 1080, height: 2000 }, deviceScaleFactor: 1 });
  await page.goto(pathToFileURL(svgFile).href);
  await page.evaluate(async (fams) => { for (const fm of fams) await document.fonts.load(`20px "${fm}"`); await document.fonts.ready; }, families);
  await page.waitForTimeout(250);
  const chromePng = (await page.screenshot({ type: 'png', clip: { x: 0, y: 0, width: 1080, height: H } })).toString('base64');
  await page.close();
  const d = await diff(b64(pngFile), chromePng);
  if (d.mean > LIMIT.mean || d.worst > LIMIT.worst) bad.push(`Chrome's drawing of the SVG differs from the PNG (average ${d.mean.toFixed(2)}, worst square ${d.worst.toFixed(1)} at ${d.at})`);
  notes.push(`chrome ${d.mean.toFixed(2)} avg / ${d.worst.toFixed(1)} worst`);

  // 3. words
  const hp = await browser.newPage({ viewport: { width: 1080, height: 2000 } });
  await hp.goto(pathToFileURL(path.join(dir, base + '.html')).href); await hp.evaluate(() => document.fonts.ready);
  const htmlWords = (await hp.evaluate(() => document.getElementById('ad').innerText)).split(/\s+/).filter(Boolean).sort();
  await hp.close();
  const svgWords = [...svg.matchAll(/<text\b[^>]*>([\s\S]*?)<\/text>/g)].map((m) => m[1].replace(/<tspan x=/g, ' <tspan x=').replace(/<[^>]+>/g, '').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')).join(' ').split(/\s+/).filter(Boolean);
  const missing = htmlWords.filter((w) => { const i = svgWords.indexOf(w); if (i < 0) return true; svgWords.splice(i, 1); return false; });
  if (missing.length) bad.push(`words missing from the live text: ${missing.join(' ')}`);
  if (svgWords.length) bad.push(`extra words in the live text: ${svgWords.join(' ')}`);

  // 4. VectorCraft headless
  pics[base] = { png: b64(pngFile), chrome: chromePng };
  if (cli) {
    const vcPng = path.join(tmp, base + '.png');
    let text = '';
    try { text = execFileSync(cli, ['run', '--in', svgFile, '--export', vcPng, '--scale', '1'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], timeout: 120000 }); }
    catch (e) { text = (e.stdout || '') + (e.stderr || ''); bad.push(`VectorCraft couldn't open or export it (${String(e.message).split('\n')[0]})`); }
    const warnings = text.split('\n').filter((l) => l.trim().startsWith('{')).flatMap((l) => { try { const j = JSON.parse(l); return [...(j.result?.warnings || []), ...(j.result?.missingLinks || []).map((m) => `missing link ${m}`)]; } catch { return []; } });
    const fontWarn = warnings.filter((w) => /font/i.test(w));
    if (fontWarn.length) bad.push(`VectorCraft font warning: ${fontWarn.join(' | ')}`);
    for (const w of warnings.filter((w) => !/font/i.test(w))) notes.push(`VectorCraft says: ${w}`);
    if (fs.existsSync(vcPng)) {
      const v = await diff(b64(pngFile), b64(vcPng));
      if (v.mean > VC_LIMIT.mean || v.worst > VC_LIMIT.worst) bad.push(`VectorCraft's drawing differs from the PNG (average ${v.mean.toFixed(2)}, worst square ${v.worst.toFixed(1)} at ${v.at})${v.note ? `, ${v.note}` : ''}`);
      notes.push(`vectorcraft ${v.mean.toFixed(2)} avg / ${v.worst.toFixed(1)} worst, ${warnings.length} warning(s)`);
      pics[base].vc = b64(vcPng);
    }
  }
  const layers = [...svg.matchAll(/<g id="([^"]+)"/g)].map((m) => m[1]);
  console.log(`${bad.length ? 'FAIL' : 'PASS'}  ${f}   ${notes.join('; ')}; fonts ${families.join(', ')}; layers ${layers.join(', ')}`);
  for (const m of bad) console.log(`      ${m}`);
  if (bad.length) failed++;
}
if (!cli) console.log('\nVectorCraft CLI not found, so files were not opened the way VectorCraft will. setup.py --install-vectorcraft adds it.');

if (opt.compare) {
  const h = 560, rows = Object.entries(pics).map(([b, p]) => {
    const w = Math.round(1080 * h / SIZES[sizeOf(b + '.svg')][1]);
    const cells = [{ data: p.png, w, h, caption: 'PNG (the ad)' }, { data: p.chrome, w, h, caption: 'SVG in Chrome' }];
    if (p.vc) cells.push({ data: p.vc, w, h, caption: 'SVG in VectorCraft' });
    return { label: b, cells };
  });
  const dest = path.join(edit, '_compare.jpg');
  await board(browser, rows, dest);
  console.log(`\ncompare sheet: ${dest}\nOpen it. In each row the three pictures should look the same. Look hardest at the type: a different weight or width means a font was swapped; a missing product or logo means a layer didn't export.`);
}
await browser.close();
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`\n${files.length - failed} of ${files.length} editable file(s) pass.`);
if (!failed) console.log(`Next, to make the delivery folder:  ${cmd('deliver.mjs', dir, '--name', '<Client job name>')}`);
process.exit(failed ? 1 : 0);
