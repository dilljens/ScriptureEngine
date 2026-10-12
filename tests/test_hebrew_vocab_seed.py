"""Top-2000 vocab seeding: gloss fallback, idempotent seed, resolution."""

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from seed_hebrew_vocabulary import get_top_words  # noqa: E402


def test_top_words_have_real_glosses():
    words = get_top_words(2000, 10)
    assert len(words) >= 1600
    freqs = [w["frequency"] for w in words]
    assert freqs == sorted(freqs, reverse=True)
    for w in words:
        assert w["gloss"] and not w["gloss"].replace(" ", "").isdigit(), w["hebrew"]
    by_hw = {w["hebrew"]: w for w in words}
    # Lemma 7637 has no lemma_gloss row: derived from the definition.
    assert by_hw["השביעי"]["gloss"].startswith("1) seventh")


def _fresh_db(path):
    """Empty DB with the alignment table the seeder expects to exist."""
    conn = sqlite3.connect(str(path))
    conn.execute("""CREATE TABLE hebrew_vocabulary_alignment (
        node_id TEXT PRIMARY KEY, lemma_key TEXT, lemma_base TEXT,
        strongs_id TEXT, language TEXT, example_verse_id TEXT,
        example_word_index INTEGER, token_surface TEXT, token_lemma_raw TEXT,
        token_morph TEXT, source_id TEXT, source_version TEXT,
        source_license TEXT, alignment_method TEXT, confidence REAL,
        updated_at TEXT)""")
    conn.commit()
    conn.close()


def test_seed_small_idempotent(tmp_path):
    import runpy
    dest = tmp_path / "mem.db"
    _fresh_db(dest)
    for run in (1, 2):
        sys.argv = ["seed", "--count", "3", "--db", str(dest)]
        runpy.run_path("scripts/seed_hebrew_vocabulary.py", run_name="__main__")
    conn = sqlite3.connect(str(dest))
    n = conn.execute("SELECT COUNT(*) FROM hebrew_nodes WHERE category='word'").fetchone()[0]
    assert n == 3, f"expected 3 word nodes after 2 runs, got {n}"
    items = conn.execute("SELECT COUNT(*) FROM hebrew_practice_items").fetchone()[0]
    assert items > 0
    conn.close()


def test_seeded_surfaces_resolve(tmp_path):
    import runpy
    dest = tmp_path / "mem.db"
    _fresh_db(dest)
    sys.argv = ["seed", "--count", "3", "--db", str(dest)]
    runpy.run_path("scripts/seed_hebrew_vocabulary.py", run_name="__main__")
    from web.routes.hebrew import resolve_hebrew_node
    conn = sqlite3.connect(str(dest))
    for (hw,) in conn.execute(
            "SELECT json_extract(content_json, '$.hebrew') FROM hebrew_lessons LIMIT 3"):
        assert resolve_hebrew_node(conn, hw), hw
    conn.close()
