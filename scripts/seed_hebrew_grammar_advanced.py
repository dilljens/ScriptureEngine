#!/usr/bin/env python3
"""Advanced grammar lessons: definite article, prepositions, construct chain, demonstratives, interrogatives.

Adds 5 new grammar lessons covering foundational gaps identified in the audit.
Run AFTER seed_hebrew_grammar.py.

Usage:
    python3 scripts/seed_hebrew_grammar_advanced.py
"""

import json
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"

NEW_LESSONS = [
    # ── Level 3: Definite Article ──
    {
        "id": "definite_article",
        "title": "Definite Article (הַ)",
        "category": "grammar",
        "level": 3,
        "description": "The prefix הַ (ha-) means 'the' and attaches to the beginning of nouns",
        "prerequisites": ["he", "aleph", "ayin", "chet"],
        "explanation": """The definite article in Hebrew is the prefix הַ (ha-) attached to the beginning of a noun. It means 'the'. Unlike English, there is no separate word for 'the' — it is always a prefix.

Basic rule: הַ + consonant with dagesh forte in the next letter.
  • דָּבָר (davar = word) → הַדָּבָר (hadavar = the word)
  • מֶלֶךְ (melekh = king) → הַמֶּלֶךְ (hamelekh = the king)

Before guttural letters (א, ה, ח, ע, ר), the article changes:
  • Before א or ר: הַ + patah, no dagesh → הָאָדָם (ha-adam), הָרָע (hara)
  • Before ה or ח: הַ + qamats → הָהָר (hahar), הֶחָזוֹן (hehazon)
  • Before ע: הַ + patah → הָעִיר (hair)

The interrogative ה (he interrogative) is identical in form but changes meaning:
  • הֲשָׁמַרְתָּ? (hashamarta?) = "Did you guard?"
  • When followed by sheva, the article takes patah and the interrogative takes hataf-patah (הֲ)

This distinction is critical for reading — context determines whether הַ means "the" or "?".""",
        "key_points": [
            "הַ (ha-) = the — always a prefix, never a separate word",
            "Basic form: הַ + dagesh forte in next consonant",
            "Before gutturals: vowel changes to qamats or patah, no dagesh",
            "Interrogative הֲ asks a question: 'Did...?' 'Is...?'",
            "Context disambiguates: search for question marks or interrogative markers",
        ],
        "worked_examples": [
            {"question": "Compare הַמֶּלֶךְ vs הֲמֶלֶךְ",
             "steps": ["הַמֶּלֶךְ (ha-melekh) = 'the king' — definite article",
                       "הֲמֶלֶךְ (ha-melekh?) = 'the king?' or 'is it the king?' — interrogative ה",
                       "The vowel under ה distinguishes: patah (article) vs hataf-patah (interrogative)",
                       "In unpointed text, context is your only guide."],
             "answer": "Same consonants, different vowel, completely different meaning."},
            {"question": "Why does אָדָם (adam) become הָאָדָם (ha-adam) not הַאָדָם?",
             "steps": ["א is a guttural — it cannot take dagesh forte",
                       "Without dagesh, the vowel lengthens from patah to qamats",
                       "Result: הָאָדָם (ha-adam), not הַאָּדָם"],
             "answer": "Gutturals reject dagesh, so the article vowel compensates."},
        ],
        "verse_examples": [
            {"ref": "gen.1.1", "hebrew": "בְּרֵאשִׁית בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם וְאֵת הָאָרֶץ", "english": "In the beginning God created the heavens and the earth", "highlight": "הַשָּׁמַיִם (the heavens) and הָאָרֶץ (the earth) — both have the definite article"},
            {"ref": "gen.1.3", "hebrew": "וַיֹּאמֶר אֱלֹהִים יְהִי אוֹר", "english": "And God said let there be light", "highlight": "אוֹר is indefinite without the article"},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is the definite article in Hebrew?", "opts": ["A separate word 'ha' before the noun", "A prefix הַ attached to the noun", "A suffix at the end of the noun", "A vowel change inside the noun"], "ans": "A prefix הַ attached to the noun"},
            {"type": "multiple_choice", "q": "Before guttural letters, why does the article change form?", "opts": ["Because gutturals cannot take dagesh", "Because gutturals are always silent", "Because gutturals are always doubled", "Because gutturals change the noun's gender"], "ans": "Because gutturals cannot take dagesh"},
            {"type": "classification", "q": "Is הָאָרֶץ using the article or interrogative?", "opts": ["Definite article", "Interrogative ה", "Both", "Neither"], "ans": "Definite article"},
            {"type": "recall", "q": "What does הָ/הֲ at the beginning of a verb (not a noun) typically indicate?", "ans": "Interrogative — asking a yes/no question"},
        ],
    },

    # ── Level 3: Independent Prepositions ──
    {
        "id": "independent_prepositions",
        "title": "Independent Prepositions",
        "category": "grammar",
        "level": 3,
        "description": "Stand-alone prepositions for spatial, temporal, and logical relationships",
        "prerequisites": ["aleph", "lamed", "bet", "kaf", "mem"],
        "explanation": """Prepositions show relationships between words: location, direction, time, association. Hebrew has two types:

1. INSEPARABLE prefixes (already covered): ב (in/with), כ (as/like), ל (to/for), מ (from)
2. INDEPENDENT prepositions: separate words that stand alone

The most common independent prepositions:

Spatial/Directional:
  • אֶל (el) = to, toward — direction of movement
  • עַל (al) = upon, on, over, about
  • תַּחַת (tahat) = under, beneath, instead of
  • לִפְנֵי (lifnei) = before, in front of (lit. 'to the face of')
  • אַחֲרֵי (aharei) = after, behind
  • בֵּין (bein) = between, among
  • עִם (im) = with, alongside
  • נֶגֶד (neged) = before, opposite, in front of
  • אֵצֶל (etzel) = beside, near

Temporal:
  • לִפְנֵי (lifnei) = before (time)
  • אַחֲרֵי (aharei) = after (time)
  • עַד (ad) = until, as far as
  • מִן (min) = from, since

Logical/Relational:
  • עַל (al) = concerning, about
  • עִם (im) = with (accompaniment)
  • תַּחַת (tahat) = instead of, in place of

Most independent prepositions can take pronominal suffixes (covered in Prepositions + Suffixes lesson).""",
        "key_points": [
            "Independent prepositions are separate words (unlike ב,כ,ל,מ which are prefixes)",
            "אֶל = to/toward, עַל = upon/over, תַּחַת = under",
            "לִפְנֵי = before (lit. 'to the face of'), אַחֲרֵי = after",
            "עִם = with, בֵּין = between, נֶגֶד = opposite",
            "Many can take pronominal suffixes (e.g. עִמָּדִי = with me)",
        ],
        "worked_examples": [
            {"question": "What's the difference between אֶל and עַל?",
             "steps": ["אֶל (el) = to/toward — movement toward a destination",
                       "עַל (al) = upon/on/over — position on top or about a topic",
                       "Gen 1:1: וְרוּחַ אֱלֹהִים מְרַחֶפֶת עַל־פְּנֵי הַמָּיִם = Spirit hovering OVER the waters",
                       "Gen 12:1: לֶךְ־לְךָ מֵאַרְצְךָ... אֶל־הָאָרֶץ = Go TO the land"],
             "answer": "אֶל = direction/toward, עַל = position/upon"},
        ],
        "verse_examples": [
            {"ref": "gen.1.2", "hebrew": "וְרוּחַ אֱלֹהִים מְרַחֶפֶת עַל־פְּנֵי הַמָּיִם", "english": "The Spirit of God was hovering over the waters", "highlight": "עַל־פְּנֵי = 'over the face of' — preposition עַל with construct chain"},
            {"ref": "gen.1.4", "hebrew": "וַיַּבְדֵּל אֱלֹהִים בֵּין הָאוֹר וּבֵין הַחֹשֶׁךְ", "english": "God separated between the light and between the darkness", "highlight": "בֵּין... וּבֵין = 'between...and between...' — paired preposition"},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "Which preposition means 'upon' or 'over'?", "opts": ["אֶל", "עַל", "עִם", "תַּחַת"], "ans": "עַל"},
            {"type": "multiple_choice", "q": "What's the difference between inseparable and independent prepositions?", "opts": ["Independent are longer", "Inseparable are prefixes, independent are separate words", "Independent are only temporal", "There is no difference"], "ans": "Inseparable are prefixes, independent are separate words"},
            {"type": "recall", "q": "Name the independent preposition meaning 'before' (spatial and temporal)", "ans": "לִפְנֵי (lifnei)"},
            {"type": "recall", "q": "Name two prepositions that mean 'after' or 'behind'", "ans": "אַחֲרֵי (aharei)"},
        ],
    },

    # ── Level 4: Construct Chain ──
    {
        "id": "construct_chain",
        "title": "Construct Chain (סְמִיכוּת)",
        "category": "grammar",
        "level": 4,
        "description": "Two or more nouns chained together meaning 'X of Y'",
        "prerequisites": ["noun_state", "noun_gender", "noun_number"],
        "explanation": """A construct chain (סְמִיכוּת / smikhut) is two or more nouns linked together where the first is in CONSTRUCT state and the rest are in ABSOLUTE state. It translates as 'X of Y'.

Structure:
  • Noun₁ (construct) + Noun₂ (absolute) = "X of Y"
  • Only the LAST noun takes the definite article (if any)
  • The first noun never takes the article

Examples:
  • מֶלֶךְ יִשְׂרָאֵל (melekh yisrael) = king of Israel
  • בֵּית־הַמִּקְדָּשׁ (beit hamikdash) = house of the sanctuary (the Temple)
  • דְּבַר־יְהוָה (devar YHWH) = word of YHWH

The first noun in construct may change form:
  • Masculine plural: ־ִים → ־ֵי (e.g. דְּבָרִים → דִּבְרֵי = words of)
  • Feminine: ־ָה → ־ַת (e.g. תּוֹרָה → תּוֹרַת = law of)
  • Some nouns have special construct forms: אָב → אֲבִי (father of)

Chains can be 3+ nouns long:
  • אֲרוֹן בְּרִית יְהוָה (aron brit YHWH) = the ark of the covenant of YHWH
  • בֵּית מֶלֶךְ יְהוּדָה (beit melekh yehudah) = the house of the king of Judah""",
        "key_points": [
            "Construct chain = Noun (construct) + Noun (absolute) = 'X of Y'",
            "Only the LAST noun can take the definite article",
            "The first noun loses its article (if any) when in construct",
            "Masculine plural: ־ִים → ־ֵי (e.g. דְּבָרִים → דִּבְרֵי)",
            "Chains can be stacked 3+ deep — read from right to left",
        ],
        "worked_examples": [
            {"question": "Parse the chain: בֵּית הַמֶּלֶךְ",
             "steps": ["בֵּית = construct of בַּיִת (house) — 'house of'",
                       "הַמֶּלֶךְ = the king (absolute with article)",
                       "The chain means: 'the house of the king'",
                       "Note: only the last noun takes the article"],
             "answer": "בֵּית הַמֶּלֶךְ = 'the house of the king' (or 'the king's house')"},
            {"question": "Why is it מַלְכֵי and not מְלָכִים in מַלְכֵי יִשְׂרָאֵל?",
             "steps": ["מְלָכִים = kings (absolute plural)",
                       "In construct, plural changes: ־ִים → ־ֵי",
                       "מַלְכֵי יִשְׂרָאֵל = 'kings of Israel'",
                       "The vowel changes from sheva to patah under the first letter"],
             "answer": "Plural construct form is מַלְכֵי, not מְלָכִים"},
        ],
        "verse_examples": [
            {"ref": "gen.1.1", "hebrew": "בְּרֵאשִׁית בָּרָא אֱלֹהִים", "english": "In the beginning God created", "highlight": "בְּרֵאשִׁית = 'in beginning of' — construct of רֵאשִׁית (beginning) with inseparable preposition ב"},
            {"ref": "exo.15.3", "hebrew": "יְהוָה אִישׁ מִלְחָמָה", "english": "YHWH is a man of war", "highlight": "אִישׁ מִלְחָמָה = construct chain: 'man of war' — both nouns are indefinite"},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "In a construct chain, which noun gets the definite article?", "opts": ["The first noun", "The last noun", "All nouns", "No nouns"], "ans": "The last noun"},
            {"type": "multiple_choice", "q": "What is the construct form of דְּבָרִים (words)?", "opts": ["דְּבָרִים", "דִּבְרֵי", "דָּבָר", "דְּבָרִים"], "ans": "דִּבְרֵי"},
            {"type": "recall", "q": "Translate the construct chain: בְּנֵי יִשְׂרָאֵל", "ans": "children/sons of Israel"},
            {"type": "classification", "q": "In אֲרוֹן הַבְּרִית, which word is in construct state?", "opts": ["אֲרוֹן (first)", "הַבְּרִית (last)", "Both", "Neither"], "ans": "אֲרוֹן (first)"},
        ],
    },

    # ── Level 4: Demonstratives ──
    {
        "id": "demonstratives",
        "title": "Demonstratives (This/That/These/Those)",
        "category": "grammar",
        "level": 4,
        "description": "Demonstrative pronouns and adjectives: זֶה, זֹאת/זוֹ, אֵלֶּה, הוּא, הִיא",
        "prerequisites": ["vocab_הוא_48", "vocab_אתה_47", "vocab_אלה_92"],
        "explanation": """Demonstratives point to specific things: 'this', 'that', 'these', 'those'. Hebrew has two patterns:

ATTRIBUTIVE (modifies a noun):
  • The noun has the article, the demonstrative follows WITHOUT the article
  • הָאִישׁ הַזֶּה (ha-ish ha-zeh) = THIS man (lit. 'the man, the this')
  • הָאִשָּׁה הַזֹּאת (ha-ishah ha-zot) = THIS woman
  • הָאֲנָשִׁים הָאֵלֶּה (ha-anashim ha-eleh) = THESE men

PREDICATE (the noun IS this/that):
  • No article on the demonstrative
  • זֶה דָּבָר טוֹב (zeh davar tov) = THIS is a good thing
  • אֵלֶּה דִּבְרֵי הָעֵדוּת (eleh divrei ha-edut) = THESE are the words of the testimony

Demonstrative forms:
  Singular masculine: זֶה (zeh) = this, זֶה/הוּא = that
  Singular feminine: זֹאת (zot) or זוֹ (zo) = this, הִיא = that
  Plural (both genders): אֵלֶּה (eleh) = these/those
  Distal ('that'): הַהוּא (hahu) = that (m.), הַהִיא (hahi) = that (f.)

The distal forms are actually the article + pronoun: הַהוּא = 'the-he' = 'that one'.""",
        "key_points": [
            "This = זֶה (m.), זֹאת/זוֹ (f.) — These = אֵלֶּה (both genders)",
            "Attributive: noun + article, then demonstrative without article",
            "Predicate: demonstrative first, then noun (no article)",
            "That = הַהוּא (m. distal), הַהִיא (f. distal) — article + pronoun",
            "The same forms work for both adjectives and pronouns",
        ],
        "worked_examples": [
            {"question": "Compare: הַיּוֹם הַזֶּה vs זֶה הַיּוֹם",
             "steps": ["הַיּוֹם הַזֶּה = 'this day' (attributive) — describing which day",
                       "זֶה הַיּוֹם = 'this is the day' (predicate) — identifying the day",
                       "Word order determines the meaning!",
                       "Psalm 118:24: זֶה הַיּוֹם עָשָׂה יְהוָה = THIS IS the day YHWH has made"],
             "answer": "Word order: N-adj = attributive, Pro-N = predicate"},
        ],
        "verse_examples": [
            {"ref": "deu.6.4", "hebrew": "שְׁמַע יִשְׂרָאֵל יְהוָה אֱלֹהֵינוּ יְהוָה אֶחָד", "english": "Hear O Israel: YHWH our God, YHWH is one", "highlight": "אֱלֹהֵינוּ (our God) and אֶחָד (one) — predicate use"},
            {"ref": "gen.2.23", "hebrew": "זֹאת הַפַּעַם עֶצֶם מֵעֲצָמַי", "english": "This is now bone of my bones", "highlight": "זֹאת = 'this one' (predicate) — refers to the woman"},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "'This man' in Hebrew is:", "opts": ["הָאִישׁ זֶה", "הָאִישׁ הַזֶּה", "זֶה אִישׁ", "אִישׁ זֶה"], "ans": "הָאִישׁ הַזֶּה"},
            {"type": "multiple_choice", "q": "How do you express 'that day' (far/distal)?", "opts": ["הַיּוֹם הַהוּא", "זֶה הַיּוֹם", "הַיּוֹם זֶה", "הַיּוֹם הַזֶּה"], "ans": "הַיּוֹם הַהוּא"},
            {"type": "recall", "q": "What is the feminine form of זֶה (this)?", "ans": "זֹאת (zot) or זוֹ (zo)"},
            {"type": "recall", "q": "What is the plural demonstrative (these/those)?", "ans": "אֵלֶּה (eleh)"},
        ],
    },

    # ── Level 4: Interrogatives ──
    {
        "id": "interrogatives",
        "title": "Interrogatives (Who, What, Why, Where, How, Which)",
        "category": "grammar",
        "level": 4,
        "description": "Question words and yes/no question formation in Biblical Hebrew",
        "prerequisites": ["vocab_מי_95", "vocab_מה_63", "vocab_לא_8", "vocab_כי_5"],
        "explanation": """Biblical Hebrew asks questions in two ways: with question words, or with the interrogative ה prefix.

QUESTION WORDS:
  • מִי (mi) = who? — for persons
  • מָה (mah) / מַה (mah) = what? — for things, often in construct מֶה
  • מַדּוּעַ (madua) = why? — the most common 'why'
  • לָמָּה (lamah) / לָמָה (lamah) = why? — literally 'for what?'
  • אֵיךְ (ekh) = how? — manner
  • אֵיפֹה (eifoh) = where? — location
  • מָתַי (matai) = when? — time
  • אֵיזֶה (eizeh) = which? (m.), אֵיזוֹ (eizo) = which? (f.) — rare in BH

Yes/No QUESTIONS — the Interrogative ה (he interrogative):
  • A ה prefix attached to the first word of a sentence turns it into a question
  • Distinguish from the definite article (same letters, different vowels):
    - Article: הַ + dagesh (or compensatory vowel before gutturals)
    - Interrogative: הֲ (hataf-patah) before letters with sheva, or הַ before other vowels
  • The answer to a yes/no question is often just the key word repeated or negated:
    - Question: הֲשָׁמַרְתָּ? (hashamarta?) = 'Did you guard?'
    - Answer: שָׁמַרְתִּי (shamarti) = 'I guarded' or לֹא שָׁמַרְתִּי = 'I did not guard'

Rhetorical questions often use the same forms — context determines whether a real answer is expected.""",
        "key_points": [
            "מִי = who?, מָה/מֶה = what?, מַדּוּעַ/לָמָּה = why?",
            "אֵיךְ = how?, מָתַי = when?, אֵיפֹה = where?",
            "Interrogative ה (hataf-patah הֲ) turns a statement into a yes/no question",
            "Answering: repeat the key verb, add לֹא to negate",
            "Rhetorical questions use the same forms — watch for context",
        ],
        "worked_examples": [
            {"question": "Compare the interrogative ה vs the definite article הַ",
             "steps": ["הָאִישׁ (ha-ish) = 'the man' — definite article with qamats",
                       "הֲאִישׁ (ha-ish?) = 'the man?' — interrogative with hataf-patah",
                       "הֲשָׁמַר (hashamar?) = 'did he guard?' — interrogative on verb",
                       "The vowel under ה is the only difference!",
                       "In unpointed text: 'האיש' could be either 'the man' or 'the man?'"],
             "answer": "Article = patah/qamats + dagesh. Interrogative = hataf-patah."},
        ],
        "verse_examples": [
            {"ref": "gen.3.9", "hebrew": "וַיֹּאמֶר יְהוָה אֱלֹהִים אֶל־הָאָדָם אַיֶּכָּה", "english": "And YHWH God called to the man: 'Where are you?'", "highlight": "אַיֶּכָּה (ayekah) = 'where are you?' — rare form of אֵיפֹה with 2ms suffix"},
            {"ref": "gen.18.14", "hebrew": "הֲיִפָּלֵא מֵיְהוָה דָּבָר", "english": "Is anything too wonderful for YHWH?", "highlight": "הֲיִפָּלֵא (ha-yipaleh) = 'is it too wonderful?' — interrogative ה on a verb"},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What's the Hebrew word for 'who?'", "opts": ["מָה", "מִי", "אֵיךְ", "מָתַי"], "ans": "מִי"},
            {"type": "multiple_choice", "q": "How does Biblical Hebrew form yes/no questions?", "opts": ["Adding 'yes?' at the end", "Using the interrogative ה prefix", "Raising the voice at the end", "Adding מִי at the beginning"], "ans": "Using the interrogative ה prefix"},
            {"type": "recall", "q": "Name two Hebrew words meaning 'why?'", "ans": "מַדּוּעַ (madua) and לָמָּה (lamah)"},
            {"type": "recall", "q": "What vowel distinguishes interrogative ה from the definite article?", "ans": "Interrogative ה has hataf-patah (הֲ), article has patah or qamats"},
        ],
    },
]


def main():
    conn = sqlite3.connect(str(MEM_DB))
    conn.execute("PRAGMA foreign_keys=OFF")

    new_nodes = 0
    new_items = 0
    new_edges = 0

    for lesson in NEW_LESSONS:
        lid = lesson["id"]
        existing = conn.execute(
            "SELECT id FROM hebrew_practice_items WHERE node_id=? LIMIT 1", (lid,)
        ).fetchone()
        if existing:
            print(f"  SKIP {lid}: already exists")
            continue

        conn.execute(
            "INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'grammar', ?)",
            (lid, lesson["title"], lesson["level"], lesson["description"])
        )
        new_nodes += 1

        content = {
            "node_id": lid,
            "title": lesson["title"],
            "category": "grammar",
            "level": lesson["level"],
            "explanation": lesson["explanation"],
            "key_points": lesson["key_points"],
            "worked_examples": lesson["worked_examples"],
            "verse_examples": lesson.get("verse_examples", []),
        }
        conn.execute(
            "INSERT OR IGNORE INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
            (lid, json.dumps(content, ensure_ascii=False))
        )

        for pi in lesson["practice"]:
            opts_j = json.dumps(pi.get("opts", []), ensure_ascii=False)
            conn.execute(
                "INSERT OR IGNORE INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty) VALUES (?,?,?,?,?,?)",
                (lid, pi["type"], pi["q"], opts_j, pi["ans"], 0.5)
            )
            new_items += 1

        for pid in lesson.get("prerequisites", []):
            exists = conn.execute(
                "SELECT 1 FROM hebrew_edges WHERE source_id=? AND target_id=? AND edge_type='prerequisite'",
                (pid, lid)
            ).fetchone()
            if not exists:
                conn.execute(
                    "INSERT OR IGNORE INTO hebrew_edges (source_id, target_id, edge_type) VALUES (?, ?, 'prerequisite')",
                    (pid, lid)
                )
                new_edges += 1

        print(f"  CREATED {lid}: {lesson['title']} (L{lesson['level']}, {len(lesson['practice'])} items)")

    conn.commit()
    conn.close()

    print(f"\n✓ Done! Created {new_nodes} new grammar lessons, {new_items} practice items, {new_edges} prerequisite edges")


if __name__ == '__main__':
    main()
