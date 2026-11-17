---
name: statics
description: Makes static image ads and carousels for Meta, from the brief to finished 9:16, 4:5 and 1:1 files and editable layered SVGs, on this Mac with Google Chrome. A person sets the idea, the lines and the picture; Claude builds each ad as a page in code from the client's brand kit, lays the real packshot over any generated product so every label word is right, re-lays out every size, checks each against a layout gate, exports files that open with live text and named layers in VectorCraft, Illustrator or Figma, and checks those too. Use it whenever someone asks for static ads, statics, image ads, carousels, Black Friday or sale statics, a static set or round, resizing ads to 4:5 or 1:1, fixing garbled text on a generated pack, editable or layered files, or opening ads in Illustrator or VectorCraft. Video belongs to /bb:edit, scripts to /bb:script.
argument-hint: "[client and offer, or a job folder]"
---

# /bb:statics

## Goal
A set of static ads a stranger understands in a second and wants to act on: one idea per ad, a headline that fits its picture, the offer as a plain sentence, the real product with every label word right. Each ad in 9:16, 4:5 and 1:1, laid out for that size, plus an editable SVG a designer can open and change.

## Who does what
A person owns the taste: the idea, the lines and which picture (steps 2 and 3). Claude does the rest and checks it: reads the brief, builds, fixes labels, re-lays out sizes, runs the gate, exports and checks the files. Claude shows two or three rough options before building, and never ships a judgement it only checked by machine. The gate measures layout; it can't tell whether an ad is any good.

## Before anything: check this Mac
```
python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py" --data "${CLAUDE_PLUGIN_DATA}"
```
One status line per tool with the exact fix, then READY or NOT READY. On NOT READY give the person the fix lines and stop. OPTIONAL lines don't block. VectorCraft is optional: if it's missing, say it's the free, open-source Illustrator we use for editing, about 310 MB, and on their yes add `--install-vectorcraft`. Once there's a kit, add `--kit <kit folder>`; on a yes, `--install-fonts` puts the brand fonts where the editors can find them.

## Then: ask what we're making
Read what's there first (the client's notes, past winners, the brand kit, the offer) and say it back, so they confirm rather than retype. Then ask, in one short round, only what's missing:

1. What's the offer, exactly? Spend levels, what's free, what it's worth. Any line or claim that must or mustn't appear?
2. How many ads, which sizes and placements, and any carousels? By when?
3. Where are the brand kit and the client's own photography? Which past ads passed?

Write the answers to `brief.md` in the job folder. If nobody can answer (a headless run), say what you would have asked and take the sensible reading.

## Why
Our first rounds for a client failed on judgement, not code: a tidy template filled thirteen times, headlines that didn't fit their pictures, garbled labels, offers lost on busy grounds, sale dates on statics. Each is now a rule or a check (`lessons.md`). Building in code means any word, size or position is an edit and a re-render, every size is laid out properly, and the editable file matches the PNG.

## What good looks like
- One idea per ad, sayable in six words, with one playful move made from the headline or the product. No two ads in a set share a layout.
- The headline makes sense with its picture. The picture belongs to the product.
- Logo top centre, type on one axis, in real empty space, at least 96px from any product.
- The offer is one plain sentence with its value in bold, readable at a glance. No sale dates.
- The real product, front-on, huge or small in a big room, every label word right at zoom.
- Every size laid out again, not cropped. The editable SVG opens with no font warnings and matches the PNG.

## Commands
The person asks; Claude runs these and shows the results. They're listed in the references so people understand them. Reference files write these short. Shell state doesn't carry between commands, so always use the full form, and give any agent the full form too. Every script prints the full next command when it finishes.

- `NODE` means `BB_STATICS_DATA="${CLAUDE_PLUGIN_DATA}/statics" node`. Run every `.mjs` script with it.
- `scripts/...` means `${CLAUDE_SKILL_DIR}/scripts/...`. `references/...` means `${CLAUDE_SKILL_DIR}/references/...`. `examples/...` means `${CLAUDE_SKILL_DIR}/examples/...`.

| Script | Does |
|---|---|
| `NODE scripts/new-job.mjs <folder> [--kit <client kit>]` | starts a job: `brief.md`, `job.mjs`, and a practice kit when no kit is given |
| `NODE scripts/render.mjs <job.mjs> [id] [--size 9x16]` | draws each ad: PNG, HTML and `layout.json` |
| `NODE scripts/gate.mjs <out>` | checks every ad against the layout rules |
| `NODE scripts/sheet.mjs <out>` | contact sheet, sizes side by side, plus a 216px glance |
| `NODE scripts/measure.mjs grid\|crop <image> <out.png> ...` | coordinates on a scene; zoom to read labels |
| `NODE scripts/export.mjs <out>` | editable SVGs with named layers and live text |
| `NODE scripts/export-check.mjs <out> --compare` | fonts, words, Chrome and VectorCraft renders against the PNG |
| `NODE scripts/deliver.mjs <out> --name "<Client job>"` | the numbered hand-over folder, per size, plus the editable files |

## The six steps
Start every job with `new-job.mjs`: a client job with `--kit <the client's kit folder>`, or a practice job (a self-contained copy of the Fynn example) without it. The job folder sits where the person is working, never inside the skill; the brand kit stays in the client's own folder (`references/brand-kit.md`). Words a newcomer won't know (helpers, `h.quad`, PostScript name, MCP, headless) are explained at the top of `references/workflow.md`; point people there.

1. **Brief and brand.** The exact offer, the brand kit (checked with `setup.py --kit`), past winners from the ad account, the client's own photography. Into `brief.md`. Facts come from the client or the live store, never invented.
2. **Idea and lines** (the person decides). One idea per ad; headline fits the picture; offer a plain sentence. `/bb:books` for an argument about a line. Show two or three rough renders before building.
3. **Make the picture** (the person picks). The client's real photos first. When a scene doesn't exist, generate it in Higgsfield with the real packshots as references, product front-on, labels clear, the top 45% empty for type (`references/higgsfield.md`). Generations cost credits: say roughly how many first.
4. **Fix the labels** (only for generated scenes; skip it when the picture is the client's real photo with correct labels). Image models garble small print on every pack. Read the four corners off `measure.mjs grid`, fresh for every scene, and lay the real packshot over with `h.quad`; or patch only the wrong strip, or set the line as live type; blur what's left with `h.soften`. Zoom in and read every word (`references/labels.md`).
5. **Build in code.** Each ad is a page; each size its own layout (`references/sizes.md`). Render, gate, fix every FAIL using its "try:" line, read every WARN (`references/layout.md`). New words: width first (hs scales with width), then the gap, then contrast (`workflow.md`, "Fitting your own words").
6. **Review, edit, export, deliver.** Contact sheet to the person (or a review board page if several people give notes); notes go back to step 2. Then export, export-check (open `_compare.jpg`), edit in VectorCraft if needed (`references/vectorcraft.md`), and `deliver.mjs` for the numbered folder. Drive only on the person's yes.

The whole flow, with a worked example, is `references/workflow.md`. It doubles as the training doc.

## Hard limits
- Nothing goes to a client, gets published, spends ad money or uploads to a client's Drive without the person's yes. Higgsfield credits: say the count first.
- Never claim a label is right without a zoom crop of it. Never present a gate PASS as "the ad is good".
- Offers, prices and claims come from the brief or the live store, never invented. No sale dates on a static.
- A client's kit, photos, fonts and lessons stay in that client's folder; nothing crosses clients.

## References (load by step)
- `references/workflow.md`: the glossary, the six steps, the text block settings, fitting new words, and a worked example.
- `references/layout.md`: the rules, the gate and how a kit overrides them.
- `references/sizes.md`: 9:16, 4:5, 1:1 and carousels, and how to re-lay out.
- `references/labels.md`: fixing garbled packaging text, and the pitfalls.
- `references/higgsfield.md`: generating a scene around the real product.
- `references/vectorcraft.md`: the editor, its CLI and MCP, and editing a file.
- `references/brand-kit.md`: what a client kit holds and where it lives.

## Lessons
`lessons.md` holds dated lessons from real rounds. Read it at step 2. A client's own lessons go in that client's folder; a lesson for everyone goes in through the repo (`CONTRIBUTING.md`).
