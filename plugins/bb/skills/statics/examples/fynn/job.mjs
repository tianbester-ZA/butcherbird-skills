// Worked example: one Fynn static (an invented sock brand) in all three sizes.
//   node <skill>/scripts/render.mjs job.mjs --out <somewhere outside the skill>
//
// The idea in six words: "warm feet by the fire". Headline "Toasty toes." fits the picture: the box sits on a hearth.
// The scene stands in for a Higgsfield generation: its label is garbled, so each size lays the real packshot over the
// box face with h.quad (label exact), and blurs the garbled small print on the box's side with h.soften.
// Every size is laid out again, not cropped: the scene moves up as the frame gets shorter, the headline shrinks,
// and the type keeps 96px clear of the box.

const SCENE = 'scenes/hearth.svg';
const BOX = 'packs/fynn-box.svg';
const FACE = [0, 0, 1200, 1160]; //                      the whole front of the real packshot (its own pixels)
const CORNERS = [440, 1620, 1080, 1610, 1090, 2210, 440, 2222]; // where the box face sits in the scene (measure.mjs grid)
const SIDE_PRINT = [1090, 1700, 44, 450]; //            garbled print on the box's side, in scene pixels
const OFFER = 'Buy one pair, get two more free, <b>worth R480.</b>';

// Draws the scene at a width and offset, fixes the label and the side print, then sets the type.
const ad = (h, { width = 1080, left = 0, top = 0 }, type) => {
  const toAd = h.at(width, left, top); //                 scene pixels -> ad pixels
  const [sx, sy, sw, sh] = toAd(SIDE_PRINT);
  return `${h.scene(SCENE, { width, left, top })}
${h.quad(BOX, FACE, toAd(CORNERS), { name: 'sock-box', filter: 'brightness(.93) sepia(.08)' })}
${h.soften(sx, sy, (SIDE_PRINT[2] * width) / 1536, (SIDE_PRINT[3] * width) / 1536, { blur: 4 })}
${h.block(type)}`;
};

export const kit = './kit';
export const out = './out';

export default {
  'toasty-toes': {
    // Stories and Reels: type from y 280, two-line headline, box low in the frame.
    '9x16': (h) => ad(h, { top: 0 }, { top: 280, logoW: 380, g1: 44, hs: 236, h: 'Toasty<br>toes.', os: 42, g2: 34, o: 'Buy one pair, get two more free,<br><b>worth R480.</b>' }),
    // Feed: the scene moves up 360px so the box still clears the type; smaller headline, offer on two lines.
    '4x5': (h) => ad(h, { top: -360 }, { top: 65, logoW: 320, g1: 38, hs: 196, h: 'Toasty<br>toes.', os: 36, g2: 24, o: 'Buy one pair, get two more free,<br><b>worth R480.</b>' }),
    // Square: its own layout. One-line headline and offer so the box fits under them.
    '1x1': (h) => ad(h, { top: -719 }, { top: 50, logoW: 230, g1: 28, hs: 112, h: 'Toasty toes.', os: 30, g2: 16, o: OFFER }),
  },
};
