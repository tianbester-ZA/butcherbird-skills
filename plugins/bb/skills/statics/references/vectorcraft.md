# Editing the files in VectorCraft

VectorCraft is a free, open-source alternative to Illustrator, made by the ArtCraft team (github.com/storytold/vectorcraft, MIT or Apache licence). It's still early (alpha). Everything on this page was tested with VectorCraft 0.24.1; a newer version may move things. Our SVGs also open in Illustrator and Figma; VectorCraft is the one everyone can have for free, and the one Claude can drive.

## What's in an exported file
Open any `out/edit/<id>_<size>.svg` and the layers panel shows, back to front:

| Layer | What it is | What you can do |
|---|---|---|
| `background` | flat ground colour | change the colour |
| `scene` | the picture, with its washes and blur fixes, flattened | replace it with a new picture |
| `product-<name>` | each real product, on its own transparent layer | move, scale, swap |
| `effect-<blend>` | smoke or glow in front of a product, with its blend mode | move with the product, or delete |
| `label-type` | live words fixed onto a label | correct a word |
| `logo` | the logo as vector shapes | recolour, resize |
| `type` | headline, offer and small line as live text | change words, sizes, positions |

**Moving a product shows what's underneath.** In a generated scene, the model's own garbled copy of the product is baked into the scene layer. Move the product far and you'll see it. Small nudges are fine; for a big move, ask Claude to rebuild the ad.

## Editing by hand
1. **Install the fonts first.** Open the `fonts` folder beside the SVGs, double-click each font and choose Install (or run `setup.py --kit <kit> --install-fonts`). Do it before opening the file, or VectorCraft swaps them.
2. **Open the SVG.** File, Open, pick `<id>_<size>.svg`. It opens at 1080px wide.
3. **The layers panel** lists the layers in the table above. Click the eye to hide one, the lock to protect the scene while you work on the type.
4. **Change words.** Double-click a line of the headline or offer and type. If the value was bold, select it again and set the bold font (the offer's bold font is in the kit, e.g. `Geist-Bold`).
5. **Move or resize a product.** Click its `product-...` layer, drag it, or hold Shift and drag a corner to scale. Small moves only (see above).
6. **Export a PNG at 1x.** File, Export, PNG, scale 1, so it comes out 1080px wide like the original. Save the SVG too, so the next person can keep editing.

If something looks off, compare with the PNG in `out/`: that is what the client approved.

## Fonts
Install the brand's fonts on your Mac first, or VectorCraft (and Illustrator) will swap them for a fallback. The setup check does it on a yes: `setup.py --kit <kit> --install-fonts` copies them into `~/Library/Fonts`. The export names each font by its PostScript name (e.g. `Geist-Black`), which is how the editors find the exact weight. A family name alone ("Geist") opens without a warning but quietly picks the wrong weight.

## Installing it
The setup check finds it, and on the person's yes installs it: `setup.py --install-vectorcraft`. That downloads the latest Mac release from GitHub (about 310 MB), checks each file against the release's published SHA256 checksums, puts `VectorCraft.app` in `~/Applications`, and unpacks the command-line tool into the plugin's data folder. By hand: download `vectorcraft-<version>-macos-universal.dmg` and `vectorcraft-cli-<version>-macos-universal.zip` from the releases page, and check them against `SHA256SUMS.txt`.

## The command-line tool (used by the export check)
`vectorcraft-cli run --in file.svg --export out.png --scale 1` opens a file without the app, exports a PNG and prints what it found as JSON. A font it can't find shows up as a warning ("fonts that aren't available were written in the fallback font ..."). `export-check.mjs` runs this on every file: zero font warnings is a pass, and its picture is compared with the PNG.

## Or: letting Claude edit in VectorCraft (MCP)
VectorCraft's command-line tool is also an MCP server, which lets Claude open files, read the layers and make edits. Add it once (the setup check prints the exact line with your path):

```
claude mcp add vectorcraft -- "<path to vectorcraft-cli>" mcp
```

Two ways to work:
- **Live, in the open app, so you watch the edit happen:** start the app with `open -a VectorCraft --args --control 7979`. The MCP server connects to it at 127.0.0.1:7979.
- **Headless, no window:** `vectorcraft-cli mcp --headless`. It also falls back to this when the app isn't open.

Tools Claude uses: `open_file`; `doc_inspect` (the layer tree with ids and names); `command_run` (e.g. `select.set {ids:[n]}`, then `text.setText {text}`); `transform {ids, dx, dy, scale, rotate}`; `export {path, options:{scale}}`; `ui_screenshot`; `answer_dialog {action: confirm|cancel}`.

One catch: `text.setText` drops mixed styling, so a bold value in the offer goes plain. Follow it with `text.setRangeStyle` on the bold words.

## In Illustrator or Figma
Open the SVG directly. Keep the `fonts/` folder beside the files and the fonts installed. Illustrator wasn't tested by us yet; if a layer or font comes in wrong, note it in `lessons.md` through the repo.
