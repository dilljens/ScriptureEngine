"""
Scripture Knowledge Engine — Database schema and operations.
"""

import json
import sqlite3
from pathlib import Path

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "processed" / "scripture.db"


def get_db(db_path=None):
    """Get a database connection with row factory."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -8000")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db_vec(db_path=None):
    """Get a database connection with sqlite-vec extension loaded."""
    import sqlite_vec
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -8000")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA trusted_schema=ON")  # Required for extension loading
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    return conn


SCHEMA_SQL = """
-- Works (canonical divisions)
CREATE TABLE IF NOT EXISTS works (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT
);

-- Books
CREATE TABLE IF NOT EXISTS books (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES works(id),
    title TEXT NOT NULL,
    subtitle TEXT,
    position INTEGER NOT NULL
);

-- Verses (canonical text)
CREATE TABLE IF NOT EXISTS verses (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES books(id),
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text_english TEXT NOT NULL DEFAULT '',
    text_hebrew TEXT DEFAULT '',
    text_hebrew_translit TEXT DEFAULT '',
    text_greek TEXT DEFAULT '',
    has_hebrew INTEGER DEFAULT 0,
    has_greek INTEGER DEFAULT 0,
    heading TEXT DEFAULT ''
);

-- Hebrew gematria values (pre-computed per word)
CREATE TABLE IF NOT EXISTS gematria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    word_index INTEGER NOT NULL,
    word_hebrew TEXT NOT NULL,
    word_english TEXT DEFAULT '',
    lemma TEXT DEFAULT '',
    morph TEXT DEFAULT '',
    value_standard INTEGER DEFAULT 0,
    value_ordinal INTEGER DEFAULT 0,
    value_reduced INTEGER DEFAULT 0,
    value_mispar_gadol INTEGER DEFAULT 0
);

-- Greek isopsephy values (pre-computed per word)
CREATE TABLE IF NOT EXISTS gematria_greek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    word_index INTEGER NOT NULL,
    word_greek TEXT NOT NULL,
    lemma TEXT DEFAULT '',
    morph TEXT DEFAULT '',
    value_standard INTEGER DEFAULT 0,
    value_ordinal INTEGER DEFAULT 0,
    value_reduced INTEGER DEFAULT 0
);

-- Divine names / sacred values reference
CREATE TABLE IF NOT EXISTS divine_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hebrew TEXT NOT NULL,
    transliteration TEXT DEFAULT '',
    value_standard INTEGER NOT NULL,
    value_ordinal INTEGER DEFAULT 0,
    value_reduced INTEGER DEFAULT 0,
    category TEXT DEFAULT 'name'
);

-- Connection graph (typed, layered)
CREATE TABLE IF NOT EXISTS connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL REFERENCES verses(id),
    target_verse TEXT NOT NULL REFERENCES verses(id),
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}',
    hermeneutic TEXT DEFAULT NULL,
    UNIQUE(source_verse, target_verse, layer, type, subtype)
);

-- Passage-level connections (ranges of verses, chapters, or books)
CREATE TABLE IF NOT EXISTS passage_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_start TEXT NOT NULL,       -- gen.40.1
    source_end TEXT NOT NULL,         -- gen.40.23
    target_start TEXT NOT NULL,       -- exod.12.1
    target_end TEXT NOT NULL,         -- exod.12.51
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}',
    hermeneutic TEXT DEFAULT NULL,
    quality_version INTEGER DEFAULT 0,
    UNIQUE(source_start, source_end, target_start, target_end, layer, type, subtype)
);

CREATE INDEX IF NOT EXISTS idx_pc_source ON passage_connections(source_start, source_end);
CREATE INDEX IF NOT EXISTS idx_pc_target ON passage_connections(target_start, target_end);
CREATE INDEX IF NOT EXISTS idx_pc_layer ON passage_connections(layer);
CREATE INDEX IF NOT EXISTS idx_pc_type ON passage_connections(type);

-- Passage-level genre classification
CREATE TABLE IF NOT EXISTS passage_genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    start_verse TEXT NOT NULL,
    end_verse TEXT NOT NULL,
    genre TEXT NOT NULL,
    subgenre TEXT DEFAULT '',
    confidence REAL DEFAULT 0.7,
    assigned_by TEXT DEFAULT 'algorithm',
    notes TEXT DEFAULT '',
    UNIQUE(start_verse, end_verse, genre)
);

CREATE INDEX IF NOT EXISTS idx_pg_genre ON passage_genres(genre);
CREATE INDEX IF NOT EXISTS idx_pg_range ON passage_genres(start_verse, end_verse);

-- Disagreements / contradictions between connections
CREATE TABLE IF NOT EXISTS disagreements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_a_id INTEGER NOT NULL REFERENCES connections(id),
    connection_b_id INTEGER NOT NULL REFERENCES connections(id),
    verse_pair TEXT NOT NULL,
    conflict_score REAL DEFAULT 0.5,
    conflict_type TEXT DEFAULT 'contradictory',
    resolution TEXT DEFAULT 'unresolved',
    resolved_by TEXT DEFAULT '',
    resolved_at TEXT DEFAULT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Frequency / word occurrence data
CREATE TABLE IF NOT EXISTS word_frequency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_english TEXT NOT NULL,
    word_hebrew TEXT DEFAULT '',
    strongs_number TEXT DEFAULT '',
    book_id TEXT REFERENCES books(id),
    count INTEGER DEFAULT 0,
    scope TEXT DEFAULT 'canon'  -- 'canon', 'work', 'book'
);

-- Pattern records (literary patterns found)
CREATE TABLE IF NOT EXISTS patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT REFERENCES books(id),
    start_verse TEXT REFERENCES verses(id),
    end_verse TEXT REFERENCES verses(id),
    pattern_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}'
);

-- Known chiasms from scholarly research (Giliadi, Welch, etc.)
CREATE TABLE IF NOT EXISTS known_chiasms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholar TEXT NOT NULL,
    reference TEXT DEFAULT '',
    book_id TEXT REFERENCES books(id),
    start_verse TEXT REFERENCES verses(id),
    end_verse TEXT REFERENCES verses(id),
    pivot_verse TEXT REFERENCES verses(id),
    chiasm_type TEXT DEFAULT '',  -- 'word_level', 'thematic', 'word_count', 'integral'
    layers_json TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.7,
    discovered_by TEXT DEFAULT 'human',
    notes TEXT DEFAULT '',
    source_url TEXT DEFAULT ''
);

-- Structural formula markers (pre-computed per book)
CREATE TABLE IF NOT EXISTS structural_formulas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT REFERENCES books(id),
    verse_id TEXT REFERENCES verses(id),
    formula_type TEXT NOT NULL,  -- 'toledot', 'god_said', 'came_to_pass', etc.
    formula_text TEXT NOT NULL,
    position INTEGER NOT NULL    -- sequential position within the book
);

-- Cross-lingual entity links (for Hebrew↔Greek↔English alignment)
CREATE TABLE IF NOT EXISTS entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL UNIQUE,      -- canonical ID like 'person.jacob', 'place.bethel'
    entity_type TEXT DEFAULT '',          -- 'person', 'place', 'concept', 'object', 'event'
    english_name TEXT DEFAULT '',
    hebrew_name TEXT DEFAULT '',
    hebrew_strongs TEXT DEFAULT '',
    greek_name TEXT DEFAULT '',
    greek_strongs TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);

-- Verse-to-entity links (people, places, concepts linked to verses)
CREATE TABLE IF NOT EXISTS verse_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    entity_id TEXT NOT NULL REFERENCES entity_links(entity_id),
    relationship_type TEXT NOT NULL DEFAULT 'mentions',
    confidence REAL DEFAULT 0.5,
    UNIQUE(verse_id, entity_id, relationship_type)
);

-- Topic collections (user-definable groupings of verses)
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES topics(id),
    description TEXT DEFAULT '',
    color TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);

-- Topic ↔ verse membership
CREATE TABLE IF NOT EXISTS topic_verses (
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    note TEXT DEFAULT '',
    PRIMARY KEY (topic_id, verse_id)
);

-- User preferences for layer visibility in UI
CREATE TABLE IF NOT EXISTS ui_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pref_key TEXT NOT NULL UNIQUE,
    pref_value TEXT NOT NULL
);

-- Custom user-created tabs (top-level + subtab groupings)
CREATE TABLE IF NOT EXISTS custom_tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES custom_tabs(id),
    icon TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_by TEXT DEFAULT 'user',
    created_at TEXT DEFAULT (datetime('now'))
);

-- Tab content: which texts/verses/queries a tab shows
CREATE TABLE IF NOT EXISTS tab_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tab_id INTEGER NOT NULL REFERENCES custom_tabs(id),
    content_type TEXT NOT NULL DEFAULT 'verses',  -- 'verses', 'query', 'study_guide'
    content_value TEXT NOT NULL,                   -- verse IDs, search query, or guide ID
    label TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);

-- AI-guided study paths (exploration through the connection graph)
CREATE TABLE IF NOT EXISTS study_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',          -- 'angel_of_the_lord', 'zodiac', 'covenant', etc.
    seed_verse TEXT REFERENCES verses(id),
    created_by TEXT DEFAULT 'ai',   -- 'ai', 'user', 'shared'
    is_public INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    content_json TEXT DEFAULT '{}'  -- Canonical JSON blob: steps, graph paths, metadata
);

-- Published study snapshots (immutable, shareable via URL)
CREATE TABLE IF NOT EXISTS published_studies (
    id TEXT PRIMARY KEY,
    study_guide_id INTEGER REFERENCES study_guides(id),
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    author_name TEXT DEFAULT 'anonymous',
    author_id TEXT DEFAULT '',
    forked_from TEXT REFERENCES published_studies(id),
    content_json TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    version INTEGER DEFAULT 1,
    view_count INTEGER DEFAULT 0,
    fork_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_published_slug ON published_studies(slug);
CREATE INDEX IF NOT EXISTS idx_published_guide ON published_studies(study_guide_id);

-- Steps in a guided study (the exploration path through connections)
CREATE TABLE IF NOT EXISTS study_guide_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_guide_id INTEGER NOT NULL REFERENCES study_guides(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    title TEXT DEFAULT '',
    explanation TEXT DEFAULT '',     -- AI-generated explanation for this step
    connection_from TEXT DEFAULT '',  -- verse_id this step connects from
    connection_type TEXT DEFAULT '',  -- the connection type that led here
    connection_layer TEXT DEFAULT '',
    choices_json TEXT DEFAULT '[]',  -- [{verse, label, type}, ...] for branching
    notes TEXT DEFAULT '',
    UNIQUE(study_guide_id, step_number)
);

-- Knowledge assessment items (one per high-quality connection)
CREATE TABLE IF NOT EXISTS knowledge_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL,
    connection_type TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    quality_level TEXT NOT NULL,
    star_rating INTEGER NOT NULL,
    pa_r_de_s_level TEXT NOT NULL,
    layer TEXT NOT NULL,
    difficulty REAL DEFAULT 0.5,
    bloom_level TEXT DEFAULT 'remember',
    item_metadata TEXT DEFAULT '{}',
    UNIQUE(verse_id, connection_type, target_verse)
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_layer ON knowledge_items(layer);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_pardes ON knowledge_items(pa_r_de_s_level);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_verse ON knowledge_items(verse_id);

-- Knowledge prerequisite edges (for adaptive assessment)
CREATE TABLE IF NOT EXISTS knowledge_prerequisites (
    item_id INTEGER NOT NULL,
    prerequisite_item_id INTEGER NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'rule',       -- 'rule', 'query_algorithm', 'human'
    PRIMARY KEY (item_id, prerequisite_item_id),
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id),
    FOREIGN KEY (prerequisite_item_id) REFERENCES knowledge_items(id)
);

-- Auto-generated assessment items from knowledge domain
CREATE TABLE IF NOT EXISTS assessment_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    knowledge_item_id INTEGER,
    question_type TEXT NOT NULL,       -- 'multiple_choice', 'true_false', 'classification'
    question_text TEXT NOT NULL,
    options_json TEXT DEFAULT '[]',
    correct_answer TEXT NOT NULL,
    layer TEXT NOT NULL,
    bloom_level TEXT DEFAULT 'remember',
    difficulty REAL DEFAULT 0.5,
    discrimination REAL DEFAULT 1.0,
    guess_param REAL DEFAULT 0.15,
    slip_param REAL DEFAULT 0.10,
    source_knowledge_item_id INTEGER
);

-- Multi-version Bible text (alternative translations)
CREATE TABLE IF NOT EXISTS text_resources (
    verse_id TEXT NOT NULL,
    version TEXT NOT NULL,              -- 'KJV', 'WEB', 'LEB', 'BSB', 'YLT'
    text TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'eng',-- 'eng','grc','heb','lat'
    is_default INTEGER DEFAULT 0,       -- 1 if this is the default version
    metadata TEXT DEFAULT '{}',
    PRIMARY KEY (verse_id, version)
);
CREATE INDEX IF NOT EXISTS idx_text_resources_version ON text_resources(version);

-- Joseph Smith teachings corpus (sermons, letters, writings)
CREATE TABLE IF NOT EXISTS js_sources (
    ref_id TEXT PRIMARY KEY,             -- e.g., "js.1844.04.07" for King Follett
    title TEXT NOT NULL,                 -- Discourse title
    date TEXT DEFAULT '',                -- ISO date: "1844-04-07"
    source_type TEXT NOT NULL DEFAULT 'sermon', -- 'sermon', 'letter', 'writing', 'interview', 'diary'
    location TEXT DEFAULT '',            -- Where delivered/written
    source TEXT DEFAULT '',              -- Source manuscript (e.g., "Wilford Woodruff Diary")
    text TEXT NOT NULL,                  -- Full text of the teaching
    metadata TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_js_sources_date ON js_sources(date);
CREATE INDEX IF NOT EXISTS idx_js_sources_type ON js_sources(source_type);

-- Full-text search for JS teachings
CREATE VIRTUAL TABLE IF NOT EXISTS js_sources_fts USING fts5(
    title, text, content=js_sources, content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS js_sources_ai AFTER INSERT ON js_sources BEGIN
    INSERT INTO js_sources_fts(rowid, title, text) VALUES (new.rowid, new.title, new.text);
END;
CREATE TRIGGER IF NOT EXISTS js_sources_ad AFTER DELETE ON js_sources BEGIN
    INSERT INTO js_sources_fts(js_sources_fts, rowid, title, text) VALUES('delete', old.rowid, old.title, old.text);
END;
CREATE TRIGGER IF NOT EXISTS js_sources_au AFTER UPDATE ON js_sources BEGIN
    INSERT INTO js_sources_fts(js_sources_fts, rowid, title, text) VALUES('delete', old.rowid, old.title, old.text);
    INSERT INTO js_sources_fts(rowid, title, text) VALUES (new.rowid, new.title, new.text);
END;

-- Staging — proposed connections (LLM/UI → dev review → approved)
CREATE TABLE IF NOT EXISTS staging_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    metadata TEXT DEFAULT '{}',
    reasoning TEXT DEFAULT '',           -- LLM's explanation
    status TEXT DEFAULT 'pending',       -- pending | approved | rejected
    submitted_by TEXT DEFAULT '',        -- 'llm', 'webui', 'cli'
    submitted_at TEXT DEFAULT (datetime('now')),
    reviewed_by TEXT DEFAULT '',
    reviewed_at TEXT,
    rejection_reason TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_staging_conn_status ON staging_connections(status);
CREATE INDEX IF NOT EXISTS idx_staging_conn_layer ON staging_connections(layer);

-- Staging — proposed study guides (LLM/UI drafts → dev review → published)
CREATE TABLE IF NOT EXISTS staging_studies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    seed_verse TEXT DEFAULT '',
    steps_json TEXT DEFAULT '[]',        -- JSON array of {step_number, verse, title, explanation, choices}
    metadata TEXT DEFAULT '{}',
    status TEXT DEFAULT 'draft',         -- draft | submitted | approved | rejected
    submitted_by TEXT DEFAULT '',
    submitted_at TEXT DEFAULT (datetime('now')),
    reviewed_by TEXT DEFAULT '',
    reviewed_at TEXT,
    rejection_reason TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_staging_studies_status ON staging_studies(status);

-- Dead Sea Scrolls biblical text variants
CREATE TABLE IF NOT EXISTS dss_texts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scroll_id TEXT NOT NULL,
    scroll_name TEXT DEFAULT '',
    document_type TEXT DEFAULT '',
    bible_ref TEXT DEFAULT '',
    dss_hebrew TEXT DEFAULT '',
    mt_hebrew TEXT DEFAULT '',
    variant_description TEXT DEFAULT '',
    transcription_notes TEXT DEFAULT '',
    has_variant INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dss_sectarian (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scroll_id TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    bible_parallels TEXT DEFAULT ''
);

-- Symbol reference table (known scriptural symbols)
CREATE TABLE IF NOT EXISTS symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT '',    -- 'animal', 'object', 'being', 'color', 'number', 'plant', 'food', 'element', 'garment', 'material', 'body_part', 'action', 'place', 'time'
    meaning TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    ai_discovered INTEGER DEFAULT 0
);

-- Symbol occurrences (which verses use which symbols)
CREATE TABLE IF NOT EXISTS symbol_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL REFERENCES symbols(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    is_symbolic INTEGER DEFAULT 1,       -- 1=symbolic use, 0=literal mention
    strength REAL DEFAULT 0.5,
    context_note TEXT DEFAULT '',
    UNIQUE(symbol_id, verse_id)
);

-- Known typology pairs (type → antitype)
CREATE TABLE IF NOT EXISTS typology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL,
    antitype_name TEXT NOT NULL,
    type_verse TEXT REFERENCES verses(id),
    antitype_verse TEXT REFERENCES verses(id),
    description TEXT DEFAULT '',
    connection_layer TEXT DEFAULT 'symbolic',
    UNIQUE(type_verse, antitype_verse)
);

-- Interpretive disagreements (contradictory connections across traditions)
CREATE TABLE IF NOT EXISTS interpretive_disagreements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL,
    tradition_a TEXT NOT NULL,
    tradition_b TEXT NOT NULL,
    connection_a_id INTEGER,
    connection_b_id INTEGER,
    description TEXT NOT NULL,
    resolved_by TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (connection_a_id) REFERENCES connections(id),
    FOREIGN KEY (connection_b_id) REFERENCES connections(id)
);

CREATE INDEX IF NOT EXISTS idx_disagreements_verse ON interpretive_disagreements(verse_id);

-- Official LDS footnotes (from churchofjesuschrist.org API)
CREATE TABLE IF NOT EXISTS footnotes (
    id TEXT PRIMARY KEY,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    marker TEXT NOT NULL,
    word_index INTEGER,
    context_word TEXT,
    category TEXT,
    body_html TEXT,
    reference_data TEXT DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_footnotes_verse ON footnotes(verse_id);
CREATE INDEX IF NOT EXISTS idx_footnotes_cat ON footnotes(verse_id, category);

-- Resolved cross-references from footnotes
CREATE TABLE IF NOT EXISTS cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL REFERENCES verses(id),
    target_verse TEXT NOT NULL REFERENCES verses(id),
    footnote_id TEXT REFERENCES footnotes(id),
    confidence REAL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_xref_source ON cross_references(source_verse);
CREATE INDEX IF NOT EXISTS idx_xref_target ON cross_references(target_verse);
CREATE UNIQUE INDEX IF NOT EXISTS idx_xref_pair ON cross_references(source_verse, target_verse);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_verses_book_chapter ON verses(book_id, chapter, verse);
CREATE INDEX IF NOT EXISTS idx_gematria_verse ON gematria(verse_id);
CREATE INDEX IF NOT EXISTS idx_gematria_value_std ON gematria(value_standard);
CREATE INDEX IF NOT EXISTS idx_gematria_greek_verse ON gematria_greek(verse_id);
CREATE INDEX IF NOT EXISTS idx_gematria_greek_value ON gematria_greek(value_standard);
CREATE INDEX IF NOT EXISTS idx_verses_has_greek ON verses(has_greek);
CREATE INDEX IF NOT EXISTS idx_connections_source ON connections(source_verse);
CREATE INDEX IF NOT EXISTS idx_connections_target ON connections(target_verse);
CREATE INDEX IF NOT EXISTS idx_connections_layer ON connections(layer, type);
CREATE INDEX IF NOT EXISTS idx_connections_src_tgt_layer ON connections(source_verse, target_verse, layer);
CREATE INDEX IF NOT EXISTS idx_patterns_book ON patterns(book_id);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_word_freq_word ON word_frequency(word_english);
CREATE INDEX IF NOT EXISTS idx_known_chiasms_book ON known_chiasms(book_id);
CREATE INDEX IF NOT EXISTS idx_known_chiasms_scholar ON known_chiasms(scholar);
CREATE INDEX IF NOT EXISTS idx_struct_formulas_book ON structural_formulas(book_id);
CREATE INDEX IF NOT EXISTS idx_struct_formulas_type ON structural_formulas(formula_type);
CREATE INDEX IF NOT EXISTS idx_verse_entities_verse ON verse_entities(verse_id);
CREATE INDEX IF NOT EXISTS idx_verse_entities_entity ON verse_entities(entity_id);

-- Conversation tracking (LLM chat sessions)
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id TEXT PRIMARY KEY,
    title TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    created_by TEXT DEFAULT 'anonymous',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    message_count INTEGER DEFAULT 0,
    is_starred INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    timestamp TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_conv_msg_session ON conversation_messages(session_id);

CREATE TABLE IF NOT EXISTS conversation_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    context TEXT DEFAULT '',
    confidence REAL DEFAULT 1.0,
    UNIQUE(message_id, verse_id)
);
CREATE INDEX IF NOT EXISTS idx_conv_refs_session ON conversation_refs(session_id);

CREATE TABLE IF NOT EXISTS conversation_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    source_verse TEXT NOT NULL REFERENCES verses(id),
    target_verse TEXT NOT NULL REFERENCES verses(id),
    relationship TEXT DEFAULT '',
    connection_type TEXT NOT NULL DEFAULT 'discovered'
        CHECK(connection_type IN ('discovered','retrieved','suggested')),
    existing_connection_id INTEGER,
    confidence REAL DEFAULT 0.5,
    description TEXT DEFAULT '',
    context_message TEXT DEFAULT '',
    promoted INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(session_id, source_verse, target_verse)
);
CREATE INDEX IF NOT EXISTS idx_conv_conn_session ON conversation_connections(session_id);

-- Audio alignment timestamps for verse-level and word-level audio
CREATE TABLE IF NOT EXISTS audio_timestamps (
    verse_id TEXT PRIMARY KEY REFERENCES verses(id),
    book_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    audio_source TEXT DEFAULT 'shmuelof',
    word_timestamps TEXT DEFAULT '[]',
    source_file TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Hebrew word images (FreeBibleImages, AI generation, etc.)
CREATE TABLE IF NOT EXISTS word_images (
    word_hebrew TEXT NOT NULL,
    node_id TEXT,
    source TEXT DEFAULT 'freebible',
    image_url TEXT NOT NULL,
    attribution TEXT DEFAULT '',
    width INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    prompt TEXT DEFAULT '',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (word_hebrew, source)
);

-- Generator metadata for incremental generation
CREATE TABLE IF NOT EXISTS generator_meta (
    generator_name TEXT PRIMARY KEY,
    last_run_at TEXT NOT NULL,
    source_hash TEXT,        -- hash of input data at last run
    connection_count INTEGER,
    duration_ms INTEGER
);

-- Auth / cross-device sync
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    google_id TEXT UNIQUE,
    email TEXT UNIQUE,
    name TEXT DEFAULT '',
    avatar_url TEXT DEFAULT '',
    anon_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    last_login TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS recovery_keys (
    key_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    user_data TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    claimed_at TEXT,
    claimed_by TEXT
);
CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT NOT NULL,
    pref_key TEXT NOT NULL,
    pref_value TEXT NOT NULL DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, pref_key)
);
"""


def init_db(db_path=None):
    """Initialize the database schema."""
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db(path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def verse_id(book, chapter, verse):
    """Create a canonical verse ID."""
    return f"{book}.{chapter}.{verse}"


def resolve_verse_id(conn, book, chapter, verse):
    """Try all known verse ID patterns for a (book, chapter, verse) triple.

    Returns (verse_id, row) or (None, None).
    Works for standard works (gen.1.1), DSS dss-prefixed IDs, etc.
    """
    # Standard format
    vid = f"{book}.{chapter}.{verse}"
    row = conn.execute("SELECT * FROM verses WHERE id=?", (vid,)).fetchone()
    if row:
        return vid, dict(row)

    # DSS format: dss.{book}.{chapter}.{verse}
    dss_vid = f"dss.{book}.{chapter}.{verse}"
    # But DSS lines have chapter=1 always, so book.line = book.1.line
    # The DSS verse ID is actually: dss.{book}.1.{line}, and line=verse param
    # Let's check: dss.{book}.{chapter}.{verse}
    if True:  # Try with the given params
        row2 = conn.execute("SELECT * FROM verses WHERE id=?", (dss_vid,)).fetchone()
        if row2:
            return dss_vid, dict(row2)

    # Try just dss.{book}.{verse} (old import format where chapter was implicit)
    # Some older DSS imports used dss.{book}.{line} format
    # But that would be dss.1QS.1 where 1 is the verse/line
    # Already covered above

    return None, None


def parse_verse_id(vid):
    """Parse a verse ID into (book_id, chapter, verse)."""
    parts = vid.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid verse ID: {vid}")
    return parts[0], int(parts[1]), int(parts[2])


def insert_verse(conn, book_id, chapter, verse, text_english, text_hebrew="", heading=""):
    """Insert or update a verse."""
    vid = verse_id(book_id, chapter, verse)
    has_heb = 1 if text_hebrew.strip() else 0
    conn.execute("""
        INSERT INTO verses (id, book_id, chapter, verse, text_english, text_hebrew, has_hebrew, heading)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            text_english = excluded.text_english,
            text_hebrew = excluded.text_hebrew,
            has_hebrew = excluded.has_hebrew,
            heading = excluded.heading
    """, (vid, book_id, chapter, verse, text_english, text_hebrew, has_heb, heading))


def insert_gematria(conn, verse_id, word_index, word_hebrew, word_english="",
                    lemma="", morph="", values=None):
    """Insert a gematria record."""
    values = values or {}
    conn.execute("""
        INSERT INTO gematria (verse_id, word_index, word_hebrew, word_english,
                              lemma, morph, value_standard, value_ordinal,
                              value_reduced, value_mispar_gadol)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (verse_id, word_index, word_hebrew, word_english, lemma, morph,
          values.get("standard", 0), values.get("ordinal", 0),
          values.get("reduced", 0), values.get("mispar_gadol", 0)))


def get_verse(conn, book, chapter, verse):
    """Look up a single verse by book, chapter, verse.

    Supports all works — standard (gen.1.1), DSS (dss.1QS.1), etc.
    Tries multiple ID patterns:
      1. {book}.{chapter}.{verse}      — standard (gen.1.1)
      2. dss.{book}.{chapter}.{verse}  — DSS with chapter (dss.1QS.1.1)
      3. dss.{book}.{verse}            — DSS no chapter (dss.1QS.1)
    """
    patterns = [
        f"{book}.{chapter}.{verse}",              # standard
        f"dss.{book}.{chapter}.{verse}",           # dss with chapter
        f"dss.{book}.{verse}",                     # dss without chapter
    ]

    for vid in patterns:
        row = conn.execute("""
            SELECT v.*, b.title as book_title, b.work_id
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.id = ?
        """, (vid,)).fetchone()
        if row:
            return dict(row)

    return None


def _ngrams(text, n=3):
    """Generate n-gram tokens from text."""
    text = text.strip()
    if len(text) < n:
        return [text] if text else []
    return [text[i:i+n] for i in range(len(text) - n + 1)]


def search_verses(conn, query, book_id=None, limit=20):
    """Search verses by text content.

    Uses trigram FTS5 for substring matching with BM25 ranking.
    Falls back to LIKE % for typo tolerance.
    """
    # Helper for LIKE fallback
    def _like_fallback(q):
        sql = """
            SELECT v.*, b.title as book_title, b.work_id
            FROM verses v
            JOIN books b ON b.id = v.book_id
            WHERE v.text_english LIKE ?
        """
        params = [f"%{q}%"]
        if book_id:
            if book_id == "dc":
                sql += " AND (v.book_id LIKE 'dc%' OR b.work_id = 'dc')"
            else:
                sql += " AND v.book_id = ?"
                params.append(book_id)
        sql += " LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def _fts_search(q, and_mode=True):
        nonlocal book_id
        if len(q) < 2:
            return None
        sanitized = q.replace('"', '""').replace("^", " ").replace("*", " ").strip()
        # For OR mode, decompose into individual trigrams
        if not and_mode:
            ngrams = _ngrams(sanitized, 3)
            if len(ngrams) >= 2:
                sanitized = " OR ".join(f'"{g}"' for g in ngrams if len(g) == 3)
            else:
                return None  # Single trigram can't do OR
        if book_id:
            rows = conn.execute("""
                SELECT v.*, b.title as book_title, b.work_id
                FROM verses_fts_trigram f
                JOIN verses v ON v.id = f.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE verses_fts_trigram MATCH ?
                AND (b.id = ? OR b.id LIKE ?)
                ORDER BY rank
                LIMIT ?
            """, (sanitized, book_id, f"{book_id}%", limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT v.*, b.title as book_title, b.work_id
                FROM verses_fts_trigram f
                JOIN verses v ON v.id = f.verse_id
                JOIN books b ON b.id = v.book_id
                WHERE verses_fts_trigram MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (sanitized, limit)).fetchall()
        return [dict(r) for r in rows] if rows else None

    # 1. Try AND trigram (exact trigram overlap)
    try:
        result = _fts_search(query, and_mode=True)
        if result:
            return result
    except Exception:
        pass

    # 2. Try OR trigram (typo-tolerant)
    try:
        result = _fts_search(query, and_mode=False)
        if result:
            return result
    except Exception:
        pass

    # 3. Fallback to LIKE
    return _like_fallback(query)


def search_by_strongs(conn, strongs, limit=50):
    """Find verses containing a word with a given Strong's number."""
    rows = conn.execute("""
        SELECT g.verse_id, g.word_hebrew, g.word_english, g.value_standard,
               v.text_english, b.title as book_title
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.lemma LIKE ?
        LIMIT ?
    """, (f"%{strongs}%", limit)).fetchall()
    return [dict(r) for r in rows]


def get_connections(conn, verse_id, layer=None):
    """Get all connections for a verse, optionally filtered by layer."""
    sql = """
        SELECT c.*, v.text_english as target_text,
               b.title as target_book_title
        FROM connections c
        JOIN verses v ON v.id = c.target_verse
        JOIN books b ON b.id = v.book_id
        WHERE c.source_verse = ?
    """
    params = [verse_id]
    if layer:
        sql += " AND c.layer = ?"
        params.append(layer)
    sql += " ORDER BY c.layer, c.strength DESC"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_connections_by_layer(conn, verse_id):
    """Get connections grouped by layer."""
    rows = get_connections(conn, verse_id)
    by_layer = {}
    for r in rows:
        layer = r["layer"]
        if layer not in by_layer:
            by_layer[layer] = []
        by_layer[layer].append(r)
    return by_layer


def add_connection(conn, source_verse, target_verse, layer, type_name,
                   subtype="", strength=0.5, confidence=0.5,
                   discovered_by="algorithm", metadata=None):
    """Add a typed connection between two verses."""
    meta_json = json.dumps(metadata or {})
    try:
        conn.execute("""
            INSERT INTO connections (source_verse, target_verse, layer, type,
                                     subtype, strength, confidence, discovered_by, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_verse, target_verse, layer, type, subtype)
            DO UPDATE SET strength = excluded.strength,
                          confidence = excluded.confidence,
                          discovered_by = excluded.discovered_by,
                          metadata = excluded.metadata
        """, (source_verse, target_verse, layer, type_name, subtype,
              strength, confidence, discovered_by, meta_json))
        conn.commit()
    except sqlite3.IntegrityError:
        # Missing verse reference -- skip gracefully
        pass


def get_gematria_for_verse(conn, verse_id):
    """Get all gematria records for a verse."""
    rows = conn.execute("""
        SELECT * FROM gematria WHERE verse_id = ? ORDER BY word_index
    """, (verse_id,)).fetchall()
    return [dict(r) for r in rows]


def get_verse_gematria_total(conn, verse_id):
    """Get the total gematria of a verse (sum of all words)."""
    row = conn.execute("""
        SELECT COALESCE(SUM(value_standard), 0) as total_std,
               COALESCE(SUM(value_ordinal), 0) as total_ord,
               COALESCE(SUM(value_reduced), 0) as total_red
        FROM gematria WHERE verse_id = ?
    """, (verse_id,)).fetchone()
    if row:
        return dict(row)
    return {"total_std": 0, "total_ord": 0, "total_red": 0}


def find_matching_gematria(conn, value, system="standard", limit=50):
    """Find all words/verses with a matching gematria value."""
    col = {"standard": "value_standard", "ordinal": "value_ordinal",
           "reduced": "value_reduced"}.get(system, "value_standard")
    rows = conn.execute(f"""
        SELECT g.*, v.text_english, b.title as book_title, v.id as vid
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE g.{col} = ?
        LIMIT ?
    """, (value, limit)).fetchall()
    return [dict(r) for r in rows]


def get_book_info(conn, book_id):
    """Get book metadata."""
    row = conn.execute("""
        SELECT b.*, w.title as work_title
        FROM books b
        JOIN works w ON w.id = b.work_id
        WHERE b.id = ?
    """, (book_id,)).fetchall()
    return dict(row[0]) if row else None


def get_chapter(conn, book_id, chapter):
    """Get all verses in a chapter."""
    rows = conn.execute("""
        SELECT v.*, b.title as book_title, b.work_id
        FROM verses v
        JOIN books b ON b.id = v.book_id
        WHERE v.book_id = ? AND v.chapter = ?
        ORDER BY v.verse
    """, (book_id, chapter)).fetchall()
    return [dict(r) for r in rows]


def get_word_frequency(conn, word, scope="canon"):
    """Get frequency data for a word."""
    rows = conn.execute("""
        SELECT * FROM word_frequency
        WHERE word_english = ? AND scope = ?
        ORDER BY count DESC
    """, (word, scope)).fetchall()
    return [dict(r) for r in rows]


# === Known Chiasms ===

def add_known_chiasm(conn, scholar, book_id, start_verse, end_verse,
                     pivot_verse="", chiasm_type="", layers_json="[]",
                     confidence=0.7, notes="", source_url="", reference=""):
    """Add a known chiasm from scholarly research."""
    conn.execute("""
        INSERT INTO known_chiasms
            (scholar, reference, book_id, start_verse, end_verse,
             pivot_verse, chiasm_type, layers_json, confidence,
             discovered_by, notes, source_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'human', ?, ?)
    """, (scholar, reference, book_id, start_verse, end_verse,
          pivot_verse, chiasm_type, layers_json, confidence,
          notes, source_url))
    conn.commit()


def get_known_chiasms(conn, book_id=None, scholar=None, limit=50):
    """Get known chiasms, optionally filtered by book or scholar."""
    sql = """
        SELECT kc.*, b.title as book_title
        FROM known_chiasms kc
        JOIN books b ON b.id = kc.book_id
        WHERE 1=1
    """
    params = []
    if book_id:
        sql += " AND kc.book_id = ?"
        params.append(book_id)
    if scholar:
        sql += " AND kc.scholar = ?"
        params.append(scholar)
    sql += " ORDER BY kc.book_id, kc.start_verse LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def find_matching_known_chiasm(conn, start_verse, end_verse, threshold=0.8):
    """Check if a passage matches any known chiasm."""
    rows = conn.execute("""
        SELECT * FROM known_chiasms
        WHERE start_verse <= ? AND end_verse >= ?
           OR (start_verse >= ? AND end_verse <= ?)
        ORDER BY confidence DESC
    """, (start_verse, end_verse, start_verse, end_verse)).fetchall()
    return [dict(r) for r in rows]


# === Structural Formulas ===

def add_formula_marker(conn, book_id, verse_id, formula_type, formula_text, position):
    """Record a structural formula marker."""
    conn.execute("""
        INSERT INTO structural_formulas (book_id, verse_id, formula_type, formula_text, position)
        VALUES (?, ?, ?, ?, ?)
    """, (book_id, verse_id, formula_type, formula_text, position))


def get_formula_sequence(conn, book_id, formula_types=None):
    """Get the sequence of formula markers for a book, in order."""
    sql = """
        SELECT sf.*, v.text_english
        FROM structural_formulas sf
        JOIN verses v ON v.id = sf.verse_id
        WHERE sf.book_id = ?
    """
    params = [book_id]
    if formula_types:
        placeholders = ",".join("?" for _ in formula_types)
        sql += f" AND sf.formula_type IN ({placeholders})"
        params.extend(formula_types)
    sql += " ORDER BY sf.position"
    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def get_word_counts_by_chapter(conn, book_id):
    """Get Hebrew word count per chapter for a book."""
    rows = conn.execute("""
        SELECT v.chapter, COUNT(g.id) as heb_word_count
        FROM verses v
        LEFT JOIN gematria g ON g.verse_id = v.id
        WHERE v.book_id = ? AND v.has_hebrew = 1
        GROUP BY v.chapter
        ORDER BY v.chapter
    """, (book_id,)).fetchall()
    return [dict(r) for r in rows]


def get_word_counts_by_verse_range(conn, start_verse, end_verse):
    """Get total Hebrew word count for a range of verse IDs."""
    # Parse verse IDs for proper numeric comparison
    parts_s = start_verse.split(".")
    parts_e = end_verse.split(".")
    if len(parts_s) == 3 and len(parts_e) == 3:
        book = parts_s[0]
        start_ch = int(parts_s[1])
        start_v = int(parts_s[2])
        end_ch = int(parts_e[1])
        end_v = int(parts_e[2])
        row = conn.execute("""
            SELECT COUNT(g.id) as word_count
            FROM gematria g
            JOIN verses v ON v.id = g.verse_id
            WHERE v.book_id = ?
            AND (v.chapter > ? OR (v.chapter = ? AND v.verse >= ?))
            AND (v.chapter < ? OR (v.chapter = ? AND v.verse <= ?))
        """, (book, start_ch, start_ch, start_v, end_ch, end_ch, end_v)).fetchone()
        return dict(row)["word_count"] if row else 0
    # Fallback to string comparison for single-verse cases
    row = conn.execute("""
        SELECT COUNT(g.id) as word_count
        FROM gematria g
        JOIN verses v ON v.id = g.verse_id
        WHERE v.id >= ? AND v.id <= ?
    """, (start_verse, end_verse)).fetchone()
    return dict(row)["word_count"] if row else 0


def get_keyword_distribution(conn, book_id, terms, scope="chapter"):
    """Get distribution of key Hebrew terms across a book.

    Args:
        terms: list of Hebrew words (with niqqud) or Strong's numbers
    """
    results = {}
    for term in terms:
        if any('\u0590' <= c <= '\u05FF' for c in term):
            # Hebrew: extract consonants and interleave with % to skip niqqud
            cons = ""
            for c in term:
                cp = ord(c)
                if (0x05D0 <= cp <= 0x05EA) or (0x05EF <= cp <= 0x05F2):
                    cons += c
            like_pattern = f"%{'%'.join(cons)}%" if cons else f"%{term}%"

            # Also check if this is a known divine name (search by gematria value)
            # Known divine name values (avoid circular imports)
            DIVINE_VALUES = {"יהוה": 26, "אלהים": 86, "אדני": 65, "אל שדי": 345,
                            "אל": 31, "שדי": 314, "ישוע": 386, "משיח": 358}
            value_match = DIVINE_VALUES.get(term)

            if value_match:
                rows = conn.execute("""
                    SELECT v.chapter, COUNT(*) as count
                    FROM gematria g
                    JOIN verses v ON v.id = g.verse_id
                    WHERE v.book_id = ? AND g.value_standard = ?
                    GROUP BY v.chapter ORDER BY v.chapter
                """, (book_id, value_match)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT v.chapter, COUNT(*) as count
                    FROM gematria g
                    JOIN verses v ON v.id = g.verse_id
                    WHERE v.book_id = ? AND g.word_hebrew LIKE ?
                    GROUP BY v.chapter ORDER BY v.chapter
                """, (book_id, like_pattern)).fetchall()
        else:
            # Non-Hebrew: search as lemma or plain text
            rows = conn.execute("""
                SELECT v.chapter, COUNT(*) as count
                FROM gematria g
                JOIN verses v ON v.id = g.verse_id
                WHERE v.book_id = ? AND (g.lemma LIKE ? OR g.word_hebrew LIKE ?)
                GROUP BY v.chapter ORDER BY v.chapter
            """, (book_id, f"%{term}%", f"%{term}%")).fetchall()

        results[term] = {r["chapter"]: r["count"] for r in rows}
    return results


def get_section_verses(conn, start_verse, end_verse):
    """Get all verses in a section, with Hebrew word counts.

    Uses proper numeric chapter/verse comparison instead of string IDs.
    """
    parts_s = start_verse.split(".")
    parts_e = end_verse.split(".")
    if len(parts_s) == 3 and len(parts_e) == 3:
        book = parts_s[0]
        start_ch = int(parts_s[1])
        start_v = int(parts_s[2])
        end_ch = int(parts_e[1])
        end_v = int(parts_e[2])
        rows = conn.execute("""
            SELECT v.id, v.chapter, v.verse, v.text_english, v.text_hebrew,
                   COUNT(g.id) as heb_word_count
            FROM verses v
            LEFT JOIN gematria g ON g.verse_id = v.id
            WHERE v.book_id = ?
            AND (v.chapter > ? OR (v.chapter = ? AND v.verse >= ?))
            AND (v.chapter < ? OR (v.chapter = ? AND v.verse <= ?))
            GROUP BY v.id
            ORDER BY v.chapter, v.verse
        """, (book, start_ch, start_ch, start_v, end_ch, end_ch, end_v)).fetchall()
        return [dict(r) for r in rows]
    # Fallback for malformed IDs
    rows = conn.execute("""
        SELECT v.id, v.chapter, v.verse, v.text_english, v.text_hebrew,
               COUNT(g.id) as heb_word_count
        FROM verses v
        LEFT JOIN gematria g ON g.verse_id = v.id
        WHERE v.id >= ? AND v.id <= ?
        GROUP BY v.id
        ORDER BY v.chapter, v.verse
    """, (start_verse, end_verse)).fetchall()
    return [dict(r) for r in rows]


def compare_sections(conn, start_a, end_a, start_b, end_b):
    """Compare two sections and return overlap metrics.

    Args can be verse IDs (e.g., "gen.19.1") or chapter ranges
    (e.g., "gen.19" for entire chapter 19).
    """
    verses_a = get_section_verses(conn, start_a, end_a)
    verses_b = get_section_verses(conn, start_b, end_b)

    word_count_a = sum(v.get("heb_word_count", 0) for v in verses_a)
    word_count_b = sum(v.get("heb_word_count", 0) for v in verses_b)

    # Keyword overlap (English)
    words_a = set()
    for v in verses_a:
        for w in v.get("text_english", "").lower().split():
            if len(w) > 3:
                words_a.add(w)

    words_b = set()
    for v in verses_b:
        for w in v.get("text_english", "").lower().split():
            if len(w) > 3:
                words_b.add(w)

    shared = words_a & words_b
    unique_a = words_a - words_b
    unique_b = words_b - words_a

    overlap_score = len(shared) / max(len(words_a | words_b), 1)

    return {
        "section_a": {"start": start_a, "end": end_a, "word_count": word_count_a, "unique_words": len(words_a)},
        "section_b": {"start": start_b, "end": end_b, "word_count": word_count_b, "unique_words": len(words_b)},
        "word_count_ratio": round(word_count_a / max(word_count_b, 1), 2),
        "shared_keywords": list(shared)[:50],
        "unique_to_a": list(unique_a)[:30],
        "unique_to_b": list(unique_b)[:30],
        "overlap_score": round(overlap_score, 3),
    }


# === Study Guides (AI-guided explorations) ===

def create_study_guide(conn, title, description="", theme="", seed_verse="",
                       created_by="ai", is_public=0):
    """Create a new AI-guided study guide."""
    conn.execute("""
        INSERT INTO study_guides (title, description, theme, seed_verse, created_by, is_public)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, description, theme, seed_verse, created_by, is_public))
    conn.commit()
    row = conn.execute("""
        SELECT id FROM study_guides WHERE title = ? ORDER BY created_at DESC LIMIT 1
    """, (title,)).fetchone()
    return row["id"] if row else None


def add_study_step(conn, guide_id, step_number, verse_id, title="", explanation="",
                   connection_from="", connection_type="", connection_layer="",
                   choices_json="[]"):
    """Add a step to a study guide."""
    conn.execute("""
        INSERT INTO study_guide_steps
            (study_guide_id, step_number, verse_id, title, explanation,
             connection_from, connection_type, connection_layer, choices_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(study_guide_id, step_number) DO UPDATE SET
            verse_id = excluded.verse_id,
            title = excluded.title,
            explanation = excluded.explanation,
            connection_from = excluded.connection_from,
            connection_type = excluded.connection_type,
            connection_layer = excluded.connection_layer,
            choices_json = excluded.choices_json
    """, (guide_id, step_number, verse_id, title, explanation,
          connection_from, connection_type, connection_layer, choices_json))
    conn.commit()


def get_study_guide(conn, guide_id):
    """Get a study guide with all its steps."""
    guide = conn.execute("""
        SELECT * FROM study_guides WHERE id = ?
    """, (guide_id,)).fetchone()
    if not guide:
        return None

    steps = conn.execute("""
        SELECT s.*, v.text_english, v.text_hebrew,
               b.title as book_title, b.id as book_id
        FROM study_guide_steps s
        JOIN verses v ON v.id = s.verse_id
        JOIN books b ON b.id = v.book_id
        WHERE s.study_guide_id = ?
        ORDER BY s.step_number
    """, (guide_id,)).fetchall()

    return {
        "guide": dict(guide),
        "steps": [dict(s) for s in steps],
    }


def list_study_guides(conn, theme=None, limit=20):
    """List all study guides, optionally filtered by theme."""
    sql = """
        SELECT sg.*, COUNT(ss.id) as step_count
        FROM study_guides sg
        LEFT JOIN study_guide_steps ss ON ss.study_guide_id = sg.id
    """
    params = []
    if theme:
        sql += " WHERE sg.theme = ?"
        params.append(theme)
    sql += " GROUP BY sg.id ORDER BY sg.updated_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def search_study_guides(conn, query, limit=10):
    """Search study guides by title or description."""
    rows = conn.execute("""
        SELECT sg.*, COUNT(ss.id) as step_count
        FROM study_guides sg
        LEFT JOIN study_guide_steps ss ON ss.study_guide_id = sg.id
        WHERE sg.title LIKE ? OR sg.description LIKE ? OR sg.theme LIKE ?
        GROUP BY sg.id
        ORDER BY sg.updated_at DESC
        LIMIT ?
    """, (f"%{query}%", f"%{query}%", f"%{query}%", limit)).fetchall()
    return [dict(r) for r in rows]


# === Custom Tabs ===

def create_custom_tab(conn, name, parent_id=None, icon="", sort_order=0):
    """Create a custom tab (top-level or subtab)."""
    conn.execute("""
        INSERT INTO custom_tabs (name, parent_id, icon, sort_order)
        VALUES (?, ?, ?, ?)
    """, (name, parent_id, icon, sort_order))
    conn.commit()
    row = conn.execute("SELECT id FROM custom_tabs WHERE name = ? AND parent_id IS ?",
                      (name, parent_id)).fetchone()
    return row["id"] if row else None


def get_custom_tab_tree(conn):
    """Get the full custom tab tree (top-level tabs with their subtabs)."""
    parents = conn.execute("""
        SELECT * FROM custom_tabs WHERE parent_id IS NULL ORDER BY sort_order, name
    """).fetchall()

    tree = []
    for p in parents:
        children = conn.execute("""
            SELECT * FROM custom_tabs WHERE parent_id = ? ORDER BY sort_order, name
        """, (p["id"],)).fetchall()

        p_dict = dict(p)
        p_dict["children"] = [dict(c) for c in children]

        # Get content for each tab
        for tab in [p_dict] + p_dict["children"]:
            tab["content"] = [
                dict(r) for r in conn.execute("""
                    SELECT * FROM tab_content WHERE tab_id = ? ORDER BY sort_order
                """, (tab["id"],)).fetchall()
            ]

        tree.append(p_dict)

    return tree


def add_tab_content(conn, tab_id, content_type, content_value, label="", sort_order=0):
    """Add content to a tab."""
    conn.execute("""
        INSERT INTO tab_content (tab_id, content_type, content_value, label, sort_order)
        VALUES (?, ?, ?, ?, ?)
    """, (tab_id, content_type, content_value, label, sort_order))
    conn.commit()
