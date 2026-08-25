"""Shared conversation snapshots — unlisted link sharing with fork-on-question.

A share is a frozen snapshot of a conversation, or of a single response within
it. Anyone with the link can read it (GET /api/v1/shared/{slug} is public by
design). Asking a follow-up question forks the snapshot into a new session
owned by the asker; the original conversation is never touched.
"""
import json
import re
import uuid
from datetime import datetime

from lib.api.conversations import add_message, create_session, get_session


def _slugify(title):
    """Generate a URL-safe slug from a title (mirrors lib/api/study.py)."""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if not slug:
        slug = str(uuid.uuid4())[:8]
    return slug[:60]


def _unique_slug(conn, base):
    slug = base
    counter = 1
    while conn.execute(
        "SELECT 1 FROM shared_conversations WHERE slug = ?", (slug,)
    ).fetchone():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def share_conversation(conn, session_id, created_by="anonymous", message_id=None):
    """Snapshot a conversation (or one response) into a shareable record.

    Args:
        session_id: Conversation session to snapshot.
        created_by: Owner id of the sharer.
        message_id: Optional conversation_messages.id — share just that
            response. An assistant response includes its preceding user
            question for context.

    Returns: dict with id, slug, url, title — or {"error": ...}.
    """
    session = get_session(conn, session_id)
    if not session:
        return {"error": f"Conversation {session_id} not found"}

    messages = session.get("messages", [])
    if message_id is not None:
        idx = next((i for i, m in enumerate(messages) if m["id"] == message_id), None)
        if idx is None:
            return {"error": f"Message {message_id} not found in conversation"}
        selected = [messages[idx]]
        if (
            messages[idx]["role"] == "assistant"
            and idx > 0
            and messages[idx - 1]["role"] == "user"
        ):
            selected.insert(0, messages[idx - 1])
        messages = selected
        title = f"Response: {session.get('title') or 'Untitled conversation'}"
    else:
        title = session.get("title") or "Shared conversation"

    content = {
        "title": title,
        "shared_at": datetime.utcnow().isoformat(),
        "messages": [
            {"role": m["role"], "content": m["content"], "timestamp": m.get("timestamp")}
            for m in messages
        ],
    }

    share_id = str(uuid.uuid4())[:8]
    slug = _unique_slug(conn, _slugify(title))
    conn.execute("""
        INSERT INTO shared_conversations
            (id, slug, source_session_id, source_message_id, title, content_json, created_by)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (share_id, slug, session_id, message_id, title,
          json.dumps(content, ensure_ascii=False), created_by))
    conn.commit()

    return {"id": share_id, "slug": slug, "url": f"/?shared={slug}", "title": title}


def get_shared(conn, slug):
    """Get a shared snapshot by slug. Public — no ownership check."""
    row = conn.execute(
        "SELECT * FROM shared_conversations WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        return None

    conn.execute(
        "UPDATE shared_conversations SET view_count = view_count + 1 WHERE slug = ?",
        (slug,),
    )
    conn.commit()

    data = json.loads(row["content_json"])
    return {
        "id": row["id"],
        "slug": row["slug"],
        "title": row["title"],
        "created_by": row["created_by"],
        "view_count": row["view_count"] + 1,
        "fork_count": row["fork_count"],
        "created_at": row["created_at"],
        "messages": data.get("messages", []),
    }


def fork_shared(conn, slug, created_by="anonymous"):
    """Fork a shared snapshot into a new session owned by `created_by`.

    Messages are re-inserted through add_message so verse refs and
    connections are re-extracted for the forked session.

    Returns: dict with session_id, title, message_count — or {"error": ...}.
    """
    row = conn.execute(
        "SELECT * FROM shared_conversations WHERE slug = ?", (slug,)
    ).fetchone()
    if not row:
        return {"error": f"Shared conversation {slug} not found"}

    data = json.loads(row["content_json"])
    session = create_session(conn, title=row["title"], theme="forked", created_by=created_by)
    new_sid = session["id"]
    count = 0
    for m in data.get("messages", []):
        add_message(conn, new_sid, m["role"], m["content"],
                    metadata={"source": "shared_fork", "shared_slug": slug})
        count += 1

    conn.execute(
        "UPDATE shared_conversations SET fork_count = fork_count + 1 WHERE slug = ?",
        (slug,),
    )
    conn.commit()
    return {"session_id": new_sid, "title": row["title"], "message_count": count}
