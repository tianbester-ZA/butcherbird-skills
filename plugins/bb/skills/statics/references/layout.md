# Layout rules and the gate

These defaults came from a real Black Friday set that was rejected three times before it passed. They are brand-neutral. A brand kit can change any number under `"rules"` in `kit.json` (see the end of this page). Where the brand and these rules disagree, the brand wins, but write the override down in the kit so the gate knows.

## The method
1. **One idea per ad, in six words, before any layout.** Not a format to fill.
2. **One real scene per ad.** The product photographed in its place, or a scene generated around the real pack with matching light and a contact shadow. Never a cut-out pasted on a texture.
3. **The background belongs to the product.** Its own world, its own ingredients, or true black.
4. **Design, then build, then gate.** Roughs first, build only what's chosen, then the gate and a person's look before anyone else sees it.

## The look
- **Scale:** the product huge (more than half the width) or small in a big room (15 to 30%). Medium looks like a catalogue.
- **Point of view:** eye level, straight on. Top-down only for flat boxes.
- **Empty space is real.** Type goes in a quiet patch of the picture. No dark fades or plates to fake it.
- **Type colour follows the ground:** dark type on light grounds, white on dark.
- **Crop with confidence:** things may run off the edge, but labels stay whole.
- **Vary the layout across a set.** Five ads with the same stack read as one template.

## Type
- **Three elements:** logo, headline (carries the idea), offer line. A fourth small line at most. 20 words in all.
- **Two sizes, far apart.** The headline is big and tight; the offer is a quiet sentence.
- **The headline is big (widest line 756 to 960px) or small (under 378px). Never in between.** In between looks unsure. A small headline lives in a narrow column of a big room.
- **No letter-spacing** on headlines or offers. Only the logo is spaced.
- **One alignment axis:** everything centred, or everything on one left edge.
- **The logo sits top centre** (left-set logos looked badly designed).
- **The offer is a sentence with the value in bold:** "Spend R600, receive a beanie, **worth R250.**" No sale dates: they date the ad and clutter it.
- **The offer must read at a glance.** On a busy or same-tone ground, quiet it with `h.wash`.
- **One playful move**, made from the headline or the product: an outline word (`<span class="ol">`), the product overlapping a letter. Never a gimmick that cuts a letter in half.

## Space
- Text never touches a product: at least 96px between the type and any pack.
- Every readable thing inside the safe area for its size (`references/sizes.md`).

## The gate
`NODE scripts/gate.mjs <out>` reads `layout.json` and checks each ad. Every FAIL names the number, and a "try:" line under it says what to change (a new `hs`, how many px of gap to cut, an `h.wash` line to paste). Exit 0 only when nothing fails. The order to fix things in is in `workflow.md`, "Fitting your own words".

| Check | Default | Why |
|---|---|---|
| Text items, logo included | at most 4 | more reads as clutter |
| Words | at most 20 | a static is read in a second |
| Type sizes | at most 3 | more looks unplanned |
| Smallest text | 24px | smaller doesn't read on a phone |
| Headline widest line | 756 to 960px, or under 378px | big or small, never in between |
| Headline to offer | 4x on 9:16, 3x on 4:5 and 1:1 | sizes far apart; smaller frames carry smaller headlines |
| Offer size | 40 to 44px on 9:16, 32 to 44 on 4:5, 28 to 44 on 1:1 | quiet but readable |
| Offer with a small headline | at least 31px | it carries more weight then |
| Letter-spacing | none on headline, offer or small line | statics are never spaced |
| Safe area | see `sizes.md` | Meta's buttons and captions cover the edges |
| One axis | centres or left edges within 4px | one clean line through the type |
| Logo | top centre, above all type | it looked badly designed anywhere else |
| Type to product | 96px | text must never crowd the product |
| Contrast | offer 4.5:1, headline 3:1 | measured against the worst 10% of pixels behind each line |
| Busy ground behind the offer | warning | check it reads; add a wash if not |
| Offer value in bold | required | the value is what people look for |
| Dates | none | months, "23 to 29", weekdays (Black Friday itself is fine) |
| Words cut off | none | the text box is too narrow |

The gate prints the checks only a person can make at the end of every run: the idea, the headline against the picture, the product's scale, every label word at zoom, and the 216px glance.

## Changing the rules for a brand
In the kit's `kit.json`, under `"rules"`, give only what changes. For example, a brand whose logo always sits bottom left and whose offer runs smaller:

```json
"rules": {
  "logo": "free",
  "offerPx": { "9x16": [34, 40] },
  "headlineBig": [700, 980]
}
```

The full list of names and defaults is at the top of `scripts/lib/kit.mjs`.
