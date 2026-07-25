CREATE TABLE verses (
    id TEXT PRIMARY KEY,
    book TEXT NOT NULL,
    chapter INTEGER NOT NULL,
    verse_num INTEGER NOT NULL,
    text TEXT NOT NULL,
    reference TEXT NOT NULL,
    language TEXT DEFAULT 'english',
    last_synced TEXT DEFAULT (datetime('now'))
);

CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    card_type TEXT NOT NULL DEFAULT 'text',
    state INTEGER NOT NULL DEFAULT 0,
    stability REAL NOT NULL DEFAULT 0.0,
    difficulty REAL NOT NULL DEFAULT 0.0,
    elapsed_days REAL NOT NULL DEFAULT 0.0,
    scheduled_days REAL NOT NULL DEFAULT 0.0,
    reps INTEGER NOT NULL DEFAULT 0,
    lapses INTEGER NOT NULL DEFAULT 0,
    hint_level INTEGER NOT NULL DEFAULT 0,
    last_review TEXT,
    due TEXT NOT NULL DEFAULT (datetime('now')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
, fi_re_credit REAL NOT NULL DEFAULT 0.0, student_ability REAL NOT NULL DEFAULT 1.0, topic_difficulty REAL NOT NULL DEFAULT 1.0, learning_speed REAL NOT NULL DEFAULT 1.0);

CREATE TABLE sqlite_sequence(name,seq);

CREATE TABLE review_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL REFERENCES cards(id),
    rating INTEGER NOT NULL,
    elapsed_seconds REAL NOT NULL DEFAULT 0.0,
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE palaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    photo_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE loci (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    palace_id INTEGER NOT NULL REFERENCES palaces(id),
    label TEXT NOT NULL DEFAULT '',
    x_pct REAL NOT NULL DEFAULT 0.5,
    y_pct REAL NOT NULL DEFAULT 0.5,
    verse_id TEXT REFERENCES verses(id)
);

CREATE TABLE concept_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    file_path TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'openverse',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE composite_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    palace_id INTEGER NOT NULL REFERENCES palaces(id),
    locus_id INTEGER NOT NULL REFERENCES loci(id),
    file_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE audio_recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    verse_id TEXT NOT NULL REFERENCES verses(id),
    file_path TEXT NOT NULL,
    duration_secs REAL NOT NULL DEFAULT 0.0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE user_xp (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    xp INTEGER NOT NULL DEFAULT 0,
    streak_count INTEGER NOT NULL DEFAULT 0,
    last_review_date TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE verse_connections (
    verse_id TEXT NOT NULL,
    connected_verse_id TEXT NOT NULL,
    connection_type TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 0.2,
    PRIMARY KEY (verse_id, connected_verse_id, connection_type)
);

CREATE TABLE push_subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT NOT NULL UNIQUE,
    p256dh_key TEXT NOT NULL DEFAULT '',
    auth_key TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE hebrew_nodes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    level INTEGER NOT NULL,
    category TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT ''
, tradition TEXT DEFAULT 'tiberian');

CREATE TABLE hebrew_edges (
    source_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    target_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    edge_type TEXT NOT NULL DEFAULT 'prerequisite',
    weight REAL NOT NULL DEFAULT 1.0,
    PRIMARY KEY (source_id, target_id, edge_type)
);

CREATE TABLE hebrew_lessons (
    node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
    content_json TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE hebrew_practice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    question_type TEXT NOT NULL,
    question_text TEXT NOT NULL,
    options_json TEXT DEFAULT '[]',
    correct_answer TEXT NOT NULL,
    difficulty REAL DEFAULT 0.5,
    explanation TEXT DEFAULT ''
);

CREATE TABLE hebrew_progress (
    user_id TEXT NOT NULL DEFAULT 'default',
    node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
    mastery REAL DEFAULT 0.0,
    attempts INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    last_practiced TEXT,
    PRIMARY KEY (user_id, node_id)
);

CREATE TABLE grammar_reference (
            paragraph_id INTEGER PRIMARY KEY,
            section TEXT,
            subsection TEXT,
            summary TEXT,
            hebrew_examples TEXT,
            html_content TEXT,
            has_details INTEGER DEFAULT 1
        );

CREATE TABLE hebrew_confusability (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_a TEXT NOT NULL,
            node_b TEXT NOT NULL,
            reason TEXT DEFAULT '',
            strength REAL DEFAULT 0.5,
            FOREIGN KEY (node_a) REFERENCES hebrew_nodes(id),
            FOREIGN KEY (node_b) REFERENCES hebrew_nodes(id)
        );

CREATE TABLE hebrew_attestations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id TEXT NOT NULL REFERENCES hebrew_nodes(id),
        verse_id TEXT NOT NULL,
        attestation_type TEXT NOT NULL DEFAULT 'grammar',
        explanation TEXT DEFAULT '',
        difficulty TEXT DEFAULT 'beginner',
        UNIQUE(node_id, verse_id)
    );

CREATE TABLE hebrew_gamification (
            user_id TEXT NOT NULL DEFAULT 'default',
            xp INTEGER DEFAULT 0,
            streak_count INTEGER DEFAULT 0,
            last_review_date TEXT,
            best_streak INTEGER DEFAULT 0,
            insight_xp INTEGER DEFAULT 0,
            PRIMARY KEY (user_id)
        );

CREATE TABLE hebrew_badges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            badge_id TEXT NOT NULL,
            earned_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, badge_id)
        );

CREATE TABLE hebrew_seen_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'default',
            connection_key TEXT NOT NULL,
            seen_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, connection_key)
        );

CREATE TABLE fi_re_credits (
    user_id     TEXT NOT NULL DEFAULT 'default',
    item_type   TEXT NOT NULL,   -- 'verse', 'hebrew_concept', 'learning_module'
    item_id     TEXT NOT NULL,
    credit      REAL DEFAULT 0.0,
    last_updated TEXT DEFAULT (datetime('now')),
    source_item_type TEXT DEFAULT NULL,  -- what gave this credit
    source_item_id   TEXT DEFAULT NULL,
    PRIMARY KEY (user_id, item_type, item_id)
);

CREATE TABLE entity_verse_bridge (
    item_type   TEXT NOT NULL,   -- 'hebrew_concept', 'entity'
    item_id     TEXT NOT NULL,
    verse_id    TEXT NOT NULL,
    weight      REAL DEFAULT 0.5,
    PRIMARY KEY (item_type, item_id, verse_id)
);

