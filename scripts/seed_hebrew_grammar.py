#!/usr/bin/env python3
"""Seed Hebrew grammar lessons — 20+ topics with structured input/output.

Uses research-backed grammar instruction approach:
1. EXPLAIN → rule explanation
2. SHOW → paradigm/pattern display
3. EXAMPLE → verse examples
4. RECOGNIZE → identify in context
5. PRODUCE → generate correct form
6. DISCRIMINATE → distinguish similar forms

Usage:
    python3 scripts/seed_hebrew_grammar.py
"""

import json
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"


def clean_for_id(s):
    """Clean string for use as a node ID."""
    import re
    s = re.sub(r'[^a-z0-9_]', '', s.lower().replace(' ', '_').replace('(', '').replace(')', ''))
    return s[:40]


# ── Grammar Lesson Definitions ──
# Each lesson: id, title, description, level, prerequisite_ids,
# explanation, key_points, worked_examples, practice_items

GRAMMAR_LESSONS = [
    # ── Level 3: Foundational ──
    {
        "id": "begadkefat",
        "title": "Begadkefat (Spirantization)",
        "category": "grammar",
        "level": 3,
        "description": "Six letters change pronunciation when they lose their dagesh",
        "prerequisites": ["aleph", "bet", "gimel", "dalet", "kaf", "pe", "tav"],
        "explanation": """Begadkefat (also called Spirantization) is a phonological rule that affects six Hebrew letters: ב ג ד כ פ ת (begadkefat = an acronym of these letters).

When these letters have a dagesh (dot) inside, they have a "hard" (plosive) pronunciation. When they lose the dagesh, they have a "soft" (fricative/spirant) pronunciation.

The rule:
• בּ (bet) = B sound → ב (vet) = V sound
• גּ (gimel) = G sound → ג (ghimel) = GH sound (rare)
• דּ (dalet) = D sound → ד (dhalet) = DH sound (rare)
• כּ (kaf) = K sound → כ/ך (khaf) = KH sound (like Bach)
• פּ (pe) = P sound → פ/ף (fe) = F sound
• תּ (tav) = T sound → ת (thav) = TH sound (rare)

After a vowel, the letter loses its dagesh and becomes soft. After a consonant or pause, it keeps the dagesh and stays hard.

Exception: When a begadkefat letter is the first letter of a word and the previous word ends in a vowel, it may lose its dagesh.""",
        "key_points": [
            "Six letters: בגדכפת (begadkefat)",
            "Dagesh = hard/plosive, No dagesh = soft/fricative",
            "After a vowel → soft pronunciation",
            "After a consonant → hard pronunciation",
            "Most common: ב→ב (b→v), כ→כ (k→kh), פ→פ (p→f), ת→ת (t→th)",
        ],
        "worked_examples": [
            {"question": "Why does ב in בְּרֵאשִׁית have a soft (v) sound?", "steps": [
                "The letter is ב without dagesh",
                "It follows an implied vowel (sheva)",
                "Therefore it's spirantized → V sound",
                "בְּרֵאשִׁית = b'reishit → v'reishit"
            ]},
            {"question": "Compare בָּרָא vs בְּרֵאשִׁית — why different Bet sounds?", "steps": [
                "בָּרָא: Bet has a dagesh → B sound (bara)",
                "בְּרֵאשִׁית: Bet has no dagesh → V sound (v'reishit)",
                "The difference is the dagesh presence/absence"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What happens to בגדכפת letters when they lose their dagesh?", "opts": ["They become silent", "They become soft/fricative", "They double", "They become vowels"], "ans": "They become soft/fricative"},
            {"type": "multiple_choice", "q": "Which letter pair shows the most common begadkefat alternation?", "opts": ["ב/ב (b/v)", "ג/ג (g/gh)", "ד/ד (d/dh)", "ת/ת (t/th)"], "ans": "ב/ב (b/v)"},
            {"type": "true_false", "q": "Begadkefat affects all 22 Hebrew letters.", "opts": ["True", "False"], "ans": "False"},
            {"type": "true_false", "q": "After a vowel, a begadkefat letter loses its dagesh and becomes soft.", "opts": ["True", "False"], "ans": "True"},
            {"type": "classification", "q": "Does the Bet in 'בְּרֵאשִׁית' have hard or soft pronunciation?", "opts": ["Hard (B)", "Soft (V)"], "ans": "Soft (V)"},
            {"type": "classification", "q": "Does the Kaf in 'כָּתַב' have hard or soft pronunciation?", "opts": ["Hard (K)", "Soft (KH)"], "ans": "Hard (K)"},
            {"type": "contrast", "q": "Compare 'בָּיִת' (house) vs 'בְתוּלָה' (virgin) — contrast the Bet sounds", "opts": ["Both hard", "Both soft", "First hard, second soft", "First soft, second hard"], "ans": "First hard, second soft"},
            {"type": "recall", "q": "What are the six begadkefat letters in order?", "ans": "בגדכפת"},
        ],
    },
    {
        "id": "direct_object_marker",
        "title": "Direct Object Marker (את)",
        "category": "grammar",
        "level": 3,
        "description": "The particle את marks the definite direct object of a verb",
        "prerequisites": ["aleph", "bet", "vocab_את_0"],
        "explanation": """The word אֵת (et) is the direct object marker — one of the most common words in Biblical Hebrew (6,411x). It precedes the definite direct object of a transitive verb.

Key rules:
• את ONLY appears before DEFINITE objects (with ה-, proper names, or possessive suffixes)
• It has NO English translation
• It sometimes merges with object suffixes: אֹתִי (me), אֹתְךָ (you), אֹתוֹ (him), etc.

Example:
  בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם
  "Created God [direct object marker] the heavens"
  → God created the heavens (את marks 'the heavens' as the object)

Remember: NOT every את is the object marker! את can also be a preposition meaning "with" (rare). Context determines which one.""",
        "key_points": [
            "Marks the definite direct object before the verb's object",
            "Only before DEFINITE nouns (ה־, proper names, suffixes)",
            "No English translation",
            "Merges with pronominal suffixes: אֹתִי, אֹתְךָ, אֹתוֹ",
            "Occurs 6,411x in the OT — one of the most common words",
            "NOT the same as אֶת־ meaning 'with' (preposition)",
        ],
        "worked_examples": [
            {"question": "Why does Gen 1:1 use את before הַשָּׁמַיִם?", "steps": [
                "הַשָּׁמַיִם (the heavens) is definite (has ה־)",
                "It's the direct object of 'created'",
                "Therefore it needs את before it",
                "בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם"
            ]},
            {"question": "Translate: וַיִּבְרָא אֱלֹהִים אֶת־הָאָדָם", "steps": [
                "וַיִּבְרָא = and he created",
                "אֱלֹהִים = God (subject)",
                "אֶת־ = direct object marker",
                "הָאָדָם = the man (object)",
                "Result: And God created the man"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is the function of את?", "opts": ["Preposition 'with'", "Direct object marker", "Conjunction 'and'", "Definite article"], "ans": "Direct object marker"},
            {"type": "multiple_choice", "q": "When does את appear before a noun?", "opts": ["Only before indefinite nouns", "Only before definite nouns", "Before all nouns", "Only before verbs"], "ans": "Only before definite nouns"},
            {"type": "classification", "q": "In 'בָּרָא אֱלֹהִים אֵת הַשָּׁמַיִם', what is את doing?", "opts": ["Object marker", "Preposition 'with'", "Relative pronoun", "Not applicable"], "ans": "Object marker"},
            {"type": "classification", "q": "In verse 'אֶת־הָאָרֶץ', the word את indicates:", "opts": ["'the earth' is the subject", "'the earth' is the direct object", "'with the earth'", "'and the earth'"], "ans": "'the earth' is the direct object"},
            {"type": "recall", "q": "What does את mean when it appears before a definite noun?", "ans": "Direct object marker (no English translation)"},
            {"type": "transliteration", "q": "How is את transliterated?", "ans": "et"},
        ],
    },
    {
        "id": "nominal_clauses",
        "title": "Nominal (Verbless) Clauses",
        "category": "grammar",
        "level": 4,
        "description": "Sentences without a verb — 'A is B' patterns",
        "prerequisites": ["vocab_את_0", "vocab_הוא_48"],
        "explanation": """Biblical Hebrew often uses sentences WITHOUT a verb of being (is, are, was, were). These are called nominal clauses or verbless clauses.

Pattern: [Subject] + [Predicate] (no verb needed)

Examples:
• וְהָאָרֶץ הָיְתָה תֹהוּ וָבֹהוּ — "And the earth WAS formless and void" (has היה verb)
• זֶה סֵפֶר — "This IS a book" (NO verb)
• שְׁמוֹ דָּוִד — "His name IS David" (NO verb)
• אֲנִי יְהוָה — "I AM YHWH" (NO verb)

Types of nominal clauses:
1. IDENTIFICATION: "A is B" — זֶה סֵפֶר (this is a book)
2. DESCRIPTION: "A is [adjective]" — הַסֵּפֶר טוֹב (the book is good)
3. EXISTENCE: "There is/are B" — יֵשׁ אֱלֹהִים (there is a God)
4. POSSESSION: "A has B" — לִי סֵפֶר (I have a book = to-me a book)

The verb היה (to be) exists but is used mainly for PAST and FUTURE tense. Present tense uses the verbless pattern.""",
        "key_points": [
            "Biblical Hebrew often omits the verb 'to be' in present tense",
            "Pattern: Subject + Predicate (no verb needed)",
            "Four types: identification, description, existence, possession",
            "Verb היה used for past and future tenses",
            "Context determines the meaning",
        ],
        "worked_examples": [
            {"question": "Translate 'זֶה סֵפֶר' (lit. 'this book')", "steps": [
                "No verb present",
                "Two nouns juxtaposed = nominal clause",
                "Implies 'is': 'This is a book'",
                "זֶה = this, סֵפֶר = book"
            ]},
            {"question": "Why is there no 'is' in 'אֲנִי יְהוָה' (I YHWH)?", "steps": [
                "Nominal clause — no copula needed",
                "אֲנִי = I, יְהוָה = YHWH",
                "Implied 'am': 'I am YHWH'",
                "This is God's standard self-introduction formula"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is a nominal clause?", "opts": ["A sentence with two verbs", "A sentence without a verb", "A sentence with only nouns", "A sentence with only prepositions"], "ans": "A sentence without a verb"},
            {"type": "classification", "q": "Is 'הָאָרֶץ תֹהוּ' a nominal clause?", "opts": ["Yes (no verb)", "No (has verb)", "Maybe"], "ans": "Yes (no verb)"},
            {"type": "recall", "q": "What verb is usually omitted in Hebrew present-tense nominal clauses?", "ans": "to be (was, were, is, are, am)"},
        ],
    },
    {
        "id": "adjective_agreement",
        "title": "Adjective Agreement (Gender & Number)",
        "category": "grammar",
        "level": 4,
        "description": "Adjectives match their noun in gender, number, and definiteness",
        "prerequisites": ["noun_gender", "noun_number"],
        "explanation": """In Biblical Hebrew, adjectives must AGREE with the noun they modify in THREE ways:

1. GENDER: masculine or feminine
2. NUMBER: singular or plural
3. DEFINITENESS: definite (with ה־) or indefinite

Patterns:
• Masculine singular: טוֹב (good) — no special ending
• Feminine singular: טוֹבָה (good) — הָה ending
• Masculine plural: טוֹבִים (good) — ים ending
• Feminine plural: טוֹבוֹת (good) — ות ending

Definiteness: If the noun is definite (has ה־), the adjective must ALSO have ה־:
• סוּס טוֹב — a good horse (indefinite + indefinite)
• הַסּוּס הַטּוֹב — the good horse (definite + definite)
• הַסּוּס טוֹב — THE horse is good (predicate adjective — no article needed!)

Word order: The adjective usually FOLLOWS the noun it modifies.
• אִישׁ טוֹב — a good man (lit. 'man good')""",
        "key_points": [
            "Adjectives match in GENDER: masc טוֹב, fem טוֹבָה",
            "Adjectives match in NUMBER: sg טוֹב, pl טוֹבִים",
            "Adjectives match in DEFINITENESS: הַטּוֹב with ה־ if noun has ה־",
            "Word order: Noun → Adjective (the good man = האיש הטוב)",
            "Predicate adjective (A is good) does NOT take the article",
        ],
        "worked_examples": [
            {"question": "Why is 'the good man' הַאִישׁ הַטּוֹב not הַאִישׁ טוֹב?", "steps": [
                "The noun הָאִישׁ is definite (has ה־)",
                "Attributive adjectives must match definiteness",
                "So adjective also gets ה־: הַטּוֹב",
                "Result: הָאִישׁ הַטּוֹב = the good man"
            ]},
            {"question": "Compare: הָאִישׁ טוֹב vs הָאִישׁ הַטּוֹב", "steps": [
                "הָאִישׁ טוֹב = 'The man is good' (predicate — no article on adj)",
                "הָאִישׁ הַטּוֹב = 'The good man' (attributive — article on adj)",
                "The presence/absence of ה־ on the adjective changes the meaning!"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "How does a Hebrew adjective agree with its noun?", "opts": ["Gender only", "Number only", "Gender, number, AND definiteness", "Gender and number only"], "ans": "Gender, number, AND definiteness"},
            {"type": "classification", "q": "In 'הָאִישׁ הַטּוֹב', is טוֹב attributive or predicate?", "opts": ["Attributive (the good man)", "Predicate (the man is good)"], "ans": "Attributive (the good man)"},
            {"type": "multiple_choice", "q": "Feminine plural of טוֹב (good)?", "opts": ["טוֹבִים", "טוֹבוֹת", "טוֹבָה", "טוֹב"], "ans": "טוֹבוֹת"},
            {"type": "recall", "q": "What are the three agreement features for Hebrew adjectives?", "ans": "Gender, number, and definiteness"},
        ],
    },
    # ── Level 5: Intermediate ──
    {
        "id": "pronominal_suffixes_nouns",
        "title": "Pronominal Suffixes on Nouns",
        "category": "grammar",
        "level": 5,
        "description": "Possessive suffixes attached to nouns: my, your, his, etc.",
        "prerequisites": ["noun_state", "noun_number"],
        "explanation": """In Biblical Hebrew, possessive pronouns are ATTACHED as suffixes to nouns, not written as separate words.

The pattern for a singular noun:
• ךִי/י = my (דְּבָרִי = my word)
• ְךָ = your (ms) (דְּבָרְךָ = your word)
• ֵךְ = your (fs) (דְּבָרֵךְ = your word)
• וֹ = his (דְּבָרוֹ = his word)
• ָהּ = her (דְּבָרָהּ = her word)
• ֵנוּ = our (דְּבָרֵנוּ = our word)
• כֶם = your (mp) (דִּבְרֵיכֶם = your words)
• כֶן = your (fp) (דִּבְרֵיכֶן = your words)
• הֶם/ם = their (m) (דִּבְרֵיהֶם = their words)
• הֶן/ן = their (f) (דִּבְרֵיהֶן = their words)

Important: The noun often changes form when suffixes are added! The construct state or a special 'connective vowel' may appear before the suffix.

For PLURAL nouns, the suffix attaches after the plural ending:
• סוּסַי = my horses (סוּס + pl + my)
• דְּבָרָיו = his words (דָּבָר + pl + his)""",
        "key_points": [
            "Possession expressed with SUFFIXES, not separate words",
            "Singular: my = י/ִי, your = ְךָ/ֵךְ, his = וֹ, her = ָהּ",
            "Plural: our = ֵנוּ, your = כֶם/כֶן, their = הֶם/הֶן",
            "Noun often changes form before suffix (construct-like)",
            "Plural nouns use the plural stem + suffix",
        ],
        "worked_examples": [
            {"question": "Parse 'דְּבָרוֹ' (Devar + o)", "steps": [
                "דְּבָר = construct form of דָּבָר (word)",
                "וֹ = his (3ms suffix)",
                "דְּבָרוֹ = his word"
            ]},
            {"question": "Parse 'סוּסֵינוּ'", "steps": [
                "סוּס = horse",
                "ֵינוּ = our",
                "סוּסֵינוּ = our horse (with connective vowel)"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "How is 'his word' expressed in Hebrew?", "opts": ["דָּבָר שֶׁלּוֹ", "דְּבָרוֹ", "הַדָּבָר שֶׁלּוֹ", "דָּבָר הוּא"], "ans": "דְּבָרוֹ"},
            {"type": "classification", "q": "The suffix וֹ indicates which person?", "opts": ["Your (ms)", "His", "Her", "Our"], "ans": "His"},
            {"type": "multiple_choice", "q": "What happens to the noun when a pronominal suffix is added?", "opts": ["Nothing", "It goes to construct state", "It doubles", "It drops the first letter"], "ans": "It goes to construct state"},
            {"type": "recall", "q": "What is the suffix for 'our' (1cp)?", "ans": "ֵנוּ"},
        ],
    },
    {
        "id": "prepositions_with_suffixes",
        "title": "Prepositions with Pronominal Suffixes",
        "category": "grammar",
        "level": 5,
        "description": "Common prepositions (ל, ב, כ, מ, עַל, אֶל) with attached pronouns",
        "prerequisites": ["pronominal_suffixes_nouns", "preposition_independent"],
        "explanation": """The most common Hebrew prepositions (ל = to/for, ב = in/with, כ = like/as, מ = from) are single letters that ATTACH directly to the following word. When they combine with pronouns, they form special fused forms.

Key prepositions with suffixes:

ל (to/for):
• לִי = to me, לְךָ = to you (m), לָךְ = to you (f), לוֹ = to him, לָהּ = to her
• לָנוּ = to us, לָכֶם = to you (mp), לָהֶם = to them (m), לָהֶן = to them (f)

ב (in/with/by):
• בִּי = in me, בְּךָ = in you, בּוֹ = in him, בָּהּ = in her
• בָּנוּ = in us, בָּכֶם = in you, בָּהֶם = in them

עַל (upon/over):
• עָלַי = upon me, עָלֶיךָ = upon you, עָלָיו = upon him
• עָלֵינוּ = upon us, עֲלֵיהֶם = upon them

אֶל (to/toward):
• אֵלַי = to me, אֵלֶיךָ = to you, אֵלָיו = to him
• אֵלֵינוּ = to us, אֲלֵיהֶם = to them

מִן/מ (from):
• מִמֶּנִּי = from me, מִמְּךָ = from you, מִמֶּנּוּ = from him
• מִמֶּנּוּ = from us, מֵהֶם = from them

Note: These forms are extremely common and must be memorized.""",
        "key_points": [
            "Prepositions fuse with pronouns into single words",
            "Each preposition has its own pattern",
            "ל (lamed) is the most common — לִי, לְךָ, לוֹ, לָהּ",
            "The forms must be memorized — they're not always predictable",
            "These appear constantly in every Hebrew sentence",
        ],
        "worked_examples": [
            {"question": "Parse 'לָהֶם'", "steps": [
                "ל = to/for (preposition)",
                "ָהֶם = them (3mp suffix)",
                "לָהֶם = to them"
            ]},
            {"question": "Parse 'בּוֹ'", "steps": [
                "ב = in/with",
                "וֹ = him (3ms suffix)",
                "בּוֹ = in him / with him"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is 'to me' in Hebrew?", "opts": ["לִי", "לְךָ", "לוֹ", "לָהּ"], "ans": "לִי"},
            {"type": "multiple_choice", "q": "What is 'to him' in Hebrew?", "opts": ["לִי", "לָךְ", "לוֹ", "לָהּ"], "ans": "לוֹ"},
            {"type": "classification", "q": "The form 'בָּנוּ' means:", "opts": ["In him", "In us", "In them", "In you"], "ans": "In us"},
            {"type": "recall", "q": "What is the Hebrew for 'to them' (masc)?", "ans": "לָהֶם"},
        ],
    },
    # ── Level 6: Advanced ──
    {
        "id": "object_suffixes_verbs",
        "title": "Object Suffixes on Verbs",
        "category": "grammar",
        "level": 6,
        "description": "Direct object pronouns attached to verbs: 'he killed him'",
        "prerequisites": ["qal_perfect", "pronominal_suffixes_nouns"],
        "explanation": """In Biblical Hebrew, the direct object pronoun (me, you, him, her, us, them) can be ATTACHED directly to the verb as a suffix. This is extremely common in narrative.

Pattern: [Verb] + [Object Suffix]

Example: שְׁמָרַנִי = שָׁמַר (he kept) + נִי (me) = "he kept me"

Common object suffixes:
• נִי = me
• ְךָ = you (ms)
• ֵךְ = you (fs)
• וּ/הוּ = him
• ָהּ = her
• ָנוּ = us
• כֶם = you (mp)
• ם/הֶם = them (m)
• ן/הֶן = them (f)

Important: The verb form may change slightly before the suffix. For example:
• Perfect 3ms: קָטַל + וּ/הוּ → קְטָלוֹ (he killed him)
• Note the vowel change: qatal → qetalo

A helping vowel (usually וֹ or ־ָה) often appears between the verb and the suffix.""",
        "key_points": [
            "Object pronouns attach directly to verbs",
            "Pattern: Verb + Suffix (e.g., שְׁמָרַנִי = he kept me)",
            "The verb form often changes before the suffix",
            "Very common in Biblical Hebrew narrative",
            "Key suffixes: נִי (me), וּ/הוּ (him), ָהּ (her), ם (them)",
        ],
        "worked_examples": [
            {"question": "Parse 'שְׁמָרַנִי'", "steps": [
                "שָׁמַר = he kept (Qal perfect 3ms)",
                "נִי = me (1cs object suffix)",
                "Verb changes form: שָׁמַר → שְׁמָרַ + נִי",
                "שְׁמָרַנִי = he kept me"
            ]},
            {"question": "Parse 'וַיִּקְטְלֵהוּ'", "steps": [
                "וַיִּקְטֹל = and he killed (wayyiqtol)",
                "ֵהוּ = him (3ms object suffix)",
                "וַיִּקְטְלֵהוּ = and he killed him"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What does the suffix נִי mean on a verb?", "opts": ["Him", "Me", "Us", "Them"], "ans": "Me"},
            {"type": "classification", "q": "In 'שְׁמָרַנִי', what is the suffix?", "opts": ["נִי (me)", "וּ (him)", "ָהּ (her)", "ם (them)"], "ans": "נִי (me)"},
            {"type": "recall", "q": "What is the 3ms object suffix attached to verbs?", "ans": "וּ or הוּ"},
        ],
    },
    {
        "id": "infinitive_construct",
        "title": "Infinitive Construct",
        "category": "grammar",
        "level": 6,
        "description": "The verbal noun — 'to write', 'in the day of', 'by saying'",
        "prerequisites": ["qal_perfect", "prepositions_with_suffixes"],
        "explanation": """The Infinitive Construct is a VERBAL NOUN — it functions like both a verb and a noun. It's one of the most common verb forms in Biblical Hebrew, often used with prepositions like ב, כ, ל.

Patterns:
• Qal: קְטֹל (like "to kill") — vowel pattern: e/o
• With ל: לִקְטֹל = "to kill" (purpose/infinitive)
• With ב: בִּקְטֹל = "in/when killing" (temporal)
• With כ: כִּקְטֹל = "as/when killing" (temporal)
• With מִן/מ: מִקְּטֹל = "from killing"

The infinitive construct can also take:
• A SUBJECT (in construct): "in the king's coming" = בְּבוֹא הַמֶּלֶךְ
• An OBJECT (with את): "in keeping the law" = בִּשְׁמֹר אֶת־הַתּוֹרָה
• SUFFIXES (possessive): "in his coming" = בְּבוֹאוֹ

This form is EXTREMELY common — about 50% of all verb uses in narrative are infinitive construct.""",
        "key_points": [
            "A verbal noun — like English 'to write' or 'writing'",
            "Often used with prepositions: ל (to), ב (in/when), כ (as/when)",
            "Qal pattern: קְטֹל",
            "Can take subjects, objects, and possessive suffixes",
            "~50% of all verb uses in narrative",
            "Critical for reading fluency",
        ],
        "worked_examples": [
            {"question": "Parse 'לִשְׁמֹר'", "steps": [
                "ל = to (preposition)",
                "שְׁמֹר = infinitive construct of שָׁמַר (to keep)",
                "לִשְׁמֹר = to keep / in order to keep"
            ]},
            {"question": "Parse 'בְּבוֹא הַמֶּלֶךְ'", "steps": [
                "בְּ = in/when (preposition)",
                "בוֹא = infinitive construct of בּוֹא (to come)",
                "הַמֶּלֶךְ = the king (subject of infinitive)",
                "בְּבוֹא הַמֶּלֶךְ = when the king came/comes"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is an infinitive construct?", "opts": ["A past tense verb", "A verbal noun", "A future tense verb", "An adjective"], "ans": "A verbal noun"},
            {"type": "classification", "q": "In 'לִשְׁמֹר', what does the ל prefix indicate?", "opts": ["Past tense", "To/in order to (infinitive)", "Definite article", "Conjunction 'and'"], "ans": "To/in order to (infinitive)"},
            {"type": "multiple_choice", "q": "What is the Qal infinitive construct pattern?", "opts": ["קָטַל", "קְטֹל", "קֹטֵל", "יִקְטֹל"], "ans": "קְטֹל"},
            {"type": "recall", "q": "What preposition is used before the infinitive to mean 'to/in order to'?", "ans": "ל"},
        ],
    },
    {
        "id": "infinitive_absolute",
        "title": "Infinitive Absolute",
        "category": "grammar",
        "level": 6,
        "description": "The emphatic verbal form — 'you shall surely die'",
        "prerequisites": ["qal_perfect"],
        "explanation": """The Infinitive Absolute is a special verb form used for EMPHASIS. It usually appears right before a finite verb of the same root to intensify or strengthen its meaning.

Pattern: [INFINITIVE ABSOLUTE] + [Finite Verb]

Example: מוֹת תָּמוּת = "You shall surely die" (lit. 'dying you will die')
• מוֹת = infinitive absolute of מות (to die)
• תָּמוּת = you will die (imperfect)
• Together: STRONG emphasis on the action

Qal infinitive absolute pattern: קָטוֹל or קָטֹל
• שָׁמוֹר תִּשְׁמְרוּן = "You shall surely keep"

It can also function as:
• An IMPERATIVE: זָכוֹר = "Remember!" (Deut 5:12 — the Exodus command)
• A GERUND: "keeping the law" (rare)
• A CONTINUOUS action: הָלוֹךְ וְנָסוֹעַ = "traveling and journeying"

The infinitive absolute is a hallmark of Biblical Hebrew style and appears frequently in legal texts, narratives, and prophecies.""",
        "key_points": [
            "Used for EMPHASIS before a finite verb of the same root",
            "Qal pattern: קָטוֹל or קָטֹל",
            "מוֹת תָּמוּת = 'you shall surely die'",
            "Can function as an imperative (זָכוֹר = Remember!)",
            "Very common in legal/covenant language",
        ],
        "worked_examples": [
            {"question": "Parse 'מוֹת תָּמוּת'", "steps": [
                "מוֹת = infinitive absolute of מות (to die) — emphatic",
                "תָּמוּת = you will die (Qal imperfect 2ms)",
                "Together: 'you shall surely die' (emphatic)",
                "This is the famous phrase from Gen 2:17"
            ]},
            {"question": "Parse 'שָׁמוֹר תִּשְׁמְרוּן'", "steps": [
                "שָׁמוֹר = infinitive absolute of שׁמר (to keep) — emphatic",
                "תִּשְׁמְרוּן = you (plural) will keep",
                "Together: 'you shall surely keep' (strong command)"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is the function of infinitive absolute?", "opts": ["Past tense", "Emphasis/intensification", "Future tense", "Question"], "ans": "Emphasis/intensification"},
            {"type": "classification", "q": "In 'מוֹת תָּמוּת', what does מוֹת add?", "opts": ["Past meaning", "Emphasis (surely)", "Negation", "Question"], "ans": "Emphasis (surely)"},
            {"type": "multiple_choice", "q": "What is the Qal infinitive absolute pattern?", "opts": ["קָטַל", "קְטֹל", "קָטוֹל", "קֹטֵל"], "ans": "קָטוֹל"},
            {"type": "recall", "q": "In what type of text does infinitive absolute appear most often?", "ans": "Legal/covenant texts and narratives"},
        ],
    },
    {
        "id": "commands_jussive",
        "title": "Commands, Jussive, & Cohortative",
        "category": "grammar",
        "level": 6,
        "description": "Expressing commands, wishes, and self-exhortation",
        "prerequisites": ["qal_imperfect", "qal_imperative"],
        "explanation": """Biblical Hebrew has three main ways to express commands and wishes:

1. IMPERATIVE — direct command (2nd person only)
   • קְטֹל = "Kill!" (ms)
   • קִטְלִי = "Kill!" (fs)
   • קִטְלוּ = "Kill!" (mp)

2. JUSSIVE — indirect command/wish (3rd person, often with ו)
   • יִקְטֹל = "Let him kill" / "May he kill"
   • The jussive often looks identical to the imperfect
   • Sometimes distinguished by vowel shortening: יָקוּם → יָקֹם
   • A negative jussive uses אַל: אַל־תִּקְטֹל = "Do not kill"

3. COHORTATIVE — self-encouragement / "let me / let us" (1st person)
   • אֶקְטְלָה = "Let me kill" / "I will kill"
   • נִקְטְלָה = "Let us kill"
   • Marked by the הָה suffix on the imperfect

The negative of commands uses:
• לֹא + imperfect = "You shall not" (strong prohibition, Decalogue)
• אַל + imperfect/jussive = "Do not" (softer prohibition)""",
        "key_points": [
            "Imperative = direct command (2nd person only)",
            "Jussive = let/may (3rd person, often subtle distinction from imperfect)",
            "Cohortative = let me/us (1st person, marked by הָה ending)",
            "Negative commands: לֹא (strong) vs אַל (soft)",
            "Vowel shortening can distinguish jussive from imperfect",
        ],
        "worked_examples": [
            {"question": "Parse 'קְטֹל' as an imperative", "steps": [
                "קְטֹל = Qal imperative 2ms",
                "Direct command: 'Kill!'",
                "No subject pronoun needed — it's built into the form"
            ]},
            {"question": "Distinguish 'יִקְטֹל' (imperfect) vs 'יִקְטֹל' (jussive)", "steps": [
                "Both forms are identical for strong verbs",
                "Context determines meaning",
                "יִקְטֹל as imperfect: 'he will kill' (indicative)",
                "יִקְטֹל as jussive: 'let him kill' / 'may he kill'"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What person does the imperative appear in?", "opts": ["1st person", "2nd person only", "3rd person", "All persons"], "ans": "2nd person only"},
            {"type": "classification", "q": "The cohortative ending הָה indicates:", "opts": ["Past tense", "Self-exhortation (let me/us)", "Question", "Negation"], "ans": "Self-exhortation (let me/us)"},
            {"type": "multiple_choice", "q": "What is the negative particle for a softer prohibition ('do not')?", "opts": ["לֹא", "אַל", "הֲ", "כִּי"], "ans": "אַל"},
            {"type": "recall", "q": "What suffix marks the cohortative in 1st person?", "ans": "ָה (cohortative he)"},
        ],
    },
    {
        "id": "conditional_sentences",
        "title": "Conditional Sentences (If...Then)",
        "category": "grammar",
        "level": 6,
        "description": "Patterns for 'if...then' clauses in Biblical Hebrew",
        "prerequisites": ["qal_imperfect", "nominal_clauses"],
        "explanation": """Biblical Hebrew expresses conditional sentences ('if...then') in several ways:

1. אִם + [protasis] + [apodosis]
   • אִם = "if" (most common)
   • Both clauses usually in the imperfect or perfect
   • Example: אִם־תִּשְׁמַע... תִּחְיֶה = "If you listen... you will live"

2. כִּי + [protasis] + [apodosis]
   • כִּי = "if/when/for" (ambiguous — context determines)
   • Example: כִּי־תָבוֹא... תֹּאכַל = "When/If you come... you will eat"

3. לוּ / לוּלֵא + [protasis] + [apodosis]
   • Contrafactual: "If only / If not" (unreal condition)
   • Example: לוּ־שָׁמַעְתָּ = "If only you had listened..."
   • לוּלֵא = "if not" / "unless"

4. No conditional particle (asyndetic)
   • Two clauses simply juxtaposed
   • Context implies condition

The verb tenses in conditionals:
• Real condition (likely): protasis + apodosis in imperfect
• Unreal condition (unlikely/contrary to fact): both clauses in perfect or with לוּ""",
        "key_points": [
            "אִם = if (most common conditional particle)",
            "כִּי = if/when/for (ambiguous)",
            "לוּ / לוּלֵא = if only / if not (contrafactual)",
            "Real condition: imperfect in both clauses",
            "Unreal condition: perfect or לוּ construction",
            "Sometimes no particle — context implies the condition",
        ],
        "worked_examples": [
            {"question": "Parse 'אִם־תִּשְׁמַע... תִּחְיֶה'", "steps": [
                "אִם = if (conditional particle)",
                "תִּשְׁמַע = you will listen / you listen (imperfect)",
                "תִּחְיֶה = you will live (imperfect, apodosis)",
                "Full: 'If you listen, you will live'"
            ]},
            {"question": "Parse 'לוּלֵא יְהוָה... אָז...'", "steps": [
                "לוּלֵא = if not / unless (contrafactual)",
                "יְהוָה = YHWH (subject)",
                "אָז = then (apodosis marker)",
                "Full: 'Unless YHWH... then...' (Psalm 124)"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "Which particle is the most common 'if' in Biblical Hebrew?", "opts": ["כִּי", "אִם", "לוּ", "אָז"], "ans": "אִם"},
            {"type": "classification", "q": "לוּלֵא introduces what kind of condition?", "opts": ["Real (likely)", "Contrafactual (unreal)", "Future (possible)", "Past (certain)"], "ans": "Contrafactual (unreal)"},
            {"type": "recall", "q": "What does אִם mean?", "ans": "if"},
        ],
    },
    {
        "id": "numeral_agreement",
        "title": "Numeral Agreement (Gender Reversal)",
        "category": "grammar",
        "level": 6,
        "description": "Numbers 3-10 show GENDER REVERSAL with the noun they modify",
        "prerequisites": ["noun_gender", "noun_number"],
        "explanation": """Biblical Hebrew has a unique feature: numbers 3 through 10 show GENDER REVERSAL with the noun they modify.

The rule:
• A MASCULINE number modifies a FEMININE noun
• A FEMININE number modifies a MASCULINE noun

This is the OPPOSITE of what you might expect!

Examples:
• 3 MASCULINE: שְׁלֹשָׁה בָנִים = THREE SONS (masculine noun → feminine number form)
• 3 FEMININE: שָׁלֹשׁ בָּנוֹת = THREE DAUGHTERS (feminine noun → masculine number form)

Number forms:
| Number | Masculine Form | Feminine Form |
|--------|---------------|---------------|
| 3 | שְׁלֹשָׁה | שָׁלֹשׁ |
| 4 | אַרְבָּעָה | אַרְבַּע |
| 5 | חֲמִשָּׁה | חָמֵשׁ |
| 6 | שִׁשָּׁה | שֵׁשׁ |
| 7 | שִׁבְעָה | שֶׁבַע |
| 8 | שְׁמוֹנָה | שְׁמֹנֶה |
| 9 | תִּשְׁעָה | תֵּשַׁע |
| 10 | עֲשָׂרָה | עֶשֶׂר |

Exception: Numbers 1-2 behave normally (agree in gender). Numbers 11+ also follow a different pattern.""",
        "key_points": [
            "Numbers 3-10 show gender REVERSAL with the noun",
            "Masculine noun → feminine number (e.g., שְׁלֹשָׁה בָנִים)",
            "Feminine noun → masculine number (e.g., שָׁלֹשׁ בָּנוֹת)",
            "Numbers 1-2 agree normally (no reversal)",
            "This is one of the most distinctive features of Hebrew grammar",
        ],
        "worked_examples": [
            {"question": "Why is 3 sons = שְׁלֹשָׁה בָנִים (not שָׁלֹשׁ)?", "steps": [
                "בָנִים = sons (MASCULINE plural)",
                "Number must show 'reversed' gender",
                "Masculine noun → use feminine number form",
                "שְׁלֹשָׁה is the feminine form of 3"
            ]},
            {"question": "Why is 3 daughters = שָׁלֹשׁ בָּנוֹת (not שְׁלֹשָׁה)?", "steps": [
                "בָּנוֹת = daughters (FEMININE plural)",
                "Feminine noun → use masculine number form",
                "שָׁלֹשׁ is the masculine form of 3"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What happens to numbers 3-10 in Hebrew?", "opts": ["They stay the same", "They reverse gender with the noun", "They become plural", "They drop the final letter"], "ans": "They reverse gender with the noun"},
            {"type": "classification", "q": "For 'שְׁלֹשָׁה בָנִים', is the number masculine or feminine?", "opts": ["Masculine (matching 'sons')", "Feminine (opposite of 'sons')"], "ans": "Feminine (opposite of 'sons')"},
            {"type": "recall", "q": "What is the feminine form of 3 (שלושה)?", "ans": "שָׁלֹשׁ"},
        ],
    },
    {
        "id": "cognate_accusative",
        "title": "Cognate Accusative",
        "category": "grammar",
        "level": 7,
        "description": "A verb paired with a noun of the same root for emphasis",
        "prerequisites": ["qal_perfect", "direct_object_marker"],
        "explanation": """The Cognate Accusative (also called Internal Object) is when a verb is followed by a noun from the SAME ROOT. This is a common Hebrew idiom for emphasis.

Pattern: [Verb] + [Cognate Noun (same root)]

Examples:
• חָלַם חֲלוֹם = "He dreamed a dream" (both from חלם)
• שָׁמַר שִׁמְרָה = "He kept the keep" (both from שׁמר)
• בֵּרַךְ בְּרָכָה = "He blessed a blessing" (both from ברך)

This is similar to the English idiom "he slept the sleep of death" or "she lived her life."

The cognate noun is often accompanied by an adjective:
• חָלַם חֲלוֹם גָּדוֹל = "He dreamed a GREAT dream"
• יָרֵא יִרְאָה גְדוֹלָה = "He feared a GREAT fear"

The effect is to INTENSIFY or SPECIFY the action of the verb.""",
        "key_points": [
            "Verb + noun from same root for emphasis",
            "חָלַם חֲלוֹם = 'he dreamed a dream' (both from חלם)",
            "Intensifies or specifies the action",
            "Often includes an adjective for further description",
            "Common in Hebrew narrative and poetry",
        ],
        "worked_examples": [
            {"question": "Parse 'חָלַם חֲלוֹם'", "steps": [
                "חָלַם = he dreamed (Qal perfect 3ms)",
                "חֲלוֹם = a dream (noun from חלם)",
                "Together: 'he dreamed a dream' (emphatic)",
                "The noun adds emphasis/specificity to the verb"
            ]},
            {"question": "Parse 'יָרֵא יִרְאָה גְדוֹלָה'", "steps": [
                "יָרֵא = he feared (Qal perfect)",
                "יִרְאָה = fear (cognate noun)",
                "גְדוֹלָה = great (adjective modifying the noun)",
                "Full: 'He feared a great fear' = 'He was very afraid'"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is a cognate accusative?", "opts": ["Two verbs in a row", "A verb + noun from the same root", "A noun with two adjectives", "A verb with two objects"], "ans": "A verb + noun from the same root"},
            {"type": "classification", "q": "Does 'חָלַם חֲלוֹם' (dreamed a dream) use cognate accusative?", "opts": ["Yes", "No"], "ans": "Yes"},
            {"type": "recall", "q": "What is the purpose of a cognate accusative?", "ans": "To intensify or specify the action of the verb"},
        ],
    },
    {
        "id": "emphatic_structures",
        "title": "Emphatic Structures (Word Order Fronting)",
        "category": "grammar",
        "level": 7,
        "description": "Fronting words to the beginning of a sentence for emphasis",
        "prerequisites": ["word_order", "nominal_clauses"],
        "explanation": """While the usual Hebrew word order is VERB-SUBJECT-OBJECT (VSO), speakers often front (move to the beginning) a word for emphasis.

Examples of fronting:

1. OBJECT fronting (for contrast/emphasis):
   • Normal: וַיִּקְרָא אֱלֹהִים לָאוֹר יוֹם
     "God called the light 'day'"
   • Fronted: לָאוֹר קָרָא אֱלֹהִים יוֹם
     "THE LIGHT God called 'day'" (emphasis on light)

2. ADVERB fronting:
   • Normal: וַיִּשְׁכַּן יִשְׂרָאֵל בַּאֲרָצוֹת
     "Israel dwelt in the lands"
   • Fronted: בַּאֲרָצוֹת שָׁכַן יִשְׂרָאֵל
     "IN THE LANDS Israel dwelt" (emphasis on location)

3. INFINITIVE ABSOLUTE fronting:
   • בָּרֵךְ אֲבָרֶכְךָ = "I will surely bless you" (Gen 22:17)
   • The infinitive absolute before the finite verb

4. PRONOMINAL SUBJECT fronting (for contrast):
   • אֲנִי יְהוָה = "I am YHWH" (emphasizes 'I')
   • The pronoun אֲנִי is not normally needed (verb already marks subject)""",
        "key_points": [
            "Normal VSO word order can be broken for emphasis",
            "Fronted elements: object, adverb, infinitive, pronoun",
            "Fronting signals contrast, focus, or intensity",
            "Very common in poetry and prophecy",
            "Critical for accurate reading comprehension",
        ],
        "worked_examples": [
            {"question": "Compare normal vs fronted: 'לָאוֹר קָרָא אֱלֹהִים יוֹם'", "steps": [
                "Normal VSO: וַיִּקְרָא אֱלֹהִים לָאוֹר יוֹם",
                "Fronted: לָאוֹר קָרָא אֱלֹהִים יוֹם",
                "The object לָאוֹר (the light) is fronted for emphasis",
                "Effect: 'It was THE LIGHT that God called \"day\"'"
            ]},
            {"question": "Why is אֲנִי used in 'אֲנִי יְהוָה'?", "steps": [
                "The verb is first person singular (implied by form)",
                "אֲנִי = I (explicit pronoun) adds emphasis",
                "Effect: 'I, YHWH, am speaking' / 'I am YHWH'",
                "Common in prophetic speech: 'Thus says YHWH'"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is fronting in Hebrew?", "opts": ["Moving a word to the end", "Moving a word to the beginning for emphasis", "Adding a prefix", "Removing a word"], "ans": "Moving a word to the beginning for emphasis"},
            {"type": "classification", "q": "Does 'לָאוֹר קָרָא אֱלֹהִים' have fronting?", "opts": ["Yes (object fronted)", "No (normal VSO)"], "ans": "Yes (object fronted)"},
            {"type": "recall", "q": "What is the normal Hebrew word order?", "ans": "VSO (Verb-Subject-Object)"},
        ],
    },
    {
        "id": "waw_relative",
        "title": "Waw Relative (Asher + Resumption)",
        "category": "grammar",
        "level": 7,
        "description": "Relative clauses with אשר and resumptive pronouns",
        "prerequisites": ["relative_clause", "direct_object_marker"],
        "explanation": """Relative clauses in Biblical Hebrew are introduced by אֲשֶׁר (who/which/that) and often contain a RESUMPTIVE PRONOUN — a pronoun that refers back to the antecedent within the relative clause.

Pattern: [Antecedent] + [אֲשֶׁר] + [Clause with resumptive pronoun]

Examples:
• הָאִישׁ אֲשֶׁר דִּבַּרְתִּי אֵלָיו
  = "The man that I spoke TO HIM"
  (אֵלָיו = 'to him' resumes the antecedent הָאִישׁ)

• הַסֵּפֶר אֲשֶׁר קְרָאתִיו
  = "The book that I read IT"
  (וּ/הוּ = 'it' as object suffix resumes הַסֵּפֶר)

Sometimes אֲשֶׁר is omitted:
• הָאִישׁ דִּבַּרְתִּי אֵלָיו
  = "The man I spoke to him" (no אשר, but still has resumptive pronoun)

Key: English drops the resumptive pronoun ('the man THAT I spoke to ___'), but Hebrew KEEPS it.""",
        "key_points": [
            "Relative clauses use אֲשֶׁר + resumptive pronoun",
            "The resumptive pronoun refers back to the antecedent",
            "English drops the pronoun, Hebrew keeps it",
            "Sometimes אֲשֶׁר can be omitted (asyndetic)",
            "Critical for understanding complex sentences",
        ],
        "worked_examples": [
            {"question": "Parse 'הָאִישׁ אֲשֶׁר דִּבַּרְתִּי אֵלָיו'", "steps": [
                "הָאִישׁ = the man (antecedent)",
                "אֲשֶׁר = who/that (relative particle)",
                "דִּבַּרְתִּי = I spoke",
                "אֵלָיו = to him (resumptive pronoun)",
                "Full: 'the man that I spoke to him' = 'the man I spoke to'"
            ]},
            {"question": "Why is there an extra 'him' in the Hebrew?", "steps": [
                "English: 'the man I spoke to' (no pronoun)",
                "Hebrew: 'the man that I spoke to HIM' (resumptive pronoun retained)",
                "The resumptive pronoun is GRAMMATICALLY REQUIRED in Hebrew",
                "Never drop it when translating into Hebrew"
            ]},
        ],
        "practice": [
            {"type": "multiple_choice", "q": "What is a resumptive pronoun?", "opts": ["A pronoun at the start of a sentence", "A pronoun that refers back to the antecedent in a relative clause", "A reflexive pronoun", "An interrogative pronoun"], "ans": "A pronoun that refers back to the antecedent in a relative clause"},
            {"type": "classification", "q": "In 'הָאִישׁ אֲשֶׁר דִּבַּרְתִּי אֵלָיו', what is אֵלָיו?", "opts": ["Subject", "Resumptive pronoun", "Negative particle", "Preposition"], "ans": "Resumptive pronoun"},
            {"type": "recall", "q": "Which particle introduces most relative clauses in Hebrew?", "ans": "אֲשֶׁר"},
        ],
    },
]


def main():
    conn = sqlite3.connect(str(MEM_DB))
    conn.execute("PRAGMA foreign_keys=OFF")

    # Ensure tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hebrew_nodes (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, level INTEGER NOT NULL DEFAULT 4,
            category TEXT NOT NULL DEFAULT 'grammar', description TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS hebrew_lessons (
            node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
            content_json TEXT DEFAULT '{}', version INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS hebrew_practice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            question_type TEXT NOT NULL, question_text TEXT NOT NULL,
            options_json TEXT DEFAULT '', correct_answer TEXT NOT NULL,
            difficulty REAL DEFAULT 0.5, explanation TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS hebrew_edges (
            source_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            target_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
            edge_type TEXT DEFAULT 'prerequisite');
    """)

    new_nodes = 0
    new_items = 0
    new_edges = 0

    for lesson in GRAMMAR_LESSONS:
        lid = lesson["id"]

        # Skip if practice items already exist for this node
        existing = conn.execute("SELECT id FROM hebrew_practice_items WHERE node_id=? LIMIT 1", (lid,)).fetchone()
        if existing:
            print(f"  SKIP {lid}: practice items already exist")
            continue

        # Create node
        conn.execute(
            "INSERT INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, ?, ?)",
            (lid, lesson["title"], lesson["level"], lesson["category"], lesson["description"])
        )
        new_nodes += 1

        # Create lesson content
        content = {
            "node_id": lid,
            "title": lesson["title"],
            "glyph": lid,
            "category": lesson["category"],
            "description": lesson["description"],
            "explanation": lesson["explanation"],
            "key_points": lesson["key_points"],
            "worked_examples": lesson["worked_examples"],
        }
        conn.execute(
            "INSERT INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
            (lid, json.dumps(content, ensure_ascii=False))
        )

        # Create practice items
        for item in lesson["practice"]:
            opts = json.dumps(item.get("opts", []), ensure_ascii=False) if item.get("opts") else ""
            conn.execute(
                "INSERT INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (lid, item["type"], item["q"], opts, item["ans"], 0.5, "")
            )
            new_items += 1

        # Create prerequisite edges
        for pid in lesson.get("prerequisites", []):
            # Check if prerequisite exists
            exists = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (pid,)).fetchone()
            if exists:
                edge_exists = conn.execute(
                    "SELECT 1 FROM hebrew_edges WHERE source_id=? AND target_id=?",
                    (pid, lid)
                ).fetchone()
                if not edge_exists:
                    conn.execute(
                        "INSERT INTO hebrew_edges (source_id, target_id, edge_type) VALUES (?, ?, 'prerequisite')",
                        (pid, lid)
                    )
                    new_edges += 1

        print(f"  CREATED {lid}: {lesson['title']} (L{lesson['level']}, {len(lesson['practice'])} items)")

    conn.commit()
    conn.close()

    print(f"\n✓ Done! Created {new_nodes} new grammar lessons, {new_items} practice items, {new_edges} prerequisite edges")

    # Summary
    conn2 = sqlite3.connect(str(MEM_DB))
    total = conn2.execute("SELECT COUNT(*) FROM hebrew_nodes WHERE category='grammar'").fetchone()[0]
    items_total = conn2.execute("SELECT COUNT(*) FROM hebrew_practice_items").fetchone()[0]
    print(f"  Total grammar nodes: {total}")
    print(f"  Total practice items: {items_total}")
    conn2.close()


if __name__ == '__main__':
    main()
