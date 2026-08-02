#!/usr/bin/env python3
"""Seed essential Masoretic reading skills missing from the base curriculum."""

import argparse
import json
import sqlite3
from pathlib import Path

SOURCES = [
    {"id": "oshb", "name": "Open Scriptures Hebrew Bible", "url": "https://github.com/openscriptures/morphhb", "version": "3d15126fb1ef74867fc1434be1942e837932691f", "license": "WLC text: public domain; OSHB morphology/lemmas: CC BY 4.0", "attribution": "Open Scriptures Hebrew Bible Project"},
    {"id": "unicode-hebrew", "name": "Unicode Hebrew", "url": "https://unicode.org/charts/PDF/U0590.pdf", "version": "Unicode 17.0", "license": "Unicode Terms of Use", "attribution": "Unicode Consortium"},
    {"id": "gkc", "name": "Gesenius' Hebrew Grammar", "url": "https://en.wikisource.org/wiki/Gesenius%27_Hebrew_Grammar", "version": "Kautzsch-Cowley 1910 edition", "license": "Public domain (US)", "attribution": "Gesenius, Kautzsch, and Cowley"},
]

LESSONS = [
    {
        "id": "dagesh_types", "title": "Dagesh Lene, Dagesh Forte, and Mappiq",
        "category": "grammar", "level": 3,
        "description": "Distinguish the identical-looking dots used for stop values, doubling, and consonantal He",
        "prerequisites": ["bet", "kaf", "pe", "vowel_patah"],
        "explanation": (
            "A dot inside a Hebrew letter must be interpreted in context. Dagesh lene marks the stop "
            "value of a begadkephat letter, as in the initial בּ of בְּרֵאשִׁית. Dagesh forte marks "
            "historical doubling, as in the שּׁ of הַשָּׁמַיִם after the article. A dot in final הּ is "
            "mappiq and shows that He is consonantal. Modern classroom pronunciation may not audibly "
            "preserve every historical distinction, but parsing still depends on it."
        ),
        "key_points": [
            "The same dot can have different grammatical functions",
            "Dagesh lene is limited to begadkephat letters",
            "Dagesh forte represents historical consonant doubling",
            "Mappiq in final הּ marks consonantal He",
        ],
        "verse_examples": [{"verse_ref": "gen.1.1", "hebrew": "בְּרֵאשִׁית … הַשָּׁמַיִם", "note": "Dagesh lene in initial Bet; dagesh forte after the article in הַשָּׁמַיִם."}],
        "practice": [
            ("multiple_choice", "What does dagesh forte represent in the Tiberian system?", ["Consonant doubling", "A silent letter", "Word stress", "A long vowel"], "Consonant doubling"),
            ("multiple_choice", "What is a dot in final הּ called?", ["Mappiq", "Meteg", "Maqqef", "Shewa"], "Mappiq"),
            ("multiple_choice", "How many distinct functions can the dot inside a Hebrew letter serve?", ["One", "Two", "Three", "Four"], "Three"),
        ],
    },
    {
        "id": "furtive_patah", "title": "Furtive Patah",
        "category": "vowel", "level": 3,
        "description": "Read final ח, ע, or הּ with patah in the correct spoken order",
        "prerequisites": ["vowel_patah", "chet", "ayin", "he"],
        "explanation": (
            "When final ח, ע, or consonantal הּ follows a non-a vowel, a patah written under the final "
            "guttural can be pronounced before that consonant. Thus רוּחַ is read approximately rūaḥ, "
            "not rūḥa. The writing remains in normal logical order; this is a pronunciation rule, not "
            "a reason to reverse Unicode characters."
        ),
        "key_points": ["The patah is displayed under the final guttural", "It is pronounced before the final consonant", "Common example: רוּחַ (rūaḥ)"],
        "verse_examples": [{"verse_ref": "gen.1.2", "hebrew": "וְרוּחַ אֱלֹהִים", "note": "רוּחַ ends with furtive patah under ח."}],
        "practice": [
            ("multiple_choice", "Which reading reflects furtive patah in רוּחַ?", ["rūaḥ", "rūḥa", "raḥū", "rūḥ"], "rūaḥ"),
            ("multiple_choice", "Where is furtive patah pronounced relative to the final guttural?", ["Before the guttural", "After the guttural", "As a separate syllable", "It is silent"], "Before the guttural"),
        ],
    },
    {
        "id": "maqqef_stress", "title": "Maqqef and Word Stress",
        "category": "reading", "level": 3,
        "description": "Read maqqef-bound words as one accentual unit",
        "prerequisites": ["syllable_stress"],
        "explanation": (
            "Maqqef (־) joins adjacent written words into one accentual unit. A word before maqqef "
            "normally gives up its independent primary accent, so maqqef can affect stress and vowel "
            "reduction. Preserve it when tokenizing: it is not merely a modern hyphen."
        ),
        "key_points": ["Maqqef joins words into one accentual unit", "The first word normally lacks independent primary stress", "Do not discard maqqef from canonical text"],
        "verse_examples": [{"verse_ref": "gen.1.4", "hebrew": "אֶת־הָאוֹר", "note": "The object marker and noun form one maqqef-bound accentual unit."}],
        "practice": [
            ("multiple_choice", "What does maqqef join?", ["Words into one accentual unit", "Two vowels", "Two verses", "A root and lexicon entry"], "Words into one accentual unit"),
            ("multiple_choice", "What does the maqqef (־) do to the words it joins?", ["Joins them into one accentual unit", "Separates two verses", "Marks a question", "Ends a sentence"], "Joins them into one accentual unit"),
        ],
    },
    {
        "id": "cantillation_basics", "title": "Cantillation: Stress and Clause Structure",
        "category": "reading", "level": 4,
        "description": "Use the accents to locate stress and major syntactic divisions",
        "prerequisites": ["maqqef_stress"],
        "explanation": (
            "The Masoretic accents (te'amim) record word stress, group words syntactically, and guide "
            "liturgical chanting. Begin by distinguishing conjunctive accents, which bind a word to what "
            "follows, from disjunctive accents, which mark divisions of different strengths. The prose "
            "books and Psalms–Proverbs–Job do not use exactly the same accent system."
        ),
        "key_points": ["Accents mark stress", "Accents divide and join clauses", "Melodies vary by reading tradition", "Poetic books have a distinct accent system"],
        "verse_examples": [{"verse_ref": "gen.1.1", "hebrew": "בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים", "note": "The accents mark stress and a major division after אֱלֹהִים."}],
        "practice": [
            ("multiple_choice", "Which is a linguistic function of the Masoretic accents?", ["Marking stress and clause grouping", "Replacing consonants", "Translating words", "Identifying every root"], "Marking stress and clause grouping"),
            ("multiple_choice", "Do all Jewish reading traditions chant the accents with the same melody?", ["No — melodies vary by tradition", "Yes — identical melody", "Only Sephardic traditions chant", "Accents are never chanted"], "No — melodies vary by tradition"),
        ],
    },
    {
        "id": "masoretic_text_layers", "title": "Consonantal Text, Pointing, and Accents",
        "category": "reading", "level": 5,
        "description": "Distinguish the written consonants from Masoretic vocalization and accent metadata",
        "prerequisites": ["cantillation_basics", "reading_torah"],
        "explanation": (
            "A pointed Hebrew Bible displays several layers together: consonantal letters, Masoretic "
            "vowel points, and accent signs. The consonants and the reading tradition are related evidence, "
            "but they are not identical data layers. A learner should be able to hide the accents or points "
            "without changing the underlying consonants, and should not treat later vocalization as though "
            "it were a separate consonant."
        ),
        "key_points": ["Consonants, vowels, and accents are distinct encoded layers", "Pointing records a Masoretic reading tradition", "Preserve the full source even when the UI hides marks"],
        "verse_examples": [{"verse_ref": "gen.1.1", "hebrew": "בראשית / בְּרֵאשִׁית", "note": "The same consonantal sequence shown unpointed and pointed."}],
        "practice": [
            ("multiple_choice", "What do niqqud signs primarily record?", ["A Masoretic reading tradition", "New consonants", "English translation", "Verse numbering"], "A Masoretic reading tradition"),
            ("multiple_choice", "If vowel points are hidden in the display, what happens to the stored consonantal text?", ["It is unchanged — points are a separate layer", "It is rewritten without consonants", "Only the first word changes", "It becomes Aramaic"], "It is unchanged — points are a separate layer"),
        ],
    },
    {
        "id": "qere_ketiv", "title": "Qere and Ketiv",
        "category": "reading", "level": 6,
        "description": "Keep the written form and prescribed reading distinct",
        "prerequisites": ["masoretic_text_layers"],
        "explanation": (
            "Ketiv ('what is written') preserves the consonantal form in the text; qere ('what is read') "
            "records the prescribed public reading. Printed editions commonly keep the ketiv in the line "
            "and give the qere in the margin. Do not silently replace one with the other: display and search "
            "both, and label which form supplies the pronunciation or morphology."
        ),
        "key_points": ["Ketiv is written", "Qere is read", "Both forms are textual evidence", "Never merge them without a label"],
        "verse_examples": [{"verse_ref": "2kgs.8.10", "hebrew": "לֹא / לוֹ", "note": "A traditional ketiv/qere pair; editions distinguish the written and read forms."}],
        "practice": [
            ("multiple_choice", "Which term means 'what is written'?", ["Ketiv", "Qere", "Maqqef", "Meteg"], "Ketiv"),
            ("multiple_choice", "How should software handle qere and ketiv?", ["Store and label both", "Delete the ketiv", "Merge them silently", "Use only the English translation"], "Store and label both"),
        ],
    },
    {
        "id": "weak_initial_yod", "title": "Weak Verbs: Initial Yod/Waw",
        "category": "verb", "level": 6,
        "description": "Recognize roots whose initial Yod or historical Waw changes across forms",
        "prerequisites": ["qal_imperfect", "weak_nun"],
        "explanation": "Some roots beginning with י, historically including I-Waw classes, change their first radical or vowels in prefixed forms. Compare יָדַע (he knew) with the Hiphil הוֹדִיעַ (he made known). Identify the attested form first, then recover the root with a lexicon; do not delete an initial י mechanically.",
        "key_points": ["Initial Yod may participate in predictable stem changes", "Historical classification and surface spelling are not identical", "Confirm the root from multiple forms"],
        "verse_examples": [{"verse_ref": "gen.3.7", "hebrew": "וַיֵּדְעוּ", "note": "A wayyiqtol form of ידע, 'and they knew.'"}],
        "practice": [("multiple_choice", "What is the safest way to recover an I-Yod/Waw root?", ["Compare forms and consult a lexicon", "Always remove Yod", "Use the English tense", "Count vowel points"], "Compare forms and consult a lexicon")],
    },
    {
        "id": "weak_initial_aleph", "title": "Weak Verbs: Initial Aleph",
        "category": "verb", "level": 6,
        "description": "Recognize vowel changes and quiescent Aleph in common I-Aleph verbs",
        "prerequisites": ["qal_imperfect", "aleph"],
        "explanation": "I-Aleph roots can show distinctive vowels because Aleph is guttural and may become quiescent. The common root אמר appears as אָמַר in qatal and יֹאמַר in yiqtol. The consonantal root remains א־מ־ר even when the prefixed form does not look like a regular strong-verb pattern.",
        "key_points": ["Aleph is a root consonant even when quiescent", "אָמַר and יֹאמַר belong to אמר", "Parse the form before translating"],
        "verse_examples": [{"verse_ref": "gen.1.3", "hebrew": "וַיֹּאמֶר אֱלֹהִים", "note": "Wayyiqtol of the I-Aleph root אמר."}],
        "practice": [("multiple_choice", "What is the root of וַיֹּאמֶר?", ["אמר", "ימר", "מור", "מרר"], "אמר")],
    },
    {
        "id": "weak_final_aleph", "title": "Weak Verbs: Final Aleph",
        "category": "verb", "level": 6,
        "description": "Recover III-Aleph roots when final Aleph is quiescent",
        "prerequisites": ["qal_imperfect", "aleph"],
        "explanation": "In III-Aleph roots such as מצא, final Aleph remains part of the root but is often quiescent. Forms such as מָצָא and יִמְצָא must be distinguished from III-He patterns. Preserve the written Aleph when identifying the lemma.",
        "key_points": ["Final Aleph remains a radical", "Quiescent does not mean absent", "Compare qatal and yiqtol forms"],
        "verse_examples": [{"verse_ref": "gen.8.9", "hebrew": "וְלֹא־מָצְאָה הַיּוֹנָה מָנוֹחַ", "note": "מָצְאָה is from the III-Aleph root מצא."}],
        "practice": [("multiple_choice", "Which root underlies מָצָא?", ["מצא", "מצה", "יצא", "מץ"], "מצא")],
    },
    {
        "id": "weak_doubly", "title": "Doubly Weak Verbs",
        "category": "verb", "level": 7,
        "description": "Analyze verbs affected by more than one weak-root pattern",
        "prerequisites": ["weak_initial_yod", "weak_final_aleph", "weak_hollow"],
        "explanation": "A doubly weak verb combines two weak features, so several radicals may change or become quiescent in one form. בוא, for example, contains a middle vowel letter and final Aleph; forms include בָּא and יָבוֹא. Treat these as overlapping regular patterns rather than unrelated exceptions.",
        "key_points": ["More than one weak feature can operate together", "Recover all radicals from a paradigm", "Do not infer the root from one surface form alone"],
        "verse_examples": [{"verse_ref": "exo.10.1", "hebrew": "בֹּא אֶל־פַּרְעֹה", "note": "The imperative בֹּא belongs to the doubly weak root בוא."}],
        "practice": [("multiple_choice", "Why should doubly weak verbs be compared across a paradigm?", ["Several radicals may change in one form", "They have no roots", "They occur only in Aramaic", "Their vowels never change"], "Several radicals may change in one form")],
    },
    {
        "id": "weqatal_discourse", "title": "Weqatal in Instructions and Projected Sequences",
        "category": "syntax", "level": 6,
        "description": "Read waw-prefixed qatal forms by discourse function rather than tense reversal",
        "prerequisites": ["vav_consecutive", "qal_perfect"],
        "explanation": "Weqatal often continues instructions, obligations, or projected sequences. In וְאָהַבְתָּ אֵת יְהוָה (Deut 6:5), the form contributes to an instructional sequence and is commonly translated 'and you shall love.' The waw does not mechanically reverse a past tense; clause type and discourse context guide interpretation.",
        "key_points": ["Common in instruction and projected discourse", "Not mechanical tense reversal", "Interpret within the clause sequence"],
        "verse_examples": [{"verse_ref": "deu.6.5", "hebrew": "וְאָהַבְתָּ אֵת יְהוָה אֱלֹהֶיךָ", "note": "Weqatal within covenant instruction."}],
        "practice": [("multiple_choice", "What best explains וְאָהַבְתָּ in Deuteronomy 6:5?", ["A form continuing instruction", "A noun", "A reversed past tense by rule", "An Aramaic participle"], "A form continuing instruction")],
    },
    {
        "id": "poetic_parallelism", "title": "Reading Hebrew Poetry: Parallelism",
        "category": "reading", "level": 7,
        "description": "Read paired poetic lines as related but not mechanically synonymous claims",
        "prerequisites": ["reading_psalms", "cantillation_basics"],
        "explanation": "Biblical Hebrew poetry frequently places lines or clauses in parallel. The second line may restate, sharpen, contrast, specify, or advance the first. Read the relationship from syntax and vocabulary rather than assuming every pair says exactly the same thing. Ellipsis is common: a word expressed in one line may be understood in the next.",
        "key_points": ["Parallel lines can restate or advance", "Look for ellipsis and contrast", "Poetic word order is flexible"],
        "verse_examples": [{"verse_ref": "isa.1.2", "hebrew": "שִׁמְעוּ שָׁמַיִם וְהַאֲזִינִי אֶרֶץ כִּי יְהוָה דִּבֵּר", "note": "Heavens and earth form a related parallel pair; note the ellipsis of the verb in the second line."}],
        "practice": [("multiple_choice", "In biblical poetry, parallel lines typically:", ["Restate, sharpen, or advance the first", "Repeat it word-for-word", "Always contradict it", "Are always longer"], "Restate, sharpen, or advance the first")],
    },
    {
        "id": "legal_formulae", "title": "Reading Legal Hebrew",
        "category": "reading", "level": 7,
        "description": "Recognize conditional case law and direct covenant commands",
        "prerequisites": ["conditional_sentences", "reading_torah"],
        "explanation": "Biblical laws use several clause patterns. Case law commonly introduces circumstances with כִּי or אִם and then states the consequence; direct commands and prohibitions address the hearer without a narrated case. These labels describe literary form and do not by themselves determine modern application.",
        "key_points": ["כִּי or אִם can introduce a legal case", "The consequence follows the stated circumstance", "Direct commands use a different discourse shape"],
        "verse_examples": [{"verse_ref": "exo.21.2", "hebrew": "כִּי תִקְנֶה עֶבֶד עִבְרִי", "note": "כִּי introduces the circumstance of a legal case."}],
        "practice": [("multiple_choice", "What can כִּי introduce in legal prose?", ["The circumstance of a case", "Only a proper name", "A qere note", "A cantillation melody"], "The circumstance of a case")],
    },
    {
        "id": "prophetic_formulae", "title": "Reading Prophetic Messenger Formulas",
        "category": "reading", "level": 7,
        "description": "Use recurring formulas to recognize prophetic discourse boundaries",
        "prerequisites": ["reading_isaiah", "construct_chain"],
        "explanation": "Prophetic books use recurring formulas such as וַיְהִי דְבַר־יְהוָה אֵלַי לֵאמֹר ('the word of YHWH came to me, saying') and כֹּה אָמַר יְהוָה ('thus said YHWH'). These formulas help identify a new speech unit. Their theological significance is interpretation; their grammatical function as discourse markers is textual observation.",
        "key_points": ["Formulas mark speech boundaries", "דְבַר־יְהוָה is a construct chain", "לֵאמֹר introduces quoted speech"],
        "verse_examples": [{"verse_ref": "jer.1.4", "hebrew": "וַיְהִי דְבַר־יְהוָה אֵלַי לֵאמֹר", "note": "A formula introducing prophetic speech."}],
        "practice": [("multiple_choice", "What does לֵאמֹר commonly introduce?", ["Quoted speech", "A plural noun", "A qere spelling", "The article"], "Quoted speech")],
    },
    {
        "id": "biblical_aramaic_boundary", "title": "Biblical Aramaic: Know the Boundary",
        "category": "reading", "level": 7,
        "description": "Distinguish the Aramaic sections of the Old Testament from Biblical Hebrew",
        "prerequisites": ["masoretic_text_layers", "root_concept"],
        "explanation": "Most of the Old Testament is Hebrew, but substantial sections of Daniel and Ezra are Aramaic, with smaller Aramaic material elsewhere. Daniel 2:4 explicitly marks the switch with אֲרָמִית ('in Aramaic'). The languages are related but have distinct morphology and vocabulary; an Aramaic token should be labeled rather than silently taught as Hebrew.",
        "key_points": ["OT does not mean Hebrew-only", "Daniel and Ezra contain Aramaic sections", "Morphology should label H versus A data"],
        "verse_examples": [{"verse_ref": "dan.2.4", "hebrew": "וַיְדַבְּרוּ הַכַּשְׂדִּים לַמֶּלֶךְ אֲרָמִית", "note": "The text signals speech in Aramaic."}],
        "practice": [("multiple_choice", "Which parts of the Old Testament are written in Aramaic?", ["Sections of Daniel and Ezra", "None — it is all Hebrew", "The entire Pentateuch", "Only the Psalms"], "Sections of Daniel and Ezra")],
    },
]


def seed(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_hebrew_practice_unique
                    ON hebrew_practice_items(node_id,question_type,question_text,correct_answer)""")
    for lesson in LESSONS:
        node_id = lesson["id"]
        conn.execute(
            """INSERT INTO hebrew_nodes (id,title,level,category,description) VALUES (?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET title=excluded.title,level=excluded.level,
               category=excluded.category,description=excluded.description""",
            (node_id, lesson["title"], lesson["level"], lesson["category"], lesson["description"]),
        )
        content = {key: value for key, value in lesson.items() if key not in {"id", "practice", "prerequisites"}}
        content.update({"node_id": node_id, "sources": SOURCES, "source_ids": [source["id"] for source in SOURCES]})
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
            [(node_id, qtype, question, json.dumps(options, ensure_ascii=False), answer)
             for qtype, question, options, answer in lesson["practice"]],
        )
        conn.execute("DELETE FROM hebrew_edges WHERE target_id=? AND edge_type='prerequisite'", (node_id,))
        for prerequisite in lesson["prerequisites"]:
            if conn.execute("SELECT 1 FROM hebrew_nodes WHERE id=?", (prerequisite,)).fetchone():
                conn.execute(
                    "INSERT INTO hebrew_edges (source_id,target_id,edge_type) VALUES (?,?,'prerequisite')",
                    (prerequisite, node_id),
                )
        # Surface authentic examples as learner-visible attestations.
        for example in lesson.get("verse_examples", []):
            if example.get("verse_ref"):
                conn.execute("""
                    INSERT INTO hebrew_attestations
                        (node_id,verse_id,attestation_type,explanation,difficulty)
                    VALUES (?,?,'reading_example',?,'beginner')
                    ON CONFLICT(node_id,verse_id) DO UPDATE SET
                        attestation_type='reading_example',explanation=excluded.explanation
                """, (node_id, example["verse_ref"], example.get("note", "")))
    conn.commit()
    conn.close()
    print(f"Upserted {len(LESSONS)} Masoretic reading lessons")
    return len(LESSONS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path("data/memorize.db"))
    args = parser.parse_args()
    seed(args.db)
