#!/usr/bin/env python3
"""
Second pass: fix remaining vocabulary issues missed by the first pass.

1. Entries with old glosses still in practice items (parenthetical position)
2. Entries missed entirely by the first correction map
3. Remaining archaic/weird glosses
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"

# Additional corrections — entries missed in first pass
ADDITIONAL_CORRECTIONS = {
    "vocab_נאם_76":   {"hebrew": "נְאֻם", "gloss": "utterance / declaration / oracle", "title": "נְאֻם — utterance, declaration, oracle"},
    "vocab_בקרב_182": {"hebrew": "קֶרֶב", "gloss": "midst / among / inward part", "title": "קֶרֶב — midst, inward part"},
    "vocab_ספר_253":  {"gloss": "book / scroll"},
    "vocab_בל_462":   {"gloss": "not / without"},
    "vocab_כבד_338":  {"gloss": "heavy / glorious / honorable"},
    "vocab_רבה_79":   {"gloss": "to be many / to become great / much"},
    "vocab_רב_439":   {"hebrew": "רַב", "gloss": "much / many / great", "title": "רַב — much, many, great"},
    "vocab_לבדו_234":  {"hebrew": "לְבָד", "gloss": "alone / only / apart", "title": "לְבָד — alone, only"},
    "vocab_מעט_437":  {"gloss": "little / few / a little while"},
    "vocab_חי_221":   {"gloss": "alive / living"},
    "vocab_מת_73":    {"hebrew": "מָוֶת", "gloss": "death", "title": "מָוֶת — death"},
    "vocab_חיה_146":  {"gloss": "living creature / animal / life"},
    "vocab_חית_451":  {"gloss": "wild animal / beast"},
    "vocab_בהמה_378": {"gloss": "beast / cattle / animal"},
    "vocab_צאן_242":  {"gloss": "sheep / flock / goats"},
    "vocab_בקר_304":  {"gloss": "ox / cattle / herd"},
    "vocab_שור_380":  {"hebrew": "סוּס", "gloss": "horse", "title": "סוּס — horse"},
    "vocab_חמור_467": {"hebrew": "עֵז", "gloss": "goat", "title": "עֵז — goat"},
    "vocab_צבאו_102": {"hebrew": "צָבָא", "gloss": "army / host / warfare", "title": "צָבָא — army, host"},
    "vocab_מחנה_340": {"hebrew": "מַחֲנֶה", "gloss": "camp / army", "title": "מַחֲנֶה — camp"},
    "vocab_דגל_":     {"gloss": "banner / flag"},
    "vocab_קדש_119":  {"hebrew": "קֹדֶשׁ", "gloss": "holiness / sacredness / sanctuary", "title": "קֹדֶשׁ — holiness, sanctuary"},
    "vocab_קדוש_295": {"hebrew": "קָדוֹשׁ", "gloss": "holy / sacred / set apart", "title": "קָדוֹשׁ — holy, set apart"},
    "vocab_טוב_106":  {"gloss": "good / pleasant / beautiful"},
    "vocab_רע_235":   {"gloss": "bad / evil / wicked"},
    "vocab_רשע_141":  {"gloss": "wicked / guilty / criminal"},
    "vocab_צדיק_171": {"gloss": "righteous / just"},
    "vocab_ישר_448":  {"hebrew": "יָשָׁר", "gloss": "upright / straight / right", "title": "יָשָׁר — upright, straight"},
    "vocab_תמים_321": {"gloss": "blameless / complete / perfect"},
    "vocab_חכם_259":  {"hebrew": "חָכָם", "gloss": "wise", "title": "חָכָם — wise"},
    "vocab_חזק_176":  {"gloss": "strong / mighty / firm"},
    "vocab_גדול_88":  {"gloss": "great / large / mighty"},
    "vocab_קטן_":     {"gloss": "small / young / insignificant"},
    "vocab_עני_435":  {"gloss": "poor / humble / afflicted"},
    "vocab_שרי_112":  {"gloss": "prince / ruler / leader / official"},
    "vocab_נשיא_385": {"gloss": "chief / leader / prince"},
    "vocab_זקן_261":  {"hebrew": "זָקֵן", "gloss": "old / elder", "title": "זָקֵן — old, elder"},
    "vocab_נער_296":  {"hebrew": "נַעַר", "gloss": "young man / servant / boy", "title": "נַעַר — young man, servant"},
    "vocab_אלף_80":   {"gloss": "thousand / clan"},
    "vocab_רבבה_79":  {"gloss": "ten thousand / myriad"},
    "vocab_עזר_499":  {"hebrew": "עָזַר", "gloss": "to help / to aid", "title": "עָזַר — to help, to aid"},
    "vocab_קרא_81":   {"gloss": "to call / to summon / to proclaim"},
    "vocab_ענה_154":  {"gloss": "to answer / to respond"},
    "vocab_חטא_156":  {"gloss": "to sin / to miss the mark"},
    "vocab_מלך_22":   {"gloss": "king / ruler"},
    "vocab_כהן_53":   {"gloss": "priest / minister"},
    "vocab_נביא_149": {"gloss": "prophet / spokesperson"},
    "vocab_שאר_486":  {"hebrew": "שְׁאֵרִית", "gloss": "remnant / rest / remainder", "title": "שְׁאֵרִית — remnant, rest"},
}

# Fix also the source lemma_gloss for these
SOURCE_FIXES = [
    ("5002", "utterance / declaration / oracle"),
    ("5001", "utterance"),
    ("7130", "midst / among"),
    ("5612", "book / scroll"),
    ("1086", "not / without"),
    ("1097", "not / without"),
    ("3515", "heavy / glorious / honorable"),
    ("7227 a", "much / many / great"),
    ("7227", "much / many"),
    ("4592", "little / few"),
    ("2416 a", "alive / living"),
    ("2416", "alive / living / life"),
    ("4194", "death"),
    ("2416 a", "living creature"),
    ("2416 b", "living creature"),
    ("929", "beast / animal"),
    ("6629", "sheep / flock / goat"),
    ("1241", "ox / cattle"),
    ("5483 a", "horse"),
    ("6635 b", "army / host / warfare"),
    ("4264", "camp"),
    ("6944", "holiness / sanctuary"),
    ("6918", "holy / set apart"),
    ("2896 a", "good / pleasant / beautiful"),
    ("7451 b", "bad / evil / wicked"),
    ("7563", "wicked / guilty"),
    ("6662", "righteous / just"),
    ("3477", "upright / straight"),
    ("8549", "blameless / complete / perfect"),
    ("2450", "wise"),
    ("2389", "strong / mighty"),
    ("1419 a", "great / large / mighty"),
    ("6996 a", "small / young"),
    ("6041", "poor / humble / afflicted"),
    ("8269", "prince / ruler / leader"),
    ("5387", "chief / leader / prince"),
    ("2205", "old / elder"),
    ("5288", "young man / servant"),
    ("7239", "ten thousand / myriad"),
    ("5828", "to help / to aid"),
    ("7121", "to call / to summon"),
    ("6030 a", "to answer / to respond"),
    ("2398", "to sin / to miss the mark"),
    ("7611", "remnant / rest"),
]


def fix_remaining_glosses():
    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    
    fixed_nodes = 0
    fixed_lessons = 0
    fixed_practice = 0
    
    # Phase 1: Apply additional corrections
    for node_id, corr in ADDITIONAL_CORRECTIONS.items():
        node = conn.execute("SELECT * FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if not node:
            print(f"  SKIP {node_id}: not found")
            continue
        
        old_title = node['title']
        new_gloss = corr.get('gloss')
        new_hebrew = corr.get('hebrew')
        new_title = corr.get('title')
        
        old_parts = old_title.split(' — ', 1)
        old_hebrew = old_parts[0] if len(old_parts) > 1 else ''
        old_gloss = old_parts[1] if len(old_parts) > 1 else old_title
        
        if not new_hebrew:
            new_hebrew = old_hebrew
        if not new_title:
            new_title = f"{new_hebrew} — {new_gloss}" if new_gloss else old_title
        
        # Update node title
        conn.execute("UPDATE hebrew_nodes SET title=? WHERE id=?", (new_title, node_id))
        
        # Update description if needed
        if new_gloss and old_gloss and old_gloss != new_gloss:
            old_desc = node['description'] or ''
            if old_desc.startswith(old_gloss) or old_desc.startswith(old_gloss.lower()):
                new_desc = new_gloss + old_desc[len(old_gloss):]
                conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (new_desc, node_id))
        
        print(f"  FIX {node_id}: '{old_title}' → '{new_title}'")
        fixed_nodes += 1
        
        # Update lesson content
        lesson_row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if lesson_row and lesson_row[0]:
            content = json.loads(lesson_row[0]) if isinstance(lesson_row[0], str) else lesson_row[0]
            changed = False
            if new_hebrew and content.get('hebrew') and content['hebrew'] != new_hebrew:
                content['hebrew'] = new_hebrew
                changed = True
            if new_gloss and content.get('gloss') and content['gloss'] != new_gloss:
                content['gloss'] = new_gloss
                changed = True
            if content.get('title') and new_title and content['title'] != new_title:
                content['title'] = new_title
                changed = True
            if changed:
                conn.execute("UPDATE hebrew_lessons SET content_json=? WHERE node_id=?", 
                           (json.dumps(content, ensure_ascii=False), node_id))
                fixed_lessons += 1
        
        # Update practice items
        items = conn.execute("SELECT id, question_type, question_text, correct_answer, options_json FROM hebrew_practice_items WHERE node_id=?", (node_id,)).fetchall()
        for item in items:
            qtext = item['question_text']
            cans = item['correct_answer']
            opts = item['options_json']
            
            if old_gloss and new_gloss and old_gloss != new_gloss:
                # Fix correct answer
                if cans == old_gloss:
                    conn.execute("UPDATE hebrew_practice_items SET correct_answer=? WHERE id=?", (new_gloss, item['id']))
                    fixed_practice += 1
                # Fix question text
                if old_gloss in qtext:
                    conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", 
                               (qtext.replace(old_gloss, new_gloss), item['id']))
                    fixed_practice += 1
                # Fix options
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_gloss if o == old_gloss else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?", 
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                                fixed_practice += 1
                    except (json.JSONDecodeError, TypeError):
                        pass
            
            if new_hebrew and old_hebrew and new_hebrew != old_hebrew:
                if old_hebrew in qtext and new_hebrew not in qtext:
                    conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", 
                               (qtext.replace(old_hebrew, new_hebrew), item['id']))
                if cans == old_hebrew:
                    conn.execute("UPDATE hebrew_practice_items SET correct_answer=? WHERE id=?", (new_hebrew, item['id']))
                if opts:
                    try:
                        opts_list = json.loads(opts)
                        if isinstance(opts_list, list):
                            new_opts = [new_hebrew if o == old_hebrew else o for o in opts_list]
                            if new_opts != opts_list:
                                conn.execute("UPDATE hebrew_practice_items SET options_json=? WHERE id=?", 
                                           (json.dumps(new_opts, ensure_ascii=False), item['id']))
                    except (json.JSONDecodeError, TypeError):
                        pass
    
    # Phase 2: Fix remaining parenthetical old-gloss patterns
    # Scan for any practice items with (Saith), (Slept), (Thither), etc. in the question text
    print("\n=== Phase 2: Fix parenthetical old glosses ===")
    archaic_glosses = {
        "Saith": "says / said",
        "Slept": "with",
        "Thither": "there",
        "Woof": "or",
        "Rebellest": "",
        "Chronicles": "book / scroll / chronicle",
        "Tacklings": "not / without",
        "Purtenance": "midst / among / inward part",
        "Sibbechai": "then",
        "Procured": "this (f. sg.)",
        "Pare": "midst / among",
    }
    
    for old_archaic, new_gloss in archaic_glosses.items():
        if not new_gloss:
            continue
        # Look for "(OldGloss)" in question text
        pattern = f"({old_archaic})"
        items = conn.execute("""
            SELECT id, node_id, question_text 
            FROM hebrew_practice_items 
            WHERE question_text LIKE ?
        """, (f"%({old_archaic})%",)).fetchall()
        
        for item in items:
            new_qtext = item['question_text'].replace(pattern, f"({new_gloss})")
            conn.execute("UPDATE hebrew_practice_items SET question_text=? WHERE id=?", 
                       (new_qtext, item['id']))
            print(f"  FIX {item['node_id']}: '{pattern}' → '({new_gloss})'")
            fixed_practice += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n  Additional fixes: {fixed_nodes} nodes, {fixed_lessons} lessons, {fixed_practice}+ practice items")


def fix_source_additional():
    if not SCRIPTURE_DB.exists():
        return
    conn = sqlite3.connect(str(SCRIPTURE_DB))
    updated = 0
    for lemma, gloss in SOURCE_FIXES:
        existing = conn.execute("SELECT english_gloss FROM lemma_gloss WHERE lemma=?", (lemma,)).fetchone()
        if existing and existing[0] != gloss:
            print(f"  PATCH lemma_gloss {lemma}: '{existing[0]}' → '{gloss}'")
            conn.execute("UPDATE lemma_gloss SET english_gloss=? WHERE lemma=?", (gloss, lemma))
            updated += 1
    conn.commit()
    conn.close()
    print(f"  Updated {updated} additional lemma_gloss entries")


if __name__ == '__main__':
    print("=== Fixing additional lemma_gloss entries ===")
    fix_source_additional()
    print("\n=== Fixing remaining vocabulary entries ===")
    fix_remaining_glosses()
    print("\n✓ Done!")
