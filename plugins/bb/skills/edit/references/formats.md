# Formats: footage in, masters out

## The scripts in order
```
scripts/probe.sh <footage dir> > job/footage-log.md        # facts per clip; HDR flagged
scripts/proxies.sh job/px <clips...>                        # SDR working copies (avconvert for HDR)
PY scripts/beats.py <music file>                           # bpm, offset, loudness map
PY scripts/cut.py job/edl.json --beats                     # beat grid against the cuts
PY scripts/listen.py clips <footage> --out job/sound       # the real sound, read before planning
PY scripts/listen.py song <music file>                     # beats, energy, sections, words
PY scripts/mix.py job/edl.json                             # the sound; writes renders/<slug>-mix.wav and stems
PY scripts/cut.py job/edl.json --draft                     # rough 9:16
scripts/sheet.sh job/renders/<slug>-9x16.mp4               # sheet, hook strip, frame 0
PY scripts/cut.py job/edl.json                             # final 9:16
PY scripts/reframe.py job/edl.json                         # final 4:5, same audio
PY scripts/check_cut.py job/renders/<slug>-9x16.mp4        # and again on -4x5.mp4
PY scripts/listen.py cut job/renders/<slug>-9x16.mp4 --manifest job/renders/<slug>-9x16.json --sounds job/sound/sounds.json --out job/listen
```
`PY` and `scripts/` mean the full paths given in SKILL.md. Paths inside the EDL are relative to the EDL file (or absolute). Renders go to `out_dir` (default `renders/`) beside it. Source footage is only read, so it can sit on any drive.

## edl.json
```json
{
  "slug": "fynn-river-test-main",
  "fps": 30,
  "out_dir": "renders",
  "loudness": -14,
  "accent_color": "#EE7631",
  "music": {
    "file": "music/track.mp3",
    "start": 20.0,
    "bpm": 99, "offset": 0.0,
    "snap": "marked", "snap_window": 0.25,
    "gain_db": -14, "fade_in": 0.1, "fade_out": 1.2
  },
  "styles": { "caption": { "font": "fonts/ClientFont-Bold.ttf", "size": 72 } },
  "shots": [
    { "clip": "px/IMG_0412.mp4", "in": 2.0, "out": 4.2, "note": "hook: box lands",
      "x": 0.5, "y": 0.5, "y45": 285, "audio": true, "gain_db": 0, "snap": true },
    { "clip": "px/IMG_0413.mp4", "in": 6.0, "out": 7.5, "speed": 0.5,
      "punch": 1.12, "focus": [0.6, 0.7], "flash": 2 }
  ],
  "text": [
    { "text": "Wait for it", "shot": 0, "at": 0.1, "dur": 1.6, "style": "caption", "accent": ["wait"] },
    { "text": "Free shipping over R700", "start": 9.0, "end": 11.0, "style": "callout", "y": 430, "y45": 200 }
  ]
}
```

**Shot keys:** `clip`, `in`, `out` (seconds in the clip) are required. `speed` (default 1; any other speed mutes the shot's own audio). `audio` (keep the clip's sound, default false). `gain_db`. `x`, `y` (0 to 1: where the 9:16 window sits on a wider or taller source). `punch` (`true` = 1.08, or a number; a still punch-in, for the product) with `focus` `[x, y]` (0 to 1). `flash` (frames of `flash_color`, default white, at the start of the shot; the only transition besides a cut). `snap` (land this shot's end on the nearest beat within `snap_window`). `y45` (top row of the 4:5 window, default 285). `note` (the beat, for the manifest and the critic). `allow_hdr` (don't).

**Text keys:** `text`; timing either `shot` + `at` (+ `dur`, default to the end of the shot) or `start` + `end` in seconds. `style`: `caption` (Geist Black caps 76, under the chin, y 1250), `title` (110, y 640), `callout` (Bone plate, black caps 56, y 430), `aside` (Playfair italic 84, y 1120), `card` (full-screen, skips the safe-zone check). `y` is the centre row on the 9:16. `y45` sets the centre row on the 4:5 directly; without it the text keeps its place on the picture. `accent` lists words drawn in `accent_color`. `x` (centre column in pixels) is optional. `\n` in `text` breaks the line. `pair: true` marks a designed pair (a small label over a hero line, a headline with the handle) so the stacking check lets it touch; the stacking rule is about the same words said twice. Style keys (`font`, `size`, `color`, `plate`, `shadow`, `max_width`, `stroke`, `stroke_color`, `pad`, `leading`, `tracking`, `upper`) can be set per style in `styles` or per item for `size`, `color`, `font`, `plate`, `max_width`, `shadow`. The default shadow is black; for a brand that bans black, set `shadow` to null or a `shadow_color` in the style.

**Extra shot keys:** `look` (ffmpeg filter, or a top-level `look`; only when the brief asks), `flash_curve` (white per frame, e.g. `[1, 1, .8, .5, .25, .1]`), `off_beat` (why this cut is off the beat). **Extra text keys:** `rotate` (degrees), `slap` (a hard pop: two big frames, one small). **Sound:** `sound.nat`, `sound.sfx`, `sound.music_gain_db` (see `references/sound.md`). `mix.py` writes `mix_file` back into the EDL; `cut.py` then uses that mix instead of building its own.

**Music keys:** `file`, `start` (seconds into the track), `gain_db` (default -14 when any shot keeps its sound, else 0), `fade_in`, `fade_out`, `at` (timeline second it comes in), `segments` (`[[file_s, file_e], ...]`, joined on downbeats). Beats either `bpm` + `offset` (seconds into the file of a beat; `beats.py` prints both) or `beats` (a list of times in the file). `snap`: `marked` (default: only shots with `"snap": true`), `all`, or `none`.

## What comes out
- `renders/<slug>-9x16.mp4`: 1080x1920, 30 fps, H.264 yuv420p tagged BT.709, AAC 48 kHz 192k, -14 LUFS, faststart.
- `renders/<slug>-4x5.mp4`: 1080x1350, same edit, the 9:16's audio stream copied.
- `<stem>.json` beside each: shots with their timeline times, text boxes, beat snaps, warnings, loudness. `check_cut.py` reads it.
- `sheet.sh` adds `<stem>-sheet.jpg` + `.txt`, `<stem>-strip.jpg`, `<stem>-frame0.png`.

## Footage
- HDR iPhone footage goes through `proxies.sh` (avconvert, then H.264). `cut.py` refuses HDR clips.
- Rough on proxies, final from the originals. Proxies are 1080 on the short side, and a 9:16 window on a landscape source is only about a third of its width, so it goes soft and two people side by side rarely both fit.
- Proxies are 1080 on the short side. For a 4K source, cut the rough on proxies, then make full-res SDR copies the same way and swap the `clip` paths for the final; `in`/`out` stay the same.
- Frame rates mix freely: every shot is resampled to the EDL's `fps`.
- Check lip sync on one clip first; phone copies can lead the picture by about 0.1 s.
- Some files carry audio past the last picture frame; `cut.py` cuts against the picture's own end and warns if `out` overshoots it.

## Delivery
- Finals: `final/<slug>-9x16.mp4` and `-4x5.mp4`, plus `README.txt` (what it is, length, music track and source, date, the EDL path). For UGC: main, B-roll and a 40 s cut, each in both shapes.
- Client files go into the client's own Drive folder under `Edited/`, one folder per version. Draft the message for the person running this; they send it.
