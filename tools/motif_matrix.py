#!/usr/bin/env python3
"""Motif matrix scaffold for Missing Ministry rebuild.
Scans canonical seeds in scripture.db + stages incoming apocrypha files.
Outputs docs/plans/missing-ministry-matrix.csv with ? placeholders for fetch tracks to fill.

Usage: python3 tools/motif_matrix.py
# ponytail: CSV scaffold now, DB-backed cell scoring when incoming texts are normalized.
"""
import sqlite3, pathlib, csv, re

DB = "data/processed/scripture.db"
INC = pathlib.Path("data/texts-incoming")
OUT = "docs/plans/missing-ministry-matrix-auto.csv"

MOTIFS = {
    "washing/baptism (incl proxy)": [r"wash", r"bapt", r"proxy"],
    "anointing/chrism": [r"anoint", r"chrism", r"oil"],
    "garment (white/new/tangible)": [r"garment", r"robe", r"clothed", r"white raiment"],
    "new name/seal": [r"new name", r"seal", r"token"],
    "prayer circle/united prayer": [r"prayer circle", r"united.*pray", r"pray.*one accord", r"amen.*amen"],
    "creation drama (council/fall/adam)": [r"council", r"lucifer", r"adam.*eve", r"creation", r"premortal"],
    "covenant/oath/secrecy charge": [r"covenant", r"oath", r"secret", r"tell no man", r"charge.*not"],
    "ascent/veil/heavens": [r"ascen", r"veil", r"third heaven", r"caught up"],
    "descent to dead/kerygma": [r"preach.*dead", r"prison.*spirit", r"descen", r"harrowing", r"kerygma"],
    "sacramental meal/unity (be one)": [r"sacrament", r"bread.*wine|wine.*bread", r"be one", r"that they.*one"],
    "marriage/sealing": [r"marriage", r"bridegroom", r"seal.*(spouse|wife|husband)", r"eternal marriage"],
    "apostasy prophecy": [r"wolves", r"false shepherd", r"falling away", r"apostat", r"corrupters"],
    "continued appearances/commission": [r"forty days", r"many infallible proofs", r"go ye into all", r"feed my sheep"],
    "resurrection teaching": [r"firstfruits", r"first resurrection", r"rose again", r"resurrect"],
}

SEED_GROUPS = {
    "canon": ["acts.1.3", "luke.24.36", "john.20.26", "1cor.15.4", "1pet.3.19"],
    "restoration": ["3ne.11.10", "3ne.17.14", "3ne.19.6", "moro.7.9", "dc.138.1", "dc.121.45", "dc.131.1"],
}

def db_hits(patterns):
    con = sqlite3.connect(DB)
    out = {}
    for label, pats in patterns.items():
        hits = []
        for p in pats:
            try:
                rows = con.execute(
                    "SELECT id FROM verses WHERE text_english REGEXP ? LIMIT 5", (p,)
                ).fetchall()
                hits += [r[0] for r in rows]
            except Exception:
                # REGEXP may not exist — fallback LIKE on stripped keyword
                kw = re.sub(r"[^a-z ]", "", p).strip().split()
                kw = kw[-1] if kw else p
                rows = con.execute(
                    "SELECT id FROM verses WHERE text_english LIKE ? LIMIT 5", (f"%{kw}%",)
                ).fetchall()
                hits += [r[0] for r in rows]
        out[label] = sorted(set(hits))[:8]
    con.close()
    return out

def incoming_status():
    files = sorted([p.name for p in INC.glob("*")]) if INC.exists() else []
    return files

def main():
    db = db_hits(MOTIFS)
    files = incoming_status()
    cols = ["motif", "canon_hits", "restoration_hits", "apocrypha_status", "notes"]
    rows = []
    for motif, hits in db.items():
        canon = ";".join(h for h in SEED_GROUPS["canon"] if True)  # seeds fixed
        rows.append({
            "motif": motif,
            "canon_hits": ";".join(db.get(motif, [])[:4]),
            "restoration_hits": ";".join(SEED_GROUPS["restoration"]),
            "apocrypha_status": "incoming: " + (", ".join(files) if files else "none yet"),
            "notes": "? — fill +/~/-/ cell per witness when Tracks A-D land",
        })
    pathlib.Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT} ({len(rows)} motifs, incoming files: {len(files)})")

if __name__ == "__main__":
    main()
