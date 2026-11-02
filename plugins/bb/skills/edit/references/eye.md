# The eye: what gets looked at

## One thing per shot
- The eye goes to movement first, then to the brightest part of the frame (block-0113). Make sure that thing is what the shot is about: the product, the hand, the face reacting.
- Before each cut, ask what the viewer is thinking and where they're looking, and put the next thing there (murch-0022).
- Not sure? Watch it with the sound off and notice where your own eye goes (block-0126). Do this once on every rough cut.
- Phones are small and busy, which is why reels cut fast; earn each cut and keep each picture readable (murch-0103).

## Across the cut
- Keep the subject in about the same part of the frame from shot to shot. A jump across the frame is a jolt; use it only when you want one, at the hook or the turn (block-0124).
- In the EDL, `x` and `y` (0 to 1) pick where the 9:16 window sits on a landscape or larger source. Line the subject up between neighbouring shots.

## Framing and push-ins
- Footage stays as filmed. Still framing; a gentle punch-in only on the product (`"punch": 1.08` to `1.15`, `"focus": [x, y]` on the product). No moving zooms: a zoom flattens the picture and reads as cheap (block-0032).
- Never mirror-fill, stretch, blur-fill or fade to black to make room for text. Move the text, not the footage.
- Don't lean on this month's effect (block-0177).

## Text
- Captions just under the chin, or in clear sky or floor; never over a mouth, eyes or forehead.
- Callouts and captions never stack. While a callout says the words, the caption for those words drops out.
- Hard pop on the spoken word (within about 0.1 s), no easing in. Up long enough to read: about three words a second, never under 0.6 s.
- Big and bright: captions 76 px Geist Black caps by default, nothing under 36 px. One accent word.
- Pop-ups come and go. No permanent bar or panel.
- Match the text to the video. On people talking and laughing, plain small captions (about 40 px, sentence case, no box, a soft shadow via `soft_shadow`) can belong better than plates: Tian called big plates on a talking reel "tacky". Big text is the default for ads, not a law.
- The close gets calmer: fewer elements, the ask clearest of the whole cut (block-0150).

## Safe zones
- 9:16 (1080x1920): text between rows 270 and 1590, 60 px from the sides; bottom 12% is Meta's button. Full-screen cards are the exception.
- Keep text between rows 330 and 1590 and it survives Meta's 4:5 centre crop too.
- 4:5 (1080x1350): every caption 24 px inside the frame at least (`reframe.py` keeps 40), hair 30 px under the top, chin and mouth never cut unless the raw already is.
- `y` on a text item is the centre row of the text box on the 9:16. `check_cut.py` reads the real box sizes from the manifest.

## The 4:5 window
`y45` on a shot is the top row of the 1350-row window on the 1920 frame. 285 is the centre; lower numbers keep more sky and head, higher keep more floor and product. Set it per shot so the subject sits where it did on the 9:16.
