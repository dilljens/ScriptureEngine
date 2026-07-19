"""
Build passage-level connections — run all passage generators.

Usage:
    python3 scripts/build_passage_connections.py                   # All books
    python3 scripts/build_passage_connections.py --books gen,exod  # Specific books
    python3 scripts/build_passage_connections.py --generator density  # Specific generator
"""

import argparse
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_db():
    """Get database connection."""
    from lib.db import get_db
    return get_db()


def run_generators(conn, book_ids=None, gen_filter=None):
    """Run passage-level generators."""
    generators = []

    if not gen_filter or gen_filter == "density":
        from generators.passage.density_cluster import run as run_density
        generators.append(("density_cluster", run_density))

    if not gen_filter or gen_filter == "book_coherence":
        from generators.passage.book_coherence import run as run_book
        generators.append(("book_coherence", run_book))

    if not gen_filter or gen_filter == "chiastic":
        from generators.passage.chiastic_promoter import run as run_chiastic
        generators.append(("chiastic_promoter", run_chiastic))

    if not gen_filter or gen_filter == "genre":
        from generators.passage.genre_tagger import run as run_genre
        generators.append(("genre_tagger", run_genre))

    if not gen_filter or gen_filter == "theme":
        from generators.passage.theme_tracer import run as run_theme
        generators.append(("theme_tracer", run_theme))

    total = 0
    for name, gen_fn in generators:
        t0 = time.time()
        try:
            count = gen_fn(conn, book_ids=book_ids)
            elapsed = time.time() - t0
            logger.info("  %s: %d connections (%.1fs)", name, count, elapsed)
            total += count
        except Exception as e:
            logger.error("  %s failed: %s", name, e, exc_info=True)

    logger.info("Total passage connections created: %d", total)
    return total


def main():
    parser = argparse.ArgumentParser(description="Build passage-level connections")
    parser.add_argument("--books", help="Comma-separated book IDs (default: all)")
    parser.add_argument("--generator", choices=["density", "book_coherence", "chiastic", "genre", "theme"],
                        help="Specific generator to run (default: all)")
    args = parser.parse_args()

    book_ids = args.books.split(",") if args.books else None
    conn = get_db()

    t0 = time.time()
    count = run_generators(conn, book_ids=book_ids, gen_filter=args.generator)
    elapsed = time.time() - t0
    logger.info("Done: %d connections in %.1fs", count, elapsed)


if __name__ == "__main__":
    main()
