#!/usr/bin/env python3
"""Checks the whole repo before anything reaches the team. Runs on every push (.github/workflows/check.yml).
    python3 scripts/check.py
Fails on: broken JSON, a skill with no description or one over the limit, a passage id with no note, a client name,
a personal Mac path, a big file, a page number or book text in the notes."""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "bb" / "skills"
THIS = Path(__file__).resolve()
MAX_BYTES = 3_000_000
MAX_DESCRIPTION = 1024
NOTE_FIELDS = {"id", "book", "title", "author", "chapter", "jobs", "score", "says", "do"}
NOTE_MAX_CHARS = 400                       # a note is a sentence or two; a long one is probably book text
TEXT = {".md", ".py", ".sh", ".js", ".html", ".css", ".json", ".jsonl", ".txt", ".yml", ".yaml", ".swift"}
SKIP = {".git", "__pycache__"}
FAKE_IDS_OK = {"reasoning-fake.md", "reasoning-lowscore.md"}   # these prove the citation check catches bad ids

# Client names never go in this file, because this repo is public. Keep them one per line, as patterns, in
# scripts/.private-words on your own machine (it's in .gitignore). The online check skips this part.
WORDS = ROOT / "scripts" / ".private-words"
WORD_LIST = [w.strip() for w in WORDS.read_text(encoding="utf-8").splitlines() if w.strip()] if WORDS.exists() else []
CLIENT_RE = re.compile("|".join(WORD_LIST), re.I) if WORD_LIST else None
PATH_RE = re.compile(r"/Users/|~/workspaces|canon-venv|canon-library|Agency Brain|BB 1\b|video-production|[Mm]ac mini|\bthe mini\b")
ID_RE = re.compile(r"\b([a-z]+(?:-[a-z]+)*-\d{4})\b")

bad = []


def fail(where, why):
    bad.append(f"{where}: {why}")


def files():
    for dirpath, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP]
        for n in names:
            yield Path(dirpath) / n


def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    return dict(re.findall(r"^([\w-]+):\s*(.*)$", m.group(1), re.M)) if m else {}


def check_json():
    for p in files():
        if p.suffix == ".json":
            try:
                json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                fail(p.relative_to(ROOT), f"bad JSON ({e})")


def check_skills():
    found = 0
    for skill in sorted(SKILLS.glob("*/SKILL.md")):
        found += 1
        fm = frontmatter(skill.read_text(encoding="utf-8"))
        where = skill.relative_to(ROOT)
        if fm.get("name") != skill.parent.name:
            fail(where, f"name should be {skill.parent.name}")
        if not fm.get("description"):
            fail(where, "no description")
        elif ": " in fm["description"] and not fm["description"].startswith('"'):
            fail(where, "description has a colon and a space, which breaks the file's header; reword it or put it in quotes")
        elif len(fm["description"]) > MAX_DESCRIPTION:
            fail(where, f"description is {len(fm['description'])} characters, limit {MAX_DESCRIPTION}")
    if not found:
        fail(SKILLS.relative_to(ROOT), "no skills found")


def check_notes():
    path = SKILLS / "books" / "data" / "notes.jsonl"
    ids, books = set(), set()
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        r = json.loads(line)
        extra = set(r) - NOTE_FIELDS
        if extra:
            fail(f"notes.jsonl line {n}", f"field that shouldn't be there: {sorted(extra)}")
        for field in ("says", "do"):
            if len(r.get(field) or "") > NOTE_MAX_CHARS:
                fail(f"notes.jsonl line {n}", f"{field} is too long to be a note; is it book text?")
        ids.add(r["id"])
        books.add(r["book"])
    return ids, books


def check_ids(ids, books):
    for p in SKILLS.rglob("*"):
        if p.suffix not in (".md", ".py", ".html") or p.name in FAKE_IDS_OK:
            continue
        for i in sorted(set(ID_RE.findall(p.read_text(encoding="utf-8")))):
            if i.rsplit("-", 1)[0] in books and i not in ids:
                fail(p.relative_to(ROOT), f"{i} has no note (scored 0, or the id is wrong)")


def check_words():
    for p in files():
        rel = p.relative_to(ROOT)
        if p.stat().st_size > MAX_BYTES:
            fail(rel, f"{p.stat().st_size / 1e6:.1f} MB; nothing this big belongs here")
        if p.suffix not in TEXT or p == THIS:
            continue
        text = p.read_text(encoding="utf-8")
        for n, line in enumerate(text.splitlines(), 1):
            for rx, why in ((CLIENT_RE, "client name"), (PATH_RE, "personal path or machine")):
                m = rx.search(line) if rx else None
                if m:
                    fail(f"{rel}:{n}", f"{why}: {m.group(0)}")


def main():
    check_json()
    check_skills()
    ids, books = check_notes()
    check_ids(ids, books)
    check_words()
    if bad:
        print("\n".join(bad))
        print(f"\n{len(bad)} problem(s). Nothing should merge until this is clean.")
        sys.exit(1)
    print(f"clean: {len(ids)} notes, every passage id resolves, no personal paths, nothing big" + (", no client names" if WORD_LIST else "; client names not checked here"))


if __name__ == "__main__":
    main()
