# Fixing the labels

Image models garble small packaging text. Every time, on every pack: wrong letters, invented words, a brand name one letter off. Big logos sometimes survive; ingredient lines and flavour names never do. So a generated product is never trusted until every word has been read at zoom.

Skip all of this when the picture is the client's real photo and its labels are correct: read them once at zoom and move on. Every new generated scene needs its own fix and its own corners.

There are four fixes. Use the smallest one that works.

## 1. Lay the real packshot over (`h.quad`)
The usual fix. Take the client's flat packshot (straight on, the real label) and bend it onto the four corners of the generated pack. The model's light, shadow and surroundings stay; the label becomes exact.

1. Find the corners. `NODE scripts/measure.mjs grid <scene> <out.png> x y w h` draws a labelled grid over the area (x across the top in cyan, y down the side in pink, every 100px). Read off top-left, top-right, bottom-right, bottom-left, in the scene's own pixels. If an edge doesn't line up after rendering, nudge that number by 5 to 10.
2. In the job: `h.quad('packs/box.png', [sx, sy, sw, sh], toAd(corners), { name: 'box' })`, where `[sx, sy, sw, sh]` is the part of the packshot to use (often the whole front face) and `toAd = h.at(width, left, top)` maps scene pixels to ad pixels.
3. Match the tone with `filter` (`'brightness(.93) sepia(.08)'` warmed the Fynn box to firelight).
4. Zoom and read: `NODE scripts/measure.mjs crop <ad.png> <out.png> x y w h`.

How it works, in one line: a CSS `matrix3d` transform maps the flat rectangle onto any four-sided shape, the same maths as Photoshop's perspective warp. It's done in one step, so the label stays sharp.

## 2. Patch only the wrong strip
When the whole label laid over looks pasted on (the real label is flatter or cleaner than the scene's lighting), use only the strip that's wrong: give `h.quad` a smaller source rectangle (just the flavour line) and its four corners. The rest of the generated label, with its natural light, stays.

## 3. Set the line as live type (`h.label`)
For one short line on a plain band (say "MERINO WOOL" across a lid): soften the garbled line, then set the real words on top with `h.label(text, { x, y, size, colour, spacing })`. It exports as live text in its own `label-type` layer.

## 4. Blur what's left (`h.soften`)
Garbled print the packshot doesn't cover (the side of a box, a reflection, a tag): `h.soften(x, y, w, h)` blurs it into texture. A blurred line reads as "small print"; a garbled one reads as fake. At full size the blur shows as a soft bar, so keep each box small and put it only on parts nobody reads.

## Pitfalls we've hit
- **A full real-label overlay can look pasted on.** The tone or sharpness doesn't match the scene. Patch just the strip, or adjust `filter`.
- **A patch can import a band the scene doesn't have.** The packshot's strip carries a colour band or border the generated pack doesn't. Crop the source rectangle tighter.
- **Ribbons, bows and props must not cover labels.** Ask for them on the lid or beside the product. If one crosses a label, regenerate.
- **Reflections and shadows carry garbled text too.** Soften them.
- **Moving a product in the editable file shows the garbled pack underneath**, baked into the scene. Tell whoever edits the file.
- **A tilted pack is hard to fix.** If the label is turned away or curved, regenerate it upright and front-on; it's cheaper than fighting the warp.
- **Never trust a placed label.** Read every word, in every size, every round.
- **A blur over a product drops out of the editable file.** `h.soften` merges into the scene layer on export, so a blur laid over a product layer is lost in the SVG. Fix that label in the packshot file itself (or patch the strip), not with a blur on top.
