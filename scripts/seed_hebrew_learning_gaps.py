#!/usr/bin/env python3
"""Seed Hebrew learning gaps closed by expert + learning-flow audits.

Adds (idempotent, INSERT-or-update):
  1. `transliteration_guide` (L2) — the pronunciation-guide system lesson
     the expert audit flagged as missing (why katav = kātav, macron =
     long vowel, shewa-mobile apostrophe, etc).
  2. `wayyiqtol_recognition` (L3) — early narrative recognition: see
     wayyiqtol, know "past narrative, move on", no conjugation required.
     Unlocks BEFORE qal_perfect (L5) so Gen 1 wayyiqtols are readable early.
  3. Discourse-aspect judgment items (expert gap #2) on qal_perfect,
     qal_imperfect, vav_consecutive, weqatal_discourse — "this qatal is
     past / present / gnomic: why?" using existing `classification` type
     so the KP recognition stage + grading paths work unchanged.
  4. Syntax-to-reading bridge items (expert gap #4) on read_gen1 + read_exo3
     using existing `parse` / `classification` types: find the verb / head
     noun of a real verse from 4 verse words.
  5. Divine-title context cards (expert gap #3) for elohim/YHWH-type words:
     one `recall` item each rotating the non-default gloss, so learners
     cannot pass by always answering "army"/"god".

All practice rows reuse existing question_types only
(multiple_choice / true_false / classification / transliteration / recall /
parse / cloze) — no backend allowlist or KP-stage changes needed:
  recognition = multiple_choice / true_false / classification
  recall      = cloze / transliteration / contrast / recall / parse / dictation
  production  = typing / sentence

Usage: scripts/seed_hebrew_learning_gaps.py [--db data/memorize.db]
"""
import argparse
import json
import sqlite3
from pathlib import Path

SOURCES = [
    {"id": "expert-audit-2026", "label": "Hebrew expert evaluation + learning review (repo docs)"},
    {"id": "oshb", "label": "Open Scriptures Hebrew Bible (public domain morphology context)"},
]

LESSONS = [
    {
        "id": "transliteration_guide",
        "title": "How to Read the Pronunciation Guides",
        "category": "vowel",
        "level": 2,
        "description": "Learn the transliteration scheme: what macrons, apostrophes, and hats mean",
        "prerequisites": ["vowel_qamats", "vowel_patah"],
        "explanation": (
            "Every lesson shows a pronunciation hint like kātav. That hint follows one consistent scheme: "
            "a macron (ā ē ī ō ū) marks a LONG vowel, no mark is short; ’ marks a mobile shewa or aleph-stop "
            "(b’reshit = b + moving-shewa + reshit); ḥ/ṣ/ṭ mark emphatic consonants (chet, tsade, tet); "
            "q marks qof (ḳ/q) distinct from kaf (k); w vs v follows the consonant (vav as v, shuruq as u). "
            "Stress is marked with an accent on the vowel (kātā́v). Learn this once and every hint becomes readable."
        ),
        "key_points": [
            "Macron = long vowel (ā ē ī ō ū); plain letter = short",
            "’ = mobile shewa or glottal catch (never silent filler)",
            "ḥ ṣ ṭ q = emphatics + qof, distinct from h/s/t/k",
            "Accent mark shows stressed syllable",
        ],
        "verse_examples": [],
        "practice": [
            ("multiple_choice", "In kātav, what does the macron over ā tell you?",
             ["The vowel is long", "The vowel is silent", "The consonant is doubled", "The syllable is stressed"], "The vowel is long"),
            ("multiple_choice", "In b’reshit, what does ’ stand for?",
             ["A mobile shewa / glottal break", "A silent letter to ignore", "A long vowel", "A doubled consonant"], "A mobile shewa / glottal break"),
            ("transliteration", "How is כָּתַב transliterated? (hint: long first vowel)", None, "kātav"),
            ("multiple_choice", "Which pair does the scheme keep distinct?",
             ["kaf (k) vs qof (q)", "bet vs vet", "sin vs samekh"], "kaf (k) vs qof (q)"),
            ("true_false", "True or false: plain 'a' (no macron) is a short vowel in this scheme.",
             ["True", "False"], "True"),
        ],
    },
    {
        "id": "wayyiqtol_recognition",
        "title": "Wayyiqtol Recognition: Narrative Past",
        "category": "verb",
        "level": 3,
        "description": "Recognize wayyiqtol narrative forms (vayyomer) as past — no conjugation yet",
        "prerequisites": ["vav", "syllable_basics"],
        "explanation": (
            "Open Genesis 1 and you meet וַיֹּאמֶר (vayyomer, 'and he said') on page one — long before the verb lessons at L5. "
            "You do NOT need to conjugate it yet. Recognition rule: vav + doubling + imperfect-looking verb at the start of a "
            "narrative clause = wayyiqtol = past-tense storyline event ('and he said / and he went / and God saw'). "
            "When you see it, translate past and move on; full conjugation comes in the Qal Imperfect + vav-consecutive lessons."
        ),
        "key_points": [
            "Wayyiqtol = vav + doubling + imperfect base",
            "Function: past narrative storyline ('and he said')",
            "Recognition only — no parsing of person/gender/number yet",
            "Full conjugation taught at L5–L6 (qal_imperfect, vav_consecutive)",
        ],
        "verse_examples": [
            {"verse_ref": "gen.1.3", "hebrew": "וַיֹּאמֶר אֱלֹהִים יְהִי אוֹר", "note": "Wayyiqtol opens creation speech: 'and God said'."},
        ],
        "practice": [
            ("multiple_choice", "וַיֹּאמֶר (vayyomer) in Genesis 1:3 is a wayyiqtol. How do you handle it?",
             ["Translate past narrative ('and he said') and move on", "Parse full conjugation now", "Treat as present tense", "Treat as a noun"], "Translate past narrative ('and he said') and move on"),
            ("true_false", "True or false: wayyiqtol (e.g. וַיֹּאמֶר) normally advances past-tense narrative.",
             ["True", "False"], "True"),
            ("multiple_choice", "What marks וַיֹּאמֶר as a wayyiqtol?",
             ["Vav + doubling of the prefix consonant", "A final he", "A maqqef", "A qamats qatan"], "Vav + doubling of the prefix consonant"),
            ("classification", "וַיַּרְא (vayyar, 'and he saw', Gen 1:4) — narrative or instruction?",
             ["Narrative past", "Instruction / command", "Question", "Name"], "Narrative past"),
            ("multiple_choice", "Do you need to state person/gender/number for a wayyiqtol at this stage?",
             ["No — recognition (past narrative) is enough", "Yes — full parse required"], "No — recognition (past narrative) is enough"),
        ],
    },
]

# (node_id, question_type, question_text, options, correct_answer, explanation)
EXTRA_ITEMS = [
    # --- Discourse-aspect judgments (expert gap #2): use classification so the
    # KP recognition stage + choice grading accept them unchanged.
    ("qal_perfect", "classification",
     "בָּרָא אֱלֹהִים (Gen 1:1, qatal) — past, present, or gnomic? Why?",
     ["Past — completed event in narrative", "Present — ongoing action", "Gnomic — timeless truth"],
     "Past — completed event in narrative",
     "Qatal presents the event as complete; narrative context fixes past reference (aspect-over-tense)."),
    ("qal_perfect", "classification",
     "יָדַעְתִּי (1cs qatal) in a wisdom saying ('I know ...') — most likely?",
     ["Present state from completed experience", "Future event", "Command"],
     "Present state from completed experience",
     "Qatal of stative/cognitive verbs often yields present state; gloss by discourse, not morphology alone."),
    ("qal_imperfect", "classification",
     "יֹאמַר (yiqtol) in direct speech ('he says / will say') — what decides the time?",
     ["Discourse context and genre, not the prefix alone", "The prefix always means future", "The suffix always means past"],
     "Discourse context and genre, not the prefix alone",
     "Yiqtol is non-complete; narrative vs speech vs instruction fixes its time reference."),
    ("vav_consecutive", "classification",
     "וַיֹּאמֶר vs וְאָמַר — which advances past narrative?",
     ["וַיֹּאמֶר (wayyiqtol)", "וְאָמַר (weqatal)", "Both equally"],
     "וַיֹּאמֶר (wayyiqtol)",
     "Wayyiqtol chains the past storyline; weqatal projects instruction/sequence (weqatal_discourse)."),
    ("weqatal_discourse", "classification",
     "וְשָׁמַרְתָּ in a law code ('and you shall keep') — narrative past or projected instruction?",
     ["Projected instruction / sequence", "Past narrative event", "Question"],
     "Projected instruction / sequence",
     "Weqatal in legal/instructional genre projects the next step, not past time."),
    # --- Syntax-to-reading bridge (expert gap #4): parse/classification on
    # real verses — choose the verb / head noun from 4 verse words.
    ("read_gen1", "parse",
     "Gen 1:1 בְּרֵאשִׁית בָּרָא אֱלֹהִים — which word is the finite verb?",
     ["בָּרָא", "בְּרֵאשִׁית", "אֱלֹהִים", "אֵת"],
     "בָּרָא",
     "בָּרָא (3ms qatal) is the predicate; בְּרֵאשִׁית is a temporal adjunct, אֱלֹהִים the subject."),
    ("read_gen1", "classification",
     "Gen 1:1 אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ — what is אֵת marking?",
     ["Definite direct object", "The verb", "A preposition 'with'", "A pronoun"],
     "Definite direct object",
     "אֵת + definite noun marks the object; the head nouns are שָׁמַיִם / אָרֶץ."),
    ("read_exo3", "parse",
     "Exo 3:14 אֶהְיֶה אֲשֶׁר אֶהְיֶה — which word is the verb (and repeated)?",
     ["אֶהְיֶה", "אֲשֶׁר", "עַם", "הָר"],
     "אֶהְיֶה",
     "אֶהְיֶה (1cs yiqtol of היה) is the predicate; אֲשֶׁר is the relative marker."),
    # --- Theologically loaded gloss rotation (expert gap #3): force the
    # non-default gloss so one answer cannot pass every card.
    ("vocab_אלהי_11", "recall",
     "אֱלֹהִים in Gen 1:1 as divine title — which gloss fits THIS context?",
     None, "God",
     "Elohim spans gods/God/divine beings; the Gen 1:1 title reads God."),
    ("vocab_אלהי_11", "classification",
     "אֱלֹהִים with plural morphology but singular verb (Gen 1:1 בָּרָא) — what does agreement tell you?",
     ["Divine title with singular reference", "Many gods acting", "A verb form", "A place name"],
     "Divine title with singular reference",
     "Morphology is plural-shaped; singular-verb agreement marks the singular divine title."),
    ("vocab_צבאו_102", "recall",
     "צְבָאוֹת in the divine title יְהוָה צְבָאוֹת — which gloss fits THIS context?",
     None, "hosts",
     "Tsava spans army/host/warfare; the divine title reads LORD of hosts."),
    ("vocab_קדוש_295", "recall",
     "קָדוֹשׁ for God himself (qadosh = holy One) — which gloss fits THIS context?",
     None, "Holy One",
     "Qadosh spans holy/sacred/set apart; predicated of God it reads the Holy One."),
]

# Fallback word-node ids if the exact above ids are absent (never fail the seed).
GLOSS_FALLBACKS = {
    "word_elohim": ("elohim", "אֱלֹהִים as divine title (Gen 1:1) — which gloss fits THIS context?"),
    "word_qodesh": ("qodesh", "קֹדֶשׁ in a holiness context — which gloss?"),
}


def seed(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_hebrew_practice_unique
                    ON hebrew_practice_items(node_id,question_type,question_text,correct_answer)""")
    count = 0
    for lesson in LESSONS:
        node_id = lesson["id"]
        conn.execute(
            """INSERT INTO hebrew_nodes (id,title,level,category,description) VALUES (?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title,level=excluded.level,
               category=excluded.category,description=excluded.description""",
            (node_id, lesson["title"], lesson["level"], lesson["category"], lesson["description"]),
        )
        content = {k: v for k, v in lesson.items() if k not in {"id", "practice", "prerequisites"}}
        content.update({"node_id": node_id, "sources": SOURCES,
                        "source_ids": [s["id"] for s in SOURCES]})
        conn.execute(
            """INSERT INTO hebrew_lessons (node_id,content_json) VALUES (?,?)
               ON CONFLICT(node_id) DO UPDATE SET content_json=excluded.content_json,
               version=hebrew_lessons.version+1,updated_at=datetime('now')
               WHERE hebrew_lessons.content_json<>excluded.content_json""",
            (node_id, json.dumps(content, ensure_ascii=False)),
        )
        conn.executemany(
            """INSERT OR IGNORE INTO hebrew_practice_items
               (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation)
               VALUES (?,?,?,?,?,0.5,'')""",
            [(node_id, qtype, q, json.dumps(o, ensure_ascii=False) if o else None, a)
             for qtype, q, o, a in lesson["practice"]],
        )
        count += len(lesson["practice"])
        conn.execute("DELETE FROM hebrew_edges WHERE target_id=? AND edge_type='prerequisite'", (node_id,))
        for pre in lesson["prerequisites"]:
            if conn.execute("SELECT 1 FROM hebrew_nodes WHERE id=?", (pre,)).fetchone():
                conn.execute(
                    "INSERT INTO hebrew_edges (source_id,target_id,edge_type) VALUES (?,?,'prerequisite')",
                    (pre, node_id),
                )
        for ex in lesson.get("verse_examples", []):
            if ex.get("verse_ref"):
                conn.execute("""
                    INSERT INTO hebrew_attestations
                        (node_id,verse_id,attestation_type,explanation,difficulty)
                    VALUES (?,?,'reading_example',?,'beginner')
                    ON CONFLICT(node_id,verse_id) DO UPDATE SET
                        attestation_type='reading_example',explanation=excluded.explanation
                """, (node_id, ex["verse_ref"], ex.get("note", "")))
    for node_id, qtype, qtext, options, answer, expl in EXTRA_ITEMS:
        target = node_id
        if not conn.execute("SELECT 1 FROM hebrew_nodes WHERE id=?", (target,)).fetchone():
            if node_id in GLOSS_FALLBACKS:
                fb_id, fb_q = GLOSS_FALLBACKS[node_id]
                if conn.execute("SELECT 1 FROM hebrew_nodes WHERE id=?", (fb_id,)).fetchone():
                    target, qtext = fb_id, fb_q
                else:
                    continue
            else:
                continue
        conn.execute(
            """INSERT OR IGNORE INTO hebrew_practice_items
               (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation)
               VALUES (?,?,?,?,?,0.55,?)""",
            (target, qtype, qtext,
             json.dumps(options, ensure_ascii=False) if options else None,
             answer, expl),
        )
        count += 1
    migrate_to_first_class_types(conn)
    count += seed_phase2(conn)
    conn.commit()
    conn.close()
    print(f"Seeded learning-gap content: 2 lessons + extras ({count} practice rows touched)")
    return count


# --- Phase 2: first-class discourse_function / syntax_parse types ---
# The phase-1 seed used `classification`/`parse` so nothing broke before the
# type promotion shipped. Now that the backend KP map, choice sets, and the
# frontend grade the new types, promote the existing rows to them.
MIGRATE_TYPES = [
    ("qal_perfect", "classification", "discourse_function",
     "בָּרָא אֱלֹהִים (Gen 1:1, qatal)%"),
    ("qal_perfect", "classification", "discourse_function",
     "יָדַעְתִּי (1cs qatal)%"),
    ("qal_imperfect", "classification", "discourse_function",
     "יֹאמַר (yiqtol) in direct speech%"),
    ("vav_consecutive", "classification", "discourse_function",
     "וַיֹּאמֶר vs וְאָמַר%"),
    ("weqatal_discourse", "classification", "discourse_function",
     "וְשָׁמַרְתָּ in a law code%"),
    ("read_gen1", "parse", "syntax_parse",
     "Gen 1:1 בְּרֵאשִׁית בָּרָא אֱלֹהִים%"),
    ("read_gen1", "classification", "syntax_parse",
     "Gen 1:1 אֵת הַשָּׁמַיִם%"),
    ("read_exo3", "parse", "syntax_parse",
     "Exo 3:14 אֶהְיֶה אֲשֶׁר אֶהְיֶה%"),
]


def migrate_to_first_class_types(conn) -> None:
    for node_id, old, new, like in MIGRATE_TYPES:
        conn.execute(
            "UPDATE hebrew_practice_items SET question_type=? "
            "WHERE node_id=? AND question_type=? AND question_text LIKE ?",
            (new, node_id, old, like),
        )


# (node_id, question_type, question_text, options, correct_answer, explanation)
PHASE2_ITEMS = [
    # --- Weak verbs: top up thin high-frequency classes (expert gap #1) ---
    ("weak_hollow", "classification",
     "קָם (qatal) shows no middle radical; יָקוּם (yiqtol) shows vav. What class?",
     ["Hollow (II-Vav/Yod)", "Strong", "Geminate (Double Ayin)", "I-Guttural"],
     "Hollow (II-Vav/Yod)",
     "Hollow verbs hide II-vav/yod in qatal (קָם) and restore it in yiqtol (יָקוּם)."),
    ("weak_hollow", "recall", "Root of קָם / יָקוּם?", None, "קום",
     "QWM: the vav contracts in qatal, returns in yiqtol."),
    ("weak_hollow", "multiple_choice",
     "Why does קָם lack a visible middle letter?",
     ["The vav/yod contracts in qatal but returns in yiqtol", "The letter was never there",
      "A maqqef absorbed it", "Final-he rule"],
     "The vav/yod contracts in qatal but returns in yiqtol",
     "Hollow contraction is a qatal spelling fact, not a missing root letter."),
    ("weak_he", "recall", "Root of בָּנָה (he built)?", None, "בנה",
     "BNH: III-He roots end in ה that reshapes across conjugations."),
    ("weak_he", "classification",
     "יִבְנֶה (3ms yiqtol of בנה) — what happened to the final he?",
     ["It surfaces as a vowel letter (segol + ה)", "It doubles with dagesh",
      "It drops entirely", "It becomes ת"],
     "It surfaces as a vowel letter (segol + ה)",
     "III-He yiqtol ends in a vocalic syllable; the he is a mater, not a consonant."),
    ("weak_he", "multiple_choice",
     "Which marks בָּנָה as III-He (ל״ה)?",
     ["Final ה that reshapes across conjugations", "Initial nun that assimilates",
      "Doubled middle letter", "Prefixed vav"],
     "Final ה that reshapes across conjugations",
     "The ל״ה slot is the diagnostic: compare qatal בָּנָה with yiqtol יִבְנֶה."),
    ("weak_guttural", "classification",
     "יַעֲמֹד (yaʿămōd, from עמד) — why patah + hataf under the prefix?",
     ["Guttural ע prefers a-class vowels", "It is a hollow verb", "It is geminate", "Final-he rule"],
     "Guttural ע prefers a-class vowels",
     "I-guttural prefixes lower to patah/hataf-patah before ע/ח/ה/א."),
    ("weak_guttural", "recall", "Root of עָמַד (he stood)?", None, "עמד",
     "ʿMD: I-ayin guttural; watch the prefix vowels in yiqtol."),
    ("weak_nun", "classification",
     "יִפֹּל (3ms yiqtol of נפל, 'he will fall') — where is the nun?",
     ["Assimilated into the doubled פ (dagesh forte)", "Written with a maqqef",
      "Changed to ה", "Still written as נ"],
     "Assimilated into the doubled פ (dagesh forte)",
     "I-nun assimilates to the next consonant; the dagesh is its footprint."),
    ("weak_nun", "recall", "Root of יִפֹּל?", None, "נפל",
     "NFL: the missing nun is hiding in the dagesh of פ."),
    # --- Syntax-to-reading bridge: 8 more narrative nodes (10 total) ---
    ("read_exo14", "syntax_parse",
     "Exo 14:14 יְהוָה יִלָּחֵם לָכֶם — which word is the finite verb?",
     ["יִלָּחֵם", "יְהוָה", "לָכֶם", "אֵת"],
     "יִלָּחֵם",
     "יִלָּחֵם (3ms niphal yiqtol) is the predicate; יְהוָה is the subject."),
    ("read_gen22", "syntax_parse",
     "Gen 22:8 אֱלֹהִים יִרְאֶה־לּוֹ הַשֶּׂה — which word is the finite verb?",
     ["יִרְאֶה", "אֱלֹהִים", "הַשֶּׂה", "לּוֹ"],
     "יִרְאֶה",
     "יִרְאֶה (3ms qal yiqtol) is the predicate; maqqef joins it to לּוֹ."),
    ("read_deut6", "syntax_parse",
     "Deut 6:4 שְׁמַע יִשְׂרָאֵל — what kind of clause is this?",
     ["Imperative address (command to listen)", "Past narrative", "Question", "Relative clause"],
     "Imperative address (command to listen)",
     "שְׁמַע is an imperative; the Shema opens with direct address."),
    ("read_josh4", "syntax_parse",
     "Josh 4:24 אֶת־יַד יְהוָה — what is אֶת marking here?",
     ["Definite direct object (יַד is the head noun)", "The verb", "A preposition 'with'", "A pronoun"],
     "Definite direct object (יַד is the head noun)",
     "אֶת + definite noun marks the object; construct יַד־יְהוָה is the phrase."),
    ("read_1sam1", "syntax_parse",
     "1 Sam 1:27 אֶל־הַנַּעַר הַזֶּה הִתְפַּלָּלְתִּי — which word is the finite verb?",
     ["הִתְפַּלָּלְתִּי", "הַנַּעַר", "הַזֶּה", "אֶל"],
     "הִתְפַּלָּלְתִּי",
     "הִתְפַּלָּלְתִּי (1cs hithpael) is the predicate; the rest is a prepositional phrase."),
    ("read_gen47", "syntax_parse",
     "Gen 47:7 וַיְבָרֶךְ יַעֲקֹב אֶת־פַּרְעֹה — which word is the wayyiqtol?",
     ["וַיְבָרֶךְ", "יַעֲקֹב", "פַּרְעֹה", "אֶת"],
     "וַיְבָרֶךְ",
     "וַיְבָרֶךְ advances the past storyline — the L3 recognition rule in the wild."),
    ("read_exo19", "syntax_parse",
     "Exo 19:5 אִם־שָׁמוֹעַ תִּשְׁמְעוּ בְּקֹלִי — which word is the finite verb?",
     ["תִּשְׁמְעוּ", "שָׁמוֹעַ", "בְּקֹלִי", "אִם"],
     "תִּשְׁמְעוּ",
     "תִּשְׁמְעוּ (2mp yiqtol) is finite; שָׁמוֹעַ (infinitive absolute) intensifies it."),
    ("read_gen12", "syntax_parse",
     "Gen 12:1 לֶךְ־לְךָ מֵאַרְצְךָ — what kind of clause is this?",
     ["Imperative address (command to go)", "Past narrative", "Blessing formula", "Genealogy"],
     "Imperative address (command to go)",
     "לֶךְ is an imperative; the call of Abram opens with a command."),
]


def seed_phase2(conn) -> int:
    n = 0
    for node_id, qtype, qtext, options, answer, expl in PHASE2_ITEMS:
        if not conn.execute("SELECT 1 FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone():
            continue
        conn.execute(
            """INSERT OR IGNORE INTO hebrew_practice_items
               (node_id,question_type,question_text,options_json,correct_answer,difficulty,explanation)
               VALUES (?,?,?,?,?,0.55,?)""",
            (node_id, qtype, qtext,
             json.dumps(options, ensure_ascii=False) if options else None,
             answer, expl),
        )
        n += 1
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, default=Path("data/memorize.db"))
    args = ap.parse_args()
    seed(args.db)
