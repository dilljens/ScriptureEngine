"""Shared in-memory caches loaded at server startup.

These are populated by the lifespan handler in server.py and imported
by route modules that need read-only access.
"""

WIKI_CACHE = {}           # entity/id → article
GUIDE_CACHE = {}          # verse_id → passage guide
VERSE_CACHE = {}          # verse_id → {id, text_english, ...}
ENTITY_CACHE = []         # all entity links
LEXICON_CACHE = {}        # lemma → lexicon entry
LEXICON_CACHE_BY_HEBREW = {}  # hebrew_text → lemma
VEC_CACHE = {"available": False}  # vector search
BOOKS_CACHE = None        # work/book tree
