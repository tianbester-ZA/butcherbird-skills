# How a static gets made

Six steps. A person owns the taste in steps 2 and 3. Claude does the rest and checks it. This page is also the training doc: read it once end to end before your first job.

Think of it like a print shop with a very fast typesetter. You bring the idea, the words and the photo. The typesetter sets it perfectly in every size, checks the margins with a ruler, and hands you a file you can still edit. But the typesetter can't tell you whether the idea is funny.

## How you work with it
You talk to Claude: "/bb:statics three Black Friday statics for Fynn". Claude asks what's missing, runs every command, and shows you the results. The commands are written out on this page so you know what's happening and can run one yourself if you want to. You never have to.

## Words you'll see
| Word | What it means |
|---|---|
| job folder | one folder per job, where you work: `brief.md`, `job.mjs`, `out/`. Never inside the skill, which is replaced on every update. |
| `job.mjs` | the file that describes the ads, one entry per ad and per size. `.mjs` just means it's JavaScript; you change numbers and words in it, you don't write code from scratch. |
| helpers, `h` | the building blocks an ad is made from. In `job.mjs`, `h.scene(...)`, `h.block(...)` and so on are helpers; `h` is the toolbox passed to each size. The full list is at the top of `scripts/lib/ad.mjs`. |
| `h.block` | the type: logo, headline, offer, optional small line. Its settings are in the table in step 5. |
| `h.quad` | lays the real packshot over a generated product, bent to the product's four corners, so every label word is right. It uses a browser transform called `matrix3d`: the same maths as Photoshop's perspective warp. |
| `h.soften` | blurs a small box of the picture, to hide garbled print the packshot doesn't cover. |
| `h.at` | converts a position in the scene's own pixels into a position on the ad, so fixes stay put when the scene is moved or resized. |
| `out/` | where renders go: a PNG and an HTML page per ad and size, plus `layout.json` (where everything sits, for the gate). |
| the gate | `gate.mjs`: measures each ad against the layout rules and prints PASS or FAIL with the number that broke a rule and a suggested fix. |
| PostScript name | each font weight's exact name inside the file, like `Geist-Black`. Editors find fonts by it; the family name (`Geist`) isn't enough. |
| headless | a program running with no window: Chrome draws the ads headless; VectorCraft can check files headless. |
| MCP | a plug-in that lets Claude use another app's tools. Higgsfield and VectorCraft both have one. |
| `NODE` | short for the start of each command: `BB_STATICS_DATA="<data folder>" node`. The setup check prints the full line when it says READY. `scripts/` means the skill's scripts folder. |

## The worked example: Fynn
Fynn is an invented sock brand. A practice job is a copy of it with its own kit, so it works in any folder. Start one and run every step:

```
NODE scripts/new-job.mjs ~/Desktop/fynn-practice
NODE scripts/render.mjs ~/Desktop/fynn-practice/job.mjs
NODE scripts/gate.mjs ~/Desktop/fynn-practice/out
NODE scripts/sheet.mjs ~/Desktop/fynn-practice/out
NODE scripts/export.mjs ~/Desktop/fynn-practice/out
NODE scripts/export-check.mjs ~/Desktop/fynn-practice/out --compare
NODE scripts/deliver.mjs ~/Desktop/fynn-practice/out --name Fynn
```

Every script ends by printing the full next command, so you can follow the chain without this page. A client job starts the same way with the client's kit: `NODE scripts/new-job.mjs <folder> --kit <client kit folder>`.

## 1. Brief and brand
**What it does.** Collects the facts every ad rests on, so nobody invents an offer or a price.

**Tools.** The client's notes and past emails; their brand portal (logos, fonts, photography); the ad account, sorted by purchases, for the statics that sold; the live store for prices and stock. Claude writes the answers into `brief.md`.

**What you check.** The exact offer: each spend level, what's free, what it's worth, in the client's words. The brand kit exists and passes `setup.py --kit` (`brand-kit.md`). Two or three past ads that passed, to set the bar. Whether the client has real photos of the product in a place.

**Fynn.** Offer: buy one pair, get two more free, worth R480. Kit: Geist Black headlines in capitals, an italic serif sentence for the offer, two logo colours and a flat packshot of the box.

## 2. Idea and lines (the person decides)
**What it does.** Picks one idea per ad and the words that carry it. This is where ads are won or lost.

**Tools.** Your judgement and the brief. `/bb:books` is the team's library skill: ask it what 17 advertising books say about a line or an offer ("/bb:books does a discount need a reason"). Claude renders two or three quick roughs (a plain background and the type) so you choose by eye.

**What you check.**
- The idea in six words. If you can't say it, there isn't one yet.
- The headline makes sense with its picture. A clever line on an unrelated photo reads as random.
- Plain words beat clever ones. A headline that needs explaining doesn't work.
- The offer is a plain sentence with the value in bold: "Buy one pair, get two more free, **worth R480.**" No sale dates.

**Fynn.** Idea: "warm feet by the fire". Headline: "Toasty toes." Picture: the box on a cabin hearth at night.

## 3. Make the picture (the person picks)
**What it does.** Finds or makes the scene the product sits in.

**Tools.** The client's own photography first, from their portal. When the scene doesn't exist, Higgsfield, an image generator Claude drives through its MCP, with the real packshots as references (`higgsfield.md`). Claude saves the chosen picture into the kit's `scenes/` folder.

**What you check.** The product is front-on with its labels uncovered. The top 45% of the frame is quiet, so the type has somewhere to go. The background belongs to the product (a gift box on a dinner table, not on another product's packaging). Generations cost credits: Claude says roughly how many before starting.

**Fynn.** `kit/scenes/hearth.svg` stands in for a generation. It's 1536 x 2752, the size Higgsfield returns for 9:16. Like a real one, its label is garbled: "FYMN" and "MERNIO HIKNG SOKCS".

## 4. Fix the labels (only when the picture is generated)
**What it does.** Makes every word on the product right.

**When to skip it.** If the picture is the client's real photo and its labels are correct, skip this step: there's nothing to fix. Zoom in and read them once to be sure. It's needed for generated scenes, because image models garble small packaging text every time.

**Tools.** `h.quad` lays the real packshot over the generated pack. `h.soften` blurs leftover garbled print. `h.label` sets a line as live type. `measure.mjs grid` finds the corners; `measure.mjs crop` zooms in to read the result. Details and pitfalls: `labels.md`.

**Reading the corners.** Every new scene needs its own corners; never reuse them from another picture.
1. `NODE scripts/measure.mjs grid <scene> <out.png> x y w h` draws a labelled grid over the area around the product (cyan numbers across the top are x, pink down the side are y, every 100px).
2. Open the picture. Read the four corners of the label face in this order: top-left, top-right, bottom-right, bottom-left. Each is an x and a y.
3. Put the eight numbers in `job.mjs` as the corners and render.
4. Crop in and check the edges line up. If an edge is off, nudge that number by 5 to 10 and render again.

**What you check.** Zoom into every pack in every size and read every word. Reflections too.

**Fynn.** From the grid: top-left 440,1620; top-right 1080,1610; bottom-right 1090,2210; bottom-left 440,2222. The side of the box has garbled print the face doesn't cover, so it's softened.

```
NODE scripts/measure.mjs grid kit/scenes/hearth.svg ~/Desktop/grid.png 350 1450 900 900
NODE scripts/measure.mjs crop out/toasty-toes_9x16.png ~/Desktop/label.png 290 1120 520 460
```

## 5. Build in code
**What it does.** Turns the picture and the words into finished ads in every size.

**How it works.** Each ad is a small web page: the scene at the back, then product fixes, then a type block on top. Google Chrome draws the page to a PNG, the same way it draws any website. Because it's a page, changing a word or a size is an edit and a re-render, never a redraw.

**Tools.** `render.mjs` draws, `gate.mjs` checks. Each size is its own layout, never a crop (`sizes.md`). Rules: `layout.md`.

**What you check.** Every FAIL fixed, every WARN read. The gate prints a "try:" line under each failure with the number to change.

### The text block settings (`h.block`)
| Setting | What it changes |
|---|---|
| `top` | how far down the block starts, in px from the top of the ad (the logo's top edge) |
| `logoW` | logo width in px |
| `g1` | gap from the logo to the headline |
| `h` | the headline words. `<br>` breaks a line; `<span class="ol">word</span>` makes an outline word |
| `hs` | headline size in px. Its width and height both grow with it |
| `lh` | headline line height (0.88 means lines sit tight; default from the kit) |
| `o` | the offer sentence, value in `<b>...</b>` |
| `os` | offer size in px |
| `g2` | gap from the headline to the offer |
| `s`, `ss` | an optional small line and its size |
| `align` | `center` (default) or `left` |
| `logo` | `light` or `dark` logo; by default it follows the ad (`dark: true` means dark type and the dark logo) |
| `x`, `w` | the column's centre and width; default the middle, 950px wide |

### Fitting your own words
New words never fit first time. Do it in this order, one render each:
1. **Width first.** The headline's widest line grows in step with `hs`. New `hs` = old `hs` × target width ÷ the width the gate printed. Aim for about 860px (big) or under 378px (small). The gate prints this sum for you.
2. **Then the gap to the product.** A bigger headline is taller, so it may now crowd the product. On 9:16, win the space from the type, not the picture: cut `g1` and `g2`, or a smaller `top` (it can't go above y 280). On 4:5 and 1:1 you can also move the scene down (a bigger `top` in `h.scene`). The gate says how many px to gain.
3. **Then legibility.** A contrast FAIL means the offer is on a busy or same-tone patch. The gate prints an `h.wash(...)` line to paste just before `h.block`: a soft pool of shade behind the offer.
4. **Then the other sizes**, the same way.

**Fynn.** The first 4:5 failed twice: the headline was 605px wide (between big and small) and the type sat 78px from the box. 152 × 860 ÷ 605 ≈ 216; 196 was enough to reach the big range, and moving the scene down 118px cleared the box.

## 6. Review, edit, export, deliver
**What it does.** Gets the person's notes, then hands over files a designer can keep working on.

**Tools and how.**
- **Review.** `sheet.mjs` makes a contact sheet: each ad's sizes side by side, plus a copy 216px wide to check it reads at a glance. Open it and send it with the round. For notes per ad from several people, ask Claude for a review board: a private claude.ai page with each ad and a note box, which Claude reads back. The contact sheet alone is fine for one reviewer.
- **Notes go back to step 2**, not straight into the code. "The headline doesn't fit the picture" is an idea problem.
- **Export.** `export.mjs` writes an editable SVG per ad: named layers (scene, each product, logo, type) and live text in the brand fonts.
- **Check the export.** `export-check.mjs --compare` checks every font is named properly, every word is there, and the file drawn by Chrome and by VectorCraft both match the PNG. Open `out/edit/_compare.jpg`: each row should look identical three times. A different weight or width in the type means a font was swapped.
- **Edit by hand** if needed, in VectorCraft, Illustrator or Figma (`vectorcraft.md`).
- **Deliver.** `deliver.mjs <out> --name "<Client job>"` builds the hand-over folder beside `out/`: `01 Stories and Reels 9x16`, `02 Feed 4x5`, `03 Square 1x1`, `Carousel` (ads whose id starts with `car-`), and `Editable (SVG)` with the fonts and a README. Files are numbered in job order: `01 Fynn Toasty Toes 9x16.png`.

**What you check.** The person has said yes to the set. The compare sheet looks identical across each row. Open the delivery folder and click through it. It goes to Drive or the client portal only after the person's yes.

**Fynn.** All three sizes pass the gate; the export check shows zero font warnings in VectorCraft and its drawing within about 1.7 of 255 of the PNG on average.

## Where things go
```
<client>-<job>/          where you're working, never inside the skill
  brief.md               the answers from the ask round
  job.mjs                the ads, per size
  out/                   PNGs, HTML, layout.json, _sheet.jpg
  out/edit/              SVGs, fonts/, _compare.jpg
  delivery/              the numbered hand-over folder
<client folder>/kit/     the brand kit (brand-kit.md)
```
