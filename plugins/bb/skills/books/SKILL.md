---
name: books
description: Answers what 17 advertising and editing books say about a question (Schwartz, Caples, Hopkins, Ogilvy, Sugarman, Cialdini, Heath, Bencivenga, Masters of Copywriting, Miller, Sharp, three Hormozi books, Murch, Pearlman, Block), by searching notes on 3,286 passages that were each read in full, and citing the passage ids. Use it whenever someone asks what the books say about a hook, offer, proof, awareness, urgency, pricing, guarantees, rhythm, cuts or where the eye goes, wants evidence for a creative call, wants to settle an argument about an ad, or asks what a named book or author is good for. /bb:script and /bb:edit call it for their decisions.
argument-hint: "[question]"
---

# /bb:books

## Goal
A straight answer to what the books say, with the passage ids behind it, and a plain note of where they disagree or don't speak at all.

## Why
Claude half-remembers these books and sounds sure anyway. Each book here has been read passage by passage, and a reader wrote a plain note on each passage: what it says and what to do about it in a reel. Searching those beats reciting from memory, and the ids mean anyone can check.

## How
```
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" "plain words" --job hook --k 8
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" "plain words" --book caples
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" --show caples-0221
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" --toc sugarman
python3 "${CLAUDE_SKILL_DIR}/scripts/search.py" --books
```
Search matches words, not meaning, so literal short words work and whole questions don't. Run a few searches with different words, then `--show` the ones you'll rely on.

**Jobs:** `want`, `awareness`, `offer`, `proof`, `hook`, `shape`, and for editing `feel`, `rhythm`, `eye`.

**The cards.** `${CLAUDE_SKILL_DIR}/cards/<book>.md` is a one-page summary of each book: the core idea, what it changes against what a generic script does, its ten best passages and an index by job. Read a card when someone asks about a book as a whole, or to get your bearings before searching.

## What you get
Answer first in a few plain lines, each with its id (`caples-0221`). Then one line on where the books disagree, if they do, and which way we'd lean for a 15 to 60 second video.

Be straight about the limits. These are print, mail-order, TV and lab books, so a number tells you what happened there, not what a reel will do. Hormozi's numbers are his own claims. Many of Cialdini's are favours, not purchases. Nothing tests a muted feed. If the books don't speak to it, say so; never force a citation.

## What's here and what isn't
Short notes in our own words and the cards ship with this pack, never the books or quotes from them. `--show` gives you the note, and that's what you cite. Say what a book teaches in your own words. If someone wants the original, tell them which book and chapter.
