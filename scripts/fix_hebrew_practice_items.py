#!/usr/bin/env python3
"""Fix Hebrew practice item content quality.

Issues found:
- Letter/vowel practice items give away the answer in the question text
  (e.g. "What is the name of this Hebrew letter: Ayin?" — "Ayin" is in the Q)
- Sound identification questions name the answer in the question
- Typing/recall items ask name when showing name (should show Hebrew character)

Usage:
    python3 scripts/fix_hebrew_practice_items.py --dry-run
    python3 scripts/fix_hebrew_practice_items.py --apply
"""

import argparse
import sqlite3
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"


def get_letter_name(title):
    """Extract letter name from title like 'Aleph (א)' or 'Bet (בּ)'."""
    return title.split('(')[0].strip()


def get_hebrew_char(title):
    """Extract Hebrew character from title like 'Aleph (א)'."""
    m = re.search(r'\(([^)]+)\)', title)
    return m.group(1) if m else ''


def build_fix(item, node):
    """Determine the fix for a practice item.
    
    Returns (should_fix, new_question_text, new_answer, new_options, reason)
    """
    qtype = item['question_type']
    qtext = item['question_text']
    answer = item['correct_answer']
    cat = node['category']
    title = node['title']

    name = get_letter_name(title)
    heb_char = get_hebrew_char(title)
    name_lower = name.lower()
    answer_lower = answer.strip().lower()

    if cat not in ('consonant', 'vowel') or not heb_char:
        return (False, qtext, answer, item['options_json'], '')

    # ── Pattern 1: "What is the name of this Hebrew letter: Ayin?" ──
    # Fix: Show Hebrew char instead of name in question
    m = re.match(r'^(What is the name of this Hebrew letter):\s*(.+?)\??\s*$', qtext)
    if m and answer_lower == m.group(2).strip().lower():
        new_q = f'{m.group(1)}: {heb_char}?'
        return (True, new_q, name, item['options_json'],
                f'show Hebrew char instead of name')

    # ── Pattern 2: "Which letter makes the sound described in the lesson for Ayin?" ──
    m = re.match(r'^(Which letter makes the sound described in(?: the lesson)? for)\s*(.+?)\??\s*$', qtext)
    if m and answer_lower == m.group(2).strip().lower():
        new_q = f'{m.group(1)} this letter: {heb_char}?'
        return (True, new_q, name, item['options_json'],
                f'show Hebrew char instead of name in sound question')

    # ── Pattern 3: "Type the Hebrew letter: Ayin" / "Type the letter: Ayin" ──
    m = re.match(r'^Type (?:the |this )?(?:Hebrew )?letter:?\s*(.+?)\??\s*$', qtext)
    if m and answer_lower == m.group(1).strip().lower():
        # Old: Q="Type the Hebrew letter: Ayin" A="Ayin" → testing if user can type the NAME
        # Fix: show Hebrew char, ask to type name
        new_q = f'Type the name of this Hebrew letter: {heb_char}'
        return (True, new_q, name, item['options_json'],
                f'show char, ask to type name')

    # ── Pattern 4: "How is this letter transliterated: Ayin?" ──
    m = re.match(r'^How is this letter transliterated:\s*(.+?)\??\s*$', qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f'How is this letter transliterated: {heb_char}?'
        return (True, new_q, name, item['options_json'],
                f'show char instead of name for transliteration')

    # ── Pattern 5: "What is the Hebrew letter named 'Ayin'?" ──
    m = re.match(r"^What is the Hebrew letter named\s*'([^']+)'\??\s*$", qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f'What Hebrew letter is this: {heb_char}?'
        return (True, new_q, name, item['options_json'],
                f'show char instead of name in recall')

    # ── Pattern 6: "What is Ayin in Hebrew?" ──
    m = re.match(r'^What is\s+(.+?)\s+in Hebrew\??\s*$', qtext)
    if m and answer_lower == m.group(1).strip().lower():
        new_q = f'What is this Hebrew letter: {heb_char}?'
        return (True, new_q, name, item['options_json'],
                f'show char instead of name')

    # ── Pattern 7: "How is X (Ayin) transliterated?" ──
    # These already have Hebrew char in Q. They're fine.

    return (False, qtext, answer, item['options_json'], '')


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

    items = conn.execute("""
        SELECT pi.*, n.category, n.title as node_title
        FROM hebrew_practice_items pi
        JOIN hebrew_nodes n ON n.id = pi.node_id
        ORDER BY n.category, pi.node_id, pi.id
    """).fetchall()

    print(f"Checking {len(items)} practice items...\n")

    fixes = []
    for item in items:
        node = {'category': item['category'], 'title': item['node_title']}
        should_fix, new_q, new_a, new_opts, reason = build_fix(dict(item), node)
        if should_fix:
            fixes.append((dict(item), new_q, new_a, new_opts, reason))

    # Group by node for display
    by_node = {}
    for item, nq, na, no, reason in fixes:
        nid = item['node_id']
        if nid not in by_node:
            by_node[nid] = {
                'items': [],
                'category': item['category'],
                'title': item['node_title'],
                'heb': get_hebrew_char(item['node_title']),
            }
        by_node[nid]['items'].append((item, nq, na, reason))

    total_by_cat = {}
    for nid, info in sorted(by_node.items()):
        total_by_cat[info['category']] = total_by_cat.get(info['category'], 0) + len(info['items'])
        print(f"\n  {nid:20s} ({info['title'][:35]:35s}) heb={info['heb']:4s} [{info['category']}]")
        for item, nq, na, reason in info['items']:
            print(f"    #{item['id']} [{item['question_type']:16s}] → {reason}")
            print(f"       OLD: {item['question_text'][:65]}")
            print(f"       NEW: {nq[:65]}")
            print(f"       OLD A: {item['correct_answer'][:30]}  NEW A: {na[:30]}")

    print(f"\n  Summary by category:")
    for cat, cnt in sorted(total_by_cat.items(), key=lambda x: -x[1]):
        print(f"    {cat:15s}: {cnt} fixes")
    print(f"\n  TOTAL: {len(fixes)} items need fixing")

    if not args.apply:
        print(f"\n  → Run with --apply to apply {len(fixes)} fixes.")
        conn.close()
        return

    # ── Apply fixes ──
    print(f"\n  Applying fixes...")
    cur = conn.cursor()
    applied = 0
    for item, new_q, new_a, new_opts, reason in fixes:
        cur.execute(
            "UPDATE hebrew_practice_items SET question_text=?, correct_answer=? WHERE id=?",
            (new_q, new_a, item['id'])
        )
        applied += 1

    conn.commit()
    print(f"  ✅ Applied {applied} fixes to {MEM_DB.name}")

    # Verify
    cur2 = conn.execute("""
        SELECT pi.id, pi.question_text, n.title
        FROM hebrew_practice_items pi
        JOIN hebrew_nodes n ON n.id = pi.node_id
        WHERE n.category IN ('consonant', 'vowel')
        ORDER BY n.id, pi.id
    """)
    bad_remaining = 0
    for r in cur2.fetchall():
        # Check if any vowel/consonant items still have the name in the Q
        name = get_letter_name(r['title'])
        if name.lower() in r['question_text'].lower() and 'transliterated' not in r['question_text']:
            bad_remaining += 1
    if bad_remaining:
        print(f"  ⚠ {bad_remaining} items may still have issues (manual review needed)")
    else:
        print(f"  ✓ All vowel/consonant items verified clean")

    conn.close()


if __name__ == "__main__":
    main()
