#!/usr/bin/env python3
"""beats.py: tempo, beat offset and the energy map of a music file, for the EDL's music block.

    python3 beats.py <music file> [--from 0] [--to 120] [--bpm-range 60 180] [--json]

Prints the tempo (BPM), the offset of the first beat in file seconds (what the EDL's
"offset" wants), the runner-up tempos (half and double time are the usual mix-ups),
and the loudness per 2 s with the low end, so you can see the intro, the build, the
drop and the break and pick "music.start" by ear and eye.

Reads the file through ffmpeg (mono, 11,025 Hz). Python 3 stdlib; uses numpy when it
is installed, only for speed. The offset is a beat, not necessarily bar one: if the
cut needs the downbeat, look at the energy map or listen, and add 60/bpm per beat.
"""
import array, json, math, subprocess, sys

SR, HOP = 11025, 128            # about 86 envelope frames a second, 11.6 ms each
FPS = SR / HOP

try:
    import numpy as np
except ImportError:
    np = None


def decode(path, t0, t1):
    args = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(t0)]
    if t1:
        args += ["-t", str(t1 - t0)]
    args += ["-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    r = subprocess.run(args, capture_output=True)
    if r.returncode or not r.stdout:
        sys.exit(f"beats.py: cannot decode {path}: {r.stderr.decode(errors='replace').strip()}")
    a = array.array("h")
    a.frombytes(r.stdout[: len(r.stdout) // 2 * 2])
    return a


def envelopes(a):
    """RMS per hop for the full band and a one-pole low band (under about 150 Hz: kick and bass)."""
    n = len(a) // HOP
    alpha = 2 * math.pi * 150 / SR
    alpha = alpha / (alpha + 1)
    if np is not None:
        x = np.frombuffer(a, dtype=np.int16)[: n * HOP].astype(np.float64)
        rms = np.sqrt((x.reshape(n, HOP) ** 2).mean(axis=1))
        lp = np.empty_like(x)        # the one-pole filter is a loop either way; do it in chunks of Python
        acc = 0.0
        for i, v in enumerate(x.tolist()):
            acc += alpha * (v - acc)
            lp[i] = acc
        low = np.sqrt((lp.reshape(n, HOP) ** 2).mean(axis=1))
        return rms.tolist(), low.tolist()
    rms, low, acc = [], [], 0.0
    for i in range(n):
        s = sl = 0.0
        for v in a[i * HOP:(i + 1) * HOP]:
            acc += alpha * (v - acc)
            s += v * v
            sl += acc * acc
        rms.append(math.sqrt(s / HOP))
        low.append(math.sqrt(sl / HOP))
    return rms, low


def flux(env):
    """Rises in log energy: where something hits."""
    le = [math.log(1e-3 + r) for r in env]
    return [0.0] + [max(0.0, le[i] - le[i - 1]) for i in range(1, len(le))]


def autocorr(o, lo, hi):
    """Score each tempo from lo to hi BPM (0.5 BPM steps) by how well the onsets repeat at that period."""
    m = sum(o) / len(o)
    o = [v - m for v in o]
    n = len(o)
    if np is not None:
        ov = np.array(o)
    out = []
    for b2 in range(int(lo * 2), int(hi * 2) + 1):
        bpm = b2 / 2
        lag = FPS * 60 / bpm
        L, f = int(lag), lag - int(lag)
        if L + 2 >= n:
            continue
        if np is not None:
            s = float(np.dot(ov[: n - L - 1], (1 - f) * ov[L:n - 1] + f * ov[L + 1:n]))
        else:
            s = sum(o[i] * ((1 - f) * o[i + L] + f * o[i + L + 1]) for i in range(0, n - L - 1))
        out.append((s, bpm))
    return sorted(out, reverse=True)


def comb(o, bpm, span=1.5, step=0.05, phases=80):
    """Fine tempo and phase: the grid whose ticks sit on the most onset energy, scored as contrast
    (best phase against the average phase), so a slow grid that happens to catch a few loud hits
    doesn't beat the real pulse."""
    n = len(o)
    dur = n / FPS
    peak = [max(o[max(0, i - 1):i + 2]) for i in range(n)]
    best = (-1, bpm, 0.0)
    b = bpm - span
    while b <= bpm + span + 1e-9:
        P = 60 / b
        scores = []
        for ph in range(phases):
            off = P * ph / phases
            t, s, k = off, 0.0, 0
            while t < dur:
                s += peak[int(t * FPS)]
                k += 1
                t += P
            scores.append((s / k if k else 0.0, off))
        top, off = max(scores)
        mean = sum(x for x, _ in scores) / len(scores) or 1e-9
        if top / mean > best[0]:
            best = (top / mean, b, off)
        b += step
    return best


def estimate(o, ranked, lo, hi):
    """Half and double time score almost alike, so fit the top tempos and their halves and doubles,
    then lean towards the range people tap along to (about 70 to 140 BPM), so 84 doesn't come back as 168."""
    peaks = []
    for _, b in ranked:
        if all(abs(b - x) > 3 for x in peaks):
            peaks.append(b)
        if len(peaks) == 3:
            break
    cands = sorted({round(x * 2) / 2 for b in peaks for x in (b, b / 2, b * 2) if lo <= x <= hi})
    prior = lambda b: math.exp(-0.5 * (math.log2(b / 100.0) / 0.6) ** 2)
    return max((comb(o, c) for c in cands), key=lambda f: f[0] * prior(f[1]))


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    path = argv[0]
    opt = lambda k, d: float(argv[argv.index(k) + 1]) if k in argv else d
    t0, t1 = opt("--from", 0.0), opt("--to", 0.0)
    lo, hi = (float(argv[argv.index("--bpm-range") + 1]), float(argv[argv.index("--bpm-range") + 2])) \
        if "--bpm-range" in argv else (60.0, 180.0)
    a = decode(path, t0, t1)
    rms, low = envelopes(a)
    o = [x + y for x, y in zip(flux(rms), flux(low))]
    ranked = autocorr(o, lo, hi)
    if not ranked:
        sys.exit("beats.py: the file is too short to measure a tempo")
    score, bpm, off = estimate(o, ranked, lo, hi)
    # Self-check: the two halves should agree. A short window across an intro or a build can lock
    # onto a wrong pulse; when the halves disagree, measure the whole track and trust your ear.
    steady = None
    half = len(o) // 2
    if half / FPS >= 10:
        bs = []
        for part in (o[:half], o[half:]):
            r = autocorr(part, lo, hi)
            bs.append(estimate(part, r, lo, hi)[1] if r else 0)
        steady = all(abs(x - bpm) <= 1.5 for x in bs), [round(x, 1) for x in bs]
    bpm = round(bpm, 2)
    off = round(t0 + off, 3)
    others = []
    for s, b in ranked[1:]:
        if all(abs(b - x) > 3 for x in [ranked[0][1]] + others):
            others.append(b)
        if len(others) == 3:
            break
    energy = []
    for t in range(0, int(len(rms) / FPS), 2):
        seg, sl = rms[int(t * FPS):int((t + 2) * FPS)], low[int(t * FPS):int((t + 2) * FPS)]
        if seg:
            energy.append((round(t0 + t, 1), round(20 * math.log10(sum(seg) / len(seg) / 32768 + 1e-9), 1),
                           round(20 * math.log10(sum(sl) / len(sl) / 32768 + 1e-9), 1)))
    if "--json" in argv:
        print(json.dumps(dict(bpm=bpm, offset=off, others=others, steady=steady and steady[0], energy=energy)))
        return
    print(f"tempo {bpm} BPM, first beat at {off:.3f} s (file time), beat every {60 / bpm:.3f} s")
    print(f"runners-up: {', '.join(f'{b:g}' for b in others)} BPM (check half / double time by ear)")
    if steady is not None:
        print(f"halves: {steady[1][0]:g} and {steady[1][1]:g} BPM, "
              + ("steady" if steady[0] else "they disagree: measure the whole track, or listen and tap it"))
    print(f'EDL: "music": {{"bpm": {bpm}, "offset": {off}, ...}}')
    print("\nloudness per 2 s (dBFS, full band | low end): look for the build, the drop and the break")
    top = max(e[1] for e in energy) if energy else 0
    for t, db, dbl in energy:
        bar = "#" * max(0, int((db - top + 30) / 1.5))
        print(f"{t:7.1f}s {db:6.1f} | {dbl:6.1f}  {bar}")
    note = "; under 60 s is less sure, the whole track is the default for a reason" if len(a) / SR < 60 else ""
    print(f"\n({'numpy' if np is not None else 'stdlib only'}; {len(a) / SR:.0f} s analysed{note})")


if __name__ == "__main__":
    main(sys.argv[1:])
