"""In-memory cache for deterministic read-only chat tool results.

The chat pipeline executes tool calls to answer scripture questions. Many
tools (verse lookups, gematria, Strong's, sources) return deterministic
results for the same arguments — caching them skips repeat SQLite work
entirely, which compounds with the parallel tool executor: a round that
re-looks-up a verse already fetched this session costs ~0ms.

Design: small in-memory dict with TTL + size cap, keyed by sha256 of
(tool name + canonical JSON args). Per-process only — uvicorn --workers 2
means two independent caches, which is fine for a session-scoped win.
A SQLite-backed cache table is the documented upgrade path if cross-worker
cache hits ever matter (they don't for latency: the worker-local hit rate
is what saves wall-clock).
"""

import hashlib
import json
import threading
import time

# Deterministic read-only tools safe to cache. Connection-heavy or mutable
# tools are excluded deliberately: results must not go stale mid-session.
CACHEABLE_TOOLS = {
    "scripture_verse",
    "scripture_verse_text",
    "scripture_gematria",
    "scripture_strongs",
    "scripture_interlinear",
    "scripture_sources",
    "scripture_sources_by_scholar",
    "scripture_sources_list",
    "scripture_versions",
    "scripture_info",
    "scripture_graph_stats",
}

TTL_SECONDS = 24 * 60 * 60  # 24h — verse text/gematria don't drift day-to-day
MAX_ENTRIES = 2048          # rough cap; evicts oldest when exceeded


class _ToolCache:
    """Thread-safe TTL cache with FIFO-ish size cap."""

    def __init__(self):
        self._data = {}  # key -> (expires_at, value)
        self._lock = threading.Lock()

    def _key(self, name, args):
        raw = json.dumps([name, args], sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, name, args):
        if name not in CACHEABLE_TOOLS:
            return None
        key = self._key(name, args)
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._data[key]
                return None
            return value

    def set(self, name, args, value):
        if name not in CACHEABLE_TOOLS or value is None:
            return
        if isinstance(value, dict) and value.get("error"):
            return  # never cache failures
        key = self._key(name, args)
        with self._lock:
            if len(self._data) >= MAX_ENTRIES:
                # Evict ~10% oldest entries (expired first, then insertion order)
                now = time.time()
                expired = [k for k, (exp, _) in self._data.items() if exp <= now]
                for k in expired:
                    del self._data[k]
                if len(self._data) >= MAX_ENTRIES:
                    # Drop oldest by expiry
                    for k in sorted(self._data, key=lambda k: self._data[k][0])[:MAX_ENTRIES // 10]:
                        del self._data[k]
            self._data[key] = (time.time() + TTL_SECONDS, value)

    def clear(self):
        with self._lock:
            self._data.clear()

    def __len__(self):
        return len(self._data)


tool_cache = _ToolCache()
