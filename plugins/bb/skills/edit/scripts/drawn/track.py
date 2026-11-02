#!/usr/bin/env python3
"""Finds where a coloured thing sits in a video, frame by frame, so a drawing can follow it.
    PY track.py <video> --min 150,0,60 --max 255,110,255 [--fps 10]
--min and --max are the red, green and blue limits of the colour. Prints: time, centre and box in 1080-wide
frame coordinates, ready to paste into a kf() track in anim.html."""
import argparse, os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import bbenv  # noqa: E402
bbenv.need("numpy")
import numpy as np  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("video")
ap.add_argument("--min", required=True, help="r,g,b lower limits")
ap.add_argument("--max", required=True, help="r,g,b upper limits")
ap.add_argument("--fps", type=int, default=10)
a = ap.parse_args()
W, H = 270, 480
SCALE = 1080 / W
lo = np.array([int(v) for v in a.min.split(",")])
hi = np.array([int(v) for v in a.max.split(",")])
raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", a.video, "-vf", f"fps={a.fps},scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
n = len(raw) // (W * H * 3)
fr = np.frombuffer(raw, np.uint8).reshape(n, H, W, 3)
mask = ((fr >= lo) & (fr <= hi)).all(axis=3)
for i in range(n):
    ys, xs = np.nonzero(mask[i])
    t = i / a.fps
    if len(xs) < 12:
        print(f"{t:.1f} -")
        continue
    print(f"{t:.1f} cx={int(xs.mean() * SCALE)} cy={int(ys.mean() * SCALE)} "
          f"box=({int(xs.min() * SCALE)},{int(ys.min() * SCALE)})-({int(xs.max() * SCALE)},{int(ys.max() * SCALE)}) n={len(xs)}")
