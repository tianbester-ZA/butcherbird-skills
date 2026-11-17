#!/usr/bin/env node
// Checks every rendered ad against the layout rules (references/layout.md), using the layout.json render.mjs wrote.
//
//   node gate.mjs <out folder> [ad-id ...] [--kit <kit folder or kit.json>]
//
// The kit's "rules" override the defaults (scripts/lib/kit.mjs). Without --kit it uses the kit the job named.
// Prints FAIL and WARN lines per ad with the number that broke the rule, then the checks only a person can make.
// Exit 0 only when nothing fails. The gate measures; it doesn't judge whether the idea is any good.
import fs from 'node:fs';
import path from 'node:path';
import { args, needDir, cmd } from './lib/env.mjs';
import { loadKit, RULES } from './lib/kit.mjs';

const { pos, opt } = args();
const [outDir, ...want] = pos;
if (!outDir) { console.error('usage: node gate.mjs <out folder> [ad-id ...] [--kit <kit>]'); process.exit(1); }
const out = path.resolve(outDir);
needDir(out, 'Give the out folder render.mjs wrote to (it prints it at the end).');
if (!fs.existsSync(path.join(out, 'layout.json'))) throw new Error(`No layout.json in ${out}. Render first: ${cmd('render.mjs', '<job.mjs>')}`);
const layout = JSON.parse(fs.readFileSync(path.join(out, 'layout.json'), 'utf8'));
let rules = RULES;
const kitPath = opt.kit || (fs.existsSync(path.join(out, 'job.json')) && JSON.parse(fs.readFileSync(path.join(out, 'job.json'), 'utf8')).kit);
if (kitPath) rules = loadKit(kitPath).rules;

const MONTHS = /\b(january|february|march|april|june|july|august|september|october|november|december|jan|feb|apr|jun|jul|aug|sept?|oct|nov|dec)\b\.?/i;
const DATES = /\b\d{1,2}\s*(\/|\.|–|-|to|till|until)\s*\d{1,2}\b|\b\d{1,2}(st|nd|rd|th)\b|\b(mon|tues|wednes|thurs|fri|satur|sun)day\b/i;
const SALE_DAYS = /\b(black friday|cyber monday)\b/gi;

function gap(a, b) { // empty space between two boxes; 0 when they touch or overlap
  const dx = Math.max(0, Math.max(a.x, b.x) - Math.min(a.x + a.w, b.x + b.w));
  const dy = Math.max(0, Math.max(a.y, b.y) - Math.min(a.y + a.h, b.y + b.h));
  return Math.hypot(dx, dy);
}

let fails = 0, warns = 0, checked = 0;
for (const [name, ad] of Object.entries(layout)) {
  if (want.length && !want.includes(ad.id) && !want.includes(name)) continue;
  checked++;
  const R = [], fail = (m) => R.push(['FAIL', m]), warn = (m) => R.push(['WARN', m]), fix = (m) => R.push(['FIX', m]);
  const { size, w: W, h: H } = ad;
  const texts = ad.items.filter((i) => ['headline', 'offer', 'small'].includes(i.k) || (i.lines && i.k !== 'label'));
  const logo = ad.items.find((i) => i.k === 'logo'), packs = ad.items.filter((i) => i.k === 'pack');
  const hl = texts.find((i) => i.k === 'headline'), offer = texts.find((i) => i.k === 'offer');
  const tol = rules.axisTolerance;

  // How much type
  const words = texts.map((t) => t.text).join(' ').split(/\s+/).filter(Boolean).length;
  const count = texts.length + (logo ? 1 : 0);
  if (count > rules.maxTextItems) fail(`${count} text items (logo included); at most ${rules.maxTextItems}`);
  if (words > rules.maxWords) fail(`${words} words; at most ${rules.maxWords}`);
  const sizes = new Set(texts.flatMap((t) => t.sizes.map(Math.round)));
  if (sizes.size > rules.maxSizes) fail(`${sizes.size} type sizes (${[...sizes].join(', ')} px); at most ${rules.maxSizes}`);
  for (const t of texts) {
    if (t.px < rules.minTextPx) fail(`${t.k} is ${t.px}px; nothing readable under ${rules.minTextPx}px`);
    if (t.tracking > 0.01) fail(`${t.k} is letter-spaced (${t.tracking}px); only the logo is ever spaced`);
    if (t.clipped) fail(`${t.k} is cut off: the words don't fit their box`);
  }

  // Headline and offer sizes
  let small = false;
  if (!hl) fail('no headline (data-field="headline")');
  else {
    const [lo, hi] = rules.headlineBig;
    small = hl.lw < rules.headlineSmall;
    if (!small && (hl.lw < lo || hl.lw > hi)) {
      fail(`headline's widest line is ${hl.lw}px: make it ${lo} to ${hi}px (big) or under ${rules.headlineSmall}px (small), never in between`);
      const big = Math.round(hl.px * ((lo + hi) / 2) / hl.lw), sm = Math.floor(hl.px * (rules.headlineSmall * 0.9) / hl.lw);
      fix(`width grows with hs, so try hs: ${big} (big, widest line about ${Math.round((lo + hi) / 2)}px) or hs: ${sm} (small). A bigger headline is taller too: re-run the gate for the gap.`);
    }
  }
  if (!offer) warn('no offer line (data-field="offer")');
  else {
    const [lo, hi] = rules.offerPx[size];
    if (small) { if (offer.px < rules.offerPxSmallHeadline) fail(`offer is ${offer.px}px; with a small headline it stays at least ${rules.offerPxSmallHeadline}px`); }
    else {
      if (offer.px < lo || offer.px > hi) { fail(`offer is ${offer.px}px; on ${size} it's ${lo} to ${hi}px`); fix(`set os between ${lo} and ${hi}`); }
      const k = rules.headlineToOffer[size];
      if (hl && hl.px < k * offer.px) { fail(`headline ${hl.px}px is ${(hl.px / offer.px).toFixed(1)}x the offer; on ${size} it's at least ${k}x`); fix(`make hs at least ${Math.ceil(k * offer.px)}, or os at most ${Math.floor(hl.px / k)}`); }
    }
    if (rules.offerValueBold && !offer.bold) fail('the offer has no bold value: write it as a sentence with the value in <b>, e.g. "..., <b>worth R480.</b>"');
  }

  // Safe zones
  const s = rules.safe[size];
  const inside = (b) => b.x >= s.side - 0.5 && b.x + b.w <= W - s.side + 0.5 && b.y >= s.top - 0.5 && b.y + b.h <= H - s.bottom + 0.5;
  for (const t of texts) for (const l of t.lines) if (!inside(l)) {
    fail(`${t.k} line at y ${l.y} to ${l.y + l.h}, x ${l.x} to ${l.x + l.w} is outside the safe area (y ${s.top} to ${H - s.bottom}, ${s.side}px sides)`);
    if (l.y < s.top) fix(`move the type down ${s.top - l.y}px (raise top)`);
    else if (l.y + l.h > H - s.bottom) fix(`it runs ${l.y + l.h - (H - s.bottom)}px too low: cut g1 or g2, or a smaller hs`);
    else fix(`the line is too wide: break it with <br>, or a smaller size`);
    break;
  }
  if (logo && !inside(logo)) fail(`logo at y ${logo.y} to ${logo.y + logo.h} is outside the safe area (y ${s.top} to ${H - s.bottom}, ${s.side}px sides)`);

  // One alignment axis, logo top centre
  const lines = texts.flatMap((t) => t.lines);
  if (lines.length) {
    const centres = lines.map((l) => l.x + l.w / 2).concat(logo ? [logo.x + logo.w / 2] : []);
    const lefts = lines.map((l) => l.x).concat(logo ? [logo.x] : []);
    const spread = (v) => Math.max(...v) - Math.min(...v);
    if (spread(centres) > 2 * tol && spread(lefts) > 2 * tol) fail(`no single axis: line centres spread ${Math.round(spread(centres))}px, left edges ${Math.round(spread(lefts))}px (allowed ${2 * tol})`);
  }
  if (rules.logo === 'top-centre') {
    if (!logo) fail('no logo (data-role="logo")');
    else {
      const cx = logo.x + logo.w / 2;
      if (Math.abs(cx - W / 2) > tol) fail(`logo centre is at x ${Math.round(cx)}; it sits top centre (x ${W / 2})`);
      if (lines.some((l) => l.y < logo.y)) fail('type sits above the logo; the logo goes on top');
    }
  }

  // Space between type and product
  if (!packs.length) warn('no product marked as data-role="pack", so the gap to the product was not checked');
  const typeBoxes = lines.concat(logo ? [logo] : []);
  for (const p of packs) {
    const g = Math.min(...typeBoxes.map((b) => gap(b, p)));
    if (g < rules.productGap) {
      fail(`type is ${Math.round(g)}px from the product${p.name ? ` "${p.name}"` : ''}; keep ${rules.productGap}px clear`);
      const need = Math.ceil(rules.productGap - g), typeTop = Math.min(...typeBoxes.map((b) => b.y)), typeBottom = Math.max(...typeBoxes.map((b) => b.y + b.h));
      if (p.y >= typeBottom - 1) {
        const room = Math.max(0, typeTop - s.top), n = hl ? hl.lines.length : 1, perPx = hl ? (hl.h / n) / hl.px : 0.9;
        const opts = [`cut g1 and/or g2 by ${need}px in total`];
        if (room > 0) opts.push(`move the type up with a smaller top (up to ${Math.min(room, need)}px before it leaves the safe area)`);
        if (hl) opts.push(`a smaller headline, about hs: ${Math.floor(hl.px - need / (n * perPx))}`);
        if (size !== '9x16') opts.push(`move the scene down ${need}px (a bigger h.scene top; corners follow through h.at)`);
        fix(`gain ${need}px: ${opts.join('; or ')}`);
      } else fix(`the product sits beside or above the type: move one of them ${need}px apart`);
    }
    if (p.x < -2 || p.y < -2 || p.x + p.w > W + 2 || p.y + p.h > H + 2) warn(`product${p.name ? ` "${p.name}"` : ''} runs off the edge: fine for a confident crop, but its label must stay whole`);
  }

  // Legibility
  for (const t of texts) {
    const need = rules.contrast[t.k];
    if (need && t.contrast != null && t.contrast < need) {
      fail(`${t.k} contrast ${t.contrast}:1 against what's behind it; needs ${need}:1`);
      const x0 = Math.min(...t.lines.map((l) => l.x)), y0 = Math.min(...t.lines.map((l) => l.y)), x1 = Math.max(...t.lines.map((l) => l.x + l.w)), y1 = Math.max(...t.lines.map((l) => l.y + l.h));
      const tone = ad.dark ? '255,255,255' : '0,0,0';
      fix(`quiet the ground behind it: put h.wash(${x0 - 80}, ${y0 - 50}, ${x1 - x0 + 160}, ${y1 - y0 + 100}, '${tone}', .55) just before h.block, and raise the last number until it passes. Or flip the type colour (dark: true).`);
    }
    if (t.k === 'offer' && t.busy > 0.12) warn(`the ground behind the offer is busy (${t.busy}); check it reads at a glance, or quiet it with h.wash`);
  }

  // No sale dates
  if (rules.noDates) {
    const all = texts.map((t) => t.text).join(' / ').replace(SALE_DAYS, '');
    const m = all.match(MONTHS) || all.match(DATES);
    if (m) fail(`looks like a date ("${m[0]}"); statics carry the offer and its value, never the sale dates`);
  }

  const bad = R.filter((r) => r[0] === 'FAIL').length;
  fails += bad; warns += R.filter((r) => r[0] === 'WARN').length;
  console.log(`${bad ? 'FAIL' : 'PASS'}  ${name}${hl ? `   headline ${hl.px}px, widest line ${hl.lw}px${offer ? `; offer ${offer.px}px, contrast ${offer.contrast}:1` : ''}` : ''}`);
  for (const [k, m] of R) console.log(k === 'FIX' ? `            try: ${m}` : `      ${k}  ${m}`);
}
if (!checked) { console.error('No ads matched.'); process.exit(1); }
console.log(`
${checked} ad(s): ${fails ? `${fails} failure(s)` : 'all pass the measured rules'}${warns ? `, ${warns} warning(s) to read` : ''}.
Still for a person (the gate can't see these):
  - The idea in six words, and one playful move. Not the same layout as another ad in the set.
  - The headline makes sense with its picture; the picture belongs to the product.
  - The product is huge or small in a big room, grounded, front-on.
  - Every word on every label read at zoom (node measure.mjs crop ...). Garbled text anywhere, reflections too.
  - At thumbnail size (about 216px wide) the headline and the offer value still read.
${fails ? 'Change the numbers in job.mjs, render again, and re-run this.' : `Next:  ${cmd('sheet.mjs', out)}`}`);
process.exit(fails ? 1 : 0);
