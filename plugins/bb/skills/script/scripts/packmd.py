"""Reads a pack.md written in the shoot-pack format (see references/pack-format.md).
Shared by check_pack.py and build_pack.py, so the page people see and the checks read the same source."""
import re
from pathlib import Path

AD_HEAD = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
FIELD = re.compile(r"^\*\*(.+?)(?::\*\*|\*\*:)\s*(.*)$")          # **Label:** text  or  **Label**: text
KIND = re.compile(r"<!--\s*kind:\s*([\w-]+)\s*-->")


def _strip_md(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", s)
    return s.strip()


def _split_say(text):
    """'Do: x. Say: y' -> (x, y). Say may be missing."""
    m = re.match(r"^Do:\s*(.*?)\s*Say:\s*(.*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    m = re.match(r"^Do:\s*(.*)$", text)
    if m:
        return m.group(1).strip(), ""
    return text.strip(), ""


def parse(path):
    lines = Path(path).read_text().splitlines()
    pack = {"title": "", "front": {}, "intro": [], "running": [], "numbers": [], "number_notes": [],
            "warnings": [], "how_to_film": [], "ads": [], "tail": []}
    i = 0
    # optional front matter
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            if ":" in lines[i]:
                k, v = lines[i].split(":", 1)
                pack["front"][k.strip()] = v.strip()
            i += 1
        i += 1
    section, ad, part, tail = None, None, None, None
    for raw in lines[i:]:
        line = raw.rstrip()
        s = line.strip()
        if s.startswith("# ") and not pack["title"]:
            pack["title"] = s[2:].strip(); section = "intro"; continue
        if s == "---":
            continue
        m = AD_HEAD.match(s)
        if m:
            ad = {"n": int(m.group(1)), "title": m.group(2), "italic": "", "message": "", "hook_do": "",
                  "hook_say": "", "kind": "", "other_hooks": [], "beats": [], "close": "", "shots": ""}
            pack["ads"].append(ad); section, part = "ad", None; continue
        if s.startswith("## "):
            h = s[3:].strip()
            low = h.lower()
            if low.startswith("the numbers"):
                section = "numbers"
            elif low.startswith("how to film") or low.startswith("the footage"):
                section = "film"
            else:
                section = "tail"; tail = {"title": h, "bullets": [], "cards": [], "lines": []}
                pack["tail"].append(tail)
            ad = None; continue
        if not s:
            continue
        if section == "intro":
            if s.lower().startswith("running order"):
                section = "running"; continue
            pack["intro"].append(s); continue
        if section == "running":
            m = re.match(r"^\d+\.\s+(.+?)(?:\s+\((.+)\))?$", s)
            if m:
                pack["running"].append((m.group(1).strip(), (m.group(2) or "").strip()))
            continue
        if section == "numbers":
            if s.startswith("- "):
                b = s[2:].strip()
                m = re.match(r"^\*\*(.+?)\*\*:\s*(.*)$", b)
                if m and len(m.group(1)) <= 10:
                    first, _, rest = m.group(2).partition(". ")
                    pack["numbers"].append((m.group(1), first.rstrip(".") + ".", rest.strip()))
                    continue
                m = re.match(r"^\*\*(.+?)\*\*\s*(.*)$", b)
                if m:
                    pack["warnings"].append((m.group(1).rstrip("."), m.group(2)))
                    continue
                pack["number_notes"].append(_strip_md(b))
            continue
        if section == "film":
            if s.startswith("- "):
                pack["how_to_film"].append(_strip_md(s[2:]))
            continue
        if section == "tail":
            if s.startswith("- "):
                tail["bullets"].append(_strip_md(s[2:]))
            else:
                m = FIELD.match(s)
                if m:
                    tail["cards"].append((m.group(1).rstrip(":"), _strip_md(m.group(2))))
                else:
                    tail["lines"].append(_strip_md(s))
            continue
        if section == "ad" and ad is not None:
            k = KIND.search(s)
            if k:
                ad["kind"] = k.group(1); continue
            if s.startswith("*") and not s.startswith("**") and not ad["italic"]:
                ad["italic"] = s.strip("*").strip(); continue
            if s.startswith("**Hook"):
                part = "hook"; continue
            if s.startswith("**Body"):
                part = "body"; continue
            m = FIELD.match(s)
            if m:
                label, text = m.group(1).lower(), m.group(2).strip()
                if label.startswith("the message"):
                    ad["message"] = text
                elif label.startswith("close"):
                    ad["close"] = text; part = None
                elif label.startswith("get these shots"):
                    ad["shots"] = text; part = None
                continue
            if part == "hook":
                if raw.startswith("  ") and s.startswith("- "):
                    ad["other_hooks"].append(s[2:].strip())
                elif s.startswith("- Do:"):
                    ad["hook_do"] = s[5:].strip()
                elif s.startswith("- Say:"):
                    ad["hook_say"] = s[6:].strip()
                continue
            if part == "body":
                m = re.match(r"^\d+\.\s+(.*)$", s)
                if m:
                    ad["beats"].append(_split_say(m.group(1)))
                continue
    return pack


def is_edit(pack):
    """An edit pack (mode: edit in the front matter) cuts footage already filmed; on-screen text is the voice."""
    return pack["front"].get("mode", "").strip().lower() == "edit"


def spoken(text, on_screen=False):
    """Words a person says out loud in a Say line: the quoted parts. If nothing is quoted, the line itself,
    unless it is a stage note (Nothing, On screen ...). With on_screen=True (edit packs) the on-screen
    text counts too, because there it is the voice."""
    if not text:
        return ""
    if on_screen:
        q = re.findall(r"[\"“](.+?)[\"”]", text)
        return " ".join(q) if q else ("" if re.match(r"^nothing\b", text.strip().lower()) else text)
    q = re.findall(r"[\"“](.+?)[\"”]", text)
    if q:
        # on-screen text in quotes is read, not spoken
        out = []
        for m in re.finditer(r"[\"“](.+?)[\"”]", text):
            before = text[max(0, m.start() - 12):m.start()].lower()
            if "on screen" in before:
                continue
            out.append(m.group(1))
        return " ".join(out)
    if re.match(r"^(nothing|on screen)", text.strip().lower()):
        return ""
    return text


def words(text):
    return re.findall(r"[A-Za-z0-9R%,.'’]+", text.replace("%", " %"))
