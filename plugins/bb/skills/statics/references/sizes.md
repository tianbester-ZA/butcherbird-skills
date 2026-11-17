# Sizes

Every ad comes in three sizes, each laid out again from the same scene, never cropped. A crop cuts the headline or the product; a re-layout moves the scene and resizes the type so both fit.

| Size | Pixels | Where it runs | Safe area for text and logo |
|---|---|---|---|
| 9:16 | 1080 x 1920 | Stories and Reels | y 280 to 1250, 65px from each side |
| 4:5 | 1080 x 1350 | Feed | 65px from every edge |
| 1:1 | 1080 x 1080 | Right column, search, some placements | 50px from every edge |
| Carousel cards | 1080 x 1350 (4:5) | Feed carousels | as 4:5 |

**Why the 9:16 safe area is so tall and narrow.** On Stories and Reels the profile name covers the top, and the caption, buttons and "Shop now" cover the bottom fifth. Anything readable outside y 280 to 1250 gets hidden on someone's phone. Products and pictures can fill the whole frame; only readable things stay inside.

## How to re-lay out
Start from the 9:16, then for each smaller size:

1. **Move the scene, don't shrink it.** Keep it 1080 wide and slide it up (`h.scene(src, { top: -360 })`), so the product stays big and the empty space at the top shrinks to fit the type.
2. **Shrink the type to the frame** (the `h.block` settings are in the table in `workflow.md`, step 5). A two-line headline often stays two lines on 4:5 at a smaller size. On 1:1 it usually goes to one line, and the offer to one line.
3. **Keep the 96px gap.** The gate measures it. If the product won't fit under the type, make the type smaller, move the scene, or lay out the square differently (type beside the product, the product smaller in the room).
4. **Move every fix with the scene.** `h.at(width, left, top)` maps scene pixels to ad pixels, so corners for `h.quad` and boxes for `h.soften` follow the scene automatically. Always go through it; never type ad pixels for scene features.
5. **Check the label again** at the new size with `measure.mjs crop`.

The Fynn job does exactly this: the scene sits at top 0 on 9:16, moves up 360px on 4:5 and 719px on 1:1.

## Carousels
A carousel is a run of 4:5 cards, one idea per card, read left to right. Name the ad ids so they sort in order (`car-1-cover`, `car-2-entry`, ...). A good shape for a tiered offer: a cover, one card per tier ("spend this, receive these"), and a closing card that repeats the best offer. Every card still passes the gate on its own.
