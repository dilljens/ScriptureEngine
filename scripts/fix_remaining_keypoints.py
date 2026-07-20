#!/usr/bin/env python3
"""Add key points to remaining 22 lessons that still have generic fallbacks."""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

KP = {
    "noun_pattern_qatl": [
        "Noun pattern: C1-a-C2-e-C3 (qatl)",
        "Example: \u05de\u05b6\u05dc\u05b6\u05da\u05b0 (melekh = king), root \u05de-\u05dc-\u05db",
        "One of the most common noun patterns",
        "Often concrete objects or basic concepts",
    ],
    "noun_pattern_qitl": [
        "Noun pattern: C1-i-C2-e-C3 (qitl)",
        "Example: \u05e1\u05b5\u05e4\u05b6\u05e8 (sefer = book), root \u05e1-\u05e4-\u05e8",
        "Often indicates concrete objects or instruments",
        "Distinct from qatl pattern by first vowel (i vs a)",
    ],
    "noun_pattern_qutl": [
        "Noun pattern: C1-u-C2-e-C3 (qutl)",
        "Example: \u05e7\u05b9\u05d3\u05b6\u05e9\u05c1 (qodesh = holiness), root \u05e7-\u05d3-\u05e9\u05c1",
        "Often indicates abstract concepts",
        "Least common of the three primary noun patterns",
    ],
    "prefix_bet": [
        "Prefix \u05d1\u05b0\u05bc (bet) = \u201cin / with / by\u201d",
        "Takes sheva: \u05d1\u05b0\u05bc (b\u0259)",
        "Before vocal sheva: \u05d1\u05b4\u05bc (bi); before article: \u05d1\u05b7\u05bc (ba)",
        "One of the inseparable prepositions",
    ],
    "prefix_he": [
        "Prefix \u05d4\u05b7 (he) = definite article \u201cthe\u201d",
        "Attached to beginning of noun",
        "Doubles next letter with dagesh forte",
        "Before gutturals: vowel may lengthen to \u05d4\u05b6 or \u05d4\u05b8",
    ],
    "prefix_kaf": [
        "Prefix \u05db\u05b0\u05bc (kaf) = \u201cas / like\u201d",
        "Takes sheva: \u05db\u05b0\u05bc (k\u0259)",
        "Before article: \u05db\u05b7\u05bc (ka)",
        "One of the inseparable prepositions",
    ],
    "prefix_lamed": [
        "Prefix \u05dc\u05b0 (lamed) = \u201cto / for\u201d",
        "Takes sheva: \u05dc\u05b0 (l\u0259)",
        "Before article: \u05dc\u05b7 (la)",
        "Also marks infinitive construct: \u05dc\u05b4\u05db\u05b0\u05ea\u05b9\u05d1 (to write)",
    ],
    "prefix_mem": [
        "Prefix \u05de\u05b4 (mem) = \u201cfrom\u201d",
        "Takes hiriq: \u05de\u05b4 (mi)",
        "Before article: \u05de\u05b5 (m\u0113) or \u05de\u05b4\u05df (min)",
        "One of the inseparable prepositions",
    ],
    "prefix_shin": [
        "Prefix \u05e9\u05b6\u05c1 (shin) = \u201cthat / which\u201d",
        "Relative particle introducing clauses",
        "Takes sheva or tsere: \u05e9\u05b6\u05c1 (she)",
        "Functions like \u05d0\u05b2\u05e9\u05b6\u05c1\u05e8 (who/which/that)",
    ],
    "prefix_vav": [
        "Prefix \u05d5\u05b0 (vav) = \u201cand\u201d",
        "Takes sheva: \u05d5\u05b0 (w\u0259)",
        "Changes form: before labials \u2192 \u05d5\u05bc (\u016b); before stress \u2192 \u05d5\u05b8 (w\u0101)",
        "Vav-consecutive changes tense of verb",
    ],
    "root_extraction": [
        "Remove prefixes (\u05d1,\u05db,\u05dc,\u05de,\u05d4,\u05d5,\u05e9) and suffixes (\u05d9,\u05da\u05b8,\u05d5,\u05e0\u05d5\u05bc,\u05ea,\u05dd,\u05d4)",
        "Remove vowel pattern letters",
        "The remaining 3 consonants = the root",
        "Example: \u05de\u05b4\u05db\u05b0\u05ea\u05b8\u05d1 \u2192 remove \u05de prefix \u2192 root \u05db\u05ea\u05d1",
    ],
    "suffix_plural_m": [
        "Masculine plural suffix: \u05be\u05b4\u05d9\u05dd (-im)",
        "Example: \u05de\u05b6\u05dc\u05b6\u05da\u05b0 (king) \u2192 \u05de\u05b0\u05dc\u05b8\u05db\u05b4\u05d9\u05dd (kings)",
        "Vowel pattern often changes when suffix added",
        "Most common plural ending",
    ],
    "suffix_plural_f": [
        "Feminine plural suffix: \u05be\u05d5\u05b9\u05ea (-ot)",
        "Example: \u05ea\u05bc\u05d5\u05b9\u05e8\u05b8\u05d4 (torah) \u2192 \u05ea\u05bc\u05d5\u05b9\u05e8\u05d5\u05b9\u05ea (torahs/laws)",
        "Opposite of English expectation (-ot is feminine, -im is masculine)",
        "Some masculine nouns take -ot (irregular)",
    ],
    "suffix_pron_1s": [
        "1st person singular suffix: \u05be\u05b4\u05d9 (-i) = \u201cmy\u201d",
        "Example: \u05d3\u05b8\u05d1\u05b8\u05e8 (word) \u2192 \u05d3\u05b0\u05bc\u05d1\u05b8\u05e8\u05b4\u05d9 (my word)",
        "Added to nouns for possession",
        "Noun takes construct-like form before suffix",
    ],
    "suffix_pron_2ms": [
        "2nd person masculine singular: \u05be\u05da\u05b8 (-kha) = \u201cyour\u201d",
        "Example: \u05d3\u05b8\u05d1\u05b8\u05e8 \u2192 \u05d3\u05b0\u05bc\u05d1\u05b8\u05e8\u05b0\u05da\u05b8 (your word)",
        "Marked by final \u05b8 (qamats) + \u05da",
        "Distinct from 2fs form: \u05be\u05b5\u05da\u05b0 (your, feminine)",
    ],
    "suffix_pron_3ms": [
        "3rd person masculine singular: \u05d5\u05b9 (-o) = \u201c-his\u201d",
        "Also \u05be\u05b8\u05d9\u05d5 (-av) for plural nouns",
        "Example: \u05d3\u05b8\u05d1\u05b8\u05e8 \u2192 \u05d3\u05b0\u05bc\u05d1\u05b8\u05e8\u05d5\u05b9 (his word)",
        "Most common pronominal suffix in biblical text",
    ],
    "suffix_pron_1p": [
        "1st person plural suffix: \u05be\u05e0\u05d5\u05bc (-nu) = \u201cour\u201d",
        "Example: \u05d3\u05b8\u05d1\u05b8\u05e8 \u2192 \u05d3\u05b0\u05bc\u05d1\u05b8\u05e8\u05b5\u05e0\u05d5\u05bc (our word)",
        "Same in both masculine and feminine",
        "Connective vowel often appears before suffix",
    ],
    "reading_connections": [
        "Connections link passages across the canon",
        "Types: quotations, allusions, thematic parallels",
        "Common: Angel of YHWH, covenant formula, temple vision",
        "Connections deepen comprehension beyond individual verses",
    ],
    "reading_genesis": [
        "Genesis (\u05d1\u05b0\u05bc\u05e8\u05b5\u05d0\u05e9\u05c1\u05b4\u05d9\u05ea) = book of beginnings",
        "Creation (Gen 1) to family narratives (Gen 12-50)",
        "Key vocab: \u05d1\u05b8\u05bc\u05e8\u05b8\u05d0 (create), \u05d0\u05b8\u05de\u05b7\u05e8 (say), \u05d4\u05b8\u05d9\u05b8\u05d4 (be)",
        "Repeated formula: \u05d0\u05b5\u05dc\u05bc\u05b6\u05d4 \u05ea\u05d5\u05b9\u05dc\u05b0\u05d3\u05b9\u05ea (these are the generations)",
    ],
    "reading_psalms": [
        "Psalms (\u05ea\u05b0\u05bc\u05d4\u05b4\u05dc\u05bc\u05b4\u05d9\u05dd) = biblical poetry",
        "Key features: parallelism (synonymous, antithetic, synthetic)",
        "Compact vocabulary, frequent imperatives/volitives",
        "Psalm 1, 23, 100, 121 are excellent entry points",
    ],
    "reading_isaiah": [
        "Isaiah (\u05d9\u05b0\u05e9\u05b7\u05c1\u05e2\u05b0\u05d9\u05b8\u05d4\u05d5\u05bc) = major prophet",
        "Rich in temple theology, messianic prophecy, poetry",
        "Ch 1-39: oracles of judgment; Ch 40-66: restoration",
        "Chapter 6 (temple vision) is the most famous passage",
    ],
    "reading_torah": [
        "Torah = foundation of Biblical Hebrew study",
        "Primarily narrative prose with embedded poetry and laws",
        "More limited vocabulary than Prophets \u2014 ideal for beginners",
        "Genesis 1-3, Exodus 1-15, Deuteronomy 6-8 are good starting points",
    ],
}


def main():
    conn = sqlite3.connect(str(MEM_DB))
    updated = 0
    for nid, kp in KP.items():
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (nid,)).fetchone()
        if not row:
            print(f"  SKIP {nid}: not found")
            continue
        content = json.loads(row[0])
        content["key_points"] = kp
        conn.execute(
            "UPDATE hebrew_lessons SET content_json=? WHERE node_id=?",
            (json.dumps(content, ensure_ascii=False), nid),
        )
        # Update node description if generic
        node = conn.execute("SELECT description FROM hebrew_nodes WHERE id=?", (nid,)).fetchone()
        if node and node[0] in ("Key concept in word", "Key concept in reading",
                                 "Review the explanation above", ""):
            conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (kp[0], nid))
        updated += 1
        print(f"  FIX {nid}: {kp[0][:60]}")
    
    conn.commit()
    conn.close()
    print(f"\n  Updated {updated} lessons")


if __name__ == "__main__":
    main()
