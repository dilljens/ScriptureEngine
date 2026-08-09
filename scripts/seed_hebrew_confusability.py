#!/usr/bin/env python3
"""Seed Hebrew confusability pairs for non-interference ordering.

Ensures similar/confusable topics are separated by at least 3 other lessons
in the curriculum to prevent associative interference (Math Academy Ch. 17).

The review queue and curriculum generator read the `hebrew_confusability`
table (node_a, node_b) and reorder so confusable pairs never sit adjacent.

DB path resolution: honors the MEMORIZE_DB_PATH env var (same convention as
web/routes/hebrew.py and lib/config.py); defaults to <repo>/data/memorize.db.
Pass an explicit path as argv[1] to override both.

Confusable pairs:
- Shin (שׁ) vs Sin (שׂ) — same letter, different dot position
- Samekh (ס) vs Sin (שׂ) — same S sound
- Tet (ט) vs Tav (ת) — similar in some pronunciations
- He (ה) vs Chet (ח) — similar guttural
- Ayin (ע) vs Aleph (א) — both guttural/silent
- Bet (ב) vs Vav (ו) — similar sound
- Kaf (כ) vs Qof (ק) — similar K sound
- Zayin (ז) vs Tsade (צ) — similar shape in some scripts
- Gimel (ג) vs Nun (נ) — similar shape
- Dalet (ד) vs Resh (ר) — similar shape
- Final vs non-final letter forms
- Short vs long vowel pairs
- Binyan/aspect pairs (active/passive, perfect/imperfect)
"""

import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"


def _resolve_db_path():
    """Honor MEMORIZE_DB_PATH, then argv[1], then the default path."""
    if os.environ.get("MEMORIZE_DB_PATH"):
        return Path(os.environ["MEMORIZE_DB_PATH"])
    if len(sys.argv) > 1:
        return Path(sys.argv[1])
    return DEFAULT_MEM_DB


# Confusable pairs with reason
CONFUSABLE_PAIRS = [
    # Letters — visual/auditory confusion
    ("shin", "sin", "same letter, different dot: SH vs S"),
    ("shin", "samekh", "both produce S-like sounds"),
    ("sin", "samekh", "identical S sound"),
    ("tet", "tav", "similar T sounds in some traditions"),
    ("he", "chet", "similar guttural sounds"),
    ("aleph", "ayin", "both guttural/silent in many traditions"),
    ("bet", "vav", "similar B/V sounds"),
    ("kaf", "qof", "both K-like sounds"),
    ("kaf", "kaf_final", "same letter, final vs non-final form"),
    ("mem", "mem_final", "same letter, final vs non-final form"),
    ("nun", "nun_final", "same letter, final vs non-final form"),
    ("pe", "pe_final", "same letter, final vs non-final form"),
    ("tsade", "tsade_final", "same letter, final vs non-final form"),
    ("dalet", "resh", "similar shapes"),
    ("zayin", "tsade", "similar shapes"),
    ("gimel", "nun", "similar shapes"),

    # Vowels — auditory confusion
    ("vowel_patah", "vowel_qamats", "both A sounds, length distinction"),
    ("vowel_segol", "vowel_tsere", "both E sounds, length distinction"),
    ("vowel_hiriq", "vowel_hiriq_yod", "same I sound, with/without mater"),
    ("vowel_holam", "vowel_holam_vav", "same O sound, with/without vav"),
    ("vowel_shuruq", "vowel_qubuts", "both U sounds, length distinction"),
    ("vowel_sheva_na", "vowel_sheva_nah", "vocal vs silent sheva — identical appearance"),

    # Grammar — conceptual confusion
    ("qal_perfect", "qal_imperfect", "same stem, different aspect"),
    ("perfect_3ms", "imperfect_3ms", "3ms in two aspects"),
    ("niphal", "pual", "both passive stems"),
    ("hiphil", "hophal", "both causative stems, active vs passive"),
    ("piel", "pual", "same stem, active vs passive"),
    ("construct_chain", "definite_article", "definiteness marking confusion"),
    ("infinitive_construct", "infinitive_absolute", "same root, different infinitive forms"),
]


def seed(db_path):
    """Insert all confusable pairs whose nodes exist. Idempotent.

    Uses INSERT OR IGNORE guarded by a UNIQUE(node_a, node_b) index so
    re-runs never duplicate rows and never delete manually-added pairs.
    Returns the number of pairs actually inserted.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Hebrew DB not found: {db_path}")
    conn = sqlite3.connect(str(db_path))

    # Create confusability table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hebrew_confusability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_a TEXT NOT NULL,
            node_b TEXT NOT NULL,
            reason TEXT DEFAULT '',
            strength REAL DEFAULT 0.5,
            FOREIGN KEY (node_a) REFERENCES hebrew_nodes(id),
            FOREIGN KEY (node_b) REFERENCES hebrew_nodes(id)
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_hebrew_confusability_pair
        ON hebrew_confusability(node_a, node_b)
    """)

    inserted = 0
    skipped = []
    for a, b, reason in CONFUSABLE_PAIRS:
        a_exists = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (a,)).fetchone()
        b_exists = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (b,)).fetchone()
        if not a_exists or not b_exists:
            skipped.append((a, b))
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO hebrew_confusability (node_a, node_b, reason, strength) VALUES (?, ?, ?, 0.7)",
            (a, b, reason))
        inserted += cur.rowcount

    conn.commit()
    conn.close()

    for a, b in skipped:
        print(f"  SKIP {a}↔{b}: node not found (left for a future data pass)")
    return inserted


def main():
    db_path = _resolve_db_path()
    print(f"Seeding hebrew_confusability → {db_path}")
    inserted = seed(db_path)
    print(f"Inserted {inserted} new confusability pairs "
          f"(of {len(CONFUSABLE_PAIRS)} defined)")


if __name__ == '__main__':
    main()
