"""Weekly calibration health check.

Reports:
  - Type distribution (are any types stuck at "pattern"?)
  - Discovery method skew
  - Temporal staleness stats
  - Contradiction hot-spots
  - Calibration curve (tier distribution)
"""

import sqlite3
from pathlib import Path
from collections import Counter

DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"
REVALIDATION_THRESHOLD = 0.3


def audit():
    conn = sqlite3.connect(str(DB_PATH))
    
    print("=" * 60)
    print("  CALIBRATION AUDIT REPORT")
    print("=" * 60)
    
    # 1. Type distribution
    print("\n── Type Distribution (top 20) ──")
    rows = conn.execute(
        "SELECT type, COUNT(*) as c FROM connections WHERE deprecated=0 "
        "GROUP BY type ORDER BY c DESC LIMIT 20"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:30s} {r[1]:>8}")
    
    # 2. Quality tier distribution
    print("\n── Quality Tier Distribution ──")
    rows = conn.execute(
        "SELECT quality_level, COUNT(*) as c FROM connections WHERE deprecated=0 "
        "GROUP BY quality_level ORDER BY c DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:20s} {r[1]:>8}")
    
    # 3. Discovery method skew
    print("\n── Discovery Method Distribution ──")
    rows = conn.execute(
        "SELECT discovered_by, COUNT(*) as c FROM connections WHERE deprecated=0 "
        "GROUP BY discovered_by ORDER BY c DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r[0]:30s} {r[1]:>8}")
    
    # 4. Temporal staleness
    print("\n── Temporal Staleness (algorithmic pre-2024) ──")
    stale = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE deprecated=0 "
        "AND discovered_by IN ('algorithm','llm') AND created_at < '2024-01-01'"
    ).fetchone()[0]
    pre_2022 = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE deprecated=0 "
        "AND discovered_by IN ('algorithm','llm') AND created_at < '2022-01-01'"
    ).fetchone()[0]
    total_alg = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE deprecated=0 "
        "AND discovered_by IN ('algorithm','llm')"
    ).fetchone()[0]
    print(f"  Total algorithmic/LLM: {total_alg}")
    print(f"  Pre-2024 (aging/stale): {stale} ({stale/max(total_alg,1)*100:.1f}%)")
    print(f"  Pre-2022 (critical): {pre_2022} ({pre_2022/max(total_alg,1)*100:.1f}%)")
    
    # 5. Contradiction hot-spots
    print("\n── Contradiction Hot-Spots ──")
    try:
        unresolved = conn.execute(
            "SELECT COUNT(*) FROM disagreements WHERE resolution='unresolved'"
        ).fetchone()[0]
        print(f"  Unresolved contradictions: {unresolved}")
        if unresolved > 0:
            hot = conn.execute(
                "SELECT verse_pair, conflict_score FROM disagreements "
                "WHERE resolution='unresolved' ORDER BY conflict_score DESC LIMIT 10"
            ).fetchall()
            for h in hot:
                print(f"    {h[0]:30s} score={h[1]}")
    except Exception:
        print("  No disagreements table (run migrate_truth_alignment.py)")
    
    # 6. Connections needing revalidation
    print("\n── Revalidation Needed ──")
    needs_reval = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE deprecated=0 AND revalidation_due=1"
    ).fetchone()[0]
    print(f"  Flagged for revalidation: {needs_reval}")
    
    # 7. Overall stats
    print("\n── Summary Stats ──")
    total = conn.execute("SELECT COUNT(*) FROM connections WHERE deprecated=0").fetchone()[0]
    disputed = conn.execute(
        "SELECT COUNT(*) FROM connections WHERE quality_level='disputed'"
    ).fetchone()[0]
    print(f"  Total active connections: {total}")
    print(f"  Disputed: {disputed}")
    
    conn.close()
    print("\n" + "=" * 60)
    print("  AUDIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    audit()
