"""Symbolic layer for the scripture connection graph.

Modules:
  reference.py       — Symbol reference table + seed data
  apocalyptic.py    — Apocalyptic vocabulary (Dan/Ezek/Isa/Rev symbol network)
  shared_symbols.py — Full-canon symbol matching
  typology.py       — Type/antitype connections
"""

from .reference import (
    get_symbol, get_all_symbols, add_symbol, add_occurrence,
    get_occurrences, SEED_SYMBOLS, SEED_APOCALYPTIC, SEED_TYPOLOGY
)
from .apocalyptic import generate_apocalyptic_connections
from .shared_symbols import generate_shared_symbol_connections
from .typology import generate_typology_connections
