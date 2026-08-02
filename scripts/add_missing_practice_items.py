#!/usr/bin/env python3
"""Add practice items for Hebrew nodes that had ZERO practice items.

Math Academy Way review finding: 35 foundational nodes (syllables, prefixes,
suffixes, noun patterns, syntax, reading, roots) had teaching content but no
active retrieval practice at all — violating the testing effect (Ch. 20).

Each item is curated and grounded in the node's own lesson explanation, so the
questions test exactly what the lesson teaches. Questions never reveal the
answer in the question text, and no true/false items are generated.

Usage:
    python3 scripts/add_missing_practice_items.py --dry-run
    python3 scripts/add_missing_practice_items.py --apply
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

# node_id -> [(question_type, question, options, answer, difficulty, explanation)]
# All grounded in the lesson explanation shown in the DB.
CURATED = {
    "noun_gender": [
        ("multiple_choice", "Every Hebrew noun has which grammatical gender?",
         ["Masculine or feminine", "Masculine, feminine, or neuter", "Only masculine", "Gender is optional"], 
         "Masculine or feminine", 0.4,
         "Hebrew has grammatical gender for every noun — masculine or feminine — even for inanimate objects."),
        ("multiple_choice", "Which ending typically marks a feminine Hebrew noun?",
         ["־ָה (qamats-he)", "־ִים", "־וֹת", "־י"], "־ָה (qamats-he)", 0.5,
         "Feminine nouns typically end in ־ָה (qamats-he) or ־ֶת/-ת."),
        ("recall", "Why does noun gender matter in Hebrew sentences?",
         [], "Adjectives, verbs, and pronouns must agree with the noun's gender", 0.6,
         "Gender matters because adjectives, verbs, and pronouns must agree with the noun's gender."),
    ],
    "noun_number": [
        ("multiple_choice", "How many grammatical numbers does Hebrew have?",
         ["Three: singular, plural, dual", "Two: singular and plural", "Four", "One"],
         "Three: singular, plural, dual", 0.3,
         "Hebrew has singular, plural, and dual (for pairs like eyes, ears, hands, feet)."),
        ("multiple_choice", "Which suffix marks the masculine plural?",
         ["־ִים", "־וֹת", "־ָה", "־י"], "־ִים", 0.4,
         "Masculine plural adds ־ִים (suffix -im)."),
        ("multiple_choice", "Which suffix marks the feminine plural?",
         ["־וֹת", "־ִים", "־ָה", "־וּ"], "־וֹת", 0.4,
         "Feminine plural adds ־וֹת (suffix -ot)."),
        ("recall", "What is the dual number used for in Hebrew?",
         [], "Pairs (eyes, ears, hands, feet)", 0.6,
         "The dual is used for pairs: eyes, ears, hands, feet."),
    ],
    "preposition_independent": [
        ("multiple_choice", "Which of these is an independent (stand-alone) preposition?",
         ["אֶל (to/toward)", "ב (in)", "כ (as)", "ל (to)"], "אֶל (to/toward)", 0.4,
         "Independent prepositions are stand-alone words like אֶל, עַל, עִם; ב, כ, ל are inseparable prefixes."),
        ("multiple_choice", "Which preposition means 'with'?",
         ["עִם", "אֶל", "תַּחַת", "אַחֲרֵי"], "עִם", 0.4,
         "עִם means 'with' — a common independent preposition."),
        ("recall", "How do independent prepositions differ from inseparable ones?",
         [], "They are separate words, not prefixes", 0.6,
         "Independent prepositions are separate words; inseparable ones (ב, כ, ל) attach as prefixes."),
    ],
    "reading_connections": [
        ("multiple_choice", "What do textual connections link across the canon?",
         ["Quotations, allusions, and thematic parallels", "Only proper names", "Only verse numbers", "Only chapter headings"],
         "Quotations, allusions, and thematic parallels", 0.4,
         "Textual connections link passages via quotations, allusions, and thematic parallels."),
        ("multiple_choice", "Which pair is a classic textual connection traced across the canon?",
         ["Angel of YHWH (Gen 16 → Exo 3 → Josh 5)", "The flood (Gen 6 → Lev 11)", "The Exodus (Exo 1 → Song 2)", "Creation (Gen 1 → Ruth 1)"],
         "Angel of YHWH (Gen 16 → Exo 3 → Josh 5)", 0.5,
         "The Angel of YHWH runs Gen 16 → Exo 3 → Josh 5, a classic connection."),
        ("recall", "Why do textual connections deepen comprehension?",
         [], "They link passages so each sheds light on the others", 0.6,
         "Connections deepen comprehension beyond a single passage."),
    ],
    "reading_genesis": [
        ("multiple_choice", "Genesis is the book of what?",
         ["Beginnings", "Laws", "Prophecies", "Wisdom sayings"], "Beginnings", 0.3,
         "Genesis (בְּרֵאשִׁית) is the book of beginnings."),
        ("multiple_choice", "Which Hebrew style does Genesis 1 display?",
         ["Elevated prose of creation", "Legal casuistry", "Prophetic messenger speech", "Wisdom riddles"],
         "Elevated prose of creation", 0.5,
         "Genesis 1 is elevated prose; the book also contains genealogies, narratives, and poetry."),
        ("recall", "What is a good early reading skill to practice with Genesis?",
         [], "Parsing narrative prose", 0.6,
         "Genesis is primarily narrative prose — ideal for parsing practice."),
    ],
    "reading_isaiah": [
        ("multiple_choice", "Which kind of literature is Isaiah?",
         ["Prophetic literature", "Legal literature", "Wisdom literature", "Apocalyptic only"],
         "Prophetic literature", 0.3,
         "Isaiah is prophetic literature rich in temple theology and messianic prophecy."),
        ("multiple_choice", "What themes does Isaiah's Hebrew emphasize?",
         ["Temple theology and messianic prophecy", "Only genealogies", "Only commercial law", "Only travel itineraries"],
         "Temple theology and messianic prophecy", 0.5,
         "Isaiah is rich in temple theology and messianic prophecy."),
        ("recall", "Why does Isaiah's vocabulary differ from narrative prose?",
         [], "It uses poetic imagery and prophetic formulas", 0.6,
         "Isaiah uses poetic imagery and prophetic formulas beyond plain narrative."),
    ],
    "reading_psalms": [
        ("multiple_choice", "Which feature is distinctive of Hebrew poetry like Psalms?",
         ["Parallelism", "Casus law", "Messenger formulas", "Genealogies"],
         "Parallelism", 0.4,
         "Psalms features parallelism (synonymous, antithetic, synthetic)."),
        ("multiple_choice", "Which type of parallelism contrasts two lines?",
         ["Antithetic", "Synonymous", "Synthetic", "Acrostic"], "Antithetic", 0.5,
         "Antithetic parallelism contrasts the two lines."),
        ("recall", "How does poetic word order differ from prose in Psalms?",
         [], "More variation and ellipsis", 0.6,
         "Poetic word order has more variation and ellipsis than prose."),
    ],
    "reading_torah": [
        ("multiple_choice", "The Torah consists of which texts?",
         ["The first five books of Moses", "The twelve minor prophets", "The wisdom books", "The Psalms"],
         "The first five books of Moses", 0.3,
         "The Torah is the first five books of Moses."),
        ("multiple_choice", "What kind of Hebrew is Torah Hebrew primarily?",
         ["Narrative prose with embedded poetry and laws", "Pure poetry", "Only legal formulas", "Only genealogies"],
         "Narrative prose with embedded poetry and laws", 0.4,
         "Torah Hebrew is primarily narrative prose with embedded poetry, laws, genealogies, and speeches."),
        ("recall", "Why is the Torah ideal for early reading?",
         [], "Its vocabulary is more limited than the Prophets", 0.6,
         "Torah vocabulary is more limited than the Prophets, ideal for early reading."),
    ],
    "syllable_basics": [
        ("multiple_choice", "What is a Hebrew syllable built around?",
         ["A vowel", "A dagesh", "A consonant only", "A maqqef"], "A vowel", 0.3,
         "A Hebrew syllable is built around a vowel."),
        ("multiple_choice", "Which are the two basic Hebrew syllable patterns?",
         ["CV (open) and CVC (closed)", "VV and VC", "CCV and CCC", "V and CC"],
         "CV (open) and CVC (closed)", 0.4,
         "Basic patterns are CV (open) and CVC (closed)."),
        ("recall", "What must every Hebrew syllable begin with?",
         [], "A consonant (word-initial vowels use Aleph/Ayin as carriers)", 0.6,
         "Every syllable must begin with a consonant; word-initial vowels use Aleph or Ayin as carriers."),
    ],
    "syllable_open": [
        ("multiple_choice", "An open syllable (CV) ends with what?",
         ["A vowel", "A consonant", "A dagesh", "A sheva"], "A vowel", 0.3,
         "An open syllable (CV) ends with a vowel."),
        ("multiple_choice", "Which is an example of an open syllable?",
         ["בָּ (Bet with Qamats)", "בַּת (Bet-Patah-Tav)", "בְּ (Bet with sheva)", "מִן (Mem-Hiriq-Nun)"],
         "בָּ (Bet with Qamats)", 0.5,
         "בָּ is a CV syllable — Bet with Qamats."),
        ("recall", "What determines an open syllable's vowel quality?",
         [], "Stress and form", 0.6,
         "Its vowel quality and historical length depend on stress and form."),
    ],
    "syllable_closed": [
        ("multiple_choice", "A closed syllable (CVC) ends with what?",
         ["A consonant", "A vowel", "A sheva", "A maqqef"], "A consonant", 0.3,
         "A closed syllable (CVC) ends with a consonant."),
        ("multiple_choice", "Which is an example of a closed syllable?",
         ["בַּת (Bet-Patah-Tav)", "בָּ (Bet with Qamats)", "לָ (Lamed-Qamats)", "וּ (Vav-Shuruq)"],
         "בַּת (Bet-Patah-Tav)", 0.5,
         "בַּת is a CVC syllable: Bet-Patah-Tav."),
        ("recall", "Can you infer vowel length from a closed syllable alone?",
         [], "No — do not infer vowel length from closure alone", 0.6,
         "The final consonant closes it; do not infer vowel length from this alone."),
    ],
    "syllable_division": [
        ("multiple_choice", "How many syllables does בְּרֵאשִׁית have?",
         ["Three", "Two", "Four", "Five"], "Three", 0.4,
         "בְּרֵאשִׁית = בְּ·רֵא·שִׁית (3 syllables); the Aleph is quiescent."),
        ("multiple_choice", "What does a silent sheva do in syllable division?",
         ["Closes the syllable", "Starts a new syllable", "Doubles a consonant", "Adds a vowel"],
         "Closes the syllable", 0.5,
         "Silent sheva = end of syllable; vocal sheva = start of a new one."),
        ("recall", "What does a dagesh forte do in syllable division?",
         [], "Doubles the consonant, splitting syllables", 0.6,
         "Dagesh forte doubles the consonant, splitting syllables."),
    ],
    "syllable_stress": [
        ("multiple_choice", "Where does Hebrew stress usually fall?",
         ["On the last syllable (ultima)", "On the first syllable", "Always on the penult", "On the maqqef"],
         "On the last syllable (ultima)", 0.3,
         "Hebrew stress is usually on the LAST syllable (ultima)."),
        ("multiple_choice", "Stress can change meaning. What does בָּ֫נוּ mean?",
         ["We came", "They built", "You said", "We spoke"], "We came", 0.5,
         "בָּ֫נוּ (bā́nu) = 'we came'; בָּנ֫וּ (bānú) = 'they built'."),
        ("recall", "When stress falls on the second-to-last syllable, what is it called?",
         [], "Penultima (penultimate stress)", 0.5,
         "Sometimes stress falls on the penultima (second-to-last)."),
    ],
    "direct_object": [
        ("multiple_choice", "Which particle marks the definite direct object in Hebrew?",
         ["אֶת", "אֲשֶׁר", "בְּ", "וַ"], "אֶת", 0.4,
         "The direct object is often marked by אֶת before a definite noun."),
        ("multiple_choice", "In וַיִּבְרָא אֱלֹהִים אֶת הַשָּׁמַיִם, what does אֶת signal?",
         ["'the heavens' is the definite direct object", "'the heavens' is the subject", "'God' is the object", "a new sentence"],
         "'the heavens' is the definite direct object", 0.5,
         "אֶת marks הַשָּׁמַיִם as the definite direct object of created."),
        ("recall", "Do indefinite objects (no 'the') take אֶת?",
         [], "No — indefinite objects do not take אֶת", 0.5,
         "Indefinite objects (no 'the') do not take אֶת."),
    ],
    "relative_clause": [
        ("multiple_choice", "Which particle introduces a relative clause?",
         ["אֲשֶׁר (that/which/who)", "אֶת", "הַ", "וַ"], "אֲשֶׁר (that/which/who)", 0.4,
         "A relative clause is introduced by אֲשֶׁר (that/which/who)."),
        ("multiple_choice", "In הָאִישׁ אֲשֶׁר בָּא, which part describes the man?",
         ["אֲשֶׁר בָּא ('who came')", "הַבַּיִת", "בְּנֵי", "אֶת־הָאָרֶץ"],
         "אֲשֶׁר בָּא ('who came')", 0.5,
         "אֲשֶׁר בָּא = 'who came', describing the man."),
        ("recall", "What is an asyndetic relative clause?",
         [], "One with the relative particle omitted (juxtaposed)", 0.6,
         "Sometimes the relative particle is omitted and the clause is simply juxtaposed."),
    ],
    "vav_consecutive": [
        ("multiple_choice", "What does wayyiqtol (e.g. וַיֹּאמֶר) commonly advance?",
         ["Mainline past narrative", "Future intent", "A question", "A command"],
         "Mainline past narrative", 0.4,
         "Wayyiqtol commonly advances the mainline of past narrative."),
        ("multiple_choice", "What does weqatal (e.g. וְאָהַבְתָּ) often continue?",
         ["Instructions or projected sequences", "Past narrative only", "Only direct speech", "Only nominal clauses"],
         "Instructions or projected sequences", 0.5,
         "Weqatal often continues instructions or projected sequences."),
        ("recall", "Is the vav-consecutive a mechanical tense reverser?",
         [], "No — they are discourse forms, not a tense-reversing vav", 0.5,
         "These are discourse forms, not a mechanical vav that reverses tense."),
    ],
    "word_order": [
        ("multiple_choice", "Which word order is common in Biblical Hebrew narrative?",
         ["Verb-subject (verb often first)", "Subject-verb-object always", "Object-verb-subject", "No pattern exists"],
         "Verb-subject (verb often first)", 0.4,
         "Verb-subject order is common, especially in mainline wayyiqtol clauses."),
        ("multiple_choice", "In וַיֹּאמֶר אֱלֹהִים יְהִי אוֹר, which word comes first?",
         ["The verb וַיֹּאמֶר", "The subject אֱלֹהִים", "The object אוֹר", "A preposition"],
         "The verb וַיֹּאמֶר", 0.4,
         "The verb often comes first with the consecutive vav (וַיֹּאמֶר)."),
        ("recall", "What can invert the common verb-first order?",
         [], "Poetry and emphasis (focus)", 0.6,
         "Poetry and emphasis can invert this order."),
    ],
    "noun_pattern_qatl": [
        ("multiple_choice", "What is a qatl pattern?",
         ["A historical consonant-vowel noun pattern", "A verb conjugation", "A plural suffix", "A type of sheva"],
         "A historical consonant-vowel noun pattern", 0.4,
         "Qatl is a historical consonant-vowel pattern, not a literal surface recipe."),
        ("multiple_choice", "מֶלֶךְ (king), root מלך, is often explained from which pattern?",
         ["Qatl", "Qitl", "Qutl", "Qal"], "Qatl", 0.5,
         "מֶלֶךְ is a segolate noun often explained from an earlier qatl-type form."),
        ("recall", "Does a noun pattern by itself determine a word's meaning?",
         [], "No — confirm sense from context and lexicon", 0.6,
         "A pattern helps recognition but does not by itself determine meaning."),
    ],
    "noun_pattern_qitl": [
        ("multiple_choice", "סֵפֶר (book), root ספר, is related to which historical pattern?",
         ["Qitl", "Qatl", "Qutl", "Qal"], "Qitl", 0.4,
         "סֵפֶר is a segolate surface form often related to a qitl-type pattern."),
        ("multiple_choice", "A qitl pattern is which kind of form?",
         ["A historical noun pattern", "A verbal stem", "A definite article", "A plural ending"],
         "A historical noun pattern", 0.4,
         "Qitl is a historical noun pattern."),
        ("recall", "What should you confirm even when a pattern matches?",
         [], "The word's meaning from its context and lexicon", 0.6,
         "A pattern does not by itself determine meaning."),
    ],
    "noun_pattern_qutl": [
        ("multiple_choice", "קֹדֶשׁ (holiness), root קדש, is related to which historical pattern?",
         ["Qutl", "Qitl", "Qatl", "Qal"], "Qutl", 0.4,
         "קֹדֶשׁ is a segolate surface form often related to a qutl-type pattern."),
        ("multiple_choice", "A qutl pattern involves which vowel class?",
         ["U-class (e.g. qutl)", "A-class", "I-class", "No vowel"], "U-class (e.g. qutl)", 0.4,
         "Qutl is the u-class historical noun pattern."),
        ("recall", "How should you confirm the sense of a qutl-form word?",
         [], "From its context and lexicon entry", 0.6,
         "Confirm a word's sense from its context and lexicon entry."),
    ],
    "prefix_bet": [
        ("multiple_choice", "What does the inseparable prefix ב (bet) mean?",
         ["in / with / by", "to / for", "from", "and"], "in / with / by", 0.3,
         "Prefix bet (ב) is the inseparable preposition meaning in/with/by."),
        ("recall", "Is ב a prefix or an independent word?",
         [], "An inseparable prefix", 0.5,
         "ב is an inseparable preposition — a prefix, not a stand-alone word."),
    ],
    "prefix_he": [
        ("multiple_choice", "What does the prefix הַ (he) mark?",
         ["The definite article (the)", "A question", "Negation", "The future"],
         "The definite article (the)", 0.3,
         "The prefix הַ (ha-) means 'the' and attaches to the beginning of nouns."),
        ("recall", "How is the definite article written in Hebrew?",
         [], "As a prefix הַ attached to the noun", 0.5,
         "The definite article is a prefix הַ attached to the beginning of a noun."),
    ],
    "prefix_kaf": [
        ("multiple_choice", "What does the inseparable prefix כ (kaf) mean?",
         ["as / like", "in / with", "from", "to / for"], "as / like", 0.3,
         "Prefix kaf (כ) is the inseparable preposition meaning as/like."),
        ("recall", "What does כְּ־ mean as a prefix?",
         [], "As / like (comparison)", 0.5,
         "כְּ־ means as/like — used for comparison."),
    ],
    "prefix_lamed": [
        ("multiple_choice", "What does the inseparable prefix ל (lamed) mean?",
         ["to / for", "from", "and", "as / like"], "to / for", 0.3,
         "Prefix lamed (ל) is the inseparable preposition meaning to/for."),
        ("recall", "What is לְ־ most commonly used for?",
         [], "To / for (direction or purpose)", 0.5,
         "לְ־ means to/for — direction or purpose."),
    ],
    "prefix_mem": [
        ("multiple_choice", "What does the inseparable prefix מ (mem) mean?",
         ["from", "in", "to", "and"], "from", 0.3,
         "Prefix mem (מ) is the inseparable preposition meaning from."),
        ("recall", "What does מִ־ mean as a prefix?",
         [], "From", 0.5,
         "מִ־ means from."),
    ],
    "prefix_shin": [
        ("multiple_choice", "What does the prefix ש (shin) introduce?",
         ["A relative particle (that/which)", "A question", "The definite article", "Negation"],
         "A relative particle (that/which)", 0.4,
         "Prefix shin (ש) is the relative particle meaning that/which."),
        ("recall", "What does שֶׁ־ mean as a prefix?",
         [], "That / which (relative)", 0.5,
         "שֶׁ־ is the relative particle meaning that/which."),
    ],
    "prefix_vav": [
        ("multiple_choice", "What does the prefix ו (vav) mean?",
         ["and", "from", "to", "the"], "and", 0.3,
         "Conjunctive vav (ו) means 'and'."),
        ("recall", "What is the basic meaning of the prefix ו?",
         [], "And (conjunction)", 0.4,
         "The conjunctive vav means 'and'."),
    ],
    "root_concept": [
        ("multiple_choice", "Most Hebrew words are built from how many root consonants?",
         ["Three", "Two", "Four", "Five"], "Three", 0.3,
         "Most Hebrew words are built from a THREE-CONSONANT ROOT (שֹׁרֶשׁ)."),
        ("multiple_choice", "What does the root כ-ת-ב relate to?",
         ["Writing", "Kingship", "Blessing", "Fear"], "Writing", 0.4,
         "Root כ-ת-ב (k-t-v) relates to writing: כָּתַב, כְּתָב, מִכְתָּב."),
        ("recall", "What carries the core meaning of a Hebrew word?",
         [], "Its three-consonant root", 0.5,
         "The root carries the core meaning; vowel patterns and affixes modify it."),
    ],
    "root_extraction": [
        ("multiple_choice", "In מִכְתָּב, what is the מִ־?",
         ["A noun-pattern prefix", "A root consonant", "A plural suffix", "A vowel letter"],
         "A noun-pattern prefix", 0.5,
         "מִכְתָּב contains the noun-pattern prefix מִ־ and is confirmed under root כתב."),
        ("recall", "What should you do before proposing a root?",
         [], "Segment known prefixes/suffixes and compare with a lexicon", 0.6,
         "Segment known affixes, then compare remaining consonants with related forms and a lexicon."),
    ],
    "suffix_plural_m": [
        ("multiple_choice", "Which suffix marks the masculine plural?",
         ["־ִים", "־וֹת", "־ָה", "־י"], "־ִים", 0.3,
         "Masculine plural suffix: ־ִים."),
        ("recall", "What does the suffix ־ִים mark?",
         [], "Masculine plural", 0.4,
         "־ִים is the masculine plural suffix."),
    ],
    "suffix_plural_f": [
        ("multiple_choice", "Which suffix marks the feminine plural?",
         ["־וֹת", "־ִים", "־ָה", "־וּ"], "־וֹת", 0.3,
         "Feminine plural suffix: ־וֹת."),
        ("recall", "What does the suffix ־וֹת mark?",
         [], "Feminine plural", 0.4,
         "־וֹת is the feminine plural suffix."),
    ],
    "suffix_pron_1s": [
        ("multiple_choice", "What does the pronominal suffix ־ִי mean?",
         ["my", "your", "his", "our"], "my", 0.4,
         "־ִי is the 1s pronominal suffix meaning 'my'."),
        ("recall", "What does ־ִי mean as a suffix?",
         [], "My (1st person singular)", 0.5,
         "־ִי means my."),
    ],
    "suffix_pron_2ms": [
        ("multiple_choice", "What does the pronominal suffix ־ךָ mean?",
         ["your (m. sg.)", "my", "his", "our"], "your (m. sg.)", 0.4,
         "־ךָ is the 2ms pronominal suffix meaning 'your (masculine singular)'."),
        ("recall", "What does ־ךָ mean as a suffix?",
         [], "Your (masculine singular)", 0.5,
         "־ךָ means your (m. sg.)."),
    ],
    "suffix_pron_3ms": [
        ("multiple_choice", "What does the pronominal suffix וֹ mean?",
         ["his", "her", "our", "your"], "his", 0.4,
         "וֹ/־יו is the 3ms pronominal suffix meaning 'his'."),
        ("recall", "What does וֹ mean as a suffix?",
         [], "His (3rd person masculine singular)", 0.5,
         "וֹ/־יו means his."),
    ],
    "suffix_pron_1p": [
        ("multiple_choice", "What does the pronominal suffix ־נוּ mean?",
         ["our", "my", "his", "your"], "our", 0.4,
         "־נוּ is the 1p pronominal suffix meaning 'our'."),
        ("recall", "What does ־נוּ mean as a suffix?",
         [], "Our (1st person plural)", 0.5,
         "־נוּ means our."),
    ],
}


def main():
    parser = argparse.ArgumentParser(description="Add practice items for empty Hebrew nodes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    empty = [r["id"] for r in conn.execute(
        "SELECT n.id FROM hebrew_nodes n "
        "WHERE NOT EXISTS (SELECT 1 FROM hebrew_practice_items p WHERE p.node_id=n.id)")]
    covered = [nid for nid in empty if nid in CURATED]
    uncovered = [nid for nid in empty if nid not in CURATED]
    print(f"Empty nodes: {len(empty)} | curated: {len(covered)} | uncurated: {len(uncovered)}")
    if uncovered:
        print(f"  WARNING — no curated items for: {uncovered}")

    total = sum(len(v) for v in CURATED.values() if v)
    print(f"Total items to add: {total}")

    if args.dry_run:
        for nid in covered:
            print(f"  [{nid}] {len(CURATED[nid])} items")
        conn.close()
        return

    cur = conn.cursor()
    added = 0
    for nid in covered:  # only nodes that were empty at scan time
        for qtype, q, opts, ans, diff, expl in CURATED[nid]:
            # Re-check under the write path + per-item dedup guard (idempotent).
            if cur.execute(
                "SELECT 1 FROM hebrew_practice_items WHERE node_id=? AND question_type=? AND question_text=? AND correct_answer=?",
                (nid, qtype, q, ans)).fetchone():
                continue
            opts_json = json.dumps(opts, ensure_ascii=False) if opts else "[]"
            cur.execute(
                """INSERT INTO hebrew_practice_items
                   (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
                   VALUES (?,?,?,?,?,?,?)""",
                (nid, qtype, q, opts_json, ans, diff, expl))
            added += 1
    conn.commit()

    print(f"  ✅ Added {added} practice items")
    remaining = conn.execute(
        "SELECT COUNT(*) FROM hebrew_nodes n "
        "WHERE NOT EXISTS (SELECT 1 FROM hebrew_practice_items p WHERE p.node_id=n.id)").fetchone()[0]
    print(f"  nodes still with zero practice items: {remaining}")
    conn.close()


if __name__ == "__main__":
    main()
