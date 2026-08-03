"""Come Follow Me + General Conference corpora tools.

These tools read the prose corpora (cfm_lessons / talks tables) — long-form
LDS curriculum and conference content that lives OUTSIDE the verse graph.

Scope note: the chat proxy only exposes these tools when the request declares
the matching scope (cfm / conference) — see web/routes/chat.py.
"""

import datetime
import re

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def _today():
    return datetime.date.today()


def _current_lesson(conn, year):
    """Pick the lesson whose [start_date, end_date] covers today; else nearest."""
    today = _today()
    rows = conn.execute(
        "SELECT ref_id, year, week_slug, date_range, title, scripture_block, text, start_date, end_date "
        "FROM cfm_lessons WHERE year = ? ORDER BY start_date", (year,)
    ).fetchall()
    if not rows:
        return None
    # Exact match first
    for r in rows:
        if r["start_date"] and r["end_date"] and r["start_date"] <= today.isoformat() <= r["end_date"]:
            return r
    # Fallback: smallest |distance| from today
    best = None
    for r in rows:
        if not r["start_date"]:
            continue
        dist = abs((datetime.date.fromisoformat(r["start_date"]) - today).days)
        if best is None or dist < best[1]:
            best = (r, dist)
    return best[0] if best else rows[0]


def _lesson_row_to_dict(r):
    return {
        "ref_id": r["ref_id"],
        "year": r["year"],
        "week": r["week_slug"],
        "date_range": r["date_range"],
        "title": r["title"],
        "scripture_block": r["scripture_block"],
        "text": r["text"],
    }


def cfm_lesson(conn, year=None, week=None, ref_id=None):
    """Look up a Come Follow Me weekly lesson.

    Provide year + week (e.g. year=2026, week='03') or a ref_id
    (e.g. 'cfm.2026.03'). With no arguments, returns the current
    calendar week's lesson automatically.
    """
    if ref_id:
        r = conn.execute("SELECT * FROM cfm_lessons WHERE ref_id = ?", (ref_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"No Come Follow Me lesson found for ref '{ref_id}'"}
        return {"ok": True, "lesson": _lesson_row_to_dict(r)}

    if year is None:
        year = _today().year
    else:
        year = int(year)

    if week is not None:
        r = conn.execute(
            "SELECT * FROM cfm_lessons WHERE year = ? AND week_slug = ?",
            (year, str(week).zfill(2)),
        ).fetchone()
        if not r:
            return {"ok": False, "error": f"No Come Follow Me lesson for year {year}, week '{week}'"}
        return {"ok": True, "lesson": _lesson_row_to_dict(r)}

    r = _current_lesson(conn, year)
    if not r:
        return {"ok": False, "error": f"No Come Follow Me lessons ingested for year {year}"}
    return {"ok": True, "lesson": _lesson_row_to_dict(r)}


def conference_talk(conn, year=None, month=None, session=None, speaker=None, title=None, ref_id=None):
    """Look up a General Conference talk.

    Pass a ref_id (e.g. 'gc.2025.04.13holland') for an exact hit, or filter by
    year/month/session/speaker/title (speaker and title are fuzzy substring
    matches). With only year+month, returns the session list for that
    conference so the caller can pick a talk.
    """
    if ref_id:
        r = conn.execute("SELECT * FROM talks WHERE ref_id = ?", (ref_id,)).fetchone()
        if not r:
            return {"ok": False, "error": f"No conference talk found for ref '{ref_id}'"}
        return {"ok": True, "talk": _talk_row_to_dict(r)}

    where, params = [], []
    if year is not None:
        where.append("year = ?"); params.append(int(year))
    if month is not None:
        where.append("month = ?"); params.append(int(month))
    if session:
        where.append("session LIKE ?"); params.append(f"%{session}%")
    if speaker:
        where.append("speaker LIKE ?"); params.append(f"%{speaker}%")
    if title:
        where.append("title LIKE ?"); params.append(f"%{title}%")

    sql = "SELECT * FROM talks" + (f" WHERE {' AND '.join(where)}" if where else "")
    sql += " ORDER BY year DESC, month DESC, ref_id"
    rows = conn.execute(sql, params).fetchall()

    if not rows:
        return {"ok": False, "error": "No conference talk matches those filters"}

    if len(rows) == 1 and (speaker or title or ref_id):
        return {"ok": True, "talk": _talk_row_to_dict(rows[0])}

    # Multiple matches — return candidates (with full text so the LLM can quote)
    return {"ok": True, "count": len(rows), "talks": [_talk_row_to_dict(r) for r in rows[:10]]}


def _talk_row_to_dict(r):
    return {
        "ref_id": r["ref_id"],
        "year": r["year"],
        "month": r["month"],
        "session": r["session"],
        "speaker": r["speaker"],
        "title": r["title"],
        "date": r["date"],
        "text": r["text"],
    }


def cfm_search(conn, query, corpus="both", year=None, limit=10):
    """Search the Come Follow Me and General Conference corpora.

    corpus: 'cfm' | 'conference' | 'both' (default both).
    year: optional filter. limit: max results (default 10, max 30).
    Returns ranked matches with snippets.
    """
    limit = min(int(limit or 10), 30)
    if not query or not query.strip():
        return {"ok": False, "error": "query is required"}
    query = query.strip()
    results = []

    if corpus in ("cfm", "both"):
        sql = (
            "SELECT l.ref_id, l.title, l.date_range, l.scripture_block, "
            "snippet(cfm_lessons_fts, 1, '[', ']', '…', 24) AS snip "
            "FROM cfm_lessons_fts JOIN cfm_lessons l ON l.rowid = cfm_lessons_fts.rowid "
            "WHERE cfm_lessons_fts MATCH ?"
        )
        params = [query]
        if year is not None:
            sql += " AND l.year = ?"; params.append(int(year))
        sql += " ORDER BY rank LIMIT ?"; params.append(limit)
        for r in conn.execute(sql, params).fetchall():
            results.append({
                "corpus": "cfm",
                "ref_id": r["ref_id"],
                "title": r["title"],
                "date_range": r["date_range"],
                "scripture_block": r["scripture_block"],
                "snippet": r["snip"],
            })

    if corpus in ("conference", "both"):
        sql = (
            "SELECT t.ref_id, t.title, t.speaker, t.session, t.year, t.month, "
            "snippet(talks_fts, 1, '[', ']', '…', 24) AS snip "
            "FROM talks_fts JOIN talks t ON t.rowid = talks_fts.rowid "
            "WHERE talks_fts MATCH ?"
        )
        params = [query]
        if year is not None:
            sql += " AND t.year = ?"; params.append(int(year))
        sql += " ORDER BY rank LIMIT ?"; params.append(limit)
        for r in conn.execute(sql, params).fetchall():
            results.append({
                "corpus": "conference",
                "ref_id": r["ref_id"],
                "title": r["title"],
                "speaker": r["speaker"],
                "session": r["session"],
                "year": r["year"],
                "month": r["month"],
                "snippet": r["snip"],
            })

    results.sort(key=lambda x: x["corpus"] == "cfm")
    return {"ok": True, "query": query, "count": len(results), "results": results[:limit]}


# ─── Scripture-block parsing (weekly study) ───

def _normalize(s: str) -> str:
    """Collapse \xa0 / whitespace, lowercase — for book-name matching."""
    return re.sub(r"\s+", " ", s.replace("\xa0", " ").replace("\u2009", " ")).strip().lower()


def _book_id_map(conn):
    """normalized book title → book id (longest titles first for prefix matching)."""
    rows = conn.execute("SELECT id, title FROM books").fetchall()
    entries = []
    for r in rows:
        t = _normalize(r["title"])
        if t:
            entries.append((t, r["id"]))
    # extra aliases (DB title vs common usage)
    alias = {"song of solomon": "song", "solomon's song": "song", "1 sam": "1sam",
             "2 sam": "2sam", "1 kgs": "1kgs", "2 kgs": "2kgs", "abraham": "abraham",
             "1 nephi": "1ne", "2 nephi": "2ne"}
    for name, bid in alias.items():
        entries.append((name, bid))
    entries.sort(key=lambda e: len(e[0]), reverse=True)
    return entries


def _parse_chapter_token(token: str):
    """'1–2' → (1,2); '27' → (27,27); '102–3' → (102,103). Handles abbreviated ends."""
    token = token.strip()
    m = re.match(r"^(\d{1,3})(?:\s*[–—-]\s*(\d{1,3}))?$", token)
    if not m:
        return None
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    if end < start and end < 100:  # abbreviated: "102–3" = 102–103
        cand = (start // 100) * 100 + end
        if cand > start:
            end = cand
    if end < start:
        start, end = end, start
    return (start, end)


def cfm_scripture_blocks(conn, ref_id):
    """Parse a lesson's scripture_block into structured, resolvable references.

    Handles: chapter ranges ("Genesis 1–2"), mixed ranges ("Exodus 19–20; 24;
    31–34" → Exodus 19,20,24,31,32,33,34), bare books ("Esther" → whole book),
    abbreviated ends ("Psalms 102–3" → 102–103), and \xa0 in "1\xa0Samuel".

    Returns: {"ok", "ref_id", "blocks": [{"book","book_id","chapters":[...],
    "whole_book"}]} — non-scripture segments (Easter, Christmas, Introduction)
    are skipped.
    """
    row = conn.execute("SELECT ref_id, scripture_block FROM cfm_lessons WHERE ref_id = ?", (ref_id,)).fetchone()
    if not row:
        return {"ok": False, "error": f"No lesson {ref_id}"}
    raw = row["scripture_block"] or ""

    book_map = _book_id_map(conn)
    blocks = []
    current_book = None  # (title, id) for bare continuation chapters

    def _push(title, bid, chapters, whole):
        blocks.append({
            "book": title, "book_id": bid,
            "chapters": chapters, "whole_book": whole,
        })

    for segment in [s.strip() for s in re.split(r";", raw)]:
        seg_norm = _normalize(segment)
        if not seg_norm:
            continue
        # Does this segment start a (new) book?
        matched = None
        for title, bid in book_map:
            if seg_norm == title or seg_norm.startswith(title + " "):
                matched = (title, bid)
                break
        if matched:
            current_book = matched
            rest = seg_norm[len(matched[0]):].strip()
        elif current_book is not None:
            rest = seg_norm  # continuation chapters of current book
        else:
            continue  # e.g. "Easter", "Introduction to the Old Testament"

        chapters = []
        if not rest:
            # whole book — resolve all chapters present in the verses table
            rows = conn.execute(
                "SELECT DISTINCT chapter FROM verses WHERE book_id = ? ORDER BY chapter",
                (current_book[1],),
            ).fetchall()
            chapters = [r["chapter"] for r in rows]
            _push(current_book[0], current_book[1], chapters, True)
            continue

        # rest is "1–2", "8–10", "1", or "1; 3–7" (already split) — single token here
        tok = _parse_chapter_token(rest)
        if tok:
            chapters = list(range(tok[0], tok[1] + 1))
            _push(current_book[0], current_book[1], chapters, False)
        # else: unrecognized token — skip silently

    # Merge consecutive blocks of the same book (e.g. "1 Samuel 8–10; 13; 15–16"
    # could split across segments if a book name appeared mid-list — rare; merge
    # anyway for cleanliness).
    merged = []
    for b in blocks:
        if merged and merged[-1]["book_id"] == b["book_id"]:
            seen = set(merged[-1]["chapters"])
            merged[-1]["chapters"] += [c for c in b["chapters"] if c not in seen]
            merged[-1]["whole_book"] = merged[-1]["whole_book"] and b["whole_book"]
        else:
            merged.append(dict(b))
    merged = [b for b in merged if b["chapters"]]

    return {"ok": True, "ref_id": ref_id, "blocks": merged}
