#!/usr/bin/env python3
"""Normalize incoming PD apocrypha to verse-style IDs for motif scanning.
Reads data/texts-incoming/*.txt, splits on blank lines / chapter headers,
writes data/texts-incoming-normalized/<base>.jsonl with {ref, text}.
Then motif scan appends evidence to docs/plans/missing-ministry-matrix.csv.

Usage: python3 tools/normalize_incoming.py
# ponytail: regex splitter now; proper TEI/verse parser if corpus grows past 10 texts.
"""
import pathlib, re, json

SRC = pathlib.Path("data/texts-incoming")
DST = pathlib.Path("data/texts-incoming-normalized")

MOTIFS = {
    "washing/baptism (incl proxy)": [r"wash", r"bapt", r"laver", r"ablution"],
    "anointing/chrism": [r"anoint", r"chrism", r"oil upon"],
    "garment (white/new/tangible)": [r"garment", r"white robe", r"white raiment", r"clothed with", r"put on"],
    "new name/seal": [r"new name", r"\bseal", r"signet", r"token"],
    "prayer circle/united prayer": [r"prayer circle", r"one accord", r"amen.*amen", r"encircled|stood round"],
    "creation drama (council/fall/adam)": [r"council", r"lucifer|satan.*fell|fall of", r"adam and eve", r"premortal"],
    "covenant/oath/secrecy charge": [r"covenant", r"oath", r"secret saying|secret word", r"tell no|reveal not|keep.*secret"],
    "ascent/veil/heavens": [r"ascen", r"veil", r"treasur|firmament", r"caught up|taken up"],
    "descent to dead/kerygma": [r"dead|hades|abyss|prison", r"preach", r"descen|harrowing"],
    "sacramental meal/unity (be one)": [r"bread.*cup|cup.*bread|eucharist|agape", r"be one|they.*one|unity"],
    "marriage/sealing": [r"marriage|bridegroom|bridechamber|bridal"],
    "apostasy prophecy": [r"wolves|false|apostat|falling away|corrupt"],
    "continued appearances/commission": [r"forty days|appeared|commission|go ye"],
    "resurrection teaching": [r"resurrect|firstfruits|rose again"],
}

def split_chunks(text):
    text = re.sub(r"\r", "", text)
    # drop header lines
    lines = [l for l in text.split("\n") if not re.match(r"^(SOURCE|TRANS|LICENSE|FETCHED):", l)]
    body = "\n".join(lines)
    # split on blank lines or Chapter/Book headers
    parts = re.split(r"\n\s*\n", body)
    chunks = []
    for p in parts:
        p = re.sub(r"\s+", " ", p).strip()
        if len(p) > 80:
            chunks.append(p)
    return chunks

def main():
    DST.mkdir(parents=True, exist_ok=True)
    if not SRC.exists():
        print("no incoming dir yet")
        return
    files = sorted(SRC.glob("*.txt")) + sorted(SRC.glob("*.md"))
    if not files:
        print("incoming empty — fetch tracks still running")
        return
    total = 0
    for f in files:
        base = f.stem
        chunks = split_chunks(f.read_text(errors="ignore"))
        out = DST / f"{base}.jsonl"
        with open(out, "w") as fh:
            for i, c in enumerate(chunks, 1):
                hits = sorted({m for m, pats in MOTIFS.items() if any(re.search(p, c, re.I) for p in pats)})
                fh.write(json.dumps({"ref": f"{base}.{i}", "motifs": hits, "text": c[:2000]}) + "\n")
        total += len(chunks)
        print(f"{base}: {len(chunks)} chunks -> {out}")
    print(f"total chunks: {total}")

if __name__ == "__main__":
    main()
