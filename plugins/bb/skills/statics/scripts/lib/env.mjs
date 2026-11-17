// Finds this skill's tools on this Mac: the Chrome driver (playwright-core), Google Chrome and the VectorCraft CLI.
// They live in Claude Code's data folder for the plugin, because the plugin folder is replaced on every update.
// Order: $BB_STATICS_DATA, then $CLAUDE_PLUGIN_DATA/statics, then the newest record setup.py left in
// ~/.claude/plugins/data/bb-*/statics, then a fallback in ~/.cache.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { pathToFileURL, fileURLToPath } from 'node:url';

// Every script imports this file, so problems print as one plain line, not a stack trace. BB_DEBUG=1 shows the trace.
const plain = (e) => { console.error(process.env.BB_DEBUG ? (e && e.stack) || e : `Stopped: ${(e && e.message) || e}`); process.exit(1); };
process.on('uncaughtException', plain);
process.on('unhandledRejection', plain);

export const RECORD = 'setup.json';
export const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
export const SIZES = { '9x16': [1080, 1920], '4x5': [1080, 1350], '1x1': [1080, 1080] };

export function dataDir() {
  if (process.env.BB_STATICS_DATA) return process.env.BB_STATICS_DATA;
  if (process.env.CLAUDE_PLUGIN_DATA) return path.join(process.env.CLAUDE_PLUGIN_DATA, 'statics');
  const base = path.join(process.env.CLAUDE_CONFIG_DIR || path.join(os.homedir(), '.claude'), 'plugins', 'data');
  let best = null, when = 0;
  try {
    for (const d of fs.readdirSync(base)) {
      if (!d.startsWith('bb-')) continue;
      const rec = path.join(base, d, 'statics', RECORD);
      if (fs.existsSync(rec) && fs.statSync(rec).mtimeMs > when) { best = path.dirname(rec); when = fs.statSync(rec).mtimeMs; }
    }
  } catch { /* no plugin data yet */ }
  return best || path.join(os.homedir(), '.cache', 'butcherbird-bb', 'statics');
}

export function record() {
  try { return JSON.parse(fs.readFileSync(path.join(dataDir(), RECORD), 'utf8')); } catch { return {}; }
}

const SETUP_HINT = 'Run the setup check first: python3 <skill>/scripts/setup.py --data <plugin data folder> (the /bb:statics skill shows the exact line).';

export async function chromium() {
  const entry = path.join(dataDir(), 'node_modules', 'playwright-core', 'index.mjs');
  if (!fs.existsSync(entry)) throw new Error(`The Chrome driver isn't installed in ${dataDir()}. ${SETUP_HINT}`);
  return (await import(pathToFileURL(entry).href)).chromium;
}

export async function launch() {
  if (!fs.existsSync(CHROME)) throw new Error(`Google Chrome isn't at ${CHROME}. Install it from https://www.google.com/chrome, or set CHROME_PATH.`);
  const c = await chromium();
  return c.launch({ executablePath: CHROME, headless: true, args: ['--force-color-profile=srgb', '--hide-scrollbars', '--font-render-hinting=none', '--allow-file-access-from-files'] });
}

// The VectorCraft command-line tool, if this Mac has one. Returns a path or null.
export function vectorcraftCli() {
  const tries = [process.env.VECTORCRAFT_CLI, record().vectorcraft_cli];
  for (const p of tries) if (p && fs.existsSync(p)) return p;
  try { return execFileSync('/usr/bin/which', ['vectorcraft-cli'], { encoding: 'utf8' }).trim() || null; } catch { return null; }
}

// Small argument reader: positional words plus --flag value / --flag.
export function args(argv = process.argv.slice(2), booleans = []) {
  const pos = [], opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) { const k = a.slice(2); if (booleans.includes(k)) opt[k] = true; else opt[k] = argv[++i]; } else pos.push(a);
  }
  return { pos, opt };
}

// The full command to run another script, ready to paste: the data folder, node and the script's full path.
export const SCRIPTS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const q = (s) => (/^[\w./:=@-]+$/.test(s) ? s : `"${String(s).replace(/(["\\$`])/g, '\\$1')}"`);
export function cmd(script, ...rest) {
  return `BB_STATICS_DATA=${q(dataDir())} node ${q(path.join(SCRIPTS, script))} ${rest.map(q).join(' ')}`.trim();
}

// A folder the person named must exist; say so plainly if it doesn't.
export function needDir(dir, what) {
  if (!fs.existsSync(dir)) throw new Error(`There's no folder at ${dir}. ${what}`);
}

export function sizeOf(file) {
  const m = path.basename(file).match(/_(9x16|4x5|1x1)\.[a-z]+$/);
  return m ? m[1] : null;
}
