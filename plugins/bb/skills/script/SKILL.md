---
name: script
description: Writes 15 to 60 second paid social video scripts and reels (UGC, founder, talking head, skits) and packs them in Butcherbird's one-ad-per-page shoot-pack format, checking every hook, promise, proof and offer decision against 17 advertising books through the book search, then running a separate critic pass. Use it whenever someone asks for scripts, hooks, a script pack, a shoot pack, ad concepts, reel ideas, UGC or creator briefs, founder videos, skits, "what should they say", or "write me five videos for X", for any client, even with only a deal and a vibe. Also use it to re-hook a tired ad, rewrite a weak script, write the on-screen words for an edit of footage already shot, or judge why a script feels flat. Not for static ads, emails or landing pages.
argument-hint: "[client, deal or brief]"
---

# /bb:script

## Goal

A shoot pack the team can film from in an afternoon. Every ad stops a stranger in two seconds with the sound off, gives one person a reason to buy, and ends on one deal they could act on. Behind it, a reasoning sheet names the book passage under each hook, promise and proof.

## Start here: read, restate, ask once

The person running this holds the context, and what they say here is what makes the work good. An ad of ours failed because nothing asked; a reel worked because someone gave real context.

Read first, don't ask: the client's winners, personas, reviews and past ads; live product, price and offer; what's been said in the brief.

Restate: buyer, angle, stage, offer, as you read them from the evidence. Fill in what you know, so they confirm rather than retype.

Ask only what's missing, in one short round (AskUserQuestion when you have it, otherwise in the message). Usually two or three:

1. Who should this ad move, what should they picture for themselves, and what should they do straight after watching?
2. What exact product, offer, price, reason to act and proof can we show today? What really happened to the person speaking?
3. Who's speaking, how should they sound, and what can we actually film: camera, people, location, props, time?

Then propose where it sits, for a yes or a change: buyer × angle × awareness stage, the script mode (founder story, real comment reply, demonstration, problem-led, fair comparison, field challenge or entertainment, direct offer) and the format.

Put the answers in `job/brief.md`, then work to the end without stopping again. If they've already given it all, or say just go, don't ask. If nobody can answer (a headless run), say what you would have asked and take the sensible reading.

## Taste belongs to the job

Write the job on the first line of `job/brief.md`: paid ad, organic reel, or whatever the opening round set. What someone liked in one video doesn't carry to another. An organic reel and an ad are different jobs: the ad is meant to sell. So an ad is judged on who it's for, the product's selling points, proof and a reason to buy, not on the jokes or feel of an organic piece. A joke earns its place in an ad only by carrying the sale.

## Why this exists

Left alone, Claude writes polite ads: one person to camera, a gentle spoken hook that needs you to know the star, a small gag, the deal said twice, the same close each time. Clean, shootable and flat. Models drift to the safe, common choice, and a list of rules doesn't pull them back.

What does: finding the appeal before the words, making many hooks before choosing, having the book's note in front of you, and letting a critic who never saw your reasoning judge the draft. Books are questions and passages, never voices. "Write like Schwartz" does nothing. "This viewer is cold, so does line one describe them rather than the product?" with the passage behind it does.

## What good looks like

- Five ads that don't share a shape. Read the running order and you can't predict ad 4 from ad 1.
- A first frame and a text line a stranger gets on mute, with few words. The camera can be a character and the end gag can be a look. Not every idea is a talking head, and not every idea ends with someone falling in a pool.
- Fast and clear about who it's for and why they'd buy, and every ad ends on one deal. Skits are welcome when the brief wants fun, and must still sell: the joke is the selling point, and retelling it needs the product.
- Directable: "Do this. Do this. Say this." The simplest set-up that carries the idea, usually one place and the fewest people.
- One deal per ad, said once, at the close, exactly, in twelve words or fewer, worded in its strongest true form.
- Exact figures and named details instead of adjectives, each traced to its owner.
- It speaks to one person, and shifts one belief she holds. A product walking through nice shots is a showcase, however pretty, and fails.
- A pack that looks exactly like the shipped format, with no citations, no open questions and nothing marked unconfirmed.

## Commands

Reference files write these short. Shell state doesn't carry between commands, so always use the full form, and give a critic agent the full form too.

- `scripts/...` means `${CLAUDE_SKILL_DIR}/scripts/...`. `references/...` means `${CLAUDE_SKILL_DIR}/references/...`.
- `search.py` means `python3 "${CLAUDE_PLUGIN_ROOT}/skills/books/scripts/search.py"`.
- Book cards: `${CLAUDE_PLUGIN_ROOT}/skills/books/cards/`.

## The path

Work in `<client>-scripts/<yyyy-mm-dd>-<slug>/` in the folder the person is in, or the folder the brief names (`job/`). Each step writes something, so a restarted session picks up from the last file.

**0. Read, the client first.** The opening round above, done properly: the client's own winners and their numbers, its personas, and its customers' words (reviews, ad comments), wherever its notes point. "None on file" means you haven't looked yet. Then any client notes or profile skill, the client's own folder of winners (that client only, see `examples/README.md`), `lessons.md`, the brief. Recheck prices, deals and dates at their owners. Write `job/brief.md`: facts and deals with source and date, who's on camera, what only this brand has, the client's own ideas one per line, the answers from the opening round.

**1. Diagnose.** Load `references/diagnose.md`. Start with one real person: a name for her type, her day, what she uses now, what she'd say, why her and not the other personas, with the evidence. Then settle the appeal, what they do now, how aware they are, how many times they've heard it, what they don't believe, why the deal exists and what only this brand has. Write `reasoning.md` §1, one block per slot.

**2. Search the books for this job.** Load `references/search.md`. Don't start from memory of what the books say: run six to ten searches on this product's actual problems, read the notes with `--show`, keep eight to twelve that bear on this brief. Write `reasoning.md` §2: id, one line, which slot.

**3. Hooks.** Load `references/hooks.md`. Six to eight per ad across at least four kinds, including one plain and at least two odd ones you'd hesitate to show the client. Keep three: one safe, one odd, one that doesn't say the deal. Write `reasoning.md` §3. Make the options even when nobody's there to see them: pick, and leave the passed-over ones in the sheet.

**4. Draft.** Load `references/body-and-close.md`, `references/offer-and-proof.md` and `references/pack-format.md`. Write `job/pack-draft.md`. Write `reasoning.md` §4: per ad, a row each for hook, promise, proof, body and close, each with its passage.

**5. Check.**
```
python3 "${CLAUDE_SKILL_DIR}/scripts/check_pack.py" job/pack-draft.md --event "Black Friday"
python3 "${CLAUDE_SKILL_DIR}/scripts/cite_check.py" job/reasoning.md
```
Fix every red line. Amber lines are judgement calls. Save the output in `job/checks.txt`.

**6. Critic.** Launch a fresh agent on the strongest model available with `pack-draft.md`, `brief.md`, `references/critic.md`, the full `search.py` command (and, for an edit, the footage sheets). Not `reasoning.md`, not this chat: it judges the ad against the job in the brief, not the excuse. Its questions name real passages and it reads their notes. It returns notes, never a rewrite. Save as `job/critic.md`.

**7. Rewrite.** Read the note behind each passage the critic cites before acting on it: some ids turn out to be about something else, and a note can still be right on its own logic. Where the brief wins, disagree in writing in `reasoning.md` §5. Re-run step 5. One round, two at most. The result is `job/pack.md`.

**8. Pack.**
```
python3 "${CLAUDE_SKILL_DIR}/scripts/build_pack.py" job/pack.md --pdf
```
Open the PDF and look at every page: nothing clipped, one ad per page. Read any `warning:` lines. In the reply, give one line per ad and one sentence naming the books once. If the client has a log, add a dated line.

## Settled is settled

Facts the person has settled are settled. Nobody wants a pack that lists things as unconfirmed, or a page of small questions. So don't: use the sensible reading, write it in `reasoning.md` §0 with one line of why, and move on. Put what they've confirmed in the pack's `settled:` line, which the checker respects. If a figure truly has no owner, write the ad without it, and log that.

Only what would change a decision or a client gets raised, as one plain line in the reply. A number you can't source is never invented, and never appears as a question either.

## Editing footage that already exists

Sometimes the job is words for footage in hand, not a shoot. Same path, three differences. Step 0 starts from the footage: list the usable moments by clip and time, since the script can only promise what was filmed. Step 1 adds a footage check: for every claim, name the clip moment that shows it, and rewrite or drop a claim with no shot. On the page, put `mode: edit` in the front matter: Say lines hold on-screen words, the close is on-screen text, the film section is `## The footage`. Hand the pack to `/bb:edit`.

## Hard limits

- One client per job. Nothing from another client goes into the brief, the pack or the sheet, and no client's information goes into this skill.
- No invented numbers, deadlines, stock counts or reviews. Urgency is only what's true and has a reason.
- Book text stays out. Say what a book teaches in your own words and cite the id.
- Nothing goes to a client, gets published or spends money from this skill without the person's yes. The pack goes to the person running this; they send it.

## Know-how

**Words per second.** 2.5 spoken words a second: 15 s is about 35 words, 20 s about 50, 30 s about 75, 60 s about 150. Actions take time too.

**The books aren't about reels.** They're print, mail order, TV and lab studies. Treat the numbers as what moved people then. Hormozi's are his own claims; many of Cialdini's are favours, not purchases. Nothing in them tests a muted feed. Mute grammar, the camera as a character and end gags come from watching real reels, so that's where to look: the client's own references, and whatever the person has sent.

**Where the books fight.** Each reference ends with the disagreements and which way we lean for a 15 to 60 second video. Name the lean in the sheet when it decides an ad.

**A vote is an opinion test.** Critics and judges prefer clever; split runs often don't (`caples-0221`, `caples-0279`). So a plain hook is filmed as another option even when the critic is unimpressed, and live numbers settle it.

**Hook and hold.** Hook rate = 3-second plays ÷ impressions. Hold rate = ThruPlays ÷ 3-second plays. Hook under about 20%: re-cut the opening only. Hold under about 40%: re-cut the middle. Both healthy and no purchases: the offer or the close, not the edit.

## Load these when

| Reference | When |
|---|---|
| `references/diagnose.md` | Step 1, and whenever a script feels flat and you can't say why |
| `references/search.md` | Step 2, or when a search comes back empty |
| `references/hooks.md` | Step 3, and for any "re-hook this ad" job |
| `references/body-and-close.md` | Step 4 |
| `references/offer-and-proof.md` | Step 1 for the belief gap and the deal's reason; step 4 |
| `references/pack-format.md` | Step 4 and step 8 |
| `references/critic.md` | Only the critic agent (step 6) |
| `examples/README.md` | Step 0, to find a client's winners |
| `evals/judge.md` | Only for blind tests between two packs |

## Lessons

`lessons.md` holds dated bullets from real results: the ad, the number with its date, the passage behind the beat, what was tried. Read the last five at step 0; the critic checks the draft against them. This folder is replaced on every update, so a client's own lessons and winners go in that client's folder, and a lesson for everyone goes in through the repo (`CONTRIBUTING.md`).
