#!/usr/bin/env python3
"""Fix Hebrew practice item content quality (Math Academy Way review).

Defect classes fixed:
  1. Answer given away in the question text (consonants/vowels):
     - "What is the name of this Hebrew letter: Aleph?"  → show the glyph א
     - "Which Hebrew vowel makes the sound described by Hataf Patah?" → show glyph
     - "Name the Hebrew vowel that sounds like Hataf Patah." → show glyph
     - "How is this letter transliterated: Aleph?" → show glyph
     - "What is the Hebrew letter named 'Aleph'?" → show glyph
     - "Type the Hebrew letter: Aleph" (answer was the Latin name AND given in Q)
  2. Unanswerable typing items whose correct_answer is a Latin name while the
     task asks for Hebrew (the glyph), e.g. "Type the Hebrew letter: Aleph".
  3. Final-form typing items with broken answer "final" (should be the glyph).
  4. Contrast questions whose parenthetical reveals the answer, and whose
     stored answer is factually wrong for different-letter pairs.
  5. True/false questions → converted to 4-option multiple choice.
  6. Junk root "Find verse containing 'X'" items with placeholder options
     (["word","verse"]) → rewritten as gloss→word derived-word questions.

Usage:
    python3 scripts/fix_hebrew_practice_items.py --dry-run
    python3 scripts/fix_hebrew_practice_items.py --apply
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"

HEB_RE = re.compile(r"[\u0590-\u05FF]")

# (node_a, node_b, correct_answer) — factual answers for each contrast pair.
# Same-letter-different-dot pairs (shin/sin, sheva na/nah) and vowel-length
# pairs differ in sound/dot; all others are distinct letters → different shape.
CONTRAST_ANSWERS = {
    ("shin", "sin"): "Different sound or dot position",
    ("vowel_sheva_na", "vowel_sheva_nah"): "Different sound or dot position",
    ("vowel_patah", "vowel_qamats"): "Different sound or dot position",
    ("vowel_segol", "vowel_tsere"): "Different sound or dot position",
    ("vowel_hiriq", "vowel_hiriq_yod"): "Different sound or dot position",
    ("vowel_holam", "vowel_holam_vav"): "Different sound or dot position",
    ("vowel_shuruq", "vowel_qubuts"): "Different sound or dot position",
}
CONTRAST_OPTIONS = ["It's the same letter", "Different sound or dot position",
                    "Different shape", "Different category"]

# True/false → 4-option MC conversions (question_text -> (new_q, options, answer))
TRUE_FALSE_CONVERSIONS = {
    "Begadkefat affects all 22 Hebrew letters.": (
        "Which letters does begadkefat affect?",
        ["All 22 letters", "Six letters: בגדכפת", "Only the gutturals", "None of them"],
        "Six letters: בגדכפת",
    ),
    "After a vowel, a begadkefat letter loses its dagesh and becomes soft.": (
        "What happens to a begadkefat letter after a vowel?",
        ["It becomes soft (loses its dagesh)", "It stays hard", "It doubles", "It becomes silent"],
        "It becomes soft (loses its dagesh)",
    ),
    "Every dot inside a Hebrew letter has the same function.": (
        "How many distinct functions can the dot inside a Hebrew letter serve?",
        ["One", "Two", "Three", "Four"],
        "Three",
    ),
    "Furtive patah changes the stored right-to-left character order.": (
        "Where is furtive patah pronounced relative to the final guttural?",
        ["Before the guttural", "After the guttural", "As a separate syllable", "It is silent"],
        "Before the guttural",
    ),
    "Maqqef can be discarded as ordinary punctuation without affecting reading data.": (
        "What does the maqqef (־) do to the words it joins?",
        ["Joins them into one accentual unit", "Separates two verses",
         "Marks a question", "Ends a sentence"],
        "Joins them into one accentual unit",
    ),
    "Every Jewish reading tradition chants the accents with the same melody.": (
        "Do all Jewish reading traditions chant the accents with the same melody?",
        ["No — melodies vary by tradition", "Yes — identical melody",
         "Only Sephardic traditions chant", "Accents are never chanted"],
        "No — melodies vary by tradition",
    ),
    "Hiding vowel points should alter the stored consonantal sequence.": (
        "If vowel points are hidden in the display, what happens to the stored consonantal text?",
        ["It is unchanged — points are a separate layer", "It is rewritten without consonants",
         "Only the first word changes", "It becomes Aramaic"],
        "It is unchanged — points are a separate layer",
    ),
    "Every poetic parallel repeats exactly the same proposition.": (
        "In biblical poetry, parallel lines typically:",
        ["Restate, sharpen, or advance the first", "Repeat it word-for-word",
         "Always contradict it", "Are always longer"],
        "Restate, sharpen, or advance the first",
    ),
    "Every Old Testament token is Biblical Hebrew.": (
        "Which parts of the Old Testament are written in Aramaic?",
        ["Sections of Daniel and Ezra", "None — it is all Hebrew",
         "The entire Pentateuch", "Only the Psalms"],
        "Sections of Daniel and Ezra",
    ),
}

FINAL_FORMS = {  # node_id -> (question, glyph)
    "kaf_final": ("Type the final form of Kaf", "ך"),
    "mem_final": ("Type the final form of Mem", "ם"),
    "nun_final": ("Type the final form of Nun", "ן"),
    "pe_final": ("Type the final form of Pe", "ף"),
    "tsade_final": ("Type the final form of Tsade", "ץ"),
}


def get_letter_name(title):
    """Extract letter name from title like 'Aleph (א)' or 'Bet (בּ)'."""
    return title.split("(")[0].strip()


def get_hebrew_char(title):
    """Extract Hebrew character from title like 'Aleph (א)' or 'Kaf (final) (ך)'.

    Prefers the LAST parenthetical containing Hebrew characters, because
    final-form titles carry a Latin descriptor first: 'Kaf (final) (ך)' → 'ך'.
    """
    matches = re.findall(r"\(([^)]+)\)", title)
    for m in reversed(matches):
        if HEB_RE.search(m):
            return m
    return matches[0] if matches else ""


def _answer_correct_for_pair(node_a, node_b):
    """Correct answer for a contrast pair regardless of direction."""
    return CONTRAST_ANSWERS.get((node_a, node_b)) or CONTRAST_ANSWERS.get((node_b, node_a)) \
        or "Different shape"


def build_fix(item, node, glyph_of, conn):
    """Determine the fix for a practice item.

    Returns (should_fix, new_question_text, new_answer, new_options_json, reason).
    """
    qtype = item["question_type"]
    qtext = item["question_text"]
    answer = item["correct_answer"]
    cat = node["category"]
    title = node["title"]
    nid = item["node_id"]

    name = get_letter_name(title)
    heb_char = get_hebrew_char(title)
    answer_lower = (answer or "").strip().lower()
    name_lower = name.lower()

    # ── Class 5: true/false → 4-option MC ──
    if qtype == "true_false":
        conv = TRUE_FALSE_CONVERSIONS.get(qtext.strip())
        if conv:
            new_q, opts, ans = conv
            # The apply loop converts question_type true_false → multiple_choice.
            return (True, new_q, ans, json.dumps(opts, ensure_ascii=False),
                    "true_false → 4-option multiple choice")
        # Generic "Is 'X' a Y?" TF not in the map — drop it (validator already
        # flags these as tautological).
        return (True, qtext, answer, "[]", "unmapped true_false → removed by caller [REMOVE]")

    # ── Class 6: junk root "Find verse containing 'X'" ──
    if cat == "root" and qtype == "multiple_choice" and "Find verse containing" in qtext:
        row = conn.execute(
            "SELECT content_json FROM hebrew_lessons WHERE node_id=?", (nid,)).fetchone()
        derived = []
        if row:
            try:
                derived = json.loads(row[0]).get("derived_words", [])
            except (json.JSONDecodeError, TypeError):
                derived = []
        if not derived:
            return (True, qtext, answer, "[]", "root junk item with no derived words → removed [REMOVE]")
        # gloss of the target word from the question
        m = re.search(r"'([^']+)'", qtext)
        target = m.group(1) if m else answer
        gloss = next((d["gloss"] for d in derived if d["word"] == target), None)
        if not gloss:
            return (True, qtext, answer, "[]", "root junk item, target gloss missing → removed [REMOVE]")
        # Options: unique derived words (pad from other roots if needed)
        opts = []
        for d in derived:
            w = d["word"]
            if w not in opts:
                opts.append(w)
        if len(opts) < 4:
            for other in conn.execute(
                    "SELECT content_json FROM hebrew_lessons WHERE node_id LIKE 'root_%' AND node_id != ?",
                    (nid,)):
                try:
                    for d in json.loads(other[0]).get("derived_words", []):
                        w = d["word"]
                        if w not in opts:
                            opts.append(w)
                        if len(opts) >= 4:
                            break
                except (json.JSONDecodeError, TypeError):
                    continue
                if len(opts) >= 4:
                    break
        opts = opts[:4]
        new_q = f"Which word from root {nid.split('_')[1] if '_' in nid else nid} means '{gloss}'?"
        return (True, new_q, target, json.dumps(opts, ensure_ascii=False),
                "root 'find verse' junk → gloss→word question")

    # ── Class 4: contrast with answer-revealing parenthetical ──
    if qtype == "contrast":
        m = re.match(r"^Distinguish: How does this letter differ from (.+?)\?", qtext)
        if m:
            other_nid = m.group(1).strip()
            other_title = glyph_of.get(other_nid, "")
            other_name = get_letter_name(other_title)
            other_glyph = get_hebrew_char(other_title)
            ans = _answer_correct_for_pair(nid, other_nid)
            if cat == "vowel":
                # Vowel glyphs are combining marks; pair name + glyph for legibility.
                new_q = (f"Distinguish: How does this vowel ({name}, {heb_char}) "
                         f"differ from {other_name} ({other_glyph})?")
            else:
                new_q = f"Distinguish: How does this letter ({heb_char}) differ from {other_glyph}?"
            return (True, new_q, ans, json.dumps(CONTRAST_OPTIONS, ensure_ascii=False),
                    f"removed answer-revealing parenthetical (correct answer: {ans})")
        return (False, qtext, answer, item["options_json"], "")

    # ── Class 3: final-form typing with broken 'final' answer ──
    if qtype == "typing" and nid in FINAL_FORMS and answer.strip().lower() == "final":
        new_q, glyph = FINAL_FORMS[nid]
        return (True, new_q, glyph, item["options_json"],
                "final-form typing answer fixed to glyph")

    # ── Class 3b: any final-form item whose stimulus is the literal word
    #             "final" (e.g. "What is the name of this Hebrew letter: final?")
    #             → show the actual final-form glyph, preserving question type. ──
    if nid in FINAL_FORMS and re.search(r":\s*final\??\s*$|'final'\??\s*$", qtext, re.I):
        glyph = FINAL_FORMS[nid][1]
        if qtype == "typing":
            new_q = f"Type the name of this Hebrew letter: {glyph}"
        elif qtype == "transliteration":
            new_q = f"How is this letter transliterated: {glyph}?"
        elif qtype == "recall":
            new_q = f"What Hebrew letter is this: {glyph}?"
        elif "makes this sound" in qtext:
            new_q = f"Which Hebrew letter has this final form: {glyph}?"
        else:  # multiple_choice
            new_q = f"What is the name of this Hebrew letter: {glyph}?"
        return (True, new_q, name, item["options_json"],
                "final-form stimulus was 'final' → show glyph")

    # Consonant/vowel letter-name patterns below need the Hebrew glyph.
    if cat not in ("consonant", "vowel") or not heb_char:
        return (False, qtext, answer, item["options_json"], "")

    # ── Class 1: MC "What is the name of this Hebrew letter: Aleph?" ──
    m = re.match(r"^What is the name of this Hebrew (?:letter|vowel):\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"What is the name of this Hebrew letter: {heb_char}?"
        return (True, new_q, name, item["options_json"],
                "show Hebrew char instead of name")

    # ── Class 1: MC "Which letter/vowel makes the sound described by X?" ──
    m = re.match(r"^Which (?:Hebrew )?(?:letter|vowel) makes the sound described by\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        desc = node.get("description", "") or ""
        # Use the node's sound description as the stimulus so the question is
        # distinct from the glyph→name MC and does not name the answer.
        # Guard: if the description itself contains the answer name (e.g.
        # "A sound, long (qamats gadol)" → Qamats), fall back to the glyph.
        noun = "vowel" if cat == "vowel" else "letter"
        if answer_lower in desc.lower() or name_lower in desc.lower():
            new_q = f"Which Hebrew {noun} makes this sound: {heb_char}?"
        else:
            new_q = f"Which Hebrew {noun} makes this sound: {desc}?"
        return (True, new_q, name, item["options_json"],
                "use sound description instead of name (distinct retrieval)")

    # ── Class 1: MC "Which letter makes the sound described in the lesson for X?" ──
    m = re.match(r"^Which letter makes the sound described in(?: the lesson)? for\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        desc = node.get("description", "") or ""
        noun = "vowel" if cat == "vowel" else "letter"
        if answer_lower in desc.lower() or name_lower in desc.lower():
            new_q = f"Which Hebrew {noun} makes this sound: {heb_char}?"
        else:
            new_q = f"Which Hebrew {noun} makes this sound: {desc}?"
        return (True, new_q, name, item["options_json"],
                "use sound description instead of name (distinct retrieval)")

    # ── Class 1: MC "Which Hebrew letter makes this sound: <description>" where
    #             the description embeds the answer name ──
    m = re.match(r"^Which Hebrew (?:letter|vowel) makes this sound:\s*(.+?)\??\s*$", qtext)
    if m:
        desc = m.group(1).strip()
        noun = "vowel" if cat == "vowel" else "letter"
        if answer_lower in desc.lower() or name_lower in desc.lower():
            new_q = f"Which Hebrew {noun} makes this sound: {heb_char}?"
            return (True, new_q, name, item["options_json"],
                    "description embedded answer name → use glyph")

    # ── Class 1: MC final-form "Which Hebrew letter makes this sound: Final form of Kaf?" ──
    if qtype == "multiple_choice" and nid in FINAL_FORMS and "final form of" in qtext.lower():
        glyph = FINAL_FORMS[nid][1]
        new_q = f"Which Hebrew letter has this final form: {glyph}?"
        return (True, new_q, name, item["options_json"],
                "final-form sound question → glyph-based")

    # ── Class 1: "Which Hebrew vowel is this" / "Which letter is this" ──
    m = re.match(r"^Which (?:Hebrew )?(?:letter|vowel) is this:\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"Which Hebrew letter is this: {heb_char}?"
        return (True, new_q, name, item["options_json"],
                "show Hebrew char instead of name")

    # ── Class 2: Typing "Type the Hebrew letter: Aleph" (answer is Latin name) ──
    m = re.match(r"^Type (?:the |this )?(?:Hebrew )?letter:?\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        # Old: Q="Type the Hebrew letter: Aleph" A="Aleph" → impossible to answer
        # correctly (student types א, graded against 'aleph').
        # Fix: show char, ask to type name.
        new_q = f"Type the name of this Hebrew letter: {heb_char}"
        return (True, new_q, name, item["options_json"],
                "show char, ask to type name (old answer was unanswerable Latin)")

    # ── Class 1: Transliteration "How is this letter transliterated: Aleph?" ──
    m = re.match(r"^How is this letter transliterated:\s*(.+?)\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"How is this letter transliterated: {heb_char}?"
        return (True, new_q, name, item["options_json"],
                "show char instead of name for transliteration")

    # ── Class 1: Recall "What is the Hebrew letter named 'Aleph'?" ──
    m = re.match(r"^What is the Hebrew (?:letter|vowel) named\s*'([^']+)'\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"What Hebrew letter is this: {heb_char}?"
        return (True, new_q, name, item["options_json"],
                "show char instead of name in recall")

    # ── Class 1: Recall "Name the Hebrew vowel that sounds like X." ──
    m = re.match(r"^Name the Hebrew vowel that sounds like\s*(.+?)\.?\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"Name this Hebrew vowel: {heb_char}"
        return (True, new_q, name, item["options_json"],
                "show char instead of name in vowel recall")

    # ── Class 1: "What is X in Hebrew?" ──
    m = re.match(r"^What is\s+(.+?)\s+in Hebrew\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f"What is this Hebrew letter: {heb_char}?"
        return (True, new_q, name, item["options_json"],
                "show char instead of name")

    return (False, qtext, answer, item["options_json"], "")


def main():
    parser = argparse.ArgumentParser(description="Fix Hebrew practice item content quality")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply fixes to database")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Usage: pass --dry-run to preview or --apply to apply fixes")
        sys.exit(1)

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row

    # node_id -> title map for contrast glyph resolution
    glyph_of = {r["id"]: r["title"] for r in conn.execute("SELECT id, title FROM hebrew_nodes")}

    items = conn.execute("""
        SELECT pi.*, n.category, n.title as node_title, n.description as node_description
        FROM hebrew_practice_items pi
        JOIN hebrew_nodes n ON n.id = pi.node_id
        ORDER BY n.category, pi.node_id, pi.id
    """).fetchall()

    print(f"Checking {len(items)} practice items...\n")

    fixes = []
    for item in items:
        node = {"category": item["category"], "title": item["node_title"], "description": item["node_description"]}
        should_fix, new_q, new_a, new_opts, reason = build_fix(dict(item), node, glyph_of, conn)
        if should_fix:
            fixes.append((dict(item), new_q, new_a, new_opts, reason))

    print(f"  TOTAL: {len(fixes)} items need fixing\n")

    for item, nq, na, no, reason in fixes:
        print(f"  #{item['id']} [{item['node_id']}|{item['question_type']:15s}] {reason}")
        print(f"     OLD: {item['question_text'][:70]}")
        print(f"     NEW: {nq[:70]}")

    if not args.apply:
        print(f"\n  → Run with --apply to apply {len(fixes)} fixes.")
        conn.close()
        return

    print(f"\n  Applying fixes...")
    cur = conn.cursor()
    applied = 0
    removed = 0
    for item, new_q, new_a, new_opts, reason in fixes:
        # Removal paths (unmapped true/false, root junk with no usable derived
        # words) return options "[]" AND a reason marked "[REMOVE]". Production
        # items (typing/recall/transliteration) also carry empty options_json
        # but must be UPDATED, never deleted — so the marker is the only signal.
        if reason.endswith("[REMOVE]"):
            cur.execute("DELETE FROM hebrew_practice_items WHERE id=?", (item["id"],))
            removed += 1
        else:
            # True/false items are converted to 4-option multiple choice.
            new_type = "multiple_choice" if item["question_type"] == "true_false" else item["question_type"]
            cur.execute(
                "UPDATE hebrew_practice_items SET question_text=?, correct_answer=?, options_json=?, question_type=? WHERE id=?",
                (new_q, new_a, new_opts, new_type, item["id"]),
            )
        applied += 1

    conn.commit()
    print(f"  ✅ Applied {applied} fixes ({removed} removed) to {MEM_DB.name}")

    # ── Verify: no true_false remain ──
    tf = conn.execute("SELECT COUNT(*) FROM hebrew_practice_items WHERE question_type='true_false'").fetchone()[0]
    print(f"  true_false remaining: {tf}")

    # ── Verify: no answer-in-question (normalized word-boundary) for assessed types ──
    def norm(s):
        s = re.sub(r"[\u05be\u05f3\u2018\u2019\u201c\u201d\"'\.,;:!?()\[\]{}]", " ", s.lower())
        return re.sub(r"\s+", " ", s).strip()

    bad = 0
    for r in conn.execute("""
        SELECT p.node_id, p.question_type, p.question_text, p.correct_answer
        FROM hebrew_practice_items p JOIN hebrew_nodes n ON n.id=p.node_id
        WHERE p.question_type IN ('multiple_choice','typing','transliteration','recall','contrast')
          AND n.category IN ('consonant','vowel')
    """):
        q, a = norm(r["question_text"]), norm(r["correct_answer"] or "")
        if len(a) > 2 and re.search(r"(^|\s)" + re.escape(a) + r"(\s|$)", q):
            bad += 1
    print(f"  consonant/vowel answer-in-question remaining: {bad}")

    conn.close()


if __name__ == "__main__":
    main()
