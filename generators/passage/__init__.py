"""Passage-level connection generators.

These generators produce connections in the passage_connections table,
linking verse ranges (passages, chapters, books) rather than individual verses.

Two types:
  1. Aggregation generators — roll up existing verse-level connections
  2. Discovery generators — find passage-level patterns from text directly

Registered in GENERATOR_DEFS (generators/__init__.py). Each exports run(conn, book_ids=None).
"""

from . import (
    book_coherence,
    chiastic_promoter,
    covenant_structure,
    density_cluster,
    genre_tagger,
    interpretation_network,
    macro_chiasm,
    multilingual_network,
    narrative_parallel,
    reception_history,
    rhetorical,
    social_setting,
    source_layers,
    theme_tracer,
    typology,
)

__all__ = [
    "book_coherence",
    "chiastic_promoter",
    "covenant_structure",
    "density_cluster",
    "genre_tagger",
    "interpretation_network",
    "macro_chiasm",
    "multilingual_network",
    "narrative_parallel",
    "reception_history",
    "rhetorical",
    "social_setting",
    "source_layers",
    "theme_tracer",
    "typology",
]
