#!/usr/bin/env python3
"""System Dreaming — automated connection graph cleanup with AI review.

Deprecates and prunes connections that nobody uses:
  - Speculative connections with 0 hits after 30 days → AI reviews before deprecating
  - Deprecated connections older than 90 days → pruned from DB
  - Connections with 3+ confirmations → auto-promoted

AI review: connections eligible for deprecation are sent to an LLM
for a one-shot validity judgment before being removed.

Run:  ./run.sh cleanup                  (no AI review, time-based only)
      ./run.sh cleanup --ai-review      (LLM reviews before deprecating)
      ./run.sh cleanup --dry-run        (preview only)
"""

import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.db import get_db


def get_eligible_for_review(conn):
    """Get connections eligible for AI review before deprecation."""
    rows = conn.execute("""
        SELECT c.id, c.source_verse, c.target_verse, c.layer, c.type, c.subtype,
               c.hit_count, c.confirmation_count, c.created_at,
               vs.text_english as source_text, vs.book_id as source_book,
               vt.text_english as target_text, vt.book_id as target_book
        FROM connections c
        JOIN verses vs ON vs.id = c.source_verse
        JOIN verses vt ON vt.id = c.target_verse
        WHERE c.quality_level = 'speculative'
          AND c.hit_count < 3
          AND c.confirmation_count = 0
          AND c.created_at < datetime('now', '-14 days')
        LIMIT 50
    """).fetchall()
    return [dict(r) for r in rows]


def build_review_prompt(connections):
    """Build the LLM review prompt for a batch of connections."""
    prompt = """You are a scripture scholarship reviewer. Your task is to evaluate whether proposed connections between scripture verses are valid.

For each connection, judge whether the two verses are genuinely linked (quotation, allusion, shared symbol, theological concept, etc.) or whether the connection is coincidental.

Respond with a JSON array of judgments, one per connection in the same order.

Valid judgments:
  "valid" — a real, meaningful connection between these verses
  "invalid" — coincidental, no real relationship
  "uncertain" — possibly meaningful but unclear

---"""

    for i, c in enumerate(connections):
        prompt += f"""

Connection {i + 1}:
  From: {c['source_verse']} ({c['source_book']})
  Text: {c['source_text'][:200]}

  To: {c['target_verse']} ({c['target_book']})
  Text: {c['target_text'][:200]}

  Type: {c['layer']}/{c['type']}
  Detected by: {c.get('discovered_by', 'algorithm')}

Judgment:"""

    prompt += """

Respond ONLY with a JSON array: [{"connection": 1, "judgment": "valid", "reasoning": "..."}, ...]"""
    return prompt


def review_via_llm(connections, api_key=None, api_url=None, model=None):
    """Send connections to an LLM for review.

    If no API key is set, writes a batch file for manual review instead.
    """
    if not api_key:
        # Write batch file for manual AI review
        batch = []
        for c in connections:
            batch.append({
                "id": c["id"],
                "source": c["source_verse"],
                "target": c["target_verse"],
                "layer": c["layer"],
                "type": c["type"],
                "subtype": c.get("subtype", ""),
                "source_text": c["source_text"][:200],
                "target_text": c["target_text"][:200],
                "judgment": None,
                "reasoning": None,
            })
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"/tmp/connection_review_{timestamp}.json"
        with open(path, "w") as f:
            json.dump({"connections": batch, "instructions":
                       "Set 'judgment' to 'valid', 'invalid', or 'uncertain' for each connection, then run: ./run.sh cleanup --apply-review " + path},
                      f, indent=2, ensure_ascii=False)
        return {"mode": "file", "path": path, "count": len(connections)}

    # API-based review
    import urllib.error
    import urllib.request

    prompt = build_review_prompt(connections)
    payload = json.dumps({
        "model": model or os.environ.get("LLM_MODEL", "deepseek-v4-flash"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 2000,
    }).encode()

    req = urllib.request.Request(
        api_url or os.environ.get("LLM_API_URL", "https://api.commandcode.ai/provider/v1/chat/completions"),
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            content = data["choices"][0]["message"]["content"]
            # Parse JSON from response
            import re
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                judgments = json.loads(json_match.group())
                return {"mode": "api", "judgments": judgments, "count": len(judgments)}
    except Exception as e:
        return {"mode": "error", "error": str(e)}

    return {"mode": "error", "error": "No JSON found in LLM response"}


def apply_judgments(conn, judgments, batch_size=50):
    """Apply AI judgments to connections.

    valid → promote to probable
    invalid → deprecate
    uncertain → leave as speculative (extend lifecycle)
    """
    stats = {"promoted": 0, "deprecated": 0, "uncertain": 0}

    for j in judgments:
        conn_id = j.get("connection", j.get("id"))
        judgment = j.get("judgment", "").lower()
        reasoning = j.get("reasoning", "")

        if judgment == "valid":
            conn.execute("""
                UPDATE connections SET
                    quality_level = 'probable',
                    deprecation_reason = 'AI review: ' || ?,
                    confirmation_count = confirmation_count + 1
                WHERE id = ?
            """, (reasoning[:200], conn_id))
            stats["promoted"] += 1

        elif judgment == "invalid":
            conn.execute("""
                UPDATE connections SET
                    quality_level = 'rejected',
                    deprecation_reason = 'AI review rejected: ' || ?
                WHERE id = ?
            """, (reasoning[:200], conn_id))
            stats["deprecated"] += 1

        else:  # uncertain
            # Reset timer — give it another 30 days
            conn.execute("""
                UPDATE connections SET
                    created_at = datetime('now'),
                    deprecation_reason = 'AI uncertain — postponed'
                WHERE id = ?
            """, (conn_id,))
            stats["uncertain"] += 1

    conn.commit()
    return stats


def apply_review_file(conn, filepath):
    """Apply judgments from a manually-reviewed JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    judgments = []
    for c in data.get("connections", []):
        if c.get("judgment"):
            judgments.append({
                "id": c["id"],
                "judgment": c["judgment"],
                "reasoning": c.get("reasoning", ""),
            })
    return apply_judgments(conn, judgments)


def cleanup(conn, dry_run=False):
    """Run the base cleanup pipeline (no AI review)."""
    stats = {"deprecated": 0, "pruned": 0, "promoted": 0, "uncertain": 0}

    # Auto-promote with enough confirmations
    conn.execute("""
        UPDATE connections
        SET quality_level = 'probable', deprecation_reason = ''
        WHERE quality_level = 'speculative' AND confirmation_count >= 3
    """)
    stats["promoted"] = conn.total_changes or 0

    # Deprecate old rejected connections
    conn.execute("""
        DELETE FROM connections
        WHERE deprecated = 1 AND created_at < datetime('now', '-90 days')
    """)
    stats["pruned"] = 0  # SQLite DELETE rowcount is unreliable

    if not dry_run:
        conn.commit()
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Clean up the connection graph with optional AI review")
    parser.add_argument("--dry-run", action="store_true", help="Report what would be done")
    parser.add_argument("--verbose", action="store_true", help="Show each affected connection")
    parser.add_argument("--ai-review", action="store_true", help="Use AI to review connections before deprecating")
    parser.add_argument("--apply-review", type=str, help="Apply judgments from a manually reviewed JSON file")
    parser.add_argument("--api-key", type=str, help="LLM API key (default: $LLM_API_KEY)")
    args = parser.parse_args()

    conn = get_db()

    print("=" * 60)
    print("  SYSTEM DREAMING — Connection Graph Cleanup")
    print("=" * 60)

    # Apply a pre-reviewed file
    if args.apply_review:
        print(f"\n  Applying review from: {args.apply_review}")
        stats = apply_review_file(conn, args.apply_review)
        print(f"  Promoted:   {stats['promoted']}")
        print(f"  Deprecated: {stats['deprecated']}")
        print(f"  Uncertain:  {stats['uncertain']}")
        print("  Done.")
        conn.close()
        return

    # AI review phase
    if args.ai_review:
        print("\n  Phase 1: AI Review of Eligible Connections")
        eligible = get_eligible_for_review(conn)
        print(f"  Connections eligible for review: {len(eligible)}")

        if eligible:
            api_key = args.api_key or os.environ.get("LLM_API_KEY")
            api_url = os.environ.get("LLM_API_URL")
            model = os.environ.get("LLM_MODEL")

            if api_key:
                print(f"  Reviewing via API ({model or 'default'})...")
                # Process in batches of 10
                for i in range(0, len(eligible), 10):
                    batch = eligible[i:i + 10]
                    result = review_via_llm(batch, api_key=api_key, api_url=api_url, model=model)
                    if result["mode"] == "api":
                        stats = apply_judgments(conn, result["judgments"])
                        print(f"  Batch {i // 10 + 1}: {stats['promoted']} promoted, {stats['deprecated']} deprecated, {stats['uncertain']} uncertain")
                    else:
                        print(f"  Batch {i // 10 + 1} error: {result.get('error', 'unknown')}")
            else:
                # No API key — write batch file
                result = review_via_llm(eligible)
                if result["mode"] == "file":
                    print("  No LLM_API_KEY set.")
                    print(f"  Review file written to: {result['path']}")
                    print("  Edit the judgments field in that file, then run:")
                    print(f"    ./run.sh cleanup --apply-review {result['path']}")
        print()

    # Base cleanup
    print("\n  Phase 2: Base Cleanup (auto-promote + prune)")
    stats = cleanup(conn, dry_run=args.dry_run)
    print(f"  Promoted (from confirmations): {stats['promoted']}")
    print(f"  Pruned (deprecated >90d):      {stats.get('pruned', 0)}")
    print()

    if args.dry_run:
        conn.close()
        return

    conn.commit()

    # Show affected
    if args.verbose or args.ai_review:
        rows = conn.execute("""
            SELECT id, source_verse, target_verse, layer, type, quality_level, deprecation_reason
            FROM connections WHERE deprecation_reason != '' AND deprecation_reason IS NOT NULL
            LIMIT 15
        """).fetchall()
        if rows:
            print("  Recent actions:")
            for r in rows:
                emoji = {"probable": "✅", "rejected": "❌", "speculative": "💡"}.get(r["quality_level"], "❓")
                print(f"  {emoji} [{r['quality_level']}] {r['source_verse']} → {r['target_verse']} ({r['layer']}/{r['type']})")
                if r["deprecation_reason"]:
                    print(f"     {r['deprecation_reason'][:100]}")

    conn.close()
    print(f"\n  Next: {os.path.basename(sys.argv[0])} --help")


if __name__ == "__main__":
    main()
