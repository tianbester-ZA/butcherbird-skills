# Changing a skill

**Committing to `main` ships to everyone.** There's no release step. Everyone with auto-update on gets it the next time their Claude Code checks. So test first, and keep changes small.

## Where things are

```
plugins/bb/skills/script/   /bb:script
plugins/bb/skills/edit/     /bb:edit
plugins/bb/skills/books/    /bb:books, and the notes and cards behind it
scripts/check.py            the checks that run on every push
```

Each skill has a `SKILL.md` (what Claude reads first), `references/` (loaded when needed) and `scripts/`.

## Keep it goal-led

A `SKILL.md` says the goal, why, what good looks like, and only the few things that aren't obvious. No step-by-step scripts, no piles of rules, no capitals. Explain why, and Claude can generalise. Keep it short: every line is read on every run.

Change a skill because a real job went wrong, and fix the pattern, not the one case. To add a lesson, add a dated line to that skill's `lessons.md`: what happened, the number and its date if there is one, what to do instead. No client names.

## Test it on your Mac

From the repo folder:

```
claude --plugin-dir ./plugins/bb
```

That loads your copy for one session and beats any installed version. `/bb:edit` builds its tools again the first time you do this, because a local copy gets its own data folder. Run the skill on something real. Then:

```
python3 scripts/check.py
claude plugin validate .
```

`claude plugin validate` warns that there's no version. That's on purpose: with no version, every commit reaches people. Adding one would freeze everyone on it until someone changed it.

Paths: in a `SKILL.md`, use `${CLAUDE_SKILL_DIR}`, `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}`. Claude Code only fills these in inside `SKILL.md`, not in reference files or the shell, so reference files use the short forms that the skill's Commands section defines. Scripts find their own files from where they sit. Anything that has to survive an update goes in the data folder, because the plugin folder is replaced every time. Python packages are pinned in `edit/scripts/requirements.txt`. Change a pin and everyone's Python tools rebuild on their next `/bb:edit`.

## What must not go in

This repo is public, so anyone can read it. No client information, ever, and a client's information never crosses clients.

- **No client information.** No names, products, numbers, ads or briefs, in skills, references, lessons, examples or tests. Use invented brands (Fynn, Moss Mop, Dune Dog). A client's winners stay in that client's own folder.
- **No book text or quotes.** Only short notes in our own words in `notes.jsonl` and the cards. Nothing from the book files themselves. The notes keep only what scored 2 or 3.
- **No secrets, footage, music, client logos or client fonts.** Butcherbird's own logo and the open fonts in `assets/` are fine.
- **No personal paths or machine names.**

`scripts/check.py` catches most of this on every push: valid JSON, a description on every skill, every passage id has a note, no client names, no personal paths, nothing big, no book text in the notes. It only knows the client names on its list, so **add a new client to `CLIENTS` in `scripts/check.py` when one signs.** It can't catch everything. Read your own diff.

Limits stay in the skills: nothing goes to a client, gets published or spends money without the person's yes.

## Writing it down

Add a line to `CHANGELOG.md` when a change affects how a skill works. Commit messages say what changed and why, in plain words.
