#!/usr/bin/env python3
"""
Truth Check CLI — evaluate scholarly claims against the scripture text.

Usage:
  # Quick check a single claim
  python3 tools/truth_check.py '{"claim": "The Angel of YHWH is a created being", "verses": ["gen.16.7", "exo.3.2"]}'

  # Check multiple claims (batch)
  python3 tools/truth_check.py '{"action": "batch", "claims": [{"claim": "...", "verses": ["gen.1.1"]}, ...]}'

  # Check a scholar's claim about a topic
  python3 tools/truth_check.py '{"action": "topic", "topic": "temple_microcosm"}'

  # Ingest a scholarly text for analysis
  python3 tools/truth_check.py '{"action": "ingest", "title": "...", "author": "...", "text": "..."}'

  # List available scholarly claims in the database
  python3 tools/truth_check.py '{"action": "list"}'
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.api.truth import (
    evaluate_claim,
    batch_evaluate,
    classify_claim,
    extract_verse_refs,
    generate_audit_report,
)
from lib.api.truth_data import SCHOLARLY_CLAIMS
from lib.db import get_db


def print_result(result, indent=0):
    """Pretty-print a truth check result."""
    prefix = " " * indent
    align_icons = {
        "supports": "✅ SUPPORTS",
        "partially_supports": "🔶 PARTIALLY SUPPORTS",
        "neutral": "⚪ NEUTRAL",
        "contradicts": "❌ CONTRADICTS",
        "insufficient_evidence": "❓ INSUFFICIENT EVIDENCE",
    }
    
    icon = align_icons.get(result["alignment"], "❓ " + result["alignment"])
    print(f'{prefix}{icon} (confidence: {result["confidence"]:.1%})')
    print(f'{prefix}  Claim type: {result["claim_type"]}')
    print(f'{prefix}  Total connections checked: {result["total_connections"]}')
    
    if result["verse_texts"]:
        print(f'{prefix}  Key verse texts:')
        for ref, text in list(result["verse_texts"].items())[:3]:
            print(f'{prefix}    {ref}: {text[:80]}...')
    
    if result["strong_connections"]:
        print(f'{prefix}  Strongest evidence:')
        for c in result["strong_connections"][:3]:
            print(f'{prefix}    [{c["layer"]}] {c["type"]} → {c["target"]} (quality: {c["quality"]})')
    
    if result.get("top_connections"):
        print(f'{prefix}  Top connections in graph:')
        for c in result["top_connections"][:3]:
            print(f'{prefix}    {c["source"]} → {c["target"]} ({c["layer"]}.{c["type"]})')
    
    conn_by_layer = result.get("connections_by_layer", {})
    if conn_by_layer:
        print(f'{prefix}  By layer:')
        for layer, count in sorted(conn_by_layer.items(), key=lambda x: -x[1]):
            print(f'{prefix}    {layer}: {count}')


def handle_cli():
    args = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    action = args.get("action", "check")
    conn = get_db()
    
    if action == "list":
        print("Available topics with scholarly claims:")
        for topic, claims in SCHOLARLY_CLAIMS.items():
            scholars = set(c["scholar"] for c in claims)
            print(f'\n  {topic}:')
            print(f'    {len(claims)} claims from {", ".join(scholars)}')
        print(f'\nTotal: {sum(len(c) for c in SCHOLARLY_CLAIMS.values())} claims across {len(SCHOLARLY_CLAIMS)} topics')
    
    elif action == "topic":
        topic = args.get("topic", "")
        claims = SCHOLARLY_CLAIMS.get(topic, [])
        if not claims:
            print(f'Unknown topic: {topic}')
            print(f'Available: {", ".join(SCHOLARLY_CLAIMS.keys())}')
            return
        
        print(f'\n=== Checking topic: {topic} ({len(claims)} claims) ===\n')
        results = []
        for item in claims:
            print(f'Claim by {item["scholar"]} ({item.get("level", "L2")}):')
            print(f'  "{item["claim"]}"')
            result = evaluate_claim(conn, item["claim"], item.get("verses", []),
                                     scholar=item.get("scholar", ""),
                                     level=item.get("level", "L2_CONTEXTUAL"))
            results.append(result)
            print_result(result, indent=2)
            print()
        
        report = generate_audit_report(results)
        print(f'\n=== TOPIC SUMMARY ===')
        print(f'  Total claims: {report["total_claims"]}')
        print(f'  By alignment: {json.dumps(report["by_alignment"])}')
        print(f'  By evidence level: {json.dumps(report["by_evidence_level"])}')
        print(f'\nFull results:')
        print(json.dumps(report, indent=2, default=str))
    
    elif action == "batch":
        claims = args.get("claims", [])
        if not claims:
            # Run all topics
            all_claims = []
            for topic, topic_claims in SCHOLARLY_CLAIMS.items():
                for c in topic_claims:
                    all_claims.append({**c, "topic": topic})
            claims = all_claims
        
        results = batch_evaluate(conn, [
            {**c, "verses": c.get("verses", []),
             "scholar": c.get("scholar", ""),
             "level": c.get("level", "L2_CONTEXTUAL")}
            for c in claims
        ])
        
        report = generate_audit_report(results)
        print(json.dumps(report, indent=2, default=str))
    
    else:  # single claim check
        claim = args.get("claim", "")
        verses = args.get("verses", [])
        if not verses:
            verses = extract_verse_refs(claim)
            if not verses:
                print("No verses found. Provide 'verses' list or include refs in claim text.")
                return
        
        scholar = args.get("scholar", "")
        level = args.get("level", "L2_CONTEXTUAL")
        print(f'\nClaim: "{claim}"')
        print(f'Said by: {scholar if scholar else "(unknown)"}')
        print(f'Level: {level}')
        print(f'Verses: {", ".join(verses)}\n')
        
        result = evaluate_claim(conn, claim, verses, scholar=scholar, level=level)
        print_result(result)
        
        print(f'\n---\nJSON:')
        print(json.dumps(result, indent=2, default=str))
    
    conn.close()


if __name__ == "__main__":
    handle_cli()
