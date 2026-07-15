#!/usr/bin/env python3
"""Seed common biblical Hebrew phrase lessons.

Teaches formulaic expressions that appear repeatedly in the Bible:
prophetic formulas, covenant language, liturgical expressions.
"""

import json
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"

PHRASE_LESSONS = [
    {
        "id": "phrase_thus_says",
        "title": "כֹּה אָמַר יְהוָה — Thus Says YHWH",
        "level": 4,
        "explanation": """This is THE classic prophetic formula — occurring hundreds of times in the prophets.

  כֹּה = thus/so
  אָמַר = he said (Qal perfect)
  יְהוָה = YHWH the LORD

  כֹּה אָמַר יְהוָה = "Thus says YHWH"

This formula introduces a divine oracle. The prophet speaks on God's behalf using this phrase. When you see it, pay attention — a message from God follows.

  Variation: כֹּה אָמַר יְהוָה אֱלֹהֵי יִשְׂרָאֵל
  = "Thus says YHWH, the God of Israel"

Usage: Over 400x in Jeremiah and Isaiah alone.""",
        "key_points": ["Prophetic speech formula", "כֹּה = thus", "אָמַר יְהוָה = YHWH said", "Over 400 occurrences", "Introduces divine oracles"],
    },
    {
        "id": "phrase_word_of_lord",
        "title": "דְּבַר־יְהוָה — The Word of YHWH",
        "level": 4,
        "explanation": """This is another key prophetic formula:

  דְּבַר = construct of דָּבָר (word)
  יְהוָה = YHWH

  דְּבַר־יְהוָה = "The word of YHWH"

This phrase frequently appears in:
  וַיְהִי דְּבַר־יְהוָה אֶל... = "And the word of YHWH came to..."

  וַיְהִי = and it came to pass / and it was
  דְּבַר־יְהוָה = the word of YHWH
  אֶל־ = to (preposition)

This pattern introduces prophetic oracles: "The word of YHWH came to Jeremiah/Isaiah/Ezekiel..."

  Also: דְּבַר יְהוָה alone can mean the divine message or God's command.""",
        "key_points": ["דְּבַר־יְהוָה = word of YHWH", "Key prophetic formula", "וַיְהִי דְּבַר־יְהוָה אֶל = and the word of YHWH came to", "Opens many prophetic books"],
    },
    {
        "id": "phrase_blessed_be",
        "title": "בָּרוּךְ יְהוָה — Blessed Be YHWH",
        "level": 4,
        "explanation": """A common liturgical blessing formula:

  בָּרוּךְ = blessed (Qal passive participle)
  יְהוָה = YHWH

  בָּרוּךְ יְהוָה = "Blessed is YHWH" / "Blessed be YHWH"

Full form:
  בָּרוּךְ אַתָּה יְהוָה = "Blessed are you, YHWH" (direct address)

Extended:
  בָּרוּךְ יְהוָה אֱלֹהֵי יִשְׂרָאֵל
  = "Blessed be YHWH, the God of Israel"

Used in prayers, Psalms, and narrative responses to God's deliverance.
  בָּרוּךְ יְהוָה אֲשֶׁר = "Blessed be YHWH who..." (introduces a reason for blessing)

This structure (passive participle + divine name) is the standard blessing form.""",
        "key_points": ["בָּרוּךְ = blessed (passive participle)", "בָּרוּךְ יְהוָה = blessed be YHWH", "Key liturgical formula", "בָּרוּךְ אַתָּה יְהוָה = blessed are you, YHWH"],
    },
    {
        "id": "phrase_fear_not",
        "title": "אַל־תִּירָא — Do Not Fear",
        "level": 4,
        "explanation": """One of the most comforting phrases in the Bible:

  אַל = negative particle (soft prohibition)
  תִּירָא = you will fear (Qal imperfect 2ms)

  אַל־תִּירָא = "Do not fear!"

This phrase appears dozens of times, often spoken by:
• God to patriarchs (Gen 15:1 — to Abraham)
• Angels (Luke 1:13, 30 — to Zacharias and Mary)
• Prophets to Israel

Variations:
  אַל־תִּירְאוּ = "Do not fear" (plural)
  אַל־תִּירְאִי = "Do not fear" (feminine)
  אַל־יִירָא = "Let him not fear" (jussive)

The repeated command "Do not fear" is a key Biblical theme — God's people are called to trust, not be afraid.""",
        "key_points": ["אַל־תִּירָא = do not fear", "Most common divine reassurance formula", "אַל = soft negative", "תִּירָא = Qal imperfect 2ms of ירא"],
    },
    {
        "id": "phrase_hear_o_israel",
        "title": "שְׁמַע יִשְׂרָאֵל — Hear O Israel (The Shema)",
        "level": 4,
        "explanation": """The most famous verse in the Torah:

  שְׁמַע = hear! (Qal imperative 2ms)
  יִשְׂרָאֵל = Israel

  שְׁמַע יִשְׂרָאֵל = "Hear, O Israel"

Full text (Deut 6:4-9):
  שְׁמַע יִשְׂרָאֵל יְהוָה אֱלֹהֵינוּ יְהוָה אֶחָד
  "Hear, O Israel: YHWH our God, YHWH is One!"

  וְאָהַבְתָּ אֵת יְהוָה אֱלֹהֶיךָ
  "And you shall love YHWH your God..."

This passage (the Shema) is the central confession of Jewish faith. It's recited daily by observant Jews. The verb שָׁמַע (hear) implies obedience — to 'hear' in Hebrew means to obey.""",
        "key_points": ["שְׁמַע יִשְׂרָאֵל = hear O Israel", "The Shema — central Jewish confession", "שְׁמַע = hear/obey (imperative)", "Daily prayer for observant Jews"],
    },
    {
        "id": "phrase_glory_to_god",
        "title": "לְיְהוָה הַכָּבוֹד — To YHWH Be the Glory",
        "level": 5,
        "explanation": """A common ascription of praise:

  לְ = to (preposition)
  יְהוָה = YHWH
  הַ = the (definite article)
  כָּבוֹד = glory/honor

  לַיְהוָה הַכָּבוֹד = "To YHWH be the glory!"

Similar patterns:
  לְיְהוָה הַיְשׁוּעָה = "To YHWH belongs deliverance" (Psalm 3:8)
  לְיְהוָה הָאָרֶץ וּמְלוֹאָהּ = "To YHWH belongs the earth and its fullness"

The construction uses לְ (to/belongs to) + noun to express possession or attribution. This is the standard way to say something belongs to someone.

Also: כָּבוֹד (glory/honor) is a key theological term. God's כָּבוֹד is His manifest presence — the weightiness of His being.""",
        "key_points": ["כָּבוֹד = glory/honor/weight", "לְיְהוָה = to YHWH (belongs to)", "לְ + noun = possession formula", "Common in Psalms"],
    },
    {
        "id": "phrase_behold_i_am",
        "title": "הִנְנִי — Behold, Here I Am",
        "level": 4,
        "explanation": """A powerful one-word response:

  הִנְנִי = behold me / here I am

This word combines:
  הִנֵּה = behold/see
  נִי = me (1cs object suffix)

  הִנְנִי = "Behold, I am here!" / "Here I am!"

This is the response of key Biblical figures when God calls them:
• Abraham (Gen 22:1) — when God tested him
• Moses (Exod 3:4) — at the burning bush
• Samuel (1 Sam 3:4) — as a boy
• Isaiah (Isa 6:8) — "Whom shall I send?" → הִנְנִי שְׁלָחֵנִי = "Here am I, send me!"

It expresses READINESS AND AVAILABILITY to serve.

  הִנְנִי also appears in judgment: הִנְנִי עַל... = "Behold, I am against..." (of God against evildoers)""",
        "key_points": ["הִנְנִי = here I am / behold me", "Response to God's call", "Key word for Abraham, Moses, Samuel, Isaiah", "הִנֵּה + נִי = behold + me"],
    },
    {
        "id": "phrase_in_that_day",
        "title": "בַּיּוֹם הַהוּא — In That Day",
        "level": 5,
        "explanation": """A key eschatological/time formula:

  בַּ = in (preposition ב + article הַ)
  יוֹם = day
  הַהוּא = that (demonstrative)

  בַּיּוֹם הַהוּא = "In that day"

This phrase appears dozens of times, especially in the prophets. It refers to:
• A specific time in the narrative (past)
• The eschatological 'Day of YHWH' (future judgment/deliverance)

  בַּיָּמִים הָהֵם = "In those days" (plural)

The formula has TWO uses you must distinguish:
1. Historical: "In that day" referring back to a time just mentioned
2. Prophetic: "In that day" referring to God's future intervention

Also: יוֹם יְהוָה = "The Day of YHWH" — a key prophetic concept of divine judgment.""",
        "key_points": ["בַּיּוֹם הַהוּא = in that day", "Dual use: historical + eschatological", "Key prophetic formula", "יוֹם יְהוָה = day of YHWH"],
    },
]


def main():
    conn = sqlite3.connect(str(MEM_DB))
    conn.execute("PRAGMA foreign_keys=OFF")

    new_nodes = 0
    new_items = 0

    for lesson in PHRASE_LESSONS:
        lid = lesson["id"]

        existing = conn.execute("SELECT id FROM hebrew_practice_items WHERE node_id=? LIMIT 1", (lid,)).fetchone()
        if existing:
            print(f"  SKIP {lid}: practice items already exist")
            continue

        conn.execute(
            "INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'phrase', ?)",
            (lid, lesson['title'], lesson['level'], lesson['explanation'][:100])
        )
        new_nodes += 1

        content = {
            "node_id": lid,
            "title": lesson['title'],
            "category": "phrase",
            "level": lesson['level'],
            "explanation": lesson['explanation'],
            "key_points": lesson['key_points'],
        }
        conn.execute(
            "INSERT OR IGNORE INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
            (lid, json.dumps(content, ensure_ascii=False))
        )

        # Practice items
        def add(q, opts, ans, qtype="multiple_choice", lid=lid):
            opts_j = json.dumps(opts, ensure_ascii=False) if opts else ""
            conn.execute("INSERT OR IGNORE INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty) VALUES (?,?,?,?,?,?)",
                        (lid, qtype, q, opts_j, ans, 0.5))
            nonlocal new_items
            new_items += 1

        # Basic recognition
        title = lesson['title']
        hebrew_part = title.split('—')[0].strip()
        english_part = title.split('—')[1].strip() if '—' in title else ''

        add(f"What does '{hebrew_part}' mean?", [english_part, "The end", "God is great", "Peace"],
            english_part if english_part else hebrew_part)
        add(f"Translate: {hebrew_part}", [english_part, "Hello", "Goodbye", "Amen"],
            english_part if english_part else hebrew_part)

        # Key point recall
        for kp in lesson['key_points'][:3]:
            add(f"Complete: {kp.split('=')[0].strip()} = ?", ["—", "—", "—", "—"], kp, "recall")

        print(f"  CREATED {lid}: {lesson['title']}")

    conn.commit()
    conn.close()

    print(f"\n✓ Done! Created {new_nodes} phrase lessons, {new_items} items")


if __name__ == '__main__':
    main()
