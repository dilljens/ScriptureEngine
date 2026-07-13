#!/usr/bin/env python3
"""Import Sefaria links (Jewish commentary, Talmud, Midrash, Zohar) as connections.

Fetches links from the Sefaria API for each Tanakh verse and stores them as
connections in the engine with tradition='jewish'.

Usage:
    python3 generators/sefaria_links.py                      # All Tanakh
    python3 generators/sefaria_links.py --books gen,exo      # Specific books
    python3 generators/sefaria_links.py --books gen --limit 10  # First 10 verses only
    python3 generators/sefaria_links.py --dry-run            # Count only

API docs: https://developers.sefaria.org
Rate limit: generous, but we add 150ms delay between requests.
"""
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE_DIR = Path(__file__).parent.parent
DB_PATH = BASE_DIR / "data" / "processed" / "scripture.db"

API_BASE = "https://www.sefaria.org/api/links"
HEADERS = {"Accept": "application/json", "User-Agent": "ScriptureEngine/1.0 (research project; +https://github.com/scriptureengine)"}

# Major commentary categories worth importing
MAJOR_CATEGORIES = {
    # Core Jewish interpretive tradition — Rishonim (medieval commentators)
    "Rashi": 0.9, "Ramban": 0.85, "Ibn Ezra": 0.85, "Rashbam": 0.8,
    "Sforno": 0.8, "Radak": 0.8, "Ralbag": 0.75,
    # Targumim (Aramaic translations)
    "Targum": 0.9, "Targum Onkelos": 0.9, "Targum Jonathan": 0.85,
    # Talmud and Midrash
    "Talmud": 0.8, "Midrash": 0.75, "Mishnah": 0.8,
    # Kabbalah/Zohar (Sod-level)
    "Zohar": 0.7, "Kabbalah": 0.7,
}

# Sefaria category → engine link type
CATEGORY_TYPE_MAP = {
    "Rashi": "rabbinic_midrash", "Ramban": "rabbinic_midrash",
    "Ibn Ezra": "rabbinic_midrash", "Rashbam": "rabbinic_midrash",
    "Sforno": "rabbinic_midrash", "Radak": "rabbinic_midrash",
    "Ralbag": "rabbinic_midrash", "Malbim": "rabbinic_midrash",
    "Metzudat David": "rabbinic_midrash", "Metzudat Tzion": "rabbinic_midrash",
    "Targum": "targum_commentary", "Targum Onkelos": "targum_commentary",
    "Targum Jonathan": "targum_commentary",
    "Zohar": "zohar_commentary", "Midrash": "midrash_rabbah",
    "Talmud": "talmud_quotation", "Mishnah": "mishnah_reference",
    "Sifra": "midrash_halakhic", "Sifrei": "midrash_halakhic",
    "Mekhilta": "midrash_halakhic", "Pesikta": "midrash_aggadic",
    "Commentary": "rabbinic_midrash",
    "Quoting Commentary": "rabbinic_quotation",
    "Chasidut": "chasidic_interpretation",
    "Kabbalah": "kabbalistic_interpretation",
    "Jewish Thought": "jewish_philosophy",
    "Reference": "scriptural_reference",
    "Tanakh": "scriptural_reference",
    "Musar": "musar_interpretation",
    "Halakhah": "halakhic_reference",
}

# Verse ID prefix for Tanakh books (chapter counts)
TANAKH_BOOKS = {
    'gen': 50, 'exo': 40, 'lev': 27, 'num': 36, 'deu': 34,
    'josh': 24, 'judg': 21, 'ruth': 4,
    '1sam': 31, '2sam': 24, '1kgs': 22, '2kgs': 25,
    '1chr': 29, '2chr': 36, 'ezra': 10, 'neh': 13, 'esth': 10,
    'job': 42, 'psa': 150, 'prov': 31, 'eccl': 12, 'song': 8,
    'isa': 66, 'jer': 52, 'lam': 5, 'ezek': 48, 'dan': 12,
    'hos': 14, 'joel': 3, 'amos': 9, 'obad': 1, 'jonah': 4,
    'mic': 7, 'nah': 3, 'hab': 3, 'zeph': 3, 'hag': 2,
    'zech': 14, 'mal': 4,
}

# Sefaria book name → engine book ID (reverse of mapper)
SEFARIA_BOOKS = {
    "Genesis": "gen", "Exodus": "exo", "Leviticus": "lev", "Numbers": "num", "Deuteronomy": "deu",
    "Joshua": "josh", "Judges": "judg", "Ruth": "ruth",
    "I Samuel": "1sam", "II Samuel": "2sam", "1 Samuel": "1sam", "2 Samuel": "2sam",
    "I Kings": "1kgs", "II Kings": "2kgs", "1 Kings": "1kgs", "2 Kings": "2kgs",
    "I Chronicles": "1chr", "II Chronicles": "2chr", "1 Chronicles": "1chr", "2 Chronicles": "2chr",
    "Ezra": "ezra", "Nehemiah": "neh", "Esther": "esth",
    "Job": "job", "Psalms": "psa", "Proverbs": "prov", "Ecclesiastes": "eccl",
    "Song of Songs": "song", "Isaiah": "isa", "Jeremiah": "jer",
    "Lamentations": "lam", "Ezekiel": "ezek", "Daniel": "dan",
    "Hosea": "hos", "Joel": "joel", "Amos": "amos", "Obadiah": "obad",
    "Jonah": "jonah", "Micah": "mic", "Nahum": "nah", "Habakkuk": "hab",
    "Zephaniah": "zeph", "Haggai": "hag", "Zechariah": "zech", "Malachi": "mal",
}

# Inverse: engine → Sefaria
ENGINE_TO_SEFARIA = {v: k for k, v in SEFARIA_BOOKS.items()}


def make_verse_id(ref):
    """Convert a Sefaria ref like 'Genesis 1:1' to engine ID 'gen.1.1'."""
    for sef_book, eng_book in SEFARIA_BOOKS.items():
        if ref.startswith(sef_book):
            rest = ref[len(sef_book):].strip()
            parts = rest.split(":")
            if len(parts) >= 2:
                chapter = parts[0]
                verse = parts[1].split("-")[0].split(":")[0]  # Handle ranges
                return f"{eng_book}.{chapter}.{verse}"
    return None


def fetch_links(verse_ref):
    """Fetch Sefaria links for a verse reference like 'Genesis 1:1'."""
    url = f"{API_BASE}/{urllib.request.quote(verse_ref, safe='')}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        return []
    except Exception:
        return []


def categorize_link(link):
    """Categorize a Sefaria link and return (category, confidence, link_type) or None if skip."""
    category = str(link.get("category", "") or "")
    collective = str(link.get("collectiveTitle", "") or link.get("ref", "") or "")

    # Match on collectiveTitle first (e.g., "Rashi", "Ramban", "Talmud")
    matched = None
    for known_cat in MAJOR_CATEGORIES:
        if known_cat.lower() in collective.lower() or known_cat.lower() in category.lower():
            matched = known_cat
            break

    # Also check by category directly
    if not matched and category in MAJOR_CATEGORIES:
        matched = category

    if not matched:
        return None  # Skip minor/unknown commentators

    confidence = MAJOR_CATEGORIES[matched]
    link_type = CATEGORY_TYPE_MAP.get(matched, "rabbinic_midrash")

    return (matched, confidence, link_type)


def process_book(book_id, conn, dry_run=False, max_verses=0):
    """Fetch and store Sefaria links for all verses in a book."""
    import random

    sef_book = ENGINE_TO_SEFARIA.get(book_id)
    if not sef_book:
        print(f"  Unknown book: {book_id}")
        return 0

    chapter_count = TANAKH_BOOKS.get(book_id, 10)
    total_connections = 0
    verses_processed = 0
    now = time.strftime('%Y-%m-%d')

    for ch in range(1, chapter_count + 1):
        # Get verse count for this chapter
        verse_count = conn.execute(
            "SELECT COUNT(*) FROM verses WHERE book_id=? AND chapter=?",
            (book_id, ch)
        ).fetchone()[0]

        if verse_count == 0:
            continue

        for vs in range(1, verse_count + 1):
            if max_verses and verses_processed >= max_verses:
                return total_connections

            sef_ref = f"{sef_book} {ch}:{vs}"
            verse_id = f"{book_id}.{ch}.{vs}"

            # Fetch links
            links = fetch_links(sef_ref)

            for link in links:
                cat_info = categorize_link(link)
                if not cat_info:
                    continue

                category, confidence, link_type = cat_info

                # The anchorRef is the base verse
                anchor = link.get("anchorRef", "")

                if not dry_run:
                    target_ref = f"sefaria:{category}:{random.randint(1, 1000000)}"
                    # Store the commentary reference as a connection
                    # source = the verse being commented on
                    # target = sefaria:commentator:ref
                    try:
                        conn.execute("""
                            INSERT OR IGNORE INTO connections
                                (source_verse, target_verse, layer, type, subtype,
                                 strength, confidence, discovered_by, metadata,
                                 quality_level, tradition, hermeneutic, created_at)
                            VALUES (?, ?, 'interpretive', ?, '',
                                    ?, ?, 'sefaria_api', ?,
                                    'probable', 'jewish', 'faith', ?)
                        """, (
                            verse_id,
                            target_ref,
                            link_type,
                            confidence * 0.8,
                            confidence,
                            json.dumps({
                                "commentator": category,
                                "sefaria_ref": link.get("ref", ""),
                                "anchor_ref": anchor,
                                "text_snippet": (link.get("text", "") or "")[:200],
                                "he_title": link.get("heTitle", ""),
                                "collective_title": link.get("collectiveTitle", ""),
                            }),
                            now,
                        ))
                        total_connections += 1
                    except Exception:
                        pass
                else:
                    total_connections += 1

            verses_processed += 1

            if verses_processed % 10 == 0:
                print(f"    [{book_id}] {verses_processed} verses, {total_connections} links")
                if not dry_run:
                    conn.commit()

            # Rate limit: 150ms between requests
            time.sleep(0.15)

    return total_connections


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import Sefaria links as connections")
    parser.add_argument("--books", type=str, default="", help="Comma-separated (e.g., 'gen,exo')")
    parser.add_argument("--limit", type=int, default=0, help="Max verses per book")
    parser.add_argument("--dry-run", action="store_true", help="Count only, no inserts")
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))

    # Determine which books to process
    if args.books:
        book_ids = [b.strip() for b in args.books.split(",") if b.strip()]
    else:
        book_ids = list(TANAKH_BOOKS.keys())

    # Filter to only known books
    book_ids = [b for b in book_ids if b in ENGINE_TO_SEFARIA]

    if not book_ids:
        print("No valid books specified. Available: " + ", ".join(ENGINE_TO_SEFARIA.keys()))
        conn.close()
        return

    total = 0
    for book_id in book_ids:
        sef_book = ENGINE_TO_SEFARIA[book_id]
        print(f"\n{'='*60}")
        print(f"Processing {sef_book} ({book_id})...")
        book_total = process_book(book_id, conn, dry_run=args.dry_run, max_verses=args.limit)
        total += book_total
        if not args.dry_run:
            conn.commit()
        print(f"  {sef_book}: {book_total} connections")

    print(f"\n{'='*60}")
    print(f"Total connections: {total}")
    if args.dry_run:
        print("DRY RUN — no data written. Remove --dry-run to import.")

    conn.close()


if __name__ == "__main__":
    main()
