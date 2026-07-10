#!/usr/bin/env python3
"""
H2: Seed Hebrew lesson content — explanations, worked examples, practice items.

Generates lesson content for all 102 Hebrew knowledge graph nodes and stores
them in the database for the lesson engine.

Usage:
    python3 scripts/seed_hebrew_content.py
    python3 scripts/seed_hebrew_content.py --db data/memorize.db
"""

import sqlite3
import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCHEMA = """
CREATE TABLE IF NOT EXISTS hebrew_lessons (
    node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
    content_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS hebrew_practice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    question_type TEXT NOT NULL,
    question_text TEXT NOT NULL,
    options_json TEXT DEFAULT '[]',
    correct_answer TEXT NOT NULL,
    difficulty REAL DEFAULT 0.5,
    explanation TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS hebrew_progress (
    user_id TEXT NOT NULL DEFAULT 'default',
    node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    mastery REAL DEFAULT 0.0,
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    last_practiced TEXT,
    PRIMARY KEY (user_id, node_id)
);
"""

# ── Lesson content for each topic ──

def build_lesson(node_id, glyph, title, category, desc):
    """Build a lesson dict for a Hebrew concept node."""
    lesson = {
        "node_id": node_id,
        "title": title,
        "glyph": glyph,
        "category": category,
        "description": desc,
        "explanation": _explanation(node_id, title, category),
        "worked_examples": _worked_examples(node_id, title, category),
        "key_points": _key_points(node_id, category),
    }
    return lesson


def _explanation(nid, title, category):
    """Generate explanation text for a topic."""
    explanations = {
        # Level 1: Letters
        "aleph": (
            "Aleph (א) is the first letter of the Hebrew alphabet. "
            "It is a glottal stop — essentially a silent letter that "
            "acts as a carrier for vowels. In modern Hebrew it has no "
            "sound of its own. Think of it like a silent 'placeholder' "
            "that vowels attach to."
        ),
        "bet": (
            "Bet (בּ) makes a 'b' sound when it has a dot (dagesh) inside: בּ. "
            "Without the dagesh it becomes Vet (ב) and makes a 'v' sound. "
            "This is called begadkefat spirantization — a pattern where "
            "certain letters change their sound when they lose their dagesh."
        ),
        "gimel": (
            "Gimel (ג) makes a 'g' sound as in 'garden'. "
            "With a dagesh it's hard 'g', without it softens to a "
            "gh sound in some reading traditions. It's the third letter "
            "of the aleph-bet."
        ),
        "dalet": (
            "Dalet (ד) makes a 'd' sound with dagesh. "
            "Without dagesh it softens to 'dh' (like 'th' in 'the'). "
            "It is the fourth letter and one of the begadkefat letters."
        ),
        "he": (
            "He (ה) makes an 'h' sound. At the end of a word it is "
            "often silent or indicates the feminine gender. It can also "
            "function as a definite article prefix 'the' when added to "
            "the beginning of a word with a patah: הַ (ha)."
        ),
        "vav": (
            "Vav (ו) makes a 'v' sound. It is also used as a vowel "
            "letter (mater lectionis): with a dot above (וֹ) it's 'o', "
            "with a dot inside (וּ) it's 'u'. As a prefix it means 'and' — "
            "the famous 'vav-consecutive' that connects narrative events."
        ),
        "zayin": (
            "Zayin (ז) makes a 'z' sound as in 'zebra'. "
            "It is the seventh letter of the aleph-bet."
        ),
        "chet": (
            "Chet (ח) is a guttural sound — a voiceless pharyngeal fricative, "
            "like the 'ch' in Bach. It is one of the guttural letters "
            "(אהחע) that affect vowel behavior in grammar."
        ),
        "tet": (
            "Tet (ט) makes an emphatic 't' sound. It is one of the "
            "emphatic consonants (ט צ ק) that are unique to Semitic languages."
        ),
        "yod": (
            "Yod (י) makes a 'y' sound. It is frequently used as a vowel "
            "letter (mater lectionis) for 'i' and 'e' sounds. "
            "It's the smallest letter but appears in many grammatical patterns "
            "as a suffix meaning 'my' (־י)."
        ),
        "kaf": (
            "Kaf (כּ) makes a 'k' sound with dagesh, 'kh' (like Bach) "
            "without. It has a final form (ך) used at the end of words. "
            "It is one of the begadkefat letters."
        ),
        "kaf_final": (
            "Final Kaf (ך) is the form of Kaf used only at the end of words. "
            "It has the same sound as Kaf (kh without dagesh). "
            "Five letters have final forms (ך ם ן ף ץ)."
        ),
        "lamed": (
            "Lamed (ל) makes an 'l' sound. It is the tallest letter, "
            "rising above the line. As a prefix it means 'to' or 'for'."
        ),
        "mem": (
            "Mem (מ) makes an 'm' sound. Its final form (ם) is a closed "
            "square at the end of words. As a prefix it can mean 'from'."
        ),
        "mem_final": (
            "Final Mem (ם) is the closed form of Mem used at word endings. "
            "It looks like a box with a flat bottom."
        ),
        "nun": (
            "Nun (נ) makes an 'n' sound. Its final form (ן) extends below "
            "the line. It frequently drops or assimilates in weak verb forms."
        ),
        "nun_final": (
            "Final Nun (ן) extends below the baseline. It is used only "
            "at the end of words."
        ),
        "samekh": (
            "Samekh (ס) makes an 's' sound. It looks like a circle with "
            "a dot in the center."
        ),
        "ayin": (
            "Ayin (ע) is a guttural — a voiced pharyngeal fricative. "
            "Like Aleph, it often acts as a vowel carrier. It is one of "
            "the guttural letters that resist gemination (doubling)."
        ),
        "pe": (
            "Pe (פּ) makes a 'p' sound with dagesh, 'f' without. "
            "Its final form (ף) has a curved top. One of the begadkefat letters."
        ),
        "pe_final": (
            "Final Pe (ף) has a distinctive hook shape. Used only at "
            "the end of words, with the same 'f' sound as Pe without dagesh."
        ),
        "tsade": (
            "Tsade (צ) makes a 'ts' sound (like 'cats'). It is one of "
            "the emphatic consonants. Its final form (ץ) extends below the line."
        ),
        "tsade_final": (
            "Final Tsade (ץ) is used at word endings. Same 'ts' sound "
            "as the regular form."
        ),
        "qof": (
            "Qof (ק) makes a 'q' sound — an emphatic 'k' pronounced "
            "farther back in the throat. One of the three emphatic consonants."
        ),
        "resh": (
            "Resh (ר) makes an 'r' sound. Like the gutturals, it "
            "resists gemination (doubling with dagesh forte)."
        ),
        "shin": (
            "Shin (שׁ) makes a 'sh' sound (like 'shalom'). The dot "
            "on the upper right indicates 'sh'. When the dot is on the "
            "left (שׂ) it's Sin with an 's' sound."
        ),
        "sin": (
            "Sin (שׂ) makes an 's' sound. It looks identical to Shin "
            "but the dot is on the upper left instead of the right."
        ),
        "tav": (
            "Tav (ת) makes a 't' sound with dagesh, 'th' (like "
            "'through') without. The last letter of the aleph-bet."
        ),

        # Level 2: Vowels
        "vowel_patah": (
            "Patah (ַ) is a short 'a' sound, like 'a' in 'father'. "
            "It is a horizontal line under the consonant. It is one of "
            "the most common vowels in Biblical Hebrew."
        ),
        "vowel_qamats": (
            "Qamats (ָ) is a long 'a' sound, like 'a' in 'father' "
            "but held longer. It looks like a small 'T' under the "
            "consonant. Distinguish from Qamats Qatan which sounds like 'o'."
        ),
        "vowel_qamats_qatan": (
            "Qamats Qatan (ָ) looks identical to Qamats but makes an "
            "'o' sound instead of 'a'. It occurs in closed, unaccented "
            "syllables. Rule: if the syllable is closed and not stressed, "
            "it's probably Qamats Qatan. Example: חָכְמָה (ḥoḵmāh = wisdom)."
        ),
        "vowel_hiriq": (
            "Hiriq (ִ) is a short 'i' sound, like 'i' in 'machine'. "
            "It is a single dot under the consonant. With a following "
            "Yod (ִי) it becomes a long 'i'."
        ),
        "vowel_hiriq_yod": (
            "Hiriq Yod (ִי) is a long 'i' sound. The Yod acts as a "
            "mater lectionis (vowel letter) that makes the Hiriq into "
            "a full vowel. Common at the end of plural adjectives."
        ),
        "vowel_tsere": (
            "Tsere (ֵ) is a long 'e' sound, like 'e' in 'they'. "
            "It is two dots side by side under the consonant. With "
            "a following Yod (ֵי) it's also 'e'."
        ),
        "vowel_tsere_yod": (
            "Tsere Yod (ֵי) is a long 'e' with Yod as mater. "
            "Common at the end of words as a plural construct suffix."
        ),
        "vowel_segol": (
            "Segol (ֶ) is a short 'e' sound, like 'e' in 'bed'. "
            "It is three dots in a triangle under the consonant."
        ),
        "vowel_segol_yod": (
            "Segol Yod (ֶי) is 'e' with Yod mater. Found in some "
            "noun patterns and proper names."
        ),
        "vowel_holam": (
            "Holam Haser (ֹ) is a short 'o' sound. It is a single "
            "dot above the consonant (left side)."
        ),
        "vowel_holam_vav": (
            "Holam Male (וֹ) is a long 'o' with Vav as mater. "
            "The dot is above the Vav. Very common — 'shalom' (שָׁלוֹם) "
            "has a Holam Male."
        ),
        "vowel_shuruq": (
            "Shuruq (וּ) is a long 'u' sound. It is a Vav with a "
            "dagesh inside. Common in grammatical patterns."
        ),
        "vowel_qubuts": (
            "Qubuts (ֻ) is a short 'u' sound, like 'u' in 'rude'. "
            "It is three dots diagonally under the consonant."
        ),
        "vowel_sheva": (
            "Sheva (ְ) is two dots vertically under the consonant. "
            "It can be either vocal (pronounced as a brief 'e', "
            "like 'sheva na') or silent (just closing the syllable, "
            "'sheva nah')."
        ),
        "vowel_sheva_na": (
            "Sheva Na (vocal sheva) is pronounced as a brief 'e' "
            "sound, like the 'a' in 'about'. It occurs: "
            "1) At the beginning of a syllable, "
            "2) Under a letter with dagesh forte, "
            "3) After a long vowel."
        ),
        "vowel_sheva_nah": (
            "Sheva Nah (silent sheva) closes a syllable without "
            "being pronounced. It occurs in the middle or at the "
            "end of a word. It marks the end of a closed syllable."
        ),
        "vowel_hataf_patah": (
            "Hataf Patah (ֲ) is a reduced 'a' vowel — a Patah with "
            "a Sheva next to it. Used only on guttural letters "
            "(אהחע) because they can't take simple Sheva."
        ),
        "vowel_hataf_qamats": (
            "Hataf Qamats (ֳ) is a reduced 'o' vowel — Qamats with "
            "Sheva. Used on gutturals that need a reduced 'o' sound."
        ),
        "vowel_hataf_segol": (
            "Hataf Segol (ֱ) is a reduced 'e' vowel — Segol with "
            "Sheva. Used on gutturals that need a reduced 'e' sound."
        ),

        # Level 3: Syllables
        "syllable_basics": (
            "A Hebrew syllable is built around a vowel. "
            "Basic patterns: CV (consonant-vowel, open syllable) "
            "and CVC (consonant-vowel-consonant, closed syllable). "
            "Every syllable must begin with a consonant (exception: "
            "word-initial vowels use Aleph or Ayin as carriers)."
        ),
        "syllable_open": (
            "An open syllable (CV) ends with a vowel. "
            "It is always long (or has a vocal sheva). "
            "Example: בָּ (bā) — Bet with Qamats."
        ),
        "syllable_closed": (
            "A closed syllable (CVC) ends with a consonant. "
            "It is usually short. The final consonant closes it. "
            "Example: בַּת (bat) — Bet-Patah-Tav."
        ),
        "syllable_stress": (
            "Hebrew stress is usually on the LAST syllable "
            "(ultima), marked with a cantillation accent. "
            "Sometimes it falls on the second-to-last (penultima). "
            "Stress changes meaning: בָּ֫נוּ (bā́nu = we came) "
            "vs. בָּנ֫וּ (bānú = they built)."
        ),
        "syllable_division": (
            "To divide a word into syllables: "
            "1) Count the vowels (each vowel = one syllable) "
            "2) Silent sheva = end of syllable "
            "3) Vocal sheva = start of a new syllable "
            "4) Dagesh forte doubles the consonant, splitting syllables. "
            "Example: בְּרֵאשִׁית = בְּ·רֵ·א·שִׁית (4 syllables)."
        ),

        # Level 4: Roots & Words
        "root_concept": (
            "Most Hebrew words are built from a THREE-CONSONANT ROOT "
            "(שֹׁרֶשׁ). The root carries the core meaning. "
            "Vowel patterns and affixes modify it to create related words. "
            "Example: root כ-ת-ב (k-t-v) relates to writing: "
            "כָּתַב (he wrote), כְּתָב (writing), מִכְתָּב (letter)."
        ),
        "root_extraction": (
            "To extract the root from a word: "
            "1) Remove prefixes (ב, כ, ל, מ, ה, ו, ש) "
            "2) Remove suffixes (י, ךָ, ו, נוּ, ת, ם, ה) "
            "3) Remove vowel pattern letters "
            "4) The remaining 3 consonants are the root. "
            "Example: מִכְתָּב = מ + כ-ת-ב = root כתב."
        ),
        "noun_pattern_qatl": (
            "Qatl (קַטְל) is a noun pattern: C1-a-C2-e-C3. "
            "Example: מֶלֶךְ (melekh = king), root מ-ל-כ. "
            "This is one of the most common noun patterns."
        ),
        "noun_pattern_qitl": (
            "Qitl (קִטְל) is: C1-i-C2-e-C3. "
            "Example: סֵפֶר (sefer = book), root ס-פ-ר. "
            "Often indicates concrete objects."
        ),
        "noun_pattern_qutl": (
            "Qutl (קֻטְל) is: C1-u-C2-e-C3. "
            "Example: קֹדֶשׁ (qodesh = holiness), root ק-ד-שׁ. "
            "Often indicates abstract concepts."
        ),
        "prefix_bet": (
            "The prefix Bet (בְּ) means 'in', 'with', or 'by'. "
            "It takes Sheva: בְּ (bǝ). Before a word with vocal "
            "sheva, it becomes בִּ (bi). Before a lamed, it "
            "assimilates: בַּ (ba) before the definite article."
        ),
        "prefix_kaf": (
            "The prefix Kaf (כְּ) means 'as' or 'like'. "
            "It takes Sheva: כְּ (kǝ). Before the definite article "
            "it becomes כַּ (ka)."
        ),
        "prefix_lamed": (
            "The prefix Lamed (לְ) means 'to' or 'for'. "
            "It takes Sheva: לְ (lǝ). Before the definite article "
            "it becomes לַ (la). Indicates direction or purpose."
        ),
        "prefix_mem": (
            "The prefix Mem (מִ) means 'from'. "
            "It takes Hiriq: מִ (mi). Before the definite article "
            "it becomes מֵ (mē) or מִן (min)."
        ),
        "prefix_vav": (
            "The prefix Vav (וְ) means 'and'. It takes Sheva: "
            "וְ (wǝ). But it changes form depending on the next "
            "sound — before labials it becomes וּ (ū), before "
            "a stressed syllable it becomes וָ (wā)."
        ),
        "prefix_he": (
            "The prefix He (הַ) is the definite article 'the'. "
            "It takes Patah with dagesh forte in the next letter: "
            "הַדָּבָר (ha-davar = the word). Before gutturals "
            "the dagesh is omitted and the vowel may lengthen."
        ),
        "prefix_shin": (
            "The prefix Shin (שֶׁ) means 'that' or 'which'. "
            "It takes Sheva or Tsere: שֶׁ (she). Used as a "
            "relative particle introducing clauses."
        ),
        "suffix_plural_m": (
            "Masculine plural suffix is ־ים (-im). "
            "Example: מֶלֶךְ (king) → מְלָכִים (kings). "
            "The vowel pattern often changes when adding the suffix."
        ),
        "suffix_plural_f": (
            "Feminine plural suffix is ־וֹת (-ot). "
            "Example: תּוֹרָה (torah) → תּוֹרוֹת (torahs/laws)."
        ),
        "suffix_pron_1s": (
            "First person singular pronominal suffix is ־י (-i) = 'my'. "
            "Example: דָּבָר (word) → דְּבָרִי (my word). "
            "Added to nouns to show possession."
        ),
        "suffix_pron_2ms": (
            "Second person masculine singular suffix is ־ךָ (-kha) = 'your'. "
            "Example: דָּבָר → דְּבָרְךָ (your word)."
        ),
        "suffix_pron_3ms": (
            "Third person masculine singular suffix is וֹ (-o) or ־ָיו (-av) = 'his'. "
            "Example: דָּבָר → דְּבָרוֹ (his word)."
        ),
        "suffix_pron_1p": (
            "First person plural suffix is ־נוּ (-nu) = 'our'. "
            "Example: דָּבָר → דְּבָרֵנוּ (our word)."
        ),

        # Level 5: Verbs (Binyanim)
        "binyan_intro": (
            "Hebrew verbs are organized into seven BINYANIM (patterns). "
            "Each binyan adds a nuance to the basic root meaning: "
            "Qal (simple active) → Niphal (passive) → Piel (intensive) "
            "→ Pual (intensive passive) → Hiphil (causative) → "
            "Hophal (causative passive) → Hithpael (reflexive). "
            "All seven follow predictable conjugation patterns."
        ),
        "qal_perfect": (
            "Qal Perfect is the simplest verb form. It describes COMPLETED "
            "action (past tense in English). The pattern uses suffixes: "
            "3ms: כָּתַב (he wrote), 3fs: כָּתְבָה (she wrote), "
            "2ms: כָּתַבְתָּ (you wrote), 1cs: כָּתַבְתִּי (I wrote). "
            "The perfect is the basic form listed in lexicons."
        ),
        "qal_imperfect": (
            "Qal Imperfect describes INCOMPLETE or FUTURE action. "
            "It uses PREFIXES (א, ת, י, נ) rather than suffixes: "
            "3ms: יִכְתֹּב (he will write), 3fs: תִּכְתֹּב (she will write), "
            "1cs: אֶכְתֹּב (I will write), 1cp: נִכְתֹּב (we will write)."
        ),
        "qal_imperative": (
            "The imperative is the command form, based on the imperfect: "
            "2ms: כְּתֹב (write!), 2fs: כִּתְבִי (write! f.), "
            "2mp: כִּתְבוּ (write! pl.). Dropping the prefix from "
            "the imperfect gives the imperative."
        ),
        "qal_infinitive": (
            "The Qal Infinitive Construct is the 'to' form: "
            "לִכְתֹּב (to write). Always preceded by Lamed prefix. "
            "Used with prepositions for temporal clauses: "
            "בִּכְתֹב (when writing), כִּכְתֹב (as/when writing)."
        ),
        "qal_participle": (
            "The Qal Participle is a verbal adjective: "
            "Active: כֹּתֵב (writing / one who writes). "
            "Passive: כָּתוּב (written). "
            "Participles decline like adjectives (gender + number)."
        ),
        "niphal": (
            "Niphal is the simple PASSIVE/REFLEXIVE of Qal. "
            "Pattern: נִכְתַּב (it was written). "
            "Recognized by the נ (nun) prefix. Also used for "
            "simple reflexive: נִשְׁמַר (he guarded himself)."
        ),
        "piel": (
            "Piel is the INTENSIVE active binyan. It emphasizes "
            "intensity or repeated action. Pattern: כִּתֵּב (he wrote "
            "extensively). Marked by a dagesh forte in the middle "
            "root letter and a specific vowel pattern."
        ),
        "pual": (
            "Pual is the INTENSIVE PASSIVE of Piel. "
            "Pattern: כֻּתַּב (it was written extensively). "
            "Has a Qibbus (u) vowel under the first letter and "
            "dagesh forte in the middle root letter."
        ),
        "hiphil": (
            "Hiphil is the CAUSATIVE active binyan. It means "
            "'to cause X to do Y'. Pattern: הִכְתִּיב (he caused "
            "to write / dictated). Marked by ה (he) prefix and "
            "a characteristic 'i' vowel pattern."
        ),
        "hophal": (
            "Hophal is the CAUSATIVE PASSIVE of Hiphil. "
            "Pattern: הָכְתַּב (it was caused to be written). "
            "Has a Qamats under the prefix and a dagesh forte "
            "in the second root letter."
        ),
        "hithpael": (
            "Hithpael is the REFLEXIVE binyan. It describes "
            "action done to/for oneself. Pattern: הִתְכַּתֵּב "
            "(he corresponded / wrote to himself). Marked by "
            "הִתְ prefix and dagesh forte in the middle root."
        ),
    }
    return explanations.get(nid, f"{title}: A key concept in Biblical Hebrew {category}.")


def _worked_examples(nid, title, category):
    """Generate worked examples for a topic."""
    examples = {
        "aleph": [
            {"question": "How is Aleph (א) different from other letters?",
             "steps": ["Aleph is a glottal stop — it has no sound of its own.",
                       "It acts as a carrier for vowels.",
                       "Words beginning with a vowel sound start with Aleph (or Ayin).",
                       "Example: אָב (av = father) — the Aleph carries the Qamats vowel."],
             "answer": "Aleph is silent; it's a vowel carrier."},
        ],
        "bet": [
            {"question": "What's the difference between Bet and Vet?",
             "steps": ["Bet has a dagesh (dot) inside: בּ — sounds like 'b'.",
                       "Vet has no dagesh: ב — sounds like 'v'.",
                       "Example: בָּרָא (bārā' = he created) vs. בָּרָא (without dagesh: vārā').",
                       "Rule: at the beginning of a word, Bet usually has dagesh."],
             "answer": "Bet = b, Vet = v. The dagesh makes the difference."},
        ],
        "qal_perfect": [
            {"question": "Conjugate כָּתַב (katav = write) in Qal Perfect",
             "steps": ["3ms: כָּתַב (katáv) — he wrote",
                       "3fs: כָּתְבָה (kātǝvā́) — she wrote",
                       "2ms: כָּתַבְתָּ (kātávtā) — you wrote",
                       "1cs: כָּתַבְתִּי (kātávti) — I wrote",
                       "Pattern: Cā-CaC for 3ms, add suffixes for others"],
             "answer": "3ms כָּתַב, 3fs כָּתְבָה, 2ms כָּתַבְתָּ, 1cs כָּתַבְתִּי"},
        ],
        "vowel_qamats_qatan": [
            {"question": "Is this Qamats or Qamats Qatan? חָכְמָה (wisdom)",
             "steps": ["Identify the syllable: חָכְמָה = חָכְ·מָה",
                       "First syllable: חָ— closed? Yes (followed by silent sheva)",
                       "Unstressed closed syllable with qamats = Qamats Qatan",
                       "Pronounced: ḥoḵmāh (not ḥāḵmāh)",],
             "answer": "Qamats Qatan — pronounced 'o', not 'a'."},
        ],
    }
    return examples.get(nid, [
        {"question": f"What is {title}?",
         "steps": [f"{title} is a {category} in Biblical Hebrew.",
                   f"{_explanation(nid, title, category)[:100]}..."],
         "answer": f"See the explanation above."},
    ])


def _key_points(nid, category):
    """Generate key memorization points."""
    points = {
        "aleph": ["Silent letter — vowel carrier", "First letter of the aleph-bet",
                  "Numerical value: 1", "Cannot take dagesh forte"],
        "bet": ["B/V alternation via dagesh", "Begadkefat letter",
                "Numerical value: 2", "Prefix meaning 'in/with/by'"],
        "vowel_qamats_qatan": ["Looks like Qamats but sounds like 'o'",
                               "Occurs in closed unaccented syllables",
                               "Example: חָכְמָה (wisdom) → ḥoḵmāh"],
        "qal_perfect": ["Completed action (past tense)", "Uses SUFFIXES",
                        "3ms is the dictionary form", "Pattern: Cā-CaC"],
        "root_concept": ["3-consonant core carries meaning",
                         "Vowel patterns modify it",
                         "Root כ-ת-ב = writing",
                         "Identifying roots unlocks vocabulary"],
        "syllable_division": ["Each vowel = one syllable",
                              "Silent sheva closes a syllable",
                              "Vocal sheva starts a new syllable",
                              "Dagesh forte splits syllables"],
    }
    return points.get(nid, [f"Key concept in {category}", "Review the explanation above"])


def build_practice_items(nid, title, category):
    """Generate practice items for a topic with Math Academy quality."""
    items = []
    
    # Confusable pairs for smart distractors
    SIMILAR_LETTERS = {
        "aleph": ["Ayin", "He", "Chet"],
        "bet": ["Vav", "Kaf", "Bet"],
        "gimel": ["Nun", "Zayin", "Resh"],
        "dalet": ["Resh", "Dalet", "Vav"],
        "he": ["Chet", "Tav", "Aleph"],
        "vav": ["Bet", "Kaf", "Vav"],
        "zayin": ["Gimel", "Nun", "Zayin"],
        "chet": ["He", "Tav", "Ayin"],
        "tet": ["Tav", "Tet", "Qof"],
        "yod": ["Vav", "Yod", "Zayin"],
        "kaf": ["Kaf (final)", "Bet", "Kaf"],
        "lamed": ["Lamed", "Resh", "Vav"],
        "mem": ["Mem (final)", "Samekh", "Mem"],
        "nun": ["Nun (final)", "Gimel", "Nun"],
        "samekh": ["Mem", "Samekh", "Ayin"],
        "ayin": ["Aleph", "Chet", "Ayin"],
        "pe": ["Pe (final)", "Bet", "Pe"],
        "tsade": ["Tsade (final)", "Ayin", "Tsade"],
        "qof": ["Kaf", "Qof", "Resh"],
        "resh": ["Dalet", "Resh", "Zayin"],
        "shin": ["Sin", "Shin", "Samekh"],
        "sin": ["Shin", "Sin", "Samekh"],
        "tav": ["Tet", "Tav", "He"],
    }
    
    SIMILAR_VOWELS = {
        "vowel_patah": ["Qamats", "Segol", "Patah"],
        "vowel_qamats": ["Patah", "Qamats", "Holam"],
        "vowel_segol": ["Tsere", "Segol", "Sheva"],
        "vowel_tsere": ["Segol", "Tsere", "Hiriq"],
        "vowel_hiriq": ["Tsere", "Hiriq", "Segol"],
        "vowel_holam": ["Qamats", "Holam", "Shuruq"],
        "vowel_shuruq": ["Qubuts", "Shuruq", "Holam"],
        "vowel_qubuts": ["Shuruq", "Qubuts", "Holam"],
        "vowel_sheva": ["Sheva", "Hatef Patah", "Hatef Segol"],
    }
    
    # Recognition questions
    if category == "consonant":
        correct = title.split("(")[0].strip()
        # Smart distractors: use similar-looking/sounding letters
        similar = SIMILAR_LETTERS.get(nid, [])
        distractors = [s for s in similar if s != correct]
        # Fallback to random if not enough distractors
        all_letters = ["Aleph", "Bet", "Gimel", "Dalet", "He", "Vav", "Zayin", "Chet", "Tet", "Yod",
                       "Kaf", "Lamed", "Mem", "Nun", "Samekh", "Ayin", "Pe", "Tsade", "Qof", "Resh",
                       "Shin", "Sin", "Tav"]
        import random
        while len(distractors) < 3:
            d = random.choice(all_letters)
            if d != correct and d not in distractors:
                distractors.append(d)
        random.shuffle(distractors)
        opts = [correct] + distractors[:3]
        random.shuffle(opts)
        items.append({
            "question_type": "multiple_choice",
            "question_text": f"What is the name of this Hebrew letter: {title}?",
            "options": json.dumps(opts),
            "correct_answer": correct,
            "difficulty": 0.3,
            "explanation": f"The letter shown is {title}. It belongs to the Hebrew aleph-bet."
        })
        # Audio identification drill
        items.append({
            "question_type": "multiple_choice",
            "question_text": f"Which letter makes the sound described in the lesson for {title}?",
            "options": json.dumps(opts),
            "correct_answer": correct,
            "difficulty": 0.4,
            "explanation": f"The letter {title} makes this sound."
        })
        # Typing drill (production)
        items.append({
            "question_type": "typing",
            "question_text": f"Type the Hebrew letter: {correct}",
            "correct_answer": correct,
            "difficulty": 0.4,
            "explanation": f"The Hebrew letter {correct} looks like this in the script."
        })
        # Transliteration (Hebrew→English)
        items.append({
            "question_type": "transliteration",
            "question_text": f"How is this letter transliterated: {title}?",
            "correct_answer": correct,
            "difficulty": 0.3,
            "explanation": f"The letter {title} is transliterated as '{correct}'."
        })
        # Reverse: English→Hebrew
        items.append({
            "question_type": "recall",
            "question_text": f"What is the Hebrew letter named '{correct}'?",
            "correct_answer": correct,
            "difficulty": 0.5,
            "explanation": f"The Hebrew letter named '{correct}' is {title}."
        })
    
    elif category == "vowel":
        correct = title.split("(")[0].strip()
        # Smart distractors based on similar vowels
        similar = SIMILAR_VOWELS.get(nid, [])
        distractors = [s for s in similar if s != correct]
        all_vowels = ["Patah", "Qamats", "Segol", "Tsere", "Hiriq", "Holam", "Shuruq", "Qubuts",
                      "Sheva", "Hatef Patah", "Hatef Segol", "Hatef Qamats"]
        import random
        while len(distractors) < 3:
            d = random.choice(all_vowels)
            if d != correct and d not in distractors:
                distractors.append(d)
        random.shuffle(distractors)
        opts = [correct] + distractors[:3]
        random.shuffle(opts)
        items.append({
            "question_type": "multiple_choice",
            "question_text": f"Which Hebrew vowel makes the sound described by {title}?",
            "options": json.dumps(opts),
            "correct_answer": correct,
            "difficulty": 0.4,
            "explanation": f"This describes the vowel {title}."
        })
        items.append({
            "question_type": "recall",
            "question_text": f"Name the Hebrew vowel that sounds like {correct}.",
            "correct_answer": correct,
            "difficulty": 0.5,
            "explanation": f"The vowel is {correct}."
        })
    
    elif category == "verb":
        items.append({
            "question_type": "multiple_choice",
            "question_text": f"What is the function of the {title} binyan?",
            "options": json.dumps(["Simple active", "Simple passive", "Intensive", "Causative", "Reflexive"]),
            "correct_answer": {"niphal": "Simple passive", "piel": "Intensive",
                             "pual": "Intensive passive", "hiphil": "Causative",
                             "hophal": "Causative passive", "hithpael": "Reflexive",
                             "qal_perfect": "Simple active", "qal_imperfect": "Simple active",
                             "qal_imperative": "Simple active", "qal_infinitive": "Simple active",
                             "qal_participle": "Simple active"}.get(nid, "Simple active"),
            "difficulty": 0.6,
            "explanation": f"The {title} binyan indicates {_explanation(nid, title, category)[:60]}..."
        })

    # Parsing questions for all categories
    items.append({
        "question_type": "true_false",
        "question_text": f"Is '{title}' a {category} in Biblical Hebrew?",
        "options": json.dumps(["True", "False"]),
        "correct_answer": "True",
        "difficulty": 0.2,
        "explanation": f"Yes, {title} is a {category} concept."
    })

    return items


def seed_content(db_path="data/memorize.db"):
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    cur = conn.cursor()

    # Get all nodes
    nodes = cur.execute(
        "SELECT id, title, level, category, description FROM hebrew_nodes ORDER BY level, id"
    ).fetchall()

    # Clear existing
    cur.execute("DELETE FROM hebrew_lessons")
    cur.execute("DELETE FROM hebrew_practice_items")

    lesson_count = 0
    practice_count = 0

    for nid, title, level, category, desc in nodes:
        # Extract glyph from title (title format: "Name (glyph)")
        glyph = ""
        if "(" in title:
            glyph = title[title.index("(")+1:title.index(")")]
            clean_title = title[:title.index("(")].strip()
        else:
            clean_title = title

        # Build and save lesson
        lesson = build_lesson(nid, glyph, clean_title, category, desc)
        cur.execute(
            "INSERT OR REPLACE INTO hebrew_lessons (node_id, content_json, version) VALUES (?, ?, 1)",
            (nid, json.dumps(lesson)),
        )
        lesson_count += 1

        # Build and save practice items
        items = build_practice_items(nid, clean_title, category)
        for item in items:
            opts = item.get("options_json", item.get("options", "[]"))
            if isinstance(opts, str):
                opts_json = opts
            else:
                opts_json = json.dumps(opts)
            cur.execute(
                """INSERT INTO hebrew_practice_items
                   (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (nid, item["question_type"], item["question_text"],
                 opts_json, item["correct_answer"], item["difficulty"], item["explanation"])
            )
            practice_count += 1

    conn.commit()
    conn.close()

    print(f"Seeded {lesson_count} lessons")
    print(f"Seeded {practice_count} practice items")
    print(f"Nodes: {len(nodes)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/memorize.db")
    args = parser.parse_args()
    seed_content(args.db)
