#!/usr/bin/env python3
"""Proves the citations in a reasoning sheet (or a reference file) are real.
Run: python3 cite_check.py job/reasoning.md [more files]
- every passage id (like caples-0033 or hormozi-leads-0178) has a reader's note, the same lookup as `search.py --show`.
  A passage the reader scored 0 has no note, so it fails here too: don't cite it.
- a citation whose note scored under 2 is flagged: the reader judged it no use for a reel
- every beat row in a per-ad table (hook / promise / proof / body / close / offer) carries an id
- every ad under a `### Ad` heading in section 4 has hook, promise and proof rows
- a reasoning sheet says what a book teaches in your own words and cites the id; book text doesn't ship with the pack.
  A quote (a '> ' line, or text after 'Quote:') is only allowed where BB_CANON_FULL_DB points at the full library, two
  sentences at most, and word for word from the cited passage.
Exit 1 if anything is red."""
import argparse, json, os, re, sqlite3, sys
from pathlib import Path

BOOKS = Path(__file__).resolve().parents[2] / "books"
ID = re.compile(r"\b([a-z]+(?:-[a-z]+)*-\d{4})\b")
BEATS = {"hook", "body", "proof", "close", "offer", "promise", "turn"}
NEEDED = {"hook", "promise", "proof"}


def norm(s):
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", s).strip().strip('"').strip()


def sentences(q):
    parts = [p for p in re.split(r"(?<=[.!?])[\"')\]]*\s+(?=[A-Z\"'])", q.strip()) if p.strip()]
    return len(parts)


def load_notes():
    return {r["id"]: r for r in (json.loads(l) for l in open(BOOKS / "data" / "notes.jsonl", encoding="utf-8"))}


def load_cards():
    return {p.stem: norm(p.read_text(encoding="utf-8")) for p in (BOOKS / "cards").glob("*.md")}


def full_library():
    path = os.environ.get("BB_CANON_FULL_DB", "")
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True) if path and os.path.exists(path) else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reasoning", nargs="+")
    a = ap.parse_args()
    notes, cards, full = load_notes(), load_cards(), full_library()
    reds = 0
    for f in a.reasoning:
        if len(a.reasoning) > 1:
            print(f"--- {f}")
        reds += check(notes, cards, full, f)
    print(f"\n{reds} red")
    sys.exit(1 if reds else 0)


def check(notes, cards, full, path):
    text = Path(path).read_text(encoding="utf-8")
    lines = text.splitlines()
    reds, out = 0, []

    ids = sorted(set(ID.findall(text)))
    known = [i for i in ids if i in notes]
    for i in ids:
        if i not in notes:
            out.append(f"RED   {i} has no note: the reader scored it 0 or the id is wrong, so don't cite it"); reds += 1
    out.append(f"OK    {len(known)} of {len(ids)} passage ids have a note")

    # the reader judged the passage no use for a reel
    for i in known:
        if notes[i]["score"] < 2:
            out.append(f"RED   {i} scored {notes[i]['score']} (under 2): {notes[i]['says'][:90]}; find a stronger passage or say why in plain words"); reds += 1

    # beat rows without an id
    for n, line in enumerate(lines, 1):
        if line.strip().startswith("|"):
            cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
            if cells and cells[0].strip("* ") in BEATS and not ID.search(line):
                out.append(f"RED   line {n}: the {cells[0].strip('* ')} row names no passage id"); reds += 1

    # every ad in section 4 names the passage behind its hook, promise and proof
    section, ad, rows = None, None, set()
    def close_ad():
        nonlocal reds
        if ad and NEEDED - rows:
            out.append(f"RED   {ad}: no row for {', '.join(sorted(NEEDED - rows))}"); reds += 1
    for line in lines:
        s = line.strip()
        if s.startswith("## "):
            close_ad(); section, ad, rows = s, None, set()
        elif s.startswith("### ") and section and re.match(r"##\s*(4\b|§?4\b|per ad)", section, re.I):
            close_ad(); ad, rows = s[4:], set()
        elif ad and s.startswith("|"):
            rows.add(s.strip("|").split("|")[0].strip(" *").lower())
    close_ad()

    # quotes
    quotes = []
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith(">"):
            quotes.append((n, s.lstrip("> ").strip()))
        m = re.search(r"Quote:\**\s*(.+)$", s)
        if m:
            quotes.append((n, m.group(1).strip()))
    for n, q in quotes:
        qn = norm(re.sub(r"[(\[]?\b[a-z]+(?:-[a-z]+)*-\d{4}\b[)\]]?\s*$", "", q))
        if not qn:
            continue
        k = sentences(qn)
        if k > 2:
            out.append(f"RED   line {n}: quote is {k} sentences; two at most"); reds += 1
        near = [i for i in ID.findall(" ".join(lines[max(0, n - 4):n + 1])) if i in notes]
        books = {notes[i]["book"] for i in near}
        pool = []
        if full:
            for i in near:
                r = full.execute("select text from passages where id=?", (i,)).fetchone()
                if r:
                    pool.append(norm(r[0]))
        core = qn.rstrip(".!?:,").strip()
        if not any(core in p for p in pool):
            out.append(f"RED   line {n}: quote not found word for word on {', '.join(sorted(books)) or 'any'} card; quote from a card, or paraphrase and cite the id"); reds += 1
        else:
            out.append(f"OK    line {n}: quote checks out ({k} sentence{'s' if k > 1 else ''})")

    for o in out:
        print(o)
    return reds


if __name__ == "__main__":
    main()
