"""
Contradiction detection for truth claims.
Checks if a truth claim contradicts clearly established scripture.

Uses the existing contradiction matrix from lib.controls.contradiction.
"""

import json
import sqlite3
from typing import Optional

from lib.controls.calibration import rate_connection_row
from lib.controls.contradiction import CONTRADICTION_MATRIX


def get_opposite_connections(conn, verse_refs: list[str], claim_text: str) -> list[dict]:
    """
    Find connections that potentially CONTRADICT the claim.
    Looks for connections where the target verse says the opposite
    of what the claim asserts.
    """
    if not verse_refs:
        return []
    
    placeholders = ",".join("?" for _ in verse_refs)
    
    # Find connections involving these verses that might contradict
    # Focus on: textual variants, interpretive disagreements, dispute_status
    rows = conn.execute(f"""
        SELECT c.*, v.text_english as source_text
        FROM connections c
        JOIN verses v ON v.id = c.source_verse
        WHERE (c.source_verse IN ({placeholders}) OR c.target_verse IN ({placeholders}))
        AND (c.dispute_status IS NOT NULL AND c.dispute_status != '')
        ORDER BY c.confidence DESC
        LIMIT 200
    """, verse_refs + verse_refs).fetchall()
    
    result = []
    for r in rows:
        d = dict(r)
        # Check if this connection is disputed
        if d.get("dispute_status") in ("disputed", "contradicted"):
            result.append(d)
    
    return result


def check_contradictions(claim: str, verse_refs: list[str],
                          conn) -> dict:
    """
    Evaluate whether a truth claim contradicts clear scripture.
    
    Returns:
    {
        "has_contradiction": bool,
        "contradiction_score": float (0.0 = no contradiction, 1.0 = clear contradiction),
        "contradicting_verses": [...],
        "contradicting_traditions": [...],
    }
    """
    contradiction_score = 0.0
    contradicting_verses = []
    contradicting_traditions = []
    
    # 1. Check disputed connections
    disputed = get_opposite_connections(conn, verse_refs, claim)
    for d in disputed:
        if d.get("dispute_status") == "contradicted":
            contradiction_score += d.get("confidence", 0.5) * 0.5
            contradicting_verses.append({
                "verse": d.get("target_verse", ""),
                "reason": d.get("type", "disputed"),
                "confidence": d.get("confidence", 0.5),
            })
    
    # 2. Check for explicit contradictions in the connection matrix
    # If the claim's verses have connections tagged as contradictory types
    claim_lower = claim.lower()
    
    # Check if the claim itself uses "restore" language while verses describe "destruction"
    negation_pairs = [
        ("restore", "destroy"),
        ("restore", "remove"),
        ("build", "tear down"),
        ("create", "destroy"),
        ("add", "remove"),
        ("support", "contradict"),
        ("affirm", "deny"),
    ]
    
    for pos, neg in negation_pairs:
        if pos in claim_lower:
            # Check if verses contain the negative concept
            for ref in verse_refs:
                row = conn.execute(
                    "SELECT text_english FROM verses WHERE id = ?", (ref,)
                ).fetchone()
                if row and neg in row[0].lower():
                    contradiction_score += 0.3
                    contradicting_verses.append({
                        "verse": ref,
                        "reason": f"Claim uses '{pos}' but verse describes '{neg}'",
                        "confidence": 0.3,
                    })
    
    # 3. Check interpretive disagreements
    for ref in verse_refs:
        rows = conn.execute("""
            SELECT tradition_a, tradition_b, description, resolved_by
            FROM interpretive_disagreements
            WHERE verse_id = ?
        """, (ref,)).fetchall()
        for r in rows:
            contradicting_traditions.append({
                "verse": ref,
                "tradition_a": r["tradition_a"],
                "tradition_b": r["tradition_b"],
                "description": r["description"],
            })
            contradiction_score += 0.1
    
    # Clamp score
    contradiction_score = min(1.0, contradiction_score)
    
    return {
        "has_contradiction": contradiction_score > 0.3,
        "contradiction_score": round(contradiction_score, 3),
        "contradicting_verses": contradicting_verses[:5],
        "contradicting_traditions": contradicting_traditions[:3],
    }


def find_supporting_connections(conn, verse_refs: list[str]) -> dict:
    """
    Find the strongest connections that SUPPORT a claim.
    Used to weigh evidence for L2 and L3 claims.
    """
    if not verse_refs:
        return {"total": 0, "strong": [], "by_layer": {}}
    
    placeholders = ",".join("?" for _ in verse_refs)
    rows = conn.execute(f"""
        SELECT c.*, v.text_english as source_text
        FROM connections c
        JOIN verses v ON v.id = c.source_verse
        WHERE (c.source_verse IN ({placeholders}) OR c.target_verse IN ({placeholders}))
        AND c.confidence > 0.5
        ORDER BY c.confidence DESC
        LIMIT 500
    """, verse_refs + verse_refs).fetchall()
    
    strong = []
    by_layer = {}
    
    for r in rows:
        d = dict(r)
        layer = d["layer"]
        by_layer[layer] = by_layer.get(layer, 0) + 1
        
        if d["confidence"] > 0.7:
            strong.append({
                "type": d["type"],
                "layer": d["layer"],
                "target": d["target_verse"],
                "confidence": d["confidence"],
                "source": d["source_verse"],
            })
    
    return {
        "total": len(rows),
        "strong": strong[:10],
        "by_layer": by_layer,
    }
