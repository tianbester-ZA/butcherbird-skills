#!/usr/bin/env node
// Turns rendered ads into editable SVG files that open in VectorCraft, Illustrator or Figma.
//
//   node export.mjs <out folder> [name-filter] [--to <folder>]
//
// For every <id>_<size>.html in the out folder it writes <id>_<size>.svg into <out>/edit (or --to), plus a fonts/
// folder with the fonts the ads use. Each SVG has named layers, back to front:
//   background      a flat rectangle in the ad's ground colour
//   scene           the picture behind everything, with its washes and blur fixes, flattened into one image
//   product-<name>  each real product on its own transparent layer, so it can be moved, scaled or swapped
//   effect-<blend>  smoke or glow drawn over a product, kept with its blend mode
//   overlay         anything else drawn above a product (flattened)
//   label-type      live type fixed onto a product label, if any
//   logo            the logo as vector paths (an SVG logo) or an image
//   type            the headline, offer and small line as live text, one line per <tspan>
//
// Fonts are named by their PostScript names (from the kit), because VectorCraft and Illustrator match on those.
// Moving a product layer shows whatever the scene has underneath: in a generated scene that is the model's own,
// garbled copy of the product. Say so to whoever edits the file.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { launch, args, SIZES, sizeOf, needDir, cmd } from './lib/env.mjs';

function extractText() {
  const ad = document.getElementById('ad'), adR = ad.getBoundingClientRect();
  const num = (v) => Math.round(v * 100) / 100;
  const xml = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const hex = (rgb) => { const m = String(rgb).match(/rgba?\(([^)]+)\)/); if (!m) return { c: rgb, a: 1 }; const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return { c: '#' + p.slice(0, 3).map((v) => Math.round(v).toString(16).padStart(2, '0')).join(''), a: p.length > 3 ? p[3] : 1 }; };
  const family = (cs) => cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, '');
  const ascCache = {};
  const ascent = (fam, size) => {
    const k = fam + '/' + size; if (ascCache[k] != null) return ascCache[k];
    const d = document.createElement('div'); d.style.cssText = `position:absolute;left:0;top:0;visibility:hidden;white-space:nowrap;font-family:"${fam}";font-size:${size}px;line-height:normal;letter-spacing:0`;
    d.innerHTML = 'H<span style="display:inline-block;width:0;height:0"></span>'; ad.appendChild(d);
    const r = document.createRange(); r.selectNodeContents(d.firstChild);
    const a = d.lastChild.getBoundingClientRect().bottom - r.getClientRects()[0].top; d.remove(); return ascCache[k] = a;
  };
  function textSvg(el, id) {
    const chars = [], walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), r = document.createRange();
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const cs = getComputedStyle(n.parentElement), up = cs.textTransform === 'uppercase', fill = hex(cs.color), sw = parseFloat(cs.webkitTextStrokeWidth) || 0, outline = fill.a === 0 && sw > 0;
      const st = { fam: family(cs), size: parseFloat(cs.fontSize), ls: cs.letterSpacing === 'normal' ? 0 : parseFloat(cs.letterSpacing), fill: outline ? 'none' : fill.c, fa: outline ? 1 : fill.a, stroke: outline ? hex(cs.webkitTextStrokeColor).c : '', sw: outline ? sw : 0 };
      for (let i = 0; i < n.data.length; i++) { r.setStart(n, i); r.setEnd(n, i + 1); const rc = r.getClientRects()[0]; if (!rc || (rc.width === 0 && /\s/.test(n.data[i]))) continue; chars.push({ ch: up ? n.data[i].toUpperCase() : n.data[i], rc, st }); }
    }
    const lines = [];
    for (const c of chars) { const mid = c.rc.top + c.rc.height / 2; let ln = lines[lines.length - 1]; if (!ln || mid > ln.bottom) { ln = { chars: [], bottom: c.rc.bottom }; lines.push(ln); } ln.chars.push(c); ln.bottom = Math.max(ln.bottom, c.rc.bottom); }
    const align = getComputedStyle(el).textAlign, anchor = align === 'center' ? 'middle' : align === 'right' || align === 'end' ? 'end' : 'start';
    const attrs = (s) => `font-family="${s.fam}" font-size="${num(s.size)}" fill="${s.fill}"${s.fa < 1 ? ` fill-opacity="${num(s.fa)}"` : ''}${s.sw ? ` stroke="${s.stroke}" stroke-width="${num(s.sw)}"` : ''}${s.ls ? ` letter-spacing="${num(s.ls)}"` : ''}`;
    const body = lines.map((ln) => {
      while (ln.chars.length && /\s/.test(ln.chars[0].ch)) ln.chars.shift();
      while (ln.chars.length && /\s/.test(ln.chars[ln.chars.length - 1].ch)) ln.chars.pop();
      if (!ln.chars.length) return '';
      const runs = []; for (const c of ln.chars) { const last = runs[runs.length - 1], k = JSON.stringify(c.st); if (last && last.k === k) last.t += c.ch; else runs.push({ k, t: c.ch, ...c.st }); }
      const first = ln.chars[0], left = first.rc.left - adR.left, right = ln.chars[ln.chars.length - 1].rc.right - adR.left;
      // Chrome adds letter-spacing after the last glyph too; take it off so centred lines match
      const x = anchor === 'middle' ? (left + right - (first.st.ls || 0)) / 2 : anchor === 'end' ? right : left;
      const y = first.rc.top - adR.top + ascent(first.st.fam, first.st.size);
      return `<tspan x="${num(x)}" y="${num(y)}" text-anchor="${anchor}">${runs.map((s) => `<tspan ${attrs(s)}>${xml(s.t)}</tspan>`).join('')}</tspan>`;
    }).join('');
    return `<text id="${id}" xml:space="preserve">${body}</text>`;
  }
  const out = { type: [], labels: [], logo: null, fonts: [], background: getComputedStyle(ad).backgroundColor };
  const blk = ad.querySelector('[data-role=text]'), logo = blk && blk.querySelector('[data-role=logo]');
  if (logo) { const b = logo.getBoundingClientRect(); out.logo = { src: logo.src, x: b.left - adR.left, y: b.top - adR.top, w: b.width, h: b.height }; }
  if (blk) for (const el of blk.querySelectorAll('[data-field]')) out.type.push(textSvg(el, el.dataset.field));
  ad.querySelectorAll('[data-field=label]').forEach((el, i) => out.labels.push(textSvg(el, `label-${i + 1}`)));
  for (const sheet of document.styleSheets) for (const rule of sheet.cssRules) {
    if (rule.constructor.name !== 'CSSFontFaceRule') continue;
    const m = rule.style.getPropertyValue('src').match(/url\(["']?([^"')]+)["']?\)/);
    if (m) out.fonts.push({ family: rule.style.getPropertyValue('font-family').replace(/["']/g, '').trim(), src: m[1] });
  }
  return out;
}

function planLayers() {
  const kids = [...document.getElementById('ad').children], groups = []; let cur = null;
  const isPack = (e) => e.dataset.role === 'pack', isText = (e) => e.dataset.role === 'text' || e.dataset.field;
  const blend = (e) => { const b = getComputedStyle(e).mixBlendMode; return b !== 'normal' ? b : ''; };
  const backdrop = (e) => (getComputedStyle(e).backdropFilter || 'none') !== 'none';
  kids.forEach((e, i) => {
    if (isText(e)) { cur = null; return; }
    if (backdrop(e) && groups.length) { groups[0].idx.push(i); return; } // a blur fix belongs to the picture it fixes
    if (isPack(e)) {
      const src = (e.tagName === 'IMG' ? e.src : (e.querySelector('img') || {}).src) || '';
      groups.push({ kind: 'product', name: e.dataset.name || decodeURIComponent(src.split('/').pop()).replace(/\.[a-z]+$/i, ''), idx: [i] }); cur = null; return;
    }
    if (blend(e)) { groups.push({ kind: 'effect', blend: blend(e), idx: [i] }); cur = null; return; }
    if (!cur) { cur = { kind: groups.length ? 'overlay' : 'scene', idx: [] }; groups.push(cur); }
    cur.idx.push(i);
  });
  return groups;
}

// Crops a transparent screenshot to what's drawn, and keeps it as JPEG when it has no see-through pixels.
async function trim(b64) {
  const i = new Image(); i.src = 'data:image/png;base64,' + b64; await i.decode();
  const c = document.createElement('canvas'); c.width = i.width; c.height = i.height; const x = c.getContext('2d'); x.drawImage(i, 0, 0);
  const d = x.getImageData(0, 0, c.width, c.height).data; let x0 = c.width, y0 = c.height, x1 = -1, y1 = -1;
  for (let y = 0; y < c.height; y++) for (let xx = 0; xx < c.width; xx++) if (d[(y * c.width + xx) * 4 + 3] > 2) { if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (y < y0) y0 = y; if (y > y1) y1 = y; }
  if (x1 < 0) return null;
  const o = document.createElement('canvas'); o.width = x1 - x0 + 1; o.height = y1 - y0 + 1; o.getContext('2d').drawImage(c, -x0, -y0);
  const dd = o.getContext('2d').getImageData(0, 0, o.width, o.height).data; let opaque = true;
  for (let k = 3; k < dd.length; k += 4) if (dd[k] < 255) { opaque = false; break; }
  return { x: x0, y: y0, w: o.width, h: o.height, href: opaque ? o.toDataURL('image/jpeg', 0.92) : o.toDataURL('image/png') };
}

const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'item';

export async function exportAll(outDir, filter, to) {
  const dir = path.resolve(outDir), edit = path.resolve(to || path.join(dir, 'edit'));
  needDir(dir, 'Give the out folder render.mjs wrote to.');
  const files = fs.readdirSync(dir).filter((f) => sizeOf(f) && f.endsWith('.html') && (!filter || f.includes(filter))).sort();
  if (!files.length) throw new Error(`No <id>_<size>.html files in ${dir}. Run render.mjs first.`);
  fs.mkdirSync(path.join(edit, 'fonts'), { recursive: true });
  const browser = await launch();
  const written = [];
  try {
    for (const f of files) {
      const H = SIZES[sizeOf(f)][1];
      const page = await browser.newPage({ viewport: { width: 1080, height: 2000 }, deviceScaleFactor: 1 });
      await page.goto(pathToFileURL(path.join(dir, f)).href, { waitUntil: 'load' });
      await page.evaluate(() => document.fonts.ready); await page.waitForTimeout(250);
      const info = await page.evaluate(extractText);
      const fontCss = [];
      for (const ft of info.fonts) {
        const src = fileURLToPath(ft.src), base = path.basename(src);
        fs.copyFileSync(src, path.join(edit, 'fonts', base));
        fontCss.push(`@font-face{font-family:"${ft.family}";src:url("fonts/${base}")}`);
      }
      const plan = await page.evaluate(planLayers);
      await page.addStyleTag({ content: 'html,body,#ad{background:transparent!important}' });
      const layers = [];
      for (const g of plan) {
        await page.evaluate((idx) => { [...document.getElementById('ad').children].forEach((e, i) => { e.style.visibility = idx.includes(i) ? '' : 'hidden'; e.style.mixBlendMode = idx.includes(i) ? 'normal' : ''; }); }, g.idx);
        await page.waitForTimeout(60);
        const png = (await page.screenshot({ type: 'png', omitBackground: true, clip: { x: 0, y: 0, width: 1080, height: H } })).toString('base64');
        const t = await page.evaluate(trim, png);
        if (t) layers.push({ ...g, ...t });
      }
      await page.close();
      const used = {}; const uniq = (b) => { used[b] = (used[b] || 0) + 1; return used[b] > 1 ? `${b}-${used[b]}` : b; };
      const layerSvg = layers.map((l) => {
        const id = uniq(l.kind === 'product' ? `product-${slug(l.name)}` : l.kind === 'effect' ? `effect-${l.blend}` : l.kind);
        return `<g id="${id}"${l.blend ? ` style="mix-blend-mode:${l.blend}"` : ''}><image x="${l.x}" y="${l.y}" width="${l.w}" height="${l.h}" preserveAspectRatio="none" href="${l.href}"/></g>`;
      }).join('\n');
      let logo = '';
      if (info.logo) {
        const src = fileURLToPath(info.logo.src);
        if (src.toLowerCase().endsWith('.svg')) {
          const text = fs.readFileSync(src, 'utf8'), vbm = text.match(/viewBox="([^"]+)"/);
          const vb = vbm ? vbm[1].split(/[ ,]+/).map(Number) : [0, 0, parseFloat(text.match(/width="([\d.]+)/)[1]), parseFloat(text.match(/height="([\d.]+)/)[1])];
          const inner = text.replace(/^[\s\S]*?<svg[^>]*>/, '').replace(/<\/svg>\s*$/, '').replace(/<!--[\s\S]*?-->/g, '').replace(/\s*\n\s*/g, '');
          const k = info.logo.w / vb[2];
          logo = `<g id="logo" transform="translate(${(info.logo.x - vb[0] * k).toFixed(2)} ${(info.logo.y - vb[1] * k).toFixed(2)}) scale(${k.toFixed(5)})">${inner}</g>`;
        } else {
          const mime = src.toLowerCase().endsWith('.png') ? 'image/png' : 'image/jpeg';
          logo = `<g id="logo"><image x="${info.logo.x}" y="${info.logo.y}" width="${info.logo.w}" height="${info.logo.h}" href="data:${mime};base64,${fs.readFileSync(src).toString('base64')}"/></g>`;
        }
      }
      const bg = info.background && !/rgba\(0, 0, 0, 0\)/.test(info.background) ? info.background : '#000';
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="${H}" viewBox="0 0 1080 ${H}" overflow="hidden">
<defs><style>${[...new Set(fontCss)].join('')}</style></defs>
<rect id="background" x="0" y="0" width="1080" height="${H}" fill="${bg}"/>
${layerSvg}
${info.labels.length ? `<g id="label-type">${info.labels.join('\n')}</g>` : ''}
${logo}
<g id="type">${info.type.join('\n')}</g>
</svg>\n`;
      const dest = path.join(edit, f.replace(/\.html$/, '.svg'));
      fs.writeFileSync(dest, svg);
      written.push(dest);
      console.log(`${(svg.length / 1e6).toFixed(2)} MB  ${path.basename(dest)}   layers: ${[...svg.matchAll(/<g id="([^"]+)"/g)].map((m) => m[1]).join(', ')}`);
    }
  } finally { await browser.close(); }
  console.log(`\n${written.length} editable file(s) in ${edit}\nNext:  ${cmd('export-check.mjs', dir, '--compare')}`);
  return written;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { pos, opt } = args();
  if (!pos[0]) { console.error('usage: node export.mjs <out folder> [name-filter] [--to <folder>]'); process.exit(1); }
  exportAll(pos[0], pos[1], opt.to).catch((e) => { console.error(e.message); process.exit(1); });
}
