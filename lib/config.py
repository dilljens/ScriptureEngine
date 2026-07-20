"""Centralized configuration for Scripture Engine.

All environment variables and hardcoded paths are defined here.
Import from this module instead of hardcoding values throughout the codebase.
"""

import os
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"

# ── Database paths ────────────────────────────────────────────────────
# Override with SCRIPTURE_DB_PATH env var
DEFAULT_DB_PATH = Path(os.environ.get(
    "SCRIPTURE_DB_PATH",
    str(PROCESSED_DIR / "scripture.db"),
))
MEMORIZE_DB_PATH = DATA_DIR / "memorize.db"
TEST_DB_PATH = DATA_DIR / "test" / "test.db"

# ── Server ────────────────────────────────────────────────────────────
API_PORT = int(os.environ.get("PORT", "8002"))
GO_SRS_PORT = int(os.environ.get("GO_SRS_PORT", "8090"))
FRONTEND_DEV_PORTS = [5173, 5176]

# ── CORS ───────────────────────────────────────────────────────────────
CORS_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:5176,http://localhost:3000",
    ).split(",") if o.strip()
]

# ── LLM / API keys ───────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")

# ── Optional feature flags ───────────────────────────────────────────
VECTOR_SEARCH_AVAILABLE = os.environ.get("VECTOR_SEARCH", "").lower() in ("1", "true", "yes")

# ── Limits ────────────────────────────────────────────────────────────
MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_SEARCH_RESULTS = 50
MAX_GRAPH_DEPTH = 5
