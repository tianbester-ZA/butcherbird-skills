// The building blocks an ad is made of. A job file gets these as `h` for each size (render.mjs passes them in),
// so a job file never imports anything. Every helper returns a piece of HTML; an ad is those pieces in order,
// back to front: the picture first, then product fixes, then the type block on top.
//
//   h.W, h.H, h.size        canvas width, height and '9x16' | '4x5' | '1x1'
//   h.url(p)                a kit file as a URL (paths are relative to the kit folder)
//   h.fill(colour, height?, top?)               a flat colour band, full width
//   h.img(src, style)                           any picture, placed with CSS (left, top, width ...)
//   h.scene(src, {top, left, width, fill, fadePx, style})  a generated or photographed scene; when pushed down
//                                               (top > 0) the band above is filled with `fill` and the scene fades in
//   h.pack(src, style, name)                    a real packshot laid flat on the picture (a product layer in the export)
//   h.at(width, left, top, srcWidth = 1536)     maps scene pixels to ad pixels, for a scene drawn at that size and place
//   h.quad(src, [sx, sy, sw, sh], corners, {name, filter, feather})
//                                               warps a rectangle of a real packshot onto four corners in the ad
//                                               (top-left, top-right, bottom-right, bottom-left), so the label is exact
//   h.soften(x, y, w, h, {blur, radius})        blurs what's behind a box: hides garbled small print the label didn't cover
//   h.relight(src, {width, left, top, from, to, opacity})  a lighten-blend copy of the scene from y `from` down, so smoke
//                                               or glow from the scene stays in front of a product laid over it
//   h.shadow(x, y, w, h, alpha)                 a soft contact shadow under a product
//   h.wash(x, y, w, h, colour, alpha)           a soft pool of colour behind a line that sits on a busy ground
//   h.label(text, {x, y, w, size, colour, spacing, font})  live type ON the product (a fixed label line), not ad copy
//   h.block({...})                              the type: logo, headline, offer, optional small line (see below)
import { pathToFileURL } from 'node:url';

const esc = (s) => String(s).replace(/"/g, '&quot;');

export function css(kit) {
  const f = kit.fonts, faces = new Set();
  for (const k of Object.keys(f)) faces.add(`@font-face{font-family:"${f[k].postscript}";src:url("${pathToFileURL(f[k].abs).href}")}`);
  const hl = kit.headline;
  return `${[...faces].join('\n')}
*{margin:0;padding:0;box-sizing:border-box}
body{background:${kit.background}}
#ad{position:relative;overflow:hidden;color:${kit.ink.light};background:${kit.background}}
#ad.dark{color:${kit.ink.dark}}
.blk{position:absolute}
.logo{display:block;margin:0 auto}
.h{font-family:"${f.headline.postscript}";${hl.case === 'upper' ? 'text-transform:uppercase;' : ''}line-height:${hl.lineHeight};letter-spacing:${hl.tracking}}
.h .ol{color:transparent;-webkit-text-stroke:3px ${kit.ink.light}}
.dark .h .ol{-webkit-text-stroke:3px ${kit.ink.dark}}
.o{font-family:"${f.offer.postscript}";line-height:1.3}
.o b{font-family:"${f.offerBold.postscript}";font-weight:normal;font-style:normal}
.s{font-family:"${f.small.postscript}";line-height:1.3}
.bg,.pack{position:absolute}
`;
}

// Solves the perspective transform that takes a unit square to four corners (TL, TR, BR, BL).
export function sq2q([x0, y0, x1, y1, x2, y2, x3, y3]) {
  const dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2, sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3;
  const det = dx1 * dy2 - dx2 * dy1, g = (sx * dy2 - dx2 * sy) / det, h = (dx1 * sy - sx * dy1) / det;
  return [x1 - x0 + g * x1, x3 - x0 + h * x3, x0, y1 - y0 + g * y1, y3 - y0 + h * y3, y0, g, h];
}

export function helpers(kit, size, W, H, dark) {
  const url = (p) => pathToFileURL(kit.abs(p)).href;
  const fill = (colour, height = H, top = 0) => `<div class="bg" style="left:0;top:${top}px;width:${W}px;height:${height}px;background:${colour}"></div>`;
  const img = (src, style = '') => `<img class="bg" src="${url(src)}" style="${style}">`;
  const scene = (src, { top = 0, left = 0, width = W, fill: band, fadePx = 140, style = '' } = {}) =>
    `${top > 0 && band ? fill(band, top + fadePx) : ''}<img class="bg" src="${url(src)}" style="left:${left}px;top:${top}px;width:${width}px;${top > 0 && band ? `-webkit-mask-image:linear-gradient(to bottom,transparent 0,#000 ${fadePx}px);` : ''}${style}">`;
  const pack = (src, style, name = '') => `<img class="pack" data-role="pack" data-name="${esc(name)}" src="${url(src)}" style="${style}">`;
  const at = (width, left, top, srcWidth = 1536) => (pts) => pts.map((v, i) => (i % 2 ? top : left) + v * width / srcWidth);
  const quad = (src, [sx, sy, sw, sh], corners, { name = '', filter = 'none', feather = 2 } = {}) => {
    const [A, B, C, D, E, F, G, Hh] = sq2q(corners);
    const m = [A / sw, D / sw, 0, G / sw, B / sh, E / sh, 0, Hh / sh, 0, 0, 1, 0, C, F, 0, 1];
    const fe = feather;
    return `<div class="pack" data-role="pack" data-name="${esc(name)}" style="left:0;top:0;width:${sw}px;height:${sh}px;transform-origin:0 0;transform:matrix3d(${m.map((v) => +v.toFixed(10)).join(',')});overflow:hidden;-webkit-mask:linear-gradient(90deg,transparent,#000 ${fe}%,#000 ${100 - fe}%,transparent),linear-gradient(transparent,#000 ${fe}%,#000 ${100 - fe}%,transparent);-webkit-mask-composite:source-in"><img src="${url(src)}" style="position:absolute;left:${-sx}px;top:${-sy}px;filter:${filter}"></div>`;
  };
  const soften = (x, y, w, h, { blur = 5, radius = 6 } = {}) => `<div class="bg" data-fix="soften" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;border-radius:${radius}px;backdrop-filter:blur(${blur}px) brightness(.92);-webkit-backdrop-filter:blur(${blur}px) brightness(.92)"></div>`;
  const relight = (src, { width = W, left = 0, top = 0, from, to, opacity = 0.7 }) => `<img class="bg" src="${url(src)}" style="left:${left}px;top:${top}px;width:${width}px;mix-blend-mode:lighten;opacity:${opacity};-webkit-mask-image:linear-gradient(to bottom,transparent ${from}px,#000 ${to}px)">`;
  const shadow = (x, y, w, h, a = 0.55) => `<div class="bg" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:radial-gradient(closest-side,rgba(0,0,0,${a}),transparent)"></div>`;
  const wash = (x, y, w, h, colour = '0,0,0', a = 0.5) => `<div class="bg" style="left:${x}px;top:${y}px;width:${w}px;height:${h}px;background:radial-gradient(closest-side,rgba(${colour},${a}) 55%,rgba(${colour},0))"></div>`;
  const label = (text, { x, y, w = 300, size: px = 14, colour = 'currentColor', spacing = '0', font = kit.fonts.small.postscript } = {}) =>
    `<div class="bg" data-field="label" style="left:${x - w / 2}px;top:${y}px;width:${w}px;text-align:center;white-space:nowrap;font-family:'${font}';font-size:${px}px;line-height:1;letter-spacing:${spacing};color:${colour}">${text}</div>`;

  // The type block: one column, logo on top, then the headline, then the offer, then an optional small line.
  //   x (column centre, default the middle), w (column width, default W - 130), top, align ('center' | 'left')
  //   logo ('light' | 'dark', default follows the ad), logoW (px), g1 (logo to headline gap)
  //   h (headline HTML; <br> breaks lines; <span class="ol"> makes an outline word), hs (px), lh (line height)
  //   o (offer HTML, value in <b>), os (px), g2 (headline to offer gap)
  //   s (small line HTML), ss (px)
  const block = (o) => {
    const x = o.x ?? W / 2, w = o.w ?? W - 130, align = o.align || 'center';
    const logos = kit.logos, which = o.logo || (dark ? 'dark' : 'light'), logo = logos[which] || logos.light || Object.values(logos)[0];
    return `<div class="blk" data-role="text" style="left:${x - w / 2}px;width:${w}px;top:${o.top}px;text-align:${align}">
 ${logo ? `<img class="logo" data-role="logo" src="${url(logo)}" style="width:${o.logoW || 400}px;margin-bottom:${o.g1 ?? 40}px;${align === 'left' ? 'margin-left:0' : ''}">` : ''}
 <div class="h" data-field="headline" style="font-size:${o.hs}px;${o.lh ? `line-height:${o.lh}` : ''}">${o.h}</div>
 ${o.o ? `<div class="o" data-field="offer" style="font-size:${o.os || 40}px;margin-top:${o.g2 ?? 30}px">${o.o}</div>` : ''}
 ${o.s ? `<div class="s" data-field="small" style="font-size:${o.ss || 28}px;margin-top:16px">${o.s}</div>` : ''}
</div>`;
  };
  return { W, H, size, dark, url, fill, img, scene, pack, at, quad, sq2q, soften, relight, shadow, wash, label, block };
}
