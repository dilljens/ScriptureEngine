"""UI tabs management — in-memory, resets with server."""

import uuid
from pydantic import BaseModel
from fastapi import APIRouter

router = APIRouter()

UI_TABS = {}  # In-memory tab storage


class TabCreate(BaseModel):
    type: str = "chapter"
    title: str = ""
    ref: str = ""
    query: str = ""
    parent: str = ""


@router.get("/api/v1/tabs")
def list_tabs():
    """List all open UI tabs."""
    return {"ok": True, "data": {"tabs": list(UI_TABS.values())}}


@router.post("/api/v1/tabs")
def create_tab(tab: TabCreate):
    """Create a new UI tab."""
    tid = f"tab_{uuid.uuid4().hex[:8]}"
    UI_TABS[tid] = {
        "id": tid, "type": tab.type, "title": tab.title,
        "ref": tab.ref, "query": tab.query, "parent": tab.parent,
    }
    return {"ok": True, "data": UI_TABS[tid]}


@router.delete("/api/v1/tabs/{tab_id}")
def delete_tab(tab_id: str):
    """Delete a UI tab."""
    if tab_id in UI_TABS:
        del UI_TABS[tab_id]
    return {"ok": True, "data": {"deleted": tab_id}}


@router.patch("/api/v1/tabs/{tab_id}")
def update_tab(tab_id: str, body: dict):
    """Update a UI tab's properties."""
    if tab_id in UI_TABS:
        UI_TABS[tab_id].update(body)
    return {"ok": True, "data": UI_TABS.get(tab_id, {})}
