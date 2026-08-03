#!/usr/bin/env python3
"""Generate sentence-cloze practice items for reading nodes from real verses.

P5 goal: the strongest card type embeds BOTH a word and a construction in one
retrieval (Pimsleur "organic learning" / Duolingo full-sentence pattern). For
each reading node (read_exo11 etc.) this pulls actual verses from scripture.db
and creates:

  - Hebrew cloze: the pointed verse with the target word blanked → type it
    (options = the word + confusable distractors, English hint given)
  - English cloze: the English verse with the target gloss blanked → pick the
    Hebrew word that fills the blank

Target words are the highest-frequency words in the verse (from the lexicon),
so cloze exercises the vocabulary the learner is most likely to meet.

Usage:
    python3 scripts/generate_sentence_cloze.py --dry-run
    python3 scripts/generate_sentence_cloze.py --apply [--limit 5] [--per-node 6]
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
MEM_DB = BASE / "data" / "memorize.db"
SCRIPTURE_DB = BASE / "data" / "processed" / "scripture.db"


def strip_niqqud(t):
    return re.sub(r"[\u0591-\u05C7]", "", t or "").strip()


def normalize_final(w):
    return w.replace("ך", "כ").replace("ם", "מ").replace("ן", "נ") \
            .replace("ף", "פ").replace("ץ", "צ")


def split_words(heb_text):
    """Split OSHB verse text into displayable Hebrew words (dropping the /
    morpheme separator inside words, keeping words whole)."""
    text = re.sub(r"[\u0591-\u05C7]", "", heb_text or "")
    words = []
    for chunk in text.split():
        # chunk may contain '/' between morphemes — treat as one word
        word = chunk.replace("/", "").strip()
        if word:
            words.append(word)
    return words


def high_frequency_words(scrip, verse_heb, top_n=3):
    """Pick the most frequent words in a verse using lexicon frequency."""
    words = split_words(verse_heb)
    if not words:
        return []
    # Look up frequency for each normalized word
    freqs = {}
    for w in set(words):
        try:
            row = scrip.execute(
                "SELECT frequency FROM lexicon WHERE hebrew_plain=? ORDER BY frequency DESC LIMIT 1",
                (normalize_final(w),)).fetchone()
            freqs[w] = row[0] if row else 0
        except Exception:
            freqs[w] = 0
    ranked = sorted(words, key=lambda w: (-freqs.get(w, 0), w))
    # Skip ultra-common function words (the, and, to, from...) — too easy as
    # cloze targets; prefer content words.
    skip = {"את", "אל", "על", "כי", "אשר", "כל", "לא", "ויהי", "ויאמר",
            "אני", "אתה", "הוא", "היא", "אנחנו", "אתם", "הם", "הנה",
            "אשר", "יום", "עד", "אחר", "בין", "תחת", "עם"}
    picked = [w for w in ranked if normalize_final(w) not in skip][:top_n]
    return picked


def distractor_words(scrip, target, count=3):
    """Confusable-ish distractors: other Hebrew words sharing the same root or
    same first two letters, else the closest-frequency words in the lexicon.
    Prefixed variants of the target (ומיהוה vs יהוה) are excluded — they'd be
    rejected too easily and test prefixes, not word discrimination."""
    t = normalize_final(target)
    stem = strip_prefixes(t)
    row = scrip.execute("SELECT root_letters FROM lexicon WHERE hebrew_plain=? LIMIT 1", (t,)).fetchone()
    root = row[0] if row else None
    candidates = []
    if root:
        same_root = scrip.execute(
            "SELECT hebrew_plain FROM lexicon WHERE root_letters=? AND hebrew_plain != ? "
            "AND length(hebrew_plain) <= ? ORDER BY frequency DESC LIMIT ?",
            (root, t, len(t) + 2, count * 4)).fetchall()
        candidates = [r[0] for r in same_root]
    if len(candidates) < count:
        rows = scrip.execute(
            "SELECT hebrew_plain FROM lexicon WHERE length(hebrew_plain) >= ? AND length(hebrew_plain) <= ? "
            "AND hebrew_plain != ? ORDER BY frequency DESC LIMIT ?",
            (max(1, len(t) - 2), len(t) + 2, t, count * 6)).fetchall()
        candidates += [r[0] for r in rows]
    # Final pad from the whole lexicon if still short (any distinct word)
    if len(candidates) < count:
        rows = scrip.execute(
            "SELECT hebrew_plain FROM lexicon WHERE hebrew_plain != ? "
            "AND length(hebrew_plain) >= 2 AND length(hebrew_plain) <= 8 "
            "ORDER BY frequency DESC LIMIT ?",
            (t, count * 8)).fetchall()
        candidates += [r[0] for r in rows]
    # Dedup + exclude prefixed variants of the target
    seen = set()
    out = []
    for c in candidates:
        cn = normalize_final(c)
        if not cn or cn in seen:
            continue
        if cn == t:
            continue
        # Same stem once prefixes are stripped → too easy to reject
        if strip_prefixes(cn) == stem:
            continue
        seen.add(cn)
        out.append(cn)
        if len(out) >= count:
            break
    return out


_PREFIXES = ("ו", "ב", "כ", "ל", "מ", "ה", "א")


def strip_prefixes(word):
    """Strip OSHB proclitic prefixes (vav/be/ke/le/mi/ha/ve) to get the stem.
    Handles stacked prefixes like ומיהוה → יהוה."""
    w = word
    changed = True
    while changed and w:
        changed = False
        for p in _PREFIXES:
            if w.startswith(p) and len(w) > 1:
                # Don't strip if it would leave a single letter (e.g. 'את' → 'ת')
                w = w[len(p):]
                changed = True
                break
    return w


def generate_for_node(scrip, conn, node_id, book, chapter, per_node):
    """Generate cloze items for one reading node. Returns list of item dicts."""
    verses = scrip.execute(
        "SELECT verse, text_english, text_hebrew FROM verses "
        "WHERE book_id=? AND chapter=? AND text_english != '' ORDER BY verse LIMIT 50",
        (book, chapter)).fetchall()
    items = []
    for v in verses:
        if len(items) >= per_node:
            break
        heb = v["text_hebrew"]
        eng = (v["text_english"] or "").strip()
        targets = high_frequency_words(scrip, heb)
        for target in targets[:2]:
            words = split_words(heb)
            if target not in words:
                continue
            # Build the cloze: replace the first occurrence of target with ___
            cloze = " ".join("___" if w == target else w for w in words)
            dist = distractor_words(scrip, target, 3)
            opts = json.dumps([target] + [d for d in dist if d != target][:3], ensure_ascii=False)
            # Hebrew cloze: blank the word, English hint
            items.append({
                "node_id": node_id,
                "question_type": "cloze",
                "question_text": f"Fill in the blank (hint: {eng[:60]}…): {cloze}",
                "options_json": json.dumps([target], ensure_ascii=False),
                "correct_answer": target,
                "difficulty": 0.6,
                "explanation": f"'{target}' from {book}.{chapter}.{v['verse']}",
            })
            # English cloze: blank the gloss, pick the Hebrew word. Only emit
            # when we found ≥2 real distractors (else the MC would be a giveaway).
            # Gloss lookup: lexicon (by plain form) → lemma → lemma_gloss
            gloss = None
            lex = scrip.execute(
                "SELECT lemma FROM lexicon WHERE hebrew_plain=? ORDER BY frequency DESC LIMIT 1",
                (normalize_final(target),)).fetchone()
            if lex:
                g2 = scrip.execute(
                    "SELECT english_gloss FROM lemma_gloss WHERE lemma=? LIMIT 1",
                    (lex[0],)).fetchone()
                if g2:
                    gloss = g2[0]
            if gloss and eng and len(dist) >= 2:
                # blank the gloss in the English sentence if present
                eng_cloze = re.sub(rf"\b{re.escape(gloss)}\b", "___", eng, count=1, flags=re.IGNORECASE)
                if "___" in eng_cloze:
                    items.append({
                        "node_id": node_id,
                        "question_type": "multiple_choice",
                        "question_text": f"Which Hebrew word fills the blank? “{eng_cloze}”",
                        "options_json": opts,
                        "correct_answer": target,
                        "difficulty": 0.55,
                        "explanation": f"'{gloss}' = {target} ({book}.{chapter}.{v['verse']})",
                    })
            if len(items) >= per_node:
                break
    return items


def reading_nodes(conn):
    """(node_id, book, chapter) for every read_* node with a passage description."""
    rows = conn.execute("SELECT id, description FROM hebrew_nodes WHERE category='reading'").fetchall()
    out = []
    for rid, desc in rows:
        m = re.search(r"Read\s+([a-z0-9]+)\.(\d+)", desc or "")
        if m:
            out.append((rid, m.group(1), int(m.group(2))))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="Only process first N nodes")
    ap.add_argument("--per-node", type=int, default=6, help="Max cloze items per node")
    args = ap.parse_args()

    if not (args.dry_run or args.apply):
        print("Pass --dry-run to preview or --apply to insert")
        return

    conn = sqlite3.connect(str(MEM_DB))
    conn.row_factory = sqlite3.Row
    scrip = sqlite3.connect(str(SCRIPTURE_DB))
    scrip.row_factory = sqlite3.Row

    nodes = reading_nodes(conn)
    if args.limit:
        nodes = nodes[:args.limit]
    print(f"Reading nodes with passages: {len(nodes)}")

    total_new = 0
    for i, (rid, book, chapter) in enumerate(nodes):
        # Skip nodes that already have cloze items (idempotent)
        has_cloze = conn.execute(
            "SELECT 1 FROM hebrew_practice_items WHERE node_id=? AND question_type IN ('cloze','multiple_choice') AND question_text LIKE '%___%' LIMIT 1",
            (rid,)).fetchone()
        if has_cloze:
            continue
        items = generate_for_node(scrip, conn, rid, book, chapter, args.per_node)
        if args.dry_run:
            if items:
                print(f"[{i+1}/{len(nodes)}] {rid}: {len(items)} cloze items "
                      f"(e.g. '{items[0]['question_text'][:50]}…')")
            continue
        for it in items:
            conn.execute(
                "INSERT OR IGNORE INTO hebrew_practice_items "
                "(node_id, question_type, question_text, options_json, correct_answer, difficulty, explanation) "
                "VALUES (?,?,?,?,?,?,?)",
                (it["node_id"], it["question_type"], it["question_text"],
                 it["options_json"], it["correct_answer"], it["difficulty"], it["explanation"]))
            total_new += 1
        if (i + 1) % 10 == 0:
            conn.commit()
            print(f"  {i+1}/{len(nodes)} nodes… ({total_new} items)")

    if args.apply:
        conn.commit()
    conn.close()
    scrip.close()
    print(f"Done: {total_new} sentence-cloze items inserted" if args.apply else "Dry run complete")


if __name__ == "__main__":
    main()
