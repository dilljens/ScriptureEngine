#!/usr/bin/env python3
"""
Full truth audit — evaluates all claims with multi-signal scoring.

Usage:
  python3 scripts/truth_audit.py                     # Human-readable report
  python3 scripts/truth_audit.py --format json       # Machine-readable JSON
  python3 scripts/truth_audit.py --topic bom_temple  # Single topic
  python3 scripts/truth_audit.py --format readable   # Default
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.api.truth import evaluate_claim, batch_evaluate, generate_audit_report
from lib.api.truth_data import SCHOLARLY_CLAIMS
from lib.db import get_db


ALIGN_ICONS = {
    "supported": "✅",
    "plausible": "🔶",
    "uncertain": "⚪",
    "contradicted": "❌",
}

LEVEL_LABELS = {
    "L1_LITERAL": "Literal — text explicitly says this",
    "L1_HISTORICAL": "Historical — text narrates this event",
    "L2_CONTEXTUAL": "Contextual — implied by context",
    "L3_INTERPRETIVE": "Interpretive — scholar's reading",
    "L3_SPECULATIVE": "Speculative — reconstructed claim",
}


def print_readable_report(report: dict):
    """Print a human-readable audit report."""
    total = report["total_claims"]
    print("=" * 72)
    print(f"TRUTH AUDIT — {total} CLAIMS")
    print("=" * 72)
    print()
    
    # Summary
    print("--- SUMMARY ---")
    for align, count in sorted(report["by_alignment"].items()):
        icon = ALIGN_ICONS.get(align, "?")
        pct = count / total * 100
        bar = "#" * int(pct / 2.5) + "-" * (40 - int(pct / 2.5))
        print(f"  {icon} {align:15s}: {count:3d} ({pct:4.0f}%) {bar}")
    print()
    
    # By evidence level
    print("--- BY EVIDENCE LEVEL ---")
    for level, count in sorted(report["by_evidence_level"].items()):
        label = LEVEL_LABELS.get(level, level)
        bar = "#" * int(count / total * 80)
        print(f"  {level:20s}: {count:3d} {bar}")
    print()
    
    # By topic
    print("--- BY TOPIC ---")
    for topic, info in sorted(report["by_topic"].items()):
        pct = info.get("supported", 0) / max(info["total"], 1) * 100
        bar = "#" * int(pct / 2.5) + "-" * (40 - int(pct / 2.5))
        s = info.get("supported", 0)
        p = info.get("plausible", 0)
        u = info.get("uncertain", 0)
        c = info.get("contradicted", 0)
        print(f"  {topic:32s}: [{bar}] {s}✅/{p}🔶/{u}⚪/{c}❌ ({pct:.0f}% supported)")
    print()
    
    # Detailed claims
    print("--- DETAILED RESULTS ---")
    current_topic = ""
    for r in report["results"]:
        topic = r.get("topic", "")
        if topic != current_topic:
            print(f"\n▸ {topic.upper()}")
            current_topic = topic
        
        icon = ALIGN_ICONS.get(r["alignment"], "?")
        sigs = r["signals"]
        contra = r["contradiction"]
        
        print(f"  {icon} [{r['alignment']}] ({r['confidence']:.0%}) [{r['level']}] {r.get('scholar','?')}")
        print(f"     \"{r['claim'][:100]}...\"")
        print(f"     Text:{sigs['text_match']:.2f} Graph:{sigs['graph_total']} Scholar:{sigs['scholar_weight']:.2f} Contra:{'⚠' if contra['has_contradiction'] else '✓'}")
        print()


def main():
    args = sys.argv[1:]
    fmt = "readable"
    topic_filter = None
    
    for i, arg in enumerate(args):
        if arg == "--format" and i + 1 < len(args):
            fmt = args[i + 1]
        if arg == "--topic" and i + 1 < len(args):
            topic_filter = args[i + 1]
    
    conn = get_db()
    all_results = []
    
    topics = [topic_filter] if topic_filter else SCHOLARLY_CLAIMS.keys()
    
    for topic in topics:
        if topic not in SCHOLARLY_CLAIMS:
            print(f"Unknown topic: {topic}")
            continue
        
        claims = SCHOLARLY_CLAIMS[topic]
        for c in claims:
            result = evaluate_claim(
                conn, c["claim"], c.get("verses", []),
                scholar=c.get("scholar", ""),
                level=c.get("level", "L2_CONTEXTUAL"),
            )
            result["topic"] = topic
            all_results.append(result)
    
    report = generate_audit_report(all_results)
    
    if fmt == "json":
        print(json.dumps(report, indent=2, default=str))
    else:
        print_readable_report(report)
    
    conn.close()


if __name__ == "__main__":
    main()
