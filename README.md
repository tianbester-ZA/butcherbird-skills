# Butcherbird skills

Butcherbird's way of writing and cutting social video, as skills for Claude Code. Install it once, and it stays up to date on its own.

| Type this | It does this |
|---|---|
| `/bb:script` | Writes a shoot pack: scripts for ads and reels, checked against the books and a separate critic |
| `/bb:edit` | Cuts raw footage into finished 9:16 and 4:5 videos with sound, on your Mac |
| `/bb:books` | Tells you what 17 advertising and editing books say about a question |

## Install

You need Claude Code on a Mac. Paste this into Terminal:

```
curl -fsSL https://raw.githubusercontent.com/tianbester-ZA/butcherbird-skills/main/install.sh | bash
```

That adds the skills, turns on auto-update and checks the tools `/bb:edit` needs. It tells you the exact fix for anything missing. The first time it takes a few minutes, because it builds the Python tools. To skip those and only write scripts: `curl -fsSL https://raw.githubusercontent.com/tianbester-ZA/butcherbird-skills/main/install.sh | SKIP_SETUP=1 bash`

Then open Claude Code in any folder and try `/bb:books what makes a hook work`. If it was already open, run `/reload-plugins` first.

## How updates work

When someone improves a skill and commits it, it reaches you. Claude Code checks a few minutes into a session, in the background, and updates the files. You'll see `Plugin updated: bb`. Run `/reload-plugins` to use it straight away, or it loads next time you open Claude Code.

Want it right now? `claude plugin update bb@butcherbird`, then reopen Claude Code.

The check happens at a random moment in the first ten minutes after your first message, so a short session may not catch it.  Your skills keep working from the last update either way.

## /bb:script

**Use it for:** scripts, hooks, a shoot pack, ad concepts, reel ideas, UGC or creator briefs, founder videos, skits, re-hooking a tired ad, words for footage already shot, or working out why a script feels flat. Not for static ads, emails or landing pages.

**What it asks:** it reads what it can first (the client's winners, personas, reviews, past ads, the live product and offer), says it back to you, and asks only what's missing, usually two or three of these. Then it works to the end without stopping.
1. Who should this ad move, what should they picture for themselves, and what should they do straight after watching?
2. What exact product, offer, price, reason to act and proof can we show today? What really happened to the person speaking?
3. Who's speaking, how should they sound, and what can we actually film?

Answer these properly. You hold the context, and what you say here is what makes the work good.

**What you get:** a PDF shoot pack with one page per ad, each with the message, the hook, what to do and say, and the close said exactly. Beside it, a reasoning sheet naming the book passage behind each decision.

**Example:**

> `/bb:script five videos for Fynn socks, buy one get two free, shooting Saturday with the founder`
>
> *Here's what I've got: buyer is a hiker who's been let down by wet socks, deal is buy one get two free. What's missing: who's on camera besides the founder, and what can we film?*
>
> You answer in a line. It comes back with five ads that don't share a shape, ready to film.

## /bb:edit

**Use it for:** editing, cutting, re-cutting, trimming, captioning or scoring a video, 4:5 versions, or fixing a weak opening. For the idea or the words, use `/bb:script`.

**What it asks:** first it checks your Mac. Then it always asks what we're trying to do and what kind of video it is: an awareness video, a showcase reel, a paid ad selling something, UGC or a founder talking, behind the scenes, something else. Then only what's missing:
- Who's it for, and what should they feel or do after watching?
- What style, and which reference is closest?
- Footage, sound or music, length, and where it runs.

**What you get:** it listens to every clip, shows you options on your real footage to pick from, cuts it, has a separate critic check it, and hands you a 1080x1920 and a 1080x1350 master at the right loudness, with the plan behind them. It tells you plainly that nobody has heard it: the sound report measures, it doesn't listen, so the mix goes to your ears.

**Example:**

> `/bb:edit ~/Desktop/saturday-shoot`
>
> *What are we trying to do, and what kind of video is it?*
>
> "Paid ad for the socks, buy one get two free."
>
> It listens to the clips, shows you three treatments for the opening, and comes back with the two videos and frame 0.

**Taste belongs to the job.** What someone liked in one video doesn't carry to another. An ad is meant to sell, so it's judged on who it's for, the selling points, proof and a reason to buy, not on the jokes or feel of an organic reel. Both skills, and their critics, judge against the job you set.

## /bb:books

**Use it for:** what the books say about a hook, an offer, proof, urgency, pricing, a guarantee, rhythm, or anything else you're arguing about. It answers in a few lines with the passage ids, says where the books disagree, and says when they don't speak to it.

**Example:** `/bb:books does a discount need a reason`

The other two skills use it for every decision.

## What it needs on your Mac

`/bb:script` and `/bb:books` need Claude Code and nothing else. The PDF needs Google Chrome.

`/bb:edit` needs a Mac, and checks all of this each time it starts, with the exact fix:

| What | For | Fix |
|---|---|---|
| ffmpeg | cutting and sound | `brew install ffmpeg` |
| whisper-cli | hearing the words | `brew install whisper-cpp` |
| Swift | drawing text | `xcode-select --install` |
| Python 3.11 to 3.14 | the sound tools | `brew install python@3.12` |
| Sound models, about 490 MB | speech and laughs | it offers to download them |
| Chrome and Node (optional) | drawn animation | `brew install node` |

To check by hand, run this and read each line:

```
python3 "$(ls -td ~/.claude/plugins/cache/butcherbird/bb/*/ | head -1)skills/edit/scripts/setup.py" --data ~/.claude/plugins/data/bb-butcherbird
```

## Your work and your clients

- Scripts and edits go in a folder where you're working, never in the skills.
- A client's winners and lessons stay in that client's own folder. Nothing crosses clients.
- Nothing goes to a client, gets published or spends money without your yes.

## Feedback, and changing a skill

Something off? Tell Tian, or open an issue on this repo with what you asked for, what you got and what you expected. A real example helps most.

Want to change a skill yourself? See [CONTRIBUTING.md](CONTRIBUTING.md). Committing to `main` ships to everyone. What's changed lately is in [CHANGELOG.md](CHANGELOG.md).

## The books

Each was read passage by passage, and a reader wrote a plain note on every useful passage. Only short notes in our own words and a one-page card per book are here, never the books themselves. Buy the books.

**Advertising:** Breakthrough Advertising (Eugene Schwartz) · Tested Advertising Methods (John Caples) · Scientific Advertising (Claude Hopkins) · Ogilvy on Advertising (David Ogilvy) · The Adweek Copywriting Handbook (Joseph Sugarman) · Influence (Robert Cialdini) · Made to Stick (Chip and Dan Heath) · Bencivenga Bullets (Gary Bencivenga) · Masters of Copywriting (various) · Building a StoryBrand (Donald Miller) · How Brands Grow (Byron Sharp) · $100M Offers, $100M Leads and $100M Money Models (Alex Hormozi, free courses)

**Editing:** In the Blink of an Eye (Walter Murch) · Cutting Rhythms (Karen Pearlman) · The Visual Story (Bruce Block)

They're print, mail-order, TV and lab books, so none of them tests a muted feed. What works on mute comes from watching real reels. The skills say so where it matters.

---

Public so the team can install it without an account. © Butcherbird. All rights reserved: see [LICENSE](LICENSE).
