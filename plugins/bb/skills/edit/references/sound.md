# Sound

## Listen first (`scripts/listen.py`)
Nobody here can hear, so measure everything that can be measured, and say that it's measured.
- `listen.py clips <footage dir> --out job/sound`: every clip's words, laughs, shouts, steps and peaks (`sounds.md`). Read it before planning.
- `listen.py song <track>`: beats, downbeats, energy sections, biggest rises, where the song really ends, its words with times. Lyrics are for timing and meaning; don't reprint them.
- `listen.py cut <video> --manifest <stem>.json --sounds job/sound/sounds.json --out job/listen`: every cut against the beat and the sung words, LUFS, true peak, clipping, the start and the end, real moments left switched off, and a waveform picture. Read the picture.
What it found on our first jobs: all 16 shots of one reel silent over 17 live moments of talk; a 1.2 s fade over the song's own last hits; a shot's "application" being mimed.

Rules of thumb from it:
- The song's biggest rise goes on the picture's biggest moment. Find it in `song`, put it there, and build backwards.
- Lay a line in a song's own gap and let the next hit answer it.
- Start a song between sung lines, under the tail of the last sound, full on its downbeat with the picture cut there. Cut bars only on downbeats (`music.segments`).
- If the track has an ending, end on it, no fade. Then let one real sound be last.
- Off-beat cuts are fine when a voice or a move owns them. Write why in the shot (`off_beat`): the report shows it.

## Building the mix (`scripts/mix.py`)
`sound.nat` lays any clip's real sound at any time, independent of the picture, so it can run over a cut; `level` sets its RMS, `duck` pulls the music down under it. `sound.sfx` does the same for effects. The mix log gives each voice's level over the music: aim for about 8 to 12 dB over. Duck the music, not the voice.

## Voice first
- Raw, close phone sound. No denoise: Tian (who owns the taste here) heard it as "into a bottle, mic far away". If the room is noisy, a gentle 80 Hz high-pass is the most we do.
- Never slow or speed a voice. It sounded wrong every time (pearlman-0197 explains why: slow motion adds weight the line doesn't want).
- Keep the sign-off. Cuts that dropped the last line ("Let's talk. Peace.") felt cut off; hold to the exit point where the idea is finished (murch-0054).

## Music under, not over
- Modern, soft, slightly hip hop is the taste for Butcherbird's own work; a client's brand may differ (check its notes).
- About 11 to 14 dB under the voice. `cut.py` puts it 14 dB under when any shot keeps its own sound; change with `music.gain_db`.
- The music can lift on a full-screen beat and the close, and it runs through the end card, then fades (`music.fade_out`, default 1 s).
- Start the track where it's already moving (`music.start`), not on a slow intro, unless the hook wants the quiet.
- Lyric tracks fight a voice. Under talking, pick an instrumental section or drop the level further.

## Effects on the movement
- Tactile and quiet: a click on a card, a soft whoosh on a move, a pop on the product. Tied to the movement in the picture, never louder than the voice (pearlman-0118).
- Synthesised beeps read cheap. One good effect beats five.
- Effects go in `sound.sfx` (see `mix.py`). Check the level in the stem: an effect 25 dB under the mix isn't there.

A strong bass: set `sound.duck_low` (0.3 works) so the mids duck the full amount and the bass line keeps going, and check the speech-band number in the mix log, not just the overall one. `music.segments` takes a third value, a tail in seconds, so a sung word can ring past a join.

## Loudness
- Masters at -14 LUFS integrated, true peak -1 dBTP or lower. `cut.py` does a two-pass `loudnorm` (linear) on the whole mix, then a limiter at 192 kHz so peaks between samples are caught, then measures the AAC file and retries with a lower ceiling if it's still over. Linear loudnorm alone can't promise the ceiling, and AAC adds its own overshoot. `check_cut.py` reads it back with `ebur128`.
- The last 0.1 s should be quiet. If `check_cut.py` says the tail is loud, the ending is chopped: lengthen the last shot or the music fade.

## Clicks at cuts
`cut.py` puts a 15 ms fade at both ends of each shot's own audio, so hard cuts don't click. If you hear one anyway, the cut is mid-word: move it to the end of the thought.
