#!/usr/bin/env python3
"""Import Come Follow Me weekly lessons from churchofjesuschrist.org.

Fetches the 2026 Old Testament manual TOC, then each weekly lesson page,
extracts the body text, and upserts into the cfm_lessons table (idempotent
by ref_id). Run again to refresh — cached HTML + INSERT OR REPLACE make
re-runs cheap.

Usage:
    python3 scripts/import_cfm.py                 # all 52 lessons
    python3 scripts/import_cfm.py --limit 2       # first 2 (test)
    python3 scripts/import_cfm.py --dry-run       # list only
    python3 scripts/import_cfm.py --delay 2.0     # slower politeness
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from lib.db import get_db, init_db
from lib.ingest.church_site import (
    BASE,
    extract_body,
    fetch,
    page_title,
    parse_cfm_toc,
    set_delay,
)

MANUAL = "/study/manual/come-follow-me-for-home-and-church-old-testament-2026"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, default=2026, help="manual year (ref_id + TOC URL)")
    ap.add_argument("--limit", type=int, default=0, help="import only the first N lessons (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="list planned lessons, don't import")
    ap.add_argument("--delay", type=float, default=None, help="override inter-request delay (s)")
    ap.add_argument("--cache", default=str(ROOT / "data" / "raw" / "church_site"), help="raw HTML cache dir")
    args = ap.parse_args()

    if args.delay is not None:
        set_delay(args.delay)

    toc_url = f"{BASE}{MANUAL}?lang=eng"
    print(f"Fetching TOC: {toc_url}")
    toc_html = fetch(toc_url, cache_dir=args.cache)
    entries = parse_cfm_toc(toc_html)
    if args.limit:
        entries = entries[: args.limit]
    print(f"Found {len(entries)} weekly lessons")

    if args.dry_run:
        for e in entries:
            print(f"  {e['slug']}  {e['date_range']}  — {e['scripture_block']}")
        return

    init_db()
    conn = get_db()
    total = len(entries)
    for i, e in enumerate(entries, 1):
        url = f"{BASE}{MANUAL}/{e['slug']}?lang=eng"
        html = fetch(url, cache_dir=args.cache)
        body = extract_body(html)
        title = page_title(html) or e["scripture_block"]
        ref_id = f"cfm.{args.year}.{e['slug']}"
        conn.execute(
            """INSERT OR REPLACE INTO cfm_lessons
               (ref_id, year, week_slug, date_range, start_date, end_date,
                title, scripture_block, text)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (ref_id, args.year, e["slug"], e["date_range"], e["start_date"],
             e["end_date"], title, e["scripture_block"], body),
        )
        conn.commit()
        print(f"  [{i}/{total}] {ref_id} {e['date_range']} — {title[:55]} ({len(body)} chars)")

    print(f"\nDone. {len(entries)} lessons in cfm_lessons.")


if __name__ == "__main__":
    main()
