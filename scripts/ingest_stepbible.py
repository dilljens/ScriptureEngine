#!/usr/bin/env python3
"""Ingest STEPBible TAGNT and TAHOT data for the textual connection layer.

TAGNT: Translators Amalgamated Greek NT
  Every word tagged with which editions contain it (NA, TR, SBL, etc.)
  Creates textual connections where editions differ.
TAHOT: Translators Amalgamated Hebrew OT
  Hebrew text with manuscript corrections and variant annotations.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from lib.db import add_connection, get_db

STEP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "STEPBible-Data")
OT_DIR = os.path.join(STEP_DIR, "Translators Amalgamated OT+NT")

# Map STEPBible book abbreviations to our book IDs
STEP_TO_OUR = {
    "Mat": "matt", "Mrk": "mark", "Luk": "luke", "Jhn": "john",
    "Act": "acts", "Rom": "rom", "1Co": "1cor", "2Co": "2cor",
    "Gal": "gal", "Eph": "eph", "Php": "phil", "Col": "col",
    "1Th": "1thes", "2Th": "2thes", "1Ti": "1tim", "2Ti": "2tim",
    "Tit": "titus", "Phm": "philem", "Heb": "heb", "Jas": "james",
    "1Pe": "1pet", "2Pe": "2pet", "1Jn": "1john", "2Jn": "2john",
    "3Jn": "3john", "Jud": "jude", "Rev": "rev",
    # OT books (for TAHOT)
    "Gen": "gen", "Exo": "exo", "Lev": "lev", "Num": "num", "Deu": "deu",
    "Jos": "josh", "Jdg": "judg", "Rut": "ruth",
    "1Sa": "1sam", "2Sa": "2sam", "1Ki": "1kgs", "2Ki": "2kgs",
    "1Ch": "1chr", "2Ch": "2chr", "Ezr": "ezra", "Neh": "neh",
    "Est": "esth", "Job": "job", "Psa": "psa", "Pro": "prov",
    "Ecc": "eccl", "Sng": "song",
    "Isa": "isa", "Jer": "jer", "Lam": "lam", "Ezk": "ezek", "Dan": "dan",
    "Hos": "hos", "Jol": "joel", "Amo": "amos", "Oba": "obad",
    "Jon": "jonah", "Mic": "mic", "Nam": "nah", "Hab": "hab",
    "Zep": "zeph", "Hag": "hag", "Zec": "zech", "Mal": "mal",
}

def parse_tagnt_line(line):
    """Parse a TAGNT data line.
    Format: Ref\tWordType\tGreek\tEnglish\tStrongs\tLemma\tEditions\t...
    Ref example: "Mat.1.1#01=NKO"
    """
    parts = line.strip().split('\t')
    if len(parts) < 7:
        return None

    # Parse reference
    ref = parts[0]
    m = re.match(r'^(\w+)\.(\d+)\.(\d+)#(\d+)=(\S+)$', ref)
    if not m:
        return None

    book_code = m.group(1)
    chapter = int(m.group(2))
    verse = int(m.group(3))
    word_type = m.group(5)  # e.g. "NKO", "NK(O)", "N(K)O", etc.

    book_id = STEP_TO_OUR.get(book_code)
    if not book_id:
        return None

    vid = f"{book_id}.{chapter}.{verse}"
    greek = parts[2] if len(parts) > 2 else ""
    english = parts[3] if len(parts) > 3 else ""

    # Determine which editions have this word from the word type
    # N = Nestlé-Aland, K = Textus Receptus/KJV, O = Other editions
    # Upper case = significant difference, lower case = minor/spelling difference
    # Parentheses = word is present but in different position
    has_na = 'N' in word_type.replace('(','').replace(')','')
    has_tr = 'K' in word_type.replace('(','').replace(')','')
    has_other = 'O' in word_type.replace('(','').replace(')','')

    # Determine variant significance
    is_variant = not (has_na and has_tr and has_other)

    return {
        "vid": vid,
        "greek": greek,
        "english": english,
        "word_type": word_type,
        "has_na": has_na,
        "has_tr": has_tr,
        "has_other": has_other,
        "is_variant": is_variant,
        "na_only": has_na and not has_tr,
        "tr_only": has_tr and not has_na,
    }

def ingest_tagnt(conn):
    """Ingest TAGNT data and create textual variant connections."""
    tagnt_files = [
        "TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
        "TAGNT Act-Rev - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt",
    ]

    verse_variants = {}  # vid → list of variant words
    total_words = 0
    variant_words = 0

    for fname in tagnt_files:
        fpath = os.path.join(OT_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  File not found: {fname}", flush=True)
            continue

        with open(fpath) as f:
            for line in f:
                parsed = parse_tagnt_line(line)
                if not parsed:
                    continue
                total_words += 1
                if parsed["is_variant"]:
                    variant_words += 1
                    vid = parsed["vid"]
                    if vid not in verse_variants:
                        verse_variants[vid] = []
                    verse_variants[vid].append(parsed)

    print(f"  Parsed {total_words} words, {variant_words} variant words", flush=True)
    print(f"  {len(verse_variants)} verses with variants", flush=True)

    # Create textual connections per verse with variants
    count = 0
    for vid, variants in verse_variants.items():
        # Determine the variant types present in this verse
        na_only = any(v["na_only"] for v in variants)
        tr_only = any(v["tr_only"] for v in variants)
        has_significant = any(
            v["word_type"] != v["word_type"].lower()
            and '(' not in v["word_type"]
            for v in variants
        )

        # Classify the type of variant
        if na_only and tr_only:
            vtype = "textual_variant"  # both traditions have unique words
        elif na_only:
            vtype = "quotation_variant"  # NA adds words not in TR
        elif tr_only:
            vtype = "textual_variant"  # TR/KJV adds words not in NA
        else:
            vtype = "textual_variant"

        # Sample to avoid too many connections per verse (max 5)
        sample_variants = variants[:5]
        strength = 0.7 if has_significant else 0.4

        try:
            add_connection(conn, vid, vid,
                          layer="textual",
                          type_name=vtype,
                          subtype="tagnt_editions",
                          strength=strength,
                          confidence=0.8,
                          discovered_by="algorithm",
                          metadata={
                              "source": "STEPBible/TAGNT",
                              "variant_word_count": len(variants),
                              "na_only_words": sum(1 for v in variants if v["na_only"]),
                              "tr_only_words": sum(1 for v in variants if v["tr_only"]),
                              "sample_variants": [
                                  {"greek": v["greek"], "type": v["word_type"]}
                                  for v in sample_variants
                              ],
                          })
            count += 1
        except Exception:
            pass

        if count % 500 == 0:
            conn.commit()

    conn.commit()
    return count


def main():
    conn = get_db()

    print("=" * 60)
    print("STEPBible Ingestion — TAGNT + TAHOT")
    print("=" * 60)

    # Step 1: TAGNT
    print("\n--- NT Variants (TAGNT) ---", flush=True)
    tagnt_count = ingest_tagnt(conn)
    print(f"  TAGNT connections: {tagnt_count}", flush=True)

    # Step 2: TAHOT (Hebrew OT corrections)
    print("\n--- OT Variants (TAHOT) ---", flush=True)
    tahot_files = [f for f in os.listdir(OT_DIR) if f.startswith("TAHOT")]
    tahot_count = 0
    for fname in tahot_files:
        fpath = os.path.join(OT_DIR, fname)
        if not os.path.isfile(fpath):
            continue
        # Simple parsing: each verse reference indicates presence of a corrected text
        with open(fpath) as f:
            for line in f:
                if line.startswith("$"):
                    continue
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    continue
                m = re.match(r'^(\w+)\.(\d+)\.(\d+)', parts[0])
                if not m:
                    continue
                book_id = STEP_TO_OUR.get(m.group(1))
                if not book_id:
                    continue
                vid = f"{book_id}.{int(m.group(2))}.{int(m.group(3))}"
                try:
                    add_connection(conn, vid, vid,
                                  layer="textual",
                                  type_name="textual_variant",
                                  subtype="tahot_corrections",
                                  strength=0.5,
                                  confidence=0.7,
                                  discovered_by="algorithm",
                                  metadata={
                                      "source": "STEPBible/TAHOT",
                                      "note": "TAHOT corrected Hebrew text",
                                  })
                    tahot_count += 1
                except Exception:
                    pass

    conn.commit()
    print(f"  TAHOT connections: {tahot_count}", flush=True)

    # Summary
    total = conn.execute("SELECT COUNT(*) as c FROM connections WHERE layer='textual'").fetchone()["c"]
    print(f"\n  Textual layer total: {total}")
    conn.close()

if __name__ == "__main__":
    main()
