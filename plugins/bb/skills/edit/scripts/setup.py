#!/usr/bin/env python3
"""Checks this Mac has everything /bb:edit needs, and fills in what it can. Safe to re-run.

    python3 setup.py --data "<plugin data folder>"             # check, and build the Python tools if needed
    python3 setup.py --data "<plugin data folder>" --download-models   # also fetch the sound models (about 490 MB)
    python3 setup.py --data "<plugin data folder>" --download-large    # also fetch the bigger whisper model (1.6 GB)
    python3 setup.py --data "<plugin data folder>" --no-build          # only look, change nothing

Prints one plain line per item, each with the exact fix, then READY or NOT READY. Exit 0 only when READY.
Everything it makes goes in the data folder, which survives plugin updates. Nothing is sent anywhere.
Standard library only, because it runs before the Python tools exist."""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request, venv, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bbenv  # noqa: E402

REQUIREMENTS = os.path.join(HERE, "requirements.txt")
# Python versions the pinned tools have wheels for, best first. See requirements.txt.
PYTHONS = ["3.12", "3.13", "3.14", "3.11"]
SELFTEST = """
import numpy, scipy, librosa, soundfile, matplotlib, PIL
from ai_edge_litert.interpreter import Interpreter
"""
MODELS = {
    "ggml-small.en.bin": ("https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin", 487_614_201),
    "yamnet.tflite": ("https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/latest/yamnet.tflite", 4_126_810),
}
LARGE = {"ggml-large-v3-turbo.bin": ("https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin", 1_624_555_275)}
def find_chrome():
    """Copy-free headless Chrome first: every launch of the Chrome app leaves a 1.4 GB code_sign_clone copy on disk."""
    import glob
    c = [os.environ.get("CHROME_PATH"), os.environ.get("CHROME_BIN"), os.path.expanduser("~/.local/bin/chrome-headless")]
    c += sorted(glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell")), reverse=True)
    c.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return next((p for p in c if p and os.path.exists(p)), c[-1])


CHROME = find_chrome()
BREW_HINT = "" if shutil.which("brew") else " (no Homebrew yet: install it first from https://brew.sh)"


class Report:
    def __init__(self):
        self.blocked = False

    def ok(self, item, note=""):
        print(f"OK       {item}{f': {note}' if note else ''}", flush=True)

    def missing(self, item, fix):
        self.blocked = True
        print(f"MISSING  {item} -> {fix}", flush=True)

    def optional(self, item, note):
        print(f"OPTIONAL {item}: {note}", flush=True)


def out(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return ""


def check_ffmpeg(rep):
    fix = "brew install ffmpeg" + BREW_HINT
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            rep.missing(tool, fix)
            return
    filters, encoders = out(["ffmpeg", "-hide_banner", "-filters"]), out(["ffmpeg", "-hide_banner", "-encoders"])
    lacking = [n for n in ("loudnorm", "alimiter", "ebur128", "overlay") if n not in filters]
    lacking += [n for n in ("libx264", "aac") if n not in encoders]
    if lacking:
        rep.missing("ffmpeg", f"this build has no {', '.join(lacking)}: {fix}")
        return
    words = out(["ffmpeg", "-version"]).split()
    rep.ok("ffmpeg and ffprobe", words[2] if len(words) > 2 else "")


def check_whisper(rep):
    if shutil.which("whisper-cli"):
        rep.ok("whisper-cli")
    else:
        rep.missing("whisper-cli", "brew install whisper-cpp" + BREW_HINT)


def check_mac_tools(rep, data, build):
    if sys.platform != "darwin":
        rep.missing("a Mac", "/bb:edit draws its text with Apple's tools and converts iPhone HDR with avconvert, so it needs macOS")
        return
    if shutil.which("avconvert"):
        rep.ok("avconvert", "converts iPhone HDR")
    else:
        rep.missing("avconvert", "it ships with macOS; update macOS")
    if not shutil.which("swiftc"):
        rep.missing("swift", "xcode-select --install")
        return
    src = os.path.join(HERE, "text_png.swift")
    binary = os.path.join(data, "bin", "text_png")
    if os.path.exists(binary) and os.path.getmtime(binary) >= os.path.getmtime(src):
        rep.ok("swift", "text tool ready")
    elif not build:
        rep.ok("swift", "text tool not compiled yet")
    else:
        os.makedirs(os.path.dirname(binary), exist_ok=True)
        r = subprocess.run(["swiftc", "-O", src, "-o", binary], capture_output=True, text=True)
        if r.returncode:
            rep.missing("swift", "it couldn't compile the text tool. Run: xcode-select --install, then re-run this")
        else:
            rep.ok("swift", "text tool compiled")


def find_python():
    if os.environ.get("BB_PYTHON"):
        return os.environ["BB_PYTHON"]
    for v in PYTHONS:
        p = shutil.which(f"python{v}")
        if p:
            return p
    v = f"{sys.version_info[0]}.{sys.version_info[1]}"
    return sys.executable if v in PYTHONS else None


def requirements_text():
    with open(REQUIREMENTS, encoding="utf-8") as f:
        return f.read()


def record(data):
    try:
        return json.load(open(os.path.join(data, bbenv.RECORD), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def check_venv(rep, data, build):
    py = os.path.join(data, "venv", "bin", "python")
    same = record(data).get("requirements") == requirements_text()
    if os.path.exists(py) and same and subprocess.run([py, "-c", SELFTEST], capture_output=True).returncode == 0:
        rep.ok("python tools", out([py, "--version"]).strip())
        return
    base = find_python()
    if not base:
        rep.missing("python 3.11 to 3.14", "brew install python@3.12" + BREW_HINT)
        return
    if not build:
        rep.missing("python tools", "re-run this without --no-build (it builds them here, a few minutes)")
        return
    print(f"...      building the python tools with {base}. This takes a few minutes the first time.", flush=True)
    venv_dir = os.path.join(data, "venv")
    if os.path.isdir(venv_dir):
        shutil.rmtree(venv_dir)
    os.makedirs(data, exist_ok=True)
    r = subprocess.run([base, "-m", "venv", venv_dir], capture_output=True, text=True)
    if r.returncode:
        rep.missing("python tools", f"couldn't make a venv with {base}: brew install python@3.12, then re-run this")
        return
    r = subprocess.run([py, "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "--only-binary=:all:", "-r", REQUIREMENTS],
                       capture_output=True, text=True)
    if r.returncode:
        tail = (r.stderr or r.stdout).strip().splitlines()[-1:]
        rep.missing("python tools", f"install failed ({' '.join(tail)[:160]}). Check your internet, or try: brew install python@3.12, then re-run this")
        return
    r = subprocess.run([py, "-c", SELFTEST], capture_output=True, text=True)
    if r.returncode:
        tail = (r.stderr or "").strip().splitlines()[-1:]
        rep.missing("python tools", f"installed but won't load ({' '.join(tail)[:160]}). Try: brew install python@3.12, then re-run this")
        return
    rep.ok("python tools", "built")
    save_record(data, requirements=requirements_text())


def save_record(data, **fields):
    rec = record(data)
    rec.update(fields, python=os.path.join(data, "venv", "bin", "python"), models=os.path.join(data, "models"),
               checked=time.strftime("%Y-%m-%d"))
    os.makedirs(data, exist_ok=True)
    with open(os.path.join(data, bbenv.RECORD), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)


def download(url, path, size):
    print(f"...      downloading {os.path.basename(path)} ({size / 1e6:,.0f} MB)", flush=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    part = path + ".part"
    got, shown = 0, -1
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            step = int(got * 4 / size)
            if step != shown and step < 4:
                shown = step
                print(f"...      {step * 25}%", flush=True)
    if got != size:
        os.remove(part)
        raise OSError(f"got {got} bytes, expected {size}")
    os.replace(part, path)


def ready(path, size):
    return os.path.exists(path) and os.path.getsize(path) == size


def labels_from_yamnet(models):
    """The class names ship inside the YAMNet file."""
    target = os.path.join(models, "yamnet_labels.txt")
    if os.path.exists(target) or not os.path.exists(os.path.join(models, "yamnet.tflite")):
        return
    with zipfile.ZipFile(os.path.join(models, "yamnet.tflite")) as z:
        with open(target, "wb") as f:
            f.write(z.read("yamnet_label_list.txt"))


def check_models(rep, data, a):
    models = os.path.join(data, "models")
    fetch = dict(MODELS) if a.download_models else {}
    if a.download_large:
        fetch.update(LARGE)
    for name, (url, size) in fetch.items():
        if not ready(os.path.join(models, name), size):
            try:
                download(url, os.path.join(models, name), size)
            except OSError as e:
                rep.missing(name, f"download failed ({e}). Check your internet and re-run with --download-models")
    labels_from_yamnet(models)
    want = [n for n, (_, s) in MODELS.items() if not ready(os.path.join(models, n), s)]
    if not want and not os.path.exists(os.path.join(models, "yamnet_labels.txt")):
        want = ["yamnet_labels.txt"]
    if want:
        rep.missing("sound models", "about 490 MB. Re-run this with --download-models")
    else:
        rep.ok("sound models", "whisper small.en, YAMNet")
    if ready(os.path.join(models, "ggml-large-v3-turbo.bin"), LARGE["ggml-large-v3-turbo.bin"][1]):
        rep.ok("bigger whisper model")
    else:
        rep.optional("bigger whisper model", "a clearer read of a doubtful line, and other languages (1.6 GB). Add it with --download-large")


def check_optional(rep):
    if os.path.exists(CHROME):
        rep.ok("chrome", f"for the PDF shoot pack and drawn animation ({os.path.basename(CHROME)})")
    else:
        rep.optional("google chrome", "only for the PDF shoot pack and drawn animation. Install from https://www.google.com/chrome")
    words = out(["node", "--version"]).strip().lstrip("v").split(".")
    if words[0].isdigit() and int(words[0]) >= 22:
        rep.ok("node", "for drawn animation")
    else:
        rep.optional("node 22 or newer", "only for drawn animation. brew install node")


def main():
    ap = argparse.ArgumentParser(description="Checks this Mac for /bb:edit")
    ap.add_argument("--data", help="where the Python tools and models live; /bb:edit passes this")
    ap.add_argument("--download-models", action="store_true", help="fetch the sound models (about 490 MB)")
    ap.add_argument("--download-large", action="store_true", help="also fetch the bigger whisper model (1.6 GB)")
    ap.add_argument("--no-build", action="store_true", help="only look, change nothing")
    a = ap.parse_args()
    data = a.data or bbenv.data_dir()
    os.environ["BB_EDIT_DATA"] = data

    rep = Report()
    check_ffmpeg(rep)
    check_whisper(rep)
    check_mac_tools(rep, data, not a.no_build)
    check_venv(rep, data, not a.no_build)
    check_models(rep, data, a)
    check_optional(rep)
    if rep.blocked:
        print("\nNOT READY. Run the fixes above, then run this again.")
        sys.exit(1)
    save_record(data)
    print(f"\nREADY. Run the Python scripts with: {os.path.join(data, 'venv', 'bin', 'python')}")


if __name__ == "__main__":
    main()
