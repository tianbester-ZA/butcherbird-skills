# The brand kit

A brand kit is one folder per client with everything an ad needs from the brand. It lives with the client's work (for example in the client's own folder or project), **never in this repo**: this repo is public, and client fonts and logos are licensed and private.

## What's in it
```
kit/
  kit.json        the settings below
  fonts/          the brand's font files (.otf or .ttf)
  logos/          the logo, one file per colour, ideally SVG
  packs/          flat packshots: each product straight on, the real label, transparent background, as large as you can get
  scenes/         the client's own photography and any generated scenes you've kept
  rules.md        optional: the brand's own layout notes in words, for people
```

## kit.json
The Fynn example (`examples/fynn/kit/kit.json`) is a complete one.

```json
{
  "name": "Fynn",
  "fonts": {
    "headline":  { "file": "fonts/Geist-Black.ttf",            "postscript": "Geist-Black" },
    "offer":     { "file": "fonts/PlayfairDisplay-Italic.otf", "postscript": "PlayfairDisplay-Italic" },
    "offerBold": { "file": "fonts/Geist-Bold.ttf",             "postscript": "Geist-Bold" }
  },
  "logos": { "light": "logos/fynn-light.svg", "dark": "logos/fynn-dark.svg" },
  "ink": { "light": "#FFFFFF", "dark": "#14110F" },
  "background": "#16100D",
  "headline": { "case": "upper", "lineHeight": 0.88, "tracking": "-0.01em" },
  "rules": {}
}
```

| Field | What it means |
|---|---|
| `fonts.headline` | the headline font |
| `fonts.offer` | the offer sentence |
| `fonts.offerBold` | the bold value inside the offer (defaults to the headline font) |
| `fonts.small` | an optional small line (defaults to the offer font) |
| `postscript` | the font's PostScript name. If you leave it out, it's read from the file. If you give one that doesn't match the file, the render stops and tells you the right one. |
| `logos.light` / `logos.dark` | the logo for dark grounds and for light grounds. An ad marked `dark: true` uses the dark one |
| `ink` | type colour on dark grounds (`light`) and on light grounds (`dark`) |
| `background` | the colour behind everything, and the editable file's background layer |
| `headline` | capitals or not, line height, tracking (keep it 0 or slightly tight; statics are never spaced) |
| `rules` | overrides for the layout gate (`layout.md`) |

**Why PostScript names matter.** A font has a family name ("Geist") and a PostScript name for each weight ("Geist-Black"). Editors find the exact weight by the PostScript name. Name it by family and VectorCraft and Illustrator look for "Geist Regular" and swap. To see a font's name: `node scripts/lib/fontname.mjs <font file>`.

## Start a job with a kit
```
NODE scripts/new-job.mjs <job folder> --kit <kit folder>
```
The job's `job.mjs` then points at the kit, and picture paths in it (`scenes/...`, `packs/...`) are relative to the kit folder.

## Check a kit
```
python3 <skill>/scripts/setup.py --data <plugin data folder> --kit <kit folder>
```
It checks every font file exists and matches its PostScript name, every logo exists, and whether the fonts are installed for editing (`--install-fonts` installs them on a yes).

## Getting the pieces
- **Fonts and logos:** the client's brand portal or guidelines. Check the font licence covers us.
- **Packshots:** the client's portal or store. Get the largest file there is; a small packshot goes soft when it's laid over a big product.
- **Photography:** the client's campaign shoots first. They make better scenes than any generation.
