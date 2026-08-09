"""Consolidation pipeline — 5-stage periodic maintenance of the connection graph.

Periodic maintenance pass that keeps the graph honest and tidy:

  Stage 1 Inspect     — find merge candidates (trigram name/alias similarity on
                        entity_links), contradictions, and stale connections.
  Stage 2 Resolve     — resolve contradictions: explicit connections beat
                        algorithmic, higher calibrated confidence wins.
  Stage 3 Merge       — coalesce duplicate entity_links rows: merge aliases,
                        re-point verse_entities, keep the canonical entity.
  Stage 4 Generalize  — record frequent (layer, type) → layer rules.
                        AUDIT ONLY — never auto-writes rules.
  Stage 5 Forget      — archive stale low-confidence connections to
                        archived_connections (never hard-deletes).

Idempotency: every write carries a marker (metadata.consolidation.resolved on
the resolved loser, removed duplicate rows, archived rows) so re-running the
pipeline reports 0 new actions on already-consolidated data.

Dry-run safety: pass dry_run=True (default) and nothing is written.
"""

import json
from datetime import datetime

from lib.controls.contradiction import conflict_score
from lib.controls.calibration import rate_connection_row
from lib.controls.temporal import needs_revalidation

# ── Tuning constants ──────────────────────────────────────────────────

# Min trigram Jaccard similarity for two same-type entities to be a merge
# candidate. High enough to avoid fusing distinct personas (Abram/Abraham
# score ~0.33), low enough to catch real duplicates (Israel / Isra'el).
MERGE_SIMILARITY_THRESHOLD = 0.9

# Stage 5 archive boundary: confidence below this AND older than this many days.
ARCHIVE_CONFIDENCE_THRESHOLD = 0.1
ARCHIVE_AGE_DAYS = 180

# Discovery methods treated as "explicit" for contradiction resolution —
# they always beat algorithmic/llm sources regardless of confidence.
EXPLICIT_DISCOVERERS = ("text", "script", "tsk", "human", "bible_dictionary")


# ── Column helpers (live-DB / fresh-DB tolerant) ──────────────────────

def _cols(conn, table):
    """Set of existing column names for a table (missing columns → no crash)."""
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _table_exists(conn, table):
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        return bool(row)
    except Exception:
        return False


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _older_than_days(created_at, days):
    """True when created_at is older than `days`; False if missing/unparseable."""
    if not created_at:
        return False
    try:
        created = datetime.strptime(str(created_at)[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return False
    return (datetime.now() - created).days > days


# ── Trigram similarity (stdlib — no FTS table required) ───────────────

def _trigrams(text):
    """Set of character trigrams for a normalized string."""
    norm = "".join(ch for ch in str(text or "").lower() if ch.isalnum())
    if len(norm) < 3:
        return {norm} if norm else set()
    return {norm[i:i + 3] for i in range(len(norm) - 2)}


def trigram_similarity(a, b):
    """Jaccard similarity over character trigrams (0.0-1.0)."""
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _surface_names(entity_row):
    """Every name surface for an entity: english/hebrew/greek + aliases."""
    names = []
    for field in ("english_name", "hebrew_name", "greek_name"):
        val = (entity_row.get(field) or "").strip()
        if val and len(val) >= 3:
            names.append(val)
    try:
        aliases = json.loads(entity_row.get("aliases") or "[]")
    except (ValueError, TypeError):
        aliases = []
    for a in aliases:
        if isinstance(a, str) and len(a.strip()) >= 3:
            names.append(a.strip())
    return names


def _best_similarity(names_a, names_b):
    """Max trigram similarity across two name-surface lists."""
    if not names_a or not names_b:
        return 0.0
    best = 0.0
    for a in names_a:
        for b in names_b:
            best = max(best, trigram_similarity(a, b))
    return best


# ── Stage 1: Inspect ──────────────────────────────────────────────────

def _verse_count(conn, entity_id):
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM verse_entities WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    return row["c"] if row else 0


def find_merge_candidates(conn, threshold=MERGE_SIMILARITY_THRESHOLD):
    """Stage 1a — same-type entities whose name surfaces are nearly identical.

    Returns list of {canonical, duplicate, similarity, entity_type, ...}.
    canonical = the entity with more verses (tie-break: lexicographically
    smaller id) — the row kept after merge.
    """
    cols = _cols(conn, "entity_links")
    alias_col = ", aliases" if "aliases" in cols else ""
    rows = conn.execute(
        f"SELECT entity_id, entity_type, english_name, hebrew_name, greek_name{alias_col} "
        f"FROM entity_links ORDER BY entity_type, entity_id"
    ).fetchall()
    entities = [dict(r) for r in rows]
    for e in entities:
        e["_names"] = _surface_names(e)
        e["_verse_count"] = _verse_count(conn, e["entity_id"])

    candidates = []
    for i in range(len(entities)):
        for j in range(i + 1, len(entities)):
            a, b = entities[i], entities[j]
            if (a["entity_type"] or "") != (b["entity_type"] or ""):
                continue
            sim = _best_similarity(a["_names"], b["_names"])
            if sim < threshold:
                continue
            if (b["_verse_count"] > a["_verse_count"]) or (
                b["_verse_count"] == a["_verse_count"] and b["entity_id"] < a["entity_id"]
            ):
                canonical, dup = b, a
            else:
                canonical, dup = a, b
            candidates.append({
                "canonical": canonical["entity_id"],
                "duplicate": dup["entity_id"],
                "similarity": round(sim, 3),
                "entity_type": a["entity_type"],
                "canonical_name": canonical["english_name"] or canonical["entity_id"],
                "duplicate_name": dup["english_name"] or dup["entity_id"],
            })
    return candidates


def _scan_conflicts(conn, limit=500):
    """Stage 1b — read-only contradiction scan (never tags/writes).

    Mirrors lib/controls/contradiction.scan_all_contradictions but stays
    side-effect free so --dry-run is truly report-only. Tolerates a missing
    deprecated/quality_level column on fresh databases.
    """
    cols = _cols(conn, "connections")
    dep_filter = " WHERE deprecated=0" if "deprecated" in cols else ""
    quality_col = ", quality_level" if "quality_level" in cols else ", NULL AS quality_level"

    pairs = conn.execute(
        f"SELECT "
        f"CASE WHEN source_verse < target_verse THEN source_verse ELSE target_verse END AS va, "
        f"CASE WHEN source_verse < target_verse THEN target_verse ELSE source_verse END AS vb, "
        f"COUNT(*) AS cnt FROM connections"
        f"{dep_filter} GROUP BY va, vb HAVING cnt > 1 ORDER BY cnt DESC"
    ).fetchall()

    conflicts = []
    for pair in pairs:
        a, b = pair["va"], pair["vb"]
        pair_rows = conn.execute(
            f"SELECT id, source_verse, target_verse, layer, type, subtype, "
            f"discovered_by{quality_col}, confidence "
            f"FROM connections"
            f"{dep_filter} AND ((source_verse=? AND target_verse=?) "
            f"OR (source_verse=? AND target_verse=?)) ORDER BY type",
            (a, b, b, a),
        ).fetchall()
        for i in range(len(pair_rows)):
            for j in range(i + 1, len(pair_rows)):
                c1, c2 = pair_rows[i], pair_rows[j]
                score = conflict_score(c1["type"], c2["type"], c1["layer"], c2["layer"])
                if score <= 0.3:
                    continue
                conflicts.append({
                    "source_verse": a,
                    "target_verse": b,
                    "conflict_score": round(score, 2),
                    "conflict_type": "contradictory" if score >= 0.5 else "tension",
                    "connection_a": {
                        "id": c1["id"], "type": c1["type"], "layer": c1["layer"],
                        "quality": c1["quality_level"], "discovered_by": c1["discovered_by"],
                    },
                    "connection_b": {
                        "id": c2["id"], "type": c2["type"], "layer": c2["layer"],
                        "quality": c2["quality_level"], "discovered_by": c2["discovered_by"],
                    },
                    "resolution_needed": score >= 0.5,
                })
        if limit and len(conflicts) >= limit:
            break
    return conflicts


def find_stale_connections(conn, threshold=0.3):
    """Stage 1c — connections whose decayed confidence would fall below threshold."""
    if "created_at" not in _cols(conn, "connections"):
        return []
    rows = conn.execute(
        "SELECT id, confidence, discovered_by, created_at FROM connections"
    ).fetchall()
    stale = []
    for r in rows:
        if needs_revalidation(r["created_at"], r["discovered_by"], threshold=threshold):
            stale.append({
                "id": r["id"],
                "confidence": r["confidence"],
                "discovered_by": r["discovered_by"],
                "created_at": r["created_at"],
            })
    return stale


# ── Stage 2: Resolve ──────────────────────────────────────────────────

def _safe_meta(row):
    if not isinstance(row, dict):
        try:
            row = dict(row)
        except Exception:
            return {}
    raw = row.get("metadata")
    if isinstance(raw, dict):
        return dict(raw)
    try:
        return json.loads(raw or "{}")
    except (ValueError, TypeError):
        return {}


def _already_resolved(row):
    return bool(_safe_meta(row).get("consolidation", {}).get("resolved"))


def _pick_winner(conn, a, b):
    """Higher calibrated quality wins; explicit sources beat algorithmic.

    Rank key: (explicitness, -quality, -confidence) — smaller tuple wins.
    """
    def _rank(row):
        explicit = 0 if (row.get("discovered_by") or "").lower() in EXPLICIT_DISCOVERERS else 1
        try:
            quality = rate_connection_row(row).get("quality_score", 0.0)
        except Exception:
            quality = 0.0
        return (explicit, -quality, -(row.get("confidence") or 0.0))

    a_rank, b_rank = _rank(a), _rank(b)
    if b_rank < a_rank:
        winner, loser = b, a
    else:
        winner, loser = a, b
    return winner, loser, (
        f"connection {winner['id']} (tier {_rank(winner)[0]}, "
        f"q={-_rank(winner)[1]:.2f}) beats {loser['id']}"
    )


def _apply_resolution(conn, winner, loser, conflict):
    """Mark the loser as resolved-against (idempotent via metadata marker)."""
    meta = _safe_meta(loser)
    meta["consolidation"] = {
        "resolved": True,
        "winner_id": winner["id"],
        "resolved_at": _now(),
        "reason": (
            f"{conflict['conflict_type']} ({conflict['conflict_score']}); "
            f"{loser.get('discovered_by')} loses to {winner.get('discovered_by')}"
        ),
    }
    conn.execute(
        "UPDATE connections SET metadata = ? WHERE id = ?",
        (json.dumps(meta, ensure_ascii=False), loser["id"]),
    )


def stage2_resolve(conn, conflicts, dry_run=True):
    """Stage 2 — resolve contradictory connection pairs.

    Only conflicts with resolution_needed (conflict_score >= 0.5) are acted on.
    Returns list of resolution records.
    """
    resolved = []
    for c in conflicts:
        if not c.get("resolution_needed"):
            continue
        a = conn.execute("SELECT * FROM connections WHERE id = ?", (c["connection_a"]["id"],)).fetchone()
        b = conn.execute("SELECT * FROM connections WHERE id = ?", (c["connection_b"]["id"],)).fetchone()
        if not a or not b:
            continue
        a, b = dict(a), dict(b)
        if _already_resolved(a) or _already_resolved(b):
            continue
        winner, loser, reason = _pick_winner(conn, a, b)
        resolved.append({
            "source_verse": c["source_verse"],
            "target_verse": c["target_verse"],
            "conflict_score": c["conflict_score"],
            "conflict_type": c["conflict_type"],
            "winner_id": winner["id"],
            "loser_id": loser["id"],
            "winner_discovered_by": winner["discovered_by"],
            "loser_discovered_by": loser["discovered_by"],
            "reason": reason,
        })
        if not dry_run:
            _apply_resolution(conn, winner, loser, c)
    return resolved


# ── Stage 3: Merge ────────────────────────────────────────────────────

def _apply_merge(conn, canonical_id, dup_id):
    """Coalesce duplicate entity row into canonical: merge aliases, re-point
    verse_entities, re-point materialized co-occurrence, drop stale card."""
    cols = _cols(conn, "entity_links")
    c_row = conn.execute("SELECT * FROM entity_links WHERE entity_id = ?", (canonical_id,)).fetchone()
    d_row = conn.execute("SELECT * FROM entity_links WHERE entity_id = ?", (dup_id,)).fetchone()
    if not c_row or not d_row:
        return False

    # 1. Merge aliases + fill blank metadata fields on canonical
    aliases = set()
    if "aliases" in cols:
        for raw in (c_row["aliases"], d_row["aliases"]):
            try:
                aliases |= {a for a in json.loads(raw or "[]") if isinstance(a, str)}
            except (ValueError, TypeError):
                pass
    for field in ("english_name", "hebrew_name", "greek_name"):
        for row in (c_row, d_row):
            name = (row[field] or "").strip()
            if name:
                aliases.add(name)
    aliases.discard((c_row["english_name"] or "").strip())

    update = {}
    for field in ("english_name", "hebrew_name", "hebrew_strongs", "greek_name", "greek_strongs", "notes"):
        if field in c_row.keys() and field in d_row.keys() and not c_row[field] and d_row[field]:
            update[field] = d_row[field]
    if "aliases" in cols:
        update["aliases"] = json.dumps(sorted(aliases), ensure_ascii=False)
    if update:
        sets = ", ".join(f"{k} = ?" for k in update)
        conn.execute(
            f"UPDATE entity_links SET {sets} WHERE entity_id = ?",
            (*update.values(), canonical_id),
        )

    # 2. Re-point verse_entities (keep UNIQUE(verse_id, entity_id, relationship_type))
    conn.execute(
        "INSERT OR IGNORE INTO verse_entities (verse_id, entity_id, relationship_type, confidence) "
        "SELECT verse_id, ?, relationship_type, confidence FROM verse_entities WHERE entity_id = ?",
        (canonical_id, dup_id),
    )
    conn.execute("DELETE FROM verse_entities WHERE entity_id = ?", (dup_id,))

    # 3. Re-point materialized co-occurrence + dedupe (keep max-frequency row)
    if _table_exists(conn, "entity_cooccurrence"):
        conn.execute("UPDATE entity_cooccurrence SET entity_a = ? WHERE entity_a = ?", (canonical_id, dup_id))
        conn.execute("UPDATE entity_cooccurrence SET entity_b = ? WHERE entity_b = ?", (canonical_id, dup_id))
        conn.execute("DELETE FROM entity_cooccurrence WHERE entity_a = entity_b")
        conn.execute(
            "DELETE FROM entity_cooccurrence WHERE rowid NOT IN ("
            "SELECT MIN(rowid) FROM entity_cooccurrence GROUP BY entity_a, entity_b)"
        )

    # 4. Drop stale materialized card for the duplicate
    if _table_exists(conn, "entity_cards"):
        conn.execute("DELETE FROM entity_cards WHERE entity_id = ?", (dup_id,))

    # 5. Remove the duplicate row
    conn.execute("DELETE FROM entity_links WHERE entity_id = ?", (dup_id,))
    return True


def stage3_merge(conn, candidates, dry_run=True):
    """Stage 3 — coalesce duplicate entity_links rows."""
    merged = []
    for cand in candidates:
        ok = True
        if not dry_run:
            ok = _apply_merge(conn, cand["canonical"], cand["duplicate"])
        if ok:
            merged.append(cand)
    return merged


# ── Stage 4: Generalize ───────────────────────────────────────────────

def stage4_generalize(conn, limit=20):
    """Stage 4 — record frequent (layer, type) → layer rules.

    AUDIT ONLY: returns the frequent combos; never auto-writes rules to the DB.
    """
    rows = conn.execute(
        "SELECT layer, type, COUNT(*) AS frequency FROM connections "
        "GROUP BY layer, type ORDER BY frequency DESC LIMIT ?",
        (limit,),
    ).fetchall()
    rules = [{"layer": r["layer"], "type": r["type"], "frequency": r["frequency"]} for r in rows]
    return {"total_rules": len(rules), "rules": rules, "note": "audit only — no auto-write"}


# ── Stage 5: Forget ───────────────────────────────────────────────────

def _archivable(conn):
    """Connections below ARCHIVE_CONFIDENCE_THRESHOLD and older than ARCHIVE_AGE_DAYS."""
    cols = _cols(conn, "connections")
    created_col = ", created_at" if "created_at" in cols else ""
    rows = conn.execute(
        f"SELECT id, source_verse, target_verse, layer, type, subtype, strength, "
        f"confidence, discovered_by, metadata{created_col} "
        f"FROM connections WHERE confidence < ?",
        (ARCHIVE_CONFIDENCE_THRESHOLD,),
    ).fetchall()
    out = []
    for r in rows:
        created = r["created_at"] if "created_at" in r.keys() else None
        if _older_than_days(created, ARCHIVE_AGE_DAYS):
            out.append(dict(r))
    return out


def stage5_forget(conn, dry_run=True):
    """Stage 5 — archive stale low-confidence connections (never hard-delete)."""
    archived = []
    targets = _archivable(conn)
    for r in targets:
        archived.append({
            "id": r["id"],
            "source_verse": r["source_verse"],
            "target_verse": r["target_verse"],
            "layer": r["layer"],
            "type": r["type"],
            "confidence": r["confidence"],
            "discovered_by": r["discovered_by"],
        })
        if dry_run:
            continue
        conn.execute(
            "INSERT INTO archived_connections "
            "(source_verse, target_verse, layer, type, subtype, strength, confidence, "
            " discovered_by, metadata, archived_at, archive_reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'stale_low_confidence')",
            (r["source_verse"], r["target_verse"], r["layer"], r["type"], r["subtype"],
             r["strength"], r["confidence"], r["discovered_by"], r["metadata"]),
        )
        conn.execute("DELETE FROM connections WHERE id = ?", (r["id"],))
    return archived


# ── Orchestrator ──────────────────────────────────────────────────────

def consolidate(conn, dry_run=True):
    """Run the full 5-stage consolidation pipeline.

    Args:
        conn: SQLite connection.
        dry_run: True → report only, zero writes (default). False → applies.

    Returns: report dict with per-stage results + summary.
    """
    # Stage 1 — inspect (always read-only)
    merge_candidates = find_merge_candidates(conn)
    conflicts = _scan_conflicts(conn)
    stale = find_stale_connections(conn)

    # Stages 2-5 (dry_run gates the writes)
    resolved = stage2_resolve(conn, conflicts, dry_run=dry_run)
    merged = stage3_merge(conn, merge_candidates, dry_run=dry_run)
    rules = stage4_generalize(conn)
    archived = stage5_forget(conn, dry_run=dry_run)

    if not dry_run:
        conn.commit()

    total_actions = len(resolved) + len(merged) + len(archived)
    return {
        "dry_run": dry_run,
        "stages": {
            "1_inspect": {
                "merge_candidates": merge_candidates,
                "merge_candidate_count": len(merge_candidates),
                "contradiction_count": len(conflicts),
                "conflicts": conflicts,
                "stale_count": len(stale),
                "stale_ids": [s["id"] for s in stale[:100]],
            },
            "2_resolve": {"resolved": resolved, "count": len(resolved)},
            "3_merge": {"merged": merged, "count": len(merged)},
            "4_generalize": rules,
            "5_forget": {"archived": archived, "count": len(archived)},
        },
        "summary": {
            "merge_candidates": len(merge_candidates),
            "contradictions": len(conflicts),
            "stale": len(stale),
            "resolved": len(resolved),
            "merged": len(merged),
            "generalized_rules": rules["total_rules"],
            "archived": len(archived),
            "total_actions": total_actions,
        },
    }
