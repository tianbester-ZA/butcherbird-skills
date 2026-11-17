// Lays pictures out on one image (contact sheets, compare sheets) by drawing them onto a canvas in Chrome.
// Why a canvas and not a screenshot of a web page: Chrome repeats the top of a page when a screenshot is taller or
// wider than the window it opened with, which broke our sheets twice. A canvas is exactly the size we ask for.
//
//   await board(browser, rows, 'out.jpg', { gap: 14, pad: 16 })
//   rows = [{ label: 'toasty-toes', cells: [{ file: 'a.png' | data: '<base64 png>', w, h, caption: '9:16' }] }]
import fs from 'node:fs';

export async function board(browser, rows, dest, { gap = 14, pad = 16, label = 22, caption = 22, rowGap = 26, quality = 0.86 } = {}) {
  let width = 0, height = pad;
  const placed = rows.map((r) => {
    const top = height + label, rowH = Math.max(...r.cells.map((c) => c.h));
    let x = pad;
    const cells = r.cells.map((c) => {
      const data = c.data || fs.readFileSync(c.file).toString('base64');
      const cell = { ...c, data, x, y: top + rowH - c.h };
      x += c.w + gap;
      return cell;
    });
    width = Math.max(width, x - gap + pad);
    height = top + rowH + caption + rowGap;
    return { label: r.label, y: top - label, cells };
  });
  height += pad - rowGap;
  const page = await browser.newPage();
  try {
    const url = await page.evaluate(async ({ placed, width, height, quality, caption }) => {
      const c = document.createElement('canvas'); c.width = width; c.height = height;
      const x = c.getContext('2d');
      x.fillStyle = '#3a3a3a'; x.fillRect(0, 0, width, height);
      x.textBaseline = 'top';
      for (const r of placed) {
        x.fillStyle = '#ffffff'; x.font = '600 15px -apple-system, Helvetica, sans-serif'; x.fillText(r.label, 16, r.y + 2);
        for (const cell of r.cells) {
          const img = new Image(); img.src = 'data:image/png;base64,' + cell.data; await img.decode();
          x.drawImage(img, cell.x, cell.y, cell.w, cell.h);
          x.fillStyle = '#bbbbbb'; x.font = '14px -apple-system, Helvetica, sans-serif';
          if (cell.caption) x.fillText(cell.caption, cell.x, cell.y + cell.h + 6, cell.w);
        }
      }
      return c.toDataURL('image/jpeg', quality);
    }, { placed, width, height, quality, caption });
    fs.writeFileSync(dest, Buffer.from(url.split(',')[1], 'base64'));
  } finally { await page.close(); }
  return { width, height };
}
