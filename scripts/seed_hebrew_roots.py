#!/usr/bin/env python3
"""Seed triconsonantal root system lessons.

For each major root, create a lesson showing:
- Root letters and core meaning
- Derived words (nouns, verbs, adjectives from this root)
- Key verses showing the root in action
- Recognition and production practice
"""

import json
import sqlite3
from pathlib import Path

MEM_DB = Path(__file__).parent.parent / "data" / "memorize.db"
DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


ROOT_LESSONS = [
    {
        "root": "כתב",
        "meaning": "write",
        "level": 5,
        "derived_words": [("כָּתַב", "he wrote"), ("כְּתָב", "writing"), ("כְּתֹבֶת", "inscription"), ("מִכְתָּב", "writing/document")],
        "explanation": "The root כ־ת־ב (K-T-V) means 'to write' or 'engrave'. It's one of the most productive roots in Hebrew. The Qal verb כָּתַב means 'he wrote'. The nouns כְּתָב and מִכְתָּב refer to writing or a written document. סֵפֶר (book/scroll) belongs to the separate root ס־פ־ר."
    },
    {
        "root": "מלך",
        "meaning": "king, rule",
        "level": 4,
        "derived_words": [("מֶלֶךְ", "king"), ("מַלְכָּה", "queen"), ("מַלְכוּת", "kingdom"), ("הִמְלִיךְ", "he made king")],
        "explanation": "The root מ־ל־ך (M-L-K) conveys kingship and rule. מֶלֶךְ is 'king', מַלְכָּה is 'queen', מַלְכוּת is 'kingdom' or 'royalty'. The verb מָלַךְ means 'he reigned'. This root is central to Israel's theology of God as King (יהוה מֶלֶךְ)."
    },
    {
        "root": "דבר",
        "meaning": "speak, word",
        "level": 4,
        "derived_words": [("דָּבָר", "word/thing"), ("דִּבֵּר", "he spoke (Piel)"), ("דְּבָרִים", "words/things"), ("דַּבָּר", "spokesman")],
        "explanation": "The root ד־ב־ר (D-B-R) means 'to speak' or 'arrange'. דָּבָר (word/thing) is one of the most common nouns. דִּבֵּר (Piel) is 'he spoke'. The book of Deuteronomy is called דְּבָרִים (words) in Hebrew. God's 'word' (דְּבַר־יְהוָה) is a key theological concept."
    },
    {
        "root": "שמר",
        "meaning": "keep, guard",
        "level": 4,
        "derived_words": [("שָׁמַר", "he kept"), ("שְׁמָר", "guard"), ("שְׁמִירָה", "guarding"), ("מִשְׁמֶרֶת", "watch/guard duty")],
        "explanation": "The root שׁ־מ־ר (SH-M-R) means 'to keep, guard, or watch'. שָׁמַר is the Qal verb. The related noun שְׁמָר means 'guard' or 'watcher'. The Mishmarot (priestly courses) derives from this root. 'Keep the commandments' = שָׁמַר אֶת־הַמִּצְוֹת."
    },
    {
        "root": "עבד",
        "meaning": "serve, work",
        "level": 4,
        "derived_words": [("עָבַד", "he served/worked"), ("עֶבֶד", "servant/slave"), ("עֲבוֹדָה", "work/service"), ("עֲבֹדָה", "slavery")],
        "explanation": "The root ע־ב־ד (A-V-D) means 'to serve' or 'work'. עֶבֶד ('servant') is a key title for prophets (עֶבֶד יְהוָה = servant of YHWH). עֲבוֹדָה means 'work' or 'service'. This root is central to the covenant relationship: serving God vs serving other gods."
    },
    {
        "root": "קדש",
        "meaning": "holy, set apart",
        "level": 5,
        "derived_words": [("קָדוֹשׁ", "holy"), ("קֹדֶשׁ", "holiness"), ("הִקְדִּישׁ", "he consecrated"), ("מִקְדָּשׁ", "sanctuary")],
        "explanation": "The root ק־ד־ש (Q-D-SH) means 'to be holy' or 'set apart'. קָדוֹשׁ ('holy') is God's primary attribute (קָדוֹשׁ קָדוֹשׁ קָדוֹשׁ = Holy, Holy, Holy). קֹדֶשׁ is 'holiness'. מִקְדָּשׁ is 'sanctuary' or 'holy place'. This root is fundamental to Israel's worship system."
    },
    {
        "root": "ברך",
        "meaning": "bless",
        "level": 4,
        "derived_words": [("בֵּרַךְ", "he blessed (Piel)"), ("בְּרָכָה", "blessing"), ("בָּרוּךְ", "blessed"), ("בֶּרֶךְ", "knee")],
        "explanation": "The root ב־ר־ך (B-R-K) has senses connected with blessing and kneeling. The first blessing use occurs in Genesis 1:22. The Piel form בֵּרַךְ is the common verb 'he blessed'; Qal forms are associated with kneeling. בָּרוּךְ means 'blessed'."
    },
    {
        "root": "שפט",
        "meaning": "judge",
        "level": 5,
        "derived_words": [("שָׁפַט", "he judged"), ("שֹׁפֵט", "judge"), ("מִשְׁפָּט", "judgment/justice"), ("שְׁפִיטָה", "jurisdiction")],
        "explanation": "The root שׁ־פ־ט (SH-P-T) means 'to judge'. מִשְׁפָּט ('justice/judgment') is a key covenant term. The book of שֹׁפְטִים (Judges/Shophtim) uses this root. God is called שׁוֹפֵט כָּל־הָאָרֶץ (Judge of all the earth). 'Do justice' = עֲשׂוֹת מִשְׁפָּט."
    },
    {
        "root": "צדק",
        "meaning": "righteous",
        "level": 5,
        "derived_words": [("צַדִּיק", "righteous"), ("צֶדֶק", "righteousness"), ("צְדָקָה", "righteousness/charity"), ("הִצְדִּיק", "he justified")],
        "explanation": "The root צ־ד־ק (TZ-D-K) means 'to be righteous'. צַדִּיק is a 'righteous person'. צֶדֶק and צְדָקָה both mean 'righteousness'. This root is central to the covenant: Abraham believed and it was counted to him as צְדָקָה (righteousness). God is called יְהוָה צִדְקֵנוּ (YHWH our Righteousness)."
    },
    {
        "root": "חנן",
        "meaning": "grace, favor",
        "level": 5,
        "derived_words": [("חָנַן", "he showed favor"), ("חֵן", "grace/favor"), ("חִנָּם", "freely/without cost"), ("תְּחִנָּה", "supplication/prayer")],
        "explanation": "The root ח־נ־נ (Ch-N-N) means 'to show favor or grace'. חֵן ('grace/favor') is a common noun. The verb חָנַן appears frequently in prayers: חָנֵּנִי (be gracious to me). The phrase 'finding favor in someone's eyes' (מָצָא חֵן בְּעֵינֵי) is a key idiom."
    },
    {
        "root": "אהב",
        "meaning": "love",
        "level": 4,
        "derived_words": [("אָהַב", "he loved"), ("אַהֲבָה", "love"), ("אֶהֶב", "beloved"), ("אֲהוּב", "beloved one")],
        "explanation": "The root א־ה־ב (A-H-V) means 'to love'. אָהַב is the Qal verb. אַהֲבָה is 'love'. The Shema (Deut 6:5) commands: וְאָהַבְתָּ אֵת יְהוָה אֱלֹהֶיךָ (You shall love YHWH your God). This root expresses covenant love, not just emotion."
    },
    {
        "root": "ירא",
        "meaning": "fear, revere",
        "level": 4,
        "derived_words": [("יָרֵא", "he feared"), ("יִרְאָה", "fear"), ("יָרֵא", "fearing/God-fearing"), ("מוֹרָא", "terror/fearful thing")],
        "explanation": "The root י־ר־א (Y-R-A) can mean 'to fear' or 'revere'. Proverbs 1:7 calls יִרְאַת יְהוָה the beginning of knowledge; Proverbs 9:10 relates it to the beginning of wisdom. Context determines whether fear, awe, or reverence is prominent."
    },
    {
        "root": "עשׂה",
        "meaning": "make, do",
        "level": 4,
        "derived_words": [("עָשָׂה", "he made/did"), ("מַעֲשֶׂה", "work/deed"), ("עֲשִׂיָּה", "making/doing"), ("עֹשֶׂה", "maker/doer")],
        "explanation": "The root ע־שׂ־ה (A-S-H) means 'to make' or 'do'. עָשָׂה is one of the most common verbs. It's the verb used for God's creation of the firmament (Gen 1:7). מַעֲשֶׂה means 'work' or 'deed'. The Sabbath command: לֹא־תַעֲשֶׂה כָל־מְלָאכָה (you shall not do any work)."
    },
    {
        "root": "שלם",
        "meaning": "peace, complete",
        "level": 4,
        "derived_words": [("שָׁלֵם", "complete/whole"), ("שָׁלוֹם", "peace"), ("שִׁלֵּם", "he paid/repaid"), ("שְׁלֵמוּת", "completeness")],
        "explanation": "The root שׁ־ל־ם (SH-L-M) means 'to be complete or whole'. שָׁלוֹם ('peace') is far richer than just absence of conflict — it means wholeness, well-being. The greeting שָׁלוֹם עֲלֵיכֶם (peace be upon you) derives from this root. The verb שִׁלֵּם means 'to repay' (making something whole)."
    },
    {
        "root": "פקד",
        "meaning": "visit, appoint",
        "level": 6,
        "derived_words": [("פָּקַד", "he visited/appointed"), ("פְּקֻדָּה", "appointment/order"), ("פְּקִיד", "official"), ("מִפְקָד", "census/numbering")],
        "explanation": "The root פ־ק־ד (P-K-D) has a rich range: 'to visit, appoint, muster, or command'. When God 'visits' (פָּקַד), it means He intervenes — either for blessing or judgment. פְּקֻדָּה means 'charge' or 'appointment'. מִפְקָד is a 'census' (the book of Numbers is called בְּמִדְבַּר in Hebrew)."
    },
    {
        "root": "גאל",
        "meaning": "redeem",
        "level": 5,
        "derived_words": [("גָּאַל", "he redeemed"), ("גֹּאֵל", "redeemer"), ("גְּאֻלָּה", "redemption"), ("יִגְאָל", "he will redeem")],
        "explanation": "The root ג־א־ל (G-A-L) means 'to redeem' or 'act as kinsman-redeemer'. The גֹּאֵל (goel) is a family member who redeems a relative from slavery or poverty. This root becomes a KEY THEOLOGICAL term for God as Israel's Redeemer (גֹּאֵל יִשְׂרָאֵל). The book of Ruth centers on this concept."
    },
    {
        "root": "חטא",
        "meaning": "sin, miss",
        "level": 5,
        "derived_words": [("חָטָא", "he sinned"), ("חַטָּאת", "sin/purification offering"), ("חֵטְא", "sin"), ("חֹטֵא", "one who sins")],
        "explanation": "The root ח־ט־א (Ch-T-A) covers failing, doing wrong, and sinning; in some contexts the verb can describe missing a target, but that image does not define every occurrence. חָטָא is 'he sinned' and חֹטֵא is a participle, 'one who sins.' Depending on context, חַטָּאת can denote sin or a purification offering. Theological conclusions should be labeled separately from these lexical observations."
    },
]


def main(db_path=MEM_DB):
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_hebrew_practice_unique
                    ON hebrew_practice_items(node_id,question_type,question_text,correct_answer)""")

    new_nodes = 0
    new_items = 0
    new_edges = 0

    for lesson in ROOT_LESSONS:
        lid = f"root_{lesson['root']}"

        title = f"Root {lesson['root']} — {lesson['meaning']}"
        desc = f"The root {lesson['root']} means '{lesson['meaning']}'. Derived words: " + ", ".join(f"{w} ({g})" for w, g in lesson['derived_words'])

        conn.execute(
            "INSERT OR IGNORE INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'root', ?)",
            (lid, title, lesson['level'], desc[:200])
        )
        conn.execute(
            "UPDATE hebrew_nodes SET title=?, level=?, category='root', description=? WHERE id=?",
            (title, lesson['level'], desc[:200], lid)
        )
        new_nodes += 1

        # Content
        content = {
            "node_id": lid,
            "title": title,
            "root": lesson['root'],
            "category": "root",
            "level": lesson['level'],
            "explanation": lesson['explanation'],
            "derived_words": [{"word": w, "gloss": g} for w, g in lesson['derived_words']],
            "key_points": [
                f"Root {lesson['root']} = {lesson['meaning']}",
                f"Derives {len(lesson['derived_words'])}+ common words",
                "Confirm each derived word and contextual sense in a lexicon",
            ],
        }
        conn.execute(
            """INSERT INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)
               ON CONFLICT(node_id) DO UPDATE SET content_json=excluded.content_json,
               version=hebrew_lessons.version+1, updated_at=datetime('now')
               WHERE hebrew_lessons.content_json<>excluded.content_json""",
            (lid, json.dumps(content, ensure_ascii=False))
        )

        # Practice items
        def add(q, opts, ans, qtype="multiple_choice", lid=lid):
            opts_j = json.dumps(opts, ensure_ascii=False) if opts else ""
            conn.execute(
                "DELETE FROM hebrew_practice_items WHERE node_id=? AND question_type=? AND question_text=? AND correct_answer<>?",
                (lid, qtype, q, ans),
            )
            conn.execute("INSERT OR IGNORE INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty) VALUES (?,?,?,?,?,?)",
                        (lid, qtype, q, opts_j, ans, 0.5))
            nonlocal new_items
            new_items += 1

        distractors = [value for value in ("king", "write", "speak", "serve", "judge") if value != lesson['meaning']]
        add(f"What does the root {lesson['root']} mean?", [lesson['meaning'], *distractors[:3]], lesson['meaning'])
        add(f"Which word derives from root {lesson['root']}?", [w for w, g in lesson['derived_words'][:4]] or ["word"], lesson['derived_words'][0][0])

        # Gloss→word question for a second derived word (real options; answer not
        # revealed by the question). Prefer a word whose gloss is distinct.
        if len(lesson['derived_words']) >= 2:
            opts = [w for w, _g in lesson['derived_words'][:4]]
            target = None
            for w, g in lesson['derived_words'][1:]:
                if w not in opts:
                    opts = [w for w, _g in lesson['derived_words'][:4]]
                if g not in (dg for dw, dg in lesson['derived_words'] if dw == w):
                    target = (w, g)
                    break
            if target is None:
                target = lesson['derived_words'][1]
            add(f"Which word from root {lesson['root']} means '{target[1]}'?",
                [w for w, _g in lesson['derived_words'][:4]], target[0])

        # Prerequisites
        conn.execute("INSERT OR IGNORE INTO hebrew_edges (source_id, target_id, edge_type) VALUES ('root_concept', ?, 'prerequisite')", (lid,))
        new_edges += 1

        print(f"  UPSERTED {lid}: {title}")

    conn.commit()
    conn.close()

    print(f"\n✓ Done! Created {new_nodes} root lessons, {new_items} items, {new_edges} edges")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=MEM_DB)
    args = parser.parse_args()
    main(args.db)
