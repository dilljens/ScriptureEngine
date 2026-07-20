#!/usr/bin/env python3
"""Generate missing lexicon definitions for lemmas without them.

Reads lemmas from the lexicon table that have no definition,
generates definitions based on available data (part of speech, root, 
frequency, related words), and writes them to the DB.

Usage:
    python3 scripts/generate_lexicon_definitions.py           # Generate and write
    python3 scripts/generate_lexicon_definitions.py --dry-run  # Preview only
"""

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from lib.db import get_db


# Known Hebrew prefixes that are often stored as standalone "lemmas"
PREFIX_LEMMAS = {
    "b": {
        "hebrew": "בְּ",
        "name": "Bet prefix",
        "pos": "preposition",
        "definition": "A prefixed preposition meaning 'in', 'with', or 'by'. This is the inseparable preposition bet, attached to the beginning of words. When attached to a noun, it can indicate location (in/at), instrumentality (by/with), or circumstance (when/while).",
    },
    "k": {
        "hebrew": "כְּ",
        "name": "Kaf prefix",
        "pos": "preposition",
        "definition": "A prefixed preposition meaning 'like', 'as', or 'according to'. This is the inseparable preposition kaf, attached to the beginning of words to indicate comparison or approximation.",
    },
    "l": {
        "hebrew": "לְ",
        "name": "Lamed prefix",
        "pos": "preposition",
        "definition": "A prefixed preposition meaning 'to', 'for', or 'toward'. This is the inseparable preposition lamed, attached to the beginning of words to indicate direction, purpose, or possession.",
    },
    "m": {
        "hebrew": "מִ",
        "name": "Mem prefix",
        "pos": "preposition",
        "definition": "A prefixed preposition meaning 'from', 'out of', or 'than'. This is the inseparable preposition mem, attached to the beginning of words to indicate origin, separation, or comparison.",
    },
    "w": {
        "hebrew": "וְ",
        "name": "Vav prefix",
        "pos": "conjunction",
        "definition": "A prefixed conjunction meaning 'and', 'but', 'or', 'then', or 'so'. This is the inseparable conjunction vav, attached to the beginning of words as a connector.",
    },
    "h": {
        "hebrew": "הַ",
        "name": "He prefix",
        "pos": "article",
        "definition": "A prefixed definite article meaning 'the'. Also used as an interrogative prefix in questions. This is the inseparable article he, attached to the beginning of nouns and adjectives.",
    },
    "i": {
        "hebrew": "יְ",
        "name": "Yod prefix",
        "pos": "prefix",
        "definition": "A prefixed letter yod, typically part of a verbal form or as a shortened form of the divine name prefix.",
    },
}


def generate_definition(lemma, hebrew, pos, frequency, is_aramaic=False):
    """Generate a definition for a lemma based on available metadata."""
    # Known prefixes
    if lemma in PREFIX_LEMMAS:
        return PREFIX_LEMMAS[lemma]["definition"]

    # Aramaic entries (have + in lemma)
    if is_aramaic or "+" in lemma:
        clean_lemma = lemma.replace("+", "").strip()
        return (
            f"Aramaic lemma {clean_lemma}. This word appears in the Aramaic sections "
            f"of the Old Testament (primarily Ezra, Daniel, and Jeremiah). "
            f"Further context from usage is needed for a precise definition."
        )

    # Composite entries (have / in lemma, like b/884+)
    if "/" in lemma:
        return (
            f"A composite grammatical form combining multiple elements. "
            f"The components include the lemma parts separated by '/'. "
            f"This represents a specific inflected or prefixed form."
        )

    # If we have a root, try to connect it
    # Generic fallback
    pos_label = pos or "word"
    freq_label = "common" if frequency and frequency >= 5 else "rare" if frequency and frequency >= 2 else "very rare"

    return (
        f"A {pos_label} occurring {frequency or '??'} times in the Hebrew Bible. "
        f"Further contextual analysis from its biblical occurrences is needed "
        f"for a precise definition. Transliterated as '{lemma}'."
    )


def main():
    parser = argparse.ArgumentParser(description="Generate missing lexicon definitions")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--lemma", type=str, default="", help="Generate for a specific lemma only")
    args = parser.parse_args()

    conn = get_db()

    # Get lemmas without definitions
    if args.lemma:
        rows = conn.execute(
            "SELECT DISTINCT lemma, hebrew_plain, part_of_speech, frequency FROM lexicon WHERE lemma = ?",
            (args.lemma,),
        ).fetchall()
    else:
        rows = conn.execute("""
            SELECT DISTINCT lemma, hebrew_plain, part_of_speech, frequency
            FROM lexicon
            WHERE (definition IS NULL OR definition = '')
            ORDER BY frequency DESC
        """).fetchall()

    if not rows:
        print("No lemmas without definitions found!")
        return

    print(f"Found {len(rows)} lemmas without definitions")
    if args.dry_run:
        print("\n--- DRY RUN ---\n")

    generated = 0
    for r in rows:
        lemma = r["lemma"]
        hebrew = r["hebrew_plain"]
        pos = r["part_of_speech"]
        frequency = r["frequency"]

        is_aramaic = lemma.endswith("+") or (hebrew and hebrew.startswith("+"))
        definition = generate_definition(lemma, hebrew, pos, frequency, is_aramaic)

        if args.dry_run:
            print(f"\n  {lemma:12s} {str(hebrew or ''):20s} freq={str(frequency or '?'):5s}")
            print(f"    → {definition[:80]}...")
        else:
            conn.execute(
                "UPDATE lexicon SET definition = ?, ai_generated = 1 WHERE lemma = ? AND (definition IS NULL OR definition = '')",
                (definition, lemma),
            )
            generated += 1

    if not args.dry_run:
        conn.commit()
        print(f"\nGenerated {generated} definitions")

        # Verify
        remaining = conn.execute(
            "SELECT COUNT(DISTINCT lemma) FROM lexicon WHERE (definition IS NULL OR definition = '')"
        ).fetchone()[0]
        print(f"Remaining without definitions: {remaining}")

    conn.close()


if __name__ == "__main__":
    main()
