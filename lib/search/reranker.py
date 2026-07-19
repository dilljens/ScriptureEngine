"""
Cross-encoder reranker with SEE (Similarity-based Early Exit).

Improves search quality by reranking hybrid search results through a
cross-encoder. SEE pre-filters low-similarity documents using token-level
embedding similarity, delivering up to 3.5x speedup with minimal quality loss.

Graceful degradation: if sentence-transformers is not installed,
functions no-op and return results unchanged.

Port from uki's wrappers/reranker.py (SIGIR 2025 SEE pattern).
"""

import logging
import time

logger = logging.getLogger(__name__)

# ── Lazy-loaded model singleton ─────────────────────────────────────

_HAS_CROSS_ENCODER = False
_MODELS = {"cross_encoder": None, "see_embedder": None}

try:
    from sentence_transformers import CrossEncoder, SentenceTransformer
    _HAS_CROSS_ENCODER = True
except ImportError:
    logger.info("reranker: sentence-transformers not installed, reranking disabled")


def _load_models():
    """Lazy-load cross-encoder and SEE embedder on first use."""
    if not _HAS_CROSS_ENCODER:
        return None, None
    if _MODELS["cross_encoder"] is not None:
        return _MODELS["cross_encoder"], _MODELS["see_embedder"]

    try:
        ce = CrossEncoder("BAAI/bge-reranker-v2-m3")
        see = SentenceTransformer("all-MiniLM-L6-v2")
        _MODELS["cross_encoder"] = ce
        _MODELS["see_embedder"] = see
        logger.info("reranker: loaded cross-encoder + SEE embedder")
        return ce, see
    except Exception as e:
        logger.warning("reranker: failed to load models: %s", e)
        _HAS_CROSS_ENCODER = False
        return None, None


def _see_should_skip(query: str, doc_text: str, threshold: float = 0.3) -> bool:
    """SEE: compute token-level query-doc similarity.
    
    If similarity falls below threshold, skip the expensive cross-encoder pass.
    """
    _, embedder = _load_models()
    if embedder is None:
        return False

    try:
        import torch
        q_emb = embedder.encode(query, convert_to_tensor=True)
        d_emb = embedder.encode(doc_text[:512], convert_to_tensor=True)
        sim = torch.cosine_similarity(q_emb.unsqueeze(0), d_emb.unsqueeze(0)).item()
        return sim < threshold
    except Exception:
        return False


def rerank(query: str, results: list[dict], top_k: int = 0,
           see_threshold: float = 0.3) -> list[dict]:
    """Rerank search results using a cross-encoder with SEE early-exit.
    
    Args:
        query: The original search query.
        results: List of result dicts, each with at least a 'verse' or 'text' field.
        top_k: Max results to rerank (0 = all).
        see_threshold: SEE similarity threshold.
    
    Returns:
        Reranked results list. If reranker unavailable, returns unchanged.
    """
    cross_encoder, _ = _load_models()
    if cross_encoder is None:
        return results

    rerank_limit = top_k if top_k > 0 else len(results)
    candidates = results[:rerank_limit]
    rest = results[rerank_limit:]

    reranked_total = 0
    early_exits = 0

    scored = []
    for result in candidates:
        # Extract text for scoring
        doc_text = result.get("verse", "") or result.get("text", "") or ""
        if not doc_text:
            continue

        # SEE: skip low-similarity docs before cross-encoder
        if _see_should_skip(query, doc_text, see_threshold):
            early_exits += 1
            scored.append((0.01, result))
            continue

        # Full cross-encoder pass
        try:
            score = cross_encoder.predict([(query, doc_text)])[0]
            reranked_total += 1
        except Exception:
            score = 0.0
        scored.append((score, result))

    # Sort by score descending
    scored.sort(key=lambda x: -x[0])
    reranked = [r for _, r in scored] + rest

    logger.debug("reranker: %d/%d reranked, %d early-exits, %d bypassed",
                 reranked_total, len(candidates), early_exits, len(rest))

    return reranked


def rerank_if_available(query: str, results: list[dict], top_k: int = 20) -> list[dict] | None:
    """Convenience wrapper: rerank if cross-encoder available, else None."""
    if not _HAS_CROSS_ENCODER:
        return None
    return rerank(query, results, top_k=top_k)
