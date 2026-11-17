# Fynn: a worked example

Fynn is an invented sock brand. This folder is a complete, tiny job: one ad in all three sizes, made the way a real one is.

- `kit/` the brand kit: `kit.json`, two logo colours drawn as shapes, a flat packshot of the box, and one scene. Its fonts point at the open ones that ship with `/bb:edit`, so this copy only works inside the skill. A real kit lives in the client's folder, never here.
- `kit/scenes/hearth.svg` stands in for a Higgsfield generation (1536 x 2752). Like a real one, its label is garbled ("FYMN", "MERNIO HIKNG SOKCS"), and so is the print on the box's side.
- `job.mjs` the ad. Read its comments: it lays the real packshot over the garbled box with `h.quad`, blurs the side print with `h.soften`, and re-lays out the type and scene for each size.

**Don't copy this folder by hand.** Make a practice job from it instead: it copies the kit and its fonts so everything works in your own folder.

```
NODE scripts/new-job.mjs ~/Desktop/fynn-practice
```

Then follow the commands it prints, or ask Claude to run them (`NODE` is the start of the line the setup check prints when it says READY; `scripts/` is the skill's scripts folder). For a client job, add `--kit <the client's kit folder>`.
