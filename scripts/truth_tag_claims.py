#!/usr/bin/env python3
"""
Auto-tag all scholarly claims with evidence levels (L1_LITERAL, L2_CONTEXTUAL,
L3_INTERPRETIVE, L3_SPECULATIVE).

Usage:
  python3 scripts/truth_tag_claims.py          # Print tags only
  python3 scripts/truth_tag_claims.py --update # Update truth_data.py with tags
  python3 scripts/truth_tag_claims.py --stats  # Show statistics
"""

import ast
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

# ── Evidence Level Constants ──

LEVELS = {
    "L1_LITERAL": {
        "description": "The text explicitly says this — highest confidence",
        "weight": 1.0,
        "text_match_weight": 0.5,
        "graph_weight": 0.3,
    },
    "L1_HISTORICAL": {
        "description": "The text narrates a historical event — verifiable from the text",
        "weight": 0.9,
        "text_match_weight": 0.4,
        "graph_weight": 0.3,
    },
    "L2_CONTEXTUAL": {
        "description": "Implied by surrounding text or context — plausible but not explicit",
        "weight": 0.6,
        "text_match_weight": 0.2,
        "graph_weight": 0.4,
    },
    "L3_INTERPRETIVE": {
        "description": "A scholar's reading or interpretation — confidence depends on scholar credibility",
        "weight": 0.4,
        "text_match_weight": 0.15,
        "graph_weight": 0.25,
    },
    "L3_SPECULATIVE": {
        "description": "Reconstructed claim with no direct textual support — lowest confidence",
        "weight": 0.2,
        "text_match_weight": 0.05,
        "graph_weight": 0.1,
    },
}


def classify_claim_level(claim_text: str, verses: list[str], scholar: str) -> str:
    """Auto-classify a claim's evidence level based on content analysis."""
    text = claim_text.lower()
    verses_str = " ".join(verses).lower()
    scholar_lower = scholar.lower()

    # ── L1_LITERAL indicators: claim says what the text literally says ──
    literal_indicators = [
        "means", "refers to", "is called", "is named", "the word",
        "literally", "in the hebrew", "in the greek", "reads",
        "says that", "depicts", "describes", "narrates",
        "the term", "the phrase", "translated as",
    ]
    
    # ── L1_HISTORICAL indicators: claim about historical events in the text ──
    historical_indicators = [
        "removed", "destroyed", "centralized", "suppressed",
        "produced", "reform", "event", "century", "bce",
        "archaeolog", "inscription", "excavated",
    ]

    # ── L3_SPECULATIVE indicators: reconstructed/lost ceremonies ──
    speculative_indicators = [
        "would have been", "was understood as", "was originally",
        "reconstruct", "lost ceremony", "no surviving",
        "speculative", "it is possible", "may have",
        "is speculative", "no direct evidence",
        "worship of the shalems", "shalems",
        "visionary men", "visionary men lineage",
        "dramatic representation", "initiates played",
    ]

    # ── L3_INTERPRETIVE indicators: scholar's reading ──
    interpretive_indicators = [
        "should be seen as", "is best understood",
        "reflects", "suggests that", "points to",
        "indicates that", "implies that", "argues that",
        "scholar", "interpretation", "reading",
        "paradigm", "framework", "hermeneutic",
    ]

    # Check speculative first (strongest signal)
    spec_count = sum(1 for ind in speculative_indicators if ind in text)
    if spec_count >= 2 or any(ind in text for ind in ["worship of the shalems", "shalems"]):
        return "L3_SPECULATIVE"

    # Check for explicit textual claims
    lit_count = sum(1 for ind in literal_indicators if ind in text)
    hist_count = sum(1 for ind in historical_indicators if ind in text)

    # Strong literal indicators
    if lit_count >= 2 and hist_count == 0:
        # Check if the text actually has the words being discussed
        key_terms = re.findall(r"'([^']+)'", claim_text)
        if key_terms:
            # If the claim quotes specific terms from the verses, it's L1
            verses_text = " ".join(verses)
            match_count = sum(1 for term in key_terms if term.lower() in verses_text.lower())
            if match_count >= len(key_terms) * 0.5:
                return "L1_LITERAL"
    
    # Historical claims with specific narrative backing
    if hist_count >= 2:
        return "L1_HISTORICAL"
    
    # Mixed: has some literal + some interpretive elements
    interp_count = sum(1 for ind in interpretive_indicators if ind in text)
    if interp_count >= 2 or (lit_count >= 1 and interp_count >= 1):
        return "L3_INTERPRETIVE"
    
    # Check for narrative patterns that are clearly L2
    if len(verses) >= 3 and "pattern" in text:
        return "L2_CONTEXTUAL"
    
    # Default: check scholar and specific claim characteristics
    if any(name in scholar_lower for name in ["butler", "independent", "self-published"]):
        return "L3_INTERPRETIVE"
    
    # Remaining ambiguous claims
    if len(verses) <= 2 and len(text) > 100:
        return "L3_INTERPRETIVE"
    
    return "L2_CONTEXTUAL"


def tag_claims(claims_dict: dict) -> dict:
    """Tag all claims with evidence levels. Returns updated dict."""
    updated = {}
    stats = {"L1_LITERAL": 0, "L1_HISTORICAL": 0, "L2_CONTEXTUAL": 0, 
             "L3_INTERPRETIVE": 0, "L3_SPECULATIVE": 0}
    
    for topic, claims in claims_dict.items():
        updated[topic] = []
        for claim in claims:
            level = classify_claim_level(
                claim["claim"], claim.get("verses", []), claim.get("scholar", "")
            )
            updated_claim = {**claim, "level": level}
            updated[topic].append(updated_claim)
            stats[level] = stats.get(level, 0) + 1
    
    return updated, stats


def print_stats(claims_dict: dict, stats: dict):
    """Print statistics about the tagged claims."""
    total = sum(stats.values())
    print(f"Total claims: {total}")
    print(f"\nBy evidence level:")
    for level, info in LEVELS.items():
        count = stats.get(level, 0)
        bar = "#" * int(count / max(total, 1) * 40) + "-" * (40 - int(count / max(total, 1) * 40))
        print(f"  {level:20s}: {count:3d} ({count/max(total,1)*100:4.0f}%) {bar}")
    
    print(f"\nBy topic:")
    for topic, claims in claims_dict.items():
        levels = [c.get("level", "UNKNOWN") for c in claims]
        counts_str = ", ".join(f"{l}={levels.count(l)}" for l in sorted(set(levels)))
        print(f"  {topic:30s}: {len(claims)} claims [{counts_str}]")


def update_data_file(claims_dict: dict):
    """Write the updated claims back to truth_data.py."""
    data_path = BASE_DIR / "lib" / "api" / "truth_data.py"
    
    # Build the Python code manually
    lines = ['"""\nBuilt-in scholarly claims for truth evaluation, organized by topic.\nEach topic contains claims from multiple scholars with verse references.\nEvidence levels: L1_LITERAL (text says it), L1_HISTORICAL (text narrates it),\nL2_CONTEXTUAL (implied), L3_INTERPRETIVE (scholar reads it), L3_SPECULATIVE (reconstructed).\n"""\n\n']
    lines.append("SCHOLARLY_CLAIMS = {\n")
    
    for topic, claims in claims_dict.items():
        lines.append(f'    "{topic}": [\n')
        for claim in claims:
            level = claim.get("level", "L2_CONTEXTUAL")
            lines.append('        {\n')
            lines.append(f'            "scholar": {repr(claim["scholar"])},\n')
            lines.append(f'            "claim": {repr(claim["claim"])},\n')
            lines.append(f'            "verses": {repr(claim["verses"])},\n')
            lines.append(f'            "level": "{level}",\n')
            lines.append(f'        }},\n')
        lines.append('    ],\n')
    
    lines.append('}\n')
    
    with open(data_path, "w") as f:
        f.writelines(lines)
    
    print(f"Updated {data_path}")


def main():
    # Import current claims
    sys.path.insert(0, str(BASE_DIR))
    from lib.api.truth_data import SCHOLARLY_CLAIMS
    
    updated, stats = tag_claims(SCHOLARLY_CLAIMS)
    
    if "--stats" in sys.argv:
        print_stats(updated, stats)
        return
    
    if "--update" in sys.argv:
        update_data_file(updated)
    
    print_stats(updated, stats)


if __name__ == "__main__":
    main()
