#!/usr/bin/env python3
"""Turns pack.md into pack.html in the Butcherbird shoot-pack look: Ink cover with the running order,
the numbers and how-to-film page, one page per ad (message, hook do/say, other hooks, numbered body, close, shots),
then the extra-shots page. Same page as the shipped shoot pack.
An edit pack (front matter `mode: edit`) labels the voice "On screen" and the film card "The footage".
Run: python3 build_pack.py job/pack.md [--out job/pack.html] [--pdf]"""
import argparse, os, re, shutil, subprocess, sys, tempfile, time
from html import escape as e
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(HERE))
from packmd import is_edit, parse  # noqa: E402

ASSETS = HERE.parent / "assets"
def find_chrome():
    """Copy-free headless Chrome first: every launch of the Chrome app leaves a 1.4 GB code_sign_clone copy on disk."""
    import glob
    c = [os.environ.get("CHROME_PATH"), os.environ.get("CHROME_BIN"), os.path.expanduser("~/.local/bin/chrome-headless")]
    c += sorted(glob.glob(os.path.expanduser("~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell")), reverse=True)
    c.append("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    return next((p for p in c if p and os.path.exists(p)), c[-1])


CHROME = find_chrome()


def bold(s):
    """escape, then turn **x** into white bold, as on the shipped cover"""
    return re.sub(r"\*\*(.+?)\*\*", r'<b style="color:#fff">\1</b>', e(s))


def cap(s):
    return s[:1].upper() + s[1:] if s else s


def ad_page(a, edit=False):
    say = "On screen" if edit else "Say"
    close_lbl = "Close. On screen, exactly" if edit else "Close. Say it exactly"
    # in an edit the voice column is all on-screen text, so drop the "Nothing. On screen:" stage note
    tidy = (lambda x: re.sub(r"^(Nothing\.?\s*)?On screen:\s*", "", x or "", flags=re.I)) if edit else (lambda x: x)
    rows = "".join(f'<div class="beat"><div class="n">{k}</div><div class="do">{e(d)}</div><div class="sy">{e(cap(tidy(s)) or "Nothing.")}</div></div>'
                   for k, (d, s) in enumerate(a["beats"], 1))
    alt = "".join(f"<li>{e(x)}</li>" for x in a["other_hooks"])
    alts = f'<div class="lbl" style="margin-top:8px">Other hooks to film</div><ul class="l alt">{alt}</ul>' if alt else ""
    shots = f'<div class="shots"><b>Get these shots:</b> {e(cap(a["shots"]))}</div>' if a["shots"] else ""
    return f'''
<section class="page ad">
  <div class="ey">{e(a["italic"])}</div>
  <h2>{e(a["title"])}<span class="dot">.</span></h2>
  <div class="card or"><div class="lbl">The message</div><div class="msg">{e(a["message"])}</div></div>
  <div class="card">
    <div class="lbl">Hook</div>
    <div class="beat head"><div></div><div>Do</div><div>{say}</div></div>
    <div class="beat"><div class="n">H</div><div class="do">{e(a["hook_do"])}</div><div class="sy">{e(cap(tidy(a["hook_say"])))}</div></div>
    {alts}
  </div>
  <div class="card">
    <div class="lbl">Body</div>
    <div class="beat head"><div></div><div>Do</div><div>{say}</div></div>
    {rows}
  </div>
  <div class="card blk"><div class="lbl">{close_lbl}</div><div class="msg" style="font-size:21px">{e(tidy(a["close"]))}</div></div>
  {shots}
</section>'''


def build(p):
    f = p["front"]
    edit = is_edit(p)
    film_title = "The footage" if edit else "How to film"
    title = p["title"]
    head, _, tagline = title.partition(":")
    cover = f.get("cover", head.strip())
    cover_html = "<br>".join(e(x) for x in cover.split(" / "))
    who = f.get("for") or next((x.replace("**", "").split(".")[0] for x in p["intro"] if x.lower().startswith("for ")), "")
    line = f.get("line") or cap(tagline.strip())
    explain = next((x for x in p["intro"] if x.lower().startswith("every ")), "")
    explain_main, _, say_line = explain.partition("Say it your way")
    say_line = ("Say it your way" + say_line) if say_line else ""
    run = "".join(f"<div><b>{k}</b>{e(t)} <span>{e(d)}</span></div>" for k, (t, d) in enumerate(p["running"] or [(a['title'], '') for a in p["ads"]], 1))
    nums = "".join(f'<div class="deal"><span class="num" style="font-size:38px">{e(n)}</span><span><b>{e(cap(b))}</b> {e(c)}</span></div>'
                   for n, b, c in p["numbers"])
    notes = "".join(f'<div style="font-size:17px;padding-top:10px">{e(x)}</div>' for x in p["number_notes"])
    warns = "".join(f'<div class="card blk"><h3>{e(t)}<span class="dot">.</span></h3><div style="margin-top:8px;font-size:18px">{e(b)}</div></div>'
                    for t, b in p["warnings"])
    film = "".join(f"<li>{e(x)}</li>" for x in p["how_to_film"])
    numbers_page = ""
    if nums or film:
        numbers_page = f'''
<section class="page">
  <div class="ey">Say these exactly</div>
  <h2>The numbers<span class="dot">.</span></h2>
  <div class="card or">{nums}{notes}</div>
  {warns}
  {f'<div class="card"><h3>{film_title}<span class="dot">.</span></h3><ul class="l" style="margin-top:8px">{film}</ul></div>' if film else ""}
</section>'''
    tails = ""
    for t in p["tail"]:
        name = t["title"]
        ey, h = ("While everyone's there", "Extra shots") if name.lower().startswith("extra shots") else ("", name)
        body = "".join(f'<div style="font-size:19px">{e(x)}</div>' for x in t["lines"])
        if t["bullets"]:
            body += f'<div class="card or"><ul class="l">{"".join(f"<li>{e(x)}</li>" for x in t["bullets"])}</ul></div>'
        body += "".join(f'<div class="card"><h3>{e(k)}<span class="dot">.</span></h3><div style="margin-top:6px">{e(cap(v))}</div></div>' for k, v in t["cards"])
        tails += f'\n<section class="page">\n  {f"<div class=ey>{e(ey)}</div>" if ey else ""}\n  <h2>{e(h)}<span class="dot">.</span></h2>\n  {body}\n</section>'
    css = (ASSETS / "pack.css").read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800;900&family=Playfair+Display:ital,wght@1,600&display=swap" rel="stylesheet">
<style>{css}</style></head><body>

<section class="page ink">
  <img class="logo" src="bb-logo-white.png" alt="Butcherbird">
  <div style="margin-top:60px" class="ey">{e(who)}</div>
  <h1>{cover_html}<span class="dot">.</span></h1>
  <div class="ey">{e(line)}</div>
  <div class="card blk" style="margin-top:18px"><div class="run">{run}</div></div>
  <div class="sub" style="font-size:19px;margin-top:10px">{bold(explain_main.strip())}</div>
  <div class="sub" style="font-size:19px;margin-top:auto">{bold(say_line.strip())}</div>
</section>
{numbers_page}
{"".join(ad_page(a, edit) for a in p["ads"])}
{tails}
</body></html>'''


def warnings(p):
    """What the builder would otherwise drop or leave empty without a word."""
    w = []
    if not p["ads"]:
        w.append("no ads found: each ad needs a '## N. Title' heading")
    if not p["how_to_film"]:
        w.append("no bullets under '## How to film' (or '## The footage' for an edit), so that card is left out")
    known = ("extra shots", "if there's time", "after the shoot")
    for t in p["tail"]:
        if not (t["bullets"] or t["cards"] or t["lines"]):
            w.append(f"section '{t['title']}' is empty and would print as a blank page")
        elif not t["title"].lower().startswith(known):
            w.append(f"section '{t['title']}' isn't a known one, so it prints as its own page after the ads")
    for a in p["ads"]:
        if not a["close"]:
            w.append(f"ad {a['n']}: no '**Close ...:**' line found")
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("--out")
    ap.add_argument("--pdf", action="store_true", help="also print pack.pdf with headless Chrome")
    a = ap.parse_args()
    src = Path(a.pack)
    out = Path(a.out) if a.out else src.with_name("pack.html")
    pack = parse(src)
    for w in warnings(pack):
        print("warning:", w, file=sys.stderr)
    out.write_text(build(pack))
    logo = out.parent / "bb-logo-white.png"
    if not logo.exists():
        shutil.copy(ASSETS / "bb-logo-white.png", logo)
    print(out)
    if a.pdf:
        if not os.path.exists(CHROME):
            sys.exit("no Chrome on this Mac, so no PDF: open pack.html in a browser and print it, or install Google Chrome (or set CHROME_PATH)")
        pdf = out.resolve().with_suffix(".pdf")
        pdf.unlink(missing_ok=True)
        # Chrome writes the file, then often hangs or exits 2 at teardown: wait for the file to settle, then stop it.
        with tempfile.TemporaryDirectory() as prof:   # throwaway profile, so no Chrome clone is left behind
            proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={prof}",
                                     f"--print-to-pdf={pdf}", out.resolve().as_uri()],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            last = -1
            for _ in range(120):
                time.sleep(0.5)
                size = pdf.stat().st_size if pdf.exists() else 0
                if (size and size == last) or proc.poll() is not None:
                    break
                last = size
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if not pdf.exists() or pdf.stat().st_size == 0:
            sys.exit("pdf failed: open pack.html in Chrome and print it instead")
        print(pdf)


if __name__ == "__main__":
    main()
