#!/usr/bin/env python3
"""reframe.py: the 4:5 Feed master (1080x1350) from the same EDL, not a crop of the 9:16 file.

    python3 reframe.py job/edl.json [--draft]

Each shot's picture is framed exactly as in the 9:16, then a 1350-row window is taken from it:
"y45" on the shot is the window's top row on the 1920 frame (default 285, the centre; 0 keeps
the top, 570 the bottom). Text is laid out again for the 4:5: by default it keeps its place on
the picture (y minus the window top) and is pulled inside a 40 px margin; "y45" on a text item
sets its centre row on the 1350 frame directly. Audio is copied from the 9:16 master, so run
cut.py first. Writes <slug>-4x5.mp4 and <slug>-4x5.json.
"""
import os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cut  # noqa: E402


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    edl_path = os.path.abspath(argv[0])
    edl = cut.load_edl(edl_path)
    edl_dir = os.path.dirname(edl_path)
    out_dir = os.path.join(edl_dir, edl.get("out_dir", "renders"))
    slug = edl.get("slug", "cut")
    master = os.path.join(out_dir, f"{slug}-9x16.mp4")
    if not os.path.exists(master):
        cut.die(f"no 9:16 master at {master}; run cut.py first so both masters share one audio stream")
    m = cut.plan(edl, edl_dir, "4x5")
    out = os.path.join(out_dir, f"{slug}-4x5.mp4")
    with tempfile.TemporaryDirectory(prefix="reframe-") as tmp:
        cut.render_text_pngs(m, tmp)
        cut.place_text(m)
        pic = os.path.join(tmp, "pic.mp4")
        subprocess.run(cut.build_cmd(m, pic, draft="--draft" in argv, with_audio=False), check=True)
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", "-i", pic, "-i", master,
                        "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart",
                        out], check=True)
    cut.write_manifest(m, os.path.join(out_dir, f"{slug}-4x5.json"), dict(file=out, audio_from=master))
    for w in m["warnings"]:
        print("warning:", w)
    print(f"wrote {out} ({m['total']:.2f}s)")


if __name__ == "__main__":
    main(sys.argv[1:])
