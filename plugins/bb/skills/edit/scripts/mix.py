#!/usr/bin/env python3
"""mix.py: builds a cut's sound before the picture render, because real people need more than a bed.

    PY mix.py job/edl.json          # writes job/renders/<slug>-mix.wav plus stems and <slug>-mix.json

The EDL's "sound" block:
  "music_gain_db": -3
  "nat": [ { "clip": path, "in": s, "out": s, "at": timeline s, "gain_db": 0, "fade_in": 0.02, "fade_out": 0.06,
             "hp": 120, "duck": -10, "level": -20, "compress": true, "kind": "voice", "note": "..." } ]
  "sfx": [ { "file": path, "at": s, "in": 0, "out": 0.4, "gain_db": -10, "duck": 0, "note": "..." } ]
  "duck_down": 0.06, "duck_up": 0.2
"level" sets the event's own RMS (dBFS) over its loud parts before gain_db; "duck" pulls the music down under it.
Music plays from music.start in the file, coming in at music.at on the timeline, and runs as long as music.end_t
or the track's own end; music.fade_out only if you set it. "music.segments" [[file_s, file_e], ...] joins bars.
Sets edl["mix_file"], music_map, sound_events and mix_info by writing them into the EDL, so cut.py and listen.py pick them up.
"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bbenv  # noqa: E402
bbenv.need("numpy")
import numpy as np  # noqa: E402

SR = 48000


def dec(path, t0=None, dur=None, af=None, ch=2):
    a = ["ffmpeg", "-nostdin", "-v", "error"]
    if t0 is not None:
        a += ["-ss", f"{t0:.4f}"]
    if dur is not None:
        a += ["-t", f"{dur:.4f}"]
    a += ["-i", path, "-vn", "-ac", str(ch), "-ar", str(SR)]
    if af:
        a += ["-af", af]
    a += ["-f", "f32le", "-"]
    r = subprocess.run(a, capture_output=True)
    if r.returncode:
        sys.exit(f"mix.py: cannot read {path}: {r.stderr.decode(errors='replace')[:300]}")
    return np.frombuffer(r.stdout, dtype=np.float32).reshape(-1, ch).copy()


def fade(x, fi, fo):
    n = len(x)
    i, o = min(int(fi * SR), n), min(int(fo * SR), n)
    if i:
        x[:i] *= np.sin(np.linspace(0, np.pi / 2, i))[:, None]
    if o:
        x[-o:] *= np.cos(np.linspace(0, np.pi / 2, o))[:, None]
    return x


def rms_db(x):
    return float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))


def active_rms(x):
    """RMS over the louder half of 50 ms windows: the voice, not the gaps."""
    m = x.mean(axis=1)
    n = int(0.05 * SR)
    if len(m) < n:
        return rms_db(x)
    e = np.array([np.sqrt((m[i:i + n] ** 2).mean()) for i in range(0, len(m) - n, n)])
    th = np.percentile(e, 50)
    return float(20 * np.log10(np.sqrt((e[e >= th] ** 2).mean()) + 1e-9))


def main():
    path = os.path.abspath(sys.argv[1])
    edl = json.load(open(path))
    base = os.path.dirname(path)
    rel = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    # total from the shots
    total = sum((s["out"] - s["in"]) / float(s.get("speed", 1)) for s in edl["shots"])
    N = int(round(total * SR))
    snd = edl.get("sound", {})
    nat = np.zeros((N, 2), dtype=np.float32)
    sfx = np.zeros((N, 2), dtype=np.float32)
    duck_db = np.zeros(N, dtype=np.float32)
    events = []
    for kind, lst in (("nat", snd.get("nat", [])), ("sfx", snd.get("sfx", []))):
        for e in lst:
            src = rel(e.get("clip") or e["file"])
            t0, t1 = float(e.get("in", 0)), e.get("out")
            dur = None if t1 is None else float(t1) - t0
            chain = []
            hp = e.get("hp", 120 if kind == "nat" else None)
            if hp:
                chain.append(f"highpass=f={hp}")
            if e.get("compress", kind == "nat"):
                chain.append("acompressor=threshold=-26dB:ratio=3:attack=6:release=140:makeup=1")
            x = dec(src, t0, dur, ",".join(chain) or None)
            if e.get("level") is not None:
                x *= 10 ** ((float(e["level"]) - active_rms(x)) / 20)
            x *= 10 ** (float(e.get("gain_db", 0)) / 20)
            x = np.tanh(x * 1.0) if np.abs(x).max() > 0.9 else x     # the camera's overs, softly
            fade(x, float(e.get("fade_in", 0.02)), float(e.get("fade_out", 0.06)))
            at = int(round(float(e["at"]) * SR))
            end = min(at + len(x), N)
            if at >= N:
                continue
            (nat if kind == "nat" else sfx)[at:end] += x[:end - at]
            ev = dict(start=round(at / SR, 3), end=round(end / SR, 3), kind="voice" if kind == "nat" else "sfx",
                      note=e.get("note", ""), level=round(active_rms(x), 1))
            if e.get("duck"):
                # ramp the music down around the event
                d = float(e["duck"])
                dn, up = float(snd.get("duck_down", 0.06)), float(snd.get("duck_up", 0.2))
                a = max(0, at - int(dn * SR))
                b = min(N, end + int(up * SR))
                seg = np.full(b - a, d, dtype=np.float32)
                k = at - a
                if k > 0:
                    seg[:k] = np.linspace(0, d, k)
                k2 = b - end
                if k2 > 0:
                    seg[-k2:] = np.linspace(d, 0, k2)
                duck_db[a:b] = np.minimum(duck_db[a:b], seg)
                ev["duck"] = d
            events.append(ev)
    # music
    mu = edl.get("music") or {}
    music = np.zeros((N, 2), dtype=np.float32)
    mmap = []
    if mu.get("file"):
        mf = rel(mu["file"])
        at = float(mu.get("at", 0))
        segs = mu.get("segments") or [[float(mu.get("start", 0)), None]]
        pos = int(at * SR)
        for sg in segs:
            fs, fe = sg[0], sg[1]
            tail = float(sg[2]) if len(sg) > 2 else 0.0      # let a sung word ring past the join
            x = dec(mf, fs, None if fe is None else fe - fs + tail)
            xf = 0.012
            fade(x, float(mu.get("fade_in", xf)) if not mmap else xf, max(xf, tail * .4) if fe is not None else 0.0)
            end = min(pos + len(x), N)
            music[pos:end] += x[:end - pos]
            nxt = min(pos + int(round((fe - fs) * SR)), N) if fe is not None else end
            mmap.append([round(pos / SR, 4), round(nxt / SR, 4), fs])
            pos = nxt
        g = float(snd.get("music_gain_db", mu.get("gain_db", 0)))
        music *= 10 ** (g / 20)
        if mu.get("fade_out"):
            n = int(float(mu["fade_out"]) * SR)
            music[pos - n:pos] *= np.linspace(1, 0, n)[:, None]
    # "duck_low": how much of the duck the bass takes (0 to 1). Below 1 the song keeps its bass line under a
    # voice while the mids, which are what actually cover speech, come down the full amount.
    low_share = float(snd.get("duck_low", 1.0))
    if low_share < 1:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, float(snd.get("duck_split_hz", 180)), "low", fs=SR, output="sos")
        low = sosfiltfilt(sos, music, axis=0).astype(np.float32)
        music_d = low * (10 ** (duck_db * low_share / 20))[:, None] + (music - low) * (10 ** (duck_db / 20))[:, None]
    else:
        music_d = music * (10 ** (duck_db / 20))[:, None]
    mix = nat + music_d + sfx
    # report: real people against the music, per voice event
    per = []
    for e in events:
        if e["kind"] != "voice":
            continue
        a, b = int(e["start"] * SR), int(e["end"] * SR)
        v, m_ = active_rms(nat[a:b]), rms_db(music_d[a:b])
        e["over_music_db"] = round(v - m_, 1)
        per.append(v - m_)
        if b - a > SR // 4 and e.get("duck"):      # the band speech lives in, where a strong bass line can't help
            from scipy.signal import butter, sosfiltfilt
            sos2 = butter(4, [300, 3000], "band", fs=SR, output="sos")
            e["over_music_speechband_db"] = round(active_rms(sosfiltfilt(sos2, nat[a:b], axis=0)) - rms_db(sosfiltfilt(sos2, music_d[a:b], axis=0)), 1)
    over = [p for p in per if p < 60]
    out_dir = os.path.join(base, edl.get("out_dir", "renders"))
    os.makedirs(out_dir, exist_ok=True)
    slug = edl.get("slug", "cut")
    import soundfile as sf
    wav = os.path.join(out_dir, f"{slug}-mix.wav")
    sf.write(wav, mix, SR, subtype="PCM_24")
    for nm, st in (("music", music_d), ("nat", nat), ("sfx", sfx)):
        sf.write(os.path.join(out_dir, f"{slug}-stem-{nm}.wav"), st, SR, subtype="PCM_16")
    summary = (f"{len(over)} real-sound moments, voice over music by {min(over):.0f} to {max(over):.0f} dB "
               f"(median {np.median(over):.0f})") if over else ("no real sound; shots marked audio: true are not in this mix, so lay them with sound.nat" if any(s.get("audio") for s in edl.get("shots", [])) else "no real sound")
    edl["mix_file"] = os.path.relpath(wav, base)
    edl["music_map"] = mmap
    edl["sound_events"] = events
    edl["mix_info"] = dict(summary=summary, peak_db=round(float(20 * np.log10(np.abs(mix).max() + 1e-9)), 1))
    json.dump(edl, open(path, "w"), indent=1)
    print(f"wrote {wav} ({total:.2f}s); {summary}; mix peak {edl['mix_info']['peak_db']} dB")
    for e in events:
        if e["kind"] == "voice":
            print(f"  {e['start']:6.2f}-{e['end']:6.2f}  level {e['level']:6.1f}  over music {e.get('over_music_db', 0):5.1f} dB, speech band {e.get('over_music_speechband_db', 0):5.1f} dB  {e['note']}")


if __name__ == "__main__":
    main()
