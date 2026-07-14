"""Wiki article endpoints — entity lookup, browse, search, concordance."""

import json
from fastapi import APIRouter, HTTPException, Query

# Import caches populated at startup by server.py's lifespan handler
from web.cache import WIKI_CACHE

router = APIRouter()


@router.get("/api/v1/wiki/search")
def search_wiki(q: str = ""):
    """Search wiki articles by title or summary."""
    query = q.strip().lower()
    if not query or not WIKI_CACHE:
        return {"ok": True, "data": {"results": [], "total": 0}}

    results = []
    for article in WIKI_CACHE.values():
        title = (article.get("title") or "").lower()
        summary = (article.get("summary") or "").lower()
        if query in title or query in summary:
            score = 2 if query in title else 1
            results.append({
                "id": article["id"],
                "title": article["title"],
                "summary": (article.get("summary") or "")[:200],
                "article_type": article.get("article_type", ""),
                "score": score,
            })

    results.sort(key=lambda r: -r["score"])
    return {"ok": True, "data": {"results": results[:20], "total": len(results)}}


@router.get("/api/v1/wiki/browse/{type_name:path}")
def browse_wiki(type_name: str = "entity"):
    """Browse wiki articles by type (entity, concept, etc.)."""
    t = type_name.strip("/").lower()
    results = [
        {"id": a["id"], "title": a["title"], "summary": a["summary"][:100]}
        for a in WIKI_CACHE.values()
        if a["article_type"] == t
    ]
    return {"ok": True, "data": {"type": t, "articles": results, "total": len(results)}}


@router.get("/api/v1/wiki/concordance/{entity_id:path}")
def wiki_concordance(entity_id: str):
    """Get key verses for an entity from its wiki article."""
    eid = entity_id.strip("/").lower().replace(" ", "_")
    article = WIKI_CACHE.get(eid)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article not found: {eid}")
    try:
        verses = json.loads(article.get("key_verses", "[]"))
    except (json.JSONDecodeError, TypeError):
        verses = []
    return {"ok": True, "data": {"entity": eid, "verses": verses, "total": len(verses)}}


@router.get("/api/v1/wiki/{entity_id:path}")
def get_wiki_article(entity_id: str):
    """Get a wiki article about a biblical entity or concept."""
    eid = entity_id.strip("/").lower().replace(" ", "_")
    article = WIKI_CACHE.get(eid)
    if not article:
        raise HTTPException(status_code=404, detail=f"Article not found: {eid}")
    result = dict(article)
    try:
        result["key_verses"] = json.loads(result.get("key_verses", "[]"))
    except (json.JSONDecodeError, TypeError):
        result["key_verses"] = []
    try:
        result["cross_references"] = json.loads(result.get("cross_references", "[]"))
    except (json.JSONDecodeError, TypeError):
        result["cross_references"] = []
    return {"ok": True, "data": result}
