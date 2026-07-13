"""Conversation session routes."""
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from lib.api.conversations import (
    add_connection,
    add_message,
    create_session,
    delete_session,
    get_session,
    list_connections,
    list_sessions,
    promote_connection,
    update_session,
)

router = APIRouter()
BASE_DIR = Path(__file__).parent.parent.parent

def get_db():
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from lib.db import get_db as _get_db
    return _get_db()

# ─── Conversation / Chat Sessions ───

class ConversationCreate(BaseModel):
    title: str = ""
    theme: str = ""
    created_by: str = "anonymous"

class MessageCreate(BaseModel):
    role: str  # 'user', 'assistant', 'system'
    content: str
    metadata: dict | None = {}

class SessionUpdate(BaseModel):
    title: str | None = None
    is_starred: bool | None = None

class ConnectionPromote(BaseModel):
    layer: str = "intertextual"
    type_name: str = "parallel"
    subtype: str = ""
    strength: float = 0.5
    confidence: float = 0.5
    discovered_by: str = "conversation"

class ManualConnection(BaseModel):
    source_verse: str
    target_verse: str
    relationship: str = ""
    connection_type: str = "discovered"
    confidence: float = 0.5
    description: str = ""

@router.get("/api/v1/conversations")
def list_conversations(page: int = 1, per_page: int = 20, starred: bool | None = None, search: str = ""):
    """List conversation sessions, paginated."""
    conn = get_db()
    result = list_sessions(conn, page=page, per_page=per_page, starred=starred, search=search)
    conn.close()
    return {"ok": True, "data": result}

@router.post("/api/v1/conversations")
def create_conversation(body: ConversationCreate):
    """Create a new conversation session."""
    conn = get_db()
    session = create_session(conn, title=body.title, theme=body.theme, created_by=body.created_by)
    conn.close()
    return {"ok": True, "data": session}

@router.get("/api/v1/conversations/{session_id}")
def get_conversation(session_id: str):
    """Get a conversation session with all messages, refs, and connections."""
    conn = get_db()
    session = get_session(conn, session_id)
    conn.close()
    if not session:
        return {"ok": False, "error": "Session not found"}
    return {"ok": True, "data": session}

@router.patch("/api/v1/conversations/{session_id}")
def update_conversation(session_id: str, body: SessionUpdate):
    """Update session title or starred status."""
    conn = get_db()
    session = update_session(conn, session_id, title=body.title, is_starred=body.is_starred)
    conn.close()
    return {"ok": True, "data": session}

@router.delete("/api/v1/conversations/{session_id}")
def delete_conversation(session_id: str):
    """Delete a conversation session."""
    conn = get_db()
    result = delete_session(conn, session_id)
    conn.close()
    return {"ok": True, "data": result}

@router.post("/api/v1/conversations/{session_id}/messages")
def add_conversation_message(session_id: str, body: MessageCreate):
    """Add a message to a conversation. Auto-extracts verse refs and detects connections."""
    if not body.content.strip():
        return {"ok": False, "error": "Content is required"}
    conn = get_db()
    # Verify session exists
    session = conn.execute(
        "SELECT id FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return {"ok": False, "error": "Session not found"}
    result = add_message(conn, session_id, body.role, body.content, metadata=body.metadata)
    conn.close()
    return {"ok": True, "data": result}

@router.post("/api/v1/conversations/{session_id}/messages/batch")
def add_conversation_messages_batch(session_id: str, body: list[MessageCreate]):
    """Add multiple messages at once (for page reload recovery)."""
    conn = get_db()
    session = conn.execute(
        "SELECT id FROM conversation_sessions WHERE id = ?", (session_id,)
    ).fetchone()
    if not session:
        conn.close()
        return {"ok": False, "error": "Session not found"}
    results = []
    for msg in body:
        r = add_message(conn, session_id, msg.role, msg.content, metadata=msg.metadata)
        results.append(r)
    conn.close()
    return {"ok": True, "data": {"messages": results, "count": len(results)}}

@router.get("/api/v1/conversations/{session_id}/connections")
def get_conversation_connections(session_id: str, connection_type: str | None = None):
    """List connections discovered/retrieved in a conversation."""
    conn = get_db()
    result = list_connections(conn, session_id, connection_type=connection_type)
    conn.close()
    return {"ok": True, "data": {"connections": result, "total": len(result)}}

@router.post("/api/v1/conversations/{session_id}/connections")
def add_conversation_connection(session_id: str, body: ManualConnection):
    """Manually add a connection to a session."""
    conn = get_db()
    add_connection(
        conn, session_id,
        source_verse=body.source_verse,
        target_verse=body.target_verse,
        relationship=body.relationship,
        connection_type=body.connection_type,
        confidence=body.confidence,
        description=body.description,
    )
    conn.close()
    return {"ok": True, "data": {"message": "Connection added"}}

@router.post("/api/v1/conversations/{session_id}/connections/{connection_id}/promote")
def promote_conversation_connection(session_id: str, connection_id: int, body: ConnectionPromote):
    """Promote a conversation connection to the main connection graph."""
    conn = get_db()
    result = promote_connection(
        conn, connection_id,
        layer=body.layer,
        type_name=body.type_name,
        subtype=body.subtype,
        strength=body.strength,
        confidence=body.confidence,
        discovered_by=body.discovered_by,
    )
    conn.close()
    if result.get("ok"):
        return {"ok": True, "data": result}
    return {"ok": False, "error": result.get("error", "Promotion failed")}


