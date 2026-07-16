"""
Graph-enhanced search — retrieves verses via knowledge graph traversal.

At query time:
  1. Extracts entity candidates from the query (sub-ms regex)
  2. Finds matching entities in entity_links via trigram FTS5
  3. Finds verses directly mentioning those entities (verse_entities)
  4. Explores k-hop neighborhood via connections (verse-to-verse)
  5. Scores verses by graph proximity to query entities
  6. Returns scored verse IDs for 3-way RRF fusion with vector + BM25

Each result carries an explanation string showing the traversal path
— a differentiator from black-box vector search.

Pattern from unicity-ai's graph_search.py, adapted for scriptureengine's
schema (entity_links + verse_entities + connections).
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── Module-level constants ───────────────────────────────────────────

# Max graph traversal depth in hops
MAX_HOPS = 2
# How many entities to extract from query
MAX_QUERY_ENTITIES = 10
# Top-K verses to return from graph signal
TOP_K_GRAPH = 50

# Known biblical entities for query-time extraction
# (extended list possible at index-time from entity_links)
KNOWN_PEOPLE = frozenset({
    "abraham", "isaac", "jacob", "moses", "david", "solomon",
    "isaiah", "jeremiah", "ezekiel", "daniel", "jonah", "amos",
    "paul", "peter", "john", "jesus", "christ", "mary",
    "noah", "adam", "eve", "abram", "sarah", "rebecca", "rachel",
    "joseph", "samuel", "saul", "jonathan", "elijah", "elisha",
    "ruth", "esther", "nehemiah", "ezra", "joshua", "gideon",
    "samson", "herod", "pilate", "michael", "gabriel", "lucifer",
    "satan", "cain", "abel", "melchizedek", "job", "james",
})
KNOWN_PLACES = frozenset({
    "jerusalem", "bethlehem", "nazareth", "galilee", "judah",
    "egypt", "babylon", "nineveh", "sodom", "gomorrah",
    "canaan", "israel", "zion", "mount sinai", "mount zion",
    "golgotha", "calvary", "bethany", "cana", "capernaum",
    "jericho", "jordan", "red sea", "dead sea",
    "antioch", "corinth", "ephesus", "philippi", "thessalonica",
    "rome", "damascus", "samaria",
})
KNOWN_CONCEPTS = frozenset({
    "covenant", "atonement", "redemption", "salvation",
    "sanctification", "justification", "propitiation",
    "reconciliation", "adoption", "glorification",
    "repentance", "faith", "grace", "mercy", "love",
    "wisdom", "glory", "holiness", "righteousness",
    "temple", "tabernacle", "sacrifice", "offering",
    "kingdom", "resurrection", "ascension", "incarnation",
    "creation", "fall", "flood", "exodus", "exile",
    "restoration", "millennium", "judgment",
    "messiah", "prophet", "priest", "king",
})


def graph_search(conn, query: str, top_k: int = TOP_K_GRAPH) -> list[dict]:
    """Search the knowledge graph for verses relevant to a query.

    Args:
        conn: SQLite connection (from get_db or get_db_vec).
        query: The search query string.
        top_k: Max results to return.

    Returns:
        List of {"verse": str, "graph_score": float, "explanation": str}.
        Empty list if no graph entities match.
    """
    # Step 1: Extract entity candidates from the query
    query_entities = _extract_entities_from_query(query)
    if not query_entities:
        return []

    # Step 2: Find matching entities in entity_links
    matched_entities = _find_matching_entities(conn, query_entities)
    if not matched_entities:
        return []

    # Step 3: Find verses mentioning matched entities
    entity_verses = _find_entity_verses(conn, matched_entities, top_k)
    if not entity_verses:
        return []

    # Step 4: Score verses by graph proximity
    scored = _score_by_proximity(
        conn, entity_verses, matched_entities, top_k
    )

    return scored


def _extract_entities_from_query(query: str) -> list[dict]:
    """Lightweight entity extraction from a search query.

    Uses regex patterns for:
      - People names (capitalized words, known biblical names)
      - Places (known biblical place names)
      - Hebrew words (contains Hebrew Unicode)
      - Greek words (contains Greek Unicode)
      - Multi-word quoted phrases

    Returns list of {"name": str, "entity_type": str, "is_heuristic": bool}.
    """
    entities = []
    seen = set()
    q = query.strip()

    # Check for Hebrew word
    if re.search(r'[\u0590-\u05FF]', q):
        entities.append({"name": q, "entity_type": "hebrew_word", "is_heuristic": True})
        return entities

    # Check for Greek word
    if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', q):
        entities.append({"name": q, "entity_type": "greek_word", "is_heuristic": True})
        return entities

    # Check for verse reference
    if re.match(r'^[a-z]{2,6}\.\d+\.\d+$', q, re.IGNORECASE):
        entities.append({"name": q, "entity_type": "verse_ref", "is_heuristic": True})
        return entities

    # Check known people, places, concepts (single words and multi-word)
    q_lower = q.lower().strip()
    words = q_lower.split()

    # Multi-word: check the whole query
    if q_lower in KNOWN_PEOPLE:
        entities.append({"name": q, "entity_type": "person", "is_heuristic": False})
    elif q_lower in KNOWN_PLACES:
        entities.append({"name": q, "entity_type": "place", "is_heuristic": False})
    elif q_lower in KNOWN_CONCEPTS:
        entities.append({"name": q, "entity_type": "concept", "is_heuristic": False})

    # Single words
    for w in words[:MAX_QUERY_ENTITIES]:
        w_clean = w.strip(".,;:!?'\"")
        if not w_clean or len(w_clean) < 2:
            continue
        wl = w_clean.lower()
        if wl in seen:
            continue
        seen.add(wl)

        if wl in KNOWN_PEOPLE:
            entities.append({"name": w_clean, "entity_type": "person", "is_heuristic": False})
        elif wl in KNOWN_PLACES:
            entities.append({"name": w_clean, "entity_type": "place", "is_heuristic": False})
        elif wl in KNOWN_CONCEPTS:
            entities.append({"name": w_clean, "entity_type": "concept", "is_heuristic": False})
        # Capitalized proper noun heuristic
        elif w_clean[0].isupper() and wl not in ("The", "A", "An", "This", "That", "It", "I"):
            entities.append({"name": w_clean, "entity_type": "unknown", "is_heuristic": True})

    return entities


def _find_matching_entities(conn, query_entities: list[dict]) -> list[dict]:
    """Find matching entities in entity_links for query entities.

    Searches by english_name (case-insensitive LIKE), then hebrew_name.
    Returns matched entities with their IDs and match quality.
    """
    matched = []
    seen_ids = set()

    # Entity types that should match against entity_links.entity_type
    _searchable_types = {"person", "place", "concept", "divine_name", "deity", "nation", "object"}

    for qe in query_entities:
        name = qe["name"]
        etype = qe["entity_type"]
        filter_etype = etype if etype in _searchable_types else ""

        # Try exact match on english_name first
        try:
            rows = conn.execute(
                """SELECT entity_id, english_name, hebrew_name, entity_type
                   FROM entity_links
                   WHERE (LOWER(english_name) = LOWER(?) OR LOWER(hebrew_name) = LOWER(?))
                     AND (? = '' OR entity_type = ?)""",
                (name, name, filter_etype, etype),
            ).fetchall()
        except Exception:
            rows = []

        # Fall back to substring match
        if not rows:
            try:
                rows = conn.execute(
                    """SELECT entity_id, english_name, hebrew_name, entity_type
                       FROM entity_links
                       WHERE (english_name LIKE ? OR hebrew_name LIKE ?)
                         AND (? = '' OR entity_type = ?)
                       LIMIT 5""",
                    (f"%{name}%", f"%{name}%", filter_etype, etype),
                ).fetchall()
            except Exception:
                continue

        for row in rows:
            eid = row["entity_id"]
            if eid not in seen_ids:
                seen_ids.add(eid)
                matched.append({
                    "entity_id": eid,
                    "name": row["english_name"] or row["hebrew_name"] or name,
                    "entity_type": row["entity_type"] or etype,
                    "match_quality": 1.0,  # exact match via known entity
                    "query_entity": qe,
                })

    logger.debug("Graph search: matched %d entities for query", len(matched))
    return matched


def _find_entity_verses(
    conn, matched_entities: list[dict], top_k: int
) -> list[dict]:
    """Find verses that mention matched entities.

    Uses verse_entities table (57K entries linking entities to verses).
    Groups by verse, scoring by number of matched entities per verse.
    """
    if not matched_entities:
        return []

    entity_ids = [e["entity_id"] for e in matched_entities]
    placeholders = ",".join("?" for _ in entity_ids)

    try:
        rows = conn.execute(f"""
            SELECT ve.verse_id, ve.entity_id, ve.confidence
            FROM verse_entities ve
            WHERE ve.entity_id IN ({placeholders})
            ORDER BY ve.confidence DESC
            LIMIT ?
        """, (*entity_ids, top_k * 3)).fetchall()
    except Exception:
        return []

    # Group by verse, count entity matches
    verse_matches: dict[str, dict] = {}
    for row in rows:
        vid = row["verse_id"]
        if vid not in verse_matches:
            verse_matches[vid] = {
                "verse": vid,
                "entity_ids": [],
                "total_confidence": 0.0,
                "match_count": 0,
            }
        verse_matches[vid]["entity_ids"].append(row["entity_id"])
        verse_matches[vid]["total_confidence"] += row["confidence"] or 0.5
        verse_matches[vid]["match_count"] += 1

    # Score: more entity matches + higher confidence = better
    scored = []
    for _vid, data in verse_matches.items():
        count_score = min(data["match_count"] / len(matched_entities), 1.0) * 0.6
        conf_score = min(data["total_confidence"] / data["match_count"], 1.0) * 0.4
        data["entity_score"] = count_score + conf_score
        scored.append(data)

    scored.sort(key=lambda x: -x["entity_score"])
    return scored[:top_k]


def _score_by_proximity(
    conn, entity_verses: list[dict], matched_entities: list[dict], top_k: int
) -> list[dict]:
    """Score verses by graph proximity, including connected verses.

    For each entity-matched verse, also fetches directly connected verses
    via the connections table (1-hop). Connected verses inherit score
    discounted by connection strength.
    """
    matched_ids = {e["entity_id"] for e in matched_entities}
    matched_verse_ids = {v["verse"] for v in entity_verses}

    # Direct entity-matched verses
    direct_results = []
    for v in entity_verses:
        explanation_parts = []
        for eid in v.get("entity_ids", []):
            # Find the entity name
            ename = eid
            for me in matched_entities:
                if me["entity_id"] == eid:
                    ename = me.get("name", eid)
                    break
            explanation_parts.append(f"entity '{ename}'")
        if explanation_parts:
            explanation = "Matched: " + " + ".join(explanation_parts)
        else:
            explanation = "Entity match"
        direct_results.append({
            "verse": v["verse"],
            "graph_score": round(v["entity_score"] * 0.9, 4),  # direct match = high score
            "explanation": explanation,
            "entity_match": True,
            "hop_depth": 0,
        })

    # 1-hop neighbors: find connections from entity-matched verses
    if matched_verse_ids:
        vid_list = list(matched_verse_ids)
        hop_results = _find_hop_neighbors(conn, vid_list, matched_ids, matched_verse_ids)

        # Merge direct + hop results
        all_results = direct_results + hop_results
    else:
        all_results = direct_results

    # Sort by graph_score descending
    all_results.sort(key=lambda x: -x["graph_score"])
    return all_results[:top_k]


def _find_hop_neighbors(
    conn, source_verses: list[str], matched_entity_ids: set,
    exclude_verse_ids: set,
) -> list[dict]:
    """Find 1-hop neighbors of source verses via connections table.

    Scores by connection strength × confidence, with entity bonus
    for neighbors that also mention query entities.
    """
    if not source_verses:
        return []

    placeholders = ",".join("?" for _ in source_verses)
    results = []
    seen = set()

    try:
        # Get all connections FROM or TO source verses
        rows = conn.execute(f"""
            SELECT source_verse, target_verse, layer, type, strength, confidence
            FROM connections
            WHERE (source_verse IN ({placeholders})
               OR target_verse IN ({placeholders}))
              AND strength > 0.3
              AND confidence > 0.3
            ORDER BY strength DESC, confidence DESC
            LIMIT 100
        """, (*source_verses, *source_verses)).fetchall()
    except Exception:
        return []

    for row in rows:
        # Determine the neighbor verse (the one NOT in our source set)
        if row["source_verse"] in exclude_verse_ids:
            neighbor = row["target_verse"]
        else:
            neighbor = row["source_verse"]

        if neighbor in exclude_verse_ids or neighbor in seen:
            continue
        seen.add(neighbor)

        strength = row["strength"] or 0.5
        confidence = row["confidence"] or 0.5
        layer = row["layer"]
        ctype = row["type"]

        # Check if this neighbor also mentions matched entities
        # (entity bonus — stronger connection, deferred for perf:
        # would need another verse_entities query per neighbor)
        layer_bonus = {
            "linguistic": 0.1,
            "intertextual": 0.1,
            "sod": 0.05,
            "numerical": 0.02,
            "symbolic": 0.08,
        }.get(layer, 0.0)

        score = (strength * 0.5 + confidence * 0.3 + layer_bonus * 0.1) * 0.7

        results.append({
            "verse": neighbor,
            "graph_score": round(score, 4),
            "explanation": f"Connected: {layer}/{ctype} (s={strength}, c={confidence})",
            "entity_match": False,
            "hop_depth": 1,
        })

    return results
