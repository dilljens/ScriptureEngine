"""Staged feature flags beyond env selection (plan hebrew-tutor-phase2, P2-E).

Precedence: FLAG_<NAME> env (1/0/true/false/yes/no/on/off) >
data/flags.json ({name: bool | {"pct": 0-100}}) > default argument.
Percentage rollouts hash name+user_id, so a user stays in their bucket.

data/flags.json is optional (absent = everything falls to defaults);
it ships with the repo so staged rollouts are reviewable diffs.
"""
import hashlib
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FLAGS_PATH = BASE_DIR / "data" / "flags.json"  # monkeypatchable in tests

_cache = None


def _load():
    global _cache
    if _cache is None:
        try:
            _cache = json.loads(Path(FLAGS_PATH).read_text())
        except (OSError, ValueError):
            _cache = {}
        if not isinstance(_cache, dict):
            _cache = {}
    return _cache


def reset_cache():
    """Forget the loaded flags file. Tests only."""
    global _cache
    _cache = None


def _rollout_bucket(name: str, user_id: str) -> int:
    digest = hashlib.sha256(f"{name}:{user_id or ''}".encode()).hexdigest()
    return int(digest, 16) % 100


def is_enabled(name: str, user_id: str = "", default: bool = False) -> bool:
    """True when the flag is on for this user."""
    key = (name or "").strip()
    if not key:
        return False
    env = os.environ.get("FLAG_" + key.upper())
    if env is not None:
        return env.strip().lower() in ("1", "true", "yes", "on")
    cfg = _load().get(key)
    if isinstance(cfg, bool):
        return cfg
    if isinstance(cfg, dict):
        try:
            pct = max(0, min(100, int(cfg.get("pct", 0))))
        except (TypeError, ValueError):
            return bool(default)
        return _rollout_bucket(key, user_id) < pct
    return bool(default)
