#!/usr/bin/env python3
"""Mechanical checks on a pack.md, so the critic spends itself on judgement.
Run: python3 check_pack.py job/pack-draft.md [--event "Black Friday"]
An edit pack (front matter `mode: edit`) reads on-screen text as the voice and skips the dead-air checks.
Front matter `settled: a; b` lists what the person running this has confirmed: those phrases never count as extra urgency or as the deal said again.
Prints red lines (fix before the critic sees it) and amber lines (look, then decide). Exit 1 if any red."""
import argparse, re, sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from packmd import is_edit, parse, spoken, words  # noqa: E402

WPS = 2.5            # spoken words per second
CLOSE_MAX = 12       # words in the close
BANNED = ["deserves better", "last chance", "imagine a world", "don't miss out", "dont miss out", "game changer",
          "game-changer", "level up", "hey guys", "hi guys", "welcome back", "so today", "trust me",
          "you won't believe", "the wait is over", "elevate your", "unlock", "treat yourself", "look no further",
          "say goodbye to", "whether you're", "it's not just", "not just a", "act now", "while stocks last",
          "limited time only", "what are you waiting for", "you deserve"]
GREETING = re.compile(r"^\W*(hey|hi|hello|howzit|welcome|so,? today|guys)\b", re.I)
URGENCY = re.compile(r"\b(last|never|again|only|ends?|ending|gone|hurry|quick|chance|ever|before|left|sold out)\b", re.I)
PRICE = re.compile(r"(\d+\s?%|\bR\s?\d[\d,]*|\bfree\b|half price|\bper cent\b|percent|off\b)", re.I)
HOW = re.compile(r"(\.co\.za|\.com|\blink\b|\btap\b|\bdm\b|whatsapp|\border\b|\bshop\b|\bsign up\b|\bjoin\b|\bbook\b|\bcall\b|\bemail\b|\bform\b|\bcomment\b|\bsite\b|\bwebsite\b)", re.I)
NUMWORD = {"two", "three", "four", "five", "ten", "twenty", "fifty", "hundred"}
STOP = set("a an the and or but to of in on at for with is are be it its it's this that these those you your i me my we our "
           "he she they them his her get got go just so now one all".split())
OPEN_QUESTION = re.compile(r"\b(unconfirmed|not confirmed|isn'?t confirmed|to be confirmed|tbc|once \w+ confirms?|waits? on|waiting on|still to check)\b", re.I)
SHIPPING = re.compile(r"(free (shipping|delivery)[^.\"]{0,25}R\s?\d[\d,]*|R\s?\d[\d,]*[^.\"]{0,25}free (shipping|delivery))", re.I)
SECONDS = re.compile(r"(\d+)\s*(?:to|-|–)?\s*(\d+)?\s*seconds", re.I)

KINDS = ["result", "odd-picture", "camera", "reaction", "flaw", "viewer", "news", "deal-first", "dare", "pov", "skit", "statement"]


def guess_kind(ad):
    """Rough hook kind when the writer didn't tag it with <!-- kind: x -->."""
    do, say = ad["hook_do"].lower(), ad["hook_say"].lower()
    sp = spoken(ad["hook_say"]).lower()
    if "pov" in do or "pov" in say:
        return "pov"
    if PRICE.search(sp):
        return "deal-first"
    if not sp:
        return "odd-picture"
    if sp.rstrip().endswith("?"):
        return "viewer"
    if re.search(r"\b(catch|try|bet|dare|watch this|don't)\b", sp):
        return "dare"
    if re.search(r"\b(news|new|announc|introducing|retiring|just)\b", sp):
        return "news"
    if re.search(r"\b(mate|friend|girl|guy|guys|dad|mom|mum|two|four)\b", do) and "off camera" not in do:
        return "skit"
    return "statement"


def deal_tokens(text):
    toks = set(re.findall(r"\d+\s?%|R\s?\d[\d,]*|\b\d+\b", text))
    toks |= {w for w in re.findall(r"[a-z]+", text.lower()) if w in NUMWORD}
    return {t.replace(" ", "") for t in toks}


def content(text):
    return {w for w in re.findall(r"[a-z']+", text.lower()) if w not in STOP and len(w) > 2}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pack")
    ap.add_argument("--event", help='the reason to buy now that must be said or shown, e.g. "Black Friday"')
    a = ap.parse_args()
    p = parse(a.pack)
    edit = is_edit(p)
    settled = [x.strip() for x in p["front"].get("settled", "").split(";") if x.strip()]

    def calm(text):
        """Take out what isn't the deal or extra urgency: settled phrases and a shipping threshold."""
        for x in settled:
            text = re.sub(re.escape(x), " ", text, flags=re.I)
        return SHIPPING.sub(" ", text)

    voice = (lambda t: spoken(t, on_screen=True)) if edit else spoken
    out = []

    def flag(level, where, msg):
        out.append((level, where, msg))

    if not p["ads"]:
        flag("RED", "pack", "no ads found: each ad needs a '## N. Title' heading (see references/pack-format.md)")
    kinds, endings, silent_total, all_text = [], [], 0, []
    for ad in p["ads"]:
        w = f"ad {ad['n']}"
        for field in ("message", "hook_do", "hook_say", "close"):
            if not ad[field]:
                flag("RED", w, f"missing {field.replace('_', ' ')}")
        hook_sp = voice(ad["hook_say"])
        body_sp = [voice(s) for _, s in ad["beats"]]
        close_sp = voice(ad["close"]) or ad["close"]
        text_all = " ".join([ad["hook_do"], ad["hook_say"], ad["close"]] + [d + " " + s for d, s in ad["beats"]])
        all_text.append(text_all)

        # length
        n_words = len(words(" ".join([hook_sp] + body_sp + [close_sp])))
        est = n_words / WPS
        m = SECONDS.search(ad["italic"])
        if m:
            top = int(m.group(2) or m.group(1))
            if est > top * 1.15:
                flag("RED", w, f"{n_words} {'on-screen' if edit else 'spoken'} words is about {est:.0f} s at {WPS} words a second; the page says {top} s")
            else:
                flag("OK", w, f"{n_words} {'on-screen' if edit else 'spoken'} words, about {est:.0f} s against {top} s")
        else:
            flag("AMBER", w, f"no length on the italic line; {n_words} spoken words is about {est:.0f} s")

        # hook
        if GREETING.search(hook_sp):
            flag("RED", w, f"hook opens on a greeting: {hook_sp[:50]!r}")
        if len(words(hook_sp)) > 15:
            flag("AMBER", w, f"spoken hook is {len(words(hook_sp))} words; the first two seconds hold about 5 to 8")
        if len(ad["other_hooks"]) < 2:
            flag("AMBER", w, f"only {len(ad['other_hooks'])} other hooks to film; give the edit two or three")
        kind = ad["kind"] or guess_kind(ad)
        kinds.append(kind)
        if not edit and "on screen" not in ad["hook_say"].lower() and "on screen" not in ad["hook_do"].lower():
            flag("AMBER", w, "hook has no on-screen line: what does a stranger get with the sound off?")
        if "!" in ad["hook_say"] + ad["close"]:
            flag("AMBER", w, "exclamation mark in the hook or close: it adds to the hype smell")

        # close
        n_close = len(words(close_sp))
        if n_close > CLOSE_MAX:
            flag("RED", w, f"close is {n_close} words; keep it to {CLOSE_MAX}")
        has_price, has_how = bool(PRICE.search(close_sp)), bool(HOW.search(close_sp))
        if not has_price and not has_how:
            flag("RED", w, "close has no price and no how: a buyer can't act on it")
        elif not has_price:
            flag("AMBER", w, "close has no price or discount: fine only if the deal isn't a price (say what they get)")
        elif not has_how:
            flag("AMBER", w, "close has no how (site, link, tap, DM): say where to get it")
        endings.append(" ".join(re.sub(r"[^\w.]", "", x).strip(".") for x in words(close_sp)[-2:]).lower())

        # deal said once
        ct = deal_tokens(calm(close_sp))
        for k, sp in enumerate(body_sp, 1):
            shared = ct & deal_tokens(calm(sp))
            overlap = content(calm(close_sp)) & content(calm(sp))
            if shared and len(overlap) >= 2:
                flag("RED", w, f"deal said in body beat {k} and again in the close ({', '.join(sorted(shared))}); say it once, at the close")
            elif len(overlap) >= 3:
                flag("AMBER", w, f"body beat {k} restates the close ({', '.join(sorted(overlap))})")
        for k, oh in enumerate(ad["other_hooks"], 1):
            # the edit may pick any hook, and every hook runs into the same close
            if ct & deal_tokens(oh) and PRICE.search(oh):
                flag("AMBER", w, f"other hook {k} says the deal ({', '.join(sorted(ct & deal_tokens(oh)))}); "
                                 f"if the edit picks it, the deal is said twice")
        if len(set(re.findall(r"\d+\s?%", " ".join(body_sp + [close_sp, hook_sp])))) > 1:
            flag("RED", w, "more than one discount in one ad: one deal each")
        urg = URGENCY.findall(calm(" ".join([hook_sp, close_sp] + body_sp)))
        if len(urg) >= 3:
            flag("AMBER", w, f"urgency piled up ({', '.join(urg)}); one true reason is enough")

        # dead air (an edit's quiet beats are the cut's call, not a script fault)
        silent = [] if edit else [k for k, (_, s) in enumerate(ad["beats"], 1) if not spoken(s).strip()]
        silent_total += len(silent)
        if len(silent) > 1:
            flag("AMBER", w, f"{len(silent)} silent beats ({', '.join(map(str, silent))}); fine as cutaways, slow in a fast reel")
        if not edit and re.search(r"\b(waits?|pause|two seconds|three seconds|beat\.)", text_all, re.I):
            flag("AMBER", w, "a timed hold or 'waits' is written in: dead air in a short reel")

        # stock phrases
        low = text_all.lower() + " " + ad["message"].lower()
        for b in BANNED:
            if b in low:
                flag("RED", w, f"stock line: '{b}'")

    # pack level
    c = Counter(kinds)
    n = len(p["ads"])
    for k, v in c.items():
        if n >= 3 and v >= max(2, (n + 1) // 2):
            flag("RED", "pack", f"{v} of {n} hooks are the same kind ({k}); spread them (references/hooks.md)")
    if c.get("statement", 0) >= 2:
        flag("AMBER", "pack", f"{c['statement']} hooks are one person to camera saying a line: does each idea need a talking head?")
    open_q = [m.group(0) for m in OPEN_QUESTION.finditer(Path(a.pack).read_text())]
    if open_q:
        flag("RED", "pack", f"lists something as open ({', '.join(sorted(set(x.lower() for x in open_q)))}): pick the sensible reading and log it in reasoning.md section 0")
    flag("OK", "pack", "hook kinds: " + ", ".join(f"ad {ad['n']} {k}" for ad, k in zip(p["ads"], kinds)))
    e = Counter(endings)
    for k, v in e.items():
        if v >= 3:
            flag("AMBER", "pack", f"{v} closes end the same way ('...{k}'): symmetry reads as a template")
    if n and silent_total > n:
        flag("AMBER", "pack", f"{silent_total} silent beats across {n} ads")
    if a.event:
        joined = " ".join(all_text).lower()
        if a.event.lower() not in joined:
            flag("RED", "pack", f"'{a.event}' is never said or shown: the reason to buy now is missing")
    else:
        flag("OK", "pack", "no --event given, so the reason-now check was skipped")
    if edit:
        flag("OK", "pack", "edit pack: on-screen text read as the voice; dead-air checks skipped")

    order = {"RED": 0, "AMBER": 1, "OK": 2}
    for lvl, where, msg in sorted(out, key=lambda x: (order[x[0]], x[1] != "pack", x[1])):
        print(f"{lvl:<5} {where:<6} {msg}")
    reds = sum(1 for x in out if x[0] == "RED")
    ambers = sum(1 for x in out if x[0] == "AMBER")
    print(f"\n{reds} red, {ambers} amber across {n} ads")
    sys.exit(1 if reds else 0)


if __name__ == "__main__":
    main()
