"""
Graph-enhanced search — retrieves verses via knowledge graph traversal.

At query time:
  1. Extracts entity candidates from the query (from entity_links DB — not hardcoded)
  2. Finds matching entities in entity_links via trigram FTS5
  3. Disambiguates ambiguous names (John, James, etc.) using context
  4. Finds verses directly mentioning those entities (verse_entities)
  5. Explores up to 2-hop neighborhood via connections (verse-to-verse)
  6. Scores verses by graph proximity to query entities
  7. Returns scored verse IDs for 3-way RRF fusion with vector + BM25

Each result carries an explanation string showing the traversal path.
"""

import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Module-level constants ───────────────────────────────────────────

MAX_HOPS = 2
MAX_QUERY_ENTITIES = 10
TOP_K_GRAPH = 50

# ── Entity cache (loaded from DB on first use) ───────────────────────

_ENTITY_CACHE = None
_CACHE_LOADED = False


def _load_entity_cache(conn):
    """Load all entity names from entity_links into memory cache.
    
    Caches by entity_type for efficient lookup. Falls back gracefully
    if entity_links table doesn't exist or is empty.
    """
    global _ENTITY_CACHE, _CACHE_LOADED
    if _CACHE_LOADED:
        return _ENTITY_CACHE

    cache = {
        "all_names": set(),
        "person": set(),
        "place": set(), 
        "concept": set(),
        "deity": set(),
        "nation": set(),
        "object": set(),
        "event": set(),
        "group": set(),
        "all_entities": [],
    }

    try:
        rows = conn.execute(
            "SELECT entity_id, english_name, hebrew_name, entity_type FROM entity_links"
        ).fetchall()

        for r in rows:
            name = (r["english_name"] or "").lower().strip()
            heb = (r["hebrew_name"] or "").lower().strip()
            etype = (r["entity_type"] or "unknown").lower()

            for n in (name, heb):
                if n and len(n) >= 2:
                    cache["all_names"].add(n)
                    if etype in cache:
                        cache[etype].add(n)

            cache["all_entities"].append({
                "entity_id": r["entity_id"],
                "name": r["english_name"] or r["hebrew_name"] or "",
                "entity_type": etype,
            })

        if cache["all_names"]:
            logger.debug("Graph search: loaded %d entity names from DB", len(cache["all_names"]))
        else:
            logger.warning("Graph search: entity_links table is empty")
            cache = None

    except Exception as e:
        logger.warning("Graph search: failed to load entity_links: %s", e)
        cache = None

    _ENTITY_CACHE = cache
    _CACHE_LOADED = True
    return cache


# ── Main entry point ─────────────────────────────────────────────────

def graph_search(conn, query: str, top_k: int = TOP_K_GRAPH) -> list[dict]:
    """Search the knowledge graph for verses relevant to a query.
    
    Args:
        conn: SQLite connection.
        query: The search query string.
        top_k: Max results to return.
    
    Returns:
        List of {"verse": str, "graph_score": float, "explanation": str, 
                 "entity_match": bool, "hop_depth": int}.
        Empty list if no graph entities match.
    """
    # Step 1: Extract entity candidates from the query (from DB cache)
    query_entities = _extract_entities_from_query(conn, query)
    if not query_entities:
        return []

    # Step 2: Find matching entities in entity_links
    matched_entities = _find_matching_entities(conn, query_entities)
    if not matched_entities:
        return []

    # Step 3: Disambiguate ambiguous names (John, James, etc.)
    disambiguated = _disambiguate_entities(conn, matched_entities, query)
    if not disambiguated:
        return []

    # Step 4: Find verses mentioning matched entities
    entity_verses = _find_entity_verses(conn, disambiguated, top_k)
    if not entity_verses:
        return []

    # Step 5: Score verses by graph proximity (up to 2 hops)
    scored = _score_by_proximity(conn, entity_verses, disambiguated, top_k)

    return scored


# ── Entity extraction from query ─────────────────────────────────────

def _extract_entities_from_query(conn, query: str) -> list[dict]:
    """Extract entity candidates from a search query using DB-loaded names.
    
    Checks against all entity names in entity_links (not hardcoded frozensets).
    Falls back to heuristic capitalized-word detection for unknown names.
    """
    cache = _load_entity_cache(conn)
    entities = []
    seen = set()
    q = query.strip()
    q_lower = q.lower()

    # Hebrew/Greek check
    if re.search(r'[\u0590-\u05FF]', q):
        entities.append({"name": q, "entity_type": "hebrew_word", "is_heuristic": True})
        return entities
    if re.search(r'[\u0370-\u03FF\u1F00-\u1FFF]', q):
        entities.append({"name": q, "entity_type": "greek_word", "is_heuristic": True})
        return entities

    # Verse reference check
    if re.match(r'^[a-z]{2,6}\.\d+\.\d+$', q, re.IGNORECASE):
        entities.append({"name": q, "entity_type": "verse_ref", "is_heuristic": True})
        return entities

    if not cache or not cache.get("all_names"):
        return _heuristic_extract(q)

    # Build a set of lowercase entity names that are substrings for easy matching
    # e.g., "james" should match "James (son of Zebedee)" 
    def _name_matches(word):
        """Check if word matches any entity name (exact or starts-with)."""
        if word in cache["all_names"]:
            return True
        # Check if word is a prefix or core part of any entity name
        for cached_name in cache["all_names"]:
            if cached_name.startswith(word + " ") or cached_name.startswith(word + "("):
                return True
        return False

    # Try multi-word query against DB names first
    if _name_matches(q_lower):
        etype = _detect_type(cache, q_lower) if q_lower in cache["all_names"] else "unknown"
        entities.append({"name": q, "entity_type": etype, "is_heuristic": False})

    # Single words
    words = q_lower.split()
    for w in words[:MAX_QUERY_ENTITIES]:
        w_clean = w.strip(".,;:!?'\"()-")
        if not w_clean or len(w_clean) < 3:
            continue
        if w_clean in seen:
            continue
        seen.add(w_clean)

        if _name_matches(w_clean):
            etype = _detect_type(cache, w_clean) if w_clean in cache["all_names"] else "unknown"
            entities.append({"name": w_clean, "entity_type": etype, "is_heuristic": False})
        elif w_clean[0].isupper() or (w_clean[0].isalpha() and w_clean[0] == w_clean[0].upper()):
            # Capitalized proper noun heuristic — always add, let DB matching sort it out
            entities.append({"name": w_clean, "entity_type": "unknown", "is_heuristic": True})

    return entities


def _detect_type(cache, name: str) -> str:
    """Detect entity type from cache by checking type-specific sets."""
    if name in cache.get("person", set()):
        return "person"
    if name in cache.get("place", set()):
        return "place"
    if name in cache.get("concept", set()):
        return "concept"
    if name in cache.get("deity", set()):
        return "deity"
    if name in cache.get("nation", set()):
        return "nation"
    if name in cache.get("event", set()):
        return "event"
    if name in cache.get("object", set()):
        return "object"
    if name in cache.get("group", set()):
        return "group"
    return "unknown"


def _heuristic_extract(q: str) -> list[dict]:
    """Fallback entity extraction without DB cache.
    
    Uses capitalized-word heuristic only. Only used when entity_links
    table is unavailable or empty.
    """
    entities = []
    seen = set()
    words = q.strip().split()
    for w in words[:MAX_QUERY_ENTITIES]:
        w_clean = w.strip(".,;:!?'\"()-")
        if not w_clean or len(w_clean) < 3:
            continue
        wl = w_clean.lower()
        if wl in seen:
            continue
        seen.add(wl)
        if w_clean[0].isupper() and wl not in ("The", "A", "An", "This", "That", "It", "I", "You"):
            entities.append({"name": w_clean, "entity_type": "unknown", "is_heuristic": True})
    return entities


# ── Entity disambiguation ─────────────────────────────────────────────

def _disambiguate_entities(conn, matched_entities: list[dict], query: str) -> list[dict]:
    """Resolve ambiguous entity names using query context.
    
    When multiple entities share a name (e.g., 3 "John"s, 2 "James"s),
    checks which book/chapter each appears in against the query context
    to pick the most likely match.
    
    If no context determines a winner, returns all matches (conservative).
    """
    # Group matches by base name
    by_name: dict[str, list[dict]] = defaultdict(list)
    for entity in matched_entities:
        key = (entity["name"] or "").lower().strip()
        by_name[key].append(entity)

    # Extract book keywords from query (gen, exod, matt, john, etc.)
    query_books = _extract_book_hints(query)

    result = []
    for name, candidates in by_name.items():
        if len(candidates) == 1:
            result.append(candidates[0])
            continue

        # Multiple candidates — disambiguate
        best = candidates[0]
        best_score = 0

        for candidate in candidates:
            score = _score_entity_context(conn, candidate, query_books)
            if score > best_score:
                best_score = score
                best = candidate

        # If no context favors any candidate, keep all (conservative)
        if best_score > 0:
            result.append(best)
            logger.debug("Graph search: disambiguated '%s' to %s (score=%d)", 
                        name, best["entity_id"], best_score)
        else:
            result.extend(candidates)  # Keep all — let fusion sort them

    return result


def _extract_book_hints(query: str) -> set[str]:
    """Extract book name hints from a query.
    
    Looks for: full book names (genesis), abbreviations (gen),
    testament references (old testament, nt), and author hints (pauline).
    """
    hints = set()
    q = query.lower().strip()

    # Known book abbreviations
    book_abbrev = {
        "gen", "exod", "lev", "num", "deut", "josh", "judg", "ruth",
        "1sam", "2sam", "1kgs", "2kgs", "1chr", "2chr", "ezra", "neh",
        "esth", "job", "psa", "prov", "eccl", "song", "isa", "jer",
        "lam", "ezek", "dan", "hos", "joel", "amos", "obad", "jonah",
        "mic", "nahum", "hab", "zeph", "hag", "zech", "mal",
        "matt", "mark", "luke", "john", "acts",
        "rom", "1cor", "2cor", "gal", "eph", "phil", "col",
        "1thess", "2thess", "1tim", "2tim", "titus", "phlm",
        "heb", "james", "1pet", "2pet", "1john", "2john", "3john", "jude",
        "rev",
    }

    # Check for book abbreviations in the query text
    words = q.split()
    for w in words:
        w_clean = w.strip(".,;:!?'\"()[]{}")
        if w_clean in book_abbrev:
            hints.add(w_clean)

    # Check for full book names
    book_names = {
        "genesis": "gen", "exodus": "exod", "leviticus": "lev",
        "numbers": "num", "deuteronomy": "deut", "joshua": "josh",
        "judges": "judg", "1 samuel": "1sam", "2 samuel": "2sam",
        "1 kings": "1kgs", "2 kings": "2kgs",
        "1 chronicles": "1chr", "2 chronicles": "2chr",
        "ezra": "ezra", "nehemiah": "neh", "esther": "esth",
        "job": "job", "psalms": "psa", "psalm": "psa",
        "proverbs": "prov", "ecclesiastes": "eccl",
        "song of solomon": "song",
        "isaiah": "isa", "jeremiah": "jer", "lamentations": "lam",
        "ezekiel": "ezek", "daniel": "dan", "hosea": "hos",
        "joel": "joel", "amos": "amos", "obadiah": "obad",
        "jonah": "jonah", "micah": "mic", "nahum": "nahum",
        "habakkuk": "hab", "zephaniah": "zeph", "haggai": "hag",
        "zechariah": "zech", "malachi": "mal",
        "matthew": "matt", "mark": "mark", "luke": "luke",
        "john": "john", "acts": "acts", "romans": "rom",
        "1 corinthians": "1cor", "2 corinthians": "2cor",
        "galatians": "gal", "ephesians": "eph", "philippians": "phil",
        "colossians": "col", "1 thessalonians": "1thess",
        "2 thessalonians": "2thess", "1 timothy": "1tim",
        "2 timothy": "2tim", "titus": "titus", "philemon": "phlm",
        "hebrews": "heb", "james": "james", "1 peter": "1pet",
        "2 peter": "2pet", "1 john": "1john", "2 john": "2john",
        "3 john": "3john", "jude": "jude", "revelation": "rev",
    }
    for full_name, abbrev in book_names.items():
        if full_name in q:
            hints.add(abbrev)

    return hints


def _score_entity_context(conn, entity: dict, query_books: set[str]) -> int:
    """Score how well an entity's context matches the query hints.
    
    Checks which books the entity appears in and compares against
    query_books. Each matching book = +1 point.
    """
    if not query_books:
        return 0

    try:
        rows = conn.execute("""
            SELECT DISTINCT SUBSTR(ve.verse_id, 1, INSTR(ve.verse_id, '.') - 1) AS book
            FROM verse_entities ve
            WHERE ve.entity_id = ?
            LIMIT 20
        """, (entity["entity_id"],)).fetchall()
    except Exception:
        return 0

    entity_books = {r["book"] for r in rows if r["book"]}
    score = sum(1 for b in query_books if b in entity_books)
    return score


# ── Entity matching ──────────────────────────────────────────────────

def _find_matching_entities(conn, query_entities: list[dict]) -> list[dict]:
    """Find matching entities in entity_links for query entities."""
    matched = []
    seen_ids = set()
    _searchable_types = {"person", "place", "concept", "deity", "nation", "object", "event", "group"}

    for qe in query_entities:
        name = qe["name"]
        etype = qe["entity_type"]
        filter_etype = etype if etype in _searchable_types else ""

        # Try exact match first
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

        # Fallback to substring match
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
                    "match_quality": 1.0,
                    "query_entity": qe,
                })

    logger.debug("Graph search: matched %d entities for query", len(matched))
    return matched


# ── Entity→verse lookup ──────────────────────────────────────────────

def _find_entity_verses(conn, matched_entities: list[dict], top_k: int) -> list[dict]:
    """Find verses mentioning matched entities via verse_entities."""
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

    scored = []
    for _vid, data in verse_matches.items():
        count_score = min(data["match_count"] / len(matched_entities), 1.0) * 0.6
        conf_score = min(data["total_confidence"] / data["match_count"], 1.0) * 0.4
        data["entity_score"] = count_score + conf_score
        scored.append(data)

    scored.sort(key=lambda x: -x["entity_score"])
    return scored[:top_k]


# ── Graph proximity scoring (with 2-hop) ─────────────────────────────

def _score_by_proximity(conn, entity_verses, matched_entities, top_k):
    """Score verses by graph proximity, including 2-hop neighbors."""
    matched_ids = {e["entity_id"] for e in matched_entities}
    matched_verse_ids = {v["verse"] for v in entity_verses}

    # Direct entity-matched verses
    direct_results = []
    for v in entity_verses:
        explanation_parts = []
        for eid in v.get("entity_ids", []):
            ename = eid
            for me in matched_entities:
                if me["entity_id"] == eid:
                    ename = me.get("name", eid)
                    break
            explanation_parts.append(f"entity '{ename}'")
        explanation = "Matched: " + " + ".join(explanation_parts) if explanation_parts else "Entity match"
        # Direct entity matches always outrank hop neighbors
        base_score = v["entity_score"]  # 0.0–1.0
        direct_score = 0.7 + (base_score * 0.3)  # Maps to 0.70–1.00 range
        direct_results.append({
            "verse": v["verse"],
            "graph_score": round(direct_score, 4),
            "explanation": explanation,
            "entity_match": True,
            "hop_depth": 0,
        })

    # 1-hop and 2-hop neighbors
    all_results = list(direct_results)
    if matched_verse_ids:
        all_results.extend(
            _find_hop_neighbors(conn, list(matched_verse_ids), matched_ids, matched_verse_ids, 
                              max_hops=MAX_HOPS, hop=1)
        )

    all_results.sort(key=lambda x: -x["graph_score"])
    return all_results[:top_k]


def _find_hop_neighbors(conn, source_verses, matched_entity_ids, exclude_ids, max_hops=2, hop=1):
    """Find N-hop neighbors via connections table.
    
    Recursively explores up to max_hops deep. Each hop scores lower
    than the previous (further from source entities).
    """
    if not source_verses or hop > max_hops:
        return []

    placeholders = ",".join("?" for _ in source_verses)
    results = []
    seen = set(exclude_ids)

    try:
        rows = conn.execute(f"""
            SELECT source_verse, target_verse, layer, type, strength, confidence
            FROM connections
            WHERE (source_verse IN ({placeholders})
               OR target_verse IN ({placeholders}))
              AND strength > 0.3
              AND confidence > 0.3
            ORDER BY strength DESC, confidence DESC
            LIMIT {200 // hop}
        """, (*source_verses, *source_verses)).fetchall()
    except Exception:
        return []

    # Collect neighbors for next hop
    next_sources = []

    for row in rows:
        if row["source_verse"] in exclude_ids:
            neighbor = row["target_verse"]
        else:
            neighbor = row["source_verse"]

        if neighbor in seen:
            continue
        seen.add(neighbor)
        next_sources.append(neighbor)

        strength = row["strength"] or 0.5
        confidence = row["confidence"] or 0.5
        layer = row["layer"]
        ctype = row["type"]

        layer_bonus = {"linguistic": 0.1, "intertextual": 0.1, "sod": 0.05,
                       "numerical": 0.02, "symbolic": 0.08}.get(layer, 0.0)

        # Score decays with hop depth
        hop_discount = 0.7 ** (hop - 1)
        score = (strength * 0.5 + confidence * 0.3 + layer_bonus * 0.1) * hop_discount

        hop_label = "Connected" if hop == 1 else "2-hop"
        results.append({
            "verse": neighbor,
            "graph_score": round(score, 4),
            "explanation": f"{hop_label}: {layer}/{ctype} (s={strength}, c={confidence})",
            "entity_match": False,
            "hop_depth": hop,
        })

    # Recursively find hop+1 neighbors
    if hop < max_hops and next_sources:
        child_results = _find_hop_neighbors(conn, next_sources, matched_entity_ids, 
                                          set(seen), max_hops=max_hops, hop=hop + 1)
        results.extend(child_results)

    return results
