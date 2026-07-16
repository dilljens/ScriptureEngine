#!/usr/bin/env python3
"""Add real verse examples to grammar lessons.

Adds scripture references to grammar lessons that currently lack them.
Each verse example shows the grammar point in its natural biblical context.

Usage:
    python3 scripts/add_grammar_verse_examples.py --dry-run    # Preview
    python3 scripts/add_grammar_verse_examples.py --apply     # Update lessons
"""

import argparse
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

# Lesson → [verse_ref, hebrew_text, english_text, grammar_highlight]
VERSE_EXAMPLES = {
    "begadkefat": [
        ("gen.1.1", "בְּרֵאשִׁית בָּרָא אֱלֹהִים",
         "In the beginning God created — bet without dagesh (v') vs bet with dagesh (b)",
         "בְּרֵאשִׁית (v) — bet without dagesh after vowel — soft V sound\nבָּרָא (b) — bet with dagesh after consonant — hard B sound"),
        ("exo.20.1", "וַיְדַבֵּר אֱלֹהִים",
         "And God spoke — vav-medaber, pe with dagesh vs without",
         "וַיְדַבֵּר — dalet with dagesh (hard D)"),
        ("deu.6.4", "שְׁמַע יִשְׂרָאֵל",
         "Hear O Israel — shin, ayin without dagesh",
         "שְׁמַע — ayin without dagesh (guttural, not affected by begadkefat)"),
    ],
    "pronominal_suffixes_nouns": [
        ("gen.1.26", "נַעֲשֶׂה אָדָם בְּצַלְמֵנוּ",
         "Let us make man in our image — בְּצַלְמֵנוּ = be+tsalme+nu = 'in our image'",
         "בְּצַלְמֵנוּ (our image) — suffix ־נוּ (1cp)"),
        ("psa.23.1", "יְהוָה רֹעִי",
         "The LORD is my shepherd — יְהוָה רֹעִי = YHWH ro'i = 'YHWH my shepherd'",
         "רֹעִי (my shepherd) — suffix ־ִי (1cs)"),
        ("gen.2.7", "עָפָר מִן־הָאֲדָמָה",
         "Dust from the ground — מִן־הָאֲדָמָה = min-ha-adamah",
         "Note: here the suffix is on the preposition מִן (from) — מִמֶּנּוּ with 3ms suffix"),
    ],
    "prepositions_with_suffixes": [
        ("psa.23.4", "כִּי אַתָּה עִמָּדִי",
         "For you are with me — עִמָּדִי = imadi = 'with me'",
         "עִמָּדִי (with me) — preposition עִם + 1cs suffix, with dagesh"),
        ("gen.3.15", "הוּא יְשׁוּפְךָ רֹאשׁ",
         "He will crush your head — יְשׁוּפְךָ = yeshuph'kha = 'he will crush you'",
         "יְשׁוּפְךָ — object suffix ־ךָ (2ms)"),
        ("gen.1.26", "בְּצַלְמֵנוּ כִּדְמוּתֵנוּ",
         "In our image, after our likeness — double preposition + suffix",
         "בְּצַלְמֵנוּ (in our image) — ב + צֶלֶם + 1cp suffix\nכִּדְמוּתֵנוּ (like our likeness)"),
    ],
    "object_suffixes_verbs": [
        ("gen.1.26", "נַעֲשֶׂה אָדָם",
         "Let us make man — 1cp volitive form",
         "נַעֲשֶׂה — Qal imperfect 1cp of עשה (to make)"),
        ("gen.4.1", "קָנִיתִי אִישׁ אֶת־יְהוָה",
         "I have gotten a man with the LORD — קָנִיתִי = kaniti = 'I have acquired'",
         "קָנִיתִי — Qal perfect 1cs of קנה, with 1cs subject (not object) suffix"),
    ],
    "infinitive_construct": [
        ("gen.2.17", "בְּיוֹם אֲכָלְךָ",
         "In the day of your eating — בְּ + infinitive construct + suffix",
         "בְּיוֹם אֲכָלְךָ — בְּ (in) + יוֹם (day) + infinitive construct אָכֹל with 2ms suffix"),
        ("exo.3.12", "בְּהוֹצִיאֲךָ אֶת־הָעָם",
         "When you bring out the people — בְּ + Hiphil infinitive + suffix",
         "בְּהוֹצִיאֲךָ — בְּ (in/when) + infinitive construct Hiphil of יצא + 2ms suffix"),
    ],
    "infinitive_absolute": [
        ("gen.2.17", "מוֹת תָּמוּת",
         "You shall surely die — infinitive absolute + finite verb for emphasis",
         "מוֹת תָּמוּת — infinitive absolute of מות + Qal imperfect 2ms = emphatic"),
        ("gen.22.17", "בָּרֵךְ אֲבָרֶכְךָ",
         "I will surely bless you — infinitve absolute + finite verb",
         "בָּרֵךְ אֲבָרֶכְךָ — infinitive absolute of ברך + Piel imperfect 1cs + 2ms suffix"),
        ("deu.6.17", "שָׁמוֹר תִּשְׁמְרוּן",
         "You shall diligently keep — infinitive absolute + finite verb",
         "שָׁמוֹר תִּשְׁמְרוּן — infinitive absolute + Qal imperfect 2mp + nun paragogicum"),
    ],
    "commands_jussive": [
        ("gen.1.3", "יְהִי אוֹר",
         "Let there be light — jussive form of היה",
         "יְהִי — Qal jussive 3ms of היה (to be). Short form of יִהְיֶה"),
        ("exo.20.13", "לֹא תִרְצָח",
         "You shall not murder — imperfect used for prohibition",
         "לֹא תִרְצָח — Qal imperfect 2ms of רצח. The negative לֹא + yiqtol for prohibition"),
        ("psa.104.31", "יְהִי כְבוֹד יְהוָה",
         "Let the glory of YHWH endure — jussive",
         "יְהִי — jussive (short form of yiqtol)"),
    ],
    "conditional_sentences": [
        ("gen.18.26", "אִם־יֵשׁ חֲמִשִּׁים",
         "If there are fifty — אִם־יֵשׁ = 'im-yesh'",
         "אִם־יֵשׁ — conditional particle אִם + existential יֵשׁ (there are)"),
        ("exo.19.5", "וְעַתָּה אִם־שָׁמוֹעַ תִּשְׁמְעוּ",
         "Now if you will indeed obey — אִם + infinitive absolute",
         "אִם־שָׁמוֹעַ תִּשְׁמְעוּ — אִם + infinitive absolute + yiqtol for emphasis"),
        ("isa.1.19", "אִם־תֹּאבוּ וּשְׁמַעְתֶּם",
         "If you are willing and obey — real condition with perfect/weqatal",
         "אִם־תֹּאבוּ — אִם + Qal imperfect 2mp. Followed by weqatal"),
    ],
    "numeral_agreement": [
        ("gen.1.9", "שְׁלֹשָׁה יָמִים",
         "Three days — masculine noun with masculine numeral (no reversal!)",
         "שְׁלֹשָׁה יָמִים — numeral שְׁלֹשָׁה (3) with יָמִים (masculine plural). The 'reversal' rule: 3-10 take opposite gender"),
        ("gen.6.15", "שְׁלֹשׁ מֵאוֹת אַמָּה",
         "Three hundred cubits — feminine numeral with feminine noun",
         "שְׁלֹשׁ מֵאוֹת — numeral שְׁלֹשׁ (3fs form) before feminine מֵאוֹת (hundreds)"),
        ("num.3.43", "עֶשְׂרִים וּשְׁלֹשָׁה אֶלֶף",
         "Twenty-three thousand — compound number",
         "עֶשְׂרִים וּשְׁלֹשָׁה אֶלֶף — 20 + 3 + thousand"),
    ],
    "cognate_accusative": [
        ("gen.37.5", "חָלַם חֲלוֹם",
         "He dreamed a dream — verb + cognate noun (same root: חלם)",
         "חָלַם חֲלוֹם — both from root ח-ל-ם. Verb Qal perfect 3ms + noun ms absolute"),
        ("gen.40.5", "שְׁנֵיהֶם אִישׁ חֲלֹמוֹ",
         "Both of them, each man his dream — same pattern repeated",
         "The dream narrative uses חלם/חלום multiple times as cognate accusative"),
        ("jonah.1.16", "וַיִּירְאוּ הָאֲנָשִׁים יִרְאָה",
         "The men feared a great fear — verb + cognate noun (same root: ירא)",
         "וַיִּירְאוּ... יִרְאָה — from root י-ר-א. Wayyiqtol 3mp + noun fs."),
    ],
    "emphatic_structures": [
        ("gen.1.5", "וַיִּקְרָא אֱלֹהִים לָאוֹר יוֹם",
         "God called the light 'day' — standard VSO word order",
         "Standard order: וַיִּקְרָא (V) אֱלֹהִים (S) לָאוֹר (O) יוֹם (complement)"),
        ("lev.19.32", "מִפְּנֵי שֵׂיבָה תָּקוּם",
         "You shall rise before the aged — fronted PP for emphasis",
         "מִפְּנֵי שֵׂיבָה (before aged) is fronted before the verb תָּקוּם (you shall rise)"),
    ],
    "waw_relative": [
        ("gen.3.12", "הָאִשָּׁה אֲשֶׁר נָתַתָּה",
         "The woman whom you gave — relative clause with אֲשֶׁר",
         "אֲשֶׁר נָתַתָּה — relative particle + Qal perfect 2ms. The woman 'who' you gave"),
        ("exo.3.14", "אֶהְיֶה אֲשֶׁר אֶהְיֶה",
         "I AM WHO I AM — relative clause as divine name",
         "אֲשֶׁר אֶהְיֶה — relative particle + Qal imperfect 1cs of היה"),
    ],
}


def add_verse_examples(dry_run=True):
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    updated = 0

    for lesson_id, examples in VERSE_EXAMPLES.items():
        row = conn.execute(
            "SELECT content_json FROM hebrew_lessons WHERE node_id = ?", (lesson_id,)
        ).fetchone()
        if not row:
            print(f"  SKIP {lesson_id}: lesson not found")
            continue

        content = json.loads(row["content_json"])
        verse_refs = [{"ref": r, "hebrew": h, "english": e, "highlight": g} for r, h, e, g in examples]
        content["verse_examples"] = verse_refs

        if not dry_run:
            conn.execute(
                "UPDATE hebrew_lessons SET content_json = ? WHERE node_id = ?",
                (json.dumps(content, ensure_ascii=False), lesson_id)
            )
        updated += 1
        print(f"  {lesson_id}: added {len(examples)} verse examples")

    conn.commit()
    conn.close()
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Updated {updated} lessons")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add verse examples to grammar lessons")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print("=== Adding Verse Examples to Grammar Lessons ===")
    add_verse_examples(dry_run=not args.apply)
