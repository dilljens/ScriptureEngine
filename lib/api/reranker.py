"""
Optional cross-encoder reranker for semantic search results.

Improves search quality by reranking hybrid (vector + BM25 + graph)
results through a cross-encoder. Graceful degradation: if
sentence-transformers is not installed, all functions no-op and
return results unchanged.

Pattern from unicity-ai's reranker with SEE (Similarity-based Early Exit)
for 3.5× speedup: pre-filters low-similarity docs using a lightweight
bi-encoder before running the expensive cross-encoder pass.

Usage:
    from lib.api.reranker import rerank_if_available

    results = rerank_if_available(query, results, top_k=20)
"""

import logging
import time

logger = logging.getLogger(__name__)

# ── Lazy-loaded model ─────────────────────────────────────────────────

_HAS_CROSS_ENCODER = False
_CROSS_ENCODER = None

try:
    from sentence_transformers import CrossEncoder, SentenceTransformer
    _HAS_CROSS_ENCODER = True
except ImportError:
    _HAS_CROSS_ENCODER = False

# Default lightweight model — good quality on CPU
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# SEE early-exit threshold: below this similarity, skip cross-encoder
SEE_THRESHOLD = 0.3


def _ensure_reranker():
    """Lazy-load the cross-encoder model on first use."""
    global _CROSS_ENCODER
    if _CROSS_ENCODER is not None:
        return _CROSS_ENCODER
    if not _HAS_CROSS_ENCODER:
        return None
    try:
        _CROSS_ENCODER = CrossEncoder(RERANKER_MODEL)
        logger.info("Reranker loaded: %s", RERANKER_MODEL)
        return _CROSS_ENCODER
    except Exception as e:
        logger.warning("Failed to load reranker %s: %s", RERANKER_MODEL, e)
        return None


# ── SEE (Similarity-based Early Exit) ────────────────────────────────

_SEE_EMBEDDER = None


def _get_see_embedder():
    """Lazy-load lightweight bi-encoder for SEE similarity checks."""
    global _SEE_EMBEDDER
    if _SEE_EMBEDDER is not None:
        return _SEE_EMBEDDER
    if not _HAS_CROSS_ENCODER:
        return None
    try:
        _SEE_EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2")
        return _SEE_EMBEDDER
    except Exception:
        return None


def _see_should_skip(query: str, doc_text: str, threshold: float = 0.3) -> bool:
    """SEE: token-level query-doc similarity check.

    If mean-pooled token embedding similarity falls below threshold,
    the document is unlikely to be relevant and cross-encoder is skipped.
    Returns True = skip (low similarity).
    """
    embedder = _get_see_embedder()
    if embedder is None:
        return False  # can't check → run cross-encoder anyway

    try:
        query_emb = embedder.encode(query, convert_to_tensor=True)
        doc_emb = embedder.encode(doc_text[:512], convert_to_tensor=True)
        from torch import cosine_similarity
        sim = cosine_similarity(query_emb.unsqueeze(0), doc_emb.unsqueeze(0)).item()
        return sim < threshold
    except Exception:
        return False


# ── Public API ───────────────────────────────────────────────────────

def rerank_if_available(
    query: str,
    results: list[dict],
    top_k: int = 0,
    see: bool = True,
) -> list[dict]:
    """Rerank results using cross-encoder if available. Returns unchanged if not.

    Args:
        query: Original search query.
        results: List of result dicts, each with at least 'text' or 'verse'.
        top_k: Max results to rerank (0 = all). Default caps at 20.
        see: Enable SEE early-exit (default True, ~3.5× speedup).

    Returns:
        Reranked results list (sorted by relevance descending).
        If reranker unavailable, returns original results unchanged.
    """
    reranker = _ensure_reranker()
    if reranker is None:
        return results  # graceful degradation

    rerank_limit = top_k if top_k > 0 else min(len(results), 20)
    if rerank_limit <= 0:
        return results

    candidates = results[:rerank_limit]
    rest = results[rerank_limit:]

    scored = []
    early_exits = 0
    reranked_count = 0
    total_time = 0.0

    for result in candidates:
        # Get text to evaluate
        doc_text = (
            result.get("text", "") or
            result.get("text_english", "") or
            result.get("_snippet", "") or
            ""
        )
        if not doc_text:
            scored.append((0.5, result))  # neutral score
            continue

        # SEE early-exit
        if see and _see_should_skip(query, doc_text, SEE_THRESHOLD):
            early_exits += 1
            scored.append((0.01, result))  # low score
            continue

        # Full cross-encoder pass
        t0 = time.time()
        try:
            score = reranker.predict([(query, doc_text)])[0]
        except Exception:
            score = 0.0
        total_time += time.time() - t0
        reranked_count += 1
        scored.append((float(score), result))

    # Sort by score descending
    scored.sort(key=lambda x: -x[0])
    reranked = [r for _, r in scored] + rest

    logger.debug(
        "Reranker: %d candidates, %d early-exits, %d reranked in %.1fms",
        len(candidates), early_exits, reranked_count, total_time * 1000,
    )

    return reranked


def reranker_available() -> bool:
    """Check if the reranker model is loaded and available."""
    return _ensure_reranker() is not None
