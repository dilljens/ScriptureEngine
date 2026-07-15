#!/usr/bin/env python3
"""Add production practice items to Hebrew teaching system.

Generates production items (typing, free recall, parsing, reverse translation)
for all Hebrew nodes, complementing the existing recognition items.

Production types added:
  - Reverse translation: English gloss → Hebrew word
  - Root extraction: from derived words  
  - Verb paradigm: root + binyan + stem → verb form
  - Parsing: word form → root + binyan + person/gender/number
  - Construct chain: "X of Y" → Hebrew construct form

Usage:
    python3 scripts/seed_hebrew_production.py
    python3 scripts/seed_hebrew_production.py --db data/memorize.db
"""

import argparse
import json
import sqlite3
import re
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"

# ── Root lesson data (mirrors seed_hebrew_roots.py for production items) ──

ROOTS = [
    ("כתב", "write", [("כָּתַב", "he wrote"), ("כְּתָב", "writing"), ("כְּתֹבֶת", "inscription"), ("סֵפֶר", "book/scroll")]),
    ("מלך", "king, rule", [("מֶלֶךְ", "king"), ("מַלְכָּה", "queen"), ("מַלְכוּת", "kingdom"), ("הִמְלִיךְ", "he made king")]),
    ("דבר", "speak, word", [("דָּבָר", "word/thing"), ("דִּבֵּר", "he spoke"), ("דְּבָרִים", "words/things"), ("דַּבָּר", "spokesman")]),
    ("שמר", "keep, guard", [("שָׁמַר", "he kept"), ("שְׁמָר", "guard"), ("שְׁמִירָה", "guarding"), ("מִשְׁמֶרֶת", "watch/guard duty")]),
    ("עבד", "serve, work", [("עָבַד", "he served/worked"), ("עֶבֶד", "servant/slave"), ("עֲבוֹדָה", "work/service"), ("עֲבֹדָה", "slavery")]),
    ("ברך", "bless", [("בָּרַךְ", "he blessed"), ("בְּרָכָה", "blessing"), ("בָּרוּךְ", "blessed"), ("בְּרֵכָה", "pool (blessing place)")]),
    ("אהב", "love", [("אָהַב", "he loved"), ("אַהֲבָה", "love"), ("אֶהֶב", "beloved")]),
    ("ירא", "fear, revere", [("יָרֵא", "he feared"), ("יִרְאָה", "fear"), ("יָרֵא", "God-fearing")]),
    ("עשׂה", "make, do", [("עָשָׂה", "he made/did"), ("מַעֲשֶׂה", "work/deed"), ("עוֹשֶׂה", "maker/doer")]),
    ("שלם", "peace, complete", [("שָׁלֵם", "whole/complete"), ("שָׁלוֹם", "peace"), ("שִׁלֵּם", "he repaid")]),
]

# ── Binyan patterns for verb paradigm questions ──

BINYAN_INFO = {
    "qal_perfect": {"name": "Qal Perfect", "example": "כָּתַב", "root": "כתב", "desc": "the simple active — 'he wrote'"},
    "qal_imperfect": {"name": "Qal Imperfect", "example": "יִכְתֹּב", "root": "כתב", "desc": "the simple active future — 'he will write'"},
    "niphal": {"name": "Niphal", "example": "נִכְתַּב", "root": "כתב", "desc": "the simple passive — 'it was written'"},
    "piel": {"name": "Piel", "example": "כִּתֵּב", "root": "כתב", "desc": "the intensive active — 'he engraved/inscribed'"},
    "pual": {"name": "Pual", "example": "כֻּתַּב", "root": "כתב", "desc": "the intensive passive — 'it was inscribed'"},
    "hiphil": {"name": "Hiphil", "example": "הִכְתִּיב", "root": "כתב", "desc": "the causative active — 'he caused to write/dictated'"},
    "hophal": {"name": "Hophal", "example": "הָכְתַּב", "root": "כתב", "desc": "the causative passive — 'it was caused to be written'"},
    "hithpael": {"name": "Hithpael", "example": "הִתְכַּתֵּב", "root": "כתב", "desc": "the reflexive — 'he corresponded'"},
}

# Common vocabulary words for construct chain production
CONSTRUCT_PAIRS = [
    ("בית", "house", "מלך", "king", "בֵּית מֶלֶךְ", "house of the king"),
    ("דבר", "word", "יהוה", "YHWH", "דְּבַר יְהוָה", "word of YHWH"),
    ("מלך", "king", "ישראל", "Israel", "מֶלֶךְ יִשְׂרָאֵל", "king of Israel"),
    ("בן", "son", "דוד", "David", "בֶּן דָּוִד", "son of David"),
    ("עיר", "city", "דוד", "David", "עִיר דָּוִד", "city of David"),
    ("בית", "house", "אלהים", "God", "בֵּית אֱלֹהִים", "house of God"),
    ("ארון", "ark", "ברית", "covenant", "אֲרוֹן הַבְּרִית", "ark of the covenant"),
    ("ארץ", "land", "ישראל", "Israel", "אֶרֶץ יִשְׂרָאֵל", "land of Israel"),
    ("בת", "daughter", "ציון", "Zion", "בַּת צִיּוֹן", "daughter of Zion"),
    ("עם", "people", "יהוה", "YHWH", "עַם יְהוָה", "people of YHWH"),
]


def add_item(cur, node_id, qtype, text, answer, difficulty, explanation="", options=""):
    """Add a production practice item with INSERT OR IGNORE."""
    opts = options if options else "[]"
    cur.execute("""INSERT OR IGNORE INTO hebrew_practice_items
        (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (node_id, qtype, text, opts, answer, difficulty, explanation))


def seed_production(mem_db):
    conn = sqlite3.connect(str(mem_db))
    cur = conn.cursor()
    added = 0

    nodes = cur.execute(
        "SELECT id, title, level, category, description FROM hebrew_nodes ORDER BY level, id"
    ).fetchall()

    for nid, title, level, category, desc in nodes:
        glyph = ""
        if "(" in title:
            glyph = title.split("(")[1].split(")")[0]
            clean = title.split("(")[0].strip()
        else:
            clean = title

        # ── Consonants: write from sound description ──
        if category == "consonant" and glyph:
            add_item(cur, nid, "typing",
                f"Type the Hebrew letter that makes the '{desc[:30].split(',')[0]}' sound",
                glyph, 0.6,
                f"The letter {clean} ({glyph}) makes the sound '{desc[:30].split(',')[0]}'")
            added += 1

        # ── Vowels: write from description ──
        if category == "vowel" and glyph:
            add_item(cur, nid, "typing",
                f"Type the vowel symbol that makes the '{desc[:40].split(',')[0]}' sound",
                glyph, 0.7,
                f"The vowel {clean} is written as {glyph}")

            # Reverse: given the glyph, name the vowel
            add_item(cur, nid, "recall",
                f"What is the name of the vowel {glyph}?",
                clean, 0.5,
                f"The vowel symbol {glyph} is called {clean}")
            added += 2

        # ── Verbs: paradigm production ──
        if category == "verb":
            binyan_info = BINYAN_INFO.get(nid)
            if binyan_info:
                root = binyan_info["root"]
                example = binyan_info["example"]
                desc_text = binyan_info["desc"]

                # Write the form from description
                add_item(cur, nid, "typing",
                    f"Write the {binyan_info['name']} of root {root} ({desc_text})",
                    example, 0.8,
                    f"The {binyan_info['name']} of {root} is {example}")
                added += 1

                # Recognition: identify the binyan from a form
                all_names = [info["name"] for _k, info in BINYAN_INFO.items()]
                wrong = [n for n in all_names if n != binyan_info["name"]][:3]
                opts = wrong + [binyan_info["name"]]
                add_item(cur, nid, "multiple_choice",
                    f"What binyan is {example} (root {root})?",
                    binyan_info["name"], 0.7,
                    f"{example} is the {binyan_info['name']} of root {root}",
                    options=json.dumps(opts))
                added += 1

                # For Qal: add person/gender/number paradigm questions
                if nid == "qal_perfect":
                    paradigm = [
                        ("3ms", "הוּא", "he wrote", "כָּתַב"),
                        ("3fs", "הִיא", "she wrote", "כָּתְבָה"),
                        ("2ms", "אַתָּה", "you (m.s.) wrote", "כָּתַבְתָּ"),
                        ("2fs", "אַתְּ", "you (f.s.) wrote", "כָּתַבְתְּ"),
                        ("1cs", "אֲנִי", "I wrote", "כָּתַבְתִּי"),
                        ("3mp", "הֵם", "they (m.) wrote", "כָּתְבוּ"),
                        ("3fp", "הֵן", "they (f.) wrote", "כָּתְבוּ"),
                        ("2mp", "אַתֶּם", "you (m.p.) wrote", "כְּתַבְתֶּם"),
                        ("2fp", "אַתֶּן", "you (f.p.) wrote", "כְּתַבְתֶּן"),
                        ("1cp", "אֲנַחְנוּ", "we wrote", "כָּתַבְנוּ"),
                    ]
                    for person, pronoun, meaning, form in paradigm:
                        add_item(cur, nid, "typing",
                            f"Qal perfect {person} ({pronoun} = {meaning}): write the verb",
                            form, 0.8,
                            f"Qal perfect {person} of root כתב is {form}")
                        added += 1

        # ── Vocabulary: reverse translation ──
        if category == "word" and nid.startswith("vocab_"):
            try:
                lesson_json = cur.execute(
                    "SELECT content_json FROM hebrew_lessons WHERE node_id=?",
                    (nid,)
                ).fetchone()[0]
                lesson = json.loads(lesson_json)
                gloss = lesson.get("gloss", "")
                hebrew = lesson.get("hebrew", "")
                if gloss and hebrew:
                    # Reverse translation: English → Hebrew
                    add_item(cur, nid, "typing",
                        f"What is the Hebrew word for '{gloss}'? (hint: root-related)",
                        hebrew, 0.6,
                        f"The Hebrew word for '{gloss}' is {hebrew}")
                    added += 1

                    # Given Hebrew + context, give English
                    if lesson.get("verse_example"):
                        verse_eng = lesson.get("verse_english", "")[:80]
                        add_item(cur, nid, "recall",
                            f"In the verse '{verse_eng}...', what does {hebrew} mean?",
                            gloss, 0.5,
                            f"In that context, {hebrew} means '{gloss}'")
                        added += 1
            except (IndexError, json.JSONDecodeError):
                pass

        # ── Root lessons: root extraction + derived words ──
        if category == "root":
            for root_letters, meaning, derived in ROOTS:
                root_id = f"root_{root_letters}"
                if nid == root_id:
                    # Extract root from a derived word
                    for word, gloss in derived:
                        add_item(cur, nid, "recall",
                            f"What's the root of {word} ('{gloss}')?",
                            root_letters, 0.7,
                            f"The root of {word} is {root_letters} (meaning: {meaning})")
                        added += 1

                    # Given root + pattern, produce the word
                    for word, gloss in derived:
                        add_item(cur, nid, "typing",
                            f"Write the Hebrew word derived from root {root_letters} that means '{gloss}'",
                            word, 0.8,
                            f"The word for '{gloss}' from root {root_letters} is {word}")
                        added += 1

    # ── Construct chain production (for noun_state nodes) ──
    for nid in ["construct_chain", "noun_state"]:
        for word1, gloss1, word2, gloss2, construct, meaning in CONSTRUCT_PAIRS:
            add_item(cur, nid, "typing",
                f"Write the construct chain: '{meaning}'",
                construct, 0.7,
                f"The construct form is {construct} (from {word1} ({gloss1}) + {word2} ({gloss2}))")
            added += 1

            add_item(cur, nid, "recall",
                f"Identify the construct state in: {construct}. Which word is in construct?",
                word1, 0.6,
                f"In {construct}, the first word {word1} is in the construct state")
            added += 1

    # ── Morphological parsing (using gematria data from scripture.db) ──
    try:
        scrip = sqlite3.connect(str(SCRIPTURE_DB))
        scrip.row_factory = sqlite3.Row

        # Find a few common verb forms with known morphology
        verb_forms = scrip.execute("""
            SELECT g.verse_id, g.word_hebrew, g.lemma, g.morph, g.word_english,
                   v.text_english
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            WHERE g.morph LIKE 'v%' 
              AND g.lemma IN ('H3068', 'H559', 'H1961')
              AND g.word_hebrew IS NOT NULL
            LIMIT 30
        """).fetchall()

        for vf in verb_forms:
            word = vf["word_hebrew"]
            morph = vf["morph"] or ""
            lemma = vf["lemma"] or ""
            # Add parsing: identify the verb form
            add_item(cur, "reading_torah", "recall",
                f"Parse this verb form: {word} (context: '{str(vf['text_english'] or '')[:60]}')",
                f"Lemma {lemma}", 0.9,
                f"The word {word} has Strong's {lemma} and morphology code {morph}")
            added += 1

        scrip.close()
    except Exception:
        pass  # scripture.db parsing is optional — don't fail if gematria not available

    conn.commit()
    conn.close()
    print(f"Added {added} production practice items")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add production practice items")
    parser.add_argument("--db", default=str(MEM_DB))
    args = parser.parse_args()
    seed_production(args.db)
