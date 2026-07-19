"""
Truth Alignment Engine — evaluate scholarly claims against the scripture text.

Compares what scholars claim about scripture against:
  1. The actual text (linguistic layer — highest confidence)
  2. The connection graph (what other verses say about the same topic)
  3. Textual evidence (manuscript variants, original language meaning)
  4. Intertextual evidence (how the verse is used elsewhere in canon)

Returns: supports | partially_supports | neutral | contradicts | insufficient_evidence
"""

import json
import re
from typing import Optional

from lib.controls.calibration import rate_connection_row

# ── Layers ordered by confidence weight ──
# Linguistic evidence is highest (what the text actually says).
# Sod/interpretive is lowest (later interpretive traditions).
LAYER_WEIGHTS = {
    "linguistic": 1.0,
    "textual": 0.95,
    "numerical": 0.85,
    "geographic": 0.85,
    "chronological": 0.85,
    "intertextual": 0.80,
    "structural": 0.70,
    "frequency": 0.65,
    "symbolic": 0.60,
    "sod": 0.50,
    "interpretive": 0.40,
}

# ── Claim type classification ──
CLAIM_TYPES = {
    "linguistic": "What the original language actually says — highest authority",
    "historical": "Historical claim about events, people, or practices",
    "theological": "Theological interpretation or doctrine",
    "textual": "Claim about manuscript evidence or textual variants",
    "interpretive": "What a tradition or scholar says a passage means",
}


def extract_verse_refs(text: str) -> list[str]:
    """Extract verse references from text (book.ch.verse format)."""
    pattern = r'([a-z0-9_]+)\.(\d+)\.(\d+)'
    matches = re.findall(pattern, text.lower())
    refs = set()
    for book, ch, vs in matches:
        refs.add(f"{book}.{ch}.{vs}")
    return sorted(refs)


def classify_claim(claim_text: str) -> str:
    """Classify what type of claim this is."""
    claim_lower = claim_text.lower()
    
    linguistic_indicators = [
        'hebrew', 'greek', 'word means', 'literally', 'the term',
        'in the original', 'the verb', 'the noun', 'etymology',
    ]
    historical_indicators = [
        'josiah', 'reform', 'deuteronomic', 'assyrian', 'babylonian',
        'century', 'bce', 'ce', 'archaeolog', 'inscription', 'excavated',
        'ancient near eastern', 'ugarit', 'egyptian', 'mesopotamian',
    ]
    theological_indicators = [
        'trinity', 'binitarian', 'christology', 'divine', 'incarnation',
        'salvation', 'atonement', 'covenant', 'god is', 'jesus is',
        'holy spirit', 'resurrection', 'eschaton', 'glorif',
    ]
    textual_indicators = [
        'manuscript', 'variant', 'septuagint', 'masoretic', 'lxx', 'dss',
        'dead sea scroll', 'scribe', 'copyist', 'original text',
        'textual criticism', 'oldest', 'codex',
    ]

    for indicator in historical_indicators:
        if indicator in claim_lower:
            return "historical"
    for indicator in linguistic_indicators:
        if indicator in claim_lower:
            return "linguistic"
    for indicator in textual_indicators:
        if indicator in claim_lower:
            return "textual"
    for indicator in theological_indicators:
        if indicator in claim_lower:
            return "theological"
    return "interpretive"


def _get_connections_for_verses(conn, verse_refs: list[str], layer: Optional[str] = None) -> list:
    """Get all connections involving any of the given verses."""
    if not verse_refs:
        return []
    
    placeholders = ",".join("?" for _ in verse_refs)
    sql = f"""
        SELECT c.*, v.text_english as source_text
        FROM connections c
        JOIN verses v ON v.id = c.source_verse
        WHERE (c.source_verse IN ({placeholders}) OR c.target_verse IN ({placeholders}))
    """
    params = verse_refs + verse_refs
    
    if layer:
        sql += " AND c.layer = ?"
        params.append(layer)
    
    sql += " LIMIT 500"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def _rate_connections(rows: list) -> dict:
    """Rate a batch of connections and return quality summary."""
    if not rows:
        return {"total": 0, "by_quality": {}, "by_layer": {}, "strong_connections": []}
    
    by_quality = {"verified": 0, "strong": 0, "probable": 0, "suggested": 0, "pattern": 0}
    by_layer = {}
    strong = []
    
    for r in rows:
        meta_str = r.get("metadata") or "{}"
        if isinstance(meta_str, str):
            try:
                meta = json.loads(meta_str)
            except json.JSONDecodeError:
                meta = {}
        else:
            meta = meta_str
        quality = rate_connection_row({
            "discovered_by": r.get("discovered_by", "algorithm"),
            "type": r.get("type", ""),
            "confidence": r.get("confidence", 0.5),
            "confirmation_count": r.get("confirmation_count", 0),
            "metadata": meta,
        })
        stars = quality.get("stars", 1)
        level = {5: "verified", 4: "strong", 3: "probable", 2: "suggested", 1: "pattern"}.get(stars, "suggested")
        by_quality[level] = by_quality.get(level, 0) + 1
        by_layer[r["layer"]] = by_layer.get(r["layer"], 0) + 1
        
        if stars >= 4:
            strong.append({
                "type": r["type"],
                "layer": r["layer"],
                "target": r["target_verse"],
                "confidence": r["confidence"],
                "quality": level,
            })
    
    return {
        "total": len(rows),
        "by_quality": by_quality,
        "by_layer": by_layer,
        "strong_connections": strong[:10],
    }


def _get_verse_text(conn, ref: str) -> Optional[str]:
    """Get the English text for a verse reference."""
    row = conn.execute(
        "SELECT text_english FROM verses WHERE id = ?", (ref,)
    ).fetchone()
    return row[0] if row else None


def _text_supports_claim(claim: str, verse_text: str) -> float:
    """
    Quick heuristic: does the verse text support the claim?
    Handles archaic English (judgeth/judging, standeth/stands) and
    proper names (YHWH/LORD/GOD).
    """
    claim_lower = claim.lower()
    verse_lower = verse_text.lower()
    
    # Key concept map for archaic/modern equivalents
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
    }
    
    # Score based on how many key concepts appear in BOTH claim and verse
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


def check_claim(conn, claim: str, verse_refs: list[str], 
                claim_type: Optional[str] = None) -> dict:
    """
    Evaluate a scholarly claim against the scripture text.
    
    The evaluation uses three signals:
      1. Direct text match — do the verses actually say what the claim asserts?
      2. Connection graph — what does the intertextual/web of verses show?
      3. Layer quality — which layers support the claim (linguistic > sod)?
    """
    if not claim_type:
        claim_type = classify_claim(claim)
    
    # Get the texts of referenced verses
    verse_texts = {}
    text_support_scores = []
    for ref in verse_refs:
        text = _get_verse_text(conn, ref)
        if text:
            verse_texts[ref] = text
            score = _text_supports_claim(claim, text)
            text_support_scores.append(score)
    
    # Signal 1: Direct text match (highest weight)
    avg_text_support = sum(text_support_scores) / max(len(text_support_scores), 1) if text_support_scores else 0.0
    has_direct_text_match = avg_text_support > 0.1  # Some keyword overlap
    
    # Get all connections involving these verses
    connections = _get_connections_for_verses(conn, verse_refs)
    conn_summary = _rate_connections(connections)
    
    # Signal 2: Connection graph by layer
    layer_evidence = {}
    for layer in LAYER_WEIGHTS:
        layer_conns = [c for c in connections if c["layer"] == layer]
        if layer_conns:
            layer_evidence[layer] = {
                "count": len(layer_conns),
                "quality": _rate_connections(layer_conns),
                "weight": LAYER_WEIGHTS[layer],
            }
    
    # Calculate weighted graph score
    total_weight = 0
    graph_score = 0
    
    for layer, evidence in layer_evidence.items():
        w = evidence["weight"]
        total_weight += w
        q = evidence["quality"]
        # Count all connections, weighted by quality
        verified_count = q["by_quality"].get("verified", 0)
        strong_count = q["by_quality"].get("strong", 0)
        probable_count = q["by_quality"].get("probable", 0)
        total = max(q["total"], 1)
        layer_score = (verified_count * 1.0 + strong_count * 0.8 + probable_count * 0.5) / total
        graph_score += w * layer_score
    
    overall_graph_score = graph_score / max(total_weight, 1) if total_weight > 0 else 0.0
    
    # Signal 3: Combine text match + graph evidence
    # Text match gets 60% weight, graph gets 40%
    combined_score = avg_text_support * 0.6 + overall_graph_score * 0.4
    
    # Classify alignment
    has_linguistic = layer_evidence.get("linguistic", {}).get("count", 0) > 0
    has_strong_graph = conn_summary["by_quality"].get("verified", 0) > 0 or conn_summary["by_quality"].get("strong", 0) > 0
    has_connections = conn_summary["total"] > 0
    textual_match_found = has_direct_text_match or has_linguistic
    
    if textual_match_found and combined_score >= 0.3:
        alignment = "supports"
        confidence = min(0.95, 0.4 + combined_score * 0.6)
    elif has_strong_graph and combined_score >= 0.15:
        alignment = "partially_supports"
        confidence = min(0.8, 0.3 + combined_score * 0.5)
    elif has_connections:
        alignment = "neutral"
        confidence = 0.5
    else:
        alignment = "insufficient_evidence"
        confidence = 0.0
    
    # Top evidence
    top_connections = []
    for c in connections[:5]:
        top_connections.append({
            "type": c["type"],
            "layer": c["layer"],
            "source": c["source_verse"],
            "target": c["target_verse"],
            "confidence": c["confidence"],
        })
    
    return {
        "claim": claim,
        "claim_type": claim_type,
        "verse_refs": verse_refs,
        "verse_texts": verse_texts,
        "alignment": alignment,
        "confidence": round(confidence, 3),
        "text_match_score": round(avg_text_support, 3),
        "graph_score": round(overall_graph_score, 3),
        "combined_score": round(combined_score, 3),
        "total_connections": conn_summary["total"],
        "connections_by_quality": conn_summary["by_quality"],
        "connections_by_layer": conn_summary["by_layer"],
        "strong_connections": conn_summary["strong_connections"],
        "top_connections": top_connections,
        "layer_evidence": {
            layer: {
                "count": e["count"],
                "weight": e["weight"],
            }
            for layer, e in layer_evidence.items()
        },
    }


def batch_check(conn, claims: list[dict]) -> list[dict]:
    """Check multiple claims at once. Each claim: {claim, verse_refs, claim_type?}"""
    results = []
    for item in claims:
        result = check_claim(
            conn,
            item["claim"],
            item.get("verse_refs", []),
            item.get("claim_type"),
        )
        results.append(result)
    return results


def generate_report(results: list[dict]) -> dict:
    """Generate a summary report from batch claim results."""
    total = len(results)
    by_alignment = {}
    by_type = {}
    
    for r in results:
        a = r["alignment"]
        by_alignment[a] = by_alignment.get(a, 0) + 1
        t = r["claim_type"]
        by_type[t] = by_type.get(t, 0) + 1
    
    strong_evidence = []
    for r in results:
        for c in r.get("strong_connections", []):
            strong_evidence.append({
                "claim": r["claim"][:100],
                "type": c["type"],
                "layer": c["layer"],
                "target": c["target"],
                "quality": c["quality"],
            })
    
    return {
        "total_claims": total,
        "by_alignment": by_alignment,
        "by_claim_type": by_type,
        "alignment_rate": round(by_alignment.get("supports", 0) / max(total, 1), 3),
        "contradiction_rate": round(by_alignment.get("contradicts", 0) / max(total, 1), 3),
        "strong_evidence": strong_evidence[:10],
        "results": results,
    }
