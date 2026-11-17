// Reads a font file's PostScript name (name table, id 6), e.g. "Geist-Black".
// Why it matters: an editable SVG must name each font by its PostScript name. Name it by family ("Geist") and
// VectorCraft and Illustrator go looking for "Geist Regular" and swap in the wrong weight.
import fs from 'node:fs';

export function postscriptName(file) {
  const b = fs.readFileSync(file);
  const tag = b.toString('latin1', 0, 4);
  if (!['\x00\x01\x00\x00', 'OTTO', 'true'].includes(tag)) return null; // .ttc collections and web fonts aren't read here
  const n = b.readUInt16BE(4);
  for (let i = 0; i < n; i++) {
    const rec = 12 + i * 16;
    if (b.toString('latin1', rec, rec + 4) !== 'name') continue;
    const at = b.readUInt32BE(rec + 8), count = b.readUInt16BE(at + 2), strings = at + b.readUInt16BE(at + 4);
    let mac = null;
    for (let j = 0; j < count; j++) {
      const r = at + 6 + j * 12, platform = b.readUInt16BE(r), id = b.readUInt16BE(r + 6), len = b.readUInt16BE(r + 8), off = strings + b.readUInt16BE(r + 10);
      if (id !== 6) continue;
      if (platform === 3 || platform === 0) { // UTF-16BE
        let s = ''; for (let k = 0; k < len; k += 2) s += String.fromCharCode(b.readUInt16BE(off + k));
        return s;
      }
      if (platform === 1) mac = b.toString('latin1', off, off + len);
    }
    return mac;
  }
  return null;
}

if (process.argv[1] && process.argv[1].endsWith('fontname.mjs')) {
  for (const f of process.argv.slice(2)) console.log(`${postscriptName(f) || '(not readable)'}  ${f}`);
}
