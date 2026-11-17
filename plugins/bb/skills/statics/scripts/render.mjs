#!/usr/bin/env node
// Renders a job file into finished ads. Each ad is an HTML page that headless Google Chrome draws to a PNG.
//
//   node render.mjs <job.mjs> [ad-id ...] [--size 9x16] [--out <folder>]
//
// Writes, for every ad and size, into the job's out folder (default: out/ beside the job file):
//   <id>_<size>.png    the ad
//   <id>_<size>.html   the page it was drawn from (export.mjs reads this)
//   layout.json        where every text item, the logo and each product sit, the type sizes and the contrast
//                      of each line against what's behind it. gate.mjs checks this.
//   job.json           which kit and job made these files
//
// A job file is plain JavaScript that names its kit and describes each ad per size. See examples/fynn/job.mjs.
//   export const kit = './kit';                      // folder holding kit.json, relative to the job file
//   export default {
//     'my-ad': {
//       '9x16': (h) => `${h.scene('scenes/x.png')}${h.block({ top: 280, hs: 220, h: 'Two<br>words.', o: '...' })}`,
//       '4x5':  { dark: true, html: (h) => `...` },   // dark: true sets dark type and the dark logo
//     },
//   };
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { launch, args, SIZES, cmd } from './lib/env.mjs';
import { loadKit } from './lib/kit.mjs';
import { css, helpers } from './lib/ad.mjs';

const { pos, opt } = args();
const [jobFile, ...want] = pos;
if (!jobFile) { console.error('usage: node render.mjs <job.mjs> [ad-id ...] [--size 9x16] [--out <folder>]'); process.exit(1); }
const jobPath = path.resolve(jobFile), jobDir = path.dirname(jobPath);
if (!fs.existsSync(jobPath)) throw new Error(`There's no job file at ${jobPath}. Start a job with: ${cmd('new-job.mjs', '<new folder>')}`);
const job = await import(pathToFileURL(jobPath).href + `?t=${Date.now()}`);
const kit = loadKit(path.resolve(jobDir, job.kit || './kit'));
const out = path.resolve(opt.out || path.resolve(jobDir, job.out || './out'));
fs.mkdirSync(out, { recursive: true });

// Runs in the page: boxes, lines, sizes and colours of everything the gate looks at.
function measure() {
  const ad = document.getElementById('ad'), A = ad.getBoundingClientRect();
  const box = (r) => ({ x: Math.round(r.left - A.left), y: Math.round(r.top - A.top), w: Math.round(r.width), h: Math.round(r.height) });
  const rgba = (s) => { const m = String(s).match(/rgba?\(([^)]+)\)/); if (!m) return [0, 0, 0, 1]; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const items = [];
  for (const e of ad.querySelectorAll('[data-field],[data-role=logo],[data-role=pack]')) {
    const it = { k: e.dataset.field || e.dataset.role, ...box(e.getBoundingClientRect()) };
    if (e.dataset.name) it.name = e.dataset.name;
    if (e.dataset.field) {
      const cs = getComputedStyle(e), r = document.createRange(); r.selectNodeContents(e);
      const lines = [];
      for (const q of r.getClientRects()) {
        if (q.width < 1) continue;
        const mid = q.top + q.height / 2, ln = lines.find((l) => Math.abs(l.mid - mid) < q.height / 2);
        if (ln) { ln.left = Math.min(ln.left, q.left); ln.right = Math.max(ln.right, q.right); ln.top = Math.min(ln.top, q.top); ln.bottom = Math.max(ln.bottom, q.bottom); }
        else lines.push({ mid, left: q.left, right: q.right, top: q.top, bottom: q.bottom });
      }
      it.lines = lines.map((l) => ({ x: Math.round(l.left - A.left), y: Math.round(l.top - A.top), w: Math.round(l.right - l.left), h: Math.round(l.bottom - l.top) }));
      it.lw = Math.max(0, ...it.lines.map((l) => l.w));
      it.px = parseFloat(cs.fontSize);
      it.tracking = cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing);
      const sizes = new Set([it.px]); e.querySelectorAll('*').forEach((c) => sizes.add(parseFloat(getComputedStyle(c).fontSize)));
      it.sizes = [...sizes];
      const fill = rgba(cs.color);
      it.colour = fill[3] < 0.05 ? rgba(cs.webkitTextStrokeColor) : fill;
      it.bold = !!e.querySelector('b,strong');
      it.text = e.innerText.replace(/\s+/g, ' ').trim();
      it.clipped = e.scrollWidth > e.clientWidth + 1;
    }
    items.push(it);
  }
  return items;
}

// Runs in the page on a screenshot with the type hidden: how well each line stands out from what's behind it.
async function contrast([b64, fields]) {
  const i = new Image(); i.src = 'data:image/png;base64,' + b64; await i.decode();
  const c = document.createElement('canvas'); c.width = i.width; c.height = i.height;
  const x = c.getContext('2d'); x.drawImage(i, 0, 0);
  const lin = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const L = (r, g, b) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  return fields.map((f) => {
    const t = L(...f.colour), ratios = [], lums = [];
    for (const l of f.lines) {
      const x0 = Math.max(0, l.x), y0 = Math.max(0, l.y), w = Math.min(c.width - x0, l.w), h = Math.min(c.height - y0, l.h);
      if (w < 1 || h < 1) continue;
      const d = x.getImageData(x0, y0, w, h).data;
      for (let k = 0; k < d.length; k += 4 * 3) {
        const p = L(d[k], d[k + 1], d[k + 2]); lums.push(p);
        ratios.push((Math.max(t, p) + 0.05) / (Math.min(t, p) + 0.05));
      }
    }
    if (!ratios.length) return { contrast: null, busy: null };
    ratios.sort((a, b) => a - b);
    const mean = lums.reduce((a, b) => a + b, 0) / lums.length, sd = Math.sqrt(lums.reduce((a, b) => a + (b - mean) ** 2, 0) / lums.length);
    return { contrast: +ratios[Math.floor(ratios.length * 0.1)].toFixed(2), busy: +sd.toFixed(3) };
  });
}

const browser = await launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 2000 }, deviceScaleFactor: 1 }); // taller than any frame: a square viewport once tiled the bottom rows
const layoutFile = path.join(out, 'layout.json');
const layout = fs.existsSync(layoutFile) ? JSON.parse(fs.readFileSync(layoutFile, 'utf8')) : {};
const style = css(kit);
let made = 0;
try {
  for (const [id, sizes] of Object.entries(job.default)) {
    if (want.length && !want.includes(id)) continue;
    for (const [size, def] of Object.entries(sizes)) {
      if (!SIZES[size]) throw new Error(`${id}: unknown size "${size}". Use 9x16, 4x5 or 1x1.`);
      if (opt.size && opt.size !== size) continue;
      const [W, H] = SIZES[size], dark = typeof def === 'object' && !!def.dark;
      const draw = typeof def === 'function' ? def : def.html;
      const body = draw(helpers(kit, size, W, H, dark));
      const name = `${id}_${size}`, htmlFile = path.join(out, name + '.html');
      fs.writeFileSync(htmlFile, `<!doctype html><html><head><meta charset="utf-8"><title>${name}</title><style>${style}</style></head><body><div id="ad" class="${dark ? 'dark' : ''}" data-size="${size}" style="width:${W}px;height:${H}px">${body}</div></body></html>`);
      const problems = [];
      const onFail = (r) => problems.push(`missing file: ${decodeURIComponent(r.url())}`);
      page.on('requestfailed', onFail);
      await page.goto(pathToFileURL(htmlFile).href, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(250);
      page.off('requestfailed', onFail);
      if (problems.length) throw new Error(`${name}: ${problems.join('; ')}. Picture paths in job.mjs are relative to the kit folder (${kit.dir}): put the file there or fix the path.`);
      const items = await page.evaluate(measure);
      await page.screenshot({ path: path.join(out, name + '.png'), clip: { x: 0, y: 0, width: W, height: H } });
      // Contrast: the same frame with the type hidden, then each line's colour against what was behind it.
      await page.evaluate(() => document.querySelectorAll('[data-role=text]').forEach((e) => { e.style.visibility = 'hidden'; }));
      const bare = (await page.screenshot({ clip: { x: 0, y: 0, width: W, height: H } })).toString('base64');
      const fields = items.filter((i) => i.lines && i.k !== 'label');
      const c = await page.evaluate(contrast, [bare, fields]);
      fields.forEach((f, k) => Object.assign(f, c[k]));
      layout[name] = { id, size, w: W, h: H, dark, items };
      made++;
      console.log(`ok  ${name}.png`);
    }
  }
} finally {
  await browser.close();
}
fs.writeFileSync(layoutFile, JSON.stringify(layout, null, 1));
fs.writeFileSync(path.join(out, 'job.json'), JSON.stringify({ job: jobPath, kit: kit.file, rendered: new Date().toISOString() }, null, 1));
if (!made) { console.error('Nothing rendered: check the ad ids and --size.'); process.exit(1); }
console.log(`\n${made} file(s) in ${out}\nNext:  ${cmd('gate.mjs', out)}`);
