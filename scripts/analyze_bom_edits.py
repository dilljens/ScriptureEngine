#!/usr/bin/env python3
"""Compare Hebraism/grammar markers between the 1830 first edition and a
modern Book of Mormon text. Tests the claim that grammatical editing
smoothed away Hebraic features.

Usage: python3 scripts/analyze_bom_edits.py  (prints JSON + markdown table)

Corpora:
  1830   — data/bom_1830/1830_wikisource_text.txt (chapter sections only)
  modern — data/bom_1830/gutenberg_modern_pg17.txt (between PG START/END)
Counts are per 10,000 words. Personal-'which' and if-and patterns are
approximations — same bias in both corpora, so the *delta* is the signal.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.bom1830 import load_1830  # noqa: E402  (shares 1830 cleaning)

BASE = os.path.join(os.path.dirname(__file__), "..")
MODERN = os.path.join(BASE, "data", "bom_1830", "gutenberg_modern_pg17.txt")

ETH_STOP = {"death", "breath", "beneath", "neath", "heath", "sheath",
            "wreath", "teeth", "sabbath"}
WHICH_VERBS = ("testified|prophesied|prophesieth|spake|spoke|speaketh|said|saith|"
               "taught|teacheth|wrote|preached|came|went|saw|heard|knew|did|had|"
               "was|were|is|are|shall|will|hath|doth|believed|murmured|feared|"
               "rejected|kept|desired|beheld|loved|sought|repented|belongeth")
DID_SKIP = ("not|you|ye|thou|he|she|it|we|they|i|them|him|her|us|me")


def corpus_1830():
    secs, err = load_1830()
    if err:
        raise RuntimeError(err)
    chap = [t for t in secs if "Chapter" in t]
    return " ".join(secs[t] for t in sorted(chap))


def corpus_modern():
    raw = open(MODERN, encoding="utf-8", errors="replace").read()
    m1 = re.search(r"\*\*\* START OF .* \*\*\*", raw)
    m2 = re.search(r"\*\*\* END OF .* \*\*\*", raw)
    body = raw[m1.end():m2.start()] if m1 and m2 else raw
    body = re.sub(r"\s+", " ", body)
    # Strip chapter:verse + bare verse numbers ("...flesh. 18 And he said"):
    # otherwise every verse-initial word hides behind a digit.
    body = re.sub(r"\b\d{1,3}:\d{1,3}\b", " ", body)
    body = re.sub(r"(?<!\w)\d{1,3}(?!\w)", " ", body)
    return re.sub(r"\s+", " ", body).strip()


def markers(text):
    t = text.lower()
    words = re.findall(r"[a-z]+", t)
    n = len(words)
    sents = re.split(r"[.!?]+", t)
    eth = [w for w in words if w.endswith("eth") and w not in ETH_STOP
           and len(w) > 4]
    return {
        "words": n,
        "it_came_to_pass": len(re.findall(r"it came to pass", t)),
        "sent_initial_and": sum(1 for s in sents if s.strip().startswith("and ")),
        "which_total": len(re.findall(r"\bwhich\b", t)),
        "which_person": len(re.findall(r"\bwhich\s+(?:" + WHICH_VERBS + r")\b", t)),
        "who": len(re.findall(r"\bwho\b", t)),
        "whom": len(re.findall(r"\bwhom\b", t)),
        "saith": len(re.findall(r"\bsaith\b", t)),
        "said": len(re.findall(r"\bsaid\b", t)),
        "eth_verbs": len(eth),
        "yea": len(re.findall(r"\byea\b", t)),
        "behold": len(re.findall(r"\bbehold\b", t)),
        "wherefore": len(re.findall(r"\bwherefore\b", t)),
        "whoso": len(re.findall(r"\bwhoso(?:ever)?\b", t)),
        "if_and": len(re.findall(r"(?:^|[.!?]\s*)if\b[^.!?]*\band\b", t)),
        "did_verb": len(re.findall(r"\bdid\s+(?!" + DID_SKIP + r"\b)[a-z]+\b", t)),
        "exceeding": len(re.findall(r"\bexceeding\s+[a-z]+\b", t)),
        "unto": len(re.findall(r"\bunto\b", t)),
        "thou_thy": len(re.findall(r"\b(thou|thee|thy|thine|ye)\b", t)),
    }


def main():
    c1830, cmod = corpus_1830(), corpus_modern()
    m1830, mmod = markers(c1830), markers(cmod)
    rows = []
    for k in m1830:
        if k == "words":
            continue
        a, b = m1830[k] / m1830["words"] * 10000, mmod[k] / mmod["words"] * 10000
        pct = (b - a) / a * 100 if a else 0.0
        rows.append({"marker": k, "per10k_1830": round(a, 2),
                     "per10k_modern": round(b, 2), "change_pct": round(pct, 1)})
    out = {"words_1830": m1830["words"], "words_modern": mmod["words"],
           "markers": sorted(rows, key=lambda r: r["change_pct"])}
    print(json.dumps(out, indent=2))
    print("\n| marker | 1830 /10k | modern /10k | change |",
          "|---|---|---|---|", sep="\n")
    for r in out["markers"]:
        print(f"| {r['marker']} | {r['per10k_1830']} | {r['per10k_modern']} | "
              f"{r['change_pct']:+.1f}% |")


if __name__ == "__main__":
    main()
