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
        "derived_words": [("כָּתַב", "he wrote"), ("כְּתָב", "writing"), ("כְּתֹבֶת", "inscription"), ("סֵפֶר", "book/scroll")],
        "explanation": "The root כ־ת־ב (K-T-V) means 'to write' or 'engrave'. It's one of the most productive roots in Hebrew. The Qal verb כָּתַב means 'he wrote'. The noun כְּתָב means 'writing' or 'script'. The common word סֵפֶר (book/scroll) also derives from this root."
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
        "derived_words": [("בָּרַךְ", "he blessed"), ("בְּרָכָה", "blessing"), ("בָּרוּךְ", "blessed"), ("בְּרֵכָה", "pool (blessing place)")],
        "explanation": "The root ב־ר־ך (B-R-K) means 'to bless'. The first occurrence is Genesis 1:22 where God blessed the creatures. The Piel form (בֵּרַךְ) is the most common verb. בָּרוּךְ ('blessed') begins many prayers (בָּרוּךְ אַתָּה יְהוָה = Blessed are you, YHWH)."
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
        "explanation": "The root י־ר־א (Y-R-A) means 'to fear' or 'revere'. יִרְאַת יְהוָה (fear of YHWH) is the 'beginning of wisdom' (Proverbs 1:7). יָרֵא as an adjective means 'God-fearing' — a key description of righteous people. This is not fright but reverential awe."
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
        "derived_words": [("חָטָא", "he sinned"), ("חַטָּאת", "sin/sin-offering"), ("חֵטְא", "sin"), ("חָטָא", "sinner")],
        "explanation": "The root ח־ט־א (Ch-T-A) literally means 'to miss the mark'. חָטָא is the Qal verb. חַטָּאת means both 'sin' and 'sin-offering' — the same word! This double meaning is theologically rich: the same word describes the problem and God's solution. The Day of Atonement (יוֹם כִּפּוּר) centers on purging חַטָּאת."
    },
]


def main():
    conn = sqlite3.connect(str(MEM_DB))
    conn.execute("PRAGMA foreign_keys=OFF")
    
    new_nodes = 0
    new_items = 0
    new_edges = 0
    
    for lesson in ROOT_LESSONS:
        lid = f"root_{lesson['root']}"
        
        existing = conn.execute("SELECT id FROM hebrew_nodes WHERE id=?", (lid,)).fetchone()
        if existing:
            print(f"  SKIP {lid}: already exists")
            continue
        
        title = f"Root {lesson['root']} — {lesson['meaning']}"
        desc = f"The root {lesson['root']} means '{lesson['meaning']}'. Derived words: " + ", ".join(f"{w} ({g})" for w, g in lesson['derived_words'])
        
        conn.execute(
            "INSERT INTO hebrew_nodes (id, title, level, category, description) VALUES (?, ?, ?, 'root', ?)",
            (lid, title, lesson['level'], desc[:200])
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
                f"Key theological term in Biblical Hebrew",
            ],
        }
        conn.execute(
            "INSERT INTO hebrew_lessons (node_id, content_json) VALUES (?, ?)",
            (lid, json.dumps(content, ensure_ascii=False))
        )
        
        # Practice items
        def add(q, opts, ans, qtype="multiple_choice"):
            opts_j = json.dumps(opts, ensure_ascii=False) if opts else ""
            conn.execute("INSERT INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty) VALUES (?,?,?,?,?,?)",
                        (lid, qtype, q, opts_j, ans, 0.5))
            nonlocal new_items
            new_items += 1
        
        add(f"What is the root {lesson['root']} mean?", [lesson['meaning'], "king", "write", "speak"], lesson['meaning'])
        add(f"Which word derives from root {lesson['root']}?", [w for w, g in lesson['derived_words'][:4]] or ["word"], lesson['derived_words'][0][0])
        
        # Find a verse example
        try:
            conn2 = sqlite3.connect(str(DB_PATH))
            for w, g in lesson['derived_words']:
                row = conn2.execute("SELECT v.id, v.text_hebrew FROM verses v JOIN gematria g ON g.verse_id=v.id WHERE g.word_hebrew LIKE ? LIMIT 1", (f'%{w}%',)).fetchone()
                if row:
                    add(f"Find verse containing '{w}' (from root {lesson['root']})", [w, lesson['root'], "word", "verse"], w)
                    break
            conn2.close()
        except:
            pass
        
        # Prerequisites
        conn.execute("INSERT OR IGNORE INTO hebrew_edges (source_id, target_id, edge_type) VALUES ('root_concept', ?, 'prerequisite')", (lid,))
        new_edges += 1
        
        print(f"  CREATED {lid}: {title}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✓ Done! Created {new_nodes} root lessons, {new_items} items, {new_edges} edges")


if __name__ == '__main__':
    main()
