"""Staged feature flags: env > file > default, stable pct buckets."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib import flags


@pytest.fixture()
def flagfile(tmp_path, monkeypatch):
    path = tmp_path / "flags.json"
    monkeypatch.setattr(flags, "FLAGS_PATH", path)
    monkeypatch.setattr(flags, "_cache", None)
    yield path
    monkeypatch.setattr(flags, "_cache", None)


def test_default_when_nothing_configured(flagfile, monkeypatch):
    monkeypatch.delenv("FLAG_TRUTH_ENTAILMENT", raising=False)
    assert flags.is_enabled("truth_entailment") is False
    assert flags.is_enabled("truth_entailment", default=True) is True
    assert flags.is_enabled("") is False


def test_env_wins_over_file(flagfile, monkeypatch):
    flagfile.write_text(json.dumps({"truth_entailment": True}))
    monkeypatch.setattr(flags, "_cache", None)
    monkeypatch.setenv("FLAG_TRUTH_ENTAILMENT", "0")
    assert flags.is_enabled("truth_entailment") is False
    monkeypatch.setenv("FLAG_TRUTH_ENTAILMENT", "yes")
    assert flags.is_enabled("truth_entailment", user_id="u1") is True


@pytest.mark.parametrize("raw,expected", [
    ("1", True), ("true", True), ("yes", True), ("on", True),
    ("0", False), ("false", False), ("no", False), ("off", False),
    ("anything-else", False),
])
def test_env_spellings(flagfile, monkeypatch, raw, expected):
    monkeypatch.setenv("FLAG_X", raw)
    assert flags.is_enabled("x") is expected


def test_file_bool_and_pct_buckets(flagfile, monkeypatch):
    monkeypatch.delenv("FLAG_X", raising=False)
    flagfile.write_text(json.dumps({"x": True, "y": {"pct": 100},
                                    "z": {"pct": 0}}))
    monkeypatch.setattr(flags, "_cache", None)
    assert flags.is_enabled("x", user_id="u") is True
    assert flags.is_enabled("y", user_id="u") is True
    assert flags.is_enabled("z", user_id="u") is False
    # Buckets are stable per user and split the population at 50%.
    flagfile.write_text(json.dumps({"half": {"pct": 50}}))
    monkeypatch.setattr(flags, "_cache", None)
    users = [f"user-{i}" for i in range(200)]
    first = [flags.is_enabled("half", user_id=u) for u in users]
    second = [flags.is_enabled("half", user_id=u) for u in users]
    assert first == second
    assert 60 < sum(first) < 140


def test_broken_file_falls_to_default(flagfile, monkeypatch):
    monkeypatch.delenv("FLAG_X", raising=False)
    flagfile.write_text("not json{")
    monkeypatch.setattr(flags, "_cache", None)
    assert flags.is_enabled("x", default=True) is True
