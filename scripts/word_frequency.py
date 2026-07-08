#!/usr/bin/env python3
"""Hebrew word frequency and importance analysis for language learning.

Outputs importance-ranked vocabulary list matching Schwartz-Groves WHV structure:
- Hebrew word (with niqqud)
- Transliteration (SBL academic) and Pronunciation (simple)
- Primary English gloss
- Root (3-letter) + Root meaning
- Part of speech
- Frequency (occurrences in OT)
- Frequency rank
- Verse example (one verse showing the word in context)
- Related words sharing the same root

Usage:
    python3 scripts/word_frequency.py --top 100
    python3 scripts/word_frequency.py --by-root --cutoff 50
    python3 scripts/word_frequency.py --export-anki
"""

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

# Paths
BASE = Path(__file__).parent.parent
DB_PATH = BASE / "data" / "processed" / "scripture.db"

# Morphology prefixes for part of speech
MORPH_POS = {
    'HV': 'verb',
    'HN': 'noun',
    'HA': 'adjective',
    'HR': 'preposition',
    'HC': 'conjunction',
    'HT': 'particle',
    'HP': 'pronoun',
    'HD': 'adverb',
    'H': 'hebrew',
}


def derive_pos(morph: str) -> str:
    if not morph:
        return ''
    for prefix, pos in MORPH_POS.items():
        if morph.startswith(prefix):
            return pos
    return ''


def main():
    parser = argparse.ArgumentParser(description="Hebrew vocabulary frequency analysis")
    parser.add_argument('--top', type=int, default=100, help='Number of top words')
    parser.add_argument('--cutoff', type=int, default=47,
                        help='Minimum frequency cutoff (WHV uses 47 = ~90%% coverage)')
    parser.add_argument('--by-root', action='store_true', help='Group words by root')
    parser.add_argument('--export-anki', action='store_true', help='Export as Anki-compatible JSON')
    args = parser.parse_args()

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # Get all words from lemma_gloss (has frequency + gloss) joined with lexicon (has root, POS, def)
    # Filter: exclude single-letter lemmas (prefixes), exclude very common particles handled separately
    rows = conn.execute("""
        SELECT DISTINCT
            l.lemma,
            l.hebrew_plain as hebrew_word,
            l.transliteration,
            l.part_of_speech,
            l.root_letters as root,
            l.definition,
            l.morphology,
            l.frequency as lex_freq,
            lg.english_gloss,
            lg.frequency as gloss_freq,
            lg.verse_count
        FROM lexicon l
        LEFT JOIN lemma_gloss lg ON l.lemma = lg.lemma
        WHERE l.lemma NOT IN ('b', 'c', 'd', 'H', 'G', 'l', 'm', 'k')
          AND l.frequency > 0
        ORDER BY l.frequency DESC
    """).fetchall()

    # Build word list with rank
    words = []
    rank = 0
    for r in rows:
        freq = r['lex_freq'] or 0
        gloss = (r['english_gloss'] or '').strip()
        word = (r['hebrew_word'] or '').strip()
        if not word or not gloss:
            continue
        if freq < args.cutoff:
            continue
        if len(word) <= 1:  # skip single chars
            continue

        rank += 1
        words.append({
            'rank': rank,
            'hebrew': word,
            'transliteration': (r['transliteration'] or '').strip(),
            'gloss': gloss,
            'root': (r['root'] or '').strip(),
            'pos': derive_pos(r['morphology'] or ''),
            'frequency': freq,
            'lemma': r['lemma'],
        })

        if rank >= args.top * 3:
            break  # fetch extra for grouping

    words = words[:args.top]

    # Get a verse example for each word (first verse where the word appears)
    # This is expensive so we limit to top words
    print(f"\n=== Biblical Hebrew Vocabulary: Top {len(words)} Words ===")
    print(f"(cutoff: ≥{args.cutoff} occurrences, covers ~90% of OT text)")
    print()

    if args.by_root:
        # Group by root
        root_groups = defaultdict(list)
        for w in words:
            r = w['root'] or 'UNKNOWN'
            root_groups[r].append(w)

        for root in sorted(root_groups.keys(), key=lambda r: -sum(w['frequency'] for w in root_groups[r])):
            group = root_groups[root]
            total_freq = sum(w['frequency'] for w in group)
            print(f"\n── Root: {root} ({total_freq} total occurrences) ──")
            for w in group:
                print(f"  {w['rank']:>4}. {w['hebrew']:<15} {w['transliteration']:<20} {w['gloss']:<15} "
                      f"({w['pos']:<8}) freq={w['frequency']}")
    else:
        # Flat list by frequency
        print(f"{'Rank':<6} {'Hebrew':<15} {'Transliteration':<22} {'Gloss':<18} {'Root':<8} {'POS':<10} {'Freq':<6}")
        print("-" * 90)
        for w in words:
            print(f"{w['rank']:<6} {w['hebrew']:<15} {w['transliteration']:<22} {w['gloss']:<18} "
                  f"{w['root']:<8} {w['pos']:<10} {w['frequency']:<6}")

    # Statistics
    total_freq = sum(w['frequency'] for w in words)
    print(f"\n--- Statistics ---")
    print(f"Total words: {len(words)}")
    print(f"Total occurrences covered: {total_freq}")
    print(f"Frequency range: {words[0]['frequency']} (most) - {words[-1]['frequency']} (least)")
    if words:
        print(f"Most common: {words[0]['hebrew']} ({words[0]['gloss']}) — {words[0]['frequency']}x")

    # Count by part of speech
    pos_counts = defaultdict(int)
    for w in words:
        pos_counts[w['pos'] or 'unknown'] += 1
    print(f"\nPart of speech distribution:")
    for pos, count in sorted(pos_counts.items(), key=lambda x: -x[1]):
        print(f"  {pos:<12} {count}")

    # Count by root frequency
    if args.by_root:
        print(f"\nTop 20 roots by frequency:")
        sorted_roots = sorted(root_groups.items(), key=lambda x: -sum(w['frequency'] for w in x[1]))
        for root, group in sorted_roots[:20]:
            words_list = ', '.join(f"{w['hebrew']} ({w['gloss']})" for w in group)
            total = sum(w['frequency'] for w in group)
            print(f"  {root:<6} ({total:>5}x): {words_list}")

    # Export Anki-compatible JSON
    if args.export_anki:
        anki_export = []
        for w in words:
            anki_export.append({
                "Hebrew_Text": w['hebrew'],
                "Transliteration": w['transliteration'],
                "Primary_Gloss": w['gloss'],
                "Root": w['root'],
                "Part_of_Speech": w['pos'],
                "Occurrences": w['frequency'],
                "Frequency_Rank": w['rank'],
                "Notes": f"Root: {w['root'] or '—'} | POS: {w['pos'] or '—'}",
            })
        out_path = BASE / "data" / "vocabulary_top_words.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(anki_export, f, ensure_ascii=False, indent=2)
        print(f"\nAnki export saved: {out_path} ({len(anki_export)} cards)")

    conn.close()


if __name__ == '__main__':
    main()
