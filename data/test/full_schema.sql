CREATE TABLE _vs_type_map(
  source_verse TEXT,
  type TEXT,
  cnt
);

CREATE TABLE assessment_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        knowledge_item_id INTEGER,
        question_type TEXT NOT NULL,
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
    , tier TEXT DEFAULT 'text', explanation TEXT DEFAULT '', question_type_open INTEGER DEFAULT 0);

CREATE TABLE audio_timestamps (
    verse_id TEXT PRIMARY KEY REFERENCES verses(id),
    book_id TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    audio_source TEXT DEFAULT 'schmueloff',
    word_timestamps TEXT DEFAULT '[]',
    source_file TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE bible_dictionary (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        entry_text TEXT NOT NULL,
        summary TEXT DEFAULT '',
        url_path TEXT DEFAULT '',
        word_origin TEXT DEFAULT '',
        related_verses TEXT DEFAULT '[]',
        related_topics TEXT DEFAULT '[]',
        related_entries TEXT DEFAULT '[]',
        raw_html TEXT DEFAULT '',
        last_fetched TEXT
    );

CREATE TABLE books (
    id TEXT PRIMARY KEY,
    work_id TEXT NOT NULL REFERENCES works(id),
    title TEXT NOT NULL,
    subtitle TEXT,
    position INTEGER NOT NULL
);

CREATE TABLE client_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, level TEXT DEFAULT 'error', message TEXT, stack TEXT DEFAULT '', url TEXT DEFAULT '', user_agent TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now')));

CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL REFERENCES verses(id),
    target_verse TEXT NOT NULL REFERENCES verses(id),
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    discovered_by TEXT DEFAULT 'algorithm',
    metadata TEXT DEFAULT '{}', p_value REAL DEFAULT NULL, null_control TEXT DEFAULT "", quality_level TEXT DEFAULT "suggested", quality_version INTEGER DEFAULT 1, deprecated INTEGER DEFAULT 0, deprecation_reason TEXT DEFAULT "", preregistered INTEGER DEFAULT 0, cross_validated INTEGER DEFAULT 0, created_at TEXT DEFAULT '2025-01-01', last_queried TEXT, hit_count INTEGER DEFAULT 0, confirmation_count INTEGER DEFAULT 0, hermeneutic TEXT DEFAULT NULL, tradition TEXT DEFAULT 'none', consensus_score REAL DEFAULT 0.0, tradition_note TEXT DEFAULT '', last_validated TEXT DEFAULT NULL, revalidation_due INTEGER DEFAULT 0, dispute_status TEXT DEFAULT '', disputed_by TEXT DEFAULT '',
    UNIQUE(source_verse, target_verse, layer, type, subtype)
);

CREATE TABLE conversation_connections (
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

CREATE TABLE conversation_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    metadata_json TEXT DEFAULT '{}',
    timestamp TEXT DEFAULT (datetime('now'))
);

CREATE TABLE conversation_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    message_id INTEGER NOT NULL REFERENCES conversation_messages(id) ON DELETE CASCADE,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    context TEXT DEFAULT '',
    confidence REAL DEFAULT 1.0,
    UNIQUE(message_id, verse_id)
);

CREATE TABLE conversation_sessions (
    id TEXT PRIMARY KEY,
    title TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    created_by TEXT DEFAULT 'anonymous',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    message_count INTEGER DEFAULT 0,
    is_starred INTEGER DEFAULT 0
);

CREATE TABLE cross_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL REFERENCES verses(id),
    target_verse TEXT NOT NULL REFERENCES verses(id),
    footnote_id TEXT REFERENCES footnotes(id),
    confidence REAL DEFAULT 1.0
);

CREATE TABLE custom_tabs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    parent_id INTEGER REFERENCES custom_tabs(id),
    icon TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    created_by TEXT DEFAULT 'user',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE disagreements (
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

CREATE TABLE divine_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    hebrew TEXT NOT NULL,
    transliteration TEXT DEFAULT '',
    value_standard INTEGER NOT NULL,
    value_ordinal INTEGER DEFAULT 0,
    value_reduced INTEGER DEFAULT 0,
    category TEXT DEFAULT 'name'
);

CREATE TABLE domain_members (
    domain_id INTEGER NOT NULL REFERENCES semantic_domains(id),
    lemma TEXT NOT NULL REFERENCES lexicon(lemma),
    PRIMARY KEY (domain_id, lemma)
);

CREATE TABLE dss_sectarian (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scroll_id TEXT NOT NULL,
    section TEXT NOT NULL,
    content TEXT NOT NULL,
    content_type TEXT DEFAULT '',
    topic TEXT DEFAULT '',
    bible_parallels TEXT DEFAULT ''
);

CREATE TABLE dss_texts (
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

CREATE TABLE entity_cooccurrence (
            entity_a TEXT NOT NULL,
            entity_b TEXT NOT NULL,
            frequency INTEGER NOT NULL DEFAULT 0,
            avg_confidence REAL DEFAULT 0.0,
            verse_ids TEXT DEFAULT '[]',
            PRIMARY KEY (entity_a, entity_b)
        );

CREATE TABLE entity_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id TEXT NOT NULL UNIQUE,
    entity_type TEXT DEFAULT '',
    english_name TEXT DEFAULT '',
    hebrew_name TEXT DEFAULT '',
    hebrew_strongs TEXT DEFAULT '',
    greek_name TEXT DEFAULT '',
    greek_strongs TEXT DEFAULT '',
    notes TEXT DEFAULT ''
);

CREATE TABLE footnotes (
    id TEXT PRIMARY KEY,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    marker TEXT NOT NULL,
    word_index INTEGER,
    context_word TEXT,
    category TEXT,
    body_html TEXT,
    reference_data TEXT DEFAULT '{}'
);

CREATE TABLE forum_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL REFERENCES forum_topics(id),
    parent_id INTEGER DEFAULT NULL REFERENCES forum_posts(id),
    author TEXT DEFAULT 'anonymous',
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE forum_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    category TEXT DEFAULT 'general',
    created_by TEXT DEFAULT 'anonymous',
    post_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE gematria (
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
, value_milui INTEGER DEFAULT 0, value_kellali INTEGER DEFAULT 0, value_kidmi INTEGER DEFAULT 0, value_boneh INTEGER DEFAULT 0, hebrew_plain TEXT DEFAULT '');

CREATE TABLE gematria_greek (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    word_index INTEGER NOT NULL,
    word_greek TEXT NOT NULL,
    lemma TEXT DEFAULT "",
    morph TEXT DEFAULT "",
    value_standard INTEGER DEFAULT 0,
    value_ordinal INTEGER DEFAULT 0,
    value_reduced INTEGER DEFAULT 0,
    UNIQUE(verse_id, word_index)
);

CREATE TABLE hub_note_progress (
    user_id TEXT NOT NULL DEFAULT 'default',
    hub_id TEXT NOT NULL,
    step_number INTEGER NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (user_id, hub_id, step_number)
);

CREATE TABLE hub_note_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hub_id TEXT NOT NULL REFERENCES hub_notes(id),
    step_number INTEGER NOT NULL,
    verse_id TEXT NOT NULL,
    title TEXT NOT NULL,
    explanation TEXT NOT NULL,
    connection_type TEXT,
    pa_r_de_s_level TEXT,
    tg_topic_ids TEXT DEFAULT '[]',
    UNIQUE(hub_id, step_number)
);

CREATE TABLE hub_notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    theme TEXT NOT NULL,
    icon TEXT DEFAULT '',
    seed_verse TEXT,
    tg_topic_ids TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now')),
    version INTEGER DEFAULT 1
);

CREATE TABLE hub_topic_links (
    hub_id TEXT NOT NULL REFERENCES hub_notes(id),
    topic_id TEXT NOT NULL REFERENCES topical_guide(id),
    relevance_weight REAL DEFAULT 0.5,
    PRIMARY KEY (hub_id, topic_id)
);

CREATE TABLE interpretive_disagreements (
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

CREATE TABLE js_scripture_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    js_ref_id TEXT NOT NULL REFERENCES js_sources(ref_id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    ref_type TEXT NOT NULL DEFAULT 'quotation',
    certainty REAL DEFAULT 0.5,
    notes TEXT DEFAULT '',
    UNIQUE(js_ref_id, verse_id, ref_type)
);

CREATE TABLE js_sources (
    ref_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    date TEXT DEFAULT '',
    source_type TEXT NOT NULL DEFAULT 'sermon',
    location TEXT DEFAULT '',
    source TEXT DEFAULT '',
    text TEXT NOT NULL,
    metadata TEXT DEFAULT '{}'
);

CREATE VIRTUAL TABLE js_sources_fts USING fts5(
    title, text, content=js_sources, content_rowid=rowid
);

CREATE TABLE 'js_sources_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE 'js_sources_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'js_sources_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'js_sources_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE js_texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            source TEXT,
            content TEXT,
            content_tsvector TEXT,
            year INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );

CREATE VIRTUAL TABLE js_texts_fts USING fts5(
                title, content, content=js_texts, content_rowid=id
            );

CREATE TABLE 'js_texts_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE 'js_texts_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'js_texts_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'js_texts_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE knowledge_items (
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

CREATE TABLE knowledge_prerequisites (
    item_id INTEGER NOT NULL,
    prerequisite_item_id INTEGER NOT NULL,
    confidence REAL DEFAULT 1.0,
    source TEXT DEFAULT 'rule',       -- 'rule', 'query_algorithm', 'human'
    PRIMARY KEY (item_id, prerequisite_item_id),
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id),
    FOREIGN KEY (prerequisite_item_id) REFERENCES knowledge_items(id)
);

CREATE TABLE known_chiasms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholar TEXT NOT NULL,
    reference TEXT DEFAULT '',
    book_id TEXT REFERENCES books(id),
    start_verse TEXT REFERENCES verses(id),
    end_verse TEXT REFERENCES verses(id),
    pivot_verse TEXT REFERENCES verses(id),
    chiasm_type TEXT DEFAULT '',
    layers_json TEXT DEFAULT '[]',
    confidence REAL DEFAULT 0.7,
    discovered_by TEXT DEFAULT 'human',
    notes TEXT DEFAULT '',
    source_url TEXT DEFAULT ''
);

CREATE TABLE learning_modules (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT DEFAULT '',
            icon TEXT DEFAULT '📖',
            difficulty INTEGER DEFAULT 1,
            prerequisite_ids TEXT DEFAULT '[]',
            lesson_content TEXT DEFAULT '',
            worked_examples TEXT DEFAULT '[]',
            estimated_minutes INTEGER DEFAULT 10,
            sort_order INTEGER DEFAULT 0
        );

CREATE TABLE learning_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            module_id TEXT NOT NULL REFERENCES learning_modules(id),
            mastery REAL DEFAULT 0.0,
            attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            stability REAL DEFAULT 1.0,
            difficulty REAL DEFAULT 5.0,
            last_review TEXT,
            next_review TEXT,
            PRIMARY KEY (user_id, module_id)
        );

CREATE TABLE lemma_gloss (
            lemma TEXT PRIMARY KEY,
            english_gloss TEXT DEFAULT '',
            frequency INTEGER DEFAULT 0,
            verse_count INTEGER DEFAULT 0
        );

CREATE TABLE lexicon (
    lemma TEXT PRIMARY KEY,                       -- base Strong's number (e.g., "H430")
    hebrew TEXT DEFAULT '',                       -- most common Hebrew spelling
    transliteration TEXT DEFAULT '',               -- phonetic transliteration
    part_of_speech TEXT DEFAULT '',                -- noun, verb, etc. (from morph)
    root_letters TEXT DEFAULT '',                  -- triconsonantal root (e.g., "אלה")
    semantic_domain TEXT DEFAULT '',               -- FK to semantic_domains
    definition TEXT DEFAULT '',                    -- LLM-written in later phase
    definition_source TEXT DEFAULT 'algorithm',    -- 'algorithm', 'ai', 'human'
    frequency INTEGER DEFAULT 0,                   -- total occurrences across canon
    frequency_per_book TEXT DEFAULT '{}',          -- JSON: {"gen": 5, "exo": 20}
    books_list TEXT DEFAULT '',                    -- comma-separated book IDs
    morphology TEXT DEFAULT '',                    -- dominant morph pattern
    ai_generated INTEGER DEFAULT 0,
    reviewed INTEGER DEFAULT 0,
    metadata TEXT DEFAULT '{}'
, hebrew_plain TEXT DEFAULT '');

CREATE TABLE memorize_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            verse_id TEXT NOT NULL,
            mastery REAL DEFAULT 0.0,
            attempts INTEGER DEFAULT 0,
            correct INTEGER DEFAULT 0,
            stability REAL DEFAULT 1.0,
            difficulty REAL DEFAULT 5.0,
            last_review TEXT,
            next_review TEXT, fi_re_credit REAL DEFAULT 0.0,
            PRIMARY KEY (user_id, verse_id)
        );

CREATE TABLE memorize_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            verse_id TEXT NOT NULL,
            chapter_id TEXT DEFAULT '',
            added_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, verse_id)
        );

CREATE TABLE method_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        method_name TEXT NOT NULL UNIQUE,
        parameters_json TEXT NOT NULL DEFAULT '{}',
        null_control_plan TEXT NOT NULL DEFAULT 'both',
        preregistered INTEGER DEFAULT 0,
        preregistered_date TEXT,
        status TEXT DEFAULT 'active',
        notes TEXT DEFAULT ''
    );

CREATE TABLE module_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id TEXT NOT NULL REFERENCES learning_modules(id),
            question_id INTEGER NOT NULL REFERENCES assessment_items(id),
            is_required INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0
        );

CREATE TABLE passage_guides (
        verse_id TEXT PRIMARY KEY REFERENCES verses(id),
        text_english TEXT,
        text_hebrew TEXT,
        text_greek TEXT,
        connections_json TEXT,
        gematria_json TEXT,
        isopsephy_json TEXT,
        quality_summary TEXT,
        layer_count INTEGER,
        total_connections INTEGER,
        updated_at TEXT DEFAULT (datetime('now'))
    );

CREATE TABLE patterns (
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

CREATE TABLE published_studies (
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

CREATE TABLE query_cache (
            cache_key   TEXT PRIMARY KEY,
            query_text  TEXT NOT NULL,
            filters     TEXT DEFAULT '{}',
            results     TEXT NOT NULL,
            hit_count   INTEGER DEFAULT 1,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at  TEXT NOT NULL
        );

CREATE TABLE quiz_progress (
            user_id TEXT NOT NULL DEFAULT 'default',
            question_id INTEGER NOT NULL,
            correct INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            last_seen TEXT,
            PRIMARY KEY (user_id, question_id)
        );

CREATE TABLE semantic_domains (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT DEFAULT '',
    ai_generated INTEGER DEFAULT 0
);

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE staging_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_verse TEXT NOT NULL,
    target_verse TEXT NOT NULL,
    layer TEXT NOT NULL,
    type TEXT NOT NULL,
    subtype TEXT DEFAULT '',
    strength REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.5,
    metadata TEXT DEFAULT '"{}"',
    reasoning TEXT DEFAULT '',
    status TEXT DEFAULT 'pending',
    submitted_by TEXT DEFAULT '',
    submitted_at TEXT DEFAULT (datetime('now')),
    reviewed_by TEXT DEFAULT '',
    reviewed_at TEXT,
    rejection_reason TEXT DEFAULT ''
);

CREATE TABLE staging_studies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    seed_verse TEXT DEFAULT '',
    steps_json TEXT DEFAULT '[]',
    metadata TEXT DEFAULT '"{}"',
    status TEXT DEFAULT 'draft',
    submitted_by TEXT DEFAULT '',
    submitted_at TEXT DEFAULT (datetime('now')),
    reviewed_by TEXT DEFAULT '',
    reviewed_at TEXT,
    rejection_reason TEXT DEFAULT ''
);

CREATE TABLE structural_formulas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT REFERENCES books(id),
    verse_id TEXT REFERENCES verses(id),
    formula_type TEXT NOT NULL,
    formula_text TEXT NOT NULL,
    position INTEGER NOT NULL
);

CREATE TABLE study_guide_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_guide_id INTEGER NOT NULL REFERENCES study_guides(id) ON DELETE CASCADE,
    step_number INTEGER NOT NULL,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    title TEXT DEFAULT '',
    explanation TEXT DEFAULT '',
    connection_from TEXT DEFAULT '',
    connection_type TEXT DEFAULT '',
    connection_layer TEXT DEFAULT '',
    choices_json TEXT DEFAULT '[]',
    notes TEXT DEFAULT '',
    UNIQUE(study_guide_id, step_number)
);

CREATE TABLE study_guides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    seed_verse TEXT REFERENCES verses(id),
    created_by TEXT DEFAULT 'ai',
    is_public INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
, content_json TEXT DEFAULT '{}');

CREATE TABLE symbol_occurrences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol_id INTEGER NOT NULL REFERENCES symbols(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    is_symbolic INTEGER DEFAULT 1,
    strength REAL DEFAULT 0.5,
    context_note TEXT DEFAULT '',
    UNIQUE(symbol_id, verse_id)
);

CREATE TABLE symbols (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT '',
    meaning TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    ai_discovered INTEGER DEFAULT 0
);

CREATE TABLE tab_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tab_id INTEGER NOT NULL REFERENCES custom_tabs(id),
    content_type TEXT NOT NULL DEFAULT 'verses',
    content_value TEXT NOT NULL,
    label TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE text_resources (
    verse_id TEXT NOT NULL,
    version TEXT NOT NULL,              -- 'KJV', 'WEB', 'LEB', 'BSB', 'YLT'
    text TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'eng',-- 'eng','grc','heb','lat'
    is_default INTEGER DEFAULT 0,       -- 1 if this is the default version
    metadata TEXT DEFAULT '{}',
    PRIMARY KEY (verse_id, version)
);

CREATE TABLE textual_variants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            verse_id TEXT NOT NULL REFERENCES verses(id),
            tradition TEXT NOT NULL DEFAULT 'vulgate',
            text TEXT NOT NULL,
            source TEXT DEFAULT 'Clementine Vulgate',
            notes TEXT DEFAULT '',
            UNIQUE(verse_id, tradition)
        );

CREATE TABLE tg_verse_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id TEXT NOT NULL REFERENCES topical_guide(id),
    verse_id TEXT NOT NULL,
    snippet TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0,
    UNIQUE(topic_id, verse_id)
);

CREATE TABLE thematic_cluster_members (
        cluster_id TEXT NOT NULL REFERENCES thematic_clusters(id),
        verse_id TEXT NOT NULL REFERENCES verses(id),
        contribution TEXT DEFAULT '',
        sort_order INTEGER DEFAULT 0,
        PRIMARY KEY (cluster_id, verse_id)
    );

CREATE TABLE thematic_clusters (
        id TEXT PRIMARY KEY,
        theme TEXT NOT NULL,
        description TEXT DEFAULT '',
        min_verses INTEGER DEFAULT 3,
        source_tradition TEXT DEFAULT 'multiple',
        strength REAL DEFAULT 0.5,
        created_at TEXT DEFAULT (datetime('now'))
    );

CREATE TABLE topic_verses (
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    verse_id TEXT NOT NULL REFERENCES verses(id),
    note TEXT DEFAULT '',
    PRIMARY KEY (topic_id, verse_id)
);

CREATE TABLE topical_guide (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    url_path TEXT DEFAULT '',
    parent_topic_id TEXT,
    related_topic_ids TEXT DEFAULT '[]',
    related_bd_entries TEXT DEFAULT '[]',
    verse_count INTEGER DEFAULT 0,
    importance REAL DEFAULT 0.5,
    raw_html TEXT DEFAULT '',
    last_fetched TEXT
);

CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    parent_id INTEGER REFERENCES topics(id),
    description TEXT DEFAULT '',
    color TEXT DEFAULT '',
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE tradition_labels (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        short_name TEXT NOT NULL,
        description TEXT DEFAULT '',
        icon TEXT DEFAULT '',
        color TEXT DEFAULT '#6b7280'
    );

CREATE TABLE typology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL,
    antitype_name TEXT NOT NULL,
    type_verse TEXT REFERENCES verses(id),
    antitype_verse TEXT REFERENCES verses(id),
    description TEXT DEFAULT '',
    connection_layer TEXT DEFAULT 'symbolic',
    UNIQUE(type_verse, antitype_verse)
);

CREATE TABLE ui_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pref_key TEXT NOT NULL UNIQUE,
    pref_value TEXT NOT NULL
);

CREATE VIRTUAL TABLE vec_verses USING vec0(
            verse_id TEXT PRIMARY KEY,
            embedding float[384] distance_metric=cosine
        );

CREATE TABLE "vec_verses_chunks"(chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,size INTEGER NOT NULL,validity BLOB NOT NULL,rowids BLOB NOT NULL);

CREATE TABLE "vec_verses_info" (key text primary key, value any);

CREATE TABLE "vec_verses_rowids"(rowid INTEGER PRIMARY KEY AUTOINCREMENT,id TEXT UNIQUE NOT NULL,chunk_id INTEGER,chunk_offset INTEGER);

CREATE TABLE "vec_verses_vector_chunks00"(rowid PRIMARY KEY,vectors BLOB NOT NULL);

CREATE TABLE verse_annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    user_id TEXT DEFAULT 'anonymous',
    annotation_type TEXT DEFAULT 'comment',
    content TEXT NOT NULL,
    parent_id INTEGER DEFAULT NULL REFERENCES verse_annotations(id),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE verse_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    entity_id TEXT NOT NULL REFERENCES entity_links(entity_id),
    relationship_type TEXT NOT NULL DEFAULT 'mentions',
    confidence REAL DEFAULT 0.5,
    UNIQUE(verse_id, entity_id, relationship_type)
);

CREATE TABLE verse_similarity (
            verse_a TEXT NOT NULL,
            verse_b TEXT NOT NULL,
            entity_overlap REAL DEFAULT 0.0,
            connection_overlap REAL DEFAULT 0.0,
            combined_score REAL DEFAULT 0.0,
            shared_entity_count INTEGER DEFAULT 0,
            shared_connection_count INTEGER DEFAULT 0,
            PRIMARY KEY (verse_a, verse_b)
        );

CREATE TABLE verses (
    id TEXT PRIMARY KEY,
    book_id TEXT NOT NULL REFERENCES books(id),
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text_english TEXT NOT NULL DEFAULT '',
    text_hebrew TEXT DEFAULT '',
    text_hebrew_translit TEXT DEFAULT '',
    has_hebrew INTEGER DEFAULT 0,
    heading TEXT DEFAULT ''
, text_greek TEXT DEFAULT "", has_greek INTEGER DEFAULT 0, hit_count INTEGER DEFAULT 0);

CREATE VIRTUAL TABLE verses_fts USING fts5(
            verse_id UNINDEXED,
            book_id UNINDEXED,
            text_english, 
            text_hebrew,
            text_greek,
            tokenize='porter unicode61'
        );

CREATE TABLE 'verses_fts_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE 'verses_fts_content'(id INTEGER PRIMARY KEY, c0, c1, c2, c3, c4);

CREATE TABLE 'verses_fts_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'verses_fts_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'verses_fts_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE VIRTUAL TABLE verses_fts_trigram USING fts5(
                verse_id UNINDEXED,
                book_id UNINDEXED,
                search_text,
                tokenize='trigram'
            );

CREATE TABLE 'verses_fts_trigram_config'(k PRIMARY KEY, v) WITHOUT ROWID;

CREATE TABLE 'verses_fts_trigram_content'(id INTEGER PRIMARY KEY, c0, c1, c2);

CREATE TABLE 'verses_fts_trigram_data'(id INTEGER PRIMARY KEY, block BLOB);

CREATE TABLE 'verses_fts_trigram_docsize'(id INTEGER PRIMARY KEY, sz BLOB);

CREATE TABLE 'verses_fts_trigram_idx'(segid, term, pgno, PRIMARY KEY(segid, term)) WITHOUT ROWID;

CREATE TABLE wiki_articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    article_type TEXT NOT NULL DEFAULT 'entity',
    summary TEXT NOT NULL,
    content TEXT DEFAULT '',
    key_verses TEXT DEFAULT '[]',
    cross_references TEXT DEFAULT '[]',
    ai_generated INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE word_collocations (
    word_a TEXT NOT NULL,                          -- lemma
    word_b TEXT NOT NULL,                          -- lemma
    book_id TEXT NOT NULL DEFAULT '',
    frequency INTEGER DEFAULT 0,
    strength REAL DEFAULT 0.0,                     -- PMI or co-occurrence score
    PRIMARY KEY (word_a, word_b, book_id)
);

CREATE TABLE word_frequency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    word_english TEXT NOT NULL,
    word_hebrew TEXT DEFAULT '',
    strongs_number TEXT DEFAULT '',
    book_id TEXT REFERENCES books(id),
    count INTEGER DEFAULT 0,
    scope TEXT DEFAULT 'canon'  -- 'canon', 'work', 'book'
);

CREATE TABLE word_images (
            word_hebrew TEXT NOT NULL,
            node_id TEXT,
            source TEXT DEFAULT 'freebible',
            image_url TEXT NOT NULL,
            attribution TEXT DEFAULT '',
            width INTEGER DEFAULT 0,
            height INTEGER DEFAULT 0,
            prompt TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (word_hebrew, source)
        );

CREATE TABLE works (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    subtitle TEXT
, position INTEGER DEFAULT 0);

CREATE INDEX idx_annotations_verse ON verse_annotations(verse_id);
CREATE INDEX idx_audio_book_chapter ON audio_timestamps(book_id, chapter);
CREATE INDEX idx_cache_expires
        ON query_cache(expires_at)
    ;
CREATE INDEX idx_collocations_a ON word_collocations(word_a);
CREATE INDEX idx_collocations_b ON word_collocations(word_b);
CREATE INDEX idx_connections_layer ON connections(layer, type);
CREATE INDEX idx_connections_layer_type ON connections(layer, type);
CREATE INDEX idx_connections_source ON connections(source_verse);
CREATE INDEX idx_connections_source_layer_type 
    ON connections(source_verse, layer, type, subtype)
;
CREATE INDEX idx_connections_src_tgt_layer ON connections(source_verse, target_verse, layer);
CREATE INDEX idx_connections_target ON connections(target_verse);
CREATE INDEX idx_connections_type ON connections(type);
CREATE INDEX idx_conv_conn_session ON conversation_connections(session_id);
CREATE INDEX idx_conv_msg_session ON conversation_messages(session_id);
CREATE INDEX idx_conv_refs_session ON conversation_refs(session_id);
CREATE INDEX idx_disagreements_verse ON interpretive_disagreements(verse_id);
CREATE INDEX idx_footnotes_cat ON footnotes(verse_id, category);
CREATE INDEX idx_footnotes_verse ON footnotes(verse_id);
CREATE INDEX idx_forum_posts_topic ON forum_posts(topic_id);
CREATE INDEX idx_gematria_greek_value ON gematria_greek(value_standard);
CREATE INDEX idx_gematria_greek_verse ON gematria_greek(verse_id);
CREATE INDEX idx_gematria_hebrew_plain ON gematria(hebrew_plain);
CREATE INDEX idx_gematria_value_std ON gematria(value_standard);
CREATE INDEX idx_gematria_verse ON gematria(verse_id);
CREATE INDEX idx_js_refs_source ON js_scripture_refs(js_ref_id);
CREATE INDEX idx_js_refs_verse ON js_scripture_refs(verse_id);
CREATE INDEX idx_js_sources_date ON js_sources(date);
CREATE INDEX idx_js_sources_type ON js_sources(source_type);
CREATE INDEX idx_knowledge_items_layer ON knowledge_items(layer);
CREATE INDEX idx_knowledge_items_pardes ON knowledge_items(pa_r_de_s_level);
CREATE INDEX idx_knowledge_items_verse ON knowledge_items(verse_id);
CREATE INDEX idx_known_chiasms_book ON known_chiasms(book_id);
CREATE INDEX idx_known_chiasms_scholar ON known_chiasms(scholar);
CREATE INDEX idx_patterns_book ON patterns(book_id);
CREATE INDEX idx_patterns_type ON patterns(pattern_type);
CREATE INDEX idx_published_guide ON published_studies(study_guide_id);
CREATE INDEX idx_published_slug ON published_studies(slug);
CREATE INDEX idx_staging_conn_layer ON staging_connections(layer);
CREATE INDEX idx_staging_conn_status ON staging_connections(status);
CREATE INDEX idx_staging_studies_status ON staging_studies(status);
CREATE INDEX idx_struct_formulas_book ON structural_formulas(book_id);
CREATE INDEX idx_struct_formulas_type ON structural_formulas(formula_type);
CREATE INDEX idx_text_resources_version ON text_resources(version);
CREATE INDEX idx_tv_verse ON textual_variants(verse_id);
CREATE INDEX idx_verse_entities_entity ON verse_entities(entity_id);
CREATE INDEX idx_verse_entities_verse ON verse_entities(verse_id);
CREATE INDEX idx_verses_book_chapter ON verses(book_id, chapter, verse);
CREATE INDEX idx_verses_has_greek ON verses(has_greek);
CREATE INDEX idx_wiki_type ON wiki_articles(article_type);
CREATE INDEX idx_word_freq_word ON word_frequency(word_english);
CREATE UNIQUE INDEX idx_xref_pair ON cross_references(source_verse, target_verse);
CREATE INDEX idx_xref_source ON cross_references(source_verse);
CREATE INDEX idx_xref_target ON cross_references(target_verse);
