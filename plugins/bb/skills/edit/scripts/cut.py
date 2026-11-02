#!/usr/bin/env python3
"""cut.py: edl.json -> 1080x1920 master with music, text and loudness at about -14 LUFS.

    python3 cut.py job/edl.json                # final quality
    python3 cut.py job/edl.json --draft        # fast encode for the rough cut
    python3 cut.py job/edl.json --beats        # print the music's beat grid and exit
    python3 cut.py job/edl.json --dry-run      # print the ffmpeg command and exit

Writes <out_dir>/<slug>-9x16.mp4 and <slug>-9x16.json (the manifest check_cut.py reads).
Python 3 stdlib only; ffmpeg/ffprobe from Homebrew; text via text_png.swift (CoreText),
because this ffmpeg has no drawtext. The EDL shape is in references/formats.md.
"""
import json, math, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
sys.path.insert(0, HERE)
import bbenv  # noqa: E402
TEXT_BIN = os.path.join(bbenv.data_dir(), "bin", "text_png")
SIZES = {"9x16": (1080, 1920), "4x5": (1080, 1350)}

# Text styles. An EDL "styles" block overrides or adds keys per style.
STYLES = {
    "caption": dict(font="Geist-Black.ttf", size=76, color="#FFFFFF", shadow=[0, 5], tracking=-0.01,
                    leading=0.9, max_width=900, upper=True, y=1250),
    "title":   dict(font="Geist-Black.ttf", size=110, color="#FFFFFF", shadow=[0, 6], tracking=-0.02,
                    leading=0.88, max_width=960, upper=True, y=640),
    "callout": dict(font="Geist-Black.ttf", size=56, color="#000000", plate="#EDECE8", pad=22,
                    tracking=-0.01, leading=0.9, max_width=820, upper=True, y=430),
    "aside":   dict(font="PlayfairDisplay-Italic.otf", size=84, color="#FFFFFF", shadow=[0, 3],
                    max_width=880, upper=False, y=1120),
    "card":    dict(font="Geist-Black.ttf", size=96, color="#FFFFFF", tracking=-0.02, leading=0.88,
                    max_width=940, upper=True, y=900, full=True),
}


def die(msg):
    sys.exit(f"cut.py: {msg}")


def load_edl(path):
    with open(path) as f:
        txt = f.read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml
        except ImportError:
            die("YAML EDL needs PyYAML; write edl.json instead")
        return yaml.safe_load(txt)
    return json.loads(txt)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "stream=codec_type,width,height,pix_fmt,color_transfer,r_frame_rate,duration:"
                          "stream_side_data=rotation:format=duration", "-of", "json", path],
                         capture_output=True, text=True)
    if out.returncode:
        die(f"cannot read {path}: {out.stderr.strip()}")
    j = json.loads(out.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    a = any(s["codec_type"] == "audio" for s in j["streams"])
    if v is None:
        die(f"no video stream in {path}")
    w, h = v["width"], v["height"]
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) in (90, 270):
        w, h = h, w
    fdur = float(j["format"].get("duration", 0))
    # The picture can end before the file does (audio runs on): cut against the picture's own end.
    vdur = float(v.get("duration") or fdur)
    return dict(w=w, h=h, pix=v.get("pix_fmt", ""), trc=v.get("color_transfer", ""),
                dur=min(vdur, fdur) if fdur else vdur, audio=a)


def beat_grid(music, total_from_start=600):
    """Beat times in music-file seconds, from a list or from bpm + offset."""
    if music.get("beats"):
        return sorted(float(b) for b in music["beats"])
    if music.get("bpm"):
        step = 60.0 / float(music["bpm"])
        off = float(music.get("offset", 0))
        return [off + i * step for i in range(int(total_from_start / step))]
    return []


def plan(edl, edl_dir, fmt="9x16"):
    """Resolve paths, probe clips, snap cuts to beats, place text. Returns the manifest."""
    W, H = SIZES[fmt]
    fps = int(edl.get("fps", 30))
    rel = lambda p: p if os.path.isabs(os.path.expanduser(p)) else os.path.join(edl_dir, p)
    music = edl.get("music") or {}
    mstart = float(music.get("start", 0))
    mat = float(music.get("at", 0))                  # timeline second the music comes in
    beats = [b - mstart + mat for b in beat_grid(music)] if music else []
    snap_mode = music.get("snap", "marked")          # marked | all | none
    window = float(music.get("snap_window", 0.25))
    warnings, snaps, shots = [], [], []
    t = 0.0
    ideal = 0.0      # the EDL's own time, so rounding to frames never accumulates
    for i, s in enumerate(edl["shots"]):
        clip = os.path.expanduser(rel(s["clip"]))
        if not os.path.exists(clip):
            die(f"shot {i}: clip not found: {clip}")
        info = probe(clip)
        if info["trc"] in ("arib-std-b67", "smpte2084") and not s.get("allow_hdr"):
            die(f"shot {i}: {os.path.basename(clip)} is HDR ({info['trc']}). Convert to SDR first "
                f"with scripts/proxies.sh (avconvert), then point the EDL at the SDR file.")
        speed = float(s.get("speed", 1))
        cin, cout = float(s["in"]), float(s["out"])
        last = info["dur"] - 1.0 / fps          # the last whole frame
        if cout > last + 0.005:
            short = cout - last
            warnings.append(f"shot {i}: out {cout} is past the picture's last frame ({last:.2f}s in "
                            f"{os.path.basename(clip)}); {short:.2f}s of held last frame fills it. "
                            f"Pull 'out' back or start earlier if a freeze would show")
            print(f"warning: shot {i} runs {short:.2f}s past the end of {os.path.basename(clip)}; "
                  f"the last frame is held", file=sys.stderr)
        dur = (cout - cin) / speed
        want_snap = s.get("snap", snap_mode == "all") and snap_mode != "none" and beats
        if want_snap:
            end = t + dur
            near = min(beats, key=lambda b: abs(b - end))
            delta = near - end
            new_out = cout + delta * speed
            if abs(delta) <= window and dur + delta >= 0.2 and new_out <= info["dur"]:
                snaps.append(dict(shot=i, moved=round(delta, 3), cut_at=round(near, 3)))
                cout, dur = new_out, dur + delta
            else:
                warnings.append(f"shot {i}: no beat within {window}s of its cut ({end:.2f}s), left as is")
        # keep every cut on the frame grid, so small frame losses can't add up and drift the picture off the sound
        ideal += dur
        dur = round(ideal * fps) / fps - t
        audio = bool(s.get("audio", False)) and info["audio"]
        if s.get("audio") and speed != 1:
            warnings.append(f"shot {i}: speed {speed} with its own audio; voice is never sped or slowed, "
                            f"so this shot's audio is muted")
            audio = False
        shots.append(dict(i=i, clip=clip, info=info, cin=round(cin, 3), cout=round(cout, 3), speed=speed,
                          dur=round(dur, 4), start=round(t, 4), end=round(t + dur, 4), audio=audio,
                          gain_db=float(s.get("gain_db", 0)), punch=s.get("punch", False),
                          focus=s.get("focus", [0.5, 0.5]), x=float(s.get("x", 0.5)),
                          y=float(s.get("y", 0.5)), y45=s.get("y45"), flash=int(s.get("flash", 0)),
                          flash_color=s.get("flash_color", "white"), note=s.get("note", ""),
                          flash_curve=s.get("flash_curve"), look=s.get("look", edl.get("look")), off_beat=s.get("off_beat")))
        t += dur
    total = round(t, 4)

    styles = {k: dict(v) for k, v in STYLES.items()}
    for k, v in (edl.get("styles") or {}).items():
        styles.setdefault(k, dict(STYLES["caption"])).update(v)
    accent_color = edl.get("accent_color", "#EE7631")
    texts = []
    for j, tx in enumerate(edl.get("text", [])):
        st = dict(styles.get(tx.get("style", "caption"), styles["caption"]))
        st.update({k: v for k, v in tx.items() if k in ("size", "color", "font", "plate", "max_width", "shadow")})
        if "shot" in tx:                       # timing relative to a shot survives beat snaps
            sh = shots[int(tx["shot"])]
            start = sh["start"] + float(tx.get("at", 0))
            end = start + float(tx["dur"]) if "dur" in tx else sh["end"]
        else:
            start, end = float(tx["start"]), float(tx["end"])
        end = min(end, total)
        text = tx["text"].upper() if st.get("upper") else tx["text"]
        texts.append(dict(j=j, text=text, style=tx.get("style", "caption"), start=round(start, 3),
                          end=round(end, 3), y=float(tx.get("y", st["y"])), y45=tx.get("y45"),
                          x=tx.get("x"), accent=[a.upper() if st.get("upper") else a for a in tx.get("accent", [])],
                          st=st, accent_color=tx.get("accent_color", accent_color), pair=bool(tx.get("pair")),
                          rotate=float(tx.get("rotate", 0)), slap=bool(tx.get("slap", False)),
                          image=tx.get("image")))
    mixf = edl.get("mix_file")
    return dict(fmt=fmt, W=W, H=H, fps=fps, shots=shots, texts=texts, total=total, music=music,
                mix_file=os.path.expanduser(rel(mixf)) if mixf else None,
                music_map=edl.get("music_map"), sound_events=edl.get("sound_events", []), mix=edl.get("mix_info", {}),
                music_file=os.path.expanduser(rel(music["file"])) if music.get("file") else None,
                snaps=snaps, warnings=warnings, beats=[round(b, 3) for b in beats if 0 <= b <= total])


def ensure_text_bin():
    src = os.path.join(HERE, "text_png.swift")
    if not os.path.exists(TEXT_BIN) or os.path.getmtime(TEXT_BIN) < os.path.getmtime(src):
        os.makedirs(os.path.dirname(TEXT_BIN), exist_ok=True)
        r = subprocess.run(["swiftc", "-O", src, "-o", TEXT_BIN], capture_output=True, text=True)
        if r.returncode:
            die("could not compile text_png.swift:\n" + r.stderr)


def render_text_pngs(m, tmp):
    if not m["texts"]:
        return
    ensure_text_bin()
    specs = []
    for tx in m["texts"]:
        st = tx["st"]
        font = st["font"] if os.path.isabs(st["font"]) else os.path.join(FONTS, st["font"])
        specs.append(dict(out=os.path.join(tmp, f"text{tx['j']}.png"), text=tx["text"], font=font,
                          size=st["size"], color=st["color"], accent=tx["accent"],
                          accent_color=tx["accent_color"], shadow=st.get("shadow"),
                          shadow_color=st.get("shadow_color", "#000000B3"), shadow_blur=st.get("shadow_blur", 0), plate=st.get("plate"),
                          pad=st.get("pad", 16), leading=st.get("leading", 0.95),
                          tracking=st.get("tracking", 0), max_width=st.get("max_width", 900),
                          stroke=st.get("stroke", 0), stroke_color=st.get("stroke_color", "#000000")))
    spec_path = os.path.join(tmp, "text.json")
    with open(spec_path, "w") as f:
        json.dump(specs, f)
    r = subprocess.run([TEXT_BIN, spec_path], capture_output=True, text=True)
    if r.returncode:
        die("text render failed: " + r.stderr)
    for tx, res in zip(m["texts"], json.loads(r.stdout)):
        tx["png"], tx["w"], tx["h"] = res["out"], res["w"], res["h"]
    for tx in m["texts"]:
        ss = tx["st"].get("soft_shadow")     # [[blur px, opacity], ...] in soft_shadow_color: readable with no box
        if ss:
            from PIL import Image, ImageFilter
            im = Image.open(tx["png"]).convert("RGBA")
            col = tx["st"].get("soft_shadow_color", "#00252C").lstrip("#")
            rgb = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4))
            base = Image.new("RGBA", im.size, (0, 0, 0, 0))
            for r_, op in ss:
                al = im.getchannel("A").filter(ImageFilter.GaussianBlur(r_)).point(lambda v: min(255, int(v * op * 2.2)))
                lay = Image.new("RGBA", im.size, rgb + (0,))
                lay.putalpha(al)
                base = Image.alpha_composite(base, lay)
            Image.alpha_composite(base, im).save(tx["png"])
    for tx in m["texts"]:
        if tx.get("rotate") or tx.get("slap"):
            from PIL import Image            # only these two extras need Pillow (the pack's Python has it)
            im = Image.open(tx["png"]).convert("RGBA")
            if tx.get("rotate"):
                im = im.rotate(tx["rotate"], expand=True, resample=Image.BICUBIC)
                im.save(tx["png"])
                tx["w"], tx["h"] = im.size
            if tx.get("slap"):               # a hard pop: two frames big, one frame small, then home
                tx["slap_png"] = []
                for k, sc in enumerate((min(1.16, 1050 / im.width) if im.width > 900 else 1.16, 0.97)):
                    b = im.resize((int(im.width * sc), int(im.height * sc)), Image.BICUBIC)
                    pth = os.path.join(tmp, f"text{tx['j']}-s{k}.png")
                    b.save(pth)
                    tx["slap_png"].append((pth, b.width, b.height, (2, 1)[k]))


def window45(sh):
    return int(sh["y45"]) if sh["y45"] is not None else (1920 - 1350) // 2


def place_text(m):
    """Box for each text in output pixels. y in the EDL is the box centre on the 9:16 frame."""
    W, H = m["W"], m["H"]
    for tx in m["texts"]:
        w, h = tx["w"], tx["h"]
        x = int(tx["x"] - w / 2) if tx["x"] is not None else (W - w) // 2
        if m["fmt"] == "4x5":
            if tx["y45"] is not None:
                cy = float(tx["y45"])
            else:   # keep it where it sat on the picture: same shot window the picture uses
                sh = next((s for s in m["shots"] if s["start"] <= tx["start"] < s["end"]), m["shots"][-1])
                cy = tx["y"] - window45(sh)
            cy = min(max(cy, 40 + h / 2), H - 40 - h / 2)
        else:
            cy = tx["y"]
        tx["box"] = [x, int(cy - h / 2), w, h]


def shot_video_filter(sh, m, idx):
    W, H, fps = m["W"], m["H"], m["fps"]
    info = sh["info"]
    # The picture is always framed for 9:16 first; the 4:5 is a window on that picture,
    # so punch-ins and framing match between the two masters.
    FW, FH = 1080, 1920
    p = sh["punch"]
    p = 1.0 if p in (False, None) else (1.08 if p is True else float(p))
    s = max(FW / info["w"], FH / info["h"])
    sw, shh = math.ceil(info["w"] * s / 2) * 2, math.ceil(info["h"] * s / 2) * 2
    # cover crop for 9:16 at x/y (0..1), then a static punch-in about the focus point
    cx = round((sw - FW) * sh["x"])
    cy = round((shh - FH) * sh["y"])
    rng = "in_range=full:out_range=tv" if info["pix"].startswith("yuvj") else "in_range=tv:out_range=tv"
    f = [f"setpts=(PTS-STARTPTS)/{sh['speed']}", f"fps={fps}",
         f"scale={sw}:{shh}:flags=lanczos:{rng}", f"crop={FW}:{FH}:{cx}:{cy}"]
    if p != 1.0:
        pw, ph = math.ceil(FW * p / 2) * 2, math.ceil(FH * p / 2) * 2
        fx, fy = sh["focus"]
        f += [f"scale={pw}:{ph}:flags=lanczos",
              f"crop={FW}:{FH}:{round((pw - FW) * fx)}:{round((ph - FH) * fy)}"]
    if m["fmt"] == "4x5":
        f.append(f"crop={W}:{H}:0:{window45(sh)}")
    if sh.get("look"):
        f.append(sh["look"])
    if sh.get("flash_curve"):                # a photo flash decays: e.g. [1, .75, .4, .15] per frame
        for n_, a_ in enumerate(sh["flash_curve"]):
            f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={sh['flash_color']}@{a_}:t=fill:"
                     f"enable='between(t,{n_ / fps - 0.001:.4f},{(n_ + 1) / fps - 0.002:.4f})'")
    elif sh["flash"]:
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={sh['flash_color']}:t=fill:"
                 f"enable='lt(t,{sh['flash'] / fps:.4f})'")
    # tpad holds the last frame if the source runs out early, so the shot (and the master) keeps its length
    f += ["setsar=1", "format=yuv420p", f"tpad=stop_mode=clone:stop_duration={sh['dur'] + 0.5:.3f}",
          f"trim=duration={sh['dur']:.4f}", "setpts=PTS-STARTPTS"]
    return f"[{idx}:v]" + ",".join(f) + f"[v{sh['i']}]"


def shot_audio_filter(sh, idx):
    d = sh["dur"]
    if sh["audio"]:
        fo = max(d - 0.015, 0)
        return (f"[{idx}:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"volume={sh['gain_db']}dB,apad,atrim=0:{d:.4f},afade=t=in:d=0.015,afade=t=out:st={fo:.4f}:d=0.015"
                f"[a{sh['i']}]")
    return f"anullsrc=r=48000:cl=stereo,atrim=0:{d:.4f},aformat=sample_fmts=fltp[a{sh['i']}]"


def build_cmd(m, out_path, draft=False, with_audio=True):
    args = ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y"]
    fc = []
    n = 0
    mix_file = m.get("mix_file") if with_audio else None
    if mix_file:              # the sound is already built by mix.py; only the picture is assembled here
        with_audio = False
    for sh in m["shots"]:
        src_len = sh["dur"] * sh["speed"] + 0.1
        args += ["-ss", f"{sh['cin']:.4f}", "-t", f"{src_len:.4f}", "-i", sh["clip"]]
        fc.append(shot_video_filter(sh, m, n))
        if with_audio:
            fc.append(shot_audio_filter(sh, n))
        n += 1
    N = len(m["shots"])
    if with_audio:
        fc.append("".join(f"[v{i}][a{i}]" for i in range(N)) + f"concat=n={N}:v=1:a=1[vcat][acat]")
    else:
        fc.append("".join(f"[v{i}]" for i in range(N)) + f"concat=n={N}:v=1:a=0[vcat]")
    last = "vcat"
    for tx in m["texts"]:
        x, y = tx["box"][0], tx["box"][1]
        st0 = tx["start"]
        for k, (pth, bw, bh, frames) in enumerate(tx.get("slap_png", [])):
            args += ["-i", pth]
            d0 = frames / m["fps"]
            fc.append(f"[{last}][{n}:v]overlay=x={x + (tx['w'] - bw) // 2}:y={y + (tx['h'] - bh) // 2}:eof_action=repeat:"
                      f"enable='between(t,{st0:.3f},{st0 + d0 - 0.001:.3f})'[s{tx['j']}_{k}]")
            last = f"s{tx['j']}_{k}"
            st0 += d0
            n += 1
        args += ["-i", tx["png"]]
        fc.append(f"[{last}][{n}:v]overlay=x={x}:y={y}:eof_action=repeat:"
                  f"enable='between(t,{st0:.3f},{tx['end'] - 0.001:.3f})'[t{tx['j']}]")
        last = f"t{tx['j']}"
        n += 1
    total = m["total"]
    if with_audio:
        mu = m["music"]
        voice = any(s["audio"] for s in m["shots"])
        if m["music_file"]:
            args += ["-ss", f"{float(mu.get('start', 0)):.3f}", "-i", m["music_file"]]
            gain = float(mu.get("gain_db", -14 if voice else 0))
            fi, fo = float(mu.get("fade_in", 0.05)), float(mu.get("fade_out", 1.0))
            fc.append(f"[{n}:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                      f"atrim=0:{total:.4f},volume={gain}dB,afade=t=in:d={fi},"
                      f"afade=t=out:st={max(total - fo, 0):.4f}:d={fo}[mus]")
            fc.append(f"[acat][mus]amix=inputs=2:duration=first:normalize=0[amix]")
            amix = "amix"
        else:
            amix = "acat"
        fc.append(f"[{amix}]apad,atrim=0:{total:.4f}[aout]")
    if mix_file:
        args += ["-i", mix_file]
    args += ["-filter_complex", ";".join(fc), "-map", f"[{last}]"]
    if with_audio:
        args += ["-map", "[aout]", "-c:a", "pcm_s16le"]
    elif mix_file:
        args += ["-map", f"{n}:a", "-c:a", "pcm_s24le"]
    args += ["-c:v", "libx264", "-preset", "veryfast" if draft else "medium", "-crf", "22" if draft else "17",
             "-pix_fmt", "yuv420p", "-r", str(m["fps"]), "-t", f"{total:.4f}",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
             # newer ffmpeg can drop the tags above when the source has none; this writes them into the stream itself
             "-bsf:v", "h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1",
             out_path]
    return args


LIMIT_DB = -1.5   # sample-peak ceiling at 4x rate; leaves room for AAC's overshoot under -1 dBTP


def true_peak(path):
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", path, "-vn", "-af", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True)
    pk = re.findall(r"Peak:\s+(-?[\d.]+|-inf) dBFS", r.stderr)
    return float(pk[-1]) if pk and pk[-1] != "-inf" else None


def loudnorm(src, dst, target=-14.0, total=None, limit_db=None):
    """Two-pass EBU R128 to `target` LUFS in linear mode, then a limiter run at 192 kHz (so peaks
    between samples are caught), then AAC. Returns (measurement, true peak of the file written).
    Linear loudnorm alone can't promise the ceiling (one ad came out at -0.4 dBTP), and AAC
    adds its own overshoot, so the file is measured and, if it's still over -1 dBTP, re-encoded
    with the ceiling lowered by the overshoot. Two retries at most; loudness moves by a tenth or so."""
    ln = f"loudnorm=I={target}:TP=-1:LRA=11"
    r = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", src, "-af", ln + ":print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    meas = json.loads(re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr)[-1])
    ln2 = (f"{ln}:measured_I={meas['input_i']}:measured_TP={meas['input_tp']}:measured_LRA={meas['input_lra']}"
           f":measured_thresh={meas['input_thresh']}:offset={meas['target_offset']}:linear=true")
    ceiling, tp = (LIMIT_DB if limit_db is None else limit_db), None
    for _ in range(3):
        subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", "-y", "-i", src, "-map", "0:v",
                        "-map", "0:a", "-c:v", "copy", "-af", ln2 + ",aresample=192000,"
                        f"alimiter=limit={10 ** (ceiling / 20):.4f}:attack=1:release=60:level=false:latency=true,"
                        "aresample=48000", "-c:a", "aac", "-b:a", "192k",
                        # an exact -t, not -shortest: with the limiter's buffering, -shortest cut the
                        # picture 0.13 s early in testing
                        *(["-t", f"{total:.4f}"] if total else ["-shortest"]), "-movflags", "+faststart", dst],
                       check=True)
        tp = true_peak(dst)
        if tp is None or tp <= -1.0:
            break
        ceiling -= (tp + 1.0) + 0.3
    return meas, tp


def write_manifest(m, path, extra):
    keep = dict(fmt=m["fmt"], size=[m["W"], m["H"]], fps=m["fps"], duration=m["total"],
                shots=[{k: v for k, v in s.items() if k != "info"} for s in m["shots"]],
                text=[{k: v for k, v in t.items() if k not in ("st", "png", "slap_png")} | {"full": bool(t["st"].get("full"))}
                      for t in m["texts"]],
                music=m["music"], beats=m["beats"], snaps=m["snaps"], warnings=m["warnings"],
                music_map=m.get("music_map"), sound_events=m.get("sound_events", []), mix=m.get("mix", {}))
    keep.update(extra)
    with open(path, "w") as f:
        json.dump(keep, f, indent=1)


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return
    edl_path = os.path.abspath(argv[0])
    edl = load_edl(edl_path)
    edl_dir = os.path.dirname(edl_path)
    m = plan(edl, edl_dir, "9x16")
    if "--beats" in argv:
        print("beats in timeline seconds (music start subtracted):")
        print(" ".join(f"{b:.2f}" for b in m["beats"]))
        print("cuts after snapping:", " ".join(f"{s['end']:.2f}" for s in m["shots"][:-1]))
        return
    out_dir = os.path.join(edl_dir, edl.get("out_dir", "renders"))
    os.makedirs(out_dir, exist_ok=True)
    slug = edl.get("slug", "cut")
    out = os.path.join(out_dir, f"{slug}-9x16.mp4")
    with tempfile.TemporaryDirectory(prefix="reelcut-") as tmp:
        render_text_pngs(m, tmp)
        place_text(m)
        pre = os.path.join(tmp, "pre.mov")
        cmd = build_cmd(m, pre, draft="--draft" in argv)
        if "--dry-run" in argv:
            print(" ".join(f"'{a}'" if " " in a or ";" in a else a for a in cmd))
            return
        subprocess.run(cmd, check=True)
        meas, tp = loudnorm(pre, out, float(edl.get("loudness", -14)), m["total"], edl.get("limit_db"))
    if tp is not None and tp > -1.0:
        m["warnings"].append(f"true peak {tp:.1f} dBTP after the limiter (want -1 or lower)")
    write_manifest(m, os.path.join(out_dir, f"{slug}-9x16.json"),
                   dict(file=out, loudness_in=meas["input_i"], loudness_target=edl.get("loudness", -14),
                        true_peak=tp))
    for w in m["warnings"]:
        print("warning:", w)
    for s in m["snaps"]:
        print(f"snap: shot {s['shot']} moved {s['moved']:+.3f}s to cut on the beat at {s['cut_at']:.2f}s")
    print(f"wrote {out} ({m['total']:.2f}s, {len(m['shots'])} shots, {len(m['texts'])} text)")


if __name__ == "__main__":
    main(sys.argv[1:])
