// Loads a brand kit (kit.json plus its files) and the layout rules, with the kit's overrides merged in.
// A kit lives with the client's work, never in this repo. See references/brand-kit.md.
import fs from 'node:fs';
import path from 'node:path';
import { postscriptName } from './fontname.mjs';
import { cmd } from './env.mjs';

// Brand-neutral defaults. Every number came from a real job that a senior signed off (references/layout.md says why).
// A kit overrides any of them under "rules" in kit.json.
export const RULES = {
  safe: { // where readable things may sit, in px from the edges
    '9x16': { top: 280, bottom: 670, side: 65 }, // text between y 280 and y 1250 on Stories and Reels
    '4x5': { top: 65, bottom: 65, side: 65 },
    '1x1': { top: 50, bottom: 50, side: 50 },
  },
  headlineBig: [756, 960], // widest headline line: big (in this range) ...
  headlineSmall: 378, //        ... or small (under this). Never in between.
  headlineToOffer: { '9x16': 4, '4x5': 3, '1x1': 3 }, // headline px at least this many times the offer px (big headlines)
  offerPx: { '9x16': [40, 44], '4x5': [32, 44], '1x1': [28, 44] },
  offerPxSmallHeadline: 31, // offer floor when the headline is small
  minTextPx: 24, // nothing readable smaller
  maxTextItems: 4,
  maxWords: 20,
  maxSizes: 3,
  productGap: 96, // px between the type and any product
  axisTolerance: 4, // px
  logo: 'top-centre', // or "free" to switch the check off
  offerValueBold: true, // the offer is a sentence with the value in bold
  contrast: { offer: 4.5, headline: 3, small: 4.5 },
  noDates: true, // no sale dates on a static
};

function merge(a, b) {
  if (b === undefined) return a;
  if (Array.isArray(b) || typeof b !== 'object' || b === null) return b;
  const o = { ...a };
  for (const k of Object.keys(b)) o[k] = merge(a ? a[k] : undefined, b[k]);
  return o;
}

export function loadKit(kitPath) {
  if (!fs.existsSync(kitPath)) throw new Error(`There's no brand kit at ${kitPath}. In job.mjs, point "export const kit" at the client's kit folder (the one holding kit.json), or make a practice job with its own kit: ${cmd('new-job.mjs', '<new folder>')}. See references/brand-kit.md.`);
  const dir = fs.statSync(kitPath).isDirectory() ? kitPath : path.dirname(kitPath);
  const file = fs.statSync(kitPath).isDirectory() ? path.join(kitPath, 'kit.json') : kitPath;
  if (!fs.existsSync(file)) throw new Error(`No kit.json at ${file}. See references/brand-kit.md.`);
  const kit = JSON.parse(fs.readFileSync(file, 'utf8'));
  kit.dir = dir;
  kit.file = file;
  kit.abs = (p) => path.resolve(dir, p);
  const problems = [];
  kit.fonts = kit.fonts || {};
  for (const [role, f] of Object.entries(kit.fonts)) {
    const abs = kit.abs(f.file);
    if (!fs.existsSync(abs)) { problems.push(`font "${role}": no file at ${abs}. Put the font file there, or fix "file" in kit.json (paths are relative to the kit folder, ${dir}).`); continue; }
    const real = postscriptName(abs);
    if (!f.postscript) f.postscript = real;
    else if (real && real !== f.postscript) problems.push(`font "${role}": kit.json says "${f.postscript}" but the file's PostScript name is "${real}". Use "${real}".`);
    f.abs = abs;
  }
  for (const need of ['headline', 'offer']) if (!kit.fonts[need]) problems.push(`kit.json has no "${need}" font`);
  if (!kit.fonts.offerBold) kit.fonts.offerBold = kit.fonts.headline;
  if (!kit.fonts.small) kit.fonts.small = kit.fonts.offer;
  kit.logos = kit.logos || {};
  for (const [k, p] of Object.entries(kit.logos)) if (!fs.existsSync(kit.abs(p))) problems.push(`logo "${k}": no file at ${kit.abs(p)}. Put the logo there, or fix "logos" in kit.json (relative to the kit folder).`);
  kit.ink = { light: '#ffffff', dark: '#111111', ...(kit.ink || {}) };
  kit.headline = { case: 'upper', lineHeight: 0.9, tracking: '-0.01em', ...(kit.headline || {}) };
  kit.background = kit.background || '#000000';
  kit.rules = merge(RULES, kit.rules || {});
  if (problems.length) throw new Error('Brand kit problems:\n  ' + problems.join('\n  '));
  return kit;
}
