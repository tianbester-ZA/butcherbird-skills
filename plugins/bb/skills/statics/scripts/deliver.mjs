#!/usr/bin/env node
// Builds the folder we hand over: one numbered folder per size, a carousel folder, and the editable files.
//
//   node deliver.mjs <out folder> --name "<Client job name>" [--to <folder>] [--replace]
//
// Default --to: a "delivery" folder beside the out folder. Example result:
//   01 Stories and Reels 9x16/01 Fynn Toasty Toes 9x16.png
//   02 Feed 4x5/01 Fynn Toasty Toes 4x5.png
//   03 Square 1x1/01 Fynn Toasty Toes 1x1.png
//   04 Carousel/01 Fynn Cover 4x5.png ...        ads whose id starts with car- (in order)
//   05 Editable (SVG)/... .svg, fonts/, README.txt
// Ads are numbered in the order the job file lists them. It copies; nothing is uploaded or sent.
import fs from 'node:fs';
import path from 'node:path';
import { args, sizeOf, needDir, cmd } from './lib/env.mjs';

const { pos, opt } = args(undefined, ['replace']);
const [outDir] = pos;
if (!outDir) { console.error('usage: node deliver.mjs <out folder> --name "<Client job name>" [--to <folder>] [--replace]'); process.exit(1); }
const out = path.resolve(outDir);
needDir(out, 'Give the out folder render.mjs wrote to.');
const name = (opt.name || '').trim();
const to = path.resolve(opt.to || path.join(path.dirname(out), 'delivery'));
if (fs.existsSync(to) && fs.readdirSync(to).length) {
  if (!opt.replace) throw new Error(`${to} already has files in it. Add --replace to rebuild it, or pick another folder with --to.`);
  fs.rmSync(to, { recursive: true, force: true });
}
const layoutFile = path.join(out, 'layout.json');
const order = fs.existsSync(layoutFile) ? [...new Set(Object.values(JSON.parse(fs.readFileSync(layoutFile, 'utf8'))).map((a) => a.id))] : [];
const pngs = fs.readdirSync(out).filter((f) => f.endsWith('.png') && sizeOf(f));
if (!pngs.length) throw new Error(`No ads in ${out}. Render first.`);
const idOf = (f) => f.replace(/_(9x16|4x5|1x1)\.[a-z]+$/, '');
for (const id of [...new Set(pngs.map(idOf))].sort()) if (!order.includes(id)) order.push(id);
const isCarousel = (id) => /^car(ousel)?[-_]/i.test(id);
const title = (id) => id.replace(/^car(ousel)?[-_]\d*[-_]?/i, '').split(/[-_]+/).filter(Boolean).map((w) => w[0].toUpperCase() + w.slice(1)).join(' ');
const fileName = (n, id, size, ext) => `${String(n).padStart(2, '0')} ${[name, title(id)].filter(Boolean).join(' ')} ${size}.${ext}`;

const groups = [
  ['Stories and Reels 9x16', (id, s) => !isCarousel(id) && s === '9x16'],
  ['Feed 4x5', (id, s) => !isCarousel(id) && s === '4x5'],
  ['Square 1x1', (id, s) => !isCarousel(id) && s === '1x1'],
  ['Carousel', (id) => isCarousel(id)],
];
let folderN = 0, copied = 0;
const made = [];
for (const [label, take] of groups) {
  const ids = order.filter((id) => pngs.some((f) => idOf(f) === id && take(id, sizeOf(f))));
  if (!ids.length) continue;
  const folder = path.join(to, `${String(++folderN).padStart(2, '0')} ${label}`);
  fs.mkdirSync(folder, { recursive: true });
  ids.forEach((id, i) => {
    for (const f of pngs.filter((f) => idOf(f) === id && take(id, sizeOf(f)))) {
      fs.copyFileSync(path.join(out, f), path.join(folder, fileName(i + 1, id, sizeOf(f), 'png')));
      copied++;
    }
  });
  made.push(`${path.basename(folder)} (${ids.length})`);
}

const edit = path.join(out, 'edit');
const svgs = fs.existsSync(edit) ? fs.readdirSync(edit).filter((f) => f.endsWith('.svg') && sizeOf(f)) : [];
if (svgs.length) {
  const folder = path.join(to, `${String(++folderN).padStart(2, '0')} Editable (SVG)`);
  fs.mkdirSync(folder, { recursive: true });
  for (const f of svgs) {
    const id = idOf(f), n = order.filter((x) => isCarousel(x) === isCarousel(id)).indexOf(id) + 1;
    fs.copyFileSync(path.join(edit, f), path.join(folder, fileName(n, id, sizeOf(f), 'svg')));
  }
  if (fs.existsSync(path.join(edit, 'fonts'))) fs.cpSync(path.join(edit, 'fonts'), path.join(folder, 'fonts'), { recursive: true });
  fs.writeFileSync(path.join(folder, 'README.txt'), `Editable files${name ? ` for ${name}` : ''}

Open any .svg in VectorCraft (free), Illustrator or Figma. Keep the fonts folder beside the files.

1. Install the fonts in the fonts folder first (double-click each, then Install), or the editor swaps them.
2. Layers, back to front: background, scene (the picture), product-... (each real product, movable),
   effect-... (smoke or glow), logo (vector), type (live text: headline, offer, small line).
3. Moving a product a long way shows the picture underneath it, which may be a rough version of the product.
4. Export at 1x for 1080px wide.
`);
  made.push(`${path.basename(folder)} (${svgs.length}, with fonts and a README)`);
} else {
  console.log(`No editable files yet, so no Editable folder. Make them with:  ${cmd('export.mjs', out)}`);
}
console.log(`Delivery folder: ${to}\n  ${made.join('\n  ')}\n${copied} PNG(s). Check it, then it goes to Drive or the client portal only after the person's yes.`);
