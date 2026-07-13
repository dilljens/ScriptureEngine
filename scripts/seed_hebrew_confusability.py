#!/usr/bin/env python3
"""Seed Hebrew confusability pairs for non-interference ordering.

Ensures similar/confusable topics are separated by at least 3 other lessons
in the curriculum to prevent associative interference (Math Academy Ch. 17).

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
"""

import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"

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


def main():
    conn = sqlite3.connect(str(MEM_DB))

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

    # Clear existing
    conn.execute("DELETE FROM hebrew_confusability")

    count = 0
    for a, b, reason in CONFUSABLE_PAIRS:
        # Check both nodes exist
        a_exists = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (a,)).fetchone()
        b_exists = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (b,)).fetchone()
        if not a_exists:
            print(f"  SKIP {a}↔{b}: node '{a}' not found")
            continue
        if not b_exists:
            print(f"  SKIP {a}↔{b}: node '{b}' not found")
            continue
        conn.execute(
            "INSERT INTO hebrew_confusability (node_a, node_b, reason, strength) VALUES (?, ?, ?, 0.7)",
            (a, b, reason))
        count += 1

    conn.commit()
    conn.close()

    print(f"Created {count} confusability pairs in hebrew_confusability table")


if __name__ == '__main__':
    main()
