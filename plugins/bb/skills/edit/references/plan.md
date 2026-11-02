# The edit plan

The plan is the edit on one page before any render: four beats, four columns, one line each, each line with the passage that made the call. It is what the critic judges the cut against and what the lessons loop reads when the numbers come in.

## The four beats of a reel
- **Hook** (0 to about 3 s): stops a stranger with the sound off. Opens one question.
- **Turn** (the middle): the problem becomes the answer, or the build becomes the reveal. The second-biggest interrupt goes here.
- **Payoff**: the question answered on screen: the product working, the result, the reaction.
- **Close**: calmer, the ask plain, the ending allowed to land.

A 15 s cut can merge turn and payoff. A 60 s cut can repeat turn and payoff once, but the hook's question still closes only at the last payoff.

## The four columns
| Column | The question | Search |
|---|---|---|
| Feel | What should the viewer feel at the end of this beat? One word. | `--job feel` |
| Rhythm | How fast does it cut, where is the hold, which cut lands on a beat or a word? | `--job rhythm` |
| Eye | What is the one thing to look at in each shot, and where is it in the frame? | `--job eye` |
| Sound | Voice, music, effect: what carries this beat and what sits under it? | `--job rhythm` or plain words |

## Format of `job/plan.md`
```
Vibe: <one line, the person's own words>
Length: <s>  Music: <track, start s, bpm/offset or beats>

## Hook (0.0 to 2.4)
Feel: curious. Close on the shoes mid-stride, no face yet. (pearlman-0132: question with something at stake)
Rhythm: one shot, cut on the foot landing, not the beat. (murch-0050)
Eye: the white shoe is the brightest moving thing, lower third. (block-0113)
Sound: trail crunch up, music in under it. (pearlman-0118)
```
One line per column per beat, a passage id at the end of each. Ids come from `search.py` output; read the passage with `--show` before you cite it.

## Queries that work (BM25, literal words)
- Feel: `emotion audience remember feel`, `tension release cycle`, `intensity decrease resolution`
- Rhythm: `cut point blink thought`, `shot duration relative`, `cutting before peak content`, `regular irregular rhythm`
- Eye: `movement attention first`, `point of attention cut`, `watch without sound`, `zoom flat`
- Sound: `slow motion emotional`, `pulse accent movement`

Start from the card passages (`murch-0050`, `murch-0054`, `pearlman-0060`, `pearlman-0132`, `block-0113`, `block-0150`) and add what the search turns up for this footage. Two to four fresh passages per job is plenty.
