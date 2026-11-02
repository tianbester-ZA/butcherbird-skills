# Drawn animation over a cut

For drawings that react to the jokes (an 80s anime line beat marker lines when we tried both). Needs Node 22 or newer and Google Chrome; `setup.py` lists them as optional.

`scripts/drawn/` is a kit:
- `anim.html` holds the hand-drawing functions (wobbly lines with line boil, hearts, sweat drops, gloom lines, focus lines, bursts, brackets) and a small example scene. Every drawing takes its time from `t`, and the page exposes `window.draw(t, mode)`.
- `render.js` steps the page in headless Chrome to transparent PNG frames: `node render.js <page.html> <frames dir> <fps> <seconds> [916|45]`.
- `composite.sh <clean.mp4> <frames dir> <out.mp4>` lays them over the clean master with the audio untouched.
- `track.py <video> --min 150,0,60 --max 255,110,255` prints where a coloured thing sits, frame by frame, so drawings can follow it with `kf()`. Run it with `PY`.

Copy `anim.html` into the job folder, rewrite `scene()` for the new footage, and time every gag to a spoken word or a bar of the song. Use the client's colours. Keep drawings off faces and captions, leave some shots empty so the moments pop, and read the frames around each gag at full size before calling it done.
