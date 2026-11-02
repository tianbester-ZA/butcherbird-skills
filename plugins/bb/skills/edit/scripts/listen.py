#!/usr/bin/env python3
"""listen.py: the sound check for a cut. It can't hear; it measures everything that can be measured.

    PY listen.py song  <music file> --out DIR
        beat and downbeat grid, energy curve, sections, biggest moments, the song's words with times.
    PY listen.py clips <clip or dir> ... --out DIR [--large]
        the natural sound in raw footage: speech (whisper), laughs, shouts, wind, steps (YAMNet), level peaks.
    PY listen.py cut   <video.mp4> --manifest <stem>.json --out DIR [--sounds sounds.json]
        the finished cut: every cut against the beat, the words, the song's biggest moment against the
        picture's, what real sound is in it, LUFS, true peak, clipping, abrupt start and end, whether the
        music ends on a phrase or is just faded. Writes <stem>-listen.md, .json and a waveform .png.
        Without a manifest, pass --music FILE --music-start S, or it beat-tracks the finished audio itself.

PY is the Python that setup.py builds. It holds numpy, scipy, librosa, soundfile, matplotlib and ai-edge-litert.
It also needs ffmpeg, whisper-cli and the models setup.py downloads (ggml-small.en.bin, yamnet.tflite, yamnet_labels.txt).
Song words stay in the JSON as working data: they are for timing, not for reprinting.
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbenv  # noqa: E402
bbenv.need("numpy")
import numpy as np  # noqa: E402

MODEL = bbenv.model("ggml-small.en.bin")
LARGE_MODEL = bbenv.model("ggml-large-v3-turbo.bin")
YAMNET = bbenv.model("yamnet.tflite")
YAMNET_LABELS = bbenv.model("yamnet_labels.txt")
CACHE = os.path.join(bbenv.data_dir(), "cache", "listen")
WHISPER = {"model": MODEL, "lang": "en"}   # --large swaps in the bigger model, which also hears other languages
SR = 22050


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def decode(path, sr=SR, ch=1, t0=None, dur=None):
    a = ["ffmpeg", "-nostdin", "-v", "error"]
    if t0 is not None:
        a += ["-ss", str(t0)]
    if dur is not None:
        a += ["-t", str(dur)]
    a += ["-i", path, "-vn", "-ac", str(ch), "-ar", str(sr), "-f", "f32le", "-"]
    r = subprocess.run(a, capture_output=True)
    if r.returncode:
        sys.exit(f"listen.py: cannot decode {path}: {r.stderr.decode(errors='replace')[:300]}")
    x = np.frombuffer(r.stdout, dtype=np.float32)
    return x if ch == 1 else x.reshape(-1, ch)


def db(x):
    return float(20 * np.log10(max(float(x), 1e-9)))


# ---------- whisper ----------
def whisper_words(path, t0=None, dur=None, band=None):
    """Word timings from whisper-cli. band=(lo,hi) filters to the voice range first (for songs)."""
    with tempfile.TemporaryDirectory(prefix="listen-") as tmp:
        wav = os.path.join(tmp, "a.wav")
        a = ["ffmpeg", "-nostdin", "-v", "error", "-y"]
        if t0 is not None:
            a += ["-ss", str(t0)]
        if dur is not None:
            a += ["-t", str(dur)]
        a += ["-i", path, "-vn", "-ac", "1", "-ar", "16000"]
        if band:
            a += ["-af", f"highpass=f={band[0]},lowpass=f={band[1]}"]
        a += [wav]
        subprocess.run(a, check=True)
        of = os.path.join(tmp, "o")
        bbenv.need_file(WHISPER["model"])
        r = run(["whisper-cli", "-m", WHISPER["model"], "-f", wav, "-l", WHISPER["lang"], "-ml", "1", "-sow", "-oj", "-of", of, "-np"])
        if r.returncode or not os.path.exists(of + ".json"):
            return []
        with open(of + ".json", errors="replace") as f:
            j = json.load(f)
    words = []
    for seg in j.get("transcription", []):
        w = seg.get("text", "").strip()
        if not w:
            continue
        s, e = seg["offsets"]["from"] / 1000, seg["offsets"]["to"] / 1000
        # whisper stretches a word up to the next one; cap it so gaps between sung lines survive
        e = min(e, s + 0.1 + 0.09 * len(w))
        words.append(dict(w=w, s=round(s, 2), e=round(e, 2)))
    return words


def group_lines(words, gap=0.45):
    lines, cur = [], []
    for w in words:
        if cur and w["s"] - cur[-1]["e"] > gap:
            lines.append(cur)
            cur = []
        cur.append(w)
    if cur:
        lines.append(cur)
    return [dict(s=l[0]["s"], e=l[-1]["e"], n=len(l), text=" ".join(x["w"] for x in l)) for l in lines]


# ---------- the song ----------
def song_map(path, out=None, force=False):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1(f"{os.path.abspath(path)}:{os.path.getsize(path)}".encode()).hexdigest()[:12]
    cache = os.path.join(CACHE, f"song-{key}.json")
    if os.path.exists(cache) and not force:
        return json.load(open(cache))
    import librosa
    y = decode(path)
    dur = len(y) / SR
    hop = 256
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=hop, aggregate=np.median)
    tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=SR, hop_length=hop, units="time", tightness=120)
    tempo = float(np.atleast_1d(tempo)[0])
    if tempo <= 0:   # no pulse found (ambient, a drone): keep a nominal grid, and the agreement check below won't trust it
        tempo, beats = 120.0, np.array([])
    # A straight grid fitted to the onset envelope: real records rarely drift, and this catches octave slips.
    t_env = librosa.frames_to_time(np.arange(len(env)), sr=SR, hop_length=hop)
    best = (-1, tempo, 0.0)
    for bpm in np.arange(tempo * 0.97, tempo * 1.03, 0.05):
        step = 60 / bpm
        for off in np.arange(0, step, 0.01):
            idx = np.searchsorted(t_env, np.arange(off, dur, step))
            idx = idx[idx < len(env)]
            s = env[idx].mean()
            if s > best[0]:
                best = (s, bpm, off)
    grid_bpm, grid_off = float(best[1]), float(best[2])
    grid = np.arange(grid_off, dur, 60 / grid_bpm)
    # Agreement between the tracker and the grid tells us if the grid can be trusted.
    d = np.array([np.min(np.abs(grid - b)) for b in beats]) if len(beats) else np.array([9.0])
    agree = float(np.median(d))
    # Downbeat: which of the 4 phases carries the most low-end attack and harmonic change.
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
    low = S[freqs < 160].sum(axis=0)
    low_on = np.maximum(0, np.diff(low, prepend=low[0]))
    chroma = librosa.feature.chroma_cens(y=y, sr=SR, hop_length=hop)
    chroma_diff = np.r_[0, np.sqrt((np.diff(chroma, axis=1) ** 2).sum(axis=0))]
    bi = np.searchsorted(t_env, grid)
    bi = bi[bi < len(low_on)]
    win = 6
    low_b = np.array([low_on[max(i - win, 0):i + win].max() for i in bi])
    ch_b = np.array([chroma_diff[max(i - 2 * win, 0):i + 4 * win].sum() for i in bi])
    z = lambda a: (a - a.mean()) / (a.std() + 1e-9)
    score = z(low_b) + z(ch_b)
    phases = [float(score[p::4].mean()) for p in range(4)]
    phase = int(np.argmax(phases))
    srt = sorted(phases)
    db_conf = float(srt[-1] - srt[-2])
    downbeats = grid[phase::4]
    # Energy curve, 4 per second.
    h2 = int(SR / 4)
    rms = librosa.feature.rms(y=y, frame_length=h2 * 2, hop_length=h2)[0]
    rms_db = 20 * np.log10(rms + 1e-6)
    tc = np.arange(len(rms)) * h2 / SR
    # Sections from timbre + harmony, snapped to the nearest downbeat.
    mfcc = librosa.feature.mfcc(y=y, sr=SR, hop_length=hop, n_mfcc=13)
    bf = np.searchsorted(t_env, downbeats)
    bf = bf[bf < mfcc.shape[1]]
    feat = np.vstack([librosa.util.sync(mfcc, bf), librosa.util.sync(chroma, bf)])
    k = max(4, min(12, int(dur / 12)))
    bound = librosa.segment.agglomerative(feat, k)
    sec_t = [0.0] + [float(downbeats[min(b, len(downbeats) - 1)]) for b in bound if b > 0] + [dur]
    sec_t = sorted(set(round(s, 2) for s in sec_t))
    sections = []
    for a, b in zip(sec_t[:-1], sec_t[1:]):
        m = (tc >= a) & (tc < b)
        sections.append(dict(s=a, e=b, bars=round((b - a) / (240 / grid_bpm), 1),
                             rms_db=round(float(rms_db[m].mean()) if m.any() else -80, 1)))
    # Biggest moments: largest rise of the next bar over the previous two bars, by downbeat.
    bar = 240 / grid_bpm
    moments = []
    for d0 in downbeats:
        pre = (tc >= d0 - 2 * bar) & (tc < d0)
        post = (tc >= d0) & (tc < d0 + bar)
        if pre.sum() < 4 or post.sum() < 4:
            continue
        moments.append((float(rms_db[post].mean() - rms_db[pre].mean()), float(d0), float(rms_db[post].mean())))
    jumps = sorted(moments, reverse=True)[:6]
    drops = sorted(moments)[:4]
    # Silence or near-silence gaps (the song's own breaks).
    words = whisper_words(path, band=(180, 5000))
    lines = group_lines(words)
    tail = rms_db[-int(4 * 4):].tolist()
    res = dict(file=path, duration=round(dur, 3), tempo_tracker=round(tempo, 2), bpm=round(grid_bpm, 2),
               offset=round(grid_off, 3), beat_grid_vs_tracker_ms=round(agree * 1000), downbeat_phase=phase,
               downbeat_confidence=round(db_conf, 2), downbeat_offset=round(float(downbeats[0]), 3),
               beats=[round(float(b), 3) for b in grid], downbeats=[round(float(b), 3) for b in downbeats],
               energy=dict(t=[round(float(t), 2) for t in tc], db=[round(float(v), 1) for v in rms_db]),
               sections=sections,
               jumps=[dict(t=round(t, 2), rise_db=round(r, 1), level_db=round(l, 1)) for r, t, l in jumps],
               drops=[dict(t=round(t, 2), rise_db=round(r, 1), level_db=round(l, 1)) for r, t, l in drops],
               words=words, lines=lines, tail_db=[round(v, 1) for v in tail])
    json.dump(res, open(cache, "w"))
    if out:
        os.makedirs(out, exist_ok=True)
        json.dump(res, open(os.path.join(out, os.path.basename(path) + ".song.json"), "w"), indent=0)
    return res


def print_song(s):
    print(f"{os.path.basename(s['file'])}: {s['duration']} s, {s['bpm']} BPM (tracker {s['tempo_tracker']}, "
          f"median gap to grid {s['beat_grid_vs_tracker_ms']} ms), first beat {s['offset']}, "
          f"first downbeat {s['downbeat_offset']} (confidence {s['downbeat_confidence']})")
    print("sections (file seconds, bars, level):")
    for x in s["sections"]:
        print(f"  {x['s']:7.2f} to {x['e']:7.2f}  {x['bars']:5.1f} bars  {x['rms_db']:6.1f} dB")
    print("biggest rises:", ", ".join(f"{j['t']:.2f}s (+{j['rise_db']} dB)" for j in s["jumps"]))
    print("biggest falls:", ", ".join(f"{j['t']:.2f}s ({j['rise_db']} dB)" for j in s["drops"]))
    print(f"sung lines found: {len(s['lines'])} (times only here; words in the JSON)")
    print("  " + " ".join(f"{l['s']:.1f}-{l['e']:.1f}" for l in s["lines"]))


# ---------- natural sound ----------
GROUPS = {
    "laugh": ["Laughter", "Baby laughter", "Giggle", "Snicker", "Belly laugh", "Chuckle, chortle"],
    "shout": ["Shout", "Bellow", "Whoop", "Yell", "Battle cry", "Children shouting", "Screaming", "Cheering", "Crowd"],
    "speech": ["Speech", "Child speech, kid speaking", "Conversation", "Narration, monologue", "Hubbub, speech noise, speech babble"],
    "wind": ["Wind", "Rustling leaves", "Wind noise (microphone)", "Howl"],
    "steps": ["Walk, footsteps", "Run", "Shuffle", "Crushing", "Crumpling, crinkling"],
    "spray": ["Spray", "Hiss", "Squish", "Liquid", "Pump (liquid)", "Squirt", "Sizzle"],
    "clap": ["Clapping", "Applause", "Hands", "Finger snapping"],
    "tap": ["Tap", "Knock", "Clicking", "Thump, thud", "Slap, smack", "Whack, thwack"],
    "breath": ["Breathing", "Gasp", "Sigh", "Pant", "Whistling"],
    "music": ["Music"],
}


def yamnet_tags(y16):
    from ai_edge_litert.interpreter import Interpreter
    bbenv.need_file(YAMNET)
    labels = [l.strip() for l in open(YAMNET_LABELS)]
    it = Interpreter(YAMNET)
    it.allocate_tensors()
    inp, outp = it.get_input_details()[0]["index"], it.get_output_details()[0]["index"]
    idx = {g: [labels.index(n) for n in names if n in labels] for g, names in GROUPS.items()}
    N, hop = 15600, 7680
    rows = []
    for st in range(0, max(len(y16) - N, 1), hop):
        w = y16[st:st + N]
        if len(w) < N:
            w = np.pad(w, (0, N - len(w)))
        it.set_tensor(inp, w.astype(np.float32))
        it.invoke()
        sc = it.get_tensor(outp)[0]
        rows.append(dict(t=st / 16000, **{g: float(sc[ii].max()) for g, ii in idx.items()}))
    return rows


def scan_clip(path, use_whisper=True):
    y = decode(path, sr=16000)
    dur = len(y) / 16000
    if len(y) < 1600:
        return dict(clip=path, duration=round(dur, 2), events=[], words=[])
    tags = yamnet_tags(y)
    # Level: 50 ms RMS, and a loudness floor for the clip.
    n = 800
    rms = np.sqrt(np.convolve(y ** 2, np.ones(n) / n, mode="same"))[::n]
    ldb = 20 * np.log10(rms + 1e-6)
    floor = float(np.percentile(ldb, 30))
    events = []
    TH = dict(laugh=0.12, shout=0.12, speech=0.35, wind=0.30, steps=0.15, spray=0.10, clap=0.12, tap=0.12, breath=0.15, music=0.5)
    for g, th in TH.items():
        run_s = None
        for r in tags + [dict(t=dur, **{k: 0 for k in GROUPS})]:
            if r[g] >= th and run_s is None:
                run_s, peak = r["t"], r[g]
            elif r[g] >= th:
                peak = max(peak, r[g])
            elif run_s is not None:
                a, b = run_s, r["t"] + 0.48
                ia, ib = int(a / 0.05), int(min(b, dur) / 0.05)
                lev = float(ldb[ia:ib].max()) if ib > ia else floor
                events.append(dict(kind=g, s=round(a, 2), e=round(min(b, dur), 2), conf=round(peak, 2),
                                   level_db=round(lev, 1), above_floor=round(lev - floor, 1)))
                run_s = None
    # Level peaks: the loudest bursts, whatever they are.
    peaks = []
    hopt = 0.05
    order = np.argsort(ldb)[::-1]
    for i in order:
        t = float(i * hopt)
        if ldb[i] < floor + 10:
            break
        if all(abs(t - p["t"]) > 1.0 for p in peaks):
            peaks.append(dict(t=round(t, 2), level_db=round(float(ldb[i]), 1), above_floor=round(float(ldb[i]) - floor, 1)))
        if len(peaks) >= 6:
            break
    words = whisper_words(path) if use_whisper else []
    words = [w for w in words if not re.match(r"^[\[\(].*[\]\)]$", w["w"]) or True]
    return dict(clip=path, duration=round(dur, 2), mean_db=round(db(np.sqrt((y ** 2).mean())), 1),
                peak_db=round(db(np.abs(y).max()), 1), floor_db=round(floor, 1), events=sorted(events, key=lambda e: e["s"]),
                peaks=sorted(peaks, key=lambda p: p["t"]), lines=group_lines(words, 0.6))


def cmd_clips(args):
    os.makedirs(args.out, exist_ok=True)
    clips = []
    for p in args.paths:
        if os.path.isdir(p):
            clips += [os.path.join(p, f) for f in sorted(os.listdir(p))
                      if f.lower().endswith((".mp4", ".mov")) and not f.startswith(".")]
        else:
            clips.append(p)
    if args.large:
        WHISPER.update(model=LARGE_MODEL, lang="auto")
    path = os.path.join(args.out, "sounds.json")
    res = json.load(open(path)) if os.path.exists(path) else {}
    for c in clips:
        name = os.path.basename(c)
        if name in res and not args.force:
            continue
        res[name] = scan_clip(c, use_whisper=not args.no_whisper)
        json.dump(res, open(path, "w"), indent=0)
        print(name, res[name]["duration"], len(res[name]["events"]), flush=True)
    with open(os.path.join(args.out, "sounds.md"), "w") as f:
        f.write("# Natural sound in the clips (measured, not heard)\n\nYAMNet labels are guesses from a small model; "
                "whisper lines are what it thinks it heard. Check a frame and the level before using one.\n\n")
        for name, r in res.items():
            ev = [e for e in r.get("events", []) if e["kind"] not in ("music",)]
            f.write(f"## {name} ({r['duration']} s, mean {r.get('mean_db')} dB, peak {r.get('peak_db')} dB)\n")
            for e in ev:
                if e["kind"] in ("laugh", "shout", "clap", "spray", "steps", "tap", "breath") or e["kind"] == "speech" and e["above_floor"] > 12:
                    f.write(f"- {e['s']:.1f}-{e['e']:.1f} {e['kind']} conf {e['conf']} level {e['level_db']} ({e['above_floor']:+.0f} over floor)\n")
            if r.get("lines"):
                f.write("- words: " + " | ".join(f"{l['s']:.1f}: {l['text']}" for l in r["lines"]) + "\n")
            if r.get("peaks"):
                f.write("- peaks: " + ", ".join(f"{p['t']:.1f}s {p['level_db']} dB" for p in r["peaks"]) + "\n")
            f.write("\n")
    print("wrote", path)


# ---------- the finished cut ----------
def ebur(path):
    r = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-"])
    t = r.stderr
    g = lambda pat: (lambda m: float(m[-1]) if m else None)(re.findall(pat, t))
    return dict(lufs=g(r"I:\s+(-?[\d.]+) LUFS"), lra=g(r"LRA:\s+(-?[\d.]+) LU"), true_peak=g(r"Peak:\s+(-?[\d.]+) dBFS"))


def momentary_max(y, sr):
    n = int(0.4 * sr)
    if len(y) < n:
        return None
    e = np.convolve(y ** 2, np.ones(n) / n, mode="valid")
    return round(db(np.sqrt(e.max())), 1), round(float(np.argmax(e) / sr), 2)


def picture_motion(path, fps=10):
    w, h = 54, 96
    r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", path, "-an", "-vf", f"fps={fps},scale={w}:{h},format=gray",
                        "-f", "rawvideo", "-"], capture_output=True)
    fr = np.frombuffer(r.stdout, dtype=np.uint8).reshape(-1, h, w).astype(np.float32)
    d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))
    b = fr.mean(axis=(1, 2))
    return dict(t=(np.arange(len(d)) + 1) / fps, motion=d, bright=b[1:])


def timeline_map(man):
    """[(t0, t1, file_start)]: which part of the music file plays when."""
    mu = man.get("music") or {}
    if man.get("music_map"):
        return man["music_map"]
    if not mu.get("file"):
        return []
    return [[0.0, man["duration"], float(mu.get("start", 0))]]


def to_timeline(ft, mp):
    out = []
    for t0, t1, fs in mp:
        for f in ft:
            t = f - fs + t0
            if t0 - 1e-3 <= t < t1:
                out.append(t)
    return np.array(sorted(out))


def cmd_cut(args):
    os.makedirs(args.out, exist_ok=True)
    import librosa
    man = json.load(open(args.manifest)) if args.manifest else {}
    stem = os.path.splitext(os.path.basename(args.video))[0]
    y = decode(args.video)
    st = decode(args.video, sr=48000, ch=2)
    dur = len(y) / SR
    # Song map: from the music file, or from the finished audio.
    mfile = args.music or (man.get("music") or {}).get("file")
    if mfile and not os.path.isabs(os.path.expanduser(mfile)) and args.manifest:
        mfile = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(args.manifest)), "..", mfile))
    if mfile and os.path.exists(os.path.expanduser(mfile)):
        song = song_map(os.path.expanduser(mfile))
        mp = timeline_map(man) if man else [[0.0, dur, float(args.music_start or 0)]]
        beats = to_timeline(song["beats"], mp)
        downs = to_timeline(song["downbeats"], mp)
        lines = []
        for l in song["lines"]:
            for t0, t1, fs in mp:
                s, e = l["s"] - fs + t0, l["e"] - fs + t0
                if e > t0 and s < t1:
                    lines.append(dict(s=round(s, 2), e=round(e, 2), n=l["n"], clipped_start=bool(s < t0 and t0 > 0 or s < 0),
                                      clipped_end=bool(e > t1)))
        words = []
        for w in song["words"]:
            for t0, t1, fs in mp:
                s, e = w["s"] - fs + t0, w["e"] - fs + t0
                if e > t0 and s < t1:
                    words.append(dict(s=s, e=e, w=w["w"]))
    else:
        song = None
        tempo, b = librosa.beat.beat_track(y=y, sr=SR, units="time")
        beats, downs, lines, words = np.array(b), np.array(b[::4]), [], []
        mp = []
    shots = man.get("shots", [])
    if shots:
        cuts = [s["end"] for s in shots[:-1]]
    else:
        ons = run(["ffmpeg", "-nostdin", "-hide_banner", "-i", args.video, "-an", "-vf", "select='gt(scene,0.3)',showinfo", "-f", "null", "-"]).stderr
        cuts = [float(x) for x in re.findall(r"pts_time:([\d.]+)", ons)]
    fps = man.get("fps", 30)
    tol_on = 1.5 / fps + 0.01
    rows = []
    for i, c in enumerate(cuts):
        row = dict(i=i, t=round(c, 3))
        if len(beats):
            j = int(np.argmin(np.abs(beats - c)))
            row["beat_off_ms"] = round(float(c - beats[j]) * 1000)
            if len(beats) > 1:
                step = float(np.median(np.diff(beats)))
                row["beat_frac"] = round(float(((c - beats[j]) / step)), 2)
        if len(downs):
            k = int(np.argmin(np.abs(downs - c)))
            row["down_off_ms"] = round(float(c - downs[k]) * 1000)
        off = abs(row.get("beat_off_ms", 9999)) / 1000
        row["flag"] = "ON" if off <= tol_on else ("near" if off <= 0.09 else "OFF")
        if row.get("beat_frac") is not None and abs(abs(row["beat_frac"]) - 0.5) < 0.08:
            row["flag"] = "half"
        if shots and shots[i].get("off_beat") and row["flag"] != "ON":
            row["on_purpose"] = shots[i]["off_beat"]
        hit = [w for w in words if w["s"] + 0.04 < c < w["e"] - 0.04]
        row["inside_word"] = bool(hit)
        if shots:
            row["note"] = shots[i + 1].get("note", "")[:60]
        rows.append(row)
    on = sum(r["flag"] == "ON" for r in rows)
    # Energy of the finished audio, 4 per second; music-only biggest moment on the timeline.
    h2 = int(SR / 4)
    rms = librosa.feature.rms(y=y, frame_length=h2 * 2, hop_length=h2)[0]
    edb = 20 * np.log10(rms + 1e-6)
    tc = np.arange(len(rms)) * h2 / SR
    # Song's biggest rises inside the cut
    inside = []
    if song:
        for j in song["jumps"] + song["drops"]:
            tl = to_timeline([j["t"]], mp)
            if len(tl):
                inside.append(dict(t=round(float(tl[0]), 2), rise_db=j["rise_db"]))
    pm = picture_motion(args.video)
    from scipy.ndimage import uniform_filter1d
    mo = uniform_filter1d(pm["motion"], 10)
    tm_peak = float(pm["t"][int(np.argmax(mo))])
    # Resampled correlation between sound energy and picture movement.
    edb_i = np.interp(pm["t"], tc, edb)
    corr = float(np.corrcoef(uniform_filter1d(edb_i, 10), mo)[0, 1]) if len(mo) > 5 else None
    # Loudness and damage.
    L = ebur(args.video)
    m_max = momentary_max(st.mean(axis=1), 48000)
    clip_n = int((np.abs(st) >= 0.999).sum())
    # Start and end.
    pk_db = db(np.abs(st).max())
    # AAC adds about 20 ms of priming silence, so the "start" window opens after it
    head = db(np.sqrt((st[int(0.025 * 48000):int(0.06 * 48000)] ** 2).mean()))
    head2 = db(np.sqrt((st[int(0.06 * 48000):int(0.3 * 48000)] ** 2).mean()))
    tail_100 = db(np.sqrt((st[-int(0.1 * 48000):] ** 2).mean()))
    tail_500 = db(np.sqrt((st[-int(0.6 * 48000):-int(0.1 * 48000)] ** 2).mean()))
    last_2 = db(np.sqrt((st[-int(2.5 * 48000):-int(2 * 48000)] ** 2).mean())) if dur > 3 else None
    end_note = []
    if head > head2 - 6:
        end_note.append(f"starts already full ({head:.0f} dB in the first 30 ms): a hard in, fine if it lands on a beat")
    if tail_100 > L["lufs"] - 12 if L["lufs"] else False:
        end_note.append(f"ABRUPT END: last 100 ms still at {tail_100:.0f} dB")
    # Does the music end on a phrase?
    music_end = {}
    if song and mp:
        t0, t1, fs = mp[-1]
        ft = min(t1, dur) - t0 + fs
        d = np.array(song["downbeats"])
        k = int(np.argmin(np.abs(d - ft)))
        step = 240 / song["bpm"]
        # Was the music faded by us (level falling faster than the song itself)? Compare with the song's own level.
        mu = man.get("music") or {}
        fade = float(mu.get("fade_out", 0) or 0)
        en_t = np.array(song["energy"]["t"])
        en_d = np.array(song["energy"]["db"])
        own_end = float(np.interp(ft, en_t, en_d))
        own_before = float(np.interp(ft - 2, en_t, en_d))
        song_left = song["duration"] - ft
        music_end = dict(file_time=round(ft, 2), nearest_downbeat_off_ms=round((ft - d[k]) * 1000), bar_s=round(step, 3),
                         faded_s=fade, song_own_level_at_end=round(own_end, 1), song_own_level_2s_before=round(own_before, 1),
                         song_left_after_end_s=round(song_left, 1))
        ends_natural = own_end < own_before - 8
        if song_left < 1.5 or own_end < -40:
            music_end["verdict"] = (f"ends on the song's own ending, but a {fade} s fade sits over its last hits" if fade > 0.3
                                    else "plays out to the song's own ending")
        else:
            music_end["verdict"] = ("the song is falling away here" if ends_natural else
                                    (f"a {fade} s fade with {song_left:.0f} s of song still going" if fade else "chopped, song still going"))
    # What real sound is in it.
    evs = man.get("sound_events", [])
    def has_nat(s):
        return bool(s.get("audio")) or any(e["end"] > s["start"] + 0.05 and e["start"] < s["end"] - 0.05 and e.get("kind") != "sfx" for e in evs)
    nat = [dict(i=s.get("i"), audio=has_nat(s), gain=s.get("gain_db", 0)) for s in shots]
    n_on = sum(n["audio"] for n in nat)
    missed, used = [], []
    if args.sounds and os.path.exists(args.sounds) and shots:
        snd = json.load(open(args.sounds))
        for s in shots:
            r = snd.get(os.path.basename(s["clip"]))
            if not r:
                continue
            for e in r.get("events", []):
                if e["kind"] in ("laugh", "shout", "speech", "clap") and e["e"] > s["cin"] and e["s"] < s["cout"] and e["above_floor"] > 8:
                    item = dict(shot=s.get("i"), clip=os.path.basename(s["clip"]), kind=e["kind"], t=e["s"], level=e["level_db"])
                    (used if has_nat(s) else missed).append(item)
    mix = man.get("mix") or {}
    res = dict(video=args.video, duration=round(dur, 2), bpm=song["bpm"] if song else None, cuts=rows,
               cuts_on_beat=on, cuts_total=len(rows), loudness=L, momentary_max=m_max, clipped_samples=clip_n,
               sample_peak_db=round(pk_db, 2), head_db=round(head, 1), tail_100ms_db=round(tail_100, 1), tail_100_600ms_db=round(tail_500, 1),
               level_2s_before_end=round(last_2, 1) if last_2 else None, start_end_notes=end_note, music_end=music_end,
               lines=lines, picture_peak_t=round(tm_peak, 2), song_moments_in_cut=inside, sound_vs_picture_corr=round(corr, 2) if corr is not None else None,
               shots_with_clip_sound=n_on, shots_total=len(nat), natural_in_shots_but_muted=missed, natural_used=used, mix=mix)
    json.dump(res, open(os.path.join(args.out, stem + "-listen.json"), "w"), indent=1)
    # ---- the picture
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(4, 1, figsize=(20, 9), sharex=True, gridspec_kw=dict(height_ratios=[3, 2, 1, 1.4]))
    t = np.arange(len(y)) / SR
    step = max(1, len(y) // 8000)
    env = np.abs(y).reshape(-1)[:len(y) // step * step].reshape(-1, step).max(axis=1)
    tt = t[::step][:len(env)]
    ax[0].fill_between(tt, -env, env, color="#3b6ea5", lw=0)
    for b in beats:
        ax[0].axvline(b, color="#bbbbbb", lw=0.4, zorder=0)
    for b in downs:
        ax[0].axvline(b, color="#666666", lw=0.9, zorder=0)
    for r in rows:
        col = {"ON": "#10a040", "near": "#d0a000", "half": "#a040d0", "OFF": "#e02020"}[r["flag"]]
        ax[0].axvline(r["t"], color=col, lw=2)
    ax[0].set_ylim(-1.02, 1.02)
    ax[0].set_ylabel("waveform\ncuts: green on beat, yellow near,\npurple half-beat, red off")
    ax[1].plot(tc, edb, color="#c03060", label="sound level dB")
    ax2 = ax[1].twinx()
    ax2.plot(pm["t"], mo, color="#208080", label="picture movement")
    ax[1].set_ylabel("sound level")
    ax2.set_ylabel("picture movement")
    for m in inside:
        ax[1].axvline(m["t"], color="#c03060", ls=":", lw=1.5)
    for l in lines:
        ax[2].barh(1, l["e"] - l["s"], left=l["s"], height=0.8, color="#d08020")
    for tx in man.get("text", []):
        ax[2].barh(0, tx["end"] - tx["start"], left=tx["start"], height=0.8, color="#ff007f")
    ax[2].set_yticks([0, 1])
    ax[2].set_yticklabels(["on-screen text", "sung lines"])
    for s in shots:
        c = "#30a030" if has_nat(s) else "#dddddd"
        ax[3].barh(0, s["end"] - s["start"], left=s["start"], height=0.8, color=c, edgecolor="white")
        ax[3].text((s["start"] + s["end"]) / 2, 0, str(s.get("i")), ha="center", va="center", fontsize=8)
    for i, e in enumerate(man.get("sound_events", [])):
        ax[3].barh(1 + (i % 2) * 0.5, e["end"] - e["start"], left=e["start"], height=0.4, color="#2070d0")
    ax[3].set_yticks([0, 1.2])
    ax[3].set_yticklabels(["shots (green = own sound on)", "real-sound moments laid in"])
    ax[3].set_xlim(0, dur)
    ax[3].set_xticks(np.arange(0, dur + 1, 1))
    ax[3].grid(axis="x", alpha=0.3)
    fig.suptitle(f"{stem}: {L['lufs']} LUFS, {L['true_peak']} dBTP, {on}/{len(rows)} cuts on a beat")
    fig.tight_layout()
    png = os.path.join(args.out, stem + "-listen.png")
    fig.savefig(png, dpi=90)
    # ---- the report
    with open(os.path.join(args.out, stem + "-listen.md"), "w") as f:
        w = f.write
        w(f"# Sound check: {stem}\n\nMeasured, not heard. {dur:.2f} s.\n\n")
        w(f"- Loudness {L['lufs']} LUFS, range {L['lra']} LU, true peak {L['true_peak']} dBTP, loudest 400 ms {m_max[0] if m_max else '?'} dB at {m_max[1] if m_max else '?'} s, clipped samples {clip_n}.\n")
        w(f"- Start: {head:.0f} dB in the first 30 ms. End: last 100 ms at {tail_100:.0f} dB, 0.6 to 0.1 s before the end at {tail_500:.0f} dB. {' '.join(end_note)}\n")
        if music_end:
            w(f"- Music end: file time {music_end['file_time']} s, {music_end['nearest_downbeat_off_ms']} ms from a downbeat; fade {music_end['faded_s']} s; song's own level there {music_end['song_own_level_at_end']} dB vs {music_end['song_own_level_2s_before']} dB 2 s before; {music_end['song_left_after_end_s']} s of song left. Verdict: {music_end['verdict']}.\n")
        w(f"- Cuts: {on} of {len(rows)} on a beat (within {tol_on * 1000:.0f} ms). Sound and picture energy correlation {res['sound_vs_picture_corr']}. Picture's busiest moment {tm_peak:.1f} s. Song moments inside the cut: {', '.join(str(m['t']) + 's (' + format(m['rise_db'], '+.1f') + ' dB)' for m in inside) or 'none'}.\n")
        if man.get("mix"):
            w(f"- Real people against the music: {man['mix'].get('summary', '')}\n")
        w(f"- Clip sound on in {n_on} of {len(nat)} shots.")
        w(f" Natural moments in the picture with the sound off: {len(missed)}. In use: {len(used)}.\n" if args.sounds else "\n")
        if lines:
            ch = [l for l in lines if l["clipped_start"] or l["clipped_end"]]
            w(f"- Sung lines inside the cut: {len(lines)}; cut off by the start or end of the cut: {len(ch)}"
              + (" (" + ", ".join(f"{l['s']:.1f}-{l['e']:.1f}" for l in ch) + ")" if ch else "") + ".\n")
        w("\n## Every cut\n| # | at (s) | from nearest beat (ms) | from downbeat (ms) | flag | inside a sung word | next shot |\n|---|---|---|---|---|---|---|\n")
        for r in rows:
            w(f"| {r['i']} | {r['t']:.2f} | {r.get('beat_off_ms', '')} | {r.get('down_off_ms', '')} | {r['flag']} | {'yes' if r['inside_word'] else ''} | {r.get('note', '')}{' (off the beat on purpose: ' + r['on_purpose'] + ')' if r.get('on_purpose') else ''} |\n")
        if missed:
            w("\n## Real sound in the shots, switched off\n")
            for m in missed:
                w(f"- shot {m['shot']} {m['clip']}: {m['kind']} around {m['t']} s in the clip, {m['level']} dB\n")
        if used:
            w("\n## Real sound on\n")
            for m in used:
                w(f"- shot {m['shot']} {m['clip']}: {m['kind']} around {m['t']} s in the clip, {m['level']} dB\n")
        w(f"\nPicture: {os.path.basename(png)}\n")
    print(os.path.join(args.out, stem + "-listen.md"))
    print(png)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("song")
    a.add_argument("file")
    a.add_argument("--out")
    a.add_argument("--force", action="store_true")
    a = sub.add_parser("clips")
    a.add_argument("paths", nargs="+")
    a.add_argument("--out", required=True)
    a.add_argument("--force", action="store_true")
    a.add_argument("--no-whisper", action="store_true")
    a.add_argument("--large", action="store_true", help="the bigger model (setup.py --download-large): clearer, slower, any language")
    a = sub.add_parser("cut")
    a.add_argument("video")
    a.add_argument("--manifest")
    a.add_argument("--music")
    a.add_argument("--music-start", type=float)
    a.add_argument("--sounds")
    a.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "song":
        print_song(song_map(args.file, args.out, args.force))
    elif args.cmd == "clips":
        cmd_clips(args)
    else:
        cmd_cut(args)


if __name__ == "__main__":
    main()
