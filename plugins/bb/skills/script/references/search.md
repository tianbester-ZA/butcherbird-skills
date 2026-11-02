# Driving the book search

17 books, each read in full, with a reader's note and a score on every passage that was any use. 3 means it changes how you'd write a reel; 2 is a usable rule. By default the search looks only at notes scoring 2 or 3. Python 3, no installs. `search.py` below means the full command given in SKILL.md.

```
search.py "headline stops reader" --job hook --k 8     # notes, score 2 and up
search.py "price reduced reason" --book schwartz       # one book
search.py --show caples-0221                           # one passage's note, chapter and score
search.py --toc sugarman                               # chapters with id ranges
```

**Read the note before you lean on it.** A note is one reader's summary and some over-reach, so use `--show` and judge what it actually claims, and say "logic" or "brief" when that's what your choice rests on. The book text doesn't ship with this pack. If someone has the full library on their Mac, `--show` also prints the passage. Don't quote the books. Say what they teach in your own words and cite the id.

**Jobs:** `want`, `awareness`, `offer`, `proof`, `hook`, `shape`. A note can have several. `feel`, `rhythm` and `eye` belong to `reel-cut`.

**Books** (`--book` takes the start of the slug): schwartz, caples, hopkins, ogilvy, sugarman, cialdini, heath, bencivenga, masters, miller, sharp, hormozi-offers, hormozi-leads, hormozi-money. Murch, Pearlman and Block are editing books, though their notes on shape and the eye are often useful.

## What each book is good for here

- **Caples:** tested headlines with real numbers; the plain hook, picture and line, the appeal.
- **Schwartz:** awareness, sophistication, how belief gets built, offer mechanics. No page numbers.
- **Sugarman:** the first line, the slide, flaws, one offer, short-form TV.
- **Hopkins:** mail-order evidence, specificity, cure against prevention.
- **Ogilvy:** what Ogilvy & Mather research found in TV.
- **Cialdini:** real experiments. Often favours and donations rather than purchases, so check.
- **Heath:** concrete, surprise, story, numbers people feel.
- **Sharp:** who buys, distinctive assets, price cuts. Mostly packaged goods.
- **Hormozi:** offer wording and hook mechanics. His numbers are his own claims from transcripts.
- **Masters, Bencivenga, Miller:** masters' speeches, emails and a framework. Practitioner opinion, some with tests behind it.

## Queries that work

Search matches words, not meaning. Short, plain words work best, and so do the older trade words the books use: headline, reader, prospect, copy, coupon, claim.

| Decision | Query |
|---|---|
| The appeal | `"right appeal sales" --job want` |
| Cold opening | `"unaware market opening" --job awareness` |
| Tired category | `"mechanism claims heard" --book schwartz` |
| Plain against clever | `"clever headline test" --book caples` |
| First frame | `"picture first attention" --job hook` |
| A flaw | `"flaw negative first" --job proof` |
| Reason for a discount | `"reason price cut" --job offer` |
| Scarcity | `"limited supply" --book cialdini` |
| Wording the deal | `"free discount offer wording" --job offer` |
| Short TV and reels | `"short commercial offer" --book sugarman` |
| Brand on mute | `"distinctive assets brand" --book sharp` |
| Holding attention | `"question curiosity" --book heath` |
| Jokes | `"humour" --book ogilvy`, `"humour" --book caples` |

## When nothing useful comes back

- Try the book's own vocabulary: "headline" for hook, "prospect" for viewer, "copy" for script.
- Narrow with `--book`, or drop `--job`. Results cap at three per book unless you pass `--book`.
- Read the book's card (`books/cards/<book>.md`), or use `--toc` to find the chapter, then `--show` ids in its range.
- If there's still nothing, the books don't speak to this decision. Camera as a character, mute grammar and end gags are like this: they come from watching reels. Say so in the sheet and decide on the brief and the client's results. Don't force a citation.

## Gotchas

- The job filter widens a query, and Block's film notes creep in on `--job shape`. Add `--book` when they do.
- Bencivenga, Heath, Masters and Schwartz have no page numbers; cite the id.
- A note scoring under 2 isn't searched by default, and `cite_check.py` flags one if you cite it. A passage scored 0 has no note at all: `--show` says so, and you don't cite it.
- In a zsh loop, a query and its flags held in one variable don't split into arguments. Write each search out.
