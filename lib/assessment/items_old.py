"""Assessment item generation — shows actual verse text, asks meaningful questions.

Instead of testing obscure verse-reference trivia, generates questions that:
  - Show both verses' text so the user can SEE the connection
  - Ask specific, answerable questions about the relationship
  - Use full book names (not abbreviations)
  - Actually teach scripture interconnectedness

Question types:
  1. Connection type ID — show 2 passages, ask what connects them
  2. Shared word — show 2 passages with shared word, ask what it is
  3. Quotation source — show a quotation, ask where it's from
  4. Thematic grouping — show verses, ask what theme connects them
"""

import json
import logging
import os
import random
import re

logger = logging.getLogger(__name__)
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from lib.db import get_db

FULL_BOOK_NAMES = {
    'gen': 'Genesis', 'exo': 'Exodus', 'lev': 'Leviticus', 'num': 'Numbers', 'deu': 'Deuteronomy',
    'josh': 'Joshua', 'judg': 'Judges', 'ruth': 'Ruth',
    '1sam': '1 Samuel', '2sam': '2 Samuel', '1kgs': '1 Kings', '2kgs': '2 Kings',
    '1chr': '1 Chronicles', '2chr': '2 Chronicles',
    'ezra': 'Ezra', 'neh': 'Nehemiah', 'esth': 'Esther',
    'job': 'Job', 'psa': 'Psalms', 'prov': 'Proverbs', 'eccl': 'Ecclesiastes', 'song': 'Song of Solomon',
    'isa': 'Isaiah', 'jer': 'Jeremiah', 'lam': 'Lamentations', 'ezek': 'Ezekiel', 'dan': 'Daniel',
    'hos': 'Hosea', 'joel': 'Joel', 'amos': 'Amos', 'obad': 'Obadiah', 'jonah': 'Jonah',
    'mic': 'Micah', 'nah': 'Nahum', 'hab': 'Habakkuk', 'zeph': 'Zephaniah', 'hag': 'Haggai',
    'zech': 'Zechariah', 'mal': 'Malachi',
    'matt': 'Matthew', 'mark': 'Mark', 'luke': 'Luke', 'john': 'John',
    'acts': 'Acts', 'rom': 'Romans',
    '1cor': '1 Corinthians', '2cor': '2 Corinthians', 'gal': 'Galatians', 'eph': 'Ephesians',
    'phil': 'Philippians', 'col': 'Colossians', '1thes': '1 Thessalonians', '2thes': '2 Thessalonians',
    '1tim': '1 Timothy', '2tim': '2 Timothy', 'titus': 'Titus', 'philem': 'Philemon',
    'heb': 'Hebrews', 'james': 'James', '1pet': '1 Peter', '2pet': '2 Peter',
    '1john': '1 John', '2john': '2 John', '3john': '3 John', 'jude': 'Jude', 'rev': 'Revelation',
    '1ne': '1 Nephi', '2ne': '2 Nephi', 'jacob': 'Jacob', 'enos': 'Enos',
    'jarom': 'Jarom', 'omni': 'Omni', 'wom': 'Words of Mormon',
    'mosiah': 'Mosiah', 'alma': 'Alma', 'hel': 'Helaman',
    '3ne': '3 Nephi', '4ne': '4 Nephi', 'morm': 'Mormon', 'ether': 'Ether', 'moro': 'Moroni',
    'moses': 'Moses', 'abraham': 'Abraham', 'jsm': 'Joseph Smith—Matthew',
    'jsh': 'Joseph Smith—History', 'aoff': 'Articles of Faith',
}

# Pedagogically useful connection types for assessment
USEFUL_TYPES = [
    'direct_quotation', 'same_lemma', 'allusion', 'parallel_synonymous',
    'parallel_antithetic', 'type_antitype',
]

CONNECTION_LABELS = {
    'direct_quotation': 'Direct quotation — one passage directly quotes the other',
    'same_lemma': 'Shared Hebrew or Greek word — both passages use the same original-language word',
    'allusion': 'Allusion — one passage echoes the other through shared imagery or phrasing',
    'parallel_synonymous': 'Synonymous parallelism — same idea expressed in parallel form',
    'parallel_antithetic': 'Antithetic parallelism — contrasting ideas set against each other',
    'type_antitype': 'Type and antitype — one event prefigures the other',
}

CONNECTION_SHORT = {
    'direct_quotation': 'Direct quotation',
    'same_lemma': 'Shared vocabulary word',
    'allusion': 'Allusion/echo',
    'parallel_synonymous': 'Parallel idea',
    'parallel_antithetic': 'Contrasting idea',
    'type_antitype': 'Type/antitype',
}


def fmt_ref(verse_id):
    """Format a verse reference like 'gen.1.1' into 'Genesis 1:1'."""
    parts = verse_id.split('.')
    if len(parts) >= 3:
        book = FULL_BOOK_NAMES.get(parts[0], parts[0].upper())
        return f"{book} {parts[1]}:{parts[2]}"
    elif len(parts) == 2:
        book = FULL_BOOK_NAMES.get(parts[0], parts[0].upper())
        return f"{book} {parts[1]}"
    return verse_id


def truncate_text(text, max_chars=150):
    """Truncate text to max_chars, adding ellipsis if needed."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '...'


class AssessmentGenerator:
    """Generates assessment questions that show verse text and teach connections."""

    def __init__(self, conn):
        self.conn = conn

    def generate_all(self, count=200):
        """Generate a balanced set of assessment questions.

        Uses efficient batch-fetching to minimize DB queries.
        """
        items = []

        # Pre-fetch random connection pairs (batch, one query)
        in_clause = ','.join('?' for _ in USEFUL_TYPES)
        sql_text = f"""
            SELECT c.type, c.source_verse, c.target_verse,
                   v1.text_english as t1, v2.text_english as t2
            FROM connections c
            JOIN verses v1 ON v1.id = c.source_verse
            JOIN verses v2 ON v2.id = c.target_verse
            WHERE c.deprecated=0
            AND c.type IN ({in_clause})
            AND v1.text_english IS NOT NULL AND v2.text_english IS NOT NULL
            AND length(v1.text_english) BETWEEN 20 AND 180
            AND length(v2.text_english) BETWEEN 20 AND 180
            AND c.source_verse NOT LIKE 'dss.%' AND c.target_verse NOT LIKE 'dss.%'
            AND v1.book_id NOT LIKE '1esd%' AND v2.book_id NOT LIKE '1esd%'
            AND v1.book_id NOT LIKE 'sir%' AND v2.book_id NOT LIKE 'sir%'
            AND v1.book_id NOT LIKE '1en%' AND v2.book_id NOT LIKE '1en%'
            AND v1.book_id NOT LIKE '2en%' AND v2.book_id NOT LIKE '2en%'
            AND v1.book_id NOT LIKE '2esd%' AND v2.book_id NOT LIKE '2esd%'
            AND v1.book_id NOT LIKE '1ma%' AND v2.book_id NOT LIKE '1ma%'
            AND v1.book_id NOT LIKE '2ma%' AND v2.book_id NOT LIKE '2ma%'
            AND v1.book_id NOT LIKE 'tob%' AND v2.book_id NOT LIKE 'tob%'
            ORDER BY RANDOM() LIMIT ?
        """
        params = USEFUL_TYPES + [count * 3]
        pairs = self.conn.execute(sql_text, params)

        pair_list = [{
            "type": r[0], "source": r[1], "target": r[2],
            "source_text": truncate_text(r[3], 150), "target_text": truncate_text(r[4], 150),
        } for r in pairs]

        if not pair_list:
            return items

        # Type A: Connection type questions (use all pairs)
        for pair in pair_list:
            if len(items) >= count // 2:
                break
            correct = pair["type"]
            distractors = [t for t in USEFUL_TYPES if t != correct]
            random.shuffle(distractors)
            correct_label = CONNECTION_SHORT[correct]
            distractor_labels = [CONNECTION_SHORT[d] for d in distractors[:3]]
            options = [correct_label] + distractor_labels
            random.shuffle(options)
            items.append({
                "type": "multiple_choice",
                "question": (
                    f"**{fmt_ref(pair['source'])}** says:\n"
                    f"> “{pair['source_text']}”\n\n"
                    f"**{fmt_ref(pair['target'])}** says:\n"
                    f"> “{pair['target_text']}”\n\n"
                    f"What type of connection links these two passages?"
                ),
                "options": options,
                "correct_answer": correct_label,
                "explanation": CONNECTION_LABELS[correct],
                "bloom_level": "understand",
            })

        # Type B: Shared word questions (from same_lemma pairs)
        lemma_pairs = [p for p in pair_list if p["type"] == "same_lemma"]
        for pair in lemma_pairs:
            if len(items) >= count * 3 // 4:
                break
            options = [
                "They share a Hebrew or Greek word (same lemma)",
                "One directly quotes the other",
                "They describe similar events",
                "They use the same literary structure",
            ]
            random.shuffle(options)
            items.append({
                "type": "multiple_choice",
                "question": (
                    f"**{fmt_ref(pair['source'])}** says:\n"
                    f"> “{pair['source_text']}”\n\n"
                    f"**{fmt_ref(pair['target'])}** says:\n"
                    f"> “{pair['target_text']}”\n\n"
                    f"These passages are connected by sharing the same Hebrew or Greek word. "
                    f"What kind of connection is this?"
                ),
                "options": options,
                "correct_answer": "They share a Hebrew or Greek word (same lemma)",
                "explanation": (
                    f"**{fmt_ref(pair['source'])}** and **{fmt_ref(pair['target'])}** "
                    f"both use the same Hebrew or Greek word — a **same_lemma** connection."
                ),
                "bloom_level": "understand",
            })

        # Type C: Well-known quotation questions (no DB needed)
        known_pairs = [
            ("hab.2.4", "rom.1.17", "The just shall live by faith"),
            ("isa.53.1", "john.12.38", "Who hath believed our report?"),
            ("psa.22.1", "matt.27.46", "My God, my God, why hast thou forsaken me?"),
            ("psa.110.1", "matt.22.44", "The Lord said unto my Lord"),
            ("isa.7.14", "matt.1.23", "Behold, a virgin shall conceive"),
            ("psa.118.22", "matt.21.42", "The stone which the builders rejected"),
            ("isa.40.3", "matt.3.3", "The voice of one crying in the wilderness"),
            ("jer.31.15", "matt.2.18", "Rachel weeping for her children"),
            ("psa.69.9", "john.2.17", "The zeal of thine house hath eaten me up"),
            ("deu.8.3", "matt.4.4", "Man shall not live by bread alone"),
        ]
        random.shuffle(known_pairs)
        for ot_ref, nt_ref, quote in known_pairs:
            if len(items) >= count:
                break
            ot_book = FULL_BOOK_NAMES.get(ot_ref.split('.')[0], ot_ref.split('.')[0].upper())
            nt_book = FULL_BOOK_NAMES.get(nt_ref.split('.')[0], nt_ref.split('.')[0].upper())
            all_books = ['Isaiah', 'Psalms', 'Deuteronomy', 'Jeremiah', 'Genesis',
                         'Exodus', 'Hosea', 'Zechariah', 'Daniel', 'Proverbs', 'Job',
                         'Malachi', 'Joel', 'Amos', 'Micah']
            correct_book = ot_book
            distractors = [b for b in all_books if b != correct_book]
            random.shuffle(distractors)
            options = [correct_book] + distractors[:3]
            random.shuffle(options)
            items.append({
                "type": "multiple_choice",
                "question": (
                    f"The New Testament quotes the Old Testament hundreds of times. "
                    f"For example, **{nt_book}** {nt_ref.split('.')[1]}:{nt_ref.split('.')[2]} says:\n\n"
                    f"> “{quote}”\n\n"
                    f"Which Old Testament book is this quotation originally from?"
                ),
                "options": options,
                "correct_answer": correct_book,
                "explanation": (
                    f"This quotation is from **{ot_book}** ({ot_ref.split('.')[1]}:{ot_ref.split('.')[2]})."
                ),
                "bloom_level": "remember",
            })

        # Type D: Thematic grouping
        topics = self.conn.execute("""
            SELECT slug, name FROM topical_guide
            WHERE verse_count BETWEEN 5 AND 40
            ORDER BY RANDOM() LIMIT 20
        """).fetchall()
        for topic_slug, topic_name in topics:
            if len(items) >= count:
                break
            verses = self.conn.execute("""
                SELECT tg.verse_id, v.text_english
                FROM tg_verse_references tg
                JOIN verses v ON v.id = tg.verse_id
                WHERE tg.topic_id = ? AND v.text_english IS NOT NULL
                AND length(v.text_english) BETWEEN 20 AND 120
                ORDER BY RANDOM() LIMIT 3
            """, (topic_slug,)).fetchall()
            if len(verses) < 3:
                continue
            verse_lines = "\n".join(
                f"• “{truncate_text(v[1], 100)}” — {fmt_ref(v[0])}"
                for v in verses
            )
            others = self.conn.execute("""
                SELECT name FROM topical_guide WHERE slug != ? AND verse_count BETWEEN 5 AND 40
                ORDER BY RANDOM() LIMIT 3
            """, (topic_slug,)).fetchall()
            all_topics = [topic_name] + [r[0] for r in others if r[0] != topic_name]
            random.shuffle(all_topics)
            items.append({
                "type": "multiple_choice",
                "question": (
                    f"These three passages all share a theme from the Topical Guide:\n\n"
                    f"{verse_lines}\n\n"
                    f"Which theme do they share?"
                ),
                "options": all_topics,
                "correct_answer": topic_name,
                "explanation": f"All three are categorized under **{topic_name}** in the Topical Guide.",
                "bloom_level": "analyze",
            })

        random.shuffle(items)
        return items[:count]


def build_assessment_items(count=3000):
    """Build and store assessment items in the database."""
    conn = get_db()

    # Clear old items
    conn.execute("DELETE FROM assessment_items")
    conn.commit()

    gen = AssessmentGenerator(conn)
    items = gen.generate_all(count=count)

    stored = 0
    for item in items:
        try:
            conn.execute("""
                INSERT INTO assessment_items
                    (question_type, question_text, options_json, correct_answer, layer, bloom_level)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                item["type"],
                item["question"],
                json.dumps(item.get("options", [])),
                str(item["correct_answer"]),
                "p'shat",
                item.get("bloom_level", "remember"),
            ))
            stored += 1
        except Exception:
            pass

    conn.commit()
    logger.info("Generated %d items, stored %d", len(items), stored)
    conn.close()
    return stored


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build scripture understanding assessment")
    parser.add_argument("--count", type=int, default=3000, help="Number of items to generate")
    args = parser.parse_args()
    build_assessment_items(count=args.count)
