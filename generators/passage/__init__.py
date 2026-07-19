"""Passage-level connection generators.

These generators produce connections in the passage_connections table,
linking verse ranges (passages, chapters, books) rather than individual verses.

Two types:
  1. Aggregation generators — roll up existing verse-level connections
  2. Discovery generators — find passage-level patterns from text directly

Registered in GENERATOR_DEFS (generators/__init__.py). Each exports run(conn, book_ids=None).
"""

from . import density_cluster
from . import chiastic_promoter
from . import book_coherence
