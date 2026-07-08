"""
Scripture Knowledge Engine — Shared Tool Registry.

Single source of truth for every tool function and its JSON schema.
Both MCP server (stdio JSON-RPC) and HTTP API (FastAPI) consume this.

Every tool:
  - Takes (conn, ...) as its signature — conn from get_db()
  - Returns a plain dict (not JSON-RPC wrapped, not HTTP wrapped)
  - Has a docstring that becomes the tool description
  - Is registered in TOOL_REGISTRY with its input schema

Adding a new tool:
  1. Implement the function in lib/api/<module>.py
  2. Import and register it in this file
  3. It's immediately available as MCP tool + HTTP API endpoint
"""

from lib.api.verse import lookup_verse, passage_guide
from lib.api.versions import list_versions, get_verse_text
from lib.api.interlinear import get_interlinear
from lib.api.search import search_text, search_xlingual
from lib.api.gematria import gematria_lookup
from lib.api.connections import get_connections, get_intertext, get_pardes
from lib.api.sod import hidden_patterns
from lib.api.graph import (
    graph_path,
    graph_reachable,
    graph_hubs,
    graph_entities,
    graph_shared_entities,
    graph_entity_network,
    graph_centrality,
    graph_stats,
)
from lib.api.info import get_stats
from lib.api.study import (
    create_guide, add_step, remove_step, reorder_steps, bulk_update_steps,
    update_guide, get_guide, list_guides, suggest_path,
    export_json, export_html, export_markdown, import_json,
    publish_study, get_published, list_published, fork_published,
)
from lib.api.strongs import strongs_lookup
from lib.api.disagreements import get_disagreements, list_disagreements
from lib.api.consensus import get_consensus
from lib.api.assessment import start_assessment, submit_answer, get_progress
from lib.api.sources import get_sources_for_verse, get_sources_by_scholar, list_scholars
from lib.api.conversations import (
    create_session,
    get_session,
    list_sessions,
    update_session,
    delete_session,
    add_message,
    add_messages_batch,
    list_connections,
    add_connection,
    promote_connection,
)

# ─── Registry ───

TOOL_REGISTRY = {}  # name → (fn, schema, description)


def register(name, fn, schema, description=""):
    """Register a tool function with its JSON Schema input spec."""
    TOOL_REGISTRY[name] = (fn, schema, description or (fn.__doc__ or "").strip())


# ─── Verse Tools ───

register(
    "scripture_verse",
    lookup_verse,
    {
        "type": "object",
        "properties": {
            "book": {"type": "string", "description": "Book ID (gen, exo, isa, matt, 1ne, etc.)"},
            "chapter": {"type": "integer"},
            "verse": {"type": "integer"},
            "version": {"type": "string", "description": "Preferred Bible version (WEB, KJV, etc.)"},
        },
        "required": ["book", "chapter", "verse"],
    },
    "Look up a verse with text, gematria, connections, and quality info",
)

register(
    "scripture_passage_guide",
    passage_guide,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
        },
        "required": ["verse"],
    },
    "Get pre-computed passage guide for a verse — instant access to all connections, gematria, and quality distribution",
)

register(
    "scripture_versions",
    list_versions,
    {"type": "object", "properties": {}},
    "List all available Bible text versions",
)

register(
    "scripture_verse_text",
    get_verse_text,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
            "version": {"type": "string", "default": "KJV", "description": "Bible version (KJV, LSV, WEB, etc.) — KJV covers the entire canon"},
        },
        "required": ["verse"],
    },
    "Get verse text in a specific Bible version",
)

register(
    "scripture_interlinear",
    get_interlinear,
    {
        "type": "object",
        "properties": {
            "book": {"type": "string", "description": "Book ID (gen, exo, isa, matt, 1ne, etc.)"},
            "chapter": {"type": "integer"},
            "verse": {"type": "integer"},
        },
        "required": ["book", "chapter", "verse"],
    },
    "Get word-by-word interlinear analysis of a verse with transliteration, Strong's, and morphology",
)

# ─── Search Tools ───

register(
    "scripture_search",
    search_text,
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search term"},
            "book": {"type": "string", "description": "Optional book filter"},
            "limit": {"type": "integer", "default": 20},
        },
        "required": ["query"],
    },
    "Search for verses by keyword in English text",
)

register(
    "scripture_search_xlingual",
    search_xlingual,
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Word to search for"},
            "language": {
                "type": "string",
                "enum": ["all", "english", "hebrew", "greek"],
                "default": "all",
                "description": "Language scope",
            },
        },
        "required": ["query"],
    },
    "Search across Hebrew, Greek, AND English simultaneously using entity alignment",
)

# ─── Gematria Tools ───

register(
    "scripture_gematria",
    gematria_lookup,
    {
        "type": "object",
        "properties": {
            "word": {"type": "string", "description": "Hebrew word (e.g., יהוה)"},
            "value": {"type": "integer", "description": "Look up verses with this gematria value"},
            "system": {
                "type": "string",
                "enum": ["standard", "ordinal", "reduced"],
                "default": "standard",
            },
        },
    },
    "Compute gematria for a Hebrew word or look up verses by gematria value",
)

# ─── Strong's Lexicon Tools ───

register(
    "scripture_strongs",
    strongs_lookup,
    {
        "type": "object",
        "properties": {
            "lemma": {"type": "string", "description": "Strong's number (e.g., H430, G26)"},
            "word": {"type": "string", "description": "Hebrew or Greek word text"},
        },
    },
    "Look up Strong's definition for a Hebrew or Greek word",
)

# ─── Connection Tools ───

register(
    "scripture_connections",
    get_connections,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
            "layer": {"type": "string", "description": "Filter by connection layer"},
            "min_quality": {"type": "string", "description": "Minimum quality level"},
        },
        "required": ["verse"],
    },
    "Get all connections for a verse, with layer and quality filtering",
)

register(
    "scripture_intertext",
    get_intertext,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID"},
        },
        "required": ["verse"],
    },
    "Get intertextual connections for a verse — quotations, allusions, echoes",
)

register(
    "scripture_pardes",
    get_pardes,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID"},
            "level": {
                "type": "string",
                "enum": ["pshat", "remez", "drash", "sod"],
                "description": "Filter to one PaRDeS level",
            },
        },
        "required": ["verse"],
    },
    "Show connections grouped by PaRDeS interpretation level (P'shat, Remez, Drash, Sod)",
)

# ─── Hidden Pattern Tools ───

register(
    "scripture_sod",
    hidden_patterns,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse to analyze for hidden patterns"},
            "atbash_word": {"type": "string", "description": "Hebrew word to decode via Atbash"},
            "acrostic_book": {"type": "string", "description": "Book ID to scan for acrostics"},
        },
    },
    "Explore hidden (Sod-level) patterns — atbash, acrostics, advanced gematria, hidden names",
)

# ─── Graph Traversal Tools (NEW) ───

register(
    "scripture_graph_path",
    graph_path,
    {
        "type": "object",
        "properties": {
            "start": {"type": "string", "description": "Starting verse ID (gen.1.1)"},
            "end": {"type": "string", "description": "Target verse ID"},
            "max_depth": {"type": "integer", "default": 3, "description": "Maximum path length in hops"},
            "layers": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional layer filter list",
            },
        },
        "required": ["start", "end"],
    },
    "Find the shortest connection path between two verses through the typed graph",
)

register(
    "scripture_graph_reachable",
    graph_reachable,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Starting verse ID"},
            "max_depth": {"type": "integer", "default": 3},
            "layers": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["verse"],
    },
    "Find all verses reachable within N hops from a verse through the connection graph",
)

register(
    "scripture_graph_hubs",
    graph_hubs,
    {
        "type": "object",
        "properties": {
            "min_connections": {"type": "integer", "default": 3},
            "layer": {"type": "string", "description": "Optional layer scope"},
            "limit": {"type": "integer", "default": 30},
        },
    },
    "Find hub verses — those connecting to the most diverse other verses",
)

register(
    "scripture_graph_entities",
    graph_entities,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID"},
            "min_confidence": {"type": "number", "default": 0.3},
        },
        "required": ["verse"],
    },
    "Get entities (people, places, concepts) linked to a specific verse",
)

register(
    "scripture_graph_shared_entities",
    graph_shared_entities,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID to start from"},
            "min_confidence": {"type": "number", "default": 0.3},
            "limit": {"type": "integer", "default": 50},
        },
        "required": ["verse"],
    },
    "Find other verses that share entities (people, places) with this verse",
)

register(
    "scripture_graph_entity_network",
    graph_entity_network,
    {
        "type": "object",
        "properties": {
            "entity": {"type": "string", "description": "Entity ID (e.g., 'person.abraham')"},
            "min_confidence": {"type": "number", "default": 0.3},
            "limit": {"type": "integer", "default": 100},
        },
        "required": ["entity"],
    },
    "Get all verses connected to a specific entity (person, place, or concept)",
)

register(
    "scripture_graph_centrality",
    graph_centrality,
    {
        "type": "object",
        "properties": {
            "book": {"type": "string", "description": "Optional book ID to scope analysis"},
            "layer": {"type": "string", "description": "Optional layer scope"},
            "limit": {"type": "integer", "default": 20},
        },
    },
    "Find the most central (best-connected) verses in the graph by degree centrality",
)

register(
    "scripture_graph_stats",
    graph_stats,
    {"type": "object", "properties": {}},
    "Get overall connection graph statistics — total connections, unique verses, hub count",
)

# ─── Info ───

register(
    "scripture_info",
    get_stats,
    {"type": "object", "properties": {}},
    "Get database statistics — total verses, connections per layer, quality distribution",
)

# ─── Study Guides ───

register(
    "scripture_study_create",
    create_guide,
    {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "description": {"type": "string", "default": ""},
            "theme": {"type": "string", "default": ""},
            "seed_verse": {"type": "string", "default": ""},
            "created_by": {"type": "string", "default": "ai"},
        },
        "required": ["title"],
    },
    "Create a new AI-guided study guide for exploring scripture connections",
)

register(
    "scripture_study_add_step",
    add_step,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
            "step_number": {"type": "integer"},
            "verse_id": {"type": "string"},
            "title": {"type": "string", "default": ""},
            "explanation": {"type": "string", "default": ""},
            "choices_json": {"type": "string", "default": "[]"},
        },
        "required": ["guide_id", "step_number", "verse_id"],
    },
    "Add a step to a study guide",
)

register(
    "scripture_study_get",
    get_guide,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
        },
        "required": ["guide_id"],
    },
    "Get a study guide with all its steps",
)

register(
    "scripture_study_list",
    list_guides,
    {
        "type": "object",
        "properties": {
            "theme": {"type": "string", "default": ""},
            "limit": {"type": "integer", "default": 20},
        },
    },
    "List all study guides, optionally filtered by theme",
)

register(
    "scripture_study_suggest",
    suggest_path,
    {
        "type": "object",
        "properties": {
            "seed_verse": {"type": "string"},
            "theme": {"type": "string", "default": ""},
        },
        "required": ["seed_verse"],
    },
    "Suggest an exploration path from a seed verse through the connection graph",
)

register(
    "scripture_study_update",
    update_guide,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
            "title": {"type": "string", "default": ""},
            "description": {"type": "string", "default": ""},
            "theme": {"type": "string", "default": ""},
            "seed_verse": {"type": "string", "default": ""},
        },
        "required": ["guide_id"],
    },
    "Update study guide metadata",
)

register(
    "scripture_study_remove_step",
    remove_step,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
            "step_number": {"type": "integer"},
        },
        "required": ["guide_id", "step_number"],
    },
    "Remove a step from a study guide and re-number remaining steps",
)

register(
    "scripture_study_bulk_update",
    bulk_update_steps,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
            "steps": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["guide_id", "steps"],
    },
    "Replace all steps of a study guide (deletes existing, inserts new)",
)

register(
    "scripture_study_export_json",
    export_json,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
        },
        "required": ["guide_id"],
    },
    "Export a study guide as JSON with full graph paths",
)

register(
    "scripture_study_export_html",
    export_html,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
        },
        "required": ["guide_id"],
    },
    "Export a study guide as a self-contained HTML page",
)

register(
    "scripture_study_publish",
    publish_study,
    {
        "type": "object",
        "properties": {
            "guide_id": {"type": "integer"},
            "author_name": {"type": "string", "default": "anonymous"},
            "author_id": {"type": "string", "default": ""},
            "forked_from": {"type": "string", "default": ""},
        },
        "required": ["guide_id"],
    },
    "Publish a study as an immutable snapshot with a shareable URL",
)

register(
    "scripture_study_get_published",
    get_published,
    {
        "type": "object",
        "properties": {
            "slug": {"type": "string"},
        },
        "required": ["slug"],
    },
    "Get a published study by its slug",
)

register(
    "scripture_study_list_published",
    list_published,
    {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 20},
            "offset": {"type": "integer", "default": 0},
        },
    },
    "List all published studies",
)

register(
    "scripture_study_fork",
    fork_published,
    {
        "type": "object",
        "properties": {
            "slug": {"type": "string"},
            "created_by": {"type": "string", "default": "user"},
        },
        "required": ["slug"],
    },
    "Fork a published study into a new mutable study guide",
)

register(
    "scripture_study_import_json",
    import_json,
    {
        "type": "object",
        "properties": {
            "json_str": {"type": "string"},
            "created_by": {"type": "string", "default": "user"},
        },
        "required": ["json_str"],
    },
    "Import a study from a JSON string",
)

# ─── Interpretive Disagreements ───

register(
    "scripture_disagreements",
    get_disagreements,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
        },
        "required": ["verse"],
    },
    "Get interpretive disagreements for a verse — contradictory readings across traditions",
)

# ─── Ecumenical Consensus ───

register(
    "scripture_consensus",
    get_consensus,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
        },
        "required": ["verse"],
    },
    "Get ecumenical consensus data for a verse — which traditions engage with it",
)

# ─── Adaptive Assessment Tools ───

register(
    "scripture_assess_start",
    start_assessment,
    {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "default": "default"},
            "target_layer": {"type": "string", "enum": ["pshat", "remez", "drash", "sod"], "default": None},
            "max_items": {"type": "integer", "default": 20},
        },
        "required": [],
    },
    "Start an adaptive assessment session for scripture knowledge",
)

register(
    "scripture_assess_answer",
    submit_answer,
    {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "default": "default"},
            "correct": {"type": "boolean"},
        },
        "required": ["correct"],
    },
    "Submit an answer and get the next question",
)

register(
    "scripture_assess_progress",
    get_progress,
    {
        "type": "object",
        "properties": {
            "user_id": {"type": "string", "default": "default"},
        },
        "required": [],
    },
    "Get current assessment progress",
)

# ─── Source Provenance Tools ───

register(
    "scripture_sources",
    get_sources_for_verse,
    {
        "type": "object",
        "properties": {
            "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
        },
        "required": ["verse"],
    },
    "Get source provenance breakdown for a verse's connections",
)

register(
    "scripture_sources_by_scholar",
    get_sources_by_scholar,
    {
        "type": "object",
        "properties": {
            "scholar_tag": {"type": "string", "description": "Scholar tag (e.g., morales_ascent)"},
            "scholar_name": {"type": "string", "description": "Scholar name (e.g., Margaret Barker)"},
        },
    },
    "Get all connections from a specific scholar",
)

register(
    "scripture_sources_list",
    list_scholars,
    {"type": "object", "properties": {}},
    "List all scholars with connections in the graph",
)

# ─── Conversation Tools ───

register(
    "conversation_create",
    create_session,
    {
        "type": "object",
        "properties": {
            "title": {"type": "string", "default": ""},
            "theme": {"type": "string", "default": ""},
            "created_by": {"type": "string", "default": "anonymous"},
        },
        "required": [],
    },
    "Create a new conversation session for LLM chat",
)

register(
    "conversation_add_message",
    add_message,
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "role": {"type": "string", "enum": ["user", "assistant", "system"]},
            "content": {"type": "string"},
            "metadata": {"type": "object", "default": {}},
        },
        "required": ["session_id", "role", "content"],
    },
    "Add a message to a conversation session (auto-extracts verse refs and detects connections)",
)

register(
    "conversation_list",
    list_sessions,
    {
        "type": "object",
        "properties": {
            "page": {"type": "integer", "default": 1},
            "per_page": {"type": "integer", "default": 20},
            "starred": {"type": "boolean"},
            "search": {"type": "string", "default": ""},
        },
        "required": [],
    },
    "List conversation sessions, paginated",
)

register(
    "conversation_get",
    get_session,
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
        },
        "required": ["session_id"],
    },
    "Get a conversation session with all messages, refs, and connections",
)

register(
    "conversation_delete",
    delete_session,
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
        },
        "required": ["session_id"],
    },
    "Delete a conversation session and all cascade data",
)

register(
    "conversation_list_connections",
    list_connections,
    {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "connection_type": {"type": "string", "enum": ["discovered", "retrieved", "suggested"]},
        },
        "required": ["session_id"],
    },
    "List all connections discovered/retrieved in a conversation session",
)

register(
    "conversation_promote_connection",
    promote_connection,
    {
        "type": "object",
        "properties": {
            "connection_id": {"type": "integer"},
            "layer": {"type": "string", "default": "intertextual"},
            "type_name": {"type": "string", "default": "parallel"},
            "subtype": {"type": "string", "default": ""},
            "strength": {"type": "number", "default": 0.5},
            "confidence": {"type": "number", "default": 0.5},
            "discovered_by": {"type": "string", "default": "conversation"},
        },
        "required": ["connection_id"],
    },
    "Promote a conversation-discovered connection to the main connection graph",
)

# ─── Hebrew Learning Tools ───

def _hebrew_lessons(category=""):
    """List available Hebrew lesson nodes from the Go backend's memorize.db."""
    import sqlite3
    from pathlib import Path
    db = Path(__file__).parent.parent.parent / "data" / "memorize.db"
    if not db.exists():
        return {"lessons": [], "total": 0, "note": "Hebrew lesson DB not found"}
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    if category:
        rows = conn.execute("SELECT id, title, category, level, description FROM hebrew_nodes WHERE category=? ORDER BY level", (category,)).fetchall()
    else:
        rows = conn.execute("SELECT id, title, category, level, description FROM hebrew_nodes ORDER BY level").fetchall()
    conn.close()
    return {"lessons": [dict(r) for r in rows], "total": len(rows)}

def _hebrew_lesson(node_id=""):
    """Get full lesson content for a Hebrew concept node."""
    import sqlite3, json
    from pathlib import Path
    db = Path(__file__).parent.parent.parent / "data" / "memorize.db"
    if not db.exists():
        return {"error": "Hebrew lesson DB not found"}
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    node = conn.execute("SELECT * FROM hebrew_nodes WHERE id=?", (node_id,)).fetchone()
    if not node:
        conn.close()
        return {"error": f"Lesson not found: {node_id}"}
    lesson = conn.execute("SELECT * FROM hebrew_lessons WHERE node_id=?", (node_id,)).fetchone()
    practices = conn.execute("SELECT * FROM hebrew_practice_items WHERE node_id=?", (node_id,)).fetchall()
    prereqs = conn.execute("SELECT n.id,n.title,n.category FROM hebrew_edges e JOIN hebrew_nodes n ON n.id=e.source_id WHERE e.target_id=?", (node_id,)).fetchall()
    conn.close()
    result = dict(node)
    if lesson:
        try:
            result["content"] = json.loads(lesson["content"]) if lesson["content"].startswith("{") else lesson["content"]
        except:
            result["content"] = lesson["content"]
    result["practice_items"] = [dict(p) for p in practices]
    result["prerequisites"] = [dict(p) for p in prereqs]
    return result

register(
    "scripture_hebrew_lessons",
    _hebrew_lessons,
    {
        "type": "object",
        "properties": {
            "category": {"type": "string", "description": "Optional filter: letter, vowel, word, grammar, phrase, reading, root_concept"},
        },
        "required": [],
    },
    "List available Hebrew lesson nodes across 7 categories. Returns 102 lessons covering the full Biblical Hebrew curriculum.",
)

register(
    "scripture_hebrew_lesson",
    _hebrew_lesson,
    {
        "type": "object",
        "properties": {
            "node_id": {"type": "string", "description": "Node ID (e.g., 'aleph', 'bet', 'qal_verb', 'construct_chain')"},
        },
        "required": ["node_id"],
    },
    "Get full lesson content for a Hebrew concept node. Returns explanation, examples, vocabulary, practice items, and prerequisite nodes.",
)

# ─── Export all registered tool names ───

def list_tools():
    """Get all registered tool names and their schemas."""
    return [
        {"name": name, "description": desc, "inputSchema": schema}
        for name, (fn, schema, desc) in TOOL_REGISTRY.items()
    ]


def call_tool(name, conn, **kwargs):
    """Call a registered tool by name with arguments."""
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    fn, _, _ = TOOL_REGISTRY[name]
    return fn(conn, **kwargs)
