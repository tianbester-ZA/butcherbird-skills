#!/usr/bin/env python3
"""Checks this Mac has everything /bb:statics needs, and fills in what it can. Safe to re-run.

    python3 setup.py --data "<plugin data folder>"                        # check, and install the Chrome driver if needed
    python3 setup.py --data "<plugin data folder>" --kit <kit folder>     # also check a brand kit's fonts and logos
    python3 setup.py --data "<plugin data folder>" --kit <kit> --install-fonts   # copy the kit's fonts into ~/Library/Fonts
    python3 setup.py --data "<plugin data folder>" --install-vectorcraft  # download and install VectorCraft (about 310 MB)
    python3 setup.py --data "<plugin data folder>" --vectorcraft-cli <path>   # use a VectorCraft CLI you already have
    python3 setup.py --data "<plugin data folder>" --no-build             # only look, change nothing

Prints one plain line per item, each with the exact fix, then READY or NOT READY. Exit 0 only when READY.
Everything it installs goes in <data>/statics, which survives plugin updates, except two things a person asks for:
VectorCraft.app goes in ~/Applications, and --install-fonts copies fonts into ~/Library/Fonts.
VectorCraft is optional: it's the free editor for the files we hand over. Nothing is sent anywhere.
Standard library only."""
import argparse, glob, hashlib, json, os, plistlib, re, shutil, subprocess, sys, tempfile, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PLAYWRIGHT = "1.48.2"  # the Chrome driver; drives the Google Chrome already on the Mac, downloads no browser
CHROME = os.environ.get("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
VC_REPO = "storytold/vectorcraft"
VC_APPS = [os.path.expanduser("~/Applications/VectorCraft.app"), "/Applications/VectorCraft.app"]
BREW_HINT = "" if shutil.which("brew") else " (no Homebrew yet: install it first from https://brew.sh)"
FONTS = os.path.expanduser("~/Library/Fonts")


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


def out(cmd, env=None, timeout=120):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return 1, str(e)


def record(home):
    try:
        return json.load(open(os.path.join(home, "setup.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_record(home, **fields):
    rec = record(home)
    rec.update(fields, checked=time.strftime("%Y-%m-%d"))
    os.makedirs(home, exist_ok=True)
    with open(os.path.join(home, "setup.json"), "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=1)


def check_mac(rep):
    if sys.platform == "darwin":
        rep.ok("macOS")
    else:
        rep.missing("a Mac", "/bb:statics is built and tested on macOS")


def check_node(rep):
    code, text = out(["node", "--version"])
    v = text.strip().lstrip("v").split(".")
    if code or not v[0].isdigit():
        rep.missing("node", "brew install node" + BREW_HINT)
        return False
    if int(v[0]) < 18:
        rep.missing("node 18 or newer", f"you have {text.strip()}: brew upgrade node")
        return False
    if not shutil.which("npm"):
        rep.missing("npm", "it comes with node: brew reinstall node")
        return False
    rep.ok("node", text.strip())
    return True


def check_chrome(rep):
    if os.path.exists(CHROME):
        rep.ok("google chrome", "draws every ad")
        return True
    rep.missing("google chrome", "install it from https://www.google.com/chrome (or set CHROME_PATH)")
    return False


def check_driver(rep, home, build, node_ok, chrome_ok):
    pkg = os.path.join(home, "node_modules", "playwright-core", "package.json")
    have = None
    try:
        have = json.load(open(pkg, encoding="utf-8")).get("version")
    except (OSError, ValueError):
        pass
    if have != PLAYWRIGHT:
        if not node_ok:
            rep.missing("chrome driver", "install node first, then re-run this")
            return
        if not build:
            rep.missing("chrome driver", "re-run this without --no-build (it installs playwright-core here, under a minute)")
            return
        print(f"...      installing the chrome driver (playwright-core {PLAYWRIGHT}) into {home}", flush=True)
        os.makedirs(home, exist_ok=True)
        if not os.path.exists(os.path.join(home, "package.json")):
            with open(os.path.join(home, "package.json"), "w", encoding="utf-8") as f:
                json.dump({"name": "bb-statics-tools", "private": True, "type": "module"}, f)
        code, text = out(["npm", "install", "--prefix", home, "--no-audit", "--no-fund", "--loglevel=error", f"playwright-core@{PLAYWRIGHT}"], timeout=600)
        if code:
            tail = text.strip().splitlines()[-1:] or [""]
            rep.missing("chrome driver", f"npm install failed ({tail[0][:160]}). Check your internet and re-run this")
            return
    if not chrome_ok:
        rep.missing("chrome driver", "installed, but it needs Google Chrome to draw with")
        return
    env = dict(os.environ, BB_STATICS_DATA=home)
    code, text = out(["node", os.path.join(HERE, "lib", "smoke.mjs")], env=env)
    if code or "drew" not in text:
        rep.missing("chrome driver", f"installed but Chrome wouldn't draw a test page ({text.strip()[-200:]}). Quit and reopen Chrome, then re-run this")
        return
    rep.ok("chrome driver", f"playwright-core {PLAYWRIGHT}, test page drawn")


def app_version(app):
    try:
        with open(os.path.join(app, "Contents", "Info.plist"), "rb") as f:
            return plistlib.load(f).get("CFBundleShortVersionString")
    except (OSError, ValueError):
        return None


def find_cli(home, given):
    tries = [given, os.environ.get("VECTORCRAFT_CLI"), record(home).get("vectorcraft_cli")]
    tries += sorted(glob.glob(os.path.join(home, "vectorcraft", "cli", "*", "vectorcraft-cli")), reverse=True)
    tries += sorted(glob.glob(os.path.expanduser("~/Applications/*/vectorcraft-cli")) + glob.glob(os.path.expanduser("~/Applications/*/*/*/vectorcraft-cli")), reverse=True)
    tries.append(shutil.which("vectorcraft-cli"))
    for p in tries:
        if p and os.path.isfile(p) and os.access(p, os.X_OK):
            return os.path.abspath(p)
    return None


def check_vectorcraft(rep, home, given):
    app = next((a for a in VC_APPS if os.path.isdir(a)), None)
    cli = find_cli(home, given)
    if app:
        rep.ok("vectorcraft app", f"{app_version(app) or '?'} in {os.path.dirname(app)}, the free editor for the files we hand over")
    else:
        rep.optional("vectorcraft app", "the free, open-source Illustrator for editing our files. Ask first, then re-run with --install-vectorcraft (about 310 MB from GitHub, checksums verified)")
    if cli:
        code, text = out([cli, "--version"])
        rep.ok("vectorcraft cli", f"{text.strip()} (lets the export check open each file the way VectorCraft will)")
        save_record(home, vectorcraft_cli=cli)
        print(f"         To let Claude drive VectorCraft:  claude mcp add vectorcraft -- \"{cli}\" mcp", flush=True)
        print(f"         Live, in the open app:  open -a VectorCraft --args --control 7979   (the MCP server then connects to 127.0.0.1:7979)", flush=True)
    else:
        rep.optional("vectorcraft cli", "the export check uses it to open each file headless. It comes with --install-vectorcraft, or point at yours with --vectorcraft-cli <path>")
    return app, cli


def fetch(url, dest=None):
    req = urllib.request.Request(url, headers={"User-Agent": "bb-statics-setup", "Accept": "application/octet-stream" if dest else "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if not dest:
            return r.read()
        size = int(r.headers.get("Content-Length") or 0)
        got, shown = 0, -1
        with open(dest + ".part", "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
                got += len(chunk)
                if size:
                    step = int(got * 4 / size)
                    if step != shown and step < 4:
                        shown = step
                        print(f"...      {step * 25}%", flush=True)
        os.replace(dest + ".part", dest)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def install_vectorcraft(rep, home, app, cli):
    try:
        rel = json.loads(fetch(f"https://api.github.com/repos/{VC_REPO}/releases/latest"))
    except OSError as e:
        rep.missing("vectorcraft", f"couldn't reach GitHub ({e}). Check your internet and re-run with --install-vectorcraft")
        return
    ver = rel["tag_name"].lstrip("v")
    assets = {a["name"]: a["browser_download_url"] for a in rel.get("assets", [])}
    want_app, want_cli = f"vectorcraft-{ver}-macos-universal.dmg", f"vectorcraft-cli-{ver}-macos-universal.zip"
    if "SHA256SUMS.txt" not in assets or want_app not in assets or want_cli not in assets:
        rep.missing("vectorcraft", f"release {ver} doesn't have the Mac files this expects. Install by hand from https://github.com/{VC_REPO}/releases")
        return
    sums = dict(reversed(l.split()) for l in fetch(assets["SHA256SUMS.txt"]).decode().splitlines() if len(l.split()) == 2)
    need_app = not app or app_version(app) != ver
    need_cli = not cli or ver not in out([cli, "--version"])[1]
    work = tempfile.mkdtemp(prefix="vectorcraft-")
    try:
        for name, needed in ((want_app, need_app), (want_cli, need_cli)):
            if not needed:
                continue
            dest = os.path.join(work, name)
            print(f"...      downloading {name}", flush=True)
            fetch(assets[name], dest)
            if sha256(dest) != sums.get(name):
                rep.missing("vectorcraft", f"{name} didn't match its published checksum, so it was thrown away. Try again later")
                return
            print(f"OK       {name}: checksum matches the release's SHA256SUMS.txt", flush=True)
            if name == want_app:
                mount = os.path.join(work, "mnt")
                code, text = out(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", mount, dest], timeout=300)
                if code:
                    rep.missing("vectorcraft app", f"couldn't open the disk image ({text.strip()[-160:]})")
                    return
                try:
                    src = next(iter(glob.glob(os.path.join(mount, "*.app"))), None)
                    target = VC_APPS[0]
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    if os.path.isdir(target):
                        shutil.rmtree(target)
                    code, text = out(["ditto", src, target], timeout=300)
                    if code:
                        rep.missing("vectorcraft app", f"couldn't copy it into ~/Applications ({text.strip()[-160:]})")
                        return
                finally:
                    out(["hdiutil", "detach", mount, "-quiet"])
                print(f"OK       VectorCraft {ver} installed in ~/Applications", flush=True)
            else:
                cli_dir = os.path.join(home, "vectorcraft", "cli")
                os.makedirs(cli_dir, exist_ok=True)
                code, text = out(["ditto", "-x", "-k", dest, cli_dir], timeout=300)  # ditto keeps the executable bit
                if code:
                    rep.missing("vectorcraft cli", f"couldn't unpack it ({text.strip()[-160:]})")
                    return
                found = sorted(glob.glob(os.path.join(cli_dir, f"*{ver}*", "vectorcraft-cli")))
                if found:
                    save_record(home, vectorcraft_cli=found[-1])
                print(f"OK       VectorCraft CLI {ver} unpacked into {cli_dir}", flush=True)
        if not need_app and not need_cli:
            print(f"OK       VectorCraft {ver} is already the latest", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def ps_name(path):
    code, text = out(["node", os.path.join(HERE, "lib", "fontname.mjs"), path])
    return text.split()[0] if not code and text.strip() and not text.startswith("(") else None


def check_kit(rep, kit, install):
    path = kit if kit.endswith(".json") else os.path.join(kit, "kit.json")
    try:
        k = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError) as e:
        rep.missing("brand kit", f"couldn't read {path} ({e}). See references/brand-kit.md")
        return
    base = os.path.dirname(os.path.abspath(path))
    for role, f in (k.get("fonts") or {}).items():
        file = os.path.normpath(os.path.join(base, f.get("file", "")))
        if not os.path.isfile(file):
            rep.missing(f"kit font {role}", f"no file at {file}")
            continue
        real = ps_name(file)
        if f.get("postscript") and real and f["postscript"] != real:
            rep.missing(f"kit font {role}", f'kit.json says "{f["postscript"]}" but the file is "{real}". Change kit.json to "{real}"')
            continue
        installed = os.path.join(FONTS, os.path.basename(file))
        if os.path.exists(installed):
            rep.ok(f"kit font {role}", f"{real}, installed for VectorCraft and Illustrator")
        elif install:
            os.makedirs(FONTS, exist_ok=True)
            shutil.copy2(file, installed)
            rep.ok(f"kit font {role}", f"{real}, copied into ~/Library/Fonts")
        else:
            rep.optional(f"kit font {role}", f"{real} isn't installed, so VectorCraft and Illustrator will swap it when editing. Re-run with --install-fonts (copies it into ~/Library/Fonts)")
    for name, p in (k.get("logos") or {}).items():
        if os.path.isfile(os.path.join(base, p)):
            rep.ok(f"kit logo {name}", "vector" if p.lower().endswith(".svg") else "picture (an SVG logo stays sharp and editable)")
        else:
            rep.missing(f"kit logo {name}", f"no file at {os.path.join(base, p)}")


def main():
    ap = argparse.ArgumentParser(description="Checks this Mac for /bb:statics")
    ap.add_argument("--data", help="the plugin data folder; /bb:statics passes this")
    ap.add_argument("--kit", help="a brand kit folder or kit.json to check")
    ap.add_argument("--install-fonts", action="store_true", help="copy the kit's fonts into ~/Library/Fonts")
    ap.add_argument("--install-vectorcraft", action="store_true", help="download and install VectorCraft from GitHub")
    ap.add_argument("--vectorcraft-cli", help="path to a VectorCraft CLI you already have")
    ap.add_argument("--no-build", action="store_true", help="only look, change nothing")
    a = ap.parse_args()
    data = a.data or os.environ.get("CLAUDE_PLUGIN_DATA") or os.path.expanduser("~/.cache/butcherbird-bb")
    home = os.path.join(data, "statics")

    rep = Report()
    check_mac(rep)
    node_ok = check_node(rep)
    chrome_ok = check_chrome(rep)
    check_driver(rep, home, not a.no_build, node_ok, chrome_ok)
    app, cli = check_vectorcraft(rep, home, a.vectorcraft_cli)
    if a.install_vectorcraft and not a.no_build:
        install_vectorcraft(rep, home, app, cli)
        check_vectorcraft(rep, home, None)
    if a.kit:
        check_kit(rep, a.kit, a.install_fonts and not a.no_build)
    if rep.blocked:
        print("\nNOT READY. Run the fixes above, then run this again.")
        sys.exit(1)
    save_record(home, data=home, playwright=PLAYWRIGHT)
    print(f"\nREADY. Run the scripts with:  BB_STATICS_DATA=\"{home}\" node <script>")


if __name__ == "__main__":
    main()
