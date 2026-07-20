"""Forum topics and posts API."""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ForumPostCreate(BaseModel):
    topic_id: int
    content: str
    author: str = "anonymous"
    parent_id: int | None = None


def get_db():
    from lib.db import get_db as _get_db
    return _get_db()


@router.get("/api/v1/forum/topics", operation_id="forum_list_topics")
def list_forum_topics(category: str = ""):
    """List forum topics, optionally filtered by category."""
    conn = get_db()
    query = "SELECT * FROM forum_topics"
    params = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY post_count DESC, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {"ok": True, "data": {
        "topics": [dict(r) for r in rows],
        "total": len(rows),
    }}


@router.get("/api/v1/forum/topics/{topic_id:path}", operation_id="forum_get_topic")
def get_forum_topic(topic_id: str):
    """Get a forum topic with its posts."""
    conn = get_db()
    topic = conn.execute("SELECT * FROM forum_topics WHERE id = ? OR slug = ?",
                        (topic_id, topic_id)).fetchone()
    if not topic:
        conn.close()
        return {"ok": False, "error": "Topic not found"}

    posts = conn.execute("""
        SELECT * FROM forum_posts WHERE topic_id = ? ORDER BY created_at ASC
    """, (topic["id"],)).fetchall()

    conn.close()
    return {"ok": True, "data": {"topic": dict(topic), "posts": [dict(p) for p in posts]}}


@router.post("/api/v1/forum/posts", operation_id="forum_create_post")
def create_forum_post(post: ForumPostCreate):
    """Create a new post in a forum topic."""
    conn = get_db()
    conn.execute("""
        INSERT INTO forum_posts (topic_id, author, content, parent_id)
        VALUES (?, ?, ?, ?)
    """, (post.topic_id, post.author, post.content.strip(), post.parent_id))
    conn.execute("UPDATE forum_topics SET post_count = post_count + 1 WHERE id = ?", (post.topic_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "data": {"created": True}}
