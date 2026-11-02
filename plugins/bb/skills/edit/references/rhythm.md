# Rhythm: where a cut falls and where it holds

## Where the cut falls
- **At the end of a thought.** In a talking shot the cut belongs where the idea has landed, which is the end of the thought, not the end of the breath (murch-0050). Cutting earlier steals the line; later leaves dead air.
- **On a movement or a word.** Blinks, glances, a foot landing, a hand lifting the product: mark them on the footage log first; they are the cut points (pearlman-0118). One frame either side changes the meaning, so check the frame before and after (pearlman-0059).
- **At one of the shot's few good exits.** Each shot has only a few clean exit points. Pick the one that gives the next thought; never cut halfway between two (murch-0054).
- **Just before they ask.** Give the next shot a moment before the viewer would want it (murch-0056). Late feels slow; early feels nervous.

## Beats and the music
Snap a cut to the music only where the cut and the beat agree: the turn, the payoff, a reveal. A cut on every beat reads as a grid, not as an edit (pearlman card, "what it changes"). In the EDL that means `"snap": true` on two or three shots, not all of them. `check_cut.py` warns when more than 80% of cuts land on a beat.

## Holds
- A shot only feels long next to quicker ones (pearlman-0060). Put the hold (the reveal, the face reading the line, the product in hand) after two or three short shots.
- At least one held shot per cut, roughly twice the median shot length. `check_cut.py` flags a cut with none.
- Fewer cuts, each a decision (murch-0015). A cut every second is a hand on the neck (murch-0016).
- More cuts can feel slower: a busy single shot is often faster than the same thing chopped up (pearlman-0064).

## Pattern that changes
- A steady tempo calms; break it where you want the viewer to feel something (block-0138). Plan the reel as build and release, not one speed (pearlman-0251).
- Hard contrast at the hook and the turn, not on every cut (pearlman-0161). All contrast tires; all sameness bores (block-0013).
- House style asks for something new on screen about every 6 s. Treat that as a check, not a timer: a new thing should be a decision (murch-0015).

## The open question
- The hook opens a question with something at stake (pearlman-0132). Don't answer it in the turn; the payoff answers it.
- Cutting just before the viewer has fully read a shot adds edge. Use it in the hook for energy; never on the offer or the price (pearlman-0236).

## Speed changes
- Slow motion adds weight; use it on the product or a moment, never on a voice (pearlman-0197). `cut.py` mutes the shot's own audio at any speed other than 1.
- Speed ramps are a change of feeling, not decoration. One per cut at most.

## Flashes
A flash is the one transition besides a cut, and it only reads as intended when it's tied to something: a hit in the music, a camera click, a reveal. A pale or coloured flash with nothing behind it reads as a glitch; a blind judge called one edit's cream flash exactly that. White, two or three frames, on a beat or a movement, and check it in the strip at 10 fps, not on the sheet.

## Re-cutting after the numbers
Hook rate under about 20%: re-cut the opening (first frame and first line), keep the body. Hold rate under about 40%: re-cut the turn, keep the hook. Both healthy and no sales: it's the offer or the close, not the edit.
