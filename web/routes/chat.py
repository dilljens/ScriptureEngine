"""LLM Chat proxy with function calling."""
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.api import call_tool
from lib.api.staging import stage_connection, stage_study
from lib.db import get_db

router = APIRouter()

# ─── LLM Chat Proxy with Function Calling (DeepSeek) ───

DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

# Reusable HTTP client for DeepSeek API calls (avoids creating a new connection each time)
_http_client = httpx.AsyncClient(timeout=600.0)  # 10 min — DeepSeek thinking mode can take 8+ min

# Pricing per 1M tokens (deepseek-v4-flash)
PRICING = {
    "input": 0.14,
    "output": 0.28,
    "cache_hit": 0.07,
}

# Load system prompts by mode
_CHAT_PROMPTS_DIR = BASE_DIR
_CHAT_PROMPT_FILES = {
    "chat": "CHAT_AGENTS.md",
    "hebrew": "CHAT_AGENTS_HEBREW.md",
    "knowledge": "CHAT_AGENTS_KNOWLEDGE.md",
}
CHAT_PROMPTS = {}
for mode, filename in _CHAT_PROMPT_FILES.items():
    path = os.path.join(_CHAT_PROMPTS_DIR, filename)
    if os.path.exists(path):
        with open(path) as f:
            CHAT_PROMPTS[mode] = f.read()
    else:
        CHAT_PROMPTS[mode] = ""

# Default to chat mode
CHAT_SYSTEM_PROMPT = CHAT_PROMPTS.get("chat", "")

# --- Tool definitions ---

# Maps tool names to their function-calling schema for DeepSeek/OpenAI
# Subset of the 42 engine tools that are most useful for scripture study
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "scripture_verse",
            "description": "Look up a verse with text, gematria, connections, and quality info. Works for all 8 works: OT (gen, exo, isa), NT (matt, john, rev), BoM (1ne, alma, 3ne), D&C (dc1-dc138), PGP (moses, abraham), DSS (1QS, 1QHa, 11Q19, CD, 1Qisaa), Apocrypha (wis, sir, tob, 1ma), Pseudepigrapha (1en, jub, ascis, barn, odessol)",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID (gen, exo, isa, matt, 1ne, 1QS, 1en, wis, etc.)"},
                    "chapter": {"type": "integer"},
                    "verse": {"type": "integer"},
                    "version": {"type": "string", "description": "Bible version (WEB, KJV, etc.)"},
                },
                "required": ["book", "chapter", "verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_search",
            "description": "Search for verses by keyword across all 8 works (OT, NT, BoM, D&C, PGP, DSS, Apocrypha, Pseudepigrapha). Returns 25 results by default covering multiple works. Only use book/works filters if you need results from a specific work — otherwise search all works at once.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term (e.g., 'atonement', 'covenant', 'Son of Man')"},
                    "book": {"type": "string", "description": "Optional book filter. Use 'dc' for all D&C sections, '1en' for 1 Enoch, '1QS' for Community Rule. NOT needed for broad searches."},
                    "works": {"type": "array", "items": {"type": "string", "enum": ["ot", "nt", "bom", "dc", "pgp", "dss", "apoc", "pseu", "expanded"]}, "description": "Optional: filter by specific works (e.g., ['ot','nt']). NOT needed for broad searches."},
                    "limit": {"type": "integer", "default": 25, "description": "Results per call (max 50). Default 25 is enough to see results from multiple works."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_passage_guide",
            "description": "Get pre-computed passage guide — all connections, gematria, and quality distribution",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_gematria",
            "description": "Compute gematria for a Hebrew word or look up verses by gematria value",
            "parameters": {
                "type": "object",
                "properties": {
                    "word": {"type": "string", "description": "Hebrew word (e.g., יהוה)"},
                    "value": {"type": "integer", "description": "Look up verses with this gematria value"},
                    "system": {"type": "string", "enum": ["standard", "ordinal", "reduced"], "default": "standard"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_connections",
            "description": "Get all connections for a verse, with layer and quality filtering",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "layer": {"type": "string", "description": "Filter by connection layer"},
                    "min_quality": {"type": "string", "description": "Minimum quality level (pattern, suggested, verified, scholarly)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_intertext",
            "description": "Get intertextual connections — quotations, allusions, echoes",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_pardes",
            "description": "Show connections grouped by PaRDeS level (Pshat, Remez, Drash, Sod)",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                    "level": {"type": "string", "enum": ["pshat", "remez", "drash", "sod"], "description": "Filter to one PaRDeS level"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sod",
            "description": "Explore hidden (Sod-level) patterns — atbash, acrostics, advanced gematria, hidden names",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse to analyze"},
                    "atbash_word": {"type": "string", "description": "Hebrew word to decode via Atbash"},
                    "acrostic_book": {"type": "string", "description": "Book ID to scan for acrostics"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_path",
            "description": "Find the shortest connection path between two verses through the typed graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Starting verse ID (gen.1.1)"},
                    "end": {"type": "string", "description": "Target verse ID"},
                    "max_depth": {"type": "integer", "default": 3, "description": "Maximum path length in hops"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_reachable",
            "description": "Find all verses reachable within N hops from a verse through the connection graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Starting verse ID"},
                    "max_depth": {"type": "integer", "default": 3},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_entities",
            "description": "Get entities (people, places, concepts) linked to a specific verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_shared_entities",
            "description": "Find other verses that share entities (people, places) with this verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_hubs",
            "description": "Find hub verses — those connecting to the most diverse other verses",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_connections": {"type": "integer", "default": 3},
                    "layer": {"type": "string", "description": "Optional layer scope"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources_by_scholar",
            "description": "Get all connections from a specific scholar by tag",
            "parameters": {
                "type": "object",
                "properties": {
                    "scholar_tag": {"type": "string", "description": "Scholar tag (e.g., barker_temple, beale_temple, heiser_council)"},
                    "scholar_name": {"type": "string", "description": "Scholar name (e.g., Margaret Barker)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_strongs",
            "description": "Look up Strong's definition for a Hebrew or Greek word",
            "parameters": {
                "type": "object",
                "properties": {
                    "lemma": {"type": "string", "description": "Strong's number (e.g., H430, G26)"},
                    "word": {"type": "string", "description": "Hebrew or Greek word text"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_interlinear",
            "description": "Get word-by-word interlinear analysis with transliteration, Strong's, morphology",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID"},
                    "chapter": {"type": "integer"},
                    "verse": {"type": "integer"},
                },
                "required": ["book", "chapter", "verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_suggest",
            "description": "Suggest an exploration path from a seed verse through the connection graph",
            "parameters": {
                "type": "object",
                "properties": {
                    "seed_verse": {"type": "string"},
                    "theme": {"type": "string", "description": "Optional theme (e.g., angel_of_yhwh, temple, covenant)"},
                },
                "required": ["seed_verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_info",
            "description": "Get database statistics — total verses, connections per layer, quality distribution",
            "parameters": {"type": "object", "properties": {}},
        },
    },

    # ── Additional search & source tools ──
    {
        "type": "function",
        "function": {
            "name": "scripture_search_xlingual",
            "description": "Search across Hebrew, Greek, AND English simultaneously using entity alignment",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "language": {"type": "string", "enum": ["all", "english", "hebrew", "greek"], "default": "all"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_entity_network",
            "description": "Get all verses connected to a specific entity (person, place, or concept)",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity ID (e.g., 'person.abraham')"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_centrality",
            "description": "Find the most central (best-connected) verses in the graph by degree centrality",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Optional book ID to scope analysis"},
                    "layer": {"type": "string", "description": "Optional layer scope"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_consensus",
            "description": "Get ecumenical consensus data — which traditions engage with this verse",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_disagreements",
            "description": "Get interpretive disagreements — contradictory readings across traditions",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources",
            "description": "Get source provenance breakdown for a verse's connections",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                },
                "required": ["verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_sources_list",
            "description": "List all scholars with connections in the graph",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_verse_text",
            "description": "Get verse text in a specific Bible version",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "version": {"type": "string", "description": "Bible version (WEB, KJV, etc.)", "default": "WEB"},
                },
                "required": ["verse"],
            },
        },
    },

    # ── Study guide tools ──
    {
        "type": "function",
        "function": {
            "name": "scripture_study_create",
            "description": "Create a study guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string", "default": ""},
                    "theme": {"type": "string", "default": ""},
                    "seed_verse": {"type": "string", "default": ""},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_add_step",
            "description": "Add a step to a study guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                    "step_number": {"type": "integer"},
                    "verse_id": {"type": "string"},
                    "title": {"type": "string", "default": ""},
                    "explanation": {"type": "string", "default": ""},
                },
                "required": ["guide_id", "step_number", "verse_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_get",
            "description": "Get a study guide with all its steps",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                },
                "required": ["guide_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_list",
            "description": "List study guides, optionally filtered by theme",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string", "default": ""},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        },
    },

    # ── Staging — propose new data (web UI / LLM → staging table → dev review) ──
    {
        "type": "function",
        "function": {
            "name": "scripture_stage_connection",
            "description": "Propose a new connection between two verses. Goes to staging for dev review before entering the graph.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_verse": {"type": "string", "description": "Source verse ID (gen.1.1)"},
                    "target_verse": {"type": "string", "description": "Target verse ID"},
                    "layer": {"type": "string", "description": "Connection layer"},
                    "type_name": {"type": "string", "description": "Connection type (direct_quotation, allusion, etc.)"},
                    "subtype": {"type": "string", "default": ""},
                    "strength": {"type": "number", "default": 0.5},
                    "confidence": {"type": "number", "default": 0.5},
                    "reasoning": {"type": "string", "default": ""},
                },
                "required": ["source_verse", "target_verse", "layer", "type_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_stage_study",
            "description": "Propose a study guide (goes to staging for dev review before publishing).",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string", "default": ""},
                    "theme": {"type": "string", "default": ""},
                    "seed_verse": {"type": "string", "default": ""},
                    "steps_json": {"type": "string", "description": "JSON array of steps: [{\"step_number\":1, \"verse\":\"gen.1.1\", \"title\":\"...\", \"explanation\":\"...\"}]"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_stats",
            "description": "Get overall connection graph statistics — total connections, unique verses, most-connected hubs, and connection distribution across layers",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_versions",
            "description": "List all available Bible text versions (KJV, WEB, LSV, DSS_HEBREW, FIRMAMENT, SCROLLMAPPER, etc.)",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    # ── Knowledge Assessment ──
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_start",
            "description": "Start an adaptive assessment session for scripture knowledge. Tests understanding of verse connections across all 8 works. Optional: target_layer (pshat/remez/drash/sod) to focus on one layer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": "default"},
                    "target_layer": {"type": "string", "enum": ["pshat", "remez", "drash", "sod"], "default": None},
                    "max_items": {"type": "integer", "default": 20},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_answer",
            "description": "Submit an answer to the current assessment question and get the next one. Call after the user answers a question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": "default"},
                    "correct": {"type": "boolean", "description": "Whether the user's answer was correct"},
                },
                "required": ["correct"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_progress",
            "description": "Get current assessment progress — questions answered, score, remaining items. Shows the assessment status at any point.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "default": "default"},
                },
                "required": [],
            },
        },
    },
    # ── Hebrew Learning ──
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_lessons",
            "description": "List available Hebrew lesson nodes. Optional category filter: letter, vowel, word, grammar, phrase, reading, root_concept. Returns all lessons by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional filter: letter, vowel, word, grammar, phrase, reading, root_concept"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_lesson",
            "description": "Get full lesson content for a Hebrew concept node. Returns explanation, vocabulary, practice items, and prerequisites. Use with a node ID from scripture_hebrew_lessons.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node ID (e.g., 'aleph', 'bet', 'qal_verb', 'construct_chain')"},
                },
                "required": ["node_id"],
            },
        },
    },
    # ── Hebrew Quiz ──
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_quiz",
            "description": "Generate Hebrew knowledge quiz questions. Perfect for practicing letter names (aleph-bet), vowel recognition, and vocabulary.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category: consonant, vowel, word, grammar, phrase, reading (default: consonant for aleph-bet practice)"},
                    "count": {"type": "integer", "default": 5, "description": "Number of questions to generate"},
                },
                "required": [],
            },
        },
    },
    # ── Compare & Research ──
    {
        "type": "function",
        "function": {
            "name": "scripture_compare",
            "description": "Compare two verses — shortest connection path, shared entities, overlapping connection types, side-by-side text, and PaRDeS level summary in ONE call",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse_a": {"type": "string", "description": "First verse ID (gen.1.1)"},
                    "verse_b": {"type": "string", "description": "Second verse ID (john.1.1)"},
                    "max_path_depth": {"type": "integer", "default": 4, "description": "Max path length in hops"},
                },
                "required": ["verse_a", "verse_b"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_research",
            "description": "Multi-hop thematic research — walk the connection graph from a seed verse, collect all connected verses with texts and paths, return structured research brief. Essential for tracing themes across the canon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "seed_verse": {"type": "string", "description": "Starting verse ID (gen.1.1)"},
                    "theme": {"type": "string", "description": "Optional theme description"},
                    "max_depth": {"type": "integer", "default": 3, "description": "Max hops to traverse"},
                    "layers": {"type": "array", "items": {"type": "string"}, "description": "Optional layer filter"},
                    "max_verses": {"type": "integer", "default": 30, "description": "Max verses to collect"},
                },
                "required": ["seed_verse"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_verse",
            "description": "Complete verse study package — verse text + all connections + gematria + entities + sources + quality + 1-hop reachable verses in ONE call. Replaces scripture_verse + scripture_connections + scripture_gematria + scripture_graph_entities + scripture_sources + scripture_graph_reachable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "max_reachable": {"type": "integer", "default": 10, "description": "Max 1-hop neighbor verses to include"},
                },
                "required": ["verse"],
            },
        },
    },
    # ── Entity Deep Dive ──
    {
        "type": "function",
        "function": {
            "name": "scripture_entity_deep",
            "description": "Deep dive on a biblical entity — all verses mentioning it, all connections between those verses, and related entities that co-occur",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Entity ID (person.abraham, place.zion, concept.covenant)"},
                    "min_confidence": {"type": "number", "default": 0.3},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["entity"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_entity_cooccurrence",
            "description": "Find entities that frequently co-occur with a given entity in the same verse.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entity_id": {"type": "string", "description": "Entity ID (person.abraham)"},
                    "limit": {"type": "integer", "default": 20, "description": "Max results"},
                },
                "required": ["entity_id"],
            },
        },
    },
    # ── Semantic Search ──
    {
        "type": "function",
        "function": {
            "name": "scripture_semantic_search",
            "description": "Hybrid semantic search — uses transformer embeddings (multilingual, Hebrew/Greek/English) fused with BM25. Finds verses by meaning, not just keywords.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (auto-detects verse refs, Hebrew, Greek, natural language)"},
                    "limit": {"type": "integer", "default": 20, "description": "Max results"},
                    "mode": {"type": "string", "enum": ["hybrid", "vector", "keyword"], "default": "hybrid", "description": "Search mode: hybrid (RRF fusion), vector (pure semantic), keyword (pure BM25)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_similar_verses",
            "description": "Find verses similar to a given verse using pre-computed entity + connection overlap.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse_id": {"type": "string", "description": "Verse ID (gen.1.1)"},
                    "limit": {"type": "integer", "default": 20, "description": "Max results"},
                    "min_score": {"type": "number", "default": 0.1, "description": "Minimum similarity score (0-1)"},
                },
                "required": ["verse_id"],
            },
        },
    },
    # ── Graph Context (structured LLM context) ──
    {
        "type": "function",
        "function": {
            "name": "scripture_graph_context",
            "description": "Get N-hop neighborhood as structured text for LLM reasoning — verse text + typed relationships with strength/confidence in readable format",
            "parameters": {
                "type": "object",
                "properties": {
                    "verse": {"type": "string", "description": "Starting verse ID (gen.1.1)"},
                    "depth": {"type": "integer", "default": 2, "description": "How many hops to traverse"},
                    "layers": {"type": "array", "items": {"type": "string"}, "description": "Optional layer filter"},
                    "limit": {"type": "integer", "default": 20, "description": "Max verses to include"},
                },
                "required": ["verse"],
            },
        },
    },
    # ── Study Guide CRUD (expanded) ──
    {
        "type": "function",
        "function": {
            "name": "scripture_study_remove_step",
            "description": "Remove a step from a study guide and re-number remaining steps",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                    "step_number": {"type": "integer"},
                },
                "required": ["guide_id", "step_number"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_bulk_update",
            "description": "Replace all steps of a study guide (deletes existing, inserts new)",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                    "steps": {"type": "array", "items": {"type": "object"}, "description": "Array of step objects with verse_id, title, explanation"},
                },
                "required": ["guide_id", "steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_publish",
            "description": "Publish a study as an immutable snapshot with a shareable URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                    "author_name": {"type": "string", "default": "anonymous"},
                    "author_id": {"type": "string", "default": ""},
                    "forked_from": {"type": "string", "default": ""},
                },
                "required": ["guide_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_get_published",
            "description": "Get a published study by its slug",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_list_published",
            "description": "List all published studies",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_fork",
            "description": "Fork a published study into a new mutable study guide",
            "parameters": {
                "type": "object",
                "properties": {
                    "slug": {"type": "string"},
                    "created_by": {"type": "string", "default": "user"},
                },
                "required": ["slug"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_import_json",
            "description": "Import a study from a JSON string",
            "parameters": {
                "type": "object",
                "properties": {
                    "json_str": {"type": "string", "description": "Full study JSON string"},
                    "created_by": {"type": "string", "default": "user"},
                },
                "required": ["json_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_export_json",
            "description": "Export a study guide as JSON with full graph paths",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                },
                "required": ["guide_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_study_export_html",
            "description": "Export a study guide as a self-contained HTML page",
            "parameters": {
                "type": "object",
                "properties": {
                    "guide_id": {"type": "integer"},
                },
                "required": ["guide_id"],
            },
        },
    },
    # ── Conversation Management ──
    {
        "type": "function",
        "function": {
            "name": "scripture_conversation_create",
            "description": "Create a new conversation session for LLM chat",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "default": ""},
                    "theme": {"type": "string", "default": ""},
                    "created_by": {"type": "string", "default": "anonymous"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_conversation_get",
            "description": "Get a conversation session with all messages, refs, and connections",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                },
                "required": ["session_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_conversation_list",
            "description": "List conversation sessions, paginated",
            "parameters": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer", "default": 1},
                    "per_page": {"type": "integer", "default": 20},
                    "starred": {"type": "boolean"},
                    "search": {"type": "string", "default": ""},
                },
                "required": [],
            },
        },
    },
]

# ── Staging tool names (recognized by the chat handler) ──
STAGING_TOOLS = {"scripture_stage_connection", "scripture_stage_study"}


def _compute_cost(usage: dict) -> dict:
    """Estimate cost from DeepSeek usage response."""
    p_in = usage.get("prompt_tokens", 0)
    p_out = usage.get("completion_tokens", 0)
    cache_hit = usage.get("prompt_cache_hit_tokens", 0)
    cost_input = p_in * PRICING["input"] / 1_000_000
    cost_output = p_out * PRICING["output"] / 1_000_000
    cost_cache = cache_hit * PRICING["cache_hit"] / 1_000_000
    return {
        "total": round(cost_input + cost_output - cost_cache, 6),
        "input": round(cost_input, 6),
        "output": round(cost_output, 6),
        "cache_saved": round(cost_cache, 6),
    }


class ChatRequest(BaseModel):
    messages: list[dict]
    model: str = DEEPSEEK_MODEL
    max_tokens: int = 4096
    temperature: float = 0.7
    tools_enabled: bool = True
    disabled_tools: list[str] = []
    mode: str = "chat"  # "chat", "hebrew", "knowledge"


@router.get("/api/v1/chat/instructions")
def chat_instructions():
    """Return the AGENTS-style system prompt and tool definitions for the chat LLM."""
    return {
        "ok": True,
        "data": {
            "system_prompt": CHAT_SYSTEM_PROMPT,
            "tools": TOOL_DEFINITIONS,
            "model": DEEPSEEK_MODEL,
            "pricing": PRICING,
        },
    }


@router.post("/api/v1/chat")
async def llm_chat(body: ChatRequest):
    """Proxy chat requests to DeepSeek API with function calling support.

    If the LLM requests a tool call, the server executes it against the
    scripture engine and feeds the result back to the LLM for a final response.
    """
    if not DEEPSEEK_API_KEY:
        return {"ok": False, "error": "DEEPSEEK_API_KEY not configured"}

    # from lib.api import call_tool, list_tools
    # from lib.api.staging import stage_connection, stage_study
    # from lib.db import get_db

    # Build messages with system prompt (mode-specific)
    msgs = list(body.messages)
    prompt = CHAT_PROMPTS.get(body.mode, CHAT_SYSTEM_PROMPT)
    if prompt:
        if not any(m.get("role") == "system" for m in msgs):
            msgs.insert(0, {"role": "system", "content": prompt})
        else:
            # Replace existing system prompt with mode-specific one
            for i, m in enumerate(msgs):
                if m.get("role") == "system":
                    msgs[i] = {"role": "system", "content": prompt}
                    break

    # Context budget management
    # Total budget: 300K tokens. max_tokens capped at 128K. Compaction trigger at 200K prompt tokens.
    MAX_PROMPT_TOKENS = 200_000
    KEEP_EXCHANGES = 15  # user+assistant pairs to keep before compaction
    body.max_tokens = min(body.max_tokens, 128_000)

    def estimate_tokens(text):
        return len(text) // 4  # rough estimate: ~4 chars per token

    def apply_context_budget(message_list):
        """Trim message list to stay within budget. Strips tool traces first,
        then keeps only the last KEEP_EXCHANGES user+assistant exchanges."""
        total_est = sum(estimate_tokens(m.get("content", "") or "") for m in message_list)
        if total_est <= MAX_PROMPT_TOKENS:
            return message_list

        # 1. Strip tool traces from messages older than the last KEEP_EXCHANGES exchanges
        system = [m for m in message_list if m["role"] == "system"]
        exchanges = [m for m in message_list if m["role"] != "system"]

        # Count exchanges (user+assistant pairs)
        exchange_count = 0
        keep_from = len(exchanges)
        for i in range(len(exchanges) - 1, -1, -1):
            if exchanges[i]["role"] == "user":
                exchange_count += 1
                if exchange_count > KEEP_EXCHANGES:
                    keep_from = i
                    break

        before = exchanges[:keep_from]
        after = exchanges[keep_from:]

        # Strip tool-related messages from the 'before' portion
        cleaned_before = [m for m in before if m["role"] in ("user", "assistant") and m.get("content")]
        cleaned_all = cleaned_before + after
        total_est = sum(estimate_tokens(m.get("content", "") or "") for m in cleaned_all)

        if total_est <= MAX_PROMPT_TOKENS:
            return system + cleaned_all

        # 2. Still over budget: keep only the most recent KEEP_EXCHANGES exchanges
        if exchange_count > KEEP_EXCHANGES:
            # Take the last KEEP_EXCHANGES exchanges from the 'after' portion
            final_after = after
            if len(exchanges) > KEEP_EXCHANGES * 2:
                final_after = exchanges[-(KEEP_EXCHANGES * 2):]
            else:
                final_after = exchanges[-(KEEP_EXCHANGES * 2):]
            system.append({
                "role": "system",
                "content": "[Earlier conversation context omitted to stay within token budget.]"
            })
            return system + final_after

        return system + after

    msgs = apply_context_budget(msgs)

    # Prepare request payload (no explicit thinking flags — let DeepSeek use own defaults
    # like OpenCode does. No thinking/reasoning_effort forcing means the model naturally
    # balances its token budget between thinking and visible response.)
    payload = {
        "model": body.model,
        "messages": msgs,
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
    }
    if body.tools_enabled:
        # Filter out disabled tools
        if body.disabled_tools:
            payload["tools"] = [t for t in TOOL_DEFINITIONS
                                if t["function"]["name"] not in body.disabled_tools]
        else:
            payload["tools"] = TOOL_DEFINITIONS
        payload["tool_choice"] = "auto"

    tool_results = []
    max_tool_rounds = 15  # prevent infinite loops; 10 was too low for multi-work searches

    async def call_deepseek(req_payload):
        global _http_client
        resp = await _http_client.post(
            f"{DEEPSEEK_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json=req_payload,
        )
        return resp.json()

    data = await call_deepseek(payload)

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        friendly_map = {
            400: "Invalid request format.",
            401: "API key issue — contact the repo maintainer.",
            429: "Rate limited — please wait a moment.",
            500: "DeepSeek server error. Try again.",
        }
        msg = err.get("message", str(err))
        friendly = friendly_map.get(code, "")
        return {"ok": False, "error": f"{friendly} [{msg}]" if friendly else msg}

    rounds = 0
    while data.get("choices") and rounds < max_tool_rounds:
        choice = data["choices"][0]
        msg = choice.get("message", {})

        # Check for tool calls
        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            break  # No more tool calls, we have final response

        # Execute each tool call
        # First, add the assistant's tool_calls message once (DeepSeek requires this order)
        msgs.append(msg)
        conn = get_db()

        # Separate staging (write) tools from read-only tools
        staging_calls = [tc for tc in tool_calls if tc["function"]["name"] in STAGING_TOOLS]
        ro_calls = [tc for tc in tool_calls if tc["function"]["name"] not in STAGING_TOOLS]

        # Run read-only tools in parallel
        async def run_ro(tc, conn=conn):
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            try:
                return tc, call_tool(fn_name, conn, **fn_args)
            except Exception as e:
                return tc, {"error": str(e)}

        ro_results = []
        if ro_calls:
            ro_results = await asyncio.gather(*[run_ro(tc) for tc in ro_calls])

        # Run staging tools sequentially (they write to DB)
        staging_results = []
        for tc in staging_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            try:
                if fn_name == "scripture_stage_connection":
                    result = stage_connection(conn, submitted_by="llm", **fn_args)
                elif fn_name == "scripture_stage_study":
                    steps = json.loads(fn_args.pop("steps_json", "[]"))
                    result = stage_study(conn, steps=steps, submitted_by="llm", **fn_args)
                else:
                    result = {"error": f"Unknown staging tool: {fn_name}"}
            except Exception as e:
                result = {"error": str(e)}
            staging_results.append((tc, result))

        # Combine all results
        all_results = ro_results + staging_results
        for tc, result in all_results:

            # Truncate large results to avoid overflowing context
            result_str = json.dumps(result, default=str, ensure_ascii=False)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + '..." [truncated]'

            # Also truncate the tool_result sent to frontend (saves context bandwidth + metadata bloat)
            tool_result_data = result
            if len(json.dumps(tool_result_data, default=str, ensure_ascii=False)) > 3000:
                import copy
                trunced = copy.copy(result) if isinstance(result, dict) else result
                if isinstance(trunced, dict):
                    # Return truncated instead of the full result
                    tool_result_data = {"_truncated": True, "data_preview": result_str[:500]}
                else:
                    tool_result_data = {"_truncated": True, "data_preview": result_str[:500]}
            tool_results.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"]),
                "result": tool_result_data,
            })

            # Add tool result message (one per tool call, with matching call_id)
            msgs.append({
                "role": "tool",
                "content": result_str,
                "tool_call_id": tc["id"],
            })

        conn.close()

        # Apply budget check only when approaching the limit (saves scanning all messages)
        est = sum(len(m.get("content", "") or "") // 4 for m in msgs)
        if est > MAX_PROMPT_TOKENS * 0.8:
            msgs = apply_context_budget(msgs)

        # Call DeepSeek again with tool results
        payload["messages"] = msgs
        data = await call_deepseek(payload)

        if "error" in data:
            err = data["error"]
            msg = err.get("message", str(err))
            return {"ok": False, "error": f"DeepSeek API error: {msg}"}

        rounds += 1

    # Final response
    usage = data.get("usage", {})
    choice = data["choices"][0] if data.get("choices") else None
    if not choice:
        return {"ok": False, "error": "No response from LLM"}

    final_content = choice["message"]["content"] or choice["message"].get("reasoning_content") or ""
    final_reasoning = choice["message"].get("reasoning_content")

    # If LLM only made tool calls without summarizing, force a summary
    # Also force summary if the content is just planning text (starts with "Let me")
    is_planning = final_content.strip()[:20].lstrip().startswith("Let me")
    if (not final_content or is_planning) and tool_results:
        msgs.append({"role": "user", "content":
            "You have all the data you need from the tool calls above. "
            "Now synthesize a complete answer in natural language based on the information you found. "
            "Cite the specific verses and data you found. "
            "Use full book names like 'Genesis 1:1'. "
            "Do not list the tools you used."})
        retry = await call_deepseek({
            "model": body.model, "messages": msgs,
            "max_tokens": body.max_tokens, "temperature": body.temperature,
        })
        if retry.get("choices"):
            rc_msg = retry["choices"][0].get("message", {})
            if rc_msg.get("content") or rc_msg.get("reasoning_content"):
                final_content = rc_msg["content"] or rc_msg.get("reasoning_content") or ""
                final_reasoning = rc_msg.get("reasoning_content") or final_reasoning
            # Merge usage from the retry call
            retry_usage = retry.get("usage", {})
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens"):
                if retry_usage.get(k):
                    usage[k] = usage.get(k, 0) + retry_usage[k]

    cost = _compute_cost(usage)

    return {
        "ok": True,
        "data": {
            "content": final_content,
            "reasoning_content": final_reasoning,
            "model": data.get("model", body.model),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
                "cache_hit_tokens": usage.get("prompt_cache_hit_tokens", 0),
            },
            "cost": cost,
            "tool_results": tool_results,
        },
    }


