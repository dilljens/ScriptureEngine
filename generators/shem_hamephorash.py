#!/usr/bin/env python3
"""Extract the 72 Names of God (Shem HaMephorash) from Exodus 14:19-21.

The 72 Names are derived from three consecutive verses in Exodus,
each containing exactly 72 Hebrew letters. When written in a grid
(verse 19 forward, verse 20 backward, verse 21 forward), they form
72 three-letter combinations — each considered a "name" of God
in Jewish mystical (Kabbalistic) tradition.

This script:
1. Extracts the 72 triplets from Ex 14:19-21
2. Scans the entire Tanakh Hebrew text for each triplet as consecutive letters
3. Stores matches as connections with type='shem_hamephorash'

Usage:
    python3 generators/shem_hamephorash.py
    python3 generators/shem_hamephorash.py --dry-run
"""
import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BASE_DIR = Path(__file__).parent.parent
SCRIPTURE_DB = BASE_DIR / "data" / "processed" / "scripture.db"


def extract_letters(text):
    """Extract only Hebrew letters from a text string, removing vowels and cantillation."""
    if not text:
        return ""
    # Remove niqqud (vowel points), cantillation marks, and other diacritics
    # Keep only the consonant letters (א-ת, ך-ץ)
    cleaned = re.sub(r'[\u0591-\u05AF\u05B0-\u05C7\u05C4-\u05C5]', '', text)
    # Keep only Hebrew letters
    cleaned = re.sub(r'[^\u05D0-\u05EA\u05F0-\u05F2]', '', cleaned)
    return cleaned


def get_seventy_two_names(conn):
    """Get the 72 three-letter Names from Exodus 14:19-21.

    Returns list of (index, triplet) tuples.
    """
    verses = []
    for v in [19, 20, 21]:
        row = conn.execute(
            "SELECT text_hebrew FROM verses WHERE book_id='exo' AND chapter=14 AND verse=?",
            (v,)
        ).fetchone()
        if not row:
            print(f"  WARNING: Exodus 14:{v} not found!")
            return []
        letters = extract_letters(row[0])
        verses.append(letters)

    if any(len(v) != 72 for v in verses):
        print(f"  WARNING: Verse lengths: {[len(v) for v in verses]} (expected 72 each)")
        print("  Note: Textual variants may affect letter counts")
        # Use what we have

    # Verse 19 forward, Verse 20 backward, Verse 21 forward
    v19 = verses[0]
    v20 = verses[1][::-1]  # reversed
    v21 = verses[2]

    # Combine: v19[i] + v20[i] + v21[i] = one Name
    names = []
    max_len = min(len(v19), len(v20), len(v21))
    for i in range(max_len):
        name = v19[i] + v20[i] + v21[i]
        if len(name) == 3:  # Should always be 3 letters
            names.append((i + 1, name))

    print(f"  Extracted {len(names)} Names from Exodus 14:19-21")
    return names


def scan_for_names(conn, names, dry_run=False):
    """Scan all Hebrew verses for occurrences of the 72 Names as consecutive letters."""
    total = 0
    now = time.strftime('%Y-%m-%d')

    # Get all verses with Hebrew text
    verses = conn.execute("""
        SELECT id, text_hebrew FROM verses
        WHERE text_hebrew IS NOT NULL AND text_hebrew != ''
        AND book_id NOT LIKE 'dss.%'  -- exclude DSS
        AND book_id NOT LIKE '1esd%'
    """).fetchall()

    print(f"  Scanning {len(verses)} Hebrew verses for 72 Names...")

    # Pre-extract letters for each verse
    verse_letters = {}
    for vid, heb in verses:
        letters = extract_letters(heb)
        if len(letters) >= 3:
            verse_letters[vid] = letters

    print(f"    {len(verse_letters)} verses with 3+ Hebrew letters")

    # For each Name, scan all verses
    for idx, triplet in names:
        name_count = 0

        for vid, letters in verse_letters.items():
            # Skip if verse is one of the source verses
            if vid in ('exo.14.19', 'exo.14.20', 'exo.14.21'):
                continue

            # Check if the triplet appears as consecutive letters
            if triplet in letters:
                # Find the position(s)
                positions = []
                start = 0
                while True:
                    pos = letters.find(triplet, start)
                    if pos == -1:
                        break
                    positions.append(pos)
                    start = pos + 1

                if not dry_run:
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO connections
                                (source_verse, target_verse, layer, type, subtype,
                                 strength, confidence, discovered_by, metadata,
                                 quality_level, tradition, hermeneutic, created_at)
                            VALUES (?, ?, 'sod', 'shem_hamephorash', ?,
                                    0.5, 0.6, 'shem_hamephorash_scanner', ?,
                                    'suggested', 'jewish', 'faith', ?)
                        """, (
                            vid,
                            f"name_72:{triplet}",
                            f"position_{positions[0]}" if positions else "",
                            json.dumps({
                                "name_index": idx,
                                "triplet": triplet,
                                "name_number": idx,
                                "positions": positions,
                                "source": "Exodus 14:19-21 encoding",
                            }),
                            now,
                        ))
                        name_count += 1
                    except Exception:
                        pass
                else:
                    name_count += 1

        total += name_count
        if name_count > 0:
            print(f"    Name {idx:2d} ({triplet}): found in {name_count} verses")

    return total


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract 72 Names of God from Hebrew text")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no inserts")
    args = parser.parse_args()

    conn = sqlite3.connect(str(SCRIPTURE_DB))

    print("=" * 60)
    print("72 Names of God (Shem HaMephorash) Extraction")
    print("=" * 60)

    names = get_seventy_two_names(conn)
    if not names:
        conn.close()
        return

    print("\nFirst 10 Names:")
    for idx, triplet in names[:10]:
        print(f"  {idx:2d}. {triplet}")

    print("\nScanning Tanakh for occurrences...")
    total = scan_for_names(conn, names, dry_run=args.dry_run)

    if not args.dry_run:
        conn.commit()

    print(f"\n{'='*60}")
    print(f"Total Name occurrences found: {total}")
    if args.dry_run:
        print("DRY RUN — no data written. Remove --dry-run to import.")
    else:
        print("Data imported successfully.")

    conn.close()


if __name__ == "__main__":
    main()
