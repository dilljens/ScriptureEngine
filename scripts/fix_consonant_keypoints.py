#!/usr/bin/env python3
"""Add meaningful key points to all consonant, verb, noun, and remaining grammar lessons.

Replaces the generic "Key concept in X" / "Review the explanation above" fallback.
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

CONSONANT_KEY_POINTS = {
    "aleph": ["Silent letter — glottal stop / vowel carrier", "First letter of the aleph-bet",
              "Numerical value: 1", "Cannot take dagesh forte"],
    "bet": ["B sound with dagesh (בּ), V sound without (ב)", 
            "One of the six Begadkefat letters",
            "Numerical value: 2", "As prefix means 'in/with/by'"],
    "gimel": ["G sound like 'garden'", "One of the Begadkefat letters (rare soft form)",
              "Numerical value: 3", "Third letter of the aleph-bet"],
    "dalet": ["D sound with dagesh, soft 'dh' without", "One of the Begadkefat letters",
              "Numerical value: 4", "Similar shape to Resh (ר)"],
    "he": ["H sound, often silent at end of word", "Definite article prefix: הַ (ha)",
           "Numerical value: 5", "Feminine noun ending in some words"],
    "vav": ["V sound; also a vowel letter (וֹ=o, וּ=u)", "Conjunction prefix meaning 'and'",
            "Numerical value: 6", "Vav-consecutive is key to biblical narrative"],
    "zayin": ["Z sound like 'zebra'", "Numerical value: 7",
              "Seventh letter", "One of the simpler sounds for English speakers"],
    "chet": ["Guttural CH sound (like Bach)", "One of the gutturals (אהחע)",
             "Numerical value: 8", "Affects vowel behavior in grammar"],
    "tet": ["Emphatic T sound", "One of the emphatic consonants (ט צ ק)",
            "Numerical value: 9", "Distinct from Tav (ת) — harder, more back in throat"],
    "yod": ["Y sound; used as vowel letter (i/e)", "Suffix meaning 'my' (־י)",
            "Numerical value: 10", "Smallest letter in the alphabet"],
    "kaf": ["K sound with dagesh, KH (Bach) without", "Begadkefat letter",
            "Numerical value: 20", "Has final form (ך) at end of words"],
    "kaf_final": ["Final form of Kaf — used only at end of words",
                  "Same KH sound as Kaf without dagesh",
                  "One of five final-form letters (ך ם ן ף ץ)",
                  "Extends below the baseline"],
    "lamed": ["L sound", "Tallest letter — rises above the line",
              "Numerical value: 30", "As prefix means 'to' or 'for'"],
    "mem": ["M sound", "As prefix can mean 'from' (מִ)",
            "Numerical value: 40", "Has closed final form (ם)"],
    "mem_final": ["Closed box shape (ם) — final form of Mem",
                  "Used only at end of words",
                  "One of five final-form letters",
                  "Same M sound as regular Mem"],
    "nun": ["N sound", "Frequently drops/assimilates in weak verbs (I-Nun)",
            "Numerical value: 50", "Has final form (ן) extending below line"],
    "nun_final": ["Extends below baseline (ן) — final form of Nun",
                  "Used only at end of words",
                  "One of five final-form letters",
                  "Same N sound as regular Nun"],
    "samekh": ["S sound — like English 's'", "Round shape with dot in center",
               "Numerical value: 60", "Same sound as Sin (שׂ) — confusable"],
    "ayin": ["Guttural sound — voiced pharyngeal", "One of the gutturals (אהחע)",
             "Numerical value: 70", "Often silent in modern Hebrew pronunciation"],
    "pe": ["P sound with dagesh (פּ), F sound without (פ)", "One of the Begadkefat letters",
           "Numerical value: 80", "Has final form (ף) with curved top"],
    "pe_final": ["Hook-shaped final form (ף) — final form of Pe",
                 "Used only at end of words",
                 "One of five final-form letters",
                 "Same F sound as Pe without dagesh"],
    "tsade": ["TS sound like 'cats'", "One of the emphatic consonants",
              "Numerical value: 90", "Has final form (ץ) extending below line"],
    "tsade_final": ["Final form (ץ) — extends below baseline",
                    "Used only at end of words",
                    "One of five final-form letters",
                    "Same TS sound as regular Tsade"],
    "qof": ["Q sound — emphatic K pronounced farther back", "One of the emphatic consonants",
            "Numerical value: 100", "Distinct from Kaf (כ)"],
    "resh": ["R sound — like English 'r'", "Resists gemination (no dagesh forte)",
             "Numerical value: 200", "Similar shape to Dalet (ד)"],
    "shin": ["SH sound (right dot: שׁ)", "Dot position determines SH vs S",
             "Numerical value: 300", "Sin (שׂ) with left dot = S sound"],
    "sin": ["S sound (left dot: שׂ)", "Looks identical to Shin — only dot differs",
            "Same sound as Samekh (ס)", "Distinguish by dot position: right=SH, left=S"],
    "tav": ["T sound with dagesh, TH (through) without", "One of the Begadkefat letters",
            "Numerical value: 400", "Last letter of the aleph-bet"],
}

# Also add key points for verb binyan lessons
VERB_KEY_POINTS = {
    "binyan_intro": [
        "Seven binyanim (verb patterns) in Hebrew",
        "Each adds a nuance: active, passive, intensive, causative",
        "Qal = simple active (most common)",
        "Patterns are predictable and follow templates",
    ],
    "qal_perfect": [
        "Completed action — like past tense in English",
        "Uses SUFFIXES to mark person/gender/number",
        "3ms is the dictionary form (no suffix)",
        "Pattern: Cā-CaC (3ms), add suffixes for others",
    ],
    "qal_imperfect": [
        "Incomplete/future action",
        "Uses PREFIXES (א, ת, י, נ) to mark person",
        "3ms: יִכְתֹּב (he will write)",
        "Often combined with vav-consecutive for past narrative",
    ],
    "qal_imperative": [
        "Command form — 2nd person only",
        "Based on the imperfect without the prefix",
        "2ms: כְּתֹב (write!), 2fs: כִּתְבִי",
        "Negative commands use אַל + imperfect",
    ],
    "qal_infinitive": [
        "'To' form: לִכְתֹּב (to write)",
        "Always preceded by ל prefix",
        "Also used with ב (when), כ (as), מ (from)",
        "Extremely common in narrative (~50% of verb uses)",
    ],
    "qal_participle": [
        "Verbal adjective: active (כֹּתֵב) vs passive (כָּתוּב)",
        "Declines like an adjective (gender + number)",
        "Can function as a noun ('one who writes')",
        "Passive participle often becomes an adjective",
    ],
    "niphal": [
        "Passive/reflexive of Qal",
        "Marked by נ (nun) prefix",
        "Pattern: נִכְתַּב (it was written)",
        "Also used for simple reflexive: נִשְׁמַר (he guarded himself)",
    ],
    "piel": [
        "Intensive active — emphasizes intensity or repetition",
        "Marked by dagesh forte in middle root letter",
        "Pattern: כִּתֵּב (he wrote extensively)",
        "Often used for verbs with a 'strengthened' meaning",
    ],
    "pual": [
        "Intensive passive of Piel",
        "Has Qibbus (u) vowel under first letter",
        "Pattern: כֻּתַּב (it was written extensively)",
        "Dagesh forte in middle root letter",
    ],
    "hiphil": [
        "Causative active — 'to cause X to do Y'",
        "Marked by ה (he) prefix",
        "Pattern: הִכְתִּיב (he caused to write / dictated)",
        "Characteristic 'i' vowel pattern",
    ],
    "hophal": [
        "Causative passive of Hiphil",
        "Pattern: הָכְתַּב (it was caused to be written)",
        "Has Qamats under the prefix",
        "Dagesh forte in second root letter",
    ],
    "hithpael": [
        "Reflexive — action done to/for oneself",
        "Pattern: הִתְכַּתֵּב (he corresponded)",
        "Marked by הִתְ prefix",
        "Dagesh forte in middle root letter",
    ],
    "weak_guttural": [
        "I-Guttural: first root letter is guttural (אהחע)",
        "Gutturals affect prefix vowels",
        "Prefix takes patah instead of sheva",
        "Example: עָמַד → יַעֲמֹד (he will stand)",
    ],
    "weak_nun": [
        "I-Nun: first root letter is נ",
        "Nun assimilates into next letter with dagesh forte",
        "Example: נָתַן → יִתֵּן (he will give)",
        "Predictable pattern — nun disappears in prefix forms",
    ],
    "weak_he": [
        "III-He: third root letter is ה",
        "Final he is lost or becomes yod-like in prefix forms",
        "Example: בָּנָה → יִבְנֶה (he will build)",
        "Also called 'Lamed-He' verbs",
    ],
    "weak_hollow": [
        "II-Vav/Yod: middle root letter is ו or י",
        "Middle radical disappears in many forms",
        "Example: קוּם → יָקוּם (he will arise)",
        "Vav reappears in some forms — hollow pattern",
    ],
    "weak_double": [
        "Double Ayin: 2nd and 3rd root letters are identical",
        "Often merge with dagesh forte",
        "Example: סָבַב (he turned)",
        "Follow distinctive but regular patterns",
    ],
}

SYLLABLE_KEY_POINTS = {
    "syllable_basics": [
        "Every syllable built around a vowel",
        "Basic patterns: CV (open) and CVC (closed)",
        "Every syllable must begin with a consonant",
        "Silent sheva = syllable end; vocal sheva = start",
    ],
    "syllable_open": [
        "Open syllable ends with a vowel (CV)",
        "Always has a long vowel or vocal sheva",
        "Example: בָּ (bā) — Bet + Qamats",
        "Cannot end with a consonant",
    ],
    "syllable_closed": [
        "Closed syllable ends with a consonant (CVC)",
        "Usually has a short vowel",
        "Example: בַּת (bat) — Bet + Patah + Tav",
        "Most Hebrew syllables in prose are closed",
    ],
    "syllable_stress": [
        "Most words stressed on last syllable (ultima)",
        "Stress marked by cantillation accent",
        "Penultima stress is less common but can change meaning",
        "Example: בָּ֫נוּ (we came) vs בָּנ֫וּ (they built)",
    ],
    "syllable_division": [
        "Each vowel = one syllable",
        "Silent sheva = end of a syllable",
        "Vocal sheva = start of a new syllable",
        "Example: בְּרֵאשִׁית = בְּ·רֵ·א·שִׁית (4 syllables)",
    ],
}

NOUN_KEY_POINTS = {
    "noun_gender": [
        "Every noun is masculine or feminine (grammatical gender)",
        "Feminine nouns typically end in ־ָה (qamats-he) or ־ֶת/־ת",
        "Masculine nouns have no fixed ending",
        "Gender affects agreement with adjectives, verbs, pronouns",
    ],
    "noun_number": [
        "Three numbers: singular, plural, and dual (for pairs)",
        "Masculine plural: ־ִים (-im); Feminine plural: ־וֹת (-ot)",
        "Dual: ־ַיִם (-ayim) for eyes, ears, hands, feet",
        "Adjectives and verbs must agree in number",
    ],
    "noun_state": [
        "Two states: absolute (basic) and construct (bound)",
        "Construct state = 'X of Y' — first noun is shortened",
        "Example: מֶלֶךְ יִשְׂרָאֵל = king of Israel",
        "Only the last noun in a chain takes the article",
    ],
    "construct_chain": [
        "Noun (construct) + noun (absolute) = 'X of Y'",
        "Only the last noun takes the definite article",
        "First noun loses its article in construct",
        "Chains can be 3+ nouns long",
    ],
}

GRAMMAR_KEY_POINTS = {
    "definite_article": [
        "Prefix הַ (ha-) = 'the' — attached to noun",
        "Doubles the next letter with dagesh forte",
        "Before gutturals, vowel may lengthen (הֶ, הָ)",
        "Only one article per construct chain (on last noun)",
    ],
    "independent_prepositions": [
        "Stand-alone words (not prefixes) for relationships",
        "Common: אֶל (to), עַל (upon), עִם (with)",
        "Also: תַּחַת (under), לִפְנֵי (before), אַחֲרֵי (after)",
        "Unlike ב/כ/ל — these are separate words, not prefixes",
    ],
    "preposition_independent": [
        "Stand-alone words for spatial/temporal/logical relations",
        "Common: אֶל (to), עַל (upon), עִם (with), תַּחַת (under)",
        "Also: לִפְנֵי (before), אַחֲרֵי (after), אֵצֶל (beside)",
        "Unlike inseparable prepositions (ב,כ,ל) — these are separate",
    ],
    "direct_object_marker": [
        "אֶת marks the definite direct object",
        "Only before DEFINITE nouns (with ה־, proper names)",
        "No English translation — purely grammatical",
        "Merges with suffixes: אֹתִי (me), אֹתוֹ (him)",
    ],
    "begadkefat": [
        "Six letters: בגדכפת — change sound without dagesh",
        "Dagesh = hard/plosive; No dagesh = soft/fricative",
        "After a consonant or pause → hard; after vowel → soft",
        "Most common: ב→v, כ→kh, פ→f, ת→th",
    ],
    "nominal_clauses": [
        "Sentences without a verb — 'A is B' pattern",
        "No copula (verb 'to be') needed in present tense",
        "Four types: identification, description, existence, possession",
        "Verb היה used for past and future tenses",
    ],
    "adjective_agreement": [
        "Adjective matches noun in gender, number, definiteness",
        "Attributive: both take ה־ for definite",
        "Predicate: noun takes ה־ but adjective does not",
        "Word order: Noun → Adjective",
    ],
    "demonstratives": [
        "זֶה = this (m. sg.), זֹאת/זוֹ = this (f. sg.)",
        "אֵלֶּה = these (pl.)",
        "הוּא/הִיא = that (m./f.) — also used as pronouns",
        "Demonstratives agree in gender and number with the noun",
    ],
    "interrogatives": [
        "מִי = who?, מָה/מַה = what?",
        "לָמָּה/מַדּוּעַ = why?, אֵיפֹה = where?",
        "אֵיךְ/אֵיכָה = how?, אֵיזֶה = which?",
        "Yes/no questions: prefix הֲ (he interrogative)",
    ],
    "pronominal_suffixes_nouns": [
        "Possession expressed with SUFFIXES, not separate words",
        "Suffixes: my=־י, your=־ךָ, his=וֹ, her=ָהּ",
        "Our=־נוּ, your=־כֶם, their=־הֶם",
        "Noun often changes form (construct) before suffix",
    ],
    "prepositions_with_suffixes": [
        "Prepositions fuse with pronouns into single words",
        "ל (to/for): לִי, לְךָ, לוֹ, לָהּ, לָנוּ",
        "ב (in/with): בִּי, בְּךָ, בּוֹ, בָּנוּ",
        "These forms are extremely common and must be memorized",
    ],
    "object_suffixes_verbs": [
        "Object pronouns attach directly to verbs",
        "Pattern: Verb + Suffix (שְׁמָרַנִי = he kept me)",
        "Verb form often changes before the suffix",
        "Very common in biblical narrative",
    ],
    "infinitive_construct": [
        "Verbal noun — like 'to write' or 'writing'",
        "Often with prepositions: ל (to), ב (in/when), כ (as)",
        "Qal pattern: קְטֹל",
        "~50% of all verb uses in narrative",
    ],
    "infinitive_absolute": [
        "Emphatic verb form — 'you shall surely die'",
        "Precedes a finite verb of the same root",
        "Qal pattern: קָטוֹל",
        "Can also function as an imperative (זָכוֹר = Remember!)",
    ],
    "commands_jussive": [
        "Imperative = direct command (2nd person only)",
        "Jussive = let/may (3rd person, subtle distinction)",
        "Cohortative = let me/us (1st person, marked by ה-ָה)",
        "Negative commands: לֹא (strong) vs אַל (soft)",
    ],
    "conditional_sentences": [
        "אִם = if (most common conditional particle)",
        "כִּי = if/when/for (ambiguous — context determines)",
        "לוּ / לוּלֵא = if only / if not (contrafactual)",
        "Real condition: imperfect in both clauses",
    ],
    "numeral_agreement": [
        "Numbers 3-10 show GENDER REVERSAL with the noun",
        "Masculine noun → feminine number form",
        "Feminine noun → masculine number form",
        "Numbers 1-2 agree normally (no reversal)",
    ],
    "cognate_accusative": [
        "Verb + noun from same root for emphasis",
        "חָלַם חֲלוֹם = 'he dreamed a dream'",
        "Intensifies or specifies the action",
        "Common in Hebrew narrative and poetry",
    ],
    "emphatic_structures": [
        "Normal word order: VSO (Verb-Subject-Object)",
        "Fronting = moving word to beginning for emphasis",
        "Can front: object, adverb, infinitive, pronoun",
        "Very common in poetry and prophecy",
    ],
    "waw_relative": [
        "Relative clauses use אֲשֶׁר + resumptive pronoun",
        "Resumptive pronoun refers back to the antecedent",
        "English drops the pronoun; Hebrew KEEPS it",
        "Sometimes אֲשֶׁר is omitted (asyndetic)",
    ],
    "vav_consecutive": [
        "Prefix וַ changes verb tense",
        "Perfect + vav → future; Imperfect + vav → past",
        "Backbone of biblical narrative prose",
        "Unique to Hebrew — no equivalent in other languages",
    ],
    "direct_object": [
        "אֶת marks the definite direct object of a verb",
        "Only before definite nouns (with ה־)",
        "No English translation",
        "Indefinite objects do not take אֶת",
    ],
    "relative_clause": [
        "Introduced by אֲשֶׁר (that/which/who)",
        "Contains a resumptive pronoun in Hebrew",
        "Sometimes the particle is omitted (asyndetic)",
        "Verb follows normal agreement patterns",
    ],
    "word_order": [
        "Standard: VSO (Verb-Subject-Object)",
        "Opposite of English (SVO)",
        "Verb often comes first with vav-consecutive",
        "Poetry can invert this order",
    ],
    "noun_gender": [
        "Every noun is masculine or feminine",
        "Feminine usually ends in ־ָה or ־ֶת/ת",
        "Masculine nouns have no fixed ending",
        "Gender affects adjectives, verbs, pronouns",
    ],
    "noun_number": [
        "Singular, plural, and dual (for pairs)",
        "Masc. plural: ־ִים; Fem. plural: ־וֹת",
        "Dual: ־ַיִם for natural pairs",
        "Agreement required with adjectives and verbs",
    ],
    "noun_state": [
        "Absolute = basic form; Construct = 'X of Y'",
        "Construct shortens the noun form",
        "Only last noun takes the article",
        "Chains of 2-5 nouns are common",
    ],
    "construct_chain": [
        "Noun (construct) + noun (absolute) = 'X of Y'",
        "Only last noun takes the article",
        "First noun is shortened in construct",
        "Chains can stack 3+ deep",
    ],
    "preposition_independent": [
        "Stand-alone prepositions (not prefixes)",
        "אֶל (to), עַל (upon), עִם (with)",
        "תַּחַת (under), לִפְנֵי (before)",
        "Separate words — unlike ב/כ/ל prefixes",
    ],
}


def main():
    conn = sqlite3.connect(str(MEM_DB))
    
    all_kp = {}
    all_kp.update(CONSONANT_KEY_POINTS)
    all_kp.update(VERB_KEY_POINTS)
    all_kp.update(SYLLABLE_KEY_POINTS)
    all_kp.update(NOUN_KEY_POINTS)
    all_kp.update(GRAMMAR_KEY_POINTS)
    
    updated = 0
    for node_id, key_points in all_kp.items():
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if not row:
            continue
        
        try:
            content = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            content = {}
        
        content["key_points"] = key_points
        conn.execute(
            "UPDATE hebrew_lessons SET content_json=? WHERE node_id=?",
            (json.dumps(content, ensure_ascii=False), node_id)
        )
        
        # Also update node description if generic
        node = conn.execute("SELECT description FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if node:
            old_desc = node[0] or ''
            if old_desc in ("Key concept in consonant", "Key concept in verb", 
                            "Key concept in grammar", "Key concept in syntax",
                            "Key concept in noun", "Review the explanation above",
                            "Key concept in word", ""):
                conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (key_points[0], node_id))
        
        updated += 1
    
    conn.commit()
    conn.close()
    print(f"  Updated {updated} lesson key point sets")


if __name__ == '__main__':
    main()
