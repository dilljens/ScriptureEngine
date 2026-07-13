#!/usr/bin/env python3
"""Build the Hebrew knowledge graph (H1).

Creates ~200 concept nodes across 7 levels with prerequisite and
encompassing edges for FIRe-based spaced repetition.

Usage:
    python3 scripts/build_hebrew_graph.py
    python3 scripts/build_hebrew_graph.py --db data/memorize.db
"""

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Graph Schema ──

SCHEMA = """
CREATE TABLE IF NOT EXISTS hebrew_nodes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    level INTEGER NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS hebrew_edges (
    source_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    target_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    edge_type TEXT NOT NULL DEFAULT 'prerequisite',
    weight REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id, edge_type)
);

CREATE INDEX IF NOT EXISTS idx_hebrew_edges_source ON hebrew_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_hebrew_edges_target ON hebrew_edges(target_id);
"""

# ── Level 1: Aleph-Bet (22 consonants + 5 finals) ──

LEVEL1 = [
    ("aleph", "א", "Aleph", "consonant", "Glottal stop, silent"),
    ("bet", "בּ", "Bet", "consonant", "B sound (with dagesh), V sound (without)"),
    ("gimel", "ג", "Gimel", "consonant", "G sound"),
    ("dalet", "ד", "Dalet", "consonant", "D sound (with dagesh), Dh sound (without)"),
    ("he", "ה", "He", "consonant", "H sound, often silent at word end"),
    ("vav", "ו", "Vav", "consonant", "V sound, also used as vowel letter"),
    ("zayin", "ז", "Zayin", "consonant", "Z sound"),
    ("chet", "ח", "Chet", "consonant", "CH sound (guttural)"),
    ("tet", "ט", "Tet", "consonant", "T sound (emphatic)"),
    ("yod", "י", "Yod", "consonant", "Y sound, also used as vowel letter"),
    ("kaf", "כ", "Kaf", "consonant", "K sound (with dagesh), KH sound (without)"),
    ("kaf_final", "ך", "Kaf (final)", "consonant", "Final form of Kaf"),
    ("lamed", "ל", "Lamed", "consonant", "L sound"),
    ("mem", "מ", "Mem", "consonant", "M sound"),
    ("mem_final", "ם", "Mem (final)", "consonant", "Final form of Mem"),
    ("nun", "נ", "Nun", "consonant", "N sound"),
    ("nun_final", "ן", "Nun (final)", "consonant", "Final form of Nun"),
    ("samekh", "ס", "Samekh", "consonant", "S sound"),
    ("ayin", "ע", "Ayin", "consonant", "Guttural sound, silent in many traditions"),
    ("pe", "פ", "Pe", "consonant", "P sound (with dagesh), F sound (without)"),
    ("pe_final", "ף", "Pe (final)", "consonant", "Final form of Pe"),
    ("tsade", "צ", "Tsade", "consonant", "TS sound"),
    ("tsade_final", "ץ", "Tsade (final)", "consonant", "Final form of Tsade"),
    ("qof", "ק", "Qof", "consonant", "Q sound (emphatic K)"),
    ("resh", "ר", "Resh", "consonant", "R sound"),
    ("shin", "שׁ", "Shin", "consonant", "SH sound (right dot)"),
    ("sin", "שׂ", "Sin", "consonant", "S sound (left dot)"),
    ("tav", "ת", "Tav", "consonant", "T sound (with dagesh), Th sound (without)"),
]

# ── Level 2: Vowels ──

LEVEL2 = [
    ("vowel_patah", "ַ", "Patah", "vowel", "A sound, short"),
    ("vowel_qamats", "ָ", "Qamats", "vowel", "A sound, long (qamats gadol)"),
    ("vowel_qamats_qatan", "ָ", "Qamats Qatan", "vowel", "O sound (qamats in closed syllable)"),
    ("vowel_hiriq", "ִ", "Hiriq", "vowel", "I sound, short"),
    ("vowel_hiriq_yod", "ִי", "Hiriq Yod", "vowel", "I sound, long (with mater)"),
    ("vowel_tsere", "ֵ", "Tsere", "vowel", "E sound, long"),
    ("vowel_tsere_yod", "ֵי", "Tsere Yod", "vowel", "E sound, long (with yod)"),
    ("vowel_segol", "ֶ", "Segol", "vowel", "E sound, short"),
    ("vowel_segol_yod", "ֶי", "Segol Yod", "vowel", "E sound (with yod)"),
    ("vowel_holam", "ֹ", "Holam Haser", "vowel", "O sound, short"),
    ("vowel_holam_vav", "וֹ", "Holam Male", "vowel", "O sound, long (with vav)"),
    ("vowel_shuruq", "וּ", "Shuruq", "vowel", "U sound, long (vav with dagesh)"),
    ("vowel_qubuts", "ֻ", "Qubuts", "vowel", "U sound, short"),
    ("vowel_sheva", "ְ", "Sheva", "vowel", "Either silent (sheva nah) or E sound (sheva na)"),
    ("vowel_sheva_na", "ְ", "Sheva Na", "vowel", "Vocal sheva — pronounced as brief E"),
    ("vowel_sheva_nah", "ְ", "Sheva Nah", "vowel", "Silent sheva — syllable closer"),
    ("vowel_hataf_patah", "ֲ", "Hataf Patah", "vowel", "A sound, reduced (on gutturals)"),
    ("vowel_hataf_qamats", "ֳ", "Hataf Qamats", "vowel", "O sound, reduced"),
    ("vowel_hataf_segol", "ֱ", "Hataf Segol", "vowel", "E sound, reduced"),
]

# ── Level 3: Syllables ──

LEVEL3 = [
    ("syllable_basics", "syllable", "Syllable Basics", "syllable", "CV and CVC syllable structure"),
    ("syllable_open", "CV", "Open Syllable", "syllable", "Consonant-Vowel, ends in vowel"),
    ("syllable_closed", "CVC", "Closed Syllable", "syllable", "Consonant-Vowel-Consonant"),
    ("syllable_stress", "stress", "Stress Patterns", "syllable", "Ultimate and penultimate stress"),
    ("syllable_division", "division", "Syllable Division", "syllable", "How to divide words into syllables"),
]

# ── Level 4: Roots & Words ──

LEVEL4 = [
    ("root_concept", "root", "Triconsonantal Roots", "word", "3-consonant core of Hebrew words"),
    ("root_extraction", "extract", "Root Extraction", "word", "Identifying the 3 root letters"),
    ("noun_pattern_qatl", "qatl", "Qatl Pattern", "word", "Noun pattern: C-a-C-e-C"),
    ("noun_pattern_qitl", "qitl", "Qitl Pattern", "word", "Noun pattern: C-i-C-e-C"),
    ("noun_pattern_qutl", "qutl", "Qutl Pattern", "word", "Noun pattern: C-u-C-e-C"),
    ("prefix_bet", "ב", "Prefix Bet", "word", "Inseparable preposition: in/with/by"),
    ("prefix_kaf", "כ", "Prefix Kaf", "word", "Inseparable preposition: as/like"),
    ("prefix_lamed", "ל", "Prefix Lamed", "word", "Inseparable preposition: to/for"),
    ("prefix_mem", "מ", "Prefix Mem", "word", "Inseparable preposition: from"),
    ("prefix_vav", "ו", "Prefix Vav", "word", "Conjunctive vav: and"),
    ("prefix_he", "ה", "Prefix He", "word", "Definite article: the"),
    ("prefix_shin", "ש", "Prefix Shin", "word", "Relative particle: that/which"),
    ("suffix_plural_m", "ים", "Masculine Plural", "word", "Plural suffix: ־ים"),
    ("suffix_plural_f", "ות", "Feminine Plural", "word", "Plural suffix: ־ות"),
    ("suffix_pron_1s", "י", "1s Pronominal Suffix", "word", "My: ־י"),
    ("suffix_pron_2ms", "ך", "2ms Pronominal Suffix", "word", "Your (m.): ־ךָ"),
    ("suffix_pron_3ms", "ו", "3ms Pronominal Suffix", "word", "His: וֹ/־יו"),
    ("suffix_pron_1p", "נו", "1p Pronominal Suffix", "word", "Our: ־נוּ"),
]

# ── Level 5: Verbs (Binyanim) ──

LEVEL5 = [
    ("binyan_intro", "binyan", "Introduction to Binyanim", "verb", "Verb conjugation patterns"),
    ("qal_perfect", "qal_pf", "Qal Perfect", "verb", "Qal stem, perfect aspect"),
    ("qal_imperfect", "qal_ipf", "Qal Imperfect", "verb", "Qal stem, imperfect aspect"),
    ("qal_imperative", "qal_imp", "Qal Imperative", "verb", "Qal stem, commands"),
    ("qal_infinitive", "qal_inf", "Qal Infinitive", "verb", "Qal stem, infinitive construct"),
    ("qal_participle", "qal_ptc", "Qal Participle", "verb", "Qal stem, active participle"),
    ("niphal", "niphal", "Niphal", "verb", "Passive/reflexive of Qal"),
    ("piel", "piel", "Piel", "verb", "Intensive active"),
    ("pual", "pual", "Pual", "verb", "Intensive passive"),
    ("hiphil", "hiphil", "Hiphil", "verb", "Causative active"),
    ("hophal", "hophal", "Hophal", "verb", "Causative passive"),
    ("hithpael", "hithpael", "Hithpael", "verb", "Reflexive/intensive"),
    ("weak_guttural", "weak_gutt", "Weak Verbs: I-Guttural", "verb", "Guttural assimilation in verbs"),
    ("weak_nun", "weak_nun", "Weak Verbs: I-Nun", "verb", "Nun dropping in verbs"),
    ("weak_he", "weak_he", "Weak Verbs: III-He", "verb", "He dropping in verbs"),
    ("weak_hollow", "weak_hollow", "Weak Verbs: II-Vav/Yod", "verb", "Hollow verb patterns"),
    ("weak_double", "weak_double", "Weak Verbs: Double Ayin", "verb", "Geminate verb patterns"),
]

# ── Level 6: Nouns, Particles, Syntax ──

LEVEL6 = [
    ("noun_gender", "gender", "Noun Gender", "noun", "Masculine and feminine nouns"),
    ("noun_number", "number", "Noun Number", "noun", "Singular, plural, dual"),
    ("noun_state", "state", "Noun State", "noun", "Absolute vs construct state"),
    ("construct_chain", "construct", "Construct Chain", "noun", "Multiple nouns in sequence"),
    ("definite_article", "def_art", "Definite Article", "noun", "Ha- prefix and vowel changes"),
    ("vav_consecutive", "vav_cons", "Vav-Consecutive", "syntax", "Conversive vav in narrative"),
    ("word_order", "word_order", "Word Order", "syntax", "VSO default, fronting for emphasis"),
    ("direct_object", "do", "Direct Object Marker", "syntax", "את and its uses"),
    ("relative_clause", "relative", "Relative Clause", "syntax", "אֲשֶׁר clauses"),
    ("preposition_independent", "prep_ind", "Independent Prepositions", "noun", "Stand-alone prepositions"),
]

# ── Level 7: Reading ──

LEVEL7 = [
    ("reading_genesis", "gen", "Reading Genesis", "reading", "Parsing narrative prose"),
    ("reading_psalms", "psa", "Reading Psalms", "reading", "Hebrew poetry and parallelism"),
    ("reading_isaiah", "isa", "Reading Isaiah", "reading", "Prophetic literature"),
    ("reading_torah", "torah", "Reading Torah", "reading", "Legal and narrative formulas"),
    ("reading_connections", "conn", "Textual Connections", "reading", "Cross-references via FIRe graph"),
]

# ── All levels ──

ALL_NODES = LEVEL1 + LEVEL2 + LEVEL3 + LEVEL4 + LEVEL5 + LEVEL6 + LEVEL7

# ── Edge Definitions ──
# Each edge: (source, target, edge_type, weight)
# source = advanced concept, target = simpler concept it depends on

def build_edges():
    """Build prerequisite and encompassing edges between nodes."""
    edges = []

    # Level 1 → Level 1: Final form dependencies
    final_forms = [("kaf", "kaf_final"), ("mem", "mem_final"), ("nun", "nun_final"),
                   ("pe", "pe_final"), ("tsade", "tsade_final")]
    for base, final in final_forms:
        edges.append((final, base, "prerequisite", 1.0))

    # Shin/Sin depend on letter recognition
    edges.append(("shin", "aleph", "prerequisite", 0.3))
    edges.append(("sin", "shin", "prerequisite", 0.5))

    # Level 2 depends on Level 1
    for node in LEVEL2:
        nid = node[0]
        edges.append((nid, "aleph", "prerequisite", 0.4))  # general letter knowledge
        if "sheva" in nid:
            edges.append((nid, "aleph", "encompassing", 0.3))

    # Vowel relationships
    edges.append(("vowel_qamats", "vowel_patah", "prerequisite", 0.6))
    edges.append(("vowel_qamats_qatan", "vowel_qamats", "prerequisite", 0.5))
    edges.append(("vowel_hiriq_yod", "vowel_hiriq", "prerequisite", 0.6))
    edges.append(("vowel_tsere_yod", "vowel_tsere", "prerequisite", 0.6))
    edges.append(("vowel_holam_vav", "vowel_holam", "prerequisite", 0.6))
    edges.append(("vowel_sheva_na", "vowel_sheva", "prerequisite", 0.5))
    edges.append(("vowel_sheva_nah", "vowel_sheva", "prerequisite", 0.5))
    edges.append(("vowel_hataf_patah", "vowel_patah", "prerequisite", 0.7))
    edges.append(("vowel_hataf_qamats", "vowel_qamats", "prerequisite", 0.7))
    edges.append(("vowel_hataf_segol", "vowel_segol", "prerequisite", 0.7))

    # Level 3 depends on Level 1+2
    for node in LEVEL3:
        nid = node[0]
        edges.append((nid, "aleph", "prerequisite", 0.3))
        edges.append((nid, "vowel_patah", "prerequisite", 0.2))

    edges.append(("syllable_open", "syllable_basics", "prerequisite", 0.8))
    edges.append(("syllable_closed", "syllable_basics", "prerequisite", 0.8))
    edges.append(("syllable_stress", "syllable_open", "prerequisite", 0.5))
    edges.append(("syllable_division", "syllable_basics", "prerequisite", 0.6))
    edges.append(("syllable_division", "syllable_stress", "prerequisite", 0.4))

    # Level 4 depends on Level 1+2+3
    for node in LEVEL4:
        nid = node[0]
        edges.append((nid, "aleph", "prerequisite", 0.2))
        edges.append((nid, "syllable_basics", "prerequisite", 0.3))

    edges.append(("root_extraction", "root_concept", "prerequisite", 0.8))
    for pat in ["noun_pattern_qatl", "noun_pattern_qitl", "noun_pattern_qutl"]:
        edges.append((pat, "root_concept", "prerequisite", 0.5))

    # Prefix/suffix chains
    prefixes = ["prefix_bet", "prefix_kaf", "prefix_lamed", "prefix_mem",
                "prefix_vav", "prefix_he", "prefix_shin"]
    for p in prefixes:
        edges.append((p, "syllable_division", "prerequisite", 0.3))
    suffixes = ["suffix_plural_m", "suffix_plural_f", "suffix_pron_1s",
                "suffix_pron_2ms", "suffix_pron_3ms", "suffix_pron_1p"]
    for s in suffixes:
        edges.append((s, "noun_pattern_qatl", "prerequisite", 0.3))

    # Level 5 depends on Level 1-4
    for node in LEVEL5:
        nid = node[0]
        edges.append((nid, "root_concept", "prerequisite", 0.4))

    edges.append(("qal_imperfect", "qal_perfect", "prerequisite", 0.6))
    edges.append(("qal_imperative", "qal_imperfect", "prerequisite", 0.5))
    edges.append(("qal_infinitive", "qal_imperfect", "prerequisite", 0.4))
    edges.append(("qal_participle", "qal_imperfect", "prerequisite", 0.4))
    for binyan in ["niphal", "piel", "pual", "hiphil", "hophal", "hithpael"]:
        edges.append((binyan, "qal_perfect", "prerequisite", 0.5))
        edges.append((binyan, "qal_imperfect", "prerequisite", 0.3))
    for weak in ["weak_guttural", "weak_nun", "weak_he", "weak_hollow", "weak_double"]:
        edges.append((weak, "qal_perfect", "prerequisite", 0.4))

    # Level 6 depends on Level 4+5
    for node in LEVEL6:
        nid = node[0]
        edges.append((nid, "noun_pattern_qatl", "prerequisite", 0.3))
    edges.append(("noun_number", "noun_gender", "prerequisite", 0.6))
    edges.append(("noun_state", "noun_number", "prerequisite", 0.5))
    edges.append(("construct_chain", "noun_state", "prerequisite", 0.7))
    edges.append(("definite_article", "noun_state", "prerequisite", 0.4))
    edges.append(("vav_consecutive", "qal_imperfect", "prerequisite", 0.6))
    edges.append(("word_order", "vav_consecutive", "prerequisite", 0.4))
    edges.append(("direct_object", "word_order", "prerequisite", 0.3))
    edges.append(("relative_clause", "word_order", "prerequisite", 0.3))

    # Level 7 depends on all previous levels
    for node in LEVEL7:
        nid = node[0]
        edges.append((nid, "qal_perfect", "prerequisite", 0.3))
        edges.append((nid, "word_order", "prerequisite", 0.3))
        edges.append((nid, "syllable_basics", "encompassing", 0.2))

    return edges


def build_graph(db_path="data/memorize.db"):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    # Insert nodes
    cur = conn.cursor()
    cur.execute("DELETE FROM hebrew_nodes")
    cur.execute("DELETE FROM hebrew_edges")

    for nid, glyph, title, category, desc in ALL_NODES:
        level = 1
        if nid.startswith("vowel_"):
            level = 2
        elif nid.startswith("syllable_"):
            level = 3
        elif nid.startswith(("root_", "noun_pattern_", "prefix_", "suffix_")):
            level = 4
        elif nid in ("qal_perfect", "qal_imperfect", "qal_imperative",
                      "qal_infinitive", "qal_participle", "niphal", "piel",
                      "pual", "hiphil", "hophal", "hithpael",
                      "weak_guttural", "weak_nun", "weak_he", "weak_hollow",
                      "weak_double", "binyan_intro"):
            level = 5
        elif nid in ("noun_gender", "noun_number", "noun_state",
                      "construct_chain", "definite_article",
                      "vav_consecutive", "word_order", "direct_object",
                      "relative_clause", "preposition_independent"):
            level = 6
        elif nid.startswith("reading_"):
            level = 7

        cur.execute(
            "INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, ?, ?)",
            (nid, f"{title} ({glyph})", level, category, desc),
        )

    # Insert edges
    edges = build_edges()
    for src, tgt, etype, weight in edges:
        cur.execute(
            "INSERT OR IGNORE INTO hebrew_edges (source_id, target_id, edge_type, weight) VALUES (?, ?, ?, ?)",
            (src, tgt, etype, weight),
        )

    conn.commit()

    # Stats
    nodes = cur.execute("SELECT COUNT(*) FROM hebrew_nodes").fetchone()[0]
    edge_count = cur.execute("SELECT COUNT(*) FROM hebrew_edges").fetchone()[0]
    levels = cur.execute("SELECT level, COUNT(*) FROM hebrew_nodes GROUP BY level ORDER BY level").fetchall()

    conn.close()

    print("Hebrew knowledge graph built:")
    print(f"  Nodes: {nodes}")
    print(f"  Edges: {edge_count}")
    for lvl, cnt in levels:
        print(f"  Level {lvl}: {cnt} topics")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/memorize.db")
    args = parser.parse_args()
    build_graph(args.db)
