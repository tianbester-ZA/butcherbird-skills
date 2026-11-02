#!/usr/bin/env python3
"""Search the Butcherbird book library: what 17 books say, passage by passage.
   search.py "question" [--job hook] [--book caples] [--k 8]
   search.py --show ID       one passage's note (and its text, where BB_CANON_FULL_DB points at the full library)
   search.py --books         the books and how many notes each has
   search.py --toc BOOK      a book's chapters with their id ranges
   search.py --ids FILE...   check every passage id in the files exists (exit 1 if not)
Only Python 3 is needed. The notes ship with the pack. Book text doesn't."""
import argparse, json, os, re, sqlite3, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
FULL = os.environ.get("BB_CANON_FULL_DB", "")
ID_RE = re.compile(r"\b([a-z]+(?:-[a-z]+)*-\d{4})\b")

rows = [json.loads(l) for l in open(os.path.join(DATA, "notes.jsonl"), encoding="utf-8")]
byid = {r["id"]: r for r in rows}
T = json.load(open(os.path.join(DATA, "tags.json"), encoding="utf-8"))
STOP = set(T.get("stopwords", []))

ap = argparse.ArgumentParser()
ap.add_argument("query", nargs="?")
ap.add_argument("--job"); ap.add_argument("--book"); ap.add_argument("--k", type=int, default=8)
ap.add_argument("--show"); ap.add_argument("--books", action="store_true"); ap.add_argument("--min-score", type=int, default=2)
ap.add_argument("--ids", nargs="+"); ap.add_argument("--toc")
a = ap.parse_args()

if a.books:
    seen = {}
    for r in rows:
        seen.setdefault(r["book"], [r["title"], r["author"], 0])[2] += 1
    for b, (t, au, n) in sorted(seen.items()):
        print(f"{b:16} {n:4}  {t} ({au})")
    sys.exit()

if a.toc:
    book, chapters = None, {}
    for r in rows:
        if r["book"].startswith(a.toc):
            book = r["book"]
            chapters.setdefault(r["chapter"] or "-", []).append(r["id"])
    if not book: sys.exit("no such book; see --books")
    for c, ids in chapters.items():
        print(f"{ids[0]} to {ids[-1]}  {c}  ({len(ids)} notes)")
    sys.exit()

if a.ids:
    bad = 0
    for f in a.ids:
        for i in sorted(set(ID_RE.findall(open(f, encoding="utf-8").read()))):
            book = i.rsplit("-", 1)[0]
            if any(r["book"] == book for r in rows) and i not in byid:
                print(f"{f}: no such passage {i}"); bad += 1
    print("all ids found" if not bad else f"{bad} bad ids"); sys.exit(1 if bad else 0)

if a.show:
    r = byid.get(a.show)
    if not r: sys.exit(f"no note for {a.show}: the reader scored it 0 or the id is wrong, so don't cite it")
    print(f"{r['id']}  {r['title']} ({r['author']})\nchapter: {r['chapter'] or '-'}   jobs: {r['jobs'] or '-'}   score: {r['score']}\n\nSAYS: {r['says']}\nDO: {r['do'] or '-'}")
    if FULL and os.path.exists(FULL):
        try:
            t = sqlite3.connect(FULL).execute("select text from passages where id=?", (a.show,)).fetchone()
            if t: print("\nPASSAGE:\n" + t[0])
        except sqlite3.Error:
            pass
    sys.exit()

if not a.query: ap.error("give a question, or --show ID, --toc BOOK or --books")
terms = [w for w in re.findall(r"[a-z0-9']+", a.query.lower().replace("'", "")) if w not in STOP and len(w) > 1]
extra = []
for w in terms:
    extra += T.get("synonyms", {}).get(w, []) + (T.get("synonyms", {}).get(w[:-1], []) if w.endswith("s") else [])
if a.job:
    if a.job not in T.get("jobs", {}): sys.exit("jobs: " + ", ".join(T.get("jobs", {})))
    extra += T.get("job_expansions", {}).get(a.job, [])
words = []
for w in terms + extra:
    for p in w.split():
        if p not in words and p not in STOP: words.append(p)
if not words: sys.exit("no usable words in the question")

db = sqlite3.connect(":memory:")
db.execute("create virtual table f using fts5(id unindexed, says, do, jobs, tokenize='porter unicode61')")
db.executemany("insert into f values(?,?,?,?)", [(r["id"], r["says"], r["do"], r["jobs"]) for r in rows])
hits = db.execute("select id, bm25(f, 0, 2.0, 1.5, 0.5) s from f where f match ? order by s limit ?",
                  (" OR ".join(f'"{w}"' for w in words), a.k * 30)).fetchall()
ranked = sorted(((s - byid[i]["score"] * 1.5, i) for i, s in hits))
out, per = [], {}
for _, i in ranked:
    r = byid[i]
    if r["score"] < a.min_score: continue
    if a.job and a.job not in (r["jobs"] or "").split(","): continue
    if a.book and not r["book"].startswith(a.book): continue
    if not a.book and per.get(r["book"], 0) >= 3: continue
    per[r["book"]] = per.get(r["book"], 0) + 1; out.append(r)
    if len(out) >= a.k: break
for n, r in enumerate(out, 1):
    print(f"{n}. [{r['id']}] {r['title']} | {r['chapter'] or '-'} | jobs: {r['jobs'] or '-'}\n   SAYS: {r['says']}\n   DO: {r['do'] or '-'}\n")
if not out: print("no hits; try plainer words")
