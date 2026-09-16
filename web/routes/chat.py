"""LLM Chat proxy with function calling."""
import asyncio
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.api import call_tool
from lib.api.staging import stage_connection, stage_study
from lib.chat_cache import tool_cache
from lib.db import get_db
from web.lib import jobs as _jobs
from web.lib.llm_provider import ProviderRouter
from web.lib import subagents as _subagents

router = APIRouter()

logger = logging.getLogger("chat")

# ─── LLM Chat Proxy with Function Calling ───

DEEPSEEK_API_KEY: str = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")
_llm_provider = ProviderRouter()
_INTERACTIVE_MARKER_RE = re.compile(r"%%%(?:QUIZ|HEBREW_QUIZ):.*?%%%", re.DOTALL)

# Reusable HTTP client for DeepSeek API calls (avoids creating a new connection each time)
_http_client = httpx.AsyncClient(timeout=600.0)  # 10 min — DeepSeek thinking mode can take 8+ min

# Pricing per 1M tokens. OpenCode Go is subscription-backed by default, so its
# accounting values are zero unless an operator supplies internal prices.
PRICING = _llm_provider.pricing(DEEPSEEK_MODEL)

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
            "name": "scripture_batch_lookup",
            "description": "Look up MANY verses in ONE call — pass a list of refs (e.g. ['gen.1.1', 'john.1.1', 'isa.6.1']) and get all their text/gematria/connections at once. ALWAYS prefer this over calling scripture_verse repeatedly for multiple verses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "verses": {"type": "array", "items": {"type": "string"},
                               "description": "Verse refs like 'gen.1.1', 'john.3.16' (max 50)"},
                    "version": {"type": "string", "description": "Preferred Bible version (WEB, KJV, etc.)"},
                },
                "required": ["verses"],
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
            "name": "scripture_passage_connections",
            "description": "Get PASSAGE-LEVEL connections for a verse range (chunks, chapters, books) — the bigger picture beyond single verses. Pass the range of the passage you're studying (e.g. start 'gen.1.1' end 'gen.1.31' for the chapter). Returns chapter↔chapter, chunk↔chapter, and chapter↔book connections with granularity labels.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start": {"type": "string", "description": "Start verse ID (e.g. 'gen.1.1')"},
                    "end": {"type": "string", "description": "End verse ID (e.g. 'gen.1.31')"},
                    "min_density": {"type": "number", "description": "Minimum density filter (0-1)"},
                },
                "required": ["start", "end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_chapter_connections",
            "description": "Get ALL connections for a whole CHAPTER — passage-level connections to other chapters/books plus verse-level connection count. Use when the user asks about an entire chapter's relationships. Returns chapter-level connections with granularity (chunk/chapter/book).",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID (e.g. 'gen', 'isa')"},
                    "chapter": {"type": "integer", "description": "Chapter number"},
                },
                "required": ["book", "chapter"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_book_connections",
            "description": "Get BOOK-LEVEL connection summary — which whole books this book connects to (book↔book connections), with layer distribution. Use for big-picture questions like 'how does Genesis connect to Revelation' or 'what books parallel Isaiah'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "book": {"type": "string", "description": "Book ID (e.g. 'gen', 'isa')"},
                },
                "required": ["book"],
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
    # ── Compare & Research ──
    {
        "type": "function",
        "function": {
            "name": "scripture_compare",
            "description": "**PREFERRED for comparing verses.** Returns verse text, connections, graph path, entities, PaRDeS levels, AND gematria for BOTH verses in ONE call. Replaces scripture_verse + scripture_passage_guide + scripture_graph_path + scripture_interlinear + scripture_gematria (7+ individual calls). Use this instead of calling individual tools for comparisons.",
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
            "name": "scripture_research_parallel",
            "description": "DEEP PARALLEL RESEARCH — breaks the query into independent sub-tasks, runs them concurrently, and returns merged findings in ONE call. Use for broad research questions spanning multiple topics/books that would otherwise need many sequential lookups. Slower than a single lookup but much faster than doing the work serially.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The research question to parallelize (e.g. 'trace atonement imagery from Leviticus through Hebrews')"},
                },
                "required": ["query"],
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
    # ── Truth Alignment Tools ──
    {
        "type": "function",
        "function": {
            "name": "scripture_truth_check",
            "description": "Evaluate a scholarly claim against scripture using the connection graph. Returns supports/contradicts/neutral with confidence score and evidence. Use this when a user asks whether a scholar's claim aligns with what scripture actually says.",
            "parameters": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "The scholarly claim to evaluate (e.g., 'The Angel of YHWH is a created being')"},
                    "verses": {"type": "array", "items": {"type": "string"}, "description": "Verse references the claim relates to (e.g., ['gen.16.7', 'exo.3.2'])"},
                    "claim_type": {"type": "string", "enum": ["linguistic", "historical", "theological", "textual", "interpretive"], "description": "Optional claim type override"},
                },
                "required": ["claim"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_truth_topic",
            "description": "Run truth check on all scholarly claims for a topic. Topics: temple_microcosm (Beale), angel_yhwh_divine_council (Heiser/Barker), josiah_reform, queen_of_heaven_asherah (Dever), two_yahwehs_origins (Barker/Bauckham), atonement_theosis (Barker), bom_temple (Butler).",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "enum": ["temple_microcosm", "angel_yhwh_divine_council", "josiah_reform", "queen_of_heaven_asherah", "two_yahwehs_origins", "atonement_theosis", "bom_temple"], "description": "Topic to analyze"},
                },
                "required": ["topic"],
            },
        },
    },
    # ── Opt-in scope-gated tools (Come Follow Me / General Conference) ──
    # Schemas live here, but _filter_tools drops them unless the request
    # declares the matching scope in ChatRequest.scopes.
    {
        "type": "function",
        "function": {
            "name": "scripture_cfm_lesson",
            "description": "Look up a Come Follow Me weekly lesson (LDS curriculum). Returns the lesson's date range, title, scripture block, and full text. With no arguments returns the current week's lesson.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Manual year (default: current year)"},
                    "week": {"type": "string", "description": "Week slug, e.g. '03' (default: current calendar week)"},
                    "ref_id": {"type": "string", "description": "Exact ref, e.g. 'cfm.2026.03'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_conference_talk",
            "description": "Look up a General Conference talk transcript. Filter by year/month/session/speaker/title, or pass ref_id for an exact hit. Returns speaker, session, title, and full text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "year": {"type": "integer", "description": "Conference year, e.g. 2025"},
                    "month": {"type": "integer", "description": "Conference month: 4 (April) or 10 (October)"},
                    "session": {"type": "string", "description": "Session name, e.g. 'Saturday Morning'"},
                    "speaker": {"type": "string", "description": "Speaker name (substring match), e.g. 'Holland'"},
                    "title": {"type": "string", "description": "Talk title (substring match)"},
                    "ref_id": {"type": "string", "description": "Exact ref, e.g. 'gc.2025.04.13holland'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_cfm_search",
            "description": "Search the Come Follow Me lessons and General Conference talks corpora. Returns ranked matches with snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search term"},
                    "corpus": {"type": "string", "enum": ["cfm", "conference", "both"], "default": "both", "description": "Which corpus to search"},
                    "year": {"type": "integer", "description": "Optional year filter"},
                    "limit": {"type": "integer", "default": 10, "description": "Max results (max 30)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_quiz_progress",
            "description": "See a user's multiple-choice question results: mastery by PaRDeS layer, IRT ability estimate, and their most recent answers. Use when the user has answered quiz/MC questions in the app or in chat and you need to know what they got right or wrong, what's weak, or how they're trending. The user_id defaults to the person chatting — omit it unless you have a specific reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "limit": {"type": "integer", "default": 10, "description": "How many recent answers to include"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_progress",
            "description": "See a user's Biblical Hebrew learning progress: mastery per category (consonants, vowels, words, grammar...), due review items, XP/streak, and placement/diagnostic results. Use whenever the user asks about Hebrew, their Hebrew progress, what to study next, or how they're doing in the Hebrew course. The user_id defaults to the person chatting — omit it unless you have a specific reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "limit": {"type": "integer", "default": 10, "description": "How many practiced/due nodes to include"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_placement",
            "description": "See where a user placed on the Hebrew placement test (per-skill 1-up-3-down staircase results: alphabet, vocab, grammar, reading) and whether they've taken it. Use to recommend where the user should start in the Hebrew course. The user_id defaults to the person chatting — omit it unless you have a specific reason.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_lessons",
            "description": "List available Hebrew lesson nodes across categories (consonant, vowel, word, grammar, phrase, reading, root). Returns the full lesson catalog.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Optional category filter"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_lesson",
            "description": "Get full lesson content for a Hebrew concept node: explanation, examples, vocabulary, practice items, and prerequisites.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node ID (e.g. 'aleph', 'bet', 'qal_verb', 'construct_chain')"},
                },
                "required": ["node_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_hebrew_quiz",
            "description": "Generate Hebrew knowledge quiz questions (consonants, vowels, vocabulary, grammar). Perfect for practicing aleph-bet or vocab in chat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Category: consonant, vowel, word, grammar, phrase, reading"},
                    "count": {"type": "integer", "default": 5, "description": "Number of questions"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_start",
            "description": "Start an adaptive assessment session for scripture knowledge (BLIM/IRT, PaRDeS-layer aware). Returns the first question. The user_id defaults to the person chatting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "target_layer": {"type": "string", "enum": ["pshat", "remez", "drash", "sod"], "description": "Optional PaRDeS layer filter"},
                    "max_items": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_answer",
            "description": "Submit the selected option, index, or free-text answer to the active adaptive assessment and get the next question. Grading is server-authoritative.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "answer": {"description": "Selected option, option index, or free-text answer"},
                },
                "required": ["answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_assess_progress",
            "description": "Get a user's adaptive assessment progress (mastery by layer, outer fringe, items answered) without submitting an answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_diagnostic_start",
            "description": "Start a broad pre-assessment diagnostic across all layers — finds what the user already knows vs needs to learn. Samples widely, stops per-topic once confident. Use before recommending a study path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "max_items": {"type": "integer", "default": 30},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_diagnostic_answer",
            "description": "Submit a diagnostic answer with conditional completion; returns the diagnostic report when complete.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                    "answer": {"description": "Selected option, option index, or free-text answer"},
                },
                "required": ["answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scripture_diagnostic_report",
            "description": "Get a user's diagnostic report (what they know / don't know by connection type and PaRDeS layer) without running a new assessment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User id (defaults to the chatting user)"},
                },
            },
        },
    },
]

# ── Staging tool names (recognized by the chat handler) ──
STAGING_TOOLS = {"scripture_stage_connection", "scripture_stage_study"}

# ─── Opt-in scoped tools (Come Follow Me / General Conference) ───
# These tools read the CFM/GC prose corpora. They are ONLY advertised to the
# LLM (and callable) when the request declares the matching scope — so the
# feature is off by default and a raw API caller must explicitly opt in.
# The frontend sets scopes from the Search Scope checkboxes.
SCOPED_TOOLS = {
    "scripture_cfm_lesson": ("cfm",),
    "scripture_conference_talk": ("conference",),
    "scripture_cfm_search": ("cfm", "conference"),  # searches both corpora
}

# General Scripture chat is intentionally not a learning/progress surface.
# Keep these definitions registered for the dedicated Hebrew/Learn routes, but
# never advertise or execute them from the general chat mode.
GENERAL_CHAT_BLOCKED_TOOLS = frozenset({
    "scripture_quiz_progress",
    "scripture_hebrew_progress",
    "scripture_hebrew_placement",
    "scripture_hebrew_lessons",
    "scripture_hebrew_lesson",
    "scripture_hebrew_quiz",
    "scripture_assess_start",
    "scripture_assess_answer",
    "scripture_assess_progress",
    "scripture_diagnostic_start",
    "scripture_diagnostic_answer",
    "scripture_diagnostic_report",
})

# Hebrew Tutor gets only language-learning/reference tools.  In particular,
# it cannot stage studies or invoke the general Scripture assessment system.
HEBREW_TOOL_ALLOWLIST = frozenset({
    "scripture_verse",
    "scripture_search",
    "scripture_search_xlingual",
    "scripture_gematria",
    "scripture_interlinear",
    "scripture_strongs",
    "scripture_hebrew_progress",
    "scripture_hebrew_placement",
    "scripture_hebrew_lessons",
    "scripture_hebrew_lesson",
    "scripture_hebrew_quiz",
    "scripture_quiz_progress",
})


def _scope_allowed(tool_name: str, scopes: list) -> bool:
    allowed = SCOPED_TOOLS.get(tool_name)
    if allowed is None:
        return True  # not a scoped tool — always allowed
    s = set(scopes or [])
    return any(x in s for x in allowed)


# Tools that take a `user_id` arg — the server injects the chatting user's id
# when the LLM doesn't pass one explicitly.
_USER_TOOLS = {
    "scripture_quiz_progress",
    "scripture_hebrew_progress",
    "scripture_hebrew_placement",
    "scripture_assess_start",
    "scripture_assess_answer",
    "scripture_assess_progress",
    "scripture_diagnostic_start",
    "scripture_diagnostic_answer",
    "scripture_diagnostic_report",
}


def _tool_accepts_user_id(tool_name: str) -> bool:
    return tool_name in _USER_TOOLS


def _mode_allowed(tool_name: str, mode: str = "chat") -> bool:
    """Enforce the mode boundary before tools reach the model or executor."""
    if mode == "hebrew":
        return tool_name in HEBREW_TOOL_ALLOWLIST
    if mode in ("chat", "knowledge"):
        return tool_name not in GENERAL_CHAT_BLOCKED_TOOLS
    # Unknown modes should fail closed rather than inherit general privileges.
    return False


def _filter_tools(tools: list, scopes: list, disabled_tools: list, mode: str = "chat") -> list:
    """Drop disabled, scoped, and mode-incompatible tools."""
    disabled = set(disabled_tools or [])
    return [t for t in tools
            if t["function"]["name"] not in disabled
            and _scope_allowed(t["function"]["name"], scopes)
            and _mode_allowed(t["function"]["name"], mode)]


def _effective_mode(mode: str) -> str:
    """Only general chat and Hebrew Tutor are interactive chat modes."""
    return "hebrew" if mode == "hebrew" else "chat"


# ─── Hebrew Tutor learner-state hydration (Track C1) ──────────────────
# Each Hebrew-mode turn gets a compact, deterministic progress snapshot so
# the tutor adapts to the real learner without reading the whole database.
# General chat never receives this context.

_SNAPSHOT_MAX_CATEGORIES = 6
_SNAPSHOT_MAX_DUE = 3
_SNAPSHOT_MAX_RECENT = 5


def _hebrew_learner_snapshot(user_id: str) -> str | None:
    """Build a bounded learner-progress block for the Hebrew Tutor mode.

    Returns None when there is no progress data (new learner) or on any
    failure — hydration must never break the chat request.
    """
    try:
        from lib.api.progress import hebrew_progress

        data = hebrew_progress(None, user_id=user_id, limit=_SNAPSHOT_MAX_RECENT)
    except Exception:
        return None
    if not isinstance(data, dict) or not data.get("ok") or not data.get("has_progress"):
        return None

    lines = ["[LEARNER PROGRESS SNAPSHOT · server-derived · read-only]"]

    placement = data.get("placement") or {}
    levels = placement.get("level_estimates") if isinstance(placement, dict) else None
    if isinstance(levels, dict) and levels:
        parts = [
            f"{skill} L{lvl}"
            for skill, lvl in list(levels.items())[:4]
        ]
        lines.append("Placement: " + ", ".join(parts))

    cats = data.get("by_category") or []
    cat_parts = []
    for c in cats[:_SNAPSHOT_MAX_CATEGORIES]:
        total = c.get("total", 0) or 0
        mastered = c.get("mastered", 0) or 0
        avg = int(round((c.get("avg_mastery", 0) or 0) * 100))
        cat_parts.append(f"{c.get('category', '?')} {avg}% ({mastered}/{total} mastered)")
    if cat_parts:
        lines.append("Mastery by category: " + "; ".join(cat_parts))

    due = data.get("due_reviews") or {}
    due_count = due.get("count", 0) or 0
    if due_count:
        next_items = ", ".join(
            i.get("title", i.get("node_id", "?"))
            for i in (due.get("next_items") or [])[:_SNAPSHOT_MAX_DUE]
        )
        lines.append(f"Due reviews: {due_count} item(s)" + (f" — next: {next_items}" if next_items else ""))

    practiced = data.get("practiced_nodes") or []
    recent = [p.get("title", p.get("node_id", "?")) for p in practiced[:_SNAPSHOT_MAX_RECENT]]
    if recent:
        lines.append("Recent practice: " + ", ".join(recent))

    gam = data.get("gamification")
    if isinstance(gam, dict):
        xp = gam.get("xp")
        streak = gam.get("streak_count")
        bits = []
        if xp is not None:
            bits.append(f"XP {xp}")
        if streak is not None:
            bits.append(f"streak {streak}d")
        if bits:
            lines.append(" · ".join(bits))

    lines.append(
        "[End snapshot — teach within this level; never invent or exceed "
        "recorded progress. For anything not listed, ask the learner.]"
    )
    return "\n".join(lines)


def _prepare_chat_messages(body) -> list[dict]:
    """Assemble the outbound message list for every chat endpoint:

    mode-specific system prompt → Hebrew learner snapshot (hebrew mode only,
    bound server-side identity only) → context budget. Shared by llm_chat,
    llm_chat_stream, and the background job runner so all paths hydrate
    identically.
    """
    msgs = list(body.messages)
    prompt = CHAT_PROMPTS.get(_effective_mode(body.mode), CHAT_SYSTEM_PROMPT)
    if prompt:
        if not any(m.get("role") == "system" for m in msgs):
            msgs.insert(0, {"role": "system", "content": prompt})
        else:
            # Replace existing system prompt with mode-specific one
            for i, m in enumerate(msgs):
                if m.get("role") == "system":
                    msgs[i] = {"role": "system", "content": prompt}
                    break

    # Hebrew Tutor hydration — compact learner state, bound identity only.
    # Never injected for general chat; never from client-supplied ids.
    if _effective_mode(body.mode) == "hebrew":
        snapshot = _hebrew_learner_snapshot(_chat_tool_user_id(body))
        if snapshot:
            msgs.insert(1, {"role": "system", "content": snapshot})

    body.max_tokens = min(body.max_tokens, MAX_OUTPUT_TOKENS)
    return apply_context_budget(msgs)


def _sanitize_chat_content(content: str, mode: str) -> str:
    """Prevent quiz cards from leaking into general chat output."""
    if _effective_mode(mode) != "chat" or not content:
        return content
    return _INTERACTIVE_MARKER_RE.sub(
        "[Interactive quizzes are available in the Hebrew/Learn section.]",
        content,
    )


def _compute_cost(usage: dict, model: str = "") -> dict:
    """Estimate cost from the configured provider's usage response."""
    pricing = _llm_provider.pricing(model or DEEPSEEK_MODEL)
    p_in = usage.get("prompt_tokens", 0)
    p_out = usage.get("completion_tokens", 0)
    cache_hit = usage.get("prompt_cache_hit_tokens", 0)
    cost_input = p_in * pricing["input"] / 1_000_000
    cost_output = p_out * pricing["output"] / 1_000_000
    cost_cache = cache_hit * pricing["cache_hit"] / 1_000_000
    return {
        "total": round(cost_input + cost_output - cost_cache, 6),
        "input": round(cost_input, 6),
        "output": round(cost_output, 6),
        "cache_saved": round(cost_cache, 6),
    }


# ─── Access Control ───

# Only allow chat requests from these origins (prevents external API abuse).
# Exact match on scheme+host+port — the old `startswith` check let
# `https://scriptureengine.org.evil.com` through.
ALLOWED_ORIGINS = {
    "https://scriptureengine.org",
    "https://www.scriptureengine.org",
    "http://localhost:5175",   # dev Vite frontend (leased port)
    "http://localhost:5174",   # local API dev (leased port)
    "http://127.0.0.1:5175",   # dev Vite frontend (loopback)
    "http://127.0.0.1:5174",   # local API dev (loopback)
}


def _origin_allowed(value: str) -> bool:
    """True if an Origin/Referer header value matches an allowed origin.

    Exact tuple match against ALLOWED_ORIGINS, plus any subdomain of the main
    domain (https://app.scriptureengine.org etc.). Malformed values are rejected.
    """
    if not value:
        return False
    v = value.lower().rstrip("/")
    if v in ALLOWED_ORIGINS:
        return True
    try:
        parts = urlsplit(v)
    except ValueError:
        return False
    host = (parts.hostname or "").lower()
    return host.endswith(".scriptureengine.org") and parts.scheme in ("https", "http")

# Simple in-memory rate limiter (per IP, sliding 60s window). General chat and
# Hebrew Tutor carry separate budgets so one heavy mode cannot exhaust the
# other's capacity (plan Track G3: per-feature budgets).
_rate_limits: dict[str, list[float]] = {}
RATE_WINDOW = 60  # seconds


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _mode_rate_limit(mode: str) -> int:
    """Requests per RATE_WINDOW for this chat mode (env-overridable)."""
    if _effective_mode(mode) == "hebrew":
        return _env_int("HEBREW_RATE_LIMIT", 20)
    return _env_int("CHAT_RATE_LIMIT", 20)


def _check_rate_limit(ip: str, limit: int | None = None) -> bool:
    """Return True if request is allowed, False if rate-limited."""
    now = time.time()
    timestamps = _rate_limits.get(ip, [])
    # Prune expired entries
    timestamps = [t for t in timestamps if now - t < RATE_WINDOW]
    if len(timestamps) >= (limit if limit is not None else _env_int("CHAT_RATE_LIMIT", 20)):
        return False
    timestamps.append(now)
    _rate_limits[ip] = timestamps
    return True


def _chat_disabled(mode: str) -> str | None:
    """Emergency disable switches (Track G3).

    CHAT_DISABLED kills both chat modes; HEBREW_CHAT_DISABLED kills Hebrew
    Tutor only. Scripture lookup endpoints are unaffected either way.
    Returns a user-facing error message, or None when chat may proceed.
    """
    def _flag_set(name: str) -> bool:
        return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")

    m = _effective_mode(mode)
    if _flag_set("CHAT_DISABLED"):
        return "Chat is temporarily unavailable. Scripture lookups still work."
    if m == "hebrew" and _flag_set("HEBREW_CHAT_DISABLED"):
        return "Hebrew Tutor is temporarily unavailable."
    return None


# ─── Context Budget Management ───

MAX_PROMPT_TOKENS = 200_000
KEEP_EXCHANGES = 15  # user+assistant pairs to keep before compaction

# ─── Output budget / truncation guards ───
# DeepSeek thinking mode counts reasoning tokens against max_tokens, so a small
# budget can be exhausted by CoT alone → finish_reason="length" → truncated.
MIN_THINKING_TOKENS = 16_384
MAX_OUTPUT_TOKENS = 128_000


def _retry_budget(max_tokens: int) -> int:
    """Bump max_tokens for a truncation retry (reasoning + answer share budget)."""
    return min(max(max_tokens * 4, MIN_THINKING_TOKENS), MAX_OUTPUT_TOKENS)


def _finish_reason(data: dict) -> str:
    """Extract finish_reason from a DeepSeek chat completion response."""
    choices = data.get("choices") or []
    return str(choices[0].get("finish_reason") or "") if choices else ""


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return len(text) // 4


def apply_context_budget(message_list: list[dict]) -> list[dict]:
    """Trim message list to stay within budget. Strips tool traces first,
    then keeps only the last KEEP_EXCHANGES user+assistant exchanges."""
    total_est = sum(_estimate_tokens(m.get("content", "") or "") for m in message_list)
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
    total_est = sum(_estimate_tokens(m.get("content", "") or "") for m in cleaned_all)

    if total_est <= MAX_PROMPT_TOKENS:
        return system + cleaned_all

    # 2. Still over budget: keep only the most recent KEEP_EXCHANGES exchanges
    if exchange_count > KEEP_EXCHANGES:
        # Take the last KEEP_EXCHANGES exchanges from the 'after' portion
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


class ChatRequest(BaseModel):
    messages: list[dict]
    model: str = _llm_provider.default_model
    max_tokens: int = MIN_THINKING_TOKENS
    temperature: float = 0.7
    tools_enabled: bool = True
    disabled_tools: list[str] = []
    scopes: list[str] = []  # opt-in scopes: "cfm", "conference" (default none = off)
    mode: str = "chat"  # "chat", "hebrew", "knowledge"
    subagents: bool = True  # planner → parallel workers → synthesizer for research questions
    session_id: str = ""            # conversation session — job saves the completed answer here
    client_message_id: str = ""     # user message id (idempotency context for the save)
    user_id: str = ""               # who is chatting — Hebrew Tutor tools are mode-scoped
    session_token: str = ""         # optional auth token; resolved server-side
    tool_user_id: str = ""           # server-bound identity for user-scoped tools


def _normalize_user_id(user_id: str) -> str:
    """Anonymous/empty chat users map to the app's anonymous id."""
    if not user_id or user_id in ("anonymous", "default"):
        return "default"
    return user_id


def _bind_chat_identity(body: ChatRequest, request: Request) -> str:
    """Resolve an authenticated chat identity and overwrite client claims.

    Anonymous clients retain the existing stable local id for compatibility;
    authenticated clients must prove ownership with the session token. The
    resolved id is then injected into every user-scoped tool call.
    """
    token = (body.session_token or "").strip()
    authorization = (request.headers.get("authorization") or "").strip()
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() != "bearer" or not value.strip():
            return "Invalid authorization header"
        token = value.strip()
    if token:
        try:
            from web.routes.auth import _resolve_user_from_token
            resolved = _resolve_user_from_token(token)
        except Exception:
            resolved = None
        if not resolved:
            return "Invalid session token"
        body.user_id = resolved
    else:
        body.user_id = _normalize_user_id(body.user_id)
        # A client-local id is suitable for anonymous conversation ownership,
        # but it is not an authorization credential for learner data.
        body.tool_user_id = "default"
    if token:
        body.tool_user_id = body.user_id
    # Tokens are never needed after identity binding and must not enter jobs DB.
    body.session_token = ""
    return ""


def _chat_tool_user_id(body) -> str:
    """Return the identity authorized for user-scoped tool calls."""
    return getattr(body, "tool_user_id", "") or "default"


def _provider_configured(model: str) -> bool:
    """Honor legacy tests/config while supporting native provider workers."""
    valid, _ = _llm_provider.validate_model(model)
    if not valid:
        return False
    if _llm_provider.is_opencode_go_model(model):
        return _llm_provider.configured(model)
    return bool(DEEPSEEK_API_KEY) or _llm_provider.configured(model)


def _provider_error(model: str) -> str:
    valid, message = _llm_provider.validate_model(model)
    if not valid:
        return message
    if not _llm_provider.is_opencode_go_model(model) and not DEEPSEEK_API_KEY:
        return "DEEPSEEK_API_KEY not configured"
    return "No configured chat provider for the selected model"


def _verify_citations_sync(content: str, mode: str):
    """Blocking part of citation verification (runs in an executor thread)."""
    try:
        from lib.controls.claims import check_quotations
    except Exception:
        return None

    def _lookup(ref: str):
        parts = ref.split(".")
        if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
            return None
        res = _run_tool_thread(
            "scripture_verse",
            {"book": parts[0], "chapter": int(parts[1]), "verse": int(parts[2])},
            [],
            "citation-check",
            mode,
        )
        if isinstance(res, dict) and not res.get("error"):
            return res.get("text_english")
        return None

    return check_quotations(content, _lookup)


async def _verify_citations(content: str, mode: str):
    """Deterministic quotation-vs-verse checks on a final answer (Track A3).

    Stage 1 of the grounded-verification pipeline: quoted spans adjacent to a
    verse ref must appear verbatim in that verse's text. Returns None when
    there is nothing to check (no quotes / Hebrew tutor mode). Bounded: at
    most six verse fetches per answer, no LLM in the loop.
    """
    if mode == "hebrew" or not content:
        return None
    if '"' not in content and "\u201c" not in content:
        return None
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _verify_citations_sync, content, mode)


def _contributor_disclosure() -> str | None:
    """Contributor-tier data-handling disclosure (Track G3).

    When the default model runs on a contributor tier, users must be told
    before sending material — the tier may be training-opt-in upstream.
    """
    if "contributor" in (_llm_provider.default_model or "").lower():
        return ("This model runs on a contributor service tier: conversation "
                "content may be used for provider training. Do not send "
                "private or sensitive material.")
    return None


@router.get("/api/v1/chat/instructions")
def chat_instructions(mode: str = "chat"):
    """Return mode-scoped instructions and tools without learner leakage."""
    mode = _effective_mode(mode)
    return {
        "ok": True,
        "data": {
            "system_prompt": CHAT_PROMPTS.get(mode, CHAT_SYSTEM_PROMPT),
            "tools": _filter_tools(TOOL_DEFINITIONS, [], [], mode),
            "model": _llm_provider.default_model,
            "pricing": _llm_provider.pricing(_llm_provider.default_model),
            # Public-safe availability only — no model inventory or worker-pool
            # counts on an unauthenticated endpoint (Track G3).
            "provider": _llm_provider.public_summary(),
            "data_handling": _contributor_disclosure(),
        },
    }


@router.post("/api/v1/chat")
async def llm_chat(body: ChatRequest, request: Request):
    """Proxy chat requests to DeepSeek API with function calling support.

    If the LLM requests a tool call, the server executes it against the
    scripture engine and feeds the result back to the LLM for a final response.
    """
    if not _provider_configured(body.model):
        return {"ok": False, "error": _provider_error(body.model)}
    identity_error = _bind_chat_identity(body, request)
    if identity_error:
        return {"ok": False, "error": identity_error}

    # Origin check — only allow requests from the SPA or local dev
    origin = (request.headers.get("origin") or "").lower().rstrip("/")
    referer = (request.headers.get("referer") or "").lower().rstrip("/")
    if not (_origin_allowed(origin) or _origin_allowed(referer)):
        return {"ok": False, "error": "Chat is only available from scriptureengine.org"}

    # Emergency disable switch (Track G3) — checked before any work
    disable_msg = _chat_disabled(body.mode)
    if disable_msg:
        return {"ok": False, "error": disable_msg}

    # Rate limiting — per-IP budgets scoped per chat mode
    # Prefer Cloudflare's connecting IP, then X-Forwarded-For, then direct client
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if not _check_rate_limit(client_ip, _mode_rate_limit(body.mode)):
        return {"ok": False, "error": "Rate limit exceeded. Try again in a minute."}

    # from lib.api import call_tool, list_tools
    # from lib.api.staging import stage_connection, stage_study
    # from lib.db import get_db

    # Build messages with system prompt (mode-specific) + Hebrew hydration
    msgs = _prepare_chat_messages(body)

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
        # Filter out disabled tools + scope-gated tools the request didn't opt into
        payload["tools"] = _filter_tools(TOOL_DEFINITIONS, body.scopes, body.disabled_tools, body.mode)
        payload["tool_choice"] = "auto"

    tool_results = []
    max_tool_rounds = 15  # prevent infinite loops; 10 was too low for multi-work searches

    data = await call_deepseek(payload)

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0) if isinstance(err, dict) else 0
        friendly_map = {
            400: "Invalid request format.",
            401: "API key issue — contact the repo maintainer.",
            429: "Rate limited — please wait a moment.",
            500: "DeepSeek server error. Try again.",
        }
        msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
        friendly = friendly_map.get(code, "")
        return {"ok": False, "error": f"{friendly} [{msg}]" if friendly else msg}

    rounds = 0
    budget_retried = False
    while data.get("choices") and rounds < max_tool_rounds:
        choice = data["choices"][0]
        msg = choice.get("message", {})
        finish_reason = choice.get("finish_reason")

        # Check for tool calls
        tool_calls = msg.get("tool_calls")

        # Truncation guard: finish_reason="length" means the budget ran out
        # (thinking + answer share max_tokens). Retry once with more room before
        # accepting a partial answer or executing a possibly-partial tool call.
        if finish_reason == "length" and not budget_retried:
            budget_retried = True
            logger.warning(
                "chat: response truncated (finish_reason=length); retrying with max_tokens=%s",
                _retry_budget(body.max_tokens),
            )
            payload["max_tokens"] = _retry_budget(body.max_tokens)
            data = await call_deepseek(payload)
            if "error" in data:
                err = data["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                return {"ok": False, "error": f"DeepSeek API error: {msg}"}
            continue

        if not tool_calls:
            break  # No more tool calls, we have final response

        # Execute each tool call
        # First, add the assistant's tool_calls message once (DeepSeek requires this order)
        msgs.append(msg)
        conn = get_db()

        # Dedup: skip tool calls that were already made in this round with same name+args
        existing_calls = set()
        for existing_tc in tool_calls:
            existing_calls.add((existing_tc["function"]["name"], existing_tc["function"]["arguments"]))

        # Track progress for frontend display
        round_tool_names = [tc["function"]["name"] for tc in tool_calls]

        # Separate staging (write) tools from read-only tools
        staging_calls = [
            tc for tc in tool_calls
            if tc["function"]["name"] in STAGING_TOOLS
            and _mode_allowed(tc["function"]["name"], body.mode)
        ]
        # A tool call that is not allowed in this mode is deliberately routed
        # through the read-only guard so it returns an error instead of writing.
        ro_calls = [tc for tc in tool_calls if tc not in staging_calls]

        # Run read-only tools in parallel (threaded — sync DB tools off the loop)
        async def run_ro(tc):
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            return tc, await asyncio.to_thread(
                _run_tool_thread,
                tc["function"]["name"],
                fn_args,
                body.scopes,
                _chat_tool_user_id(body),
                body.mode,
            )

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
            msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "error": f"DeepSeek API error: {msg}"}

        rounds += 1

    # Final response
    usage = data.get("usage", {})
    choice = data["choices"][0] if data.get("choices") else None
    if not choice:
        return {"ok": False, "error": "No response from LLM"}

    final_content = choice["message"].get("content") or ""
    final_reasoning = choice["message"].get("reasoning_content")

    # If LLM only made tool calls without summarizing, force a summary
    # Also force summary if the content is just planning text (starts with "Let me")
    # Or if it's a stub response like "Looked up N sources..." (tool listing without synthesis)
    is_planning = final_content.strip()[:20].lstrip().startswith("Let me")
    is_stub = tool_results and len(final_content.strip()) < 300 and len(tool_results) > 2
    if (not final_content or is_planning or is_stub) and tool_results:
        msgs.append({"role": "user", "content":
            "You have all the data you need from the tool calls above. "
            "Now synthesize a complete thorough answer in natural language based on the information you found. "
            "Cite the specific verses and data you found with full book names like 'Genesis 1:1'. "
            "Include specific gematria values, verse quotations, and connection details from the tool results. "
            "Do not list the tools you used or say 'I looked up...' — just present the findings directly."})
        retry = await call_deepseek({
            "model": body.model, "messages": msgs,
            "max_tokens": body.max_tokens, "temperature": body.temperature,
        })
        if retry.get("choices"):
            rc_msg = retry["choices"][0].get("message", {})
            if rc_msg.get("content") or rc_msg.get("reasoning_content"):
                final_content = rc_msg.get("content") or ""
                final_reasoning = rc_msg.get("reasoning_content") or final_reasoning
            # Merge usage from the retry call
            retry_usage = retry.get("usage", {})
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens"):
                if retry_usage.get(k):
                    usage[k] = usage.get(k, 0) + retry_usage[k]

    final_content = _sanitize_chat_content(final_content, body.mode)

    # Track A3 stage 1: label unverifiable quotations before the answer ships.
    # Nothing is deleted — the prefix plus claim_check metadata let the UI and
    # the user judge; regeneration/softening stays a later pipeline stage.
    claim_check = await _verify_citations(final_content, body.mode)
    if claim_check and claim_check["unsupported"]:
        refs = ", ".join(sorted({u["ref"] for u in claim_check["unsupported"]}))
        final_content = (
            "⚠️ Some quotations could not be verified against the cited verses "
            f"({refs}); treat those citations as provisional.\n\n" + final_content
        )

    cost = _compute_cost(usage, body.model)

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
            "finish_reason": _finish_reason(data),
            "claim_check": claim_check,
        },
    }


# ─── Module-level helpers (shared by both endpoints) ───


async def call_deepseek(req_payload):
    """Non-streaming provider call used for tool-calling rounds.

    The historical function name is retained because the subagent/job modules
    patch it in tests and use it as their provider callback.
    """
    if _llm_provider.is_opencode_go_model(req_payload.get("model")):
        return await _llm_provider.complete(req_payload)
    valid, model = _llm_provider.validate_model(req_payload.get("model"))
    if not valid:
        return {"error": {"code": 400, "message": model}}
    _, upstream_model, _ = _llm_provider.targets_for(model)
    req_payload = dict(req_payload)
    req_payload["model"] = upstream_model
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


def _build_payload(body: ChatRequest, messages: list, stream: bool = False) -> dict:
    """Build the provider-neutral chat-completions payload."""
    payload = {
        "model": body.model,
        "messages": messages,
        "max_tokens": body.max_tokens,
        "temperature": body.temperature,
        "stream": stream,
    }
    if body.tools_enabled:
        payload["tools"] = _filter_tools(TOOL_DEFINITIONS, body.scopes, body.disabled_tools, body.mode)
        payload["tool_choice"] = "auto"
    if stream:
        # Guarantees a usage chunk (incl. finish_reason + reasoning_tokens) before [DONE]
        payload["stream_options"] = {"include_usage": True}
    return payload


def _run_tool_thread(fn_name, fn_args, scopes, user_id="", mode="chat"):
    """Run one read-only chat tool in a worker thread (own DB connection).

    Executes off the event loop so concurrent tool calls in a round actually
    run in parallel — the old asyncio.gather over the synchronous call_tool
    just ran them serially on the loop (no await points). sqlite3 connections
    aren't thread-safe, so each call opens its own via get_db() and closes it
    inside the thread. Deterministic tools pass results through the in-memory
    tool cache so repeat lookups skip the DB entirely.
    """
    if not _mode_allowed(fn_name, mode):
        return {"error": f"Tool disabled in {mode} mode"}
    if fn_name == "scripture_research_parallel":
        # LLM-orchestrated parallel research — handled here (not in the tool
        # registry) because it drives its own nested planner/worker LLM calls.
        if mode in ("chat", "knowledge"):
            # Keep the historical callback signature for integrations/tests
            # that replace this helper; both modes share the general allowlist.
            return _run_research_parallel(fn_args)
        return _run_research_parallel(fn_args, mode=mode)
    if not _scope_allowed(fn_name, scopes):
        return {"error": "This tool is disabled — enable the matching scope (Come Follow Me / Conference Talks) in chat settings."}
    # Per-user tools always use the server-bound chatting user. Never honor an
    # LLM/client-supplied user_id, even when it is present in tool arguments.
    if _tool_accepts_user_id(fn_name):
        fn_args["user_id"] = user_id or "default"
    cached = tool_cache.get(fn_name, fn_args)
    if cached is not None:
        return cached
    try:
        conn = get_db()
        try:
            result = call_tool(fn_name, conn, **fn_args)
        finally:
            conn.close()
        tool_cache.set(fn_name, fn_args, result)
        return result
    except Exception as e:
        return {"error": str(e)}


async def _research_llm(payload):
    """Standalone provider call for the research_parallel tool. Uses its own
    HTTP client + event loop — the shared _http_client is bound to the server's
    loop and this runs inside a worker thread's fresh loop."""
    if _llm_provider.is_opencode_go_model(payload.get("model")):
        return await _llm_provider.complete(payload)
    valid, model = _llm_provider.validate_model(payload.get("model"))
    if not valid:
        return {"error": {"code": 400, "message": model}}
    _, upstream_model, _ = _llm_provider.targets_for(model)
    payload = dict(payload)
    payload["model"] = upstream_model
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
            json=payload,
        )
        return resp.json()


def _run_research_parallel(args, call_llm=None, mode="chat"):
    """Run the subagent worker pool as a synchronous tool call.

    Spawns its own event loop in the calling thread: planner → parallel
    workers → merged findings, all in one tool call. The chat agent decides
    when to invoke it for deep parallel research (the pipeline's own fan-out
    covers most cases; this is the explicit lever).
    """
    query = str(args.get("query") or "").strip()
    if not query:
        return {"error": "query is required"}
    llm = call_llm or _research_llm

    async def _inner():
        tool_defs = _filter_tools(TOOL_DEFINITIONS, [], [], mode)
        plan = await _subagents.plan_research(
            llm, [{"role": "user", "content": query}],
            [t["function"]["name"] for t in tool_defs])
        if not plan:
            return {"error": "planner could not break down the query — try scripture_research instead"}

        async def _run_tool(tc):
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            return await asyncio.to_thread(_run_tool_thread, tc["function"]["name"], fn_args, [], "", mode)

        async def _noop(ev):
            pass

        reports = await _subagents.run_workers(plan, tool_defs, [], llm, _run_tool, _noop)
        parts = []
        for r in reports:
            if r.get("error") and not r.get("content"):
                parts.append(f"[worker {r['task_id']} failed: {r['error']}]")
            else:
                parts.append(r.get("content") or "(no findings)")
        return {"tasks": len(plan), "findings": parts}

    try:
        return asyncio.run(_inner())
    except Exception as e:
        return {"error": f"research_parallel failed: {e}"}


def _sse_event(data: dict) -> str:
    """Format a single SSE event."""
    return f"data: {json.dumps(data, default=str)}\n\n"


async def _sse_yield(data: dict):
    """Async generator yielding a single SSE event (for error responses)."""
    yield _sse_event(data)


_STOP = object()


async def _next_line(iterator):
    """Safe next() for an async iterator — converts StopAsyncIteration to _STOP."""
    try:
        return await iterator.__anext__()
    except StopAsyncIteration:
        return _STOP


async def _heartbeat_lines(resp, interval: float = 15.0):
    """Wrap resp.aiter_lines(): yield ('line', line) per line, plus ('hb', None)
    whenever no line has arrived for `interval` seconds. Keeps browsers/proxies
    from idle-timeout during long silent thinking pauses. Upstream errors are
    re-raised via task.result()."""
    iterator = resp.aiter_lines()
    task = asyncio.ensure_future(_next_line(iterator))
    try:
        while True:
            _done, _pending = await asyncio.wait({task}, timeout=interval)
            if task.done():
                line = task.result()
                if line is _STOP:
                    return
                yield ("line", line)
                task = asyncio.ensure_future(_next_line(iterator))
            else:
                yield ("hb", None)
    finally:
        if not task.done():
            task.cancel()


async def _stream_final_response(body, msgs, tool_results):
    """Stream the final LLM response for a completed message list.

    Extracted from _chat_pipeline so both the sequential tool-loop path and the
    subagent fan-out path share identical behavior: streaming (with heartbeat),
    finish_reason="length" regenerate-once, forced summary for stub responses,
    and the `done` event with merged usage + cost. Yields plain event dicts.
    """
    usage = {}
    final_reasoning = ""
    final_content = ""
    finish_reason = ""
    budget_retried = False

    # Regenerate-once loop: if the output budget runs out mid-stream
    # (finish_reason="length"), discard the partial and retry with more room.
    while True:
        stream_payload = _build_payload(body, msgs, stream=True)
        if not _llm_provider.is_opencode_go_model(body.model):
            valid, model = _llm_provider.validate_model(body.model)
            if not valid:
                yield {"type": "error", "message": model}
                return
            _, upstream_model, _ = _llm_provider.targets_for(model)
            stream_payload["model"] = upstream_model
        if budget_retried:
            stream_payload["max_tokens"] = _retry_budget(body.max_tokens)

        # Pre-stream heartbeat — the final request can take a moment to open.
        yield {"type": "heartbeat"}
        try:
            if _llm_provider.is_opencode_go_model(body.model):
                stream_context = _llm_provider.stream(stream_payload)
            else:
                stream_context = _http_client.stream(
                    "POST", f"{DEEPSEEK_BASE}/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                    json=stream_payload,
                )
            async with stream_context as resp:
                if not 200 <= resp.status_code < 300:
                    raw_error = await resp.aread()
                    try:
                        error_data = json.loads(raw_error)
                    except (TypeError, json.JSONDecodeError):
                        error_data = {}
                    error_value = error_data.get("error", error_data)
                    if isinstance(error_value, dict):
                        error_message = error_value.get("message") or str(error_value)
                    else:
                        error_message = str(error_value)
                    yield {"type": "error", "message": f"Upstream chat error ({resp.status_code}): {error_message}"}
                    return
                async for kind, value in _heartbeat_lines(resp):
                    if kind == "hb":
                        # Long silent thinking pause — keep the proxy/browser alive
                        yield {"type": "heartbeat"}
                        continue
                    line = value
                    if not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        chunk_data = json.loads(chunk)
                    except json.JSONDecodeError:
                        continue

                    choice0 = chunk_data.get("choices", [{}])[0]
                    delta = choice0.get("delta", {})
                    fr = choice0.get("finish_reason")
                    if fr:
                        finish_reason = fr

                    # Reasoning content (thinking) — stream it
                    rc = delta.get("reasoning_content")
                    if rc:
                        final_reasoning += rc
                        yield {"type": "thinking", "content": rc}

                    # Visible content — stream it
                    c = delta.get("content")
                    if c:
                        final_content += c
                        yield {"type": "text", "content": c}

                    # Track usage from the last chunk
                    if chunk_data.get("usage"):
                        usage = chunk_data["usage"]

        except Exception as e:
            yield {"type": "error", "message": f"Stream error: {str(e)}"}
            return

        # Truncation guard: regenerate once with a bigger budget
        if finish_reason == "length" and not budget_retried:
            budget_retried = True
            usage = {}
            final_reasoning = ""
            final_content = ""
            finish_reason = ""
            logger.warning(
                "chat: stream truncated (finish_reason=length); retrying with max_tokens=%s",
                _retry_budget(body.max_tokens),
            )
            yield {"type": "truncated"}
            continue
        break

    # Force summary if content is stub (tool listing), planning text, or empty
    is_planning = final_content.strip()[:20].lstrip().startswith("Let me")
    is_stub = tool_results and len(final_content.strip()) < 300 and len(tool_results) > 2
    if (not final_content or is_planning or is_stub) and tool_results:
        # LLM returned only tool results without synthesis — force a summary
        msgs.append({"role": "user", "content":
            "You have all the data you need from the tool calls above. "
            "Now synthesize a complete thorough answer in natural language based on the information you found. "
            "Cite the specific verses and data you found with full book names like 'Genesis 1:1'. "
            "Include specific gematria values, verse quotations, and connection details from the tool results. "
            "Do not list the tools you used or say 'I looked up...' — just present the findings directly."})
        retry_payload = _build_payload(body, msgs, stream=False)
        retry_data = await call_deepseek(retry_payload)
        if _finish_reason(retry_data) == "length":
            retry_payload["max_tokens"] = _retry_budget(body.max_tokens)
            retry_data = await call_deepseek(retry_payload)
        if retry_data.get("choices"):
            rc_msg = retry_data["choices"][0].get("message", {})
            retry_content = rc_msg.get("content") or ""
            retry_reasoning = rc_msg.get("reasoning_content") or ""
            if retry_content:
                yield {"type": "text", "content": retry_content}
            if retry_reasoning:
                yield {"type": "thinking", "content": retry_reasoning}
            final_content = retry_content or final_content
            final_reasoning = retry_reasoning or final_reasoning
            retry_usage = retry_data.get("usage", {})
            for k in ("prompt_tokens", "completion_tokens", "total_tokens", "prompt_cache_hit_tokens"):
                if retry_usage.get(k):
                    usage[k] = usage.get(k, 0) + retry_usage[k]

    final_content = _sanitize_chat_content(final_content, body.mode)
    cost = _compute_cost(usage, body.model)

    yield {
        "type": "done",
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "cache_hit_tokens": usage.get("prompt_cache_hit_tokens", 0),
        },
        "cost": cost,
        "model": body.model,
        "tool_results": tool_results,
        "finish_reason": finish_reason,
        # Final content fallback: if the client missed chunks (proxy close,
        # remount, aborted fetch), it can recover the full response from here.
        "final_content": final_content,
        "final_reasoning": final_reasoning,
    }


async def _chat_pipeline(body, msgs):
    """Run the full chat pipeline — tool-calling rounds (non-streaming) then the
    streamed final response — yielding plain event dicts:
      heartbeat / tool_progress / thinking / text / truncated / error / done

    Shared by the SSE stream endpoint and the background job runner, so both
    paths behave identically (finish_reason guard, truncation retry, heartbeats).
    `body` is a ChatRequest (or dict with the same fields); `msgs` is the
    prepared message list (system prompt injected, budget applied).
    """
    tool_results = []

    # ── Subagent fan-out (planner → parallel workers → synthesizer) ──
    # For research-shaped questions, replace the sequential tool loop with one
    # planner call, ≤3 concurrent worker tool-loops, then the shared final
    # stream. Wall-clock ≈ 3 sequential LLM calls instead of up to 15.
    if getattr(body, "subagents", True) and body.tools_enabled and _subagents.should_plan(msgs):
        tool_defs = _filter_tools(TOOL_DEFINITIONS, body.scopes, body.disabled_tools, body.mode)
        plan = await _subagents.plan_research(
            call_deepseek, msgs, [t["function"]["name"] for t in tool_defs])
        if plan:
            yield {"type": "plan", "tasks": plan}

            async def _run_worker_tool(tc):
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}
                return await asyncio.to_thread(
                    _run_tool_thread,
                    tc["function"]["name"],
                    fn_args,
                    body.scopes,
                    _chat_tool_user_id(body),
                    body.mode,
                )

            queue = asyncio.Queue()

            async def _emit(ev):
                await queue.put(ev)

            workers_task = asyncio.create_task(_subagents.run_workers(
                plan, tool_defs, body.scopes, call_deepseek, _run_worker_tool, _emit))

            # Drain worker progress events until the pool finishes.
            while True:
                if not queue.empty():
                    yield queue.get_nowait()
                    continue
                if workers_task.done():
                    break
                getter = asyncio.ensure_future(queue.get())
                done, _ = await asyncio.wait({workers_task, getter},
                                             return_when=asyncio.FIRST_COMPLETED)
                if getter in done:
                    try:
                        yield getter.result()
                    except asyncio.QueueEmpty:
                        pass
                else:
                    getter.cancel()

            reports = workers_task.result()
            worker_tool_results = [tr for r in reports for tr in r.get("tool_results", [])]

            # Fall back to the sequential loop when every worker failed.
            if any(r.get("content") for r in reports):
                tool_results = worker_tool_results
                msgs = _subagents.build_synthesis_messages(msgs, reports)
                async for ev in _stream_final_response(body, msgs, tool_results):
                    yield ev
                return

    # ── Tool-calling rounds (non-streaming) ──
    payload = _build_payload(body, msgs, stream=False)
    max_tool_rounds = 15
    rounds = 0

    while rounds < max_tool_rounds:
        # DeepSeek thinking rounds can take minutes with zero bytes on the
        # wire — emit heartbeats so browsers/proxies don't idle-timeout.
        round_task = asyncio.create_task(call_deepseek(payload))
        while not round_task.done():
            _done, _pending = await asyncio.wait({round_task}, timeout=15)
            if not round_task.done():
                yield {"type": "heartbeat"}
        data = round_task.result()

        if "error" in data:
            err = data["error"]
            message = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            yield {"type": "error", "message": message}
            return

        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        tool_calls = msg.get("tool_calls")

        if not tool_calls:
            # No more tool calls — break to streaming
            break

        # Yield tool progress
        yield {"type": "tool_progress", "tools": [
            {"name": tc["function"]["name"], "args": json.loads(tc["function"]["arguments"])}
            for tc in tool_calls
        ]}

        msgs.append(msg)
        conn = get_db()

        staging_calls = [
            tc for tc in tool_calls
            if tc["function"]["name"] in STAGING_TOOLS
            and _mode_allowed(tc["function"]["name"], body.mode)
        ]
        ro_calls = [tc for tc in tool_calls if tc not in staging_calls]

        async def run_ro(tc):
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}
            return tc, await asyncio.to_thread(
                _run_tool_thread,
                tc["function"]["name"],
                fn_args,
                body.scopes,
                _chat_tool_user_id(body),
                body.mode,
            )

        ro_results = await asyncio.gather(*[run_ro(tc) for tc in ro_calls]) if ro_calls else []

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

        all_results = ro_results + staging_results
        for tc, result in all_results:
            result_str = json.dumps(result, default=str, ensure_ascii=False)
            if len(result_str) > 3000:
                result_str = result_str[:3000] + '..." [truncated]'
            tool_results.append({
                "id": tc["id"],
                "name": tc["function"]["name"],
                "args": json.loads(tc["function"]["arguments"]),
                "result": result if len(json.dumps(result, default=str, ensure_ascii=False)) <= 3000 else {"_truncated": True, "preview": result_str[:500]},
            })
            msgs.append({
                "role": "tool",
                "content": result_str,
                "tool_call_id": tc["id"],
            })

        conn.close()

        # Budget check
        est = sum(len(m.get("content", "") or "") // 4 for m in msgs)
        if est > MAX_PROMPT_TOKENS * 0.8:
            msgs = apply_context_budget(msgs)

        payload["messages"] = msgs
        rounds += 1

    # ── Streaming final response (shared helper: sequential path and
    # subagent fan-out both land here) ──
    async for ev in _stream_final_response(body, msgs, tool_results):
        yield ev


# ─── SSE Streaming Chat Endpoint ───


@router.post("/api/v1/chat/stream")
async def llm_chat_stream(body: ChatRequest, request: Request):
    """Stream chat responses via SSE — text and thinking arrive incrementally.

    Same tool-calling logic as llm_chat, but the final LLM response is streamed
    so users see text in real-time instead of waiting 2-8 minutes for the full
    response. Yields SSE events:
      - data: {"type":"thinking","content":"..."}  (reasoning chunks)
      - data: {"type":"text","content":"..."}       (visible text chunks)
      - data: {"type":"tool_progress","tools":[...]} (tool calls being executed)
      - data: {"type":"done","usage":{...},"cost":{...},"model":"..."}
    """
    if not _provider_configured(body.model):
        return StreamingResponse(
            _sse_yield({"type": "error", "ok": False, "error": _provider_error(body.model), "message": _provider_error(body.model)}),
            media_type="text/event-stream",
        )
    identity_error = _bind_chat_identity(body, request)
    if identity_error:
        return StreamingResponse(
            _sse_yield({"type": "error", "ok": False, "error": identity_error, "message": identity_error}),
            media_type="text/event-stream",
        )

    # Origin check
    origin = (request.headers.get("origin") or "").lower().rstrip("/")
    referer = (request.headers.get("referer") or "").lower().rstrip("/")
    if not (_origin_allowed(origin) or _origin_allowed(referer)):
        return StreamingResponse(
            _sse_yield({"type": "error", "ok": False, "error": "Chat is only available from scriptureengine.org", "message": "Chat is only available from scriptureengine.org"}),
            media_type="text/event-stream",
        )

    # Emergency disable switch + rate limiting (SSE error shape)
    disable_msg = _chat_disabled(body.mode)
    if disable_msg:
        return StreamingResponse(
            _sse_yield({"type": "error", "ok": False, "error": disable_msg, "message": disable_msg}),
            media_type="text/event-stream",
        )

    # Rate limiting
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if not _check_rate_limit(client_ip, _mode_rate_limit(body.mode)):
        return StreamingResponse(
            _sse_yield({"type": "error", "ok": False, "error": "Rate limit exceeded. Try again in a minute.", "message": "Rate limit exceeded. Try again in a minute."}),
            media_type="text/event-stream",
        )

    # Build messages with mode-specific system prompt (+ Hebrew hydration)
    msgs = _prepare_chat_messages(body)

    async def stream_generator():
        """Run tool rounds (non-streaming), then stream final response."""
        async for event in _chat_pipeline(body, msgs):
            yield _sse_event(event)

    return StreamingResponse(stream_generator(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


# ─── Chat Background Jobs (decoupled runs) ───


@router.post("/api/v1/chat/jobs")
async def llm_chat_job_create(body: ChatRequest, request: Request):
    """Create a background chat job. The DeepSeek run proceeds server-side
    independent of the client connection — it survives phone minimize, network
    drops, and tab switches. Poll GET /api/v1/chat/jobs/{id}?after_seq=N."""
    if not _provider_configured(body.model):
        return {"ok": False, "error": _provider_error(body.model)}
    identity_error = _bind_chat_identity(body, request)
    if identity_error:
        return {"ok": False, "error": identity_error}

    # Origin check — same gate as the other chat endpoints
    origin = (request.headers.get("origin") or "").lower().rstrip("/")
    referer = (request.headers.get("referer") or "").lower().rstrip("/")
    if not (_origin_allowed(origin) or _origin_allowed(referer)):
        return {"ok": False, "error": "Chat is only available from scriptureengine.org"}

    disable_msg = _chat_disabled(body.mode)
    if disable_msg:
        return {"ok": False, "error": disable_msg}

    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    if not _check_rate_limit(client_ip, _mode_rate_limit(body.mode)):
        return {"ok": False, "error": "Rate limit exceeded. Try again in a minute."}

    # Prepare messages (same as the stream endpoint, incl. Hebrew hydration)
    msgs = _prepare_chat_messages(body)

    try:
        job_body = body.model_dump(exclude={"session_token"})
        job_id = _jobs.manager.create(job_body, msgs, client_ip)
    except _jobs.JobLimitError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "data": {"job_id": job_id, "seq": 0, "status": "queued"}}


@router.get("/api/v1/chat/jobs/{job_id}")
async def llm_chat_job_poll(job_id: str, after_seq: int = 0):
    """Poll a chat job: events since after_seq plus a final snapshot when done.

    job_id is an unguessable UUID acting as a capability token, so this read
    endpoint skips the origin gate (plain GETs don't carry Origin anyway)."""
    job = _jobs.manager.get(job_id)
    if job is None:
        return {"ok": False, "error": "Chat job not found"}
    events = job.events_since(after_seq)
    done = None
    if job.status in ("done", "failed"):
        done = {
            "status": job.status,
            "content": job.final_content,
            "reasoning": job.final_reasoning,
            "finish_reason": job.finish_reason,
            "usage": job.usage,
            "cost": job.cost,
            "model": job.model,
            "tool_results": job.tool_results,
        }
    return {
        "ok": True,
        "data": {
            "job_id": job.id,
            "status": job.status,
            "seq": job.seq,
            "events": events,
            "done": done,
            "error": job.error or None,
        },
    }


@router.post("/api/v1/chat/jobs/{job_id}/cancel")
async def llm_chat_job_cancel(job_id: str):
    """Cancel a running chat job (Stop button)."""
    cancelled = _jobs.manager.cancel(job_id)
    return {"ok": True, "data": {"job_id": job_id, "cancelled": cancelled}}
