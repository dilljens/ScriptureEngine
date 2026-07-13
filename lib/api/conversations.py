"""
Conversation tracking for LLM chat sessions.

Saves every message, extracts verse references, detects connections
(both retrieved from the graph and newly discovered by the LLM).
"""

import contextlib
import json
import re
import uuid
from datetime import datetime

# ─── Verse Reference Extraction ───

# Known book name aliases (lowercase → canonical book_id)
BOOK_ALIASES = {
    # OT
    "genesis": "gen", "gen": "gen",
    "exodus": "exo", "exo": "exo", "exod": "exo",
    "leviticus": "lev", "lev": "lev",
    "numbers": "num", "num": "num",
    "deuteronomy": "deu", "deu": "deu", "deut": "deu",
    "joshua": "josh", "josh": "josh",
    "judges": "judg", "judg": "judg",
    "ruth": "ruth",
    "1samuel": "1sam", "1sam": "1sam",
    "2samuel": "2sam", "2sam": "2sam",
    "1kings": "1kgs", "1kgs": "1kgs",
    "2kings": "2kgs", "2kgs": "2kgs",
    "1chronicles": "1chr", "1chr": "1chr",
    "2chronicles": "2chr", "2chr": "2chr",
    "ezra": "ezra",
    "nehemiah": "neh", "neh": "neh",
    "esther": "esth", "esth": "esth",
    "job": "job",
    "psalms": "psa", "psalm": "psa", "psa": "psa",
    "proverbs": "prov", "prov": "prov",
    "ecclesiastes": "eccl", "eccl": "eccl",
    "song of solomon": "song", "song": "song",
    "isaiah": "isa", "isa": "isa",
    "jeremiah": "jer", "jer": "jer",
    "lamentations": "lam", "lam": "lam",
    "ezekiel": "ezek", "ezek": "ezek",
    "daniel": "dan", "dan": "dan",
    "hosea": "hos", "hos": "hos",
    "joel": "joel",
    "amos": "amos",
    "obadiah": "obad", "obad": "obad",
    "jonah": "jonah",
    "micah": "mic", "mic": "mic",
    "nahum": "nah", "nah": "nah",
    "habakkuk": "hab", "hab": "hab",
    "zephaniah": "zeph", "zeph": "zeph",
    "haggai": "hag", "hag": "hag",
    "zechariah": "zech", "zech": "zech",
    "malachi": "mal", "mal": "mal",
    # NT
    "matthew": "matt", "matt": "matt",
    "mark": "mark",
    "luke": "luke",
    "john": "john",
    "acts": "acts",
    "romans": "rom", "rom": "rom",
    "1corinthians": "1cor", "1cor": "1cor",
    "2corinthians": "2cor", "2cor": "2cor",
    "galatians": "gal", "gal": "gal",
    "ephesians": "eph", "eph": "eph",
    "philippians": "phil", "phil": "phil",
    "colossians": "col", "col": "col",
    "1thessalonians": "1thes", "1thes": "1thes",
    "2thessalonians": "2thes", "2thes": "2thes",
    "1timothy": "1tim", "1tim": "1tim",
    "2timothy": "2tim", "2tim": "2tim",
    "titus": "titus",
    "philemon": "philem", "philem": "philem",
    "hebrews": "heb", "heb": "heb",
    "james": "james",
    "1peter": "1pet", "1pet": "1pet",
    "2peter": "2pet", "2pet": "2pet",
    "1john": "1john",
    "2john": "2john",
    "3john": "3john",
    "jude": "jude",
    "revelation": "rev", "rev": "rev",
    # BoM
    "1nephi": "1ne", "1ne": "1ne",
    "2nephi": "2ne", "2ne": "2ne",
    "jacob": "jacob",
    "enos": "enos",
    "jarom": "jarom",
    "omni": "omni",
    "words of mormon": "wom", "wom": "wom",
    "mosiah": "mosiah",
    "alma": "alma",
    "helaman": "hel", "hel": "hel",
    "3nephi": "3ne", "3ne": "3ne",
    "4nephi": "4ne", "4ne": "4ne",
    "mormon": "morm",
    "ether": "ether",
    "moroni": "moro", "moro": "moro",
    # D&C
    "doctrine and covenants": "dc",
    # PGP
    "moses": "moses",
    "abraham": "abraham",
    "joseph smith—matthew": "jsm", "jsm": "jsm",
    "joseph smith—history": "jsh", "jsh": "jsh",
    "articles of faith": "aoff", "aoff": "aoff",
}

# Pattern: "book.chapter.verse" (gen.1.1, isa.55.6) — also handle (gen.1.1) [gen.1.1] "gen.1.1"
REF_PATTERN_DOT = re.compile(
    r'(?:^|\s|\(|\[|\")([a-z0-9_]+)\.(\d+)\.(\d+)(?=\s|$|\.|,|;|\)|\]|\"|\?|!)',
    re.IGNORECASE
)
# Pattern: find "Chapter:Verse" (1:1, 55:6) then look backwards for a book name
# This is more reliable than trying to capture book names greedily
REF_CHAPTER_VERSE = re.compile(r'(\d+):(\d+)')


def resolve_book_name(name):
    """Resolve a book name/alias to a canonical book_id. Returns None if unknown."""
    key = name.strip().lower()
    # Direct lookup
    if key in BOOK_ALIASES:
        return BOOK_ALIASES[key]
    # Try stripping 'suffix' numbers like '1 nephi' → '1ne'
    parts = key.split()
    if len(parts) >= 2:
        # "1 nephi" → "1nephi" → lookup
        joined = "".join(parts)
        if joined in BOOK_ALIASES:
            return BOOK_ALIASES[joined]
        # "first nephi" → try numbers prefix variant
        num_map = {"first": "1", "second": "2", "third": "3"}
        if parts[0] in num_map:
            joined2 = num_map[parts[0]] + "".join(parts[1:])
            if joined2 in BOOK_ALIASES:
                return BOOK_ALIASES[joined2]
    return None


def _extract_text_refs(text, seen):
    """Extract 'Book Chapter:Verse' refs by looking backwards from chapter:verse patterns."""
    refs = []
    # Split into words for backwards scanning
    words = text.split()
    word_positions = []  # (word, start_char, end_char)
    pos = 0
    for w in words:
        start = text.find(w, pos)
        end = start + len(w)
        word_positions.append((w, start, end))
        pos = end

    # Find book/chapter/verse patterns
    # Look for patterns like: "Genesis 1:1", "isa 55:6", "1 Nephi 3:7"
    for i, (word, _ws, we) in enumerate(word_positions):
        # Check if this word starts a "Chapter:Verse" or "Chapter:verse" pattern
        cv_match = REF_CHAPTER_VERSE.match(word)
        if not cv_match:
            continue

        chapter, verse = int(cv_match.group(1)), int(cv_match.group(2))

        # Look backwards at the preceding 1-3 words for a book name
        for lookback in range(1, 4):
            if i - lookback < 0:
                break
            candidate_words = word_positions[i - lookback:i]
            candidate = " ".join(w[0] for w in candidate_words)

            # Also try removing trailing "the", "of", etc.
            book_id = resolve_book_name(candidate)
            if book_id:
                verse_id = f"{book_id}.{chapter}.{verse}"
                if verse_id not in seen:
                    seen.add(verse_id)
                    start = max(0, candidate_words[0][2] - 50)
                    end = min(len(text), we + 50)
                    refs.append({
                        "verse_id": verse_id,
                        "context": text[start:end].strip(),
                    })
                break  # Found the book name, don't look further back

    return refs


def extract_verse_refs(text):
    """Extract verse references from text.

    Returns list of {"verse_id": str, "context": str} dicts.
    Supports: gen.1.1, gen 1:1, Genesis 1:1, 1ne 3:7, etc.
    """
    refs = []
    seen = set()

    # Pattern 1: book.chapter.verse (gen.1.1, isa.55.6)
    for m in REF_PATTERN_DOT.finditer(text):
        book_id = m.group(1).lower()
        chapter = int(m.group(2))
        verse = int(m.group(3))
        verse_id = f"{book_id}.{chapter}.{verse}"
        if verse_id not in seen:
            seen.add(verse_id)
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            refs.append({
                "verse_id": verse_id,
                "context": text[start:end].strip(),
            })

    # Pattern 2: Book Chapter:Verse (Isaiah 55:6, Genesis 1:1, 1ne 3:7)
    refs.extend(_extract_text_refs(text, seen))

    return refs


def validate_refs(conn, refs):
    """Filter refs to only those that exist in the verses table."""
    if not refs:
        return refs
    placeholders = ",".join("?" for _ in refs)
    verse_ids = [r["verse_id"] for r in refs]
    existing = set(
        row[0] for row in
        conn.execute(f"SELECT id FROM verses WHERE id IN ({placeholders})", verse_ids).fetchall()
    )
    return [r for r in refs if r["verse_id"] in existing]


# ─── Session CRUD ───

def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def create_session(conn, title="", theme="", created_by="anonymous"):
    """Create a new conversation session. Returns the session dict."""
    session_id = str(uuid.uuid4())
    now = _now()
    conn.execute("""
        INSERT INTO conversation_sessions (id, title, theme, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, title, theme, created_by, now, now))
    conn.commit()
    row = conn.execute(
        "SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    return dict(row)


def get_session(conn, session_id):
    """Get a session with all messages, refs, and connections."""
    session = conn.execute(
        "SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        return None
    result = dict(session)

    # Messages
    messages = conn.execute("""
        SELECT * FROM conversation_messages
        WHERE session_id = ? ORDER BY id ASC
    """, (session_id,)).fetchall()
    result["messages"] = [dict(m) for m in messages]

    # Refs (per message)
    refs = conn.execute("""
        SELECT cr.*, cm.role as message_role
        FROM conversation_refs cr
        JOIN conversation_messages cm ON cm.id = cr.message_id
        WHERE cr.session_id = ? ORDER BY cr.id ASC
    """, (session_id,)).fetchall()
    result["refs"] = [dict(r) for r in refs]

    # Connections
    connections = conn.execute("""
        SELECT * FROM conversation_connections
        WHERE session_id = ? ORDER BY created_at ASC
    """, (session_id,)).fetchall()
    result["connections"] = [dict(c) for c in connections]

    return result


def list_sessions(conn, page=1, per_page=20, starred=None, search=""):
    """List conversation sessions, paginated. Returns {sessions, total, page, pages}."""
    where = []
    params = []
    if starred is not None:
        where.append("is_starred = ?")
        params.append(1 if starred else 0)
    if search:
        where.append("(title LIKE ? OR id IN (SELECT DISTINCT session_id FROM conversation_messages WHERE content LIKE ?))")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    # Total count
    total = conn.execute(
        f"SELECT COUNT(*) FROM conversation_sessions {where_clause}", params
    ).fetchone()[0]

    pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    rows = conn.execute(f"""
        SELECT * FROM conversation_sessions
        {where_clause}
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?
    """, params + [per_page, offset]).fetchall()

    return {
        "sessions": [dict(r) for r in rows],
        "total": total,
        "page": page,
        "pages": pages,
    }


def update_session(conn, session_id, title=None, is_starred=None):
    """Update session fields (title, starred)."""
    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if is_starred is not None:
        updates.append("is_starred = ?")
        params.append(1 if is_starred else 0)
    if not updates:
        return get_session(conn, session_id)
    updates.append("updated_at = ?")
    params.append(_now())
    params.append(session_id)
    conn.execute(
        f"UPDATE conversation_sessions SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    return get_session(conn, session_id)


def delete_session(conn, session_id):
    """Delete a session and all cascade data."""
    conn.execute("DELETE FROM conversation_sessions WHERE id = ?", (session_id,))
    conn.commit()
    return {"deleted": True}


# ─── Messages ───

def add_message(conn, session_id, role, content, metadata=None):
    """Add a message to a session. Auto-extracts verse refs.

    If metadata contains a "connections" key, those are also saved.
    """
    metadata = metadata or {}
    now = _now()

    # Insert message
    cur = conn.execute("""
        INSERT INTO conversation_messages (session_id, role, content, metadata_json, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (session_id, role, content, json.dumps(metadata), now))
    message_id = cur.lastrowid

    # Auto-extract verse refs from content
    raw_refs = extract_verse_refs(content)
    valid_refs = validate_refs(conn, raw_refs)

    for ref in valid_refs:
        with contextlib.suppress(Exception):
            conn.execute("""
                INSERT OR IGNORE INTO conversation_refs (session_id, message_id, verse_id, context, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, message_id, ref["verse_id"], ref["context"], 1.0))

    # Handle connections from metadata
    connections = metadata.get("connections", [])
    if connections and isinstance(connections, list):
        for c in connections:
            try:
                conn_type = c.get("type", "discovered")
                src = c.get("source", "")
                tgt = c.get("target", "")
                if src and tgt:
                    # Check if connection already exists in main graph
                    existing_id = None
                    if conn_type == "retrieved" and "existing_connection_id" in c:
                        existing_id = c["existing_connection_id"]
                    elif conn_type in ("discovered", "suggested"):
                        row = conn.execute("""
                            SELECT id FROM connections
                            WHERE (source_verse = ? AND target_verse = ?)
                               OR (source_verse = ? AND target_verse = ?)
                            LIMIT 1
                        """, (src, tgt, tgt, src)).fetchone()
                        if row:
                            existing_id = row["id"]
                            conn_type = "retrieved"

                    conn.execute("""
                        INSERT OR IGNORE INTO conversation_connections
                            (session_id, source_verse, target_verse, relationship,
                             connection_type, existing_connection_id, confidence,
                             description, context_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, src, tgt,
                        c.get("relationship", ""),
                        conn_type, existing_id,
                        c.get("confidence", 0.5),
                        c.get("description", ""),
                        c.get("context_message", content[:200]),
                    ))
            except Exception:
                pass  # Gracefully skip invalid connections

    # Auto-detect connections from co-occurring refs in same message
    if len(valid_refs) >= 2 and not connections:
        verse_ids = [r["verse_id"] for r in valid_refs]
        for i in range(len(verse_ids)):
            for j in range(i + 1, len(verse_ids)):
                src, tgt = verse_ids[i], verse_ids[j]
                try:
                    # Check if this pair exists in connections table
                    existing = conn.execute("""
                        SELECT id FROM connections
                        WHERE (source_verse = ? AND target_verse = ?)
                           OR (source_verse = ? AND target_verse = ?)
                        LIMIT 1
                    """, (src, tgt, tgt, src)).fetchone()

                    conn_type = "retrieved" if existing else "discovered"
                    conn.execute("""
                        INSERT OR IGNORE INTO conversation_connections
                            (session_id, source_verse, target_verse, relationship,
                             connection_type, existing_connection_id, confidence,
                             context_message)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_id, src, tgt, "",
                        conn_type, existing["id"] if existing else None,
                        0.5, content[:200],
                    ))
                except Exception:
                    pass

    # Update message count + timestamp on session
    conn.execute("""
        UPDATE conversation_sessions
        SET message_count = message_count + 1, updated_at = ?
        WHERE id = ?
    """, (now, session_id))
    conn.commit()

    # Return full message
    msg = conn.execute(
        "SELECT * FROM conversation_messages WHERE id = ?", (message_id,)
    ).fetchone()

    # Also return refs that were saved for this message
    saved_refs = conn.execute("""
        SELECT * FROM conversation_refs WHERE message_id = ?
    """, (message_id,)).fetchall()

    result = dict(msg)
    result["refs"] = [dict(r) for r in saved_refs]
    return result


def add_messages_batch(conn, session_id, messages):
    """Add multiple messages at once (for page reload recovery)."""
    results = []
    for msg in messages:
        result = add_message(
            conn, session_id,
            msg.get("role", "user"),
            msg.get("content", ""),
            msg.get("metadata"),
        )
        results.append(result)
    return results


# ─── Connections ───

def list_connections(conn, session_id, connection_type=None):
    """List all connections in a session, optionally filtered."""
    sql = "SELECT * FROM conversation_connections WHERE session_id = ?"
    params = [session_id]
    if connection_type:
        sql += " AND connection_type = ?"
        params.append(connection_type)
    sql += " ORDER BY created_at ASC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def add_connection(conn, session_id, source_verse, target_verse,
                   relationship="", connection_type="discovered",
                   existing_connection_id=None, confidence=0.5,
                   description="", context_message=""):
    """Manually add a connection to a session."""
    try:
        conn.execute("""
            INSERT OR IGNORE INTO conversation_connections
                (session_id, source_verse, target_verse, relationship,
                 connection_type, existing_connection_id, confidence,
                 description, context_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, source_verse, target_verse, relationship,
              connection_type, existing_connection_id, confidence,
              description, context_message))
        conn.commit()
    except Exception:
        pass
    return {"ok": True}


def promote_connection(conn, connection_id, layer="intertextual",
                       type_name="parallel", subtype="", strength=0.5,
                       confidence=0.5, discovered_by="conversation"):
    """Promote a conversation connection to the main connections table."""
    row = conn.execute(
        "SELECT * FROM conversation_connections WHERE id = ?", (connection_id,)
    ).fetchone()
    if not row:
        return {"ok": False, "error": "Connection not found"}

    # Check if it already exists in main connections table
    existing = conn.execute("""
        SELECT id FROM connections
        WHERE (source_verse = ? AND target_verse = ?)
           OR (source_verse = ? AND target_verse = ?)
        LIMIT 1
    """, (row["source_verse"], row["target_verse"],
          row["target_verse"], row["source_verse"])).fetchone()

    if existing:
        return {"ok": False, "error": "Connection already exists in main graph"}

    try:
        from lib.db import add_connection as add_main_connection
        add_main_connection(
            conn,
            source_verse=row["source_verse"],
            target_verse=row["target_verse"],
            layer=layer,
            type_name=type_name,
            subtype=subtype,
            strength=strength,
            confidence=confidence,
            discovered_by=discovered_by,
            metadata={
                "source": "conversation_promotion",
                "description": row["description"],
                "original_connection_id": connection_id,
            },
        )
        # Mark promoted
        conn.execute(
            "UPDATE conversation_connections SET promoted = 1 WHERE id = ?",
            (connection_id,)
        )
        conn.commit()
        return {"ok": True, "message": "Connection promoted to main graph"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
