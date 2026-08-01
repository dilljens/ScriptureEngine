from scripts.align_hebrew_vocabulary import cloze_at_word_index, lemma_parts, reconciled_gloss, unpointed


def test_lemma_parts_preserves_homonym_and_strips_all_prefixes():
    assert lemma_parts("c/b/3605") == ("3605", "3605")
    assert lemma_parts("1254 a") == ("1254 a", "1254")
    assert lemma_parts("H7225") == ("7225", "7225")


def test_cloze_replaces_one_token_not_a_substring():
    verse = "וַיֹּאמֶר זֹאת אֵת הָאָרֶץ"
    assert cloze_at_word_index(verse, 2) == "וַיֹּאמֶר זֹאת ______ הָאָרֶץ"
    assert "זֹאת" in cloze_at_word_index(verse, 2)


def test_reconciled_gloss_fixes_aramaic_lexemes():
    assert reconciled_gloss("1768", "Daniel") == "that, which"
    assert reconciled_gloss("4430", "Daniel") == "king (Aramaic)"
    assert reconciled_gloss("1934", "Clay") == "to be, become"
    assert reconciled_gloss("1836", "Interpretation") == "this"


def test_reconciled_gloss_preserves_curated_hebrew_glosses():
    assert reconciled_gloss("430", "God") == "God"


def test_unpointed_reduces_pointed_tokens_to_consonant_skeletons():
    assert unpointed("מַלְכָּ֖/א") == "מלכא"
    assert unpointed("ד/הוא") == "דהוא"
    assert unpointed("דִּי") == "די"


def test_repair_vocabulary_metadata_fixes_corrupted_descriptions(tmp_path):
    import sqlite3
    import json as _json
    from scripts.repair_vocabulary_metadata import repair

    db = tmp_path / "memorize.db"
    conn = sqlite3.connect(db)
    conn.executescript("""
        CREATE TABLE hebrew_nodes (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, level INTEGER DEFAULT 4,
            category TEXT DEFAULT 'word', description TEXT DEFAULT ''
        );
        CREATE TABLE hebrew_lessons (
            node_id TEXT PRIMARY KEY REFERENCES hebrew_nodes(id),
            content_json TEXT NOT NULL, version INTEGER DEFAULT 1,
            updated_at TEXT DEFAULT (datetime('now'))
        );
        INSERT INTO hebrew_nodes VALUES
            ('vocab_אבדה_276','אָבַד — to perish / to be lost',4,'word','Father (Aramaic). Root: אב.');
    """)
    conn.execute(
        "INSERT INTO hebrew_lessons VALUES ('vocab_אבדה_276', ?, 1, datetime('now'))",
        (_json.dumps({"hebrew": "אָבַד", "gloss": "to perish / to be lost",
                      "description": "Father (Aramaic). Root: אב.", "root": "אבדה",
                      "title": "אָבַד — to perish / to be lost"}),),
    )
    conn.commit()
    conn.close()

    assert repair(db) == {"fixed": 1}
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    node = conn.execute("SELECT description FROM hebrew_nodes WHERE id='vocab_אבדה_276'").fetchone()
    lesson = _json.loads(conn.execute("SELECT content_json FROM hebrew_lessons").fetchone()[0])
    conn.close()
    assert node["description"].startswith("To perish")
    assert lesson["root"] == "אבד"
    assert "Aramaic" not in lesson["description"]


def test_get_top_words_selects_one_citation_form_per_surface():
    from scripts.seed_hebrew_vocabulary import get_top_words
    words = get_top_words(count=60)
    surfaces = [w["hebrew"] for w in words]
    assert len(surfaces) == len(set(surfaces)), "surface dedup failed"
    assert all("/" not in w["lemma"] for w in words), "prefixed rows leaked into selection"


def test_lexicon_frequency_is_exact_ot_aggregate():
    import sqlite3
    from pathlib import Path
    from scripts.rebuild_lexicon_frequencies import compute_counts, canonical_base
    scripture = Path("data/processed/scripture.db")
    if not scripture.exists():
        return  # corpus not present in this checkout
    conn = sqlite3.connect(f"file:{scripture}?mode=ro", uri=True)
    counts = compute_counts(conn)
    conn.close()
    assert counts["3605"]["tokens"] == 5413  # כל
    assert counts["3068"]["tokens"] == 6521  # יהוה
    assert canonical_base("c/b/3605") == "3605"
    assert canonical_base("H3605") == "3605"
