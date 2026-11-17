// setup.py runs this to prove Chrome can draw: opens a tiny page headless and screenshots it.
import { launch } from './env.mjs';

const b = await launch();
try {
  const p = await b.newPage({ viewport: { width: 40, height: 40 } });
  await p.setContent('<body style="margin:0;background:#c00"></body>');
  const png = await p.screenshot();
  if (png.length < 50) throw new Error('empty screenshot');
  console.log('drew a test page');
} finally {
  await b.close();
}
