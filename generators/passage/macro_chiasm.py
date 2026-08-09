"""Macro-Chiasm — detect book-level mirrored section structure.

Splits each book into chapter-sized sections, computes a rare-word signature
per section, and looks for symmetric (mirror) pairs A B C ... C' B' A' by
comparing section i with section n-1-i. A mirror pair is emitted as a
passage_connections row (type='macro_chiasm') only when the symmetric overlap
is clearly above the book's own cross-pair baseline — keeps false positives low.

This is a discovery generator (passage-level).
"""

import logging
import re
from collections import defaultdict

from ._common import upsert

logger = logging.getLogger(__name__)

# Common words that carry no structural signal for chiasm detection.
STOPWORDS = {
    "the", "and", "that", "for", "with", "unto", "them", "their", "shall",
    "lord", "god", "israel", "said", "hath", "from", "this", "they", "thou",
    "thy", "thee", "have", "will", "which", "were", "was", "his", "her",
    "all", "not", "but", "you", "your", "when", "then", "also",
}

WORD_RE = re.compile(r"[a-z']{4,}")


def _section_signatures(conn, book_id):
    """Return {chapter: set(rare words)} for a book."""
    rows = conn.execute(
        "SELECT chapter, text_english FROM verses WHERE book_id = ? ORDER BY chapter, verse",
        (book_id,),
    ).fetchall()

    per_chapter = defaultdict(list)
    for r in rows:
        per_chapter[r["chapter"]].append(r["text_english"])

    # Global word frequencies within this book (words appearing >= 2 times).
    freq = defaultdict(int)
    for texts in per_chapter.values():
        seen = set()
        for t in texts:
            for w in WORD_RE.findall(t.lower()):
                if w not in STOPWORDS:
                    seen.add(w)
        for w in seen:
            freq[w] += 1

    signatures = {}
    for chapter, texts in per_chapter.items():
        words = set()
        for t in texts:
            for w in WORD_RE.findall(t.lower()):
                if w not in STOPWORDS and freq[w] >= 2:
                    words.add(w)
        signatures[chapter] = words
    return signatures


def _overlap(a, b):
    """Jaccard-ish overlap: shared / smaller set size. 0 if either is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def run(conn, book_ids=None) -> int:
    """Detect mirrored sections per book and emit macro_chiasm connections.

    Returns the number of passage_connections created.
    """
    books = book_ids or [r["id"] for r in conn.execute("SELECT id FROM books").fetchall()]

    total = 0
    for book in books:
        signatures = _section_signatures(conn, book)
        chapters = sorted(signatures)
        n = len(chapters)
        if n < 6:  # need at least A B C C' B' A'
            continue

        # Baseline: average overlap of all cross-pairs (excluding mirror pairs).
        cross = []
        mirrors = []
        for i in range(n):
            for j in range(i + 1, n):
                o = _overlap(signatures[chapters[i]], signatures[chapters[j]])
                if i + j == n - 1:
                    mirrors.append((chapters[i], chapters[j], o))
                else:
                    cross.append(o)
        baseline = (sum(cross) / len(cross)) if cross else 0.0

        for ci, cj, o in mirrors:
            if o >= 0.15 and o > baseline + 0.05:
                a = {"start": f"{book}.{ci}.1", "end": _chapter_end(conn, book, ci), "book": book}
                b = {"start": f"{book}.{cj}.1", "end": _chapter_end(conn, book, cj), "book": book}
                if a["start"] == b["start"]:
                    continue
                if upsert(
                    conn, a, b, "structural", "macro_chiasm",
                    strength=round(o, 2), confidence=0.4,
                    metadata={"chapters": [ci, cj], "overlap": round(o, 3),
                              "source": "macro_chiasm"},
                ):
                    total += 1
        conn.commit()

    logger.info("macro_chiasm: %d connections created", total)
    return total


def _chapter_end(conn, book, chapter):
    """Last verse id in a chapter."""
    row = conn.execute(
        "SELECT id FROM verses WHERE book_id = ? AND chapter = ? ORDER BY verse DESC LIMIT 1",
        (book, chapter),
    ).fetchone()
    return row["id"] if row else f"{book}.{chapter}.1"
