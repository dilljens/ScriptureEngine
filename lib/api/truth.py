"""
Truth Alignment Engine v2 — Multi-signal truth evaluation.

Evaluates scholarly claims against the scripture text using multiple signals:
  1. TEXT_MATCH: Does the text literally contain the claim's key terms?
  2. GRAPH_SUPPORT: What does the 1.36M connection graph show?
  3. CONTRADICTION_PENALTY: Does clear scripture contradict this?
  4. SCHOLAR_WEIGHT: Multiply by scholar credibility
  5. ATTESTATION: How many scholars/connections independently affirm this?

Evidence levels:
  L1_LITERAL      — The text explicitly says this
  L1_HISTORICAL   — The text narrates a historical event
  L2_CONTEXTUAL   — Implied by context, plausible pattern
  L3_INTERPRETIVE — A scholar's reading/interpretation
  L3_SPECULATIVE  — Reconstructed claim, no direct support
"""

import json
import re
from typing import Optional

from lib.controls.calibration import rate_connection_row
from lib.api.truth_scholars import get_scholar_weight
from lib.api.truth_contradictions import check_contradictions, find_supporting_connections

# ── Evidence Level Weights ──

LEVEL_WEIGHTS = {
    "L1_LITERAL":      {"base": 1.0, "text": 0.50, "graph": 0.30, "scholar": 0.20},
    "L1_HISTORICAL":   {"base": 0.9, "text": 0.40, "graph": 0.30, "scholar": 0.30},
    "L2_CONTEXTUAL":   {"base": 0.6, "text": 0.20, "graph": 0.40, "scholar": 0.40},
    "L3_INTERPRETIVE": {"base": 0.4, "text": 0.15, "graph": 0.25, "scholar": 0.60},
    "L3_SPECULATIVE":  {"base": 0.2, "text": 0.05, "graph": 0.10, "scholar": 0.85},
}

# ── Layer weights for graph evidence ──
LAYER_WEIGHTS = {
    "linguistic": 1.0, "textual": 0.95, "numerical": 0.85,
    "geographic": 0.85, "chronological": 0.85, "intertextual": 0.80,
    "structural": 0.70, "frequency": 0.65, "symbolic": 0.60,
    "sod": 0.50, "interpretive": 0.40,
}

# ── Key concept map for text matching ──
KEY_CONCEPTS = {
    'yahweh': ['lord', 'yhwh', 'god', 'almighty'],
    'angel': ['angel', 'messenger', 'malach'],
    'council': ['council', 'congregation', 'assembly', 'host'],
    'divine': ['divine', 'god', 'heavenly', 'holy'],
    'judge': ['judge', 'judgeth', 'judged', 'judging', 'judgment'],
    'stand': ['stand', 'standeth', 'stood', 'standing'],
    'create': ['create', 'created', 'createth', 'creator', 'making', 'made'],
    'temple': ['temple', 'sanctuary', 'tabernacle', 'house', 'dwelling'],
    'heaven': ['heaven', 'heavens', 'heavenly', 'sky', 'firmament'],
    'earth': ['earth', 'land', 'world', 'ground'],
    'king': ['king', 'kingdom', 'royal', 'reign', 'rule'],
    'priest': ['priest', 'priesthood', 'minister', 'serve'],
    'sacrifice': ['sacrifice', 'offering', 'altar', 'blood'],
    'covenant': ['covenant', 'promise', 'oath', 'testament'],
    'asherah': ['asherah', 'grove', 'pole', 'image'],
    'baal': ['baal', 'baalim'],
    'atonement': ['atonement', 'cover', 'kippur', 'propitiation'],
    'fall': ['fall', 'transgress', 'sin', 'disobey'],
    'redeem': ['redeem', 'redeemer', 'salvation', 'save', 'deliver'],
    'glory': ['glory', 'kavod', 'shekinah', 'presence'],
    'name': ['name', 'shem', 'memorial'],
    'wisdom': ['wisdom', 'sophia', 'understanding', 'knowledge'],
    'tree': ['tree', 'wood', 'cross', 'branch'],
    'veil': ['veil', 'curtain', 'poreketh', 'katapetasma'],
    'throne': ['throne', 'seat', 'merkabah', 'chariot'],
    'anointed': ['anointed', 'messiah', 'christ', 'messianic'],
}


def extract_verse_refs(text: str) -> list[str]:
    """Extract verse references from text (book.ch.verse format)."""
    pattern = r'([a-z0-9_]+)\.(\d+)\.(\d+)'
    matches = re.findall(pattern, text.lower())
    refs = set()
    for book, ch, vs in matches:
        refs.add(f"{book}.{ch}.{vs}")
    return sorted(refs)


def _get_verse_text(conn, ref: str) -> Optional[str]:
    """Get the English text for a verse reference."""
    row = conn.execute(
        "SELECT text_english FROM verses WHERE id = ?", (ref,)
    ).fetchone()
    return row[0] if row else None


def _text_match_score(claim: str, verse_text: str) -> float:
    """
    Score how well a verse text supports a claim.
    Uses KEY_CONCEPTS mapping to handle synonyms and archaic English.
    Returns 0.0-1.0.
    """
    claim_lower = claim.lower()
    verse_lower = verse_text.lower()
    
    matches = 0
    total_concepts = 0
    
    for concept, keywords in KEY_CONCEPTS.items():
        in_claim = any(kw in claim_lower for kw in keywords)
        in_verse = any(kw in verse_lower for kw in keywords)
        if in_claim:
            total_concepts += 1
            if in_verse:
                matches += 1
    
    if total_concepts == 0:
        return 0.0
    
    return matches / total_concepts


def _graph_evidence_score(conn, verse_refs: list[str]) -> dict:
    """Score the connection graph evidence for given verses."""
    if not verse_refs:
        return {"score": 0.0, "total": 0, "by_layer": {}, "strong": []}
    
    placeholders = ",".join("?" for _ in verse_refs)
    rows = conn.execute(f"""
        SELECT *
        FROM connections
        WHERE (source_verse IN ({placeholders}) OR target_verse IN ({placeholders}))
        LIMIT 1000
    """, verse_refs + verse_refs).fetchall()
    
    if not rows:
        return {"score": 0.0, "total": 0, "by_layer": {}, "strong": []}
    
    total = len(rows)
    by_layer = {}
    weighted_score = 0.0
    total_weight = 0.0
    strong_connections = []
    
    for r in rows:
        d = dict(r)
        layer = d["layer"]
        by_layer[layer] = by_layer.get(layer, 0) + 1
        
        weight = LAYER_WEIGHTS.get(layer, 0.5)
        conf = d.get("confidence", 0.5)
        
        weighted_score += weight * conf
        total_weight += weight
        
        if conf > 0.7 and weight > 0.6:
            strong_connections.append({
                "type": d["type"],
                "layer": layer,
                "target": d["target_verse"],
                "confidence": conf,
            })
    
    avg_score = weighted_score / max(total_weight, 1)
    # Normalize to 0-1
    normalized = min(1.0, avg_score)
    
    return {
        "score": round(normalized, 3),
        "total": total,
        "by_layer": by_layer,
        "strong": strong_connections[:5],
    }


def evaluate_claim(conn, claim: str, verse_refs: list[str],
                   scholar: str = "", level: str = "L2_CONTEXTUAL") -> dict:
    """
    Multi-signal truth evaluation.
    
    Combines: text match, graph evidence, contradiction check, scholar weight.
    """
    # 1. Get evidence level weights
    level_info = LEVEL_WEIGHTS.get(level, LEVEL_WEIGHTS["L2_CONTEXTUAL"])
    base_weight = level_info["base"]
    
    # 2. Text match signal
    verse_texts = {}
    text_scores = []
    for ref in verse_refs:
        text = _get_verse_text(conn, ref)
        if text:
            verse_texts[ref] = text
            score = _text_match_score(claim, text)
            text_scores.append(score)
    
    avg_text_match = sum(text_scores) / max(len(text_scores), 1) if text_scores else 0.0
    text_signal = avg_text_match * level_info["text"]
    
    # 3. Graph support signal
    graph = _graph_evidence_score(conn, verse_refs)
    graph_signal = graph["score"] * level_info["graph"]
    
    # 4. Scholar credibility signal
    scholar_weight = get_scholar_weight(scholar) if scholar else 0.5
    scholar_signal = scholar_weight * level_info["scholar"]
    
    # 5. Contradiction check
    contradiction = check_contradictions(claim, verse_refs, conn)
    contradiction_penalty = contradiction["contradiction_score"] * 0.5  # Max 50% penalty
    
    # 6. Combined score
    raw_score = text_signal + graph_signal + scholar_signal
    # Apply base weight and contradiction penalty
    final_score = raw_score * base_weight * (1.0 - contradiction_penalty)
    final_score = min(1.0, max(0.0, final_score))
    
    # 7. Determine alignment
    if final_score >= 0.6 and avg_text_match > 0.3:
        alignment = "supported"
        confidence = final_score
    elif final_score >= 0.4:
        alignment = "plausible"
        confidence = final_score
    elif final_score >= 0.2:
        alignment = "uncertain"
        confidence = final_score
    elif contradiction["has_contradiction"]:
        alignment = "contradicted"
        confidence = contradiction["contradiction_score"]
    else:
        alignment = "uncertain"
        confidence = final_score
    
    return {
        "claim": claim,
        "scholar": scholar,
        "level": level,
        "alignment": alignment,
        "confidence": round(min(0.95, confidence), 3),
        "signals": {
            "text_match": round(avg_text_match, 3),
            "text_signal": round(text_signal, 3),
            "graph_signal": round(graph_signal, 3),
            "graph_total": graph["total"],
            "scholar_signal": round(scholar_signal, 3),
            "scholar_weight": round(scholar_weight, 3),
            "contradiction_penalty": round(contradiction_penalty, 3),
        },
        "contradiction": contradiction,
        "graph_evidence": {
            "total": graph["total"],
            "by_layer": graph["by_layer"],
            "strong_connections": graph["strong"],
        },
        "verse_texts": verse_texts,
        "verse_refs": verse_refs,
    }


def batch_evaluate(conn, claims: list[dict]) -> list[dict]:
    """Evaluate multiple claims at once. Each claim needs: claim, verses, scholar, level."""
    results = []
    for c in claims:
        result = evaluate_claim(
            conn, c["claim"], c.get("verses", []),
            scholar=c.get("scholar", ""),
            level=c.get("level", "L2_CONTEXTUAL"),
        )
        result["topic"] = c.get("topic", "")
        results.append(result)
    return results


def generate_audit_report(results: list[dict]) -> dict:
    """Generate a summary audit report from batch evaluation results."""
    total = len(results)
    by_alignment = {}
    by_level = {}
    by_topic = {}
    
    for r in results:
        a = r["alignment"]
        by_alignment[a] = by_alignment.get(a, 0) + 1
        l = r["level"]
        by_level[l] = by_level.get(l, 0) + 1
        t = r.get("topic", "?")
        if t not in by_topic:
            by_topic[t] = {"total": 0, "supported": 0, "plausible": 0, "uncertain": 0, "contradicted": 0}
        by_topic[t]["total"] += 1
        by_topic[t][a] = by_topic[t].get(a, 0) + 1
    
    return {
        "total_claims": total,
        "by_alignment": by_alignment,
        "by_evidence_level": by_level,
        "by_topic": by_topic,
        "results": results,
    }


# ── Legacy wrapper for backward compat ──

def check_claim(conn, claim: str, verse_refs: list[str],
                claim_type: Optional[str] = None) -> dict:
    """Legacy wrapper — evaluates at default L2 level."""
    return evaluate_claim(conn, claim, verse_refs, level="L2_CONTEXTUAL")


def batch_check(conn, claims: list[dict]) -> list[dict]:
    """Legacy wrapper for batch_check."""
    return batch_evaluate(conn, claims)


def generate_report(results: list[dict]) -> dict:
    """Legacy wrapper for generate_report."""
    return generate_audit_report(results)


def classify_claim(text: str) -> str:
    """Simple claim type classifier (kept for backward compat)."""
    text_lower = text.lower()
    if any(w in text_lower for w in ['hebrew', 'greek', 'word means', 'literally', 'the term']):
        return "linguistic"
    if any(w in text_lower for w in ['josiah', 'century', 'archaeolog', 'inscription', 'excavated']):
        return "historical"
    if any(w in text_lower for w in ['trinity', 'binitarian', 'christology', 'divine', 'incarnation']):
        return "theological"
    if any(w in text_lower for w in ['manuscript', 'variant', 'septuagint', 'lxx', 'dss']):
        return "textual"
    return "interpretive"
