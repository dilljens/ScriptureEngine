#!/usr/bin/env python3
"""
Entity Linking Migration — Link verses to entities in entity_links.

Populates the `verse_entities` table by scanning verse text for entity names.

Strategy (multi-pass, best-effort):
  1. Scan English text for entity english_name occurrences
  2. For Hebrew entities, scan Hebrew text for exact/precise matches
  3. For Greek entities, scan Greek text for exact matches
  4. Fallback: scan English for partial name matches (for multi-word names)

This is a heuristic first pass. Edges can be hand-curated later.

Usage:
  python3 scripts/link_entities.py
  ./run.sh link_entities          # after adding to run.sh
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.db import get_db


def get_entity_name_variants(row):
    """Generate name variants for an entity to match against verse text."""
    names = set()
    en = (row["english_name"] or "").strip()
    he = (row["hebrew_name"] or "").strip()
    gr = (row["greek_name"] or "").strip()

    if en:
        names.add(en.lower())
        # Single-word names only for substring matching to avoid noise
        if len(en.split()) == 1:
            names.add(en.lower())
        else:
            names.add(en.lower())  # exact match for multi-word

    if he:
        # Hebrew — match as-is (already consonantal)
        names.add(he)

    if gr:
        # Greek — match as-is
        names.add(gr)

    return names


def main():
    conn = get_db()

    # Count existing entities
    entity_count = conn.execute("SELECT COUNT(*) as c FROM entity_links").fetchone()["c"]
    print(f"Entities to link: {entity_count}")

    # Get all verse IDs for scanning (in bulk for performance)
    verse_batch = conn.execute(
        "SELECT id, text_english, text_hebrew, text_greek FROM verses"
    ).fetchall()
    print(f"Verses to scan: {len(verse_batch)}")

    # Count existing links (resume capability)
    existing = conn.execute("SELECT COUNT(*) as c FROM verse_entities").fetchone()["c"]
    if existing:
        print(f"Existing verse_entity links: {existing} (will merge)")

    # Get all entities
    entities = conn.execute("SELECT * FROM entity_links").fetchall()

    linked = 0
    skipped = 0

    for e in entities:
        eid = e["entity_id"]
        variants = get_entity_name_variants(e)

        if not variants:
            skipped += 1
            continue

        for vid, text_en, text_he, text_gr in verse_batch:
            match_confidence = 0.0

            for variant in variants:
                if not variant:
                    continue
                v_lower = variant.lower()

                # English exact word match (case-insensitive)
                if text_en and len(variant.split()) == 1:
                    # Use word boundary regex for single-word names
                    pattern = re.compile(r'\b' + re.escape(v_lower) + r'\b', re.IGNORECASE)
                    if pattern.search(text_en):
                        conf = 0.7  # exact English word match is strong
                        if conf > match_confidence:
                            match_confidence = conf
                    else:
                        # Also check for partial word match (e.g., "Abraham" in "Abraham's")
                        partial_pattern = re.compile(re.escape(v_lower), re.IGNORECASE)
                        if partial_pattern.search(text_en):
                            conf = 0.5  # partial match is weaker
                            if conf > match_confidence:
                                match_confidence = conf

                elif text_en and len(variant.split()) > 1:
                    # Multi-word name — exact phrase match
                    pattern = re.compile(re.escape(v_lower), re.IGNORECASE)
                    if pattern.search(text_en):
                        conf = 0.8  # multi-word exact phrase is very strong
                        if conf > match_confidence:
                            match_confidence = conf

                # Hebrew exact match (already consonantal)
                if text_he and variant and any('\u0590' <= c <= '\u05FF' for c in variant) and variant in text_he:
                    conf = 0.85  # Hebrew text match is strong
                    if conf > match_confidence:
                        match_confidence = conf

                # Greek exact match
                if text_gr and variant and any('\u0370' <= c <= '\u03FF' for c in variant) and variant in text_gr:
                    conf = 0.75  # Greek text match
                    if conf > match_confidence:
                        match_confidence = conf

            if match_confidence > 0:
                try:
                    conn.execute("""
                        INSERT INTO verse_entities (verse_id, entity_id, relationship_type, confidence)
                        VALUES (?, ?, 'mentions', ?)
                        ON CONFLICT(verse_id, entity_id, relationship_type) DO UPDATE SET
                            confidence = MAX(verse_entities.confidence, excluded.confidence)
                    """, (vid, eid, round(match_confidence, 2)))
                    linked += 1
                except Exception:
                    pass  # skip FK violations gracefully

        # Progress indicator
        if (linked + skipped) % 50 == 0:
            conn.commit()
            print(f"  Progress: {linked} links created, {skipped} skipped...", end="\r")

    conn.commit()
    print(f"\nDone! {linked} verse-entity links created, {skipped} entities skipped (no name variants).")

    # Summary
    summary = conn.execute("""
        SELECT entity_type, COUNT(*) as count
        FROM verse_entities ve
        JOIN entity_links el ON el.entity_id = ve.entity_id
        GROUP BY el.entity_type
        ORDER BY count DESC
    """).fetchall()
    print("\nLinks by entity type:")
    for r in summary:
        print(f"  {r['entity_type'] or 'unknown'}: {r['count']}")

    # Top linked verses
    top = conn.execute("""
        SELECT ve.verse_id, COUNT(*) as entity_count,
               v.text_english, b.title as book
        FROM verse_entities ve
        JOIN verses v ON v.id = ve.verse_id
        JOIN books b ON b.id = v.book_id
        GROUP BY ve.verse_id
        ORDER BY entity_count DESC
        LIMIT 10
    """).fetchall()
    print("\nMost entity-rich verses:")
    for r in top:
        print(f"  {r['verse_id']} ({r['book']}): {r['entity_count']} entities — {r['text_english'][:80]}")


    conn.close()


if __name__ == "__main__":
    main()
