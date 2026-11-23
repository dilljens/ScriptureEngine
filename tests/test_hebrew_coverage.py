"""M1: chapter known-word coverage (LingQ-style readability dial)."""
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.routes import hebrew as H

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def hebdb(tmp_path, monkeypatch):
    src = ROOT / "data" / "memorize.db"
    if not src.exists():
        pytest.skip("Hebrew database not found")
    isolated = tmp_path / "memorize.db"
    shutil.copy2(src, isolated)
    monkeypatch.setattr(H, "MEM_DB", isolated)
    return isolated


def test_coverage_gen1_shape(hebdb):
    out = H.get_hebrew_coverage(book="gen", chapter=1, user_id="default",
                                session_token="", authorization="")
    assert out["ok"] is True
    d = out["data"]
    assert d["tokens_total"] > 0 and d["tokens_known"] <= d["tokens_total"]
    assert 0.0 <= d["coverage"] <= 1.0
    assert d["types_known"] <= d["types_total"]
    assert isinstance(d["unknown"], list) and len(d["unknown"]) <= 25
    for u in d["unknown"]:
        assert set(u) == {"surface", "folded", "count", "node_id"}
    # On the full corpus, unknowns resolve to mineable add-word nodes.
    if d["tokens_total"] > 300:
        resolvable = [u for u in d["unknown"] if u["node_id"]]
        assert resolvable, "top unknowns should be mineable via add-word nodes"


def test_coverage_requires_book_and_chapter(hebdb):
    with pytest.raises(Exception):
        H.get_hebrew_coverage(book="", chapter=0, user_id="default",
                              session_token="", authorization="")


def test_coverage_missing_chapter_404s(hebdb):
    with pytest.raises(Exception) as exc:
        H.get_hebrew_coverage(book="gen", chapter=999, user_id="default",
                              session_token="", authorization="")
    assert "404" in str(exc.value.status_code)


def test_daily_session_composes_reviews_and_verse(hebdb):
    out = H.get_hebrew_daily_session(user_id="default", limit=20, session_token="",
                                     authorization="")
    assert out["ok"] is True
    d = out["data"]
    assert isinstance(d["reviews"], list) and d["due_count"] >= 0
    vb = d.get("verse_block")
    if vb is not None:
        assert vb.get("verse_ref") and vb.get("text_hebrew")
        assert vb.get("audio_url", "").startswith("/api/v1/audio/play/")
