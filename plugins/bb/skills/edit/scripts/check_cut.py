#!/usr/bin/env python3
"""check_cut.py: the mechanical checks on a rendered cut, so the critic can spend itself on taste.

    python3 check_cut.py renders/<slug>-9x16.mp4 [--min 6] [--max 60]

Reads the manifest cut.py or reframe.py wrote beside the video (<stem>.json).
Prints PASS / WARN / FAIL per line; exits 1 if anything failed.
Checks: file spec (size, fps, H.264, yuv420p, BT.709 tags, AAC 48 kHz), duration against the EDL,
shot lengths (a hold next to quicker shots, not all the same length, nothing too short, the
longest stretch with nothing new), cuts sitting on every music beat, black frames, loudness and
true peak, the ending (last shot long enough, sound not chopped), text inside the safe zones,
text stacking, text up long enough to read, and voice never sped or slowed.
"""
import json, os, re, statistics, subprocess, sys
from fractions import Fraction

results = []


def say(level, msg):
    results.append(level)
    print(f"{level:4}  {msg}")


def ff(args):
    return subprocess.run(["ffmpeg", "-nostdin", "-hide_banner"] + args, capture_output=True, text=True).stderr


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    video = argv[0]
    lo = float(argv[argv.index("--min") + 1]) if "--min" in argv else 6
    hi = float(argv[argv.index("--max") + 1]) if "--max" in argv else 60
    man_path = os.path.splitext(video)[0] + ".json"
    if not os.path.exists(man_path):
        sys.exit(f"no manifest at {man_path}; render with cut.py / reframe.py")
    m = json.load(open(man_path))
    W, H = m["size"]
    fmt = m["fmt"]

    # 1. file spec
    p = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                   "stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,color_transfer,"
                                   "color_primaries,color_space,sample_rate,duration:format=duration",
                                   "-of", "json", video], capture_output=True, text=True).stdout)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    spec_ok = (v["width"], v["height"]) == (W, H) and v["codec_name"] == "h264" and v["pix_fmt"] == "yuv420p" \
        and abs(float(Fraction(v["r_frame_rate"])) - m["fps"]) < 0.01
    say("PASS" if spec_ok else "FAIL", f"video {v['width']}x{v['height']} {v['codec_name']} {v['pix_fmt']} "
        f"{v['r_frame_rate']} fps (want {W}x{H} h264 yuv420p {m['fps']})")
    tags = (v.get("color_primaries"), v.get("color_transfer"), v.get("color_space"))
    say("PASS" if tags == ("bt709",) * 3 else "WARN", f"colour tags {tags} (want bt709 x3)")
    if a is None:
        say("FAIL", "no audio stream")
    else:
        say("PASS" if a["codec_name"] == "aac" and a["sample_rate"] == "48000" else "WARN",
            f"audio {a['codec_name']} {a['sample_rate']} Hz")
    dur = float(p["format"]["duration"])
    vd = float(v.get("duration", dur))
    say("PASS" if abs(vd - m["duration"]) <= 1.5 / m["fps"] else "FAIL",
        f"duration {vd:.2f}s video, EDL {m['duration']:.2f}s")
    if a is not None and abs(float(a.get("duration", vd)) - vd) > 0.1:
        say("WARN", f"audio {float(a['duration']):.2f}s vs video {vd:.2f}s")
    say("PASS" if lo <= vd <= hi else "WARN", f"length {vd:.1f}s (asked {lo:.0f} to {hi:.0f}s)")

    # 2. shots and rhythm
    shots = m["shots"]
    lens = [s["dur"] for s in shots]
    say("INFO", "shot lengths: " + " ".join(f"{x:.2f}" for x in lens))
    short = [i for i, x in enumerate(lens) if x < 0.3 and not shots[i].get("flash")]
    say("WARN" if short else "PASS", f"shots under 0.3 s: {short or 'none'}")
    if len(lens) >= 4:
        med = statistics.median(lens)
        cv = statistics.pstdev(lens) / statistics.mean(lens)
        say("WARN" if cv < 0.15 else "PASS", f"shot-length spread {cv:.2f} (under 0.15 reads as a timer)")
        holds = [i for i, x in enumerate(lens) if x >= 1.8 * med]
        say("PASS" if holds else "WARN", f"held shots (1.8x the median {med:.2f}s): {holds or 'none'}")
    events = sorted({0.0, vd} | {s["start"] for s in shots} | {t["start"] for t in m["text"]}
                    | {t["end"] for t in m["text"] if t["end"] < vd - 0.05})
    gap = max(b - a for a, b in zip(events, events[1:]))
    say("WARN" if gap > 6 else "PASS", f"longest stretch with nothing new {gap:.1f}s (house style: about 6 s)")
    beats = m.get("beats") or []
    cuts = [s["start"] for s in shots[1:]]
    if beats and len(cuts) >= 4:
        on = sum(1 for c in cuts if min(abs(c - b) for b in beats) < 0.05)
        say("WARN" if on / len(cuts) > 0.8 else "PASS",
            f"{on}/{len(cuts)} cuts on a music beat (every cut on the beat reads as a grid)")
    slowed = [s["i"] for s in shots if s["speed"] != 1 and s["audio"]]
    say("FAIL" if slowed else "PASS", f"voice sped or slowed: {slowed or 'none'}")

    # 3. black frames
    bd = ff(["-i", video, "-vf", "blackdetect=d=0.04:pic_th=0.97", "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)
    say("FAIL" if blacks else "PASS", f"black frames: {blacks or 'none'}")

    # 4. sound
    eb = ff(["-i", video, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"])
    I = re.findall(r"I:\s+(-?[\d.]+) LUFS", eb)
    pk = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", eb)
    if I:
        li = float(I[-1])
        say("PASS" if abs(li + 14) <= 1.0 else "WARN", f"loudness {li:.1f} LUFS (target -14)")
    if pk:
        tp = float(pk[-1])
        say("PASS" if tp <= -0.95 else "WARN", f"true peak {tp:.1f} dBTP (want -1 or lower; cut.py limits it)")
    say("PASS" if lens[-1] >= 1.2 else "WARN", f"last shot {lens[-1]:.2f}s (let the ending land)")
    tail = ff(["-sseof", "-0.12", "-i", video, "-vn", "-af", "volumedetect", "-f", "null", "-"])
    mv = re.findall(r"mean_volume:\s+(-?[\d.]+|-inf) dB", tail)
    if mv:
        tv = float(mv[-1]) if mv[-1] != "-inf" else -99
        say("WARN" if tv > -28 else "PASS", f"last 0.12 s at {tv:.0f} dB (loud means the sound is chopped, "
            f"fade it or hold longer)")

    # 5. text
    if fmt == "9x16":
        top, bot, side = 270, 1590, 60
        crop_top, crop_bot = 330, 1590
    else:
        top, bot, side = 24, H - 24, 24
        crop_top, crop_bot = top, bot
    for t in m["text"]:
        x, y, w, h = t["box"]
        label = f"text {t['j']} \"{t['text'][:30]}\" rows {y}-{y + h}"
        if t.get("full"):
            continue
        if y < top or y + h > bot or x < side or x + w > W - side:
            say("FAIL", f"{label}, x {x}-{x + w}, outside the safe zone ({top}-{bot}, {side}px sides)")
        elif fmt == "9x16" and (y < crop_top or y + h > crop_bot):
            say("WARN", f"{label} outside rows {crop_top}-{crop_bot}, so Meta's 4:5 crop would cut it")
        else:
            say("PASS", f"{label} inside the safe zone")
        words = len(t["text"].split())
        need = max(0.6, words / 3.0)
        on = t["end"] - t["start"]
        if on < need:
            say("WARN", f"text {t['j']} up {on:.2f}s for {words} words (about {need:.1f}s to read)")
    T = m["text"]
    for i in range(len(T)):
        for j in range(i + 1, len(T)):
            a_, b_ = T[i], T[j]
            if a_["start"] < b_["end"] and b_["start"] < a_["end"]:
                ax, ay, aw, ah = a_["box"]
                bx, by, bw, bh = b_["box"]
                close = ay < by + bh + 40 and by < ay + ah + 40 and ax < bx + bw and bx < ax + aw
                wa, wb = set(re.findall(r"\w+", a_["text"].lower())), set(re.findall(r"\w+", b_["text"].lower()))
                same = len(wa & wb) >= max(2, min(len(wa), len(wb)) // 2)
                # The rule is about the same words twice (a caption echoing a callout). A designed pair,
                # a small label over a hero line or a headline with the handle, is fine.
                if same:
                    say("FAIL" if close else "WARN", f"text {i} and {j} on screen together saying the same words"
                        + (" and touching" if close else ""))
                elif close and not (a_.get("pair") or b_.get("pair")):
                    say("WARN", f"text {i} and {j} touch (within 40 px); mark one \"pair\": true if it's designed")

    for w in m.get("warnings", []):
        say("WARN", "render: " + w)
    fails, warns = results.count("FAIL"), results.count("WARN")
    print(f"\n{'FAIL' if fails else 'OK'}: {fails} fail, {warns} warn")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
