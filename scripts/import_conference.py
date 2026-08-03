#!/usr/bin/env python3
"""Import General Conference talk transcripts from churchofjesuschrist.org.

For each conference in the covered range (default 2021.04 → 2026.04), fetches
the session page, parses sessions + talk slugs, then each talk page, extracts
the body text, and upserts into the talks table (idempotent by ref_id).

Usage:
    python3 scripts/import_conference.py                  # 2021.04 → 2026.04
    python3 scripts/import_conference.py --years 2025     # one year
    python3 scripts/import_conference.py --years 2025 2026
    python3 scripts/import_conference.py --limit 3        # first 3 talks (test)
    python3 scripts/import_conference.py --dry-run
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
    parse_conference_toc,
    set_delay,
)

REPORT_TITLES = ("Sustaining of General Authorities", "Church Auditing Department Report")


def _talk_date(year: int, days, session: str) -> str:
    """ISO date for a talk from the conference day range + session weekday."""
    if not days:
        return f"{year}-{days['month'] if days else 1:02d}-01"
    day = days["first"] if session.lower().startswith("saturday") else days["second"]
    return f"{year:04d}-{days['month']:02d}-{day:02d}"


def _default_years():
    return list(range(2021, 2027))  # 2021..2026


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, nargs="*", default=None,
                    help="conference years to import (default: 2021..2026)")
    ap.add_argument("--limit", type=int, default=0, help="import only the first N talks (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="list planned talks, don't import")
    ap.add_argument("--delay", type=float, default=None, help="override inter-request delay (s)")
    ap.add_argument("--cache", default=str(ROOT / "data" / "raw" / "church_site"), help="raw HTML cache dir")
    args = ap.parse_args()

    if args.delay is not None:
        set_delay(args.delay)

    years = args.years or _default_years()
    months = [4, 10]

    if args.dry_run:
        for year in years:
            for month in months:
                print(f"  gc.{year}.{month:02d} (plan)")
        return

    init_db()
    conn = get_db()
    total = 0
    for year in years:
        for month in months:
            toc_url = f"{BASE}/study/general-conference/{year}/{month:02d}?lang=eng"
            print(f"\n=== {year}.{month:02d} — {toc_url}")
            try:
                toc_html = fetch(toc_url, cache_dir=args.cache)
            except Exception as e:
                print(f"  SKIP (fetch failed: {e})")
                continue
            parsed = parse_conference_toc(toc_html)
            talks = [t for s in parsed["sessions"] for t in s["talks"]]
            if args.limit:
                talks = talks[: args.limit]
            for t in talks:
                if any(r in t["title"] for r in REPORT_TITLES):
                    continue  # procedural reports, not talks
                url = f"{BASE}/study/general-conference/{year}/{month:02d}/{t['slug']}?lang=eng"
                try:
                    html = fetch(url, cache_dir=args.cache)
                except Exception as e:
                    print(f"  FAIL {t['slug']}: {e}")
                    continue
                body = extract_body(html)
                title = page_title(html) or t["title"]
                speaker = t["speaker"].replace("\xa0", " ").strip()
                ref_id = f"gc.{year}.{month:02d}.{t['slug']}"
                conn.execute(
                    """INSERT OR REPLACE INTO talks
                       (ref_id, year, month, session, speaker, title, date, text)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (ref_id, year, month, t["session"], speaker, title,
                     _talk_date(year, parsed["days"], t["session"]), body),
                )
                conn.commit()
                total += 1
                print(f"  {ref_id} [{t['session']}] {speaker} — {title[:45]} ({len(body)} chars)")

    print(f"\nDone. {total} talks in talks.")


if __name__ == "__main__":
    main()
