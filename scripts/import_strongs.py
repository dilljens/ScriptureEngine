#!/usr/bin/env python3
"""Import Strong's Hebrew and Greek definitions into the lexicon table."""

import os
import sys
import unicodedata

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import xml.etree.ElementTree as ET

from lib.db import get_db
from lib.lexicon import init_lexicon_tables

NS = "http://openscriptures.github.com/morphhb/namespace"
H_XML = "/tmp/HebrewLexicon/HebrewStrong.xml"
G_XML = "/tmp/strongs-dictionary-xml/strongsgreek.xml"


def parse_hebrew(filepath):
    """Parse HebrewLexicon OSIS XML into list of entry dicts."""
    entries = []
    tree = ET.parse(filepath)
    root = tree.getroot()

    for entry_elem in root.findall(f"{{{NS}}}entry"):
        entry_id = entry_elem.get("id", "")
        if not entry_id.startswith("H"):
            continue

        w = entry_elem.find(f"{{{NS}}}w")
        hebrew = ""
        transliteration = ""
        pos = ""
        if w is not None:
            hebrew = (w.text or "").strip()
            transliteration = (w.get("xlit") or "").strip()
            pos = (w.get("pos") or "").strip()

        meaning = entry_elem.find(f"{{{NS}}}meaning")
        usage = entry_elem.find(f"{{{NS}}}usage")

        definition = ""
        if meaning is not None:
            definition = "".join(meaning.itertext()).strip()
        if usage is not None and usage.text:
            usage_text = usage.text.strip()
            if usage_text:
                if definition:
                    definition += " — Usage: " + usage_text
                else:
                    definition = usage_text

        entries.append({
            "lemma": entry_id,
            "hebrew": hebrew,
            "transliteration": transliteration,
            "part_of_speech": pos,
            "definition": definition,
        })

    return entries


def parse_greek(filepath):
    """Parse morphgnt Strong's Greek XML into list of entry dicts."""
    entries = []
    tree = ET.parse(filepath)
    root = tree.getroot()

    for entry_elem in root.findall(".//entry"):
        strongs_raw = entry_elem.get("strongs", "")
        if not strongs_raw:
            continue

        lemma = f"G{int(strongs_raw)}"

        greek = entry_elem.find("greek")
        greek_text = ""
        translit = ""
        if greek is not None:
            greek_text = (greek.get("unicode") or "").strip()
            translit = (greek.get("translit") or "").strip()

        strongs_def = entry_elem.find("strongs_def")
        kjv_def = entry_elem.find("kjv_def")

        definition = ""
        if strongs_def is not None:
            definition = "".join(strongs_def.itertext()).strip()
        if kjv_def is not None:
            kjv_text = "".join(kjv_def.itertext()).strip()
            if kjv_text:
                if definition:
                    definition += " " + kjv_text
                else:
                    definition = kjv_text

        entries.append({
            "lemma": lemma,
            "greek": greek_text,
            "transliteration": translit,
            "definition": definition,
        })

    return entries


def import_entries(conn, entries, entry_type="hebrew"):
    """UPSERT entries into lexicon table."""
    count = 0
    batch = []

    for e in entries:
        lemma = e["lemma"]
        hebrew = e.get("hebrew") or e.get("greek") or ""
        if entry_type == "greek" and hebrew:
            hebrew = unicodedata.normalize("NFC", hebrew)
        transliteration = e.get("transliteration", "")
        definition = e.get("definition", "")
        pos = e.get("part_of_speech", "")

        batch.append((lemma, hebrew, transliteration, definition, pos))

        if len(batch) >= 200:
            _do_upsert(conn, batch)
            count += len(batch)
            batch = []

    if batch:
        _do_upsert(conn, batch)
        count += len(batch)

    return count


def _do_upsert(conn, batch):
    conn.executemany("""
        INSERT INTO lexicon (lemma, hebrew, transliteration, definition, definition_source, part_of_speech)
        VALUES (?, ?, ?, ?, 'strongs', ?)
        ON CONFLICT(lemma) DO UPDATE SET
            definition = COALESCE(excluded.definition, definition),
            definition_source = CASE WHEN excluded.definition IS NOT NULL THEN 'strongs' ELSE definition_source END,
            hebrew = COALESCE(excluded.hebrew, hebrew),
            transliteration = COALESCE(excluded.transliteration, transliteration),
            part_of_speech = COALESCE(excluded.part_of_speech, part_of_speech)
    """, batch)


def main():
    print("=" * 60)
    print("Strong's Definitions Importer")
    print("=" * 60)

    conn = get_db()
    init_lexicon_tables(conn)

    heb_count = 0
    gk_count = 0

    # -- Hebrew --
    if os.path.exists(H_XML):
        print(f"\nParsing Hebrew XML: {H_XML}")
        try:
            heb_entries = parse_hebrew(H_XML)
            print(f"  Parsed {len(heb_entries)} entries")
            heb_count = import_entries(conn, heb_entries, "hebrew")
            conn.commit()
            print(f"  Imported {heb_count} Hebrew definitions")
        except Exception as e:
            print(f"  ERROR parsing Hebrew XML: {e}")
    else:
        print(f"\n  Skipping Hebrew: {H_XML} not found")

    # -- Greek --
    if os.path.exists(G_XML):
        print(f"\nParsing Greek XML: {G_XML}")
        try:
            gk_entries = parse_greek(G_XML)
            print(f"  Parsed {len(gk_entries)} entries")
            gk_count = import_entries(conn, gk_entries, "greek")
            conn.commit()
            print(f"  Imported {gk_count} Greek definitions")
        except Exception as e:
            print(f"  ERROR parsing Greek XML: {e}")
    else:
        print(f"\n  Skipping Greek: {G_XML} not found")

    print(f"\nImported {heb_count} Hebrew, {gk_count} Greek definitions")

    total = conn.execute("SELECT COUNT(*) as c FROM lexicon").fetchone()["c"]
    strongs_count = conn.execute(
        "SELECT COUNT(*) as c FROM lexicon WHERE definition_source = 'strongs'"
    ).fetchone()["c"]
    print(f"Lexicon total: {total} entries ({strongs_count} from Strong's)")

    conn.close()


if __name__ == "__main__":
    main()
