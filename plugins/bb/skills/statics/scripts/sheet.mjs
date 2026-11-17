#!/usr/bin/env node
// Contact sheet: every ad in an out folder on one picture, one row per ad, its sizes side by side at the same height,
// plus a copy 216px wide (about how big an ad is when someone glances at a feed) so you can check it still reads.
//
//   node sheet.mjs <out folder> [name-filter] [--out <file.jpg>] [--height 640]
//
// Default output: <out folder>/_sheet.jpg. Open it to review a round, or send it with the notes.
import fs from 'node:fs';
import path from 'node:path';
import { launch, args, SIZES, sizeOf, needDir, cmd } from './lib/env.mjs';
import { board } from './lib/board.mjs';

const { pos, opt } = args();
const [outDir, filter = ''] = pos;
if (!outDir) { console.error('usage: node sheet.mjs <out folder> [name-filter] [--out <file.jpg>] [--height 640]'); process.exit(1); }
const dir = path.resolve(outDir), H = +(opt.height || 640), dest = path.resolve(opt.out || path.join(dir, '_sheet.jpg'));
needDir(dir, 'Give the out folder render.mjs wrote to (it holds the PNGs and layout.json).');
const order = ['9x16', '4x5', '1x1'];
const groups = {};
for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.png') && sizeOf(f) && f.includes(filter)).sort()) {
  const id = f.replace(/_(9x16|4x5|1x1)\.png$/, '');
  (groups[id] = groups[id] || []).push(f);
}
if (!Object.keys(groups).length) throw new Error(`No <id>_<size>.png files in ${dir}. Run render.mjs first.`);
const rows = Object.entries(groups).map(([id, files]) => {
  files.sort((a, b) => order.indexOf(sizeOf(a)) - order.indexOf(sizeOf(b)));
  const cells = files.map((f) => { const [w, h] = SIZES[sizeOf(f)]; return { file: path.join(dir, f), w: Math.round(H * w / h), h: H, caption: sizeOf(f).replace('x', ':') }; });
  const [w, h] = SIZES[sizeOf(files[0])];
  cells.push({ file: path.join(dir, files[0]), w: 216, h: Math.round(216 * h / w), caption: '216px glance' });
  return { label: id, cells };
});
const b = await launch();
try { await board(b, rows, dest); } finally { await b.close(); }
console.log(`${dest}\nOpen it and look at each row: does the idea read, is each size laid out (not cropped), does the 216px copy still read?\nNext, when the person is happy:  ${cmd('export.mjs', dir)}`);
