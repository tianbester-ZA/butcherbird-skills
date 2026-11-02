---
name: edit
description: Cuts 15 to 60 second paid ads and organic reels from raw footage to finished 9:16 and 4:5 masters with sound, on this Mac with ffmpeg. Asks what the video is for first, listens to every clip, plans each beat (what to feel, where to cut and hold, where the eye lands) against three editing books through the book search, shows options before a draft, and runs a separate critic pass on the rough cut. Use it whenever someone asks to edit, cut, re-cut, trim, "make a reel from", "put together", caption, score or finish a video, for a client or for Butcherbird, paid or organic, UGC, founder, talking head, behind the scenes or montage, and for 4:5 versions, re-cutting an opening after a weak hook rate, or explaining why a cut feels off. Writing or changing the words or the idea belongs to /bb:script.
argument-hint: "[footage folder, or what the video is for]"
---

# /bb:edit

## Goal
Turn raw footage into a short video a stranger stops for, feels something in, and acts on: a 1080x1920 master and a proper 1080x1350 Feed master, both at about -14 LUFS, with an edit plan behind them that says why each cut sits where it does.

## Before anything: check this Mac
```
python3 "${CLAUDE_SKILL_DIR}/scripts/setup.py" --data "${CLAUDE_PLUGIN_DATA}"
```
It prints one status line per tool, each with the exact fix, then READY or NOT READY. It's safe to re-run, and takes seconds once everything's in. The first run builds the Python tools, which takes a few minutes.

On NOT READY, give the person the fix lines and stop. If only the models are missing, tell them it's about 490 MB, and on their yes add `--download-models` to the same command. OPTIONAL lines don't block anything.

## Then: ask what we're trying to do
The person running this holds the context, and what they say here is what makes the work good. An ad of ours failed because nothing asked; a reel worked because someone gave real context.

Look at what's there first (footage, script, brief, notes) and restate it, so they confirm rather than retype. Ask in one short round (AskUserQuestion when you have it, otherwise in the message).

Ask first, always, unless they've already told you:

1. What are we trying to do, and what kind of video is it? An awareness video, a showcase reel, a paid ad selling something, UGC or a founder talking, behind the scenes, something else?

Then only what's missing:

2. Who's it for, and what should they feel or do after watching?
3. What style? Which reference is closest? You'll then show options on the real footage to pick from.
4. Footage, sound or music, length, and where it runs.

If it's an ad, the script's buyer and stage carry over, or `/bb:script` runs first. An edit never swaps the idea or a claim; that goes back to the script.

Put the answers in `job/brief.md`, then work to the end. The only other stop is the options in step 2. If they've given it all, or say just go, don't ask. If nobody can answer (a headless run), say what you would have asked and take the sensible reading.

## Taste belongs to the job
Question 1 sets the job: write it on the first line of `job/brief.md`. What someone liked in one video doesn't carry to another. An organic reel and an ad are different jobs: the ad is meant to sell. So an ad is judged on who it's for, the product's selling points, proof and a reason to buy, not on the jokes or feel of an organic piece. Lessons from an organic cut don't bind an ad, and the other way round.

## Why
Generic AI edits cut on every music beat, give every shot the same length, push in on everything and stop the moment the last word ends. Each of those has been rejected here (see `lessons.md`). The editing books answer the same questions better, so we ask them per decision: Murch for where a thought ends, Pearlman for rhythm and the open question, Block for where the eye goes. The books are questions and passages, never voices.

## What good looks like
- Frame 0 already works as a still with the sound off: the product, a result or a surprise, not a logo or a greeting.
- One question opens in the hook and stays open until the payoff.
- Cuts land where a thought or a movement finishes, not on a grid. At least one shot is held next to quicker ones, so it reads as a pause on purpose.
- The brightest or moving thing in each shot is the thing to look at. Text sits under the chin or in clear sky, never over a mouth, and never stacked with another line saying the same words.
- The close is calmer than the shot before it and the ask is plain. The ending lands: the music ends on its own ending or a real phrase, never a fade over a song still going, and never over its own last hits.
- The real sound is in it. People in the footage are heard over the music, and the song's biggest moment lands on the picture's biggest moment.
- Footage looks as filmed: the iPhone's own colour, still framing, a gentle punch-in only on the product, no moving zooms, no mirror fill, no black bands.
- The 4:5 is laid out again from the same EDL, so captions and faces stay in frame.

## Commands
Reference files write these short. Shell state doesn't carry between commands, so always use the full form, and give a critic agent the full form too.

- `PY` means `"${CLAUDE_PLUGIN_DATA}/venv/bin/python"`, the Python that setup built. Run every Python script here with it.
- `scripts/...` means `${CLAUDE_SKILL_DIR}/scripts/...`. `references/...` means `${CLAUDE_SKILL_DIR}/references/...`.
- `search.py` means `python3 "${CLAUDE_PLUGIN_ROOT}/skills/books/scripts/search.py"`.

## Workflow
Job folder: `<client>-<job>/` in the folder the person is in, or the one the brief names (`job/`). Footage stays where it is; only renders are written.

0. **Read, and listen.** Run `PY scripts/listen.py clips <footage> --out job/sound` before you plan: it transcribes every clip and finds the speech, laughs, shouts and level peaks. Read all of it. Off-camera lines are often the idea, and they tell you what a shot really is (one ad's "application" shot was a director saying "you don't have to apply anything"). Run `PY scripts/listen.py song <track>` too and read the words: they may fight the picture or help it. Then any client notes, `lessons.md`, the client's own folder of past edits (that client only, see `examples/README.md`), the script or brief. Run `scripts/probe.sh <footage> > job/footage-log.md`, then watch the clips and add the best moments by timecode. Convert HDR with `scripts/proxies.sh` before anything else. A footage log someone else wrote is a lead, not a fact: look at a frame of every pick before it goes in the EDL (`scripts/sheet.sh <clip> <start> <len> job/sheets`, so nothing is written beside the footage). List each claim the script or brief makes against the clip moment that shows it; a claim no clip shows is changed or cut now, not by the critic. Write the vibe in one line, in the person's words.
1. **Plan.** Load `references/plan.md`, `rhythm.md`, `eye.md`, `sound.md`. Measure the music with `PY scripts/beats.py <track>`: tempo, first beat and the loudness map, which shows where the track is already moving for `music.start`. Per beat (hook, turn, payoff, close): what to feel, the rhythm, where the eye lands, the sound. One search per column. Write `job/plan.md`, each line with a passage id.
2. **Options.** About three treatments per section (casual, mid, extreme) as tiles: one frame and one line each. The person picks. If they're not there, or said just go, pick, log why in `options.md`, and keep the others visible; there a table of options is enough.
3. **Rough cut.** Load `references/formats.md`. Write `job/edl.json`, then `mix.py` (the sound) and `cut.py --draft` on proxies. `scripts/sheet.sh` on the result, `listen.py cut` on the result, and read the report and its waveform picture. Look at the sheet, the hook strip and frame 0 yourself, and watch it once with the sound off.
4. **Critic.** A fresh agent gets `job/brief.md` (so it judges against the job), frame 0 at full size, the frames, strip, the listen report, the mix log, the claim list, `references/critic.md` and the full `search.py` command. Frame 0 goes first, because a thumbnail can misread. Not your notes or this chat. It returns per-beat notes, at most three fixes with passage ids, and a verdict.
5. **Final.** Fix what the critic found (or write down why the brief wins). Point the EDL at full-quality SDR files, render without `--draft`, then `reframe.py` for the 4:5, then `check_cut.py` and `listen.py cut` on the result. Fix every FAIL; read every WARN. **Say plainly that nobody has heard it:** the report measures, it doesn't listen, so the voice lines and the mix go to the person's ears. Sheets of both masters. README.txt and delivery as in `formats.md`.

Reply with the two files, frame 0, one line per beat on what changed after the critic, and one sentence naming the books once. Citations stay in `plan.md`, never on the video.

## Hard limits
- A changed claim or idea goes back to `/bb:script`. If the footage or the sound kills the idea, stop and redo the diagnosis and the script, with the critic; never swap in a new line during the cut. An ad of ours swapped its line in the edit and shipped with no audience and no reason to exist.
- Options before a draft, every time. If nobody's there, pick and log; never skip.
- Never slow or speed a voice. `cut.py` mutes a shot's own audio when its speed isn't 1.
- No denoise, no blur, no moving zooms, no mirror fill, no black bands. HDR goes to SDR first with avconvert. No grade on talking heads and UGC. A light look only when the brief asks for one (`look` in the EDL), said out loud in the reply.
- Never ship with the clip sound switched off and no reason written in the plan.
- A shot never proves more than happened: if the audio says it was mimed, it isn't proof.
- Captions in the language spoken, every word that matters, never over the mouth, never stacked with a callout.
- Claims, prices and offers on screen come from the brief or the client's live site, never invented.
- Nothing goes to a client, gets published or spends money without the person's yes. Delivery to a client's Drive and any message is drafted for them; they send.

## Know-how
- **Text:** Homebrew's ffmpeg has no `drawtext` and no libass, so text is drawn as PNGs by `scripts/text_png.swift` (CoreText, compiled once by `cut.py`) and laid on with `overlay`. Fonts are in `assets/fonts/` (Geist Black, Geist Bold, Playfair Display Italic); a client's own font goes in the EDL `styles` block by path.
- **Whisper is English and mishears off-camera voices.** `listen.py` uses the small English model. Check any line you caption by reading the frames; for a clearer read of a doubtful line, `setup.py --download-large` adds a bigger model (1.6 GB), which `listen.py clips --large` uses.
- **Speed:** final renders run at about 3 to 5 frames a second for a 1080x1920 from 1080p sources while other encodes run; a 30 s ad takes 3 to 5 minutes. Use `--draft` for the rough cut. Run long renders as background tasks.
- **Beat-aligned cuts:** `beats.py` measures `bpm` and `offset` from the file. Measure the whole track: it checks its two halves agree, and a short window across an intro can lock onto the wrong pulse. Give the music a `bpm` and `offset` (seconds into the file of the first downbeat) or a list of `beats`. Mark the shots whose end should land on a beat with `"snap": true`; the default snaps only those. `cut.py --beats` prints the grid against the current cuts. Snap the turn and the payoff, not every cut: `check_cut.py` warns when more than 80% of cuts sit on a beat.
- **Text timing:** tie text to a shot (`"shot": 2, "at": 0.3, "dur": 1.2`) rather than absolute seconds, so it follows the shot when a beat snap moves a cut.
- **Loudness:** two-pass `loudnorm` to -14 LUFS in linear mode, then a limiter at 4x the sample rate; `cut.py` measures the file and re-encodes with a lower ceiling if AAC pushed it over -1 dBTP. Music sits 14 dB under the clip audio by default when any shot keeps its own sound; set `music.gain_db` to change it.
- **4:5:** `reframe.py` frames each shot exactly as the 9:16 and takes a 1350-row window per shot (`y45`, default 285). Text keeps its place on the picture and is pulled 40 px inside. Keep 9:16 text between rows 330 and 1590 and the 4:5 needs no extra work.
- **Safe zones (9:16):** nothing above row 270 or below 1590 except full-screen cards; bottom 12% is Meta's button.
- **Sheets:** `sheet.sh <video> [start] [len]` writes a 40-frame sheet (times in the .txt beside it), a 10 fps strip of the hook (or any window) and frame 0. Flash frames show up in the strip, not the sheet.
- **Clip ends:** `cut.py` warns when a shot's `out` is past the picture's last frame and holds that frame, so the master never comes up short of its audio. Pull `out` back if a freeze would show.
- **Handheld and punch-ins:** `x` is one number per shot, so a drifting handheld subject walks out of the window, and a punch-in multiplies the drift. Look at that shot's window in motion (`sheet.sh <render> <shot start> <len>` gives a 10 fps strip) before trusting the framing.
- **Word times drift:** whisper's per-word times can be up to 2 s out. Before a line goes in, transcribe the slice alone; a word lost at either end means the cut is wrong.
- **Lip sync:** phone copies can carry audio about 0.1 s early. Check one clip before cutting; if the voice leads, nudge `in` on the picture, never the words.
- **The book search:** `search.py "<literal words>" --job feel|rhythm|eye --book murch|pearlman|block --k 6`, then `--show <id>` to read one note. Literal words work; questions don't.

## References (load by decision)
- `references/plan.md`: the four-beat plan, one line per beat per column, and the queries per column.
- `references/rhythm.md`: where a cut falls, holds, pattern changes, the open question.
- `references/eye.md`: what the eye goes to, text placement, safe zones, the 4:5 band.
- `references/sound.md`: the listen step, voice, music, effects, loudness, the ending.
- `references/critic.md`: the rubric, loaded only by the critic agent.
- `references/formats.md`: EDL shape, the scripts in order, outputs, where finals go.
- `references/drawings.md`: hand-drawn animation over a cut, when the brief wants it.

## Lessons
`lessons.md` holds dated lines from real reactions and results. Read it at step 0; the critic checks the cut against the last five. This folder is replaced on every update, so a client's own lessons go in that client's folder, and a lesson for everyone goes in through the repo (`CONTRIBUTING.md`).
