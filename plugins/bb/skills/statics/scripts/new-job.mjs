#!/usr/bin/env node
// Starts a job folder, ready to render. Two kinds:
//
//   node new-job.mjs <new folder>                       a practice job: a copy of the Fynn example with its own kit
//                                                       (fonts, logos, packshot and scene copied in), so it works anywhere
//   node new-job.mjs <new folder> --kit <client kit>    a client job: job.mjs points at the client's kit folder
//
// Writes brief.md (the answers from the ask round), job.mjs (the ads) and, for practice, kit/. Never overwrites:
// if the folder already has a job.mjs it stops. Nothing here needs Chrome, so it works before setup too.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { args, cmd } from './lib/env.mjs';
import { loadKit } from './lib/kit.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FYNN = path.resolve(HERE, '..', 'examples', 'fynn');
const { pos, opt } = args();
const [folder] = pos;
if (!folder) { console.error('usage:\n  node new-job.mjs <new folder>                     practice job with its own kit\n  node new-job.mjs <new folder> --kit <kit folder>  client job using the client\'s kit'); process.exit(1); }
const dir = path.resolve(folder);
if (fs.existsSync(path.join(dir, 'job.mjs'))) throw new Error(`${dir} already has a job.mjs. Pick a new folder, or carry on with that job.`);
if (dir.startsWith(path.resolve(HERE, '..'))) throw new Error('Make the job outside the skill folder: it is replaced on every update.');
fs.mkdirSync(dir, { recursive: true });

const brief = `# Brief

Fill this in from the ask round. Facts come from the client or the live store, never invented.

- **Client and job:** ${opt.kit ? '' : 'Fynn (practice)'}
- **Offer, exactly:** ${opt.kit ? '' : 'buy one pair, get two more free, worth R480'}
- **Lines that must or mustn't appear:**
- **How many ads, which sizes, any carousels:** ${opt.kit ? '' : 'one ad, 9:16, 4:5 and 1:1'}
- **Due:**
- **Brand kit:** ${opt.kit ? path.resolve(opt.kit) : 'kit/ in this folder'}
- **Client photography:**
- **Past ads that passed:**

## Ideas (one per ad, six words each)
-
`;

let kitRel, job;
if (!opt.kit) {
  // Practice: copy the Fynn kit and the fonts it uses, so kit.json points inside this folder.
  const kitOut = path.join(dir, 'kit');
  fs.cpSync(path.join(FYNN, 'kit'), kitOut, { recursive: true });
  const kj = JSON.parse(fs.readFileSync(path.join(kitOut, 'kit.json'), 'utf8'));
  fs.mkdirSync(path.join(kitOut, 'fonts'), { recursive: true });
  for (const f of Object.values(kj.fonts)) {
    const src = path.resolve(FYNN, 'kit', f.file);
    fs.copyFileSync(src, path.join(kitOut, 'fonts', path.basename(src)));
    f.file = `fonts/${path.basename(src)}`;
  }
  kj.name = 'Fynn (practice kit, an invented brand)';
  delete kj.notes;
  fs.writeFileSync(path.join(kitOut, 'kit.json'), JSON.stringify(kj, null, 2) + '\n');
  kitRel = './kit';
  job = fs.readFileSync(path.join(FYNN, 'job.mjs'), 'utf8').replace(/^\/\/ Worked example[^\n]*\n\/\/[^\n]*\n/, `// Practice job: a copy of the Fynn example with its own kit. Change the headline (h) and offer (o), render, and
// let the gate tell you what to adjust (references/workflow.md, "Fitting your own words").
`);
} else {
  const kitDir = path.resolve(opt.kit);
  try { loadKit(kitDir); console.log(`OK  brand kit at ${kitDir}`); }
  catch (e) { console.log(`Check the kit before rendering:\n${e.message}\n`); }
  kitRel = path.relative(dir, kitDir) || '.';
  if (!kitRel.startsWith('.')) kitRel = './' + kitRel;
  job = `// ${opt.name || 'Client job'}. One entry per ad; inside it, one per size. Rules: references/layout.md.
// Picture paths (scenes/..., packs/...) are relative to the kit folder.
//   h.scene('scenes/<file>', { top })       the picture; on smaller sizes move it up with a negative top
//   h.quad('packs/<file>', [0, 0, w, h], toAd([...corners]), { name })   only for a generated scene with a garbled label
//   h.block({...})                           the type: see the parameter table in references/workflow.md

const OFFER = 'Spend R600, receive a beanie, <b>worth R250.</b>'; // replace with the real offer from brief.md

export const kit = '${kitRel.replace(/\\/g, '/')}';
export const out = './out';

export default {
  'first-ad': {
    '9x16': (h) => \`\${h.fill('#222')}
\${h.block({ top: 280, logoW: 380, g1: 44, hs: 220, h: 'Two<br>words.', os: 42, g2: 34, o: OFFER })}\`,
    '4x5': (h) => \`\${h.fill('#222')}
\${h.block({ top: 65, logoW: 320, g1: 36, hs: 190, h: 'Two<br>words.', os: 36, g2: 24, o: OFFER })}\`,
    '1x1': (h) => \`\${h.fill('#222')}
\${h.block({ top: 50, logoW: 230, g1: 28, hs: 112, h: 'Two words.', os: 30, g2: 16, o: OFFER })}\`,
  },
};
`;
}
fs.writeFileSync(path.join(dir, 'job.mjs'), job);
if (!fs.existsSync(path.join(dir, 'brief.md'))) fs.writeFileSync(path.join(dir, 'brief.md'), brief);
console.log(`Made ${opt.kit ? 'a client' : 'a practice'} job in ${dir}:
  brief.md   the answers from the ask round
  job.mjs    the ads (kit: ${kitRel})${opt.kit ? '' : '\n  kit/       a self-contained copy of the Fynn kit, fonts included'}

Next: fill in brief.md, change the words in job.mjs, then render:
  ${cmd('render.mjs', path.join(dir, 'job.mjs'))}`);
