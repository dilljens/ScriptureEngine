#!/usr/bin/env python3
"""
Fourth pass: fix stale explanations in practice items + improve letter/vowel lessons.

1. Fix stale explanation fields (old glosses like "Too", "Slept", "Saith")
2. Add meaningful key points to vowel/syllable lessons (replacing "Key concept in X")
3. Add Hebrew characters to letter/vowel content so audio playback works
4. Add contrast practice for confusable letter/vowel pairs
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"

# ── Old gloss → new gloss mapping for explanation fields ──
GLOSS_FIXES = {
    "Too": "from",
    "Slept": "with", 
    "Five": "this (m. sg.)",
    "Saith": "says / said",
    "Thither": "there",
    "Woof": "or",
    "Rebellest": "",
    "Chronicles": "",
    "Tacklings": "",
    "Purtenance": "",
    "Stood": "to stand",
    "Procured": "this (f. sg.)",
    "Sibbechai": "",
    "Horam": "",
    "Nisroch": "",
    "Zidkijah": "",
    "Enflaming": "",
    "Sware": "",
    "Meres": "",
    "Leadest": "",
    "Zeeb": "",
    "Tumbled": "",
    "Dimon": "",
    "Shekels": "",
    "Staves": "",
}

# ── Vowel key points improvement ──
# Replaces the generic "Key concept in {category}" / "Review the explanation above"
VOWEL_KEY_POINTS = {
    "vowel_patah": [
        "Short 'a' sound — like 'a' in 'father'",
        "Horizontal line under the consonant",
        "Most common vowel in Biblical Hebrew",
        "Can lengthen to Qamats in open syllables",
    ],
    "vowel_qamats": [
        "Long 'a' sound — like 'a' in 'father' but held longer",
        "Small 'T' shape under the consonant",
        "Qamats Gadol = 'a'; Qamats Qatan = 'o'",
        "Often appears in the first syllable of nouns",
    ],
    "vowel_qamats_qatan": [
        "Looks identical to Qamats but sounds like 'o'",
        "Occurs in closed, unaccented syllables",
        "Example: חָכְמָה (ḥoḵmāh = wisdom)",
        "Rule: closed unstressed syllable with Qamats → Qamats Qatan",
    ],
    "vowel_hiriq": [
        "Short 'i' sound — like 'i' in 'machine'",
        "Single dot under the consonant",
        "With Yod (ִי) becomes long Hiriq Yod",
        "Common in prefixed forms (מִ = from)",
    ],
    "vowel_hiriq_yod": [
        "Long 'i' sound with Yod as vowel letter",
        "Yod is a mater lectionis (silent vowel carrier)",
        "Common at end of plural adjectives",
        "Always long — never reduced",
    ],
    "vowel_tsere": [
        "Long 'e' sound — like 'e' in 'they'",
        "Two dots side by side under the consonant",
        "Can appear with or without Yod as mater",
        "Often in construct plural forms: דִּבְרֵי (divrei = words of)",
    ],
    "vowel_tsere_yod": [
        "Long 'e' with Yod as mater lectionis",
        "Common in plural construct suffixes",
        "End of words: בְּנֵי (bnei = sons of)",
        "Always long vowel",
    ],
    "vowel_segol": [
        "Short 'e' sound — like 'e' in 'bed'",
        "Three dots in a triangle under the consonant",
        "Appears in segolate nouns (e.g. מֶלֶךְ = king)",
        "Often alternates with Tsere in different forms",
    ],
    "vowel_segol_yod": [
        "'E' sound with Yod as mater lectionis",
        "Found in noun patterns and proper names",
        "Less common than Tsere Yod",
    ],
    "vowel_holam": [
        "Short/medium 'o' sound",
        "Single dot above the consonant (left side)",
        "Full form with Vav (וֹ = Holam Male)",
        "Example: טוֹב (tov = good) has Holam Male",
    ],
    "vowel_holam_vav": [
        "Long 'o' with Vav as mater lectionis",
        "Very common — 'shalom' (שָׁלוֹם) has Holam Male",
        "Dot is placed above the Vav",
        "Always long — occurs in open syllables",
    ],
    "vowel_shuruq": [
        "Long 'u' sound — like 'u' in 'rude'",
        "Vav with a dagesh dot inside: וּ",
        "Common in grammatical endings (plural suffixes)",
        "Distinct from Qubuts (short 'u') which has no Vav",
    ],
    "vowel_qubuts": [
        "Short 'u' sound",
        "Three dots diagonally under the consonant (like \u22ee)",
        "Less common than Shuruq in Biblical Hebrew",
        "Often in closed, unaccented syllables",
    ],
    "vowel_sheva": [
        "Two dots vertically under the consonant",
        "Two types: vocal (sheva na) and silent (sheva nah)",
        "Vocal sheva = brief 'e' (like 'a' in 'about')",
        "Silent sheva = closes syllable, not pronounced",
    ],
    "vowel_sheva_na": [
        "Vocal sheva — pronounced as brief 'e'",
        "Occurs at beginning of a syllable",
        "Also under a letter with dagesh forte",
        "Also after a long vowel",
    ],
    "vowel_sheva_nah": [
        "Silent sheva — closes a syllable without sound",
        "Occurs in middle or end of word",
        "Marks the end of a closed syllable",
        "Not pronounced — like a syllable boundary marker",
    ],
    "vowel_hataf_patah": [
        "Reduced 'a' vowel — Patah + Sheva combined",
        "Used ONLY on guttural letters (אהחע)",
        "Gutturals cannot take plain Sheva",
        "Other hatafim: Hataf Segol (e), Hataf Qamats (o)",
    ],
    "vowel_hataf_qamats": [
        "Reduced 'o' vowel — on guttural letters",
        "Combines Qamats + Sheva shape",
        "Occurs on gutturals needing reduced 'o'",
    ],
    "vowel_hataf_segol": [
        "Reduced 'e' vowel — on guttural letters",
        "Combines Segol + Sheva shape",
        "Least common of the three hatafim",
    ],
}

# ── Syllable key points improvement ──
SYLLABLE_KEY_POINTS = {
    "syllable_basics": [
        "Every syllable built around a vowel",
        "Basic patterns: CV (open) and CVC (closed)",
        "Every syllable must begin with a consonant",
        "Silent sheva = syllable end; vocal sheva = syllable start",
    ],
    "syllable_open": [
        "Open syllable ends with a vowel (CV)",
        "Always has a long vowel (or vocal sheva)",
        "Example: בָּ (bā) — Bet + Qamats",
        "Cannot end with a consonant",
    ],
    "syllable_closed": [
        "Closed syllable ends with a consonant (CVC)",
        "Usually has a short vowel",
        "Final consonant 'closes' the syllable",
        "Example: בַּת (bat) — Bet + Patah + Tav",
    ],
    "syllable_stress": [
        "Most Hebrew words stressed on LAST syllable (ultima)",
        "Stress marked by cantillation accent in the text",
        "Penultima stress (second-to-last) is less common",
        "Stress can change meaning: בָּ֫נוּ (we came) vs. בָּנ֫וּ (they built)",
    ],
    "syllable_division": [
        "Each vowel = one syllable",
        "Silent sheva = end of a syllable",
        "Vocal sheva = start of a new syllable",
        "Example: בְּרֵאשִׁית = בְּ·רֵ·א·שִׁית (4 syllables)",
    ],
}

# ── Letter content improvements (add hebrew glyph for audio) ──
LETTER_GLYPHS = {
    "aleph": "א", "bet": "ב", "gimel": "ג", "dalet": "ד", "he": "ה",
    "vav": "ו", "zayin": "ז", "chet": "ח", "tet": "ט", "yod": "י",
    "kaf": "כ", "kaf_final": "ך", "lamed": "ל", "mem": "מ", "mem_final": "ם",
    "nun": "נ", "nun_final": "ן", "samekh": "ס", "ayin": "ע", "pe": "פ",
    "pe_final": "ף", "tsade": "צ", "tsade_final": "ץ", "qof": "ק",
    "resh": "ר", "shin": "שׁ", "sin": "שׂ", "tav": "ת",
}

VOWEL_GLYPHS = {
    "vowel_patah": "ַ", "vowel_qamats": "ָ", "vowel_qamats_qatan": "ָ",
    "vowel_hiriq": "ִ", "vowel_hiriq_yod": "ִי",
    "vowel_tsere": "ֵ", "vowel_tsere_yod": "ֵי",
    "vowel_segol": "ֶ", "vowel_segol_yod": "ֶי",
    "vowel_holam": "ֹ", "vowel_holam_vav": "וֹ",
    "vowel_shuruq": "וּ", "vowel_qubuts": "ֻ",
    "vowel_sheva": "ְ", "vowel_sheva_na": "ְ", "vowel_sheva_nah": "ְ",
    "vowel_hataf_patah": "ֲ", "vowel_hataf_qamats": "ֳ", "vowel_hataf_segol": "ֱ",
}


def fix_stale_explanations():
    """Fix stale explanation fields in practice items."""
    conn = sqlite3.connect(str(MEM_DB))
    
    total = 0
    for old_str, new_str in GLOSS_FIXES.items():
        if not new_str:
            continue
        # Find all practice items with stale explanation referencing old gloss
        items = conn.execute(
            "SELECT id, node_id, explanation FROM hebrew_practice_items WHERE explanation LIKE ?",
            (f"%{old_str}%",)
        ).fetchall()
        
        for item in items:
            new_expl = item[2].replace(old_str, new_str)
            conn.execute("UPDATE hebrew_practice_items SET explanation=? WHERE id=?", (new_expl, item[0]))
            total += 1
    
    # Also fix: "The Hebrew word is 'X' (OldGloss)" pattern
    items2 = conn.execute(
        "SELECT id, node_id, explanation FROM hebrew_practice_items WHERE explanation LIKE '%(Too)%' OR explanation LIKE '%(Slept)%' OR explanation LIKE '%(Saith)%' OR explanation LIKE '%(Five)%' OR explanation LIKE '%(Thither)%'"
    ).fetchall()
    for item in items2:
        new_expl = item[2]
        new_expl = new_expl.replace("(Too)", "(from)")
        new_expl = new_expl.replace("(Slept)", "(with)")
        new_expl = new_expl.replace("(Saith)", "(says / said)")
        new_expl = new_expl.replace("(Five)", "(this)")
        new_expl = new_expl.replace("(Thither)", "(there)")
        conn.execute("UPDATE hebrew_practice_items SET explanation=? WHERE id=?", (new_expl, item[0]))
        total += 1
    
    conn.commit()
    conn.close()
    print(f"  Fixed {total} stale explanation fields")
    return total


def update_lesson_key_points():
    """Replace generic key points with meaningful ones for vowels/syllables."""
    conn = sqlite3.connect(str(MEM_DB))
    
    total = 0
    for node_id, key_points in {**VOWEL_KEY_POINTS, **SYLLABLE_KEY_POINTS}.items():
        # Update content_json in hebrew_lessons
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
        total += 1
        
        # Also update hebrew_nodes description if it's generic
        node = conn.execute("SELECT description FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
        if node and node[0] in ("Key concept in vowel", "Review the explanation above", 
                                 "Key concept in syllable", ""):
            # Use first key point as description
            conn.execute("UPDATE hebrew_nodes SET description=? WHERE id=?", (key_points[0], node_id))
    
    conn.commit()
    conn.close()
    print(f"  Updated {total} lesson key point sets")
    return total


def add_hebrew_glyphs_to_content():
    """Add hebrew glyph to letter/vowel content JSON for audio playback."""
    conn = sqlite3.connect(str(MEM_DB))
    
    total = 0
    for node_id, glyph in {**LETTER_GLYPHS, **VOWEL_GLYPHS}.items():
        row = conn.execute("SELECT content_json FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
        if not row:
            continue
        
        try:
            content = json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            content = {}
        
        if not content.get("hebrew"):
            content["hebrew"] = glyph
            content["glyph"] = glyph
            conn.execute(
                "UPDATE hebrew_lessons SET content_json=? WHERE node_id=?",
                (json.dumps(content, ensure_ascii=False), node_id)
            )
            total += 1
    
    conn.commit()
    conn.close()
    print(f"  Added Hebrew glyphs to {total} letter/vowel lessons")
    return total


def add_contrast_practice():
    """Add contrast practice items for confusable letter pairs."""
    conn = sqlite3.connect(str(MEM_DB))
    
    # Confusable letter pairs that should have contrast practice
    CONTRAST_PAIRS = [
        ("shin", "sin", "SH (right dot) vs S (left dot) — same letter, different dot position"),
        ("bet", "vav", "B (Bet with dagesh) vs V (Vav) — similar sound"),
        ("samekh", "sin", "S (Samekh) vs S (Sin) — same sound, different letter"),
        ("tet", "tav", "T (Tet, emphatic) vs T (Tav) — similar sound"),
        ("he", "chet", "H (He) vs CH (Chet) — similar guttural"),
        ("aleph", "ayin", "Aleph (silent) vs Ayin (guttural) — both vowel carriers"),
        ("dalet", "resh", "D (Dalet) vs R (Resh) — similar shapes"),
        ("kaf", "qof", "K/KH (Kaf) vs Q (Qof) — similar K sound"),
        ("zayin", "tsade", "Z (Zayin) vs TS (Tsade) — similar shapes"),
        ("gimel", "nun", "G (Gimel) vs N (Nun) — similar shapes"),
        ("vowel_patah", "vowel_qamats", "Short A (Patah) vs Long A (Qamats) — same sound, different length"),
        ("vowel_segol", "vowel_tsere", "Short E (Segol) vs Long E (Tsere) — same sound, different length"),
        ("vowel_hiriq", "vowel_hiriq_yod", "Short I vs Long I (with Yod mater)"),
        ("vowel_holam", "vowel_holam_vav", "Short O vs Long O (with Vav mater)"),
        ("vowel_shuruq", "vowel_qubuts", "Long U (Shuruq) vs Short U (Qubuts)"),
        ("vowel_sheva_na", "vowel_sheva_nah", "Vocal Sheva (pronounced) vs Silent Sheva (not pronounced)"),
    ]
    
    added = 0
    for node_a, node_b, description in CONTRAST_PAIRS:
        # Add a contrast practice item to each node in the pair
        for nid, other_nid, desc in [(node_a, node_b, description), (node_b, node_a, description)]:
            # Check if a contrast item already exists for this pair
            existing = conn.execute(
                "SELECT id FROM hebrew_practice_items WHERE node_id=? AND question_type='contrast' AND question_text LIKE ?",
                (nid, f"%{other_nid}%")
            ).fetchone()
            if existing:
                continue
            
            conn.execute(
                "INSERT INTO hebrew_practice_items (node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation) VALUES (?, 'contrast', ?, ?, ?, 0.6, ?)",
                (nid, f"Distinguish: How does this letter differ from {other_nid}? ({desc})",
                 json.dumps(["It's the same letter", "Different sound or dot position", "Different shape", "Different category"], ensure_ascii=False),
                 "Different sound or dot position",
                 f"{desc}")
            )
            added += 1
    
    conn.commit()
    conn.close()
    print(f"  Added {added} contrast practice items")
    return added


def patch_source_seed_script():
    """Patch the source seed script so future rebuilds get good vowel key points."""
    seed_path = BASE / "scripts" / "seed_hebrew_content.py"
    if not seed_path.exists():
        return 0
    
    content = seed_path.read_text(encoding="utf-8")
    
    # The generic key points fallback is at line ~758
    # We need to add vowel-specific entries to _key_points dict
    # Check if they exist already
    if "vowel_patah" in content and '"Key concept in vowel"' not in content:
        print("  Vowel key points already in seed script — skipping")
        return 0
    
    print("  Note: patch_source_seed_script skipped — manual update recommended")
    return 0


def main():
    print("=== Phase 1: Fix stale explanations ===")
    fix_stale_explanations()
    
    print("\n=== Phase 2: Update vowel/syllable key points ===")
    update_lesson_key_points()
    
    print("\n=== Phase 3: Add Hebrew glyphs for audio ===")
    add_hebrew_glyphs_to_content()
    
    print("\n=== Phase 4: Add contrast practice for confusable letters/vowels ===")
    add_contrast_practice()
    
    print("\n✓ Done!")


if __name__ == '__main__':
    main()
