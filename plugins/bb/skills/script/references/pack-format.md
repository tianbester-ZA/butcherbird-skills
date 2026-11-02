# Pack format

Contents: what the page is · pack.md, exactly · building the HTML · reasoning.md · what never goes on the page

## What the page is

The shoot pack is the format: an Ink cover with the running order, a numbers and how-to-film page, one page per ad, then extra shots. The team already shoots from it, so the skill changes what goes in it, never the page. No small print, no page numbers, no footnotes, no citations.

You write `pack.md`; `scripts/build_pack.py` turns it into `pack.html` (and `pack.pdf`) in the Butcherbird look, and `scripts/check_pack.py` reads the same file. If the markdown drifts from the shape below, the builder drops things silently, so keep to it.

## pack.md, exactly

```markdown
---
cover: Black Friday / with the star
for: For <names> and the team
line: Five videos, in shooting order. Each one ends on one deal.
settled: R900; made once, never again
---

# <Client> <moment> shoot: <n> videos with <who>

For <names> and the team. <n> videos, in shooting order. <How it's shot, who films.>

Every video has four parts. **The message** is what the viewer should get. **The hook** is the first two seconds. **The body** is what to do and say. **The close** is the deal, said exactly. Say it your way; only the numbers and the close need to be word for word.

Running order:
1. <Title> (<the deal in a few words>)
2. ...

## The numbers (say these exactly)

- **25%**: any two. <What counts, what doesn't.>
- **R900**: free shipping. <Terms.>
- Nothing stacks. <Any other plain note.>

## How to film

- <Phone, height, framing for 4:5.>
- Start on the hook. No intro.
- <Product visible in every shot.>
- <Takes, and no dates out loud.>

---

## 1. <Title>

*About 15 seconds. <Where, who's in it.>*

**The message:** <One sentence: what the viewer should get.>

**Hook**
<!-- kind: odd-picture -->
- Do: <the first frame>
- Say: <Nothing, or the first line. On screen: "<text>">
- Other hooks to film:
  - <do, then the line>
  - <do, then the line>

**Body**
1. Do: <action>. Say: <line in quotes, or nothing>
2. Do: ... Say: ...

**Close (say it exactly):** "<The deal, once, with the price or how. Twelve words or fewer.>"

**Get these shots:** <close-ups and cutaways the edit needs; the safe way to film any risky shot.>

---

## 2. ...

## Extra shots while everyone's there

A few seconds each, no talking. We cut these into every video.
- <shot>

**If there's time:** <one optional extra.>

**After the shoot:** Send everything full size on Google Drive or WeTransfer, not WhatsApp. We edit and send the videos over to check.
```

How the builder reads it:
- The pack is always cover, numbers page, then one page per ad, then any extra-shots pages; a one-ad job is three pages.
- `mode: edit` in the front matter marks a script for footage already shot: Say lines and the close hold on-screen text, the film section is `## The footage`, and the page labels read "On screen" (see SKILL.md).
- `settled:` in the front matter lists what the person running this has confirmed, separated by semicolons. `check_pack.py` won't read those phrases as extra urgency or as the deal said again. It never shows on the page.
- The builder prints a `warning:` for an empty film section, an empty section, or a `##` section it doesn't know (it becomes its own page). Read them.
- Front matter is optional. `cover` is the big cover headline (` / ` breaks the line); without it, the text before the colon in the `#` title is used. `for` and `line` are the orange italic lines above and below it.
- In the numbers section, `**short figure**:` makes a big-number row; a bullet that opens with a longer bold sentence becomes a black warning card; plain bullets sit under the numbers as notes. A warning card says what the team shouldn't say and why, for a real reason (legal, not in the sale). It's never a place for something undecided.
- Ad headings are `## N. Title`. The italic line under it is the page's orange line; put the length first ("About 15 seconds"), because the length check reads it.
- `<!-- kind: x -->` under **Hook** is invisible on the page and tells `check_pack.py` the hook kind (`hooks.md` lists them).
- Say lines: words in quotes are spoken; anything after "On screen:" in quotes is read, not spoken. "Nothing" means silent.
- Any `##` section after the ads becomes its own page: bullets go in an orange card, `**Label:** text` lines become cards.

## Building the HTML

```
python3 scripts/build_pack.py job/pack.md --pdf
```

Writes `pack.html`, copies the logo beside it, and prints `pack.pdf` with headless Chrome (a throwaway profile, so nothing is left behind; Chrome often errors at shutdown after writing the file, which is fine). Then look at every page of the PDF: one ad per page, nothing clipped at the bottom. If an ad runs over, shorten its shots line or other hooks before shrinking anything; text stays big.

## reasoning.md

Sits beside the pack. Only the person running this (if they ask "why"), the writer and the lessons loop read it. The critic never does. Every concept names the passage behind its hook, its promise and its proof; a row can say "brief" or "logic" beside the id if that carries more of the weight.

```markdown
# Reasoning: <client> <job>, <date>

## 0. Readings taken
- <what was unclear, the sensible reading, one line why>

## 1. Diagnosis
<one block per slot, from diagnose.md>

## 2. Passages on the table
- caples-0221 · plain beat clever by 89% · slots 1, 3
- ...

## 3. Hooks
### Ad 1
| # | kind | first frame | on screen / spoken | mute reading | passage | kept |
|---|---|---|---|---|---|---|
| 1 | odd-picture | ... | ... | ... | caples-0357 | safe |
...

## 4. Per ad
### Ad 1: <title>
| beat | choice | passage | why |
|---|---|---|---|
| hook | <what you chose> | caples-0357 | <one plain line> |
| promise | <what it says they get> | schwartz-0018 | ... |
| proof | <what shows it> | bencivenga-0005 | ... |
| body | ... | ... | ... |
| close | ... | ... | ... |

## 5. Critic notes overruled
- Ad 2, fix 1: kept the client's idea because ...
```

Don't quote the books. Say what they teach in your own words and cite the id.

## What never goes on the page

Passage ids, book names, author names, scores, the hook kinds, the critic's notes, questions for the person running this, anything marked unconfirmed, and anything another client did.
